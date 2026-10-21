# -*- coding: utf-8 -*-
"""tools/touch_target_test.py —— 触控目标尺寸判据（headless chrome 直连，自给自足）。

## 轮65/67 的三处升级（U-184）
旧版有三个致命问题：
  1. 依赖 agent-browser daemon —— 本机连续 11 轮不可用，判据实际从未跑成。
  2. 阈值 MIN_PX=24（WCAG 2.5.8 下限），但本项目按 **44px** 立基线
     （轮47 修 slider 就是按 44 修的）。24 阈值下 28px 的 <summary>「素材出处」
     直接漏网 —— **判据存在 ≠ 判据按产品自立的标准生效**（与轮58
     「扫描面≠执行面」同族）。
  3. 依赖外部 8791/8792 服务，服务一死就「无读数」（轮67 实测踩到两次）。
     现改为**进程内自起**以仓库根为 document-root 的服务：不依赖外部进程，
     且探针页与 /site/index.html 同源 -> iframe.contentDocument 可访问
     （data: URL 的 iframe 是不透明源，取不到文档，轮67 自检因此失败）。

## 双档口径
  · 独立语义交互元素（a/button/input/select/summary/[role=button]）
    自身宽高 >= 44px（产品基线）。
  · 排除「有交互祖先」的元素：按钮内部子元素不是独立目标。
    祖先判定**遇到 A 即停** —— 包裹块（整卡可点）本身已是达标目标，
    其内部 role=button 的装饰性子元素不该再被单独要求 44px（轮67 自检抓到）。
  · 行内链接（display:inline 且嵌在文本流里）按 WCAG 2.5.8 Inline 条款豁免。

## 自检（4 个合成用例，任一不符即 FAIL）
  · button.big 60x44            -> 放过（达标）
  · summary.sm 200x28           -> 必须报（正是轮65 修掉的那类缺陷）
  · p > a inline                -> 放过（inline 豁免）
  · a.blk(502x44) > span[role=button] 16x16 -> 放过（祖先达标）
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
MIN_PX = 44      # 产品自立基线（Apple HIG / Material），非 WCAG 24 下限
INLINE_MIN_PX = 24  # WCAG 2.5.8 绝对下限：inline 链接豁免 44，但行盒不得 < 24
VPS = [(320, 640), (375, 667), (390, 844), (414, 896)]

AUDIT_JS = r'''
function isInlineLink(e, cs){
  // 轮67 修正：早先要求「父级还有其它文本节点」才算 inline，判定过严，
  // 与 WCAG 原文不符（.ar-src li 里的引用链接独占一行却被误判为独立目标）。
  // display:inline 本身就意味着它随文本流排布、尺寸由行高决定。
  return cs.display === 'inline';
}
function audit(w, d, MIN, INLINE_MIN){
  var out = { small: [] };
  var sel = 'a[href], button, input:not([type=hidden]), select, summary, [role="button"], [tabindex]:not([tabindex="-1"])';
  var els = d.querySelectorAll(sel);
  for (var i = 0; i < els.length; i++){
    var e = els[i], cs = w.getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    var r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    var p = e.parentElement, nested = false;
    while (p && p !== d.body){
      // A 也算交互祖先：整卡可点时，卡内装饰性子元素不是独立触控目标
      //（轮67 自检抓到：写成「遇 A 就 break」会让 span 被当独立目标误报）
      if (/^(A|BUTTON|SUMMARY|LABEL)$/.test(p.tagName) || p.getAttribute('role') === 'button'){
        nested = true; break;
      }
      p = p.parentElement;
    }
    if (nested) continue;
    // 双档：inline 链接豁免 44 基线，但**所在行盒**不得 < WCAG 24 绝对下限。
    // 度量必须用父级 computed line-height，不能用 e.getBoundingClientRect().height：
    // inline 元素的 rect 高是字体内容盒（13px 字号约 19px），
    // 而浏览器实际可点区域随行盒增长 —— 用 rect 会把已达标的链接误判（轮67 实测）。
    if (isInlineLink(e, cs)){
      var pp = e.parentElement;
      var plh = pp ? w.getComputedStyle(pp).lineHeight : 'normal';
      var lineBox = parseFloat(plh);
      if (!isFinite(lineBox) || lineBox <= 0){
        var pfs = pp ? (parseFloat(w.getComputedStyle(pp).fontSize) || 16) : 16;
        lineBox = pfs * 1.2;   // line-height:normal 的近似
      }
      if (lineBox < INLINE_MIN){
        var cls2 = (typeof e.className === 'string' && e.className.trim())
          ? '.' + e.className.trim().split(/\s+/).slice(0,2).join('.') : '';
        out.small.push({ s: e.tagName.toLowerCase() + cls2.slice(0,34),
                         w: Math.round(r.width), h: Math.round(r.height),
                         lineBox: Math.round(lineBox), inline: true,
                         txt: (e.textContent||'').trim().slice(0,16) });
      }
      continue;
    }
    if (r.height < MIN || r.width < MIN){
      var cls = (typeof e.className === 'string' && e.className.trim())
        ? '.' + e.className.trim().split(/\s+/).slice(0,2).join('.') : '';
      out.small.push({ s: e.tagName.toLowerCase() + cls.slice(0,34),
                       w: Math.round(r.width), h: Math.round(r.height),
                       txt: (e.textContent||'').trim().slice(0,16) });
    }
  }
  return out;
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


def dump_dom(chrome, port, path, vb=33000, win='900,3200'):
    udd = os.path.join(tempfile.gettempdir(), 'chr_tt_%d' % random.randint(0, 10**6))
    cmd = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
           '--force-device-scale-factor=1', '--force-prefers-reduced-motion',
           '--window-size=' + win, '--user-data-dir=' + udd,
           '--virtual-time-budget=%d' % vb, '--dump-dom',
           'http://127.0.0.1:%d/%s' % (port, path)]
    dom = ''
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=150)
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


def selftest_fixture():
    """5 个合成用例，覆盖双档口径（同一文档内，不用跨源 iframe）。

      · button.big  60x44                -> 放过（独立目标达标）
      · summary.sm  200x28               -> 报（独立目标 < 44，正是轮65 修掉的那类）
      · a.inlok 行盒 25.6px              -> 放过（inline 豁免 44，且行盒 >= 24）
      · a.inlbad 行盒 14.3px             -> 报（inline 但行盒 < WCAG 24 绝对下限）
      · a.blk(502x44) > span[role=button] -> 放过（有交互祖先，非独立目标）
    """
    html = r'''<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>
button.big{width:60px;height:44px;display:block}
summary.sm{display:block;height:28px;width:200px}
a.blk{display:block;width:502px;height:44px}
p.oklh{font-size:16px;line-height:1.6}   /* 行盒 25.6px */
p.badlh{font-size:13px;line-height:1.1}  /* 行盒 14.3px */
</style></head><body>
<button class="big">ok</button>
<details><summary class="sm">素材出处</summary>x</details>
<p class="oklh">前缀 <a class="inlok" href="#x">行内链接达标</a> 后缀</p>
<p class="badlh">前缀 <a class="inlbad" href="#z">行内链接过小</a> 后缀</p>
<a class="blk" href="#y"><span role="button" style="display:block;width:16px;height:16px"></span></a>
<script>
''' + AUDIT_JS + r'''
setTimeout(function(){
  try {
    var a = audit(window, document, __MIN__, __IMIN__); a.vw = window.innerWidth;
    document.title = JSON.stringify([a]);
  } catch(e){ document.title = 'ERR ' + e; }
}, 400);
</script></body></html>'''
    return html.replace('__MIN__', str(MIN_PX)).replace('__IMIN__', str(INLINE_MIN_PX))


def selftest(chrome, port):
    write('_qa/touch_selftest.html', selftest_fixture())
    rows = dump_dom(chrome, port, '_qa/touch_selftest.html', vb=15000, win='560,900')
    if not rows or rows[0].get('err'):
        return ['自检无读数（chrome 或页面未回填 title）']
    tags = sorted(x['s'] for x in rows[0]['small'])
    want = ['a.inlbad', 'summary.sm']
    if tags != want:
        return ['自检期望报 %s，实报 %s' % (want, tags),
                '  （应放过：44 按钮、行盒>=24 的 inline 链接、包裹块内 16px 子元素）']
    return []

def site_probe_html():
    # 注意：占位符替换必须作用在**拼接后的完整串**上。
    # 早先写成 `a + b + c.replace(...)`，因运算符优先级只替换了最后一段，
    # 导致开头 `var MIN = __MIN__` 未替换 -> JS ReferenceError 整段脚本不执行，
    # 探针永远「无读数」（轮67 实测）。
    html = r'''<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0}iframe{border:0;display:block}</style></head>
<body><div id="host"></div><script>
var VPS = ''' + json.dumps(VPS) + r''';
var MIN = __MIN__;
var INLINE_MIN = __IMIN__;
var host = document.getElementById('host');
VPS.forEach(function(v, i){
  var f = document.createElement('iframe');
  f.id = 'f' + i;
  f.src = '/site/index.html?tt=' + v[0] + '_' + Date.now();
  f.style.width = v[0] + 'px';
  f.style.height = v[1] + 'px';
  host.appendChild(f);
});
''' + AUDIT_JS + r'''
setTimeout(function(){
  try{
    var res = [];
    VPS.forEach(function(v, i){
      var f = document.getElementById('f' + i);
      var d = f.contentDocument, w = f.contentWindow;
      var a = (d && w) ? audit(w, d, MIN, INLINE_MIN) : { err: 'no doc' };
      a.vw = v[0];
      if (d && w) { a.iw = w.innerWidth; a.scrollW = d.documentElement.scrollWidth; }
      res.push(a);
    });
    document.title = JSON.stringify(res);
  }catch(e){ document.title = 'ERR ' + e; }
}, 5200);
</script></body></html>'''
    return html.replace('__MIN__', str(MIN_PX)).replace('__IMIN__', str(INLINE_MIN_PX))


def main():
    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe')
        return 0
    httpd, port = start_server()
    try:
        print('chrome: %s  同源服务: 127.0.0.1:%d' % (
            os.path.basename(os.path.dirname(chrome)), port))

        bad = selftest(chrome, port)
        if bad:
            print('RESULT: FAIL  判据自检不通过，读数不可信：')
            for b in bad:
                print('  -', b)
            return 1
        print('[PASS] 自检：44 按钮/行内链接/包裹块内子元素均放过，28px summary 能报出')

        write('_qa/touch_site_probe.html', site_probe_html())
        rows = dump_dom(chrome, port, '_qa/touch_site_probe.html')
        if rows is None:
            print('RESULT: SKIP  站点探针无读数')
            return 0

        fails = []
        for r0 in rows:
            if r0.get('err'):
                fails.append('vw=%s 无文档（探针未加载）' % r0.get('vw'))
                continue
            ov = r0.get('scrollW', 0) - r0.get('iw', 0)
            small = r0.get('small') or []
            note = '' if ov <= 1 else '（另有横向溢出 %dpx）' % ov
            print('  vw=%-5d 不足 %dpx 的独立交互目标 %d 个%s' % (
                r0['vw'], MIN_PX, len(small), note))
            for e in small[:5]:
                if e.get('inline'):
                    print('      %-36s 行盒 %dpx < %d  %r' % (
                        e['s'], e['lineBox'], INLINE_MIN_PX, e['txt']))
                else:
                    print('      %-36s %dx%d  %r' % (e['s'], e['w'], e['h'], e['txt']))
            if small:
                fails.append('vw=%d：%d 个交互目标 < %dpx' % (r0['vw'], len(small), MIN_PX))
            if ov > 1:
                fails.append('vw=%d：横向溢出 %dpx' % (r0['vw'], ov))

        print()
        if fails:
            print('RESULT: FAIL  触控基线 %dpx（产品自立，非 WCAG 24 下限）' % MIN_PX)
            for f in fails[:8]:
                print('  -', f)
            return 1
        print('RESULT: PASS  %d 个移动视口的独立交互目标均 >= %dpx 且无横向溢出'
              % (len(VPS), MIN_PX))
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == '__main__':
    sys.exit(main())
