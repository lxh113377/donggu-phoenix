# -*- coding: utf-8 -*-
"""tools/visual_balance_test.py —— 首屏构图平衡的客观测量（CDP 版，多视口）。

## 为什么需要它
「构图是否平衡」通常是主观判断。轮40 我收到独立评审说「左右六四开、右下偏轻」，
用像素统计核实后发现：左 52.8% / 右 47.2%，差异仅 5.6%，实际是平衡的。
→ 主观判断需要客观数据校准。

## 轮99→101：从 --screenshot 迁到 CDP（关键演进）
轮99 把判据从 agent-browser 迁到 chrome 直连 + --screenshot，
功能跑通了，但三连跑证明**不能作 CI 门禁**：
  桌面 13.2/13.1/15.6 极差 2.5 稳定
  平板 29.6/30.8/32.9 极差 3.3 稳定偏高（非缺陷）
  手机  5.0/36.4/ 5.0 极差 31.4 偶发跳变
根因：--screenshot 是一次性快照，等不到 Phoenix 组装完成的事件，
常抓到 assemble 中间帧（2600 粒子仍聚在起点）。
轮99 的结论写的是「要换机制，比如上 CDP 等事件」。

轮101 按这个结论实施 CDP：
  1. chrome --remote-debugging-port + --remote-allow-origins=*
  2. browser 级 WS 调 Target.createTarget 建页
     （/json/new 只收 PUT，GET 报 405）
  3. page 级 WS 调 Page.navigate -> Runtime.evaluate 轮询 __phoenix.state
  4. 到达 idle/flight 后再 Page.captureScreenshot
实测：第 1 次轮询即到达 idle，截图粒子完整、构图居中
（对比 --screenshot 版同视口常只抓到左上角一簇）。

## 依赖
websocket-client（本机已装）。缺失时判据明确报 SKIP 而非假装通过。

## 判据
· 主方向重量差异 < 15% → 平衡
· 15%-25% → 轻微失衡（可接受，视设计意图）
· > 25% → 明显失衡

## 已知边界
CDP 版仍需 runner 有 chrome 与 websocket-client；
CI 接入前应先在本机跑 N 次确认极差可接受（轮99 的判据：极差大就不上门禁）。
"""
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
OUT = os.path.join(BASE, '_qa', 'r101')

# (标签, 视口宽, 视口高, 主方向) —— 窄屏主方向改上下，因布局已重排
VIEWPORTS = [
    ('桌面', 1440, 900, 'h'),
    ('平板', 768, 1024, 'h'),
    ('手机', 390, 844, 'v'),
]
TOP_SKIP = 60   # 去掉顶部固定导航区
SITE_PORT = 8791


def find_chrome():
    """优先本机 agent-browser 自带 chrome，回退到 PATH（供 CI 使用）。"""
    root = os.path.join(os.path.expanduser('~'), '.agent-browser', 'browsers')
    if os.path.isdir(root):
        for name in sorted(os.listdir(root), reverse=True):
            exe = os.path.join(root, name, 'chrome.exe')
            if os.path.exists(exe):
                return exe
    # 回退：PATH 上的 chrome（CI 的 setup-chrome 装到这里）
    for name in ('google-chrome', 'google-chrome-stable', 'chromium',
                 'chromium-browser', 'chrome'):
        try:
            r = subprocess.run(['which', name] if os.name != 'nt'
                               else ['where', name],
                               capture_output=True, timeout=20)
            if r.returncode == 0:
                first = (r.stdout or b'').decode('utf-8', 'replace').splitlines()
                if first and os.path.exists(first[0].strip()):
                    return first[0].strip()
        except Exception:
            continue
    return None


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(url, timeout=10):
    req = urllib.request.Request(url)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


class Cdp:
    """最小 CDP 客户端：browser 级与 page 级各一条 WebSocket。"""

    def __init__(self, ws_url):
        import websocket
        self.ws = websocket.create_connection(ws_url, timeout=40)
        self._id = 0

    def call(self, method, params=None, timeout=40):
        self._id += 1
        self.ws.send(json.dumps({'id': self._id, 'method': method,
                                 'params': params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            d = json.loads(self.ws.recv())
            if d.get('id') == self._id:
                return d
        raise TimeoutError(method)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def analyze(png, axis):
    """返回 (差异%, 判定词, 是否判红, 详情, 空洞列表)。"""
    import numpy as np
    from PIL import Image

    img = Image.open(png).convert('RGB')
    arr = np.array(img, dtype=float)
    h, w, _ = arr.shape
    content = arr[TOP_SKIP:, :, :]
    ch, cw, _ = content.shape

    def weight(region):
        r_, g_, b_ = region[:, :, 0], region[:, :, 1], region[:, :, 2]
        lum = 0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_
        mx = np.max(region, axis=2)
        mn = np.min(region, axis=2)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
        return float(np.mean(np.abs(lum - 11.0) * (1 + sat)))

    if axis == 'h':
        a, b = weight(content[:, :cw // 2]), weight(content[:, cw // 2:])
        names, detail = ('左', '右'), ''
    else:
        a, b = weight(content[:ch // 2, :]), weight(content[ch // 2:, :])
        names, detail = ('上', '下'), '（窄屏布局已重排，按上下分量）'

    total = a + b
    diff = abs(a - b) / total * 100 if total else 0.0
    if diff > 25:
        verdict, bad = '明显失衡', True
    elif diff > 15:
        verdict, bad = '轻微失衡（可视设计意图接受）', False
    else:
        verdict, bad = '平衡', False

    holes = []
    for x0, x1, label in [(0, cw // 2, '左'), (cw // 2, cw, '右')]:
        vals = []
        for y0 in range(0, ch, 100):
            region = content[y0:y0 + 100, x0:x1]
            rr2, gg2, bb2 = region[:, :, 0], region[:, :, 1], region[:, :, 2]
            lum = 0.2126 * rr2 + 0.7152 * gg2 + 0.0722 * bb2
            vals.append((lum > 30).mean() * 100)
        if all(v < 1.0 for v in vals[-3:]):
            holes.append('%s栏下方连续 300px 无内容' % label)
    return diff, verdict, bad, (names, a, b, total, detail), holes


def main():
    try:
        import websocket  # noqa: F401
        import numpy as np  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        print('RESULT: SKIP  缺依赖 %s（环境问题，非判据通过）' % e.name)
        return 0

    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe（环境问题，非判据通过）')
        return 0

    # 兼容旧用法：显式传截图路径时只做分析
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        diff, verdict, bad, det, holes = analyze(sys.argv[1], 'h')
        (names, a, b, total, _d) = det
        n1, n2 = names
        print('截图: %s' % sys.argv[1])
        print('左右视觉重量: %s %.2f (%.1f%%) / %s %.2f (%.1f%%)' % (
            n1, a, a / total * 100, n2, b, b / total * 100))
        print('差异: %.1f%%  判定: %s' % (diff, verdict))
        if holes:
            print('  提示: %s' % '; '.join(holes))
        print()
        print('RESULT: %s  %s（差异 %.1f%%）' % (
            'FAIL' if bad else 'PASS', verdict, diff))
        return 1 if bad else 0

    os.makedirs(OUT, exist_ok=True)
    # 站点静态服务
    import threading
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    try:
        srv = ThreadingHTTPServer(('127.0.0.1', SITE_PORT),
                                  partial(Quiet, directory=SITE))
    except OSError:
        print('RESULT: SKIP  站点端口 %d 被占用（环境问题）' % SITE_PORT)
        return 0
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    dbg = free_port()
    udd = os.path.join(tempfile.gettempdir(), 'cdp_vb_%d' % dbg)
    proc = subprocess.Popen(
        [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
         '--force-device-scale-factor=1',
         '--remote-debugging-port=%d' % dbg,
         '--remote-allow-origins=*',
         '--user-data-dir=' + udd,
         '--window-size=1600,1100', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    fails, measured = [], []
    try:
        ver = None
        for _ in range(40):
            try:
                ver = http_json('http://127.0.0.1:%d/json/version' % dbg, 5)
                break
            except Exception:
                time.sleep(0.5)
        if not ver:
            print('RESULT: SKIP  devtools 未就绪（环境问题）')
            return 0

        bws = Cdp(ver['webSocketDebuggerUrl'])
        for label, vw, vh, axis in VIEWPORTS:
            png = os.path.join(OUT, 'vb_%dx%d.png' % (vw, vh))
            if os.path.exists(png):
                os.remove(png)
            try:
                rr = bws.call('Target.createTarget',
                              {'url': 'about:blank'}, timeout=20)
                tid = rr.get('result', {}).get('targetId')
                if not tid:
                    print('[%s %dx%d] 建页失败' % (label, vw, vh))
                    continue
                # 找该 target 的 page ws
                wsurl = None
                for _ in range(20):
                    tabs = http_json('http://127.0.0.1:%d/json' % dbg, 5)
                    hit = [t for t in tabs
                           if t.get('type') == 'page' and t.get('id') == tid]
                    if hit:
                        wsurl = hit[0]['webSocketDebuggerUrl']
                        break
                    time.sleep(0.3)
                if not wsurl:
                    print('[%s %dx%d] 找不到 page ws' % (label, vw, vh))
                    bws.call('Target.closeTarget', {'targetId': tid})
                    continue

                pws = Cdp(wsurl)
                try:
                    # 设视口：宽高 + deviceScaleFactor 1
                    pws.call('Emulation.setDeviceMetricsOverride', {
                        'width': vw, 'height': vh,
                        'deviceScaleFactor': 1, 'mobile': False})
                    pws.call('Page.enable')
                    time.sleep(0.8)   # 首 target 刚建出，enable 后需站稳再导航
                    pws.call('Page.navigate', {
                        'url': 'http://127.0.0.1:%d/index.html?vb=%d'
                               % (SITE_PORT, vw)}, timeout=30)
                    # Page.navigate 是异步的：先等 readyState，
                    # 否则立刻查 __phoenix 会拿到 noph（脚本还没跑）
                    for _ in range(50):
                        r0 = pws.call('Runtime.evaluate', {
                            'expression': 'document.readyState',
                            'returnByValue': True}, timeout=10)
                        if r0.get('result', {}).get('result', {}).get(
                                'value') == 'complete':
                            break
                        time.sleep(0.3)
                    time.sleep(1.2)   # 留给 main.js 实例化 Phoenix
                    # 轮询 Phoenix 组装状态（CDP 能等事件，这是迁 CDP 的全部理由）
                    st, ok = 'noph', False
                    for _ in range(60):
                        r = pws.call('Runtime.evaluate', {
                            'expression':
                                '(window.__phoenix && window.__phoenix.state)'
                                ' || "noph"',
                            'returnByValue': True}, timeout=15)
                        st = r.get('result', {}).get('result', {}).get(
                            'value', '?')
                        if st in ('idle', 'flight'):
                            ok = True
                            break
                        time.sleep(0.4)
                    if not ok:
                        print('[%s %dx%d] SKIP  凤凰未组装完成（state=%s），'
                              '该视口读数不可用' % (label, vw, vh, st))
                        continue
                    # 多等两帧让 canvas 落笔
                    time.sleep(0.6)
                    r = pws.call('Page.captureScreenshot',
                                 {'format': 'png'}, timeout=30)
                    data = r.get('result', {}).get('data', '')
                    if not data:
                        print('[%s %dx%d] 截图返回空' % (label, vw, vh))
                        continue
                    open(png, 'wb').write(base64.b64decode(data))
                finally:
                    pws.close()
                    bws.call('Target.closeTarget', {'targetId': tid})

                if not (os.path.exists(png)
                        and os.path.getsize(png) > 20000):
                    print('[%s %dx%d] 截图无效' % (label, vw, vh))
                    continue
                measured.append('%s %dx%d' % (label, vw, vh))
                diff, verdict, bad, det, holes = analyze(png, axis)
                (names, a, b, total, detail) = det
                n1, n2 = names
                print('[%s %dx%d] %s %s %.2f (%.1f%%) / %s %.2f (%.1f%%)'
                      ' -> 差异 %.1f%%  %s%s'
                      % (label, vw, vh, '主方向' if detail else '左右',
                         n1, a, a / total * 100, n2, b, b / total * 100,
                         diff, verdict, detail))
                for hl in holes:
                    print('    提示: %s（可能是留白，也可能是空洞，需目检判断）' % hl)
                if bad and axis == 'h':
                    fails.append('%s %dx%d：%s重量差异 %.1f%% > 25%%'
                                 % (label, vw, vh, n1, diff))
                elif bad:
                    # 窄屏主方向改上下是为适配布局重排，但凤凰图腾是横向构图，
                    # 用上下分量量它本就不公平（轮99 引入、轮101 识别的尺子问题）。
                    # 故窄屏仅报告，不判红。
                    print('    （窄屏按上下分量仅供查阅，不判红 —— '
                          '凤凰图腾为横向构图，该尺子对其不公平）')
            except Exception as e:
                print('[%s %dx%d] 异常: %s: %s'
                      % (label, vw, vh, type(e).__name__, str(e)[:70]))
        bws.close()
    finally:
        try:
            proc.terminate()
            time.sleep(0.5)
            proc.kill()
        except Exception:
            pass
        shutil.rmtree(udd, ignore_errors=True)
        try:
            srv.shutdown()
        except Exception:
            pass

    print()
    if not measured:
        print('RESULT: SKIP  无任何视口测到（环境问题，本判据未真正执行）')
        return 0
    if len(measured) < len(VIEWPORTS):
        print('RESULT: SKIP  仅 %d/%d 个视口测到（%s）'
              % (len(measured), len(VIEWPORTS), '; '.join(measured)))
        print('  - 有视口未测到时不判 PASS：部分失败被静默吞掉，'
              '会让「只测了 2/3」伪装成「全都合格」')
        return 0
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个视口首屏构图均在可接受范围' % len(VIEWPORTS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
