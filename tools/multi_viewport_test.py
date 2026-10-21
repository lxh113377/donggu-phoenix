# -*- coding: utf-8 -*-
"""tools/multi_viewport_test.py —— 9 个视口的响应式验证（headless chrome 直连）。

## 为什么需要它
前面所有响应式验证只测过 1440 与 390 两个宽度。
轮41 扩展到 9 个视口后，立刻暴露了 320px 下两处越界（此前从未发现）：
  · craft-card 比父容器宽 36px（grid minmax 下限 320 > 容器 284）
  · carve-slider 右边界 336 > 320（label 的 ::after 补充文案撑爆布局）

## 覆盖视口
  320 / 360 / 375 / 414 / 768 / 1024 / 1280 / 1920 / 2560

## 判据（内核自轮41 起未改）
每个视口检查：
  1. documentElement.scrollWidth > innerWidth + 1 → 横向溢出
  2. 任何元素 right > innerWidth + 2 或 left < -2 → 元素越界
  3. 首屏关键元素被裁切（top<0 或 bottom>innerHeight）
  4. 首屏关键元素被固定导航遮挡

## 轮71 的传输层迁移（U-190 附的 13 项高优先级之一）
旧版靠 agent-browser daemon 逐项 set viewport —— daemon 本机连续不可用，
判据**从没产出过当前读数**。
新版：一个高窗口里放 9 个不同尺寸的 iframe，一次 headless 跑完。
  · 不依赖 daemon，也不依赖外部 8791/8792（进程内自起同源服务）
  · iframe 与站点同源 -> 可读 contentDocument
  · 每个 iframe 的 window.innerWidth 就是它的 CSS 尺寸，
    所以「视口」是真的，不是截图伪影（轮63 教训：--window-size=390
    会撞 Chrome 窗口最小宽度，产生「内容右移被切」的假象）

## 关键：必须防缓存污染
站点 SW 是 cache-first，不清缓存会读到旧 CSS，导致「改完仍报错」的假失败
（轮34/38/41 都踩过）。新版用唯一 query + 全新 user-data-dir 双保险。

## 零样本守卫
全部视口无数据时判 SKIP，不判 PASS（防止「没测到」被当「通过」）。

## 自检（轮71 新增）
合成一个 320px 视口、内含越界元素的页面，判据必须报出来。
报不出来说明尺子哑了 —— 读数不可信，直接 FAIL。
"""
import functools
import http.server
import json
import os
import random
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VIEWPORTS = [(320, 844), (360, 800), (375, 844), (414, 844), (768, 1024),
             (1024, 1024), (1280, 1024), (1920, 1080), (2560, 1080)]

# ---- 探针内核（轮41 定稿，口径勿改）----
KERNEL = r'''
function viewportProbe(win, doc){
  var de = doc.documentElement;
  var overflow = de.scrollWidth > win.innerWidth + 1;
  var wide = [];
  var all = doc.querySelectorAll('body *');
  for (var i = 0; i < all.length && wide.length < 5; i++) {
    var e = all[i];
    var r = e.getBoundingClientRect();
    if (r.width > 0 && (r.right > win.innerWidth + 2 || r.left < -2)) {
      var cn = (typeof e.className === 'string') ? e.className : '';
      wide.push({cls: cn.slice(0, 24) || e.tagName,
                 left: Math.round(r.left), right: Math.round(r.right)});
    }
  }
  var nav = doc.querySelector('.nav');
  var navBottom = nav ? Math.round(nav.getBoundingClientRect().bottom) : 0;
  var clipped = [];
  var covered = [];
  var KEY = ['.hero-tag', '.hero h1', '.hero-lead', '.hero-acts', '.hero-meta'];
  for (var j = 0; j < KEY.length; j++) {
    var ke = doc.querySelector(KEY[j]);
    if (!ke || !ke.offsetParent) continue;
    var kr = ke.getBoundingClientRect();
    if (kr.width === 0 && kr.height === 0) continue;
    if (kr.top < -2 || kr.bottom > win.innerHeight + 2) {
      clipped.push({sel: KEY[j], top: Math.round(kr.top), bottom: Math.round(kr.bottom)});
    }
    if (kr.top < navBottom - 2) {
      covered.push({sel: KEY[j], top: Math.round(kr.top), navBottom: navBottom});
    }
  }
  return {vw: win.innerWidth, vh: win.innerHeight, scrollW: de.scrollWidth,
          overflow: overflow, wide: wide, clipped: clipped, covered: covered};
}
'''


def find_chrome():
    root = os.path.join(os.path.expanduser('~'), '.agent-browser', 'browsers')
    if os.path.isdir(root):
        for d in sorted(os.listdir(root), reverse=True):
            exe = os.path.join(root, d, 'chrome.exe')
            if os.path.exists(exe):
                return exe
    for p in (r'C:\Program Files\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'):
        if os.path.exists(p):
            return p
    return None


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server():
    handler = functools.partial(_Handler, directory=BASE)
    httpd = socketserver.TCPServer(('127.0.0.1', 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return httpd, port


def dump_dom(chrome, port, path, vb, win, attempts=3):
    """chrome headless 取渲染后 DOM。

    轮70 实测 chrome 偶发 rc=0 但 stdout 为空（并发/profile 争用，与参数无关），
    故重试；重试仍空返回 None，由调用方判「不可用」而**不是**判通过。
    """
    for i in range(max(1, attempts)):
        out = _dump_once(chrome, port, path, vb, win)
        if out is not None:
            return out
        time.sleep(1.5)
    return None


def _dump_once(chrome, port, path, vb, win):
    udd = os.path.join(tempfile.gettempdir(), 'chr_mv_%d' % random.randint(0, 10**6))
    cmd = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
           '--force-device-scale-factor=1',
           # 必须强制 reduced-motion：站点在 prefers-reduced-motion 下把
           # .hero-tag/.hero h1/.hero-lead/.hero-acts/.hero-meta 设为
           # opacity:1;animation:none;clip-path:none —— 几何落在**终态**。
           # 不强制则读数取决于探针抓到动画的哪一帧：轮71 反向验证注入
           # translateX 后报的竟是「首屏被裁」而非越界，就是 reveal 动画
           # 未 settle 导致的时序敏感读数。
           '--force-prefers-reduced-motion',
           '--window-size=' + win,
           '--user-data-dir=' + udd, '--virtual-time-budget=%d' % vb,
           '--dump-dom', 'http://127.0.0.1:%d/%s' % (port, path)]
    dom = ''
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=170)
        dom = r.stdout or ''
    except subprocess.TimeoutExpired:
        return None
    finally:
        shutil.rmtree(udd, ignore_errors=True)
    m = re.search(r'<title>(.*?)</title>', dom, re.S)
    raw = (m.group(1) if m else '') or ''
    if not raw or raw == 'pending':
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def write(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(content)


def harness_html(vps, src_prefix, wait_ms):
    """把多个视口做成 iframe，一次跑完。"""
    html = r'''<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0;background:#111}iframe{border:0;display:block}</style></head>
<body><div id="host"></div><script>
var VPS = ''' + json.dumps(vps) + r''';
var host = document.getElementById('host');
VPS.forEach(function(v, i){
  var f = document.createElement('iframe');
  f.id = 'f' + i;
  f.src = __SRC__ + v[0] + '_' + Date.now();
  f.style.width = v[0] + 'px';
  f.style.height = v[1] + 'px';
  host.appendChild(f);
});
''' + KERNEL + r'''
function scrollAll(w, d, done){
  var y = 0, max = d.body.scrollHeight;
  (function step(){
    if (y > max) { w.scrollTo(0, 0); setTimeout(done, 350); return; }
    w.scrollTo(0, y); y += 600; setTimeout(step, 30);
  })();
}
setTimeout(function(){
  try{
    var res = [];
    var pending = VPS.length;
    VPS.forEach(function(v, i){
      var f = document.getElementById('f' + i);
      var d = f.contentDocument, w = f.contentWindow;
      if (!d || !w){ res.push({vw: v[0], err: 'no doc'}); if(--pending===0) finish(); return; }
      scrollAll(w, d, function(){
        var p = viewportProbe(w, d); p.vw = v[0]; res.push(p);
        if (--pending === 0) finish();
      });
    });
    function finish(){
      res.sort(function(a,b){ return a.vw - b.vw; });
      document.title = JSON.stringify(res);
    }
  }catch(e){ document.title = 'ERR ' + e; }
}, __WAIT__);
    </script></body></html>'''
    # 占位符替换必须作用在**拼接后的完整串**上（U-188 同课，第 4 次踩）：
    # 早先写成 a + b + c.replace(...)，只替换了最后一段，
    # __SRC__ 在中间段未替换 -> JS ReferenceError -> 探针静默无读数。
    html = html.replace('__SRC__', json.dumps(src_prefix))
    html = html.replace('__WAIT__', str(wait_ms))
    return html



def selftest(chrome, port):
    """data: iframe 跨源读不到，故自检用「同源临时文件」承载内层页面。"""
    write('_qa/mv_selftest_inner.html',
          '<!doctype html><html><head><style>body{margin:0}'
          '.bad{position:absolute;left:200px;width:160px;height:10px;background:#fff}'
          '</style></head><body><div class="bad"></div></body></html>')
    page = r'''<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0}iframe{border:0;display:block;width:320px;height:400px}</style></head>
<body><iframe id="f" src="/_qa/mv_selftest_inner.html"></iframe><script>
''' + KERNEL + r'''
setTimeout(function(){
  try{
    var f = document.getElementById('f');
    var d = f.contentDocument, w = f.contentWindow;
    if (!d || !w){ document.title = 'NO DOC'; return; }
    document.title = JSON.stringify([viewportProbe(w, d)]);
  }catch(e){ document.title = 'ERR ' + e; }
}, 600);
</script></body></html>'''
    write('_qa/mv_selftest.html', page)
    rows = dump_dom(chrome, port, '_qa/mv_selftest.html', vb=12000, win='400,500')
    if not rows:
        return ['自检无读数（重试 3 次仍无输出）——判据不可用，不等于通过']
    r0 = rows[0]
    problems = []
    if r0.get('err'):
        return ['自检读不到内层文档']
    if not r0.get('overflow'):
        problems.append('320 视口里放了 right=360 的元素却未判出横向溢出 -> 内核哑了')
    if not r0.get('wide'):
        problems.append('越界元素未被列出 -> 元素级检测失效')
    return problems


def main():
    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe')
        return 0

    httpd, port = start_server()
    try:
        bad = selftest(chrome, port)
        if bad:
            print('RESULT: FAIL  判据自检不通过，读数不可信：')
            for b in bad:
                print('  -', b)
            return 1
        print('[PASS] 自检：320 视口内的越界元素能被报出')

        src = '/site/index.html?mvw='
        write('_qa/mv_harness.html', harness_html(VIEWPORTS, src, 5000))
        rows = dump_dom(chrome, port, '_qa/mv_harness.html', vb=90000, win='2600,1100')
        if rows is None:
            print('RESULT: SKIP  探针无读数（重试后仍无输出）——不得引用历史读数充当当前结论')
            return 0

        issues = []
        no_data = 0
        print('%-10s %-8s %-6s %s' % ('视口', 'scrollW', '溢出', '越界元素'))
        print('-' * 68)
        for d in rows:
            if d.get('err') or 'scrollW' not in d:
                print('%-10s (无数据)' % ('%s' % d.get('vw')))
                no_data += 1
                continue
            w = d['vw']
            h = d.get('vh', 0)
            wide = '; '.join('%s(%d..%d)' % (x['cls'], x['left'], x['right'])
                             for x in d['wide'][:2])
            print('%-10s %-8s %-6s %s' % ('%dx%d' % (w, h), d['scrollW'],
                                           'YES' if d['overflow'] else 'no', wide or '-'))
            if d['overflow']:
                issues.append('%dx%d 横向溢出（scrollW %d）' % (w, h, d['scrollW']))
            if d['wide']:
                issues.append('%dx%d 越界: %s' % (w, h, wide))
            for c in d.get('clipped', []):
                issues.append('%dx%d 首屏被裁: %s (top %d, bottom %d)' % (
                    w, h, c['sel'], c['top'], c['bottom']))
            for c in d.get('covered', []):
                issues.append('%dx%d 首屏被导航遮挡: %s (top %d < nav %d)' % (
                    w, h, c['sel'], c['top'], c['navBottom']))

        print()
        if no_data == len(rows):
            print('RESULT: SKIP  全部视口无数据 —— 不计入 PASS（防止「没测到」被当「通过」）')
            return 0
        if issues:
            print('RESULT: FAIL  %d 项响应式问题（%d 个视口）' % (len(issues), len(rows)))
            for i in issues[:10]:
                print('  -', i)
            return 1
        print('RESULT: PASS  %d 个视口无横向溢出、无元素越界、首屏未被裁切/遮挡' % len(rows))
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == '__main__':
    sys.exit(main())
