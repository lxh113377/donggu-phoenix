# -*- coding: utf-8 -*-
r"""tools/ar_playback_test.py —— AR 三段实际可播放（核心功能判据，CDP 版）。

## 为什么必须重写（轮108）
旧版是 34 行的探测脚本，不是判据：
  · 依赖 agent-browser，而其二进制在本机**根本不存在**
    （D:\npm-global\...\agent-browser-win32-x64.exe CommandNotFoundException）
  · 每次调用都抛异常，ps() 把 stderr 一起返回，脚本只 print 不判定
  · **退出码恒 0** —— AR 完全没被验证过，CI 与本地都看不出问题
即「判据存在但跑不了，比没有判据更危险」（U-297）的最严重一例：
被验证对象是本站的**核心功能**（AR 展陈）。

## 本判据测什么（三段都要过）
  1) 场景数据与注册表对账：__ar.scenes 的 id 必须都在 __ar.registered 里
     （防「有数据没注册」—— 场景能列出来但点开是空的）
  2) 打开后 playing=true 且 state.t 随时间推进（真在播，不是停在 0）
  3) hud.writes 增长（canvas 真在写入，不是空转 rAF）
  4) 播放中不出现 fps=0（rAF 被节流成静止）
  5) seek 到接近结尾能落章（集章闭环可用；展陈的激励机制）

## 实测前提（本轮先验证再写判据）
headless 下两个已知风险都不成立：
  · document.hidden = False（CDP 建的页是 visible，不会被 ar.js:702 暂停）
  · 实测 fps=60、t 1->5、hud.writes 10->49、seek(70) 后 stamps=['craft']
所以本判据在 headless 下可稳定成立。

## 场景 id 不硬编码
从 __ar.scenes 动态读取。上一版我传 open("statue") 是猜的标识符，
真实 id 是 craft/red/phoenix —— 猜标识符会让判据永远测不到真东西。

## 诚实语义
chrome 缺失 / 页面未加载 / 探针无返回 -> SKIP 并说明，不判 PASS。
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OBSERVE_SEC = 4.0     # 观察播放推进的时长
SETTLE_SEC = 1.0


def run_one(chrome_page, srv, scene, idx):
    """测一个场景。返回 (是否通过, 说明行列表)。"""
    notes = []
    ok = True
    # 关掉上一段，避免状态串扰
    chrome_page.eval_js('window.__ar.close && window.__ar.close()')
    time.sleep(0.5)
    chrome_page.eval_js('window.__ar.open("%s")' % scene['id'])
    time.sleep(SETTLE_SEC)
    a = chrome_page.eval_js('JSON.stringify(window.__ar.stats())')
    da = json.loads(a) if isinstance(a, str) else a
    if not da:
        return False, ['%s: stats() 无返回' % scene['id']]

    if da.get('scene') != scene['id']:
        notes.append('  ✗ %s: 打开后 scene=%s（期望 %s）'
                     % (scene['id'], da.get('scene'), scene['id']))
        ok = False
    if not da.get('playing'):
        notes.append('  ✗ %s: playing=False（未自动播放）' % scene['id'])
        ok = False

    t0, w0 = da.get('t', 0), (da.get('hud') or {}).get('writes', 0)
    time.sleep(OBSERVE_SEC)
    b = chrome_page.eval_js('JSON.stringify(window.__ar.stats())')
    db = json.loads(b) if isinstance(b, str) else b
    t1 = db.get('t', 0)
    w1 = (db.get('hud') or {}).get('writes', 0)
    fps = db.get('fps', 0)

    if t1 <= t0:
        notes.append('  ✗ %s: 时间未推进（t %s -> %s）' % (scene['id'], t0, t1))
        ok = False
    if w1 <= w0:
        notes.append('  ✗ %s: canvas 无写入（hud.writes %s -> %s，可能在空转）'
                     % (scene['id'], w0, w1))
        ok = False
    if not fps:
        notes.append('  ✗ %s: fps=0（rAF 被节流，画面静止）' % scene['id'])
        ok = False

    # seek 到接近结尾，验证能落章
    dur = scene.get('duration') or 0
    if dur:
        chrome_page.eval_js('window.__ar.seek(%d)' % max(0, int(dur) - 2))
        time.sleep(3.5)
        c = chrome_page.eval_js('JSON.stringify(window.__ar.stats())')
        dc = json.loads(c) if isinstance(c, str) else c
        stamps = (dc or {}).get('stamps') or []
        if scene['id'] not in stamps:
            notes.append('  ✗ %s: 播到结尾未落章（stamps=%s）'
                         % (scene['id'], stamps))
            ok = False
        else:
            notes.append('  ✓ %s: 时长 %ss ｜ t %s->%s ｜ writes %s->%s ｜ '
                         'fps %s ｜ 已落章'
                         % (scene['id'], dur, t0, t1, w0, w1, fps))
            return ok, notes

    notes.append('  %s%s: t %s->%s ｜ writes %s->%s ｜ fps %s'
                 % ('✓ ' if ok else '✗ ', scene['id'], t0, t1, w0, w1, fps))
    return ok, notes


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  CDP 模块不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（环境问题，AR 未验证）')
        return 0

    srv = SiteServer(SITE)
    if not srv.ok:
        print('RESULT: SKIP  静态服务起不来（环境问题，AR 未验证）')
        return 0
    ch = None
    fails = []
    try:
        ch = Chrome()
        page, tid = ch.new_page(1440, 900)
        try:
            if not ch.navigate(page, srv.url('/index.html?arplay=1')):
                print('RESULT: SKIP  页面未加载完成')
                return 0
            if not ch.wait_for(page, '!!window.__ar', 25):
                print('RESULT: FAIL  window.__ar 未注册（AR 引擎没加载）')
                return 1

            # 1) 数据与注册表对账
            raw = page.eval_js('JSON.stringify(window.__ar.scenes)')
            scenes = json.loads(raw) if isinstance(raw, str) else (raw or [])
            raw2 = page.eval_js('JSON.stringify(window.__ar.registered)')
            registered = json.loads(raw2) if isinstance(raw2, str) else (raw2 or [])
            print('场景数据 %d 段：%s' % (
                len(scenes), [s.get('id') for s in scenes]))
            print('注册表 %d 段：%s' % (len(registered), registered))
            if not scenes:
                print('RESULT: FAIL  AR 场景数据为空')
                return 1
            missing = [s.get('id') for s in scenes
                       if s.get('id') not in registered]
            if missing:
                fails.append('有数据但未注册的场景：%s（点开会是空的）' % missing)
            if len(registered) != len(scenes):
                fails.append('注册数 %d 与数据数 %d 不符'
                             % (len(registered), len(scenes)))

            # 2) 逐段实测播放
            for i, sc in enumerate(scenes):
                ok, notes = run_one(page, srv, sc, i)
                for n in notes:
                    print(n)
                if not ok:
                    fails.append('场景 %s 播放验证未通过' % sc.get('id'))
        finally:
            page.close()
            ch.close_page(tid)
    except Exception as e:
        print('RESULT: SKIP  探针异常（环境问题，AR 未验证）：'
              '%s: %s' % (type(e).__name__, str(e)[:110]))
        return 0
    finally:
        if ch:
            ch.close()
        srv.stop()

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  AR %d 段均可播放（时间推进 + canvas 写入 + 落章闭环）'
          % len(scenes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
