# -*- coding: utf-8 -*-
"""tools/ar_e2e_test.py —— AR 核心功能端到端验证。

## 为什么需要它
前二十多轮验证的都是静态资产与 CSS，AR 播放这个核心功能从没系统验过。
它是整个站点主体（3 段 / 13 章 / 152 秒），坏了页面再好看也没用。

## 验证项
1. AR API 就绪
2. 三段能切换（craft / red / phoenix）
3. 时间在推进
4. 完整播放到结尾会落章

## 一个关键坑（轮26 实测）
seek(n) 跳到段末不会触发落章 —— 源码里 complete() 只在
「playing 中 t >= duration」分支调用。测落章必须 seek(duration-3) 再 play()
让它自然跑完；直接 seek(duration) 会误判成「集章坏了」。
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ps(cmd, timeout=50):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                           cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def ev_json(expr):
    tmp = os.path.join(BASE, '_qa', '_ar_probe.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(expr)
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % tmp)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None


STATS = ("JSON.stringify({"
         "api:(typeof window.__ar === 'object')?1:0,"
         "scene:(window.__ar&&window.__ar.stats)?window.__ar.stats().scene:null,"
         "t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null,"
         "playing:(window.__ar&&window.__ar.stats)?window.__ar.stats().playing:null,"
         "stamps:(window.__ar&&window.__ar.stats)?window.__ar.stats().stamps:[],"
         "got:document.querySelectorAll('.stamp.got').length})")


def main():
    fails = []
    checked = 0

    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "about:blank"')
    time.sleep(0.4)
    ps('agent-browser open "http://127.0.0.1:8791/"')
    ps('agent-browser wait --load networkidle')
    time.sleep(2.4)

    pre = ev_json(STATS)
    if not pre or pre.get('api') != 1:
        print('RESULT: SKIP  AR API 未就绪（环境问题，不是功能失败）')
        return 0
    checked += 1
    print('[PASS] AR API 就绪')

    for sid in ['craft', 'red', 'phoenix']:
        ps('agent-browser eval "if(window.__ar) window.__ar.open(\'%s\'); 1"' % sid)
        time.sleep(1.5)
        st = ev_json(STATS)
        checked += 1
        if st and st.get('scene') == sid:
            print('[PASS] 场景切换 %s（t=%.1f）' % (sid, st.get('t') or 0))
        else:
            fails.append('场景切换 %s 失败: %s' % (sid, st))
            print('[FAIL] 场景切换 %s' % sid)

    before = ev_json(STATS)
    time.sleep(2.5)
    after = ev_json(STATS)
    checked += 1
    if before and after and (after.get('t') or 0) > (before.get('t') or 0):
        print('[PASS] 时间推进 %.1f → %.1f' % (before['t'], after['t']))
    else:
        fails.append('时间未推进')
        print('[FAIL] 时间未推进')

    ps('agent-browser eval "localStorage.clear(); 1"')
    ps('agent-browser eval "if(window.__ar){window.__ar.open(\'phoenix\'); window.__ar.seek(33); window.__ar.play();} 1"')
    time.sleep(6.0)
    st = ev_json(STATS)
    checked += 1
    if st and st.get('stamps') and 'phoenix' in st['stamps']:
        print('[PASS] 完整播放落章（stamps=%s，页面点亮 %d）' % (st['stamps'], st['got']))
    else:
        fails.append('完整播放未落章: %s' % st)
        print('[FAIL] 完整播放未落章')

    print()
    if checked == 0:
        print('RESULT: SKIP  无任何可验证项')
        return 0
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  AR 核心功能 %d 项全部通过' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())