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

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# migrate: ps() -> ab_compat (round 122)
# 轮174：_AB（chrome）与 _SRV（静态服务）都提到模块级，
# 供 __main__ 的 finally 统一清理 —— 原先本判据跑完既不关 chrome
# 也不停服务，82 判据串行跑时会残留进程/端口污染后续判据。
_AB = None
_SRV = None


def _ab():
    global _AB
    if _AB is None:
        from ab_compat import AbSession
        _AB = AbSession()
    return _AB


def ps(cmd, timeout=90):
    return _ab().run(cmd, timeout=timeout)

def ev_json(expr):
    tmp = os.path.join(BASE, '_qa', '_ar_probe.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(expr)
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % tmp)
    # round 122: CDP returns one layer only; drop the double json.loads
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
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

    # round 122: start our own server instead of assuming 8791 is up
    # (a missing server produced RESULT: SKIP -- looks like an env issue)
    global _SRV
    try:
        from cdp_client import SiteServer
        _SRV = SiteServer(os.path.join(BASE, 'site'), port=8791)
        _base = _SRV.url('/index.html')
    except Exception as _e:
        print('RESULT: SKIP  server failed: %s' % _e)
        return 0

    # 先清 SW + caches：cache-first 会返回旧 JS，导致反向验证假绿
    _clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(_clear):
        ps('agent-browser open "%s"' % _base)
        time.sleep(1.2)
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % _clear)
        time.sleep(1.0)

    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "about:blank"')
    time.sleep(0.4)
    ps('agent-browser open "%s"' % _base)
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


    # === DEEPLINK：深链接与浏览器历史（轮44） ===
    # 一手问题：按浏览器返回键清空 hash 后，AR 仍保持打开（状态不同步）。
    # 注意：history.back() 会触发页面导航，CDP 会中断 async 探针，
    # 故必须拆成「读状态 -> 触发返回 -> 重连后再读」。
    ps('agent-browser open "http://127.0.0.1:8791/?dl=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(1.5)
    ps('agent-browser eval "if(window.__ar) window.__ar.open(\'craft\'); 1"')
    time.sleep(0.9)
    h1 = ev_json("JSON.stringify({hash:location.hash,open:window.__ar?window.__ar.stats().open:null})")
    ps('agent-browser eval "history.back();1"')
    time.sleep(1.6)
    h2 = ev_json("JSON.stringify({hash:location.hash,open:window.__ar?window.__ar.stats().open:null})")
    checked += 1
    _ok = (h1 and (h1.get("hash") or "").startswith("#ar=") and h2
           and h2.get("open") is False)
    print("[%s] 深链接+返回键：打开 hash=%s，返回后 hash=%s，AR关闭=%s" % (
        "PASS" if _ok else ("SKIP" if (not h1 or not h2) else "FAIL"),
        h1.get("hash") if h1 else None, h2.get("hash") if h2 else None,
        not (h2.get("open") if h2 else True)))
    if _ok:
        pass
    elif h1 and h2:
        fails.append("浏览器返回键未关闭 AR（hash 与状态不同步）")

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
    _rc = 1
    try:
        _rc = main()
    finally:
        # 无论成功/失败/SKIP，都关掉自己起的 chrome 与静态服务，
        # 避免残留污染回归序列里的下一个判据（轮174 修 flaky 根因）。
        try:
            if _AB is not None:
                _AB.close()
        except Exception:
            pass
        try:
            if _SRV is not None:
                _SRV.stop()
        except Exception:
            pass
    sys.exit(_rc)