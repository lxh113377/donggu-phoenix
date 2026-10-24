# -*- coding: utf-8 -*-
"""tools/cdp_client.py —— 共享的 CDP（Chrome DevTools Protocol）客户端。

## 为什么要抽出来
轮101 在 visual_balance_test 里实现了 CDP 截图，轮103 又用它做态别量化。
本仓还有多条浏览器判据依赖已死的 agent-browser daemon，都要往 CDP 迁。
**重复实现就会各自漂移**（本仓已有教训：探针逻辑复制两份后口径不一致），
故抽成单一模块，所有浏览器判据共用。

## 为什么是 CDP 而不是 --screenshot
轮99 实测：--screenshot 是一次性快照，等不到页面内事件，
对异步渲染（如 Phoenix 粒子组装）会抓到中间帧，读数全假。
CDP 可以在截图前用 Runtime.evaluate 轮询任意页面状态。

## 两个必须知道的坑（轮101/102 实测）
  · Chrome 对 CDP 的 WebSocket 有 Origin 校验，
    必须带 --remote-allow-origins=*，否则握手 403
  · /json/new 新版只收 PUT（GET 报 405），
    要建页面请用 browser 级 WS 调 Target.createTarget

## 依赖
websocket-client（本机已装；CI 里由 pip install 保证）。
"""
import json
import os
import shutil
import socket
import subprocess
import tempfile
import atexit
import threading
import time
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def find_chrome():
    """优先本机 agent-browser 自带 chrome，回退到 PATH（供 CI 使用）。"""
    root = os.path.join(os.path.expanduser('~'), '.agent-browser', 'browsers')
    if os.path.isdir(root):
        for name in sorted(os.listdir(root), reverse=True):
            exe = os.path.join(root, name, 'chrome.exe')
            if os.path.exists(exe):
                return exe
    for name in ('google-chrome', 'google-chrome-stable', 'chromium',
                 'chromium-browser', 'chrome'):
        try:
            probe = ['where', name] if os.name == 'nt' else ['which', name]
            r = subprocess.run(probe, capture_output=True, timeout=20)
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
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url), timeout=timeout).read())


class SiteServer:
    """进程内静态服务（跑完关），不依赖外部常驻进程。"""

    def __init__(self, directory, port=None):
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass

        self.port = port or free_port()
        try:
            self.srv = ThreadingHTTPServer(
                ('127.0.0.1', self.port),
                partial(Quiet, directory=directory))
        except OSError:
            self.srv = None
            return
        self._stopped = False
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        # 轮185：注册退出兜底 —— 判据忘了 stop() 也不会把端口和
        # 服务线程留到进程结束（daemon 线程随进程退出，但端口在
        # 某些平台上不会立刻可复用，且泄漏会累积）。
        atexit.register(self.stop)

    @property
    def ok(self):
        return self.srv is not None

    def url(self, path=''):
        return 'http://127.0.0.1:%d%s' % (self.port, path)

    def stop(self):
        # 幂等：判据内显式 stop() 与 atexit 兜底会各调一次，
        # 而 ThreadingHTTPServer.shutdown() 重复调用可能挂住。
        if self.srv is None or getattr(self, '_stopped', False):
            return
        self._stopped = True
        try:
            self.srv.shutdown()
        except Exception:
            pass
        try:
            self.srv.server_close()
        except Exception:
            pass


class Cdp:
    """一条 WebSocket 的最小 CDP 客户端。"""

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
                if 'error' in d:
                    raise RuntimeError('%s: %s' % (method, d['error']))
                return d.get('result', {})
        raise TimeoutError(method)

    def eval_js(self, expression, timeout=20, await_promise=False):
        """执行 JS 并取值。

        await_promise=True 用于 async 表达式（如 (async function(){...})()）：
        '        'Runtime.evaluate 默认不等 Promise，直接取 value 会得到 {}
        '        '（轮119 实测：完整 PROBE 是 async IIFE，返回值全丢，判据因此静默 SKIP）。
        """
        params = {'expression': expression, 'returnByValue': True}
        if await_promise:
            params['awaitPromise'] = True
        r = self.call('Runtime.evaluate', params, timeout)
        return r.get('result', {}).get('value')

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


class Chrome:
    """起 headless chrome + devtools，提供建页/导航/截图。

    轮185：构造成功后注册 atexit 兜底。判据若忘了 close()，残留的
    chrome 进程会持续抢 CPU —— 实测这是「单跑绿、回归红」的根因
    （engine_behavior 测 calls/s，被前面判据泄漏的 chrome 压到
    可测门槛 30 以下就报「未测得」）。
    """

    def __init__(self, window='1600,1100', extra_flags=()):
        self.chrome = find_chrome()
        if not self.chrome:
            raise RuntimeError('找不到 chrome')
        self.port = free_port()
        self.udd = os.path.join(tempfile.gettempdir(),
                                'cdp_%d' % self.port)
        self.proc = subprocess.Popen(
            [self.chrome, '--headless=new', '--disable-gpu',
             '--hide-scrollbars', '--force-device-scale-factor=1',
             '--remote-debugging-port=%d' % self.port,
             '--remote-allow-origins=*',
             '--user-data-dir=' + self.udd,
             '--window-size=' + window] + list(extra_flags) + ['about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.version = None
        for _ in range(40):
            try:
                self.version = http_json(
                    'http://127.0.0.1:%d/json/version' % self.port, 5)
                break
            except Exception:
                time.sleep(0.5)
        if not self.version:
            raise RuntimeError('devtools 未就绪')
        self.browser = Cdp(self.version['webSocketDebuggerUrl'])
        self._closed = False
        # 轮185：注册退出兜底。判据若忘了 close()，残留 chrome
        # 会持续抢 CPU；atexit 里 close() 幂等，显式调用过也不会
        # 二次报错。
        atexit.register(self.close)

    def new_page(self, width, height, mobile=False):
        """建一个 page 并返回 (Cdp, targetId)。"""
        tid = self.browser.call(
            'Target.createTarget', {'url': 'about:blank'}, 20).get('targetId')
        wsurl = None
        for _ in range(20):
            tabs = http_json('http://127.0.0.1:%d/json' % self.port, 5)
            hit = [t for t in tabs if t.get('id') == tid]
            if hit:
                wsurl = hit[0]['webSocketDebuggerUrl']
                break
            time.sleep(0.3)
        if not wsurl:
            raise RuntimeError('拿不到 page ws')
        p = Cdp(wsurl)
        p.call('Emulation.setDeviceMetricsOverride', {
            'width': width, 'height': height,
            'deviceScaleFactor': 1, 'mobile': mobile})
        p.call('Page.enable')
        time.sleep(0.5)
        return p, tid

    def close_page(self, tid):
        try:
            self.browser.call('Target.closeTarget', {'targetId': tid})
        except Exception:
            pass

    def navigate(self, page, url, ready_timeout=25):
        page.call('Page.navigate', {'url': url}, 30)
        deadline = time.time() + ready_timeout
        while time.time() < deadline:
            try:
                if page.eval_js('document.readyState') == 'complete':
                    return True
            except Exception:
                pass
            time.sleep(0.3)
        return False

    def wait_for(self, page, js_condition, timeout=25, interval=0.4):
        """轮询页面内条件（CDP 的核心价值：能等事件）。"""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                last = page.eval_js(js_condition)
            except Exception:
                last = None
            if last:
                return last
            time.sleep(interval)
        return last

    def screenshot(self, page):
        import base64
        r = page.call('Page.captureScreenshot', {'format': 'png'}, 30)
        data = r.get('data', '')
        return base64.b64decode(data) if data else None

    def close(self):
        # 幂等：判据内显式 close() 与 atexit 兜底会各调一次
        if getattr(self, '_closed', False):
            return
        self._closed = True
        try:
            self.browser.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            time.sleep(0.4)
            self.proc.kill()
        except Exception:
            pass
        shutil.rmtree(self.udd, ignore_errors=True)
