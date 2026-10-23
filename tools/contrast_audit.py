# -*- coding: utf-8 -*-
"""tools/contrast_audit.py —— 对比度审计（headless chrome 直连，自给自足）。

## 三轮失败换来的测量内核（轮25，保留不动）

**尝试 1：CSS 解析（backgroundColor 向上找）**
· 主 CTA 按钮算出 1.05:1 —— 荒谬。原因：按钮背景是 linear-gradient，
  backgroundColor 是 transparent，解析器一路找到页面深色底，
  于是「深字 + 深底」= 1.05。正确应为 9.06:1（像素实测）。
**尝试 2：像素采样（极值当前景/背景）**
· 报 53 项不达标 —— 取「最亮/最暗 10%」被抗锯齿边缘、卡片边框、装饰线干扰。
**尝试 3：像素采样（固定坐标区域）**
· 采到的可能是空白处。

**最终可靠做法：直接用浏览器计算色**
  getComputedStyle(el).color        → 前景（含 alpha）
  向上遍历祖先 backgroundColor      → 找第一个 alpha>0.9 的实色背景
  前景按 alpha 与背景合成后算 WCAG 对比度
  渐变文字（background-clip:text）跳过并计数 —— 否则算成 1.00 误报。

## 轮68 的传输层升级
旧版靠 agent-browser daemon —— 本机连续 11 轮不可用，判据**从没产出过读数**
（与轮67 触控判据同病：一个从没成功运行过的判据，等于没有判据）。
现改为 chrome headless 直连 + **进程内自起同源服务**：
  · 不依赖外部 8791/8792 与 daemon
  · iframe 与 /site/index.html 同源，可读 contentDocument
  · 一次跑完 1440 桌面 + 390 移动两个视口

## 保留的两道守卫（都是踩过的坑）
  · 零样本不判 PASS：checked==0 判 SKIP（轮9/15/22 三次零样本假绿）
  · 缓存版本守卫：磁盘 --build 与页面实际读到的不等 -> 判 SKIP 不出结论
    （轮30/34 SW 缓存假绿）

## 自检（轮68 新增，证明内核有牙）
合成两个元素：深灰字 on 深黑底（必须报）、米白字 on 深黑底（必须放过）。
内核若测不出前者，说明它已经哑了 —— 读数不可信，直接 FAIL。
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

# ---- 测量内核（轮25 定稿，勿改判据口径）----
KERNEL = r'''
function _cparse(c){
  var m = (c||'').match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  var p = m[1].split(',').map(Number);
  return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
}
function _lum(rgb){
  function f(v){ v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); }
  return 0.2126*f(rgb[0])+0.7152*f(rgb[1])+0.0722*f(rgb[2]);
}
function _ratio(a,b){
  var L1=_lum(a), L2=_lum(b), hi=Math.max(L1,L2), lo=Math.min(L1,L2);
  return (hi+0.05)/(lo+0.05);
}
function contrastAudit(doc, win, SEL){
  var bad = [], checked = 0, skippedGradient = 0, skippedTransparent = 0;
  var panelChecked = 0;   // 落在展开的 AR 面板内且被测量的元素数
  [].slice.call(doc.querySelectorAll(SEL)).forEach(function(e){
    if (!e.offsetParent) return;
    if (e.closest && e.closest('[data-decorative]')) return;
    var txt = [].slice.call(e.childNodes)
      .filter(function(n){ return n.nodeType === 3 && n.textContent.trim(); })
      .map(function(n){ return n.textContent.trim(); }).join('');
    if (!txt) return;
    var cs = win.getComputedStyle(e);
    var clip = cs.webkitBackgroundClip || cs.backgroundClip || '';
    if (clip === 'text') { skippedGradient++; return; }
    var fg = _cparse(cs.color);
    if (!fg || fg[3] < 0.05) { skippedTransparent++; return; }
    var bg = null, el = e;
    while (el) {
      var s = win.getComputedStyle(el);
      if (s.backgroundImage && s.backgroundImage.indexOf('gradient') >= 0) { bg = [11,9,8,1]; break; }
      var c = _cparse(s.backgroundColor);
      if (c && c[3] > 0.9) { bg = c; break; }
      el = el.parentElement;
    }
    if (!bg) bg = [11,9,8,1];
    var comp = [fg[0]*fg[3]+bg[0]*(1-fg[3]),
                fg[1]*fg[3]+bg[1]*(1-fg[3]),
                fg[2]*fg[3]+bg[2]*(1-fg[3])];
    var r = _ratio(comp, bg);
    var fs = parseFloat(cs.fontSize);
    var bold = parseInt(cs.fontWeight, 10) >= 700;
    var need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
    checked++;
    if (e.closest && e.closest('#ar.on')) panelChecked++;
    if (r < need) {
      bad.push({ txt: txt.slice(0, 20), ratio: Math.round(r*100)/100, need: need,
                 fs: fs, color: cs.color, bg: 'rgb(' + bg.slice(0,3).join(',') + ')' });
    }
  });
  return { checked: checked, bad: bad, skippedGradient: skippedGradient,
           skippedTransparent: skippedTransparent, panelChecked: panelChecked };
}
'''

SEL = 'p,li,dd,figcaption,blockquote,h1,h2,h3,h4'
VIEWPORTS = [(1440, 900), (390, 844)]


def find_chrome():
    r"""找 chrome 可执行文件。

    轮124：原实现只查 Windows 路径（chrome.exe / C:\Program Files\...），
    在 CI 的 Linux 上必返回 None -> 判据打印「找不到 chrome.exe」并 SKIP，
    等于该维度没有 CI 守护（实测 CI 日志里确实 SKIP）。
    改为复用 cdp_client.find_chrome（已跨平台：Win 用 where、Linux 用 which，
    且含 chromium 回退）。
    """
    try:
        from cdp_client import find_chrome as _fc
        p = _fc()
        if p:
            return p
    except Exception:
        pass
    # 兜底：仍保留非 Windows 绝对路径尝试
    for p in ('/usr/bin/chromium', '/usr/bin/google-chrome',
                  '/opt/google/chrome/chrome'):
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


_VERBOSE = bool(os.environ.get('CA_DEBUG'))


def dump_dom(chrome, port, path, vb, win, attempts=3):
    """取一次页面渲染后的 title JSON。

    轮68 实测：chrome 在本机偶发「rc=0 但 stdout 为空」（同参数时而 0 时而 2KB，
    与参数无关，是并发/profile 争用）。因此必须重试；
    重试仍空则返回 None，由调用方判「不可用」——**不可用不等于通过**。
    """
    last = None
    for i in range(max(1, attempts)):
        last = _dump_dom_once(chrome, port, path, vb, win)
        if last is not None:
            return last
        if i + 1 < attempts:
            time.sleep(1.5)
    return None


def _dump_dom_once(chrome, port, path, vb, win):
    udd = os.path.join(tempfile.gettempdir(), 'chr_ca_%d' % random.randint(0, 10**6))
    cmd = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
           '--force-device-scale-factor=1', '--window-size=' + win,
           '--user-data-dir=' + udd, '--virtual-time-budget=%d' % vb,
           '--dump-dom', 'http://127.0.0.1:%d/%s' % (port, path)]
    dom = ''
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=150)
        dom = r.stdout or ''
        if _VERBOSE:
            print('  [dbg] %s rc=%s domlen=%d' % (path, r.returncode, len(dom)))
    except subprocess.TimeoutExpired:
        if _VERBOSE:
            print('  [dbg] %s TIMEOUT' % path)
        return None
    finally:
        shutil.rmtree(udd, ignore_errors=True)
    m = re.search(r'<title>(.*?)</title>', dom, re.S)
    raw = (m.group(1) if m else '') or ''
    if _VERBOSE:
        print('  [dbg] title=%r' % raw[:120])
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


def selftest_html():
    """深灰字 on 黑底必须被报；米白字 on 黑底必须放过。"""
    return r'''<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>
body{background:#0B0908;margin:0}
p.dim{color:#2A2624}
p.ok{color:#F4EDE1}
p.grad{background:linear-gradient(180deg,#fff,#888);-webkit-background-clip:text;color:transparent}
</style></head><body>
<p class="dim">暗到不可读的正文样本</p>
<p class="ok">正常可读的正文样本</p>
<p class="grad">渐变裁切文字样本</p>
<script>
''' + KERNEL + r'''
setTimeout(function(){
  try {
    var r = contrastAudit(document, window, "p");
    document.title = JSON.stringify(r);
  } catch(e){ document.title = 'ERR ' + e; }
}, 300);
</script></body></html>'''


def selftest(chrome, port):
    write('_qa/contrast_selftest.html', selftest_html())
    d = None
    for _attempt in range(3):
        d = _dump_dom_once(chrome, port, '_qa/contrast_selftest.html', vb=12000, win='560,400')
        if d:
            break
        time.sleep(1.5)
    if not d:
        return ['自检无读数（重试 3 次仍无输出）——判据不可用，不等于通过']
    bad_txts = [b['txt'] for b in d.get('bad', [])]
    problems = []
    if d.get('checked', 0) < 2:
        problems.append('自检只检查了 %s 处（应含暗样本与正常样本）' % d.get('checked'))
    if '暗到不可读的正文样本' not in bad_txts:
        problems.append('暗字样本未被报出 —— 内核已哑，读数不可信')
    if any('正常可读' in t for t in bad_txts):
        problems.append('正常样本被误报 —— 内核过度报警')
    if d.get('skippedGradient', 0) < 1:
        problems.append('渐变裁切文字未被跳过，会误算成 1.00')
    return problems


def site_probe_html():
    vps = json.dumps(VIEWPORTS)
    return r'''<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0}iframe{border:0;display:block}</style></head>
<body><div id="host"></div><script>
var VPS = ''' + vps + r''';
var host = document.getElementById('host');
VPS.forEach(function(v, i){
  var f = document.createElement('iframe');
  f.id = 'f' + i;
  f.src = '/site/index.html?ca=' + v[0] + '_' + Date.now();
  f.style.width = v[0] + 'px';
  f.style.height = v[1] + 'px';
  host.appendChild(f);
});
''' + KERNEL + r'''
function openArPanel(w, d){
  // 展开 AR 面板并 seek 到有章节文字处，让面板内文字进入可测态。
  var ar = d.getElementById('ar');
  if (!ar) return 'noar';
  if (w.__ar && w.__ar.open){
    try{
      var sc = w.__ar.scenes;
      if (sc && sc.length){
        w.__ar.open(sc[0].id);
        try{ w.__ar.seek(Math.floor(sc[0].duration * 0.4)); }catch(e){}
        return 'ok';
      }
    }catch(e){ return 'err'; }
  }
  var b = d.querySelector('.ar-card .go');
  if (b){ b.click(); return 'click'; }
  return 'nobtn';
}
function scrollAll(w, d, done){
  var y = 0, max = d.body.scrollHeight;
  (function step(){
    if (y > max) { w.scrollTo(0, 0); setTimeout(done, 400); return; }
    w.scrollTo(0, y);
    y += 700;
    setTimeout(step, 40);
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
        var opened = openArPanel(w, d);
        setTimeout(function(){
          var r = contrastAudit(d, w, "''' + SEL + r'''");
          r.vw = v[0];
          r.arOpened = opened;
          r.iw = w.innerWidth;
          r.build = getComputedStyle(d.documentElement).getPropertyValue('--build').trim();
          res.push(r);
          if (--pending === 0) finish();
        }, 700);
      });
    });
    function finish(){
      res.sort(function(a,b){ return b.vw - a.vw; });
      document.title = JSON.stringify(res);
    }
  }catch(e){ document.title = 'ERR ' + e; }
}, 4200);
</script></body></html>'''


def main():
    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe')
        return 0
    css_path = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
    declared = ''
    try:
        m = re.search(r'--build:(\d+);', open(css_path, encoding='utf-8').read())
        declared = m.group(1) if m else ''
    except Exception:
        pass

    httpd, port = start_server()
    try:
        print('chrome: %s  同源服务: 127.0.0.1:%d' % (
            os.path.basename(os.path.dirname(chrome)), port))

        bad_self = selftest(chrome, port)
        if bad_self:
            print('RESULT: FAIL  判据自检不通过，读数不可信：')
            for b in bad_self:
                print('  -', b)
            return 1
        print('[PASS] 自检：暗字样本能报出、正常样本放过、渐变裁切文字正确跳过')

        write('_qa/contrast_site_probe.html', site_probe_html())
        rows = dump_dom(chrome, port, '_qa/contrast_site_probe.html',
                        vb=60000, win='1500,1000')
        if rows is None:
            print('RESULT: SKIP  未取到对比度读数（chrome 或探针未回填）')
            return 0

        # 缓存版本守卫（保留轮30/34 的教训）
        if declared:
            for r0 in rows:
                lb = str(r0.get('build') or '')
                if lb and lb.isdigit() and lb != declared:
                    print('RESULT: SKIP  CSS 版本不一致（磁盘 %s / 浏览器 %s）'
                          '——疑似缓存污染，不输出结论' % (declared, lb))
                    return 0

        fails = []
        total_checked = 0
        for r0 in rows:
            if r0.get('err'):
                fails.append('vw=%s 无文档（探针未加载）' % r0.get('vw'))
                continue
            checked = r0.get('checked', 0)
            # AR 面板展开态：测不到就必须报，不能静默通过（轮178）
            ao = r0.get('arOpened')
            pc = r0.get('panelChecked') or 0
            if ao not in ('ok', 'click'):
                fails.append('vw=%s：AR 面板未展开（arOpened=%s），'
                             '面板内文字未被测量' % (r0.get('vw'), ao))
            elif pc < 3:
                fails.append('vw=%s：面板展开但只测到 %d 项面板内文字（<3），'
                             '测量面不足' % (r0.get('vw'), pc))
            bad = r0.get('bad', [])
            total_checked += checked
            print('  vw=%-5d 检查 %d 处文本，不达标 %d 处'
                  '（跳过渐变 %d / 透明 %d / AR 面板内 %d 项）' % (
                      r0['vw'], checked, len(bad),
                      r0.get('skippedGradient', 0),
                      r0.get('skippedTransparent', 0),
                      r0.get('panelChecked', 0)))
            for b in bad[:8]:
                print('      - %s  对比 %.2f < %.1f  (%.0fpx)  fg=%s bg=%s' % (
                    b['txt'], b['ratio'], b['need'], b['fs'], b['color'], b['bg']))
            if checked == 0:
                fails.append('vw=%s 零样本（解析失效，不算通过）' % r0['vw'])
            elif bad:
                fails.append('vw=%d：%d 处文本对比度不达标' % (r0['vw'], len(bad)))

        print()
        if total_checked == 0:
            print('RESULT: SKIP  未检查到任何文本 —— 不计入 PASS（防止「没测到」被当「通过」）')
            return 0
        if fails:
            print('RESULT: FAIL  WCAG 对比度（正文 4.5 / 大字 3.0）')
            for f in fails[:8]:
                print('  -', f)
            return 1
        print('RESULT: PASS  %d 视口共 %d 处文本全部达标' % (len(rows), total_checked))
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == '__main__':
    # 自写时效戳（轮71）：直接跑本判据也要留下「最后一次真跑」记录，
    # 否则 run_browser_suite --status 会把今天跑过的判据报成「从未跑过」，
    # 一个给出误导读数的时效机制比没有更糟。
    sys.path.insert(0, BASE)
    from tools.gate_stamp import record
    _t0 = time.time()
    _rc = main()
    record(__file__, {0: 'PASS', 1: 'FAIL'}.get(_rc, 'SKIP'), time.time() - _t0)
    sys.exit(_rc)
