# -*- coding: utf-8 -*-
r"""tools/cache_bump_guard.py —— 改了 cache-first 资源必须同时 bump SW VERSION。

## 为什么需要（轮134 实测，且抓到我自己）
sw.js 第 29-30 行的注释自己写着：

    PRECACHE 清单未变但 index.html / main.css / ar.js 内容变了 —— 不 bump 则已装 SW 的访客
    对 JS/CSS 走 cache-first，永远拿不到旁白开关（本项目第 4 次踩同一坑，写进注释）。

即这是一条**代码自己声明过的不变量**，而且已经错过 4 次。
本轮量近 40 个提交，又抓到 1 次未记账的违规：

    637931a  feat(data): 演示数据严禁出现 10 的倍数 …（轮128，我自己）
      改了 site/assets/data/footer-stats.js（在 PRECACHE 名单里）却没 bump VERSION

后果不是「不够新」而是**直接违背老大的口径**：footer-stats.js 走 cache-first，
不 bump 则已装 SW 的访客继续拿旧样本 —— 页脚仍显示 13,000 / 4,780 这类 10 的倍数。
这次是轮134 我因改 CSS 顺手 bump 到 v54，才把它带出来；靠运气不算守住。

## 判据
  A 从 sw.js 解析 VERSION 与 PRECACHE 清单，构成 cache-first 资源集合
    （index.html + main.css + PRECACHE 各项；sw.js 自身不算）。
  B 对 HEAD 提交：若其改动文件与该集合有交集，而 VERSION 在 HEAD 与其父提交
    之间没变 -> FAIL（点名是哪几个文件、当前 VERSION）。
  C 工作区对账（不依赖历史，本地提交前就能拦）：未提交改动若含集合内文件
    而 sw.js 的 VERSION 未改 -> FAIL。
  D **历史不可用时判 FAIL，不判 SKIP**：CI 的 actions/checkout 必须
    fetch-depth: 0。缺历史是**我们自己配的管线契约缺失**，属可修的行动项，
    不是外部环境不可控 —— 按轮133 的结论，SKIP 只能留给真正的环境前提缺失
    （如没有 chrome），拿 SKIP 掩盖配置缺失就是假守护（U-413/U-425 同族）。

## 尺子有效性自检（U-149/U-151）
  S1 造一个「改了 PRECACHE 内文件、VERSION 不变」的假提交记录 -> 必须判红
  S2 造一个「改了非缓存文件（tools/*.py）、VERSION 不变」-> 不得误报
  S3 造一个「改了缓存文件且 VERSION 变了」-> 不得误报
自检不依赖 git，纯函数级，因此在任何环境都有效。
"""
import io
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = os.path.join(BASE, 'site', 'sw.js')
ALWAYS_CACHE_FIRST = ['site/index.html', 'site/assets/css/main.css']


def git(args, timeout=60):
    try:
        r = subprocess.run(['git'] + args, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           cwd=BASE, timeout=timeout)
        return (r.stdout or '').strip(), r.returncode
    except Exception:
        return '', 1


def parse_sw(text):
    """从 sw.js 取 VERSION 与 PRECACHE 清单。"""
    m = re.search(r"var\s+VERSION\s*=\s*'v?([\w.]+)'", text)
    ver = m.group(1) if m else None
    mm = re.search(r'PRECACHE\s*=\s*\[(.*?)\]', text, flags=re.S)
    items = re.findall(r"'([^']+)'", mm.group(1)) if mm else []
    return ver, items


def cache_first_set(precache):
    s = set(ALWAYS_CACHE_FIRST)
    for p in precache:
        s.add('site/' + p.lstrip('./'))
    s.discard('site/sw.js')
    return s


def evaluate(changed, ver_before, ver_after, cset):
    """核心判定（纯函数，自检也用它）。"""
    hits = sorted(set(changed) & cset)
    if not hits:
        return []
    if ver_before == ver_after:
        return ['改了 %d 个 cache-first 资源（%s%s）但 SW VERSION 未变（v%s）'
                '—— 已装 SW 的访客走 cache-first，永远拿不到新版'
                % (len(hits), ', '.join(os.path.basename(x) for x in hits[:3]),
                   '…' if len(hits) > 3 else '', ver_after)]
    return []


def selftest(cset):
    bad = []
    # S1 改了缓存文件、VERSION 不变 -> 必须红
    r1 = evaluate(['site/assets/data/footer-stats.js', 'tools/x.py'],
                  '54', '54', cset)
    ok1 = bool(r1)
    print('  [%s] S1 改 PRECACHE 内文件未 bump -> %s'
          % ('ok' if ok1 else 'X', '判红' if ok1 else '放过（判据无牙）'))
    if not ok1:
        bad.append('S1 未抓到未 bump')
    # S2 只改非缓存文件 -> 不得误报
    r2 = evaluate(['tools/foo_test.py', 'memory/08-verify.md'],
                  '54', '54', cset)
    ok2 = not r2
    print('  [%s] S2 只改 tools/memory -> %s'
          % ('ok' if ok2 else 'X', '不误报' if ok2 else '误报 %s' % r2[:1]))
    if not ok2:
        bad.append('S2 误报非缓存改动')
    # S3 改了缓存文件且 bump 了 -> 不得误报
    r3 = evaluate(['site/assets/css/main.css'], '53', '54', cset)
    ok3 = not r3
    print('  [%s] S3 改 main.css 且 VERSION 变了 -> %s'
          % ('ok' if ok3 else 'X', '不误报' if ok3 else '误报'))
    if not ok3:
        bad.append('S3 误报已 bump 的改动')
    return bad


def main():
    if not os.path.exists(SW):
        print('RESULT: FAIL  找不到 site/sw.js —— 部署面结构已变，本判据的前提不成立')
        return 1
    ver_now, precache = parse_sw(io.open(SW, encoding='utf-8',
                                         errors='ignore').read())
    if not ver_now or not precache:
        print('RESULT: FAIL  sw.js 解析不出 VERSION/PRECACHE（v=%s 清单 %d 项）'
              % (ver_now, len(precache)))
        return 1
    cset = cache_first_set(precache)
    print('=== cache-first 资源集合 %d 项（index.html + main.css + PRECACHE %d）==='
          % (len(cset), len(precache)))
    print('  当前 SW VERSION = v%s' % ver_now)
    print()
    print('=== 尺子有效性自检 ===')
    bs = selftest(cset)
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1

    fails = []
    # B HEAD 提交对账（需历史）
    cnt, rc = git(['rev-list', '--count', 'HEAD'])
    try:
        n = int(cnt)
    except ValueError:
        n = 0
    if n < 2:
        # 缺历史是我们自己的 CI 配置问题（checkout 未设 fetch-depth: 0），
        # 判 FAIL 而不是 SKIP —— 否则就是一条永远不执行的假守护。
        print('RESULT: FAIL  git 历史不可用（HEAD 只有 %d 个提交）。'
              'CI 的 actions/checkout 必须设 fetch-depth: 0，'
              '否则本判据无法执行 —— 这是管线契约缺失，不记 SKIP。' % n)
        return 1
    d, _ = git(['diff', '--name-only', 'HEAD^', 'HEAD'])
    changed = [x.strip() for x in d.splitlines() if x.strip()]
    ver_prev, _ = parse_sw(git(['show', 'HEAD^:site/sw.js'])[0])
    subj, _ = git(['log', '-1', '--format=%s'])
    print('=== HEAD 提交对账 ===')
    print('  %s' % subj[:76])
    print('  改动 %d 个文件；VERSION %s -> %s' % (len(changed), ver_prev, ver_now))
    fails += evaluate(changed, ver_prev, ver_now, cset)

    # C 工作区对账（不依赖历史）
    d2, _ = git(['diff', '--name-only', 'HEAD'])
    d3, _ = git(['ls-files', '--others', '--exclude-standard'])
    wt = [x.strip() for x in (d2 + '\n' + d3).splitlines() if x.strip()]
    if wt:
        print()
        print('=== 工作区未提交改动对账 ===')
        print('  %d 个文件待提交' % len(wt))
        # before 必须是 HEAD 里的 VERSION，after 是工作区 sw.js 的 VERSION。
        # 轮134 自查出的 bug：原先两侧都读工作区，值恒相等 ——
        # 于是「改了 main.css 同时 bump 了 sw.js」这种合法的进行中状态
        # 也会被判红，判据就变成谁也别想改资源的假守护。
        head_sw, rc = git(['show', 'HEAD:site/sw.js'])
        ver_head = parse_sw(head_sw)[0] if rc == 0 and head_sw else ver_now
        sw_wt, _ = parse_sw(io.open(SW, encoding='utf-8',
                                    errors='ignore').read())
        wt_fails = evaluate(wt, ver_head, sw_wt, cset)
        if wt_fails:
            print('  （工作区：HEAD 的 VERSION 为 v%s，工作区为 v%s）'
                  % (ver_head, sw_wt))
        fails += wt_fails

    if fails:
        print()
        print('RESULT: FAIL  %d 处 cache-first 改动未 bump：' % len(fails))
        for f in fails:
            print('  -', f)
        return 1
    print()
    print('RESULT: PASS  cache-first 资源改动与 SW VERSION 同步，'
          '且自检证明「未 bump」能抓到、「非缓存改动」不误报')
    return 0


if __name__ == '__main__':
    sys.exit(main())
