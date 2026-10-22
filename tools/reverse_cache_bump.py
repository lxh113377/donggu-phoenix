# -*- coding: utf-8 -*-
r"""tools/reverse_cache_bump.py —— 用真实历史提交喂 cache_bump_guard。

为什么不用造样本：造样本只能证明「函数按我写的逻辑走」，
证明不了「逻辑对应真实世界的违规」。本仓已 5 次遇到只会报 PASS 的判据，
而 cache_bump_guard 守的正是「改资源忘 bump」这种极易漏的动作，
必须拿真提交验过。

真实案例（轮134 量近 40 个提交时抓到）：
  637931a  改了 PRECACHE 内的 footer-stats.js，VERSION 50 -> 50（未 bump）
           必须判红。后果直接违背老大「严禁 10 的倍数」的口径 ——
           footer-stats.js 走 cache-first，已装 SW 的访客继续拿旧样本。
  fddd12d  改 main.css/index.html，VERSION 52 -> 54（bump 了）必须放过
  d4a502a  改 phoenix.js/main.css/index.html，VERSION 51 -> 52 必须放过
  4b3428f  只动 memory/（非缓存面），VERSION 54 -> 54 必须放过
           —— 这一条防的是「判据把无关改动也点红」的误报方向。

诚实语义：取不到某个提交（浅克隆/仓库变更）时判 FAIL 并说明，
不静默跳过 —— 反向验证没跑成，等于没验。
"""
import importlib.util
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(BASE, 'tools', 'cache_bump_guard.py')

CASES = [
    ('637931a', '轮128 改 footer-stats.js 未 bump（已知真违规）', True),
    ('fddd12d', '轮134 改 main.css 且 bump 到 54（合规）', False),
    ('d4a502a', '轮133 改 phoenix/main.css/index 且 bump（合规）', False),
    ('4b3428f', '轮134 台账提交只动 memory（非缓存面，不该报）', False),
]


def load_gate():
    spec = importlib.util.spec_from_file_location('cbg', GATE)
    m = importlib.util.module_from_spec(spec)
    sys.modules['cbg'] = m
    spec.loader.exec_module(m)
    return m


def git(args):
    r = subprocess.run(['git'] + args, capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       cwd=BASE, timeout=90)
    return r.stdout or '', r.returncode


def main():
    if not os.path.exists(GATE):
        print('RESULT: FAIL  找不到主判据 %s（反向验证无从进行）' % GATE)
        return 1
    try:
        m = load_gate()
    except Exception as e:
        print('RESULT: FAIL  主判据不可加载：%s: %s'
              % (type(e).__name__, str(e)[:120]))
        return 1
    import io
    ver, precache = m.parse_sw(io.open(m.SW, encoding='utf-8',
                                       errors='ignore').read())
    if not ver or not precache:
        print('RESULT: FAIL  主判据解析不出 VERSION/PRECACHE')
        return 1
    cset = m.cache_first_set(precache)

    cnt, rc = git(['rev-list', '--count', 'HEAD'])
    try:
        n = int(cnt)
    except ValueError:
        n = 0
    if n < 2:
        print('RESULT: FAIL  git 历史不可用（HEAD 只有 %d 个提交），'
              '反向验证没跑成等于没验。CI 的 checkout 需 fetch-depth>=2。' % n)
        return 1

    print('=== 真实历史提交喂判据（cache-first 集合 %d 项，当前 v%s）==='
          % (len(cset), ver))
    fails = []
    for sha, desc, expect_red in CASES:
        changed_txt, rc1 = git(['diff', '--name-only', sha + '^', sha])
        if rc1 != 0 or not changed_txt.strip():
            # 允许「该提交确实没改任何文件」为空的情况不存在；取不到即失败
            fails.append('%s 取不到改动清单（提交不存在或被 GC）' % sha)
            print('  [X] %s  %s' % (sha, desc))
            continue
        changed = [x.strip() for x in changed_txt.splitlines() if x.strip()]
        v_prev = m.parse_sw(git(['show', sha + '^:site/sw.js'])[0])[0]
        v_cur = m.parse_sw(git(['show', sha + ':site/sw.js'])[0])[0]
        if v_prev is None or v_cur is None:
            fails.append('%s 取不到 sw.js VERSION（前=%s 后=%s）'
                         % (sha, v_prev, v_cur))
            print('  [X] %s  %s' % (sha, desc))
            continue
        res = m.evaluate(changed, v_prev, v_cur, cset)
        red = bool(res)
        ok = red == expect_red
        hits = sorted(set(changed) & cset)
        print('  [%s] %s  VERSION %s->%s  期望%s、实得%s'
              % ('ok' if ok else 'X', sha, v_prev, v_cur,
                 '判红' if expect_red else '放过',
                 '判红' if red else '放过'))
        print('        %s' % desc)
        if hits:
            print('        命中缓存文件: %s'
                  % ', '.join(os.path.basename(x) for x in hits[:3]))
        if res:
            print('        理由: %s' % res[0][:108])
        if not ok:
            fails.append('%s 判定与事实不符（期望%s，实得%s）'
                         % (sha, '判红' if expect_red else '放过',
                            '判红' if red else '放过'))
    print()
    if fails:
        print('RESULT: FAIL  %d 例不符：' % len(fails))
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  真实历史违规能抓到、三个合规提交不误报'
          '（含一个「只改非缓存面」的防误报样本）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
