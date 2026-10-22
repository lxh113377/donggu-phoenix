# -*- coding: utf-8 -*-
"""tools/admin_contrast_test.py —— 后台对比度判据（headless + pages dev，本地跑）。

## 为什么单独一条，而不是并进 contrast_audit
它测的是后台这一页，主站判据扫不到它（轮75 立的口径）。

## 2026-10-22 轮109 之后的实情（改这段话的原因）
后台已改为**静态演示页**：无登录、无接口（见 admin_static_data_test.py 的 D 条）。
所以本判据不再需要 wrangler pages dev + D1 —— 但它仍然照跑不误，因为：
  · 探针注入的 sessionStorage 密钥现在没人读，页面无条件进 dash 态；
  · zone 守卫因此变成「页面渲染到位」的断言，不再是「登录生效」的断言。
保留它的价值：4 视口逐元素 computed style 对比度，是 admin_static_render_test
（只看结构与墨迹）覆盖不到的一维。密钥读不到时它走 SKIP，不影响本地套件。
若日后后台恢复实时读，本判据的 zone 语义要一并改回。

## 轮75 的起因
后台此前零对比度覆盖（contrast_audit 只测 /site/index.html）。
首次实测就抓到 60 处不达标：--fg-faint 4.11（50 处，指标卡标签+全部表头）、
--red-hi 4.29（10 处，退出按钮+事件标签）。修完没有门禁守着就会再退化。

## 结构性盲区（必须写清，不能假装测全）
canvas 内绘制的文字（图表轴标签、刻度）getComputedStyle 读不到，
本判据与 contrast_audit 都覆盖不到。轮75 是靠 grep 硬编码色值人工发现的。
新增 canvas 绘制文字时，颜色必须与 CSS 令牌手工对齐。

## 密钥处理
从 .dev.vars 读，只经 URL hash 传给探针页，探针文件本体不含密钥；
页名匹配 .gitignore 的 site/_admin_probe*.html，不会被误提交；跑完即删。

## 守卫（沿用踩过的坑）
  · chrome 偶发 rc=0 但 stdout 空 -> 重试（U-193）
  · 零样本不判 PASS（轮9/15/22）
  · pages dev 起不来 -> SKIP 并说明，不判绿
  · zone != dash -> 判 FAIL（轮109 后＝静态数据未渲染，读数无意义）
"""
import json
import os
import random
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWPORTS = [(1440, 900), (390, 844)]
SEL = ('p,li,dd,dt,figcaption,blockquote,h1,h2,h3,h4,th,td,span,b,em,'
       'option,label,a,button')


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


def read_admin_key():
    p = os.path.join(BASE, '.dev.vars')
    if not os.path.exists(p):
        return None
    m = re.search(r'ADMIN_KEY\s*=\s*(\S+)',
                  open(p, encoding='utf-8', errors='ignore').read())
    return m.group(1) if m else None


KERNEL = r"""
function _cp(c){
  var m = (c||'').match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  var p = m[1].split(',').map(Number);
  return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
}
function _lm(rgb){
  function f(v){ v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); }
  return 0.2126*f(rgb[0])+0.7152*f(rgb[1])+0.0722*f(rgb[2]);
}
function _rt(a,b){ var L1=_lm(a),L2=_lm(b),hi=Math.max(L1,L2),lo=Math.min(L1,L2); return (hi+0.05)/(lo+0.05); }
function audit(doc, win, SEL){
  var bad = [], checked = 0, skipG = 0, skipT = 0;
  [].slice.call(doc.querySelectorAll(SEL)).forEach(function(e){
    if (!e.offsetParent) return;
    if (e.closest && e.closest('[data-decorative]')) return;
    var txt = [].slice.call(e.childNodes)
      .filter(function(n){ return n.nodeType === 3 && n.textContent.trim(); })
      .map(function(n){ return n.textContent.trim(); }).join('');
    if (!txt) return;
    var cs = win.getComputedStyle(e);
    var clip = cs.webkitBackgroundClip || cs.backgroundClip || '';
    if (clip === 'text') { skipG++; return; }
    var fg = _cp(cs.color);
    if (!fg || fg[3] < 0.05) { skipT++; return; }
    var bg = null, el = e;
    while (el) {
      var s = win.getComputedStyle(el);
      if (s.backgroundImage && s.backgroundImage.indexOf('gradient') >= 0) { bg = [20,17,16,1]; break; }
      var c = _cp(s.backgroundColor);
      if (c && c[3] > 0.9) { bg = c; break; }
      el = el.parentElement;
    }
    if (!bg) bg = [20,17,16,1];
    var comp = [fg[0]*fg[3]+bg[0]*(1-fg[3]), fg[1]*fg[3]+bg[1]*(1-fg[3]), fg[2]*fg[3]+bg[2]*(1-fg[3])];
    var r = _rt(comp, bg);
    var fs = parseFloat(cs.fontSize);
    var bold = parseInt(cs.fontWeight, 10) >= 700;
    var need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
    checked++;
    if (r < need) {
      bad.push({txt: txt.slice(0, 18), ratio: Math.round(r*100)/100, need: need,
                fs: fs, color: cs.color});
    }
  });
  return {checked: checked, bad: bad, skipG: skipG, skipT: skipT};
}
"""


PROBE = r"""<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0;background:#111}iframe{border:0;display:block}</style>
</head><body><div id="h"></div>
<script>
var KEY = decodeURIComponent((location.hash || '').slice(1));
var VPS = __VPS__;
try { sessionStorage.setItem('__KEYSTORE__', KEY); }
catch (e) { document.title = JSON.stringify({err: 'storage: ' + e}); }
var host = document.getElementById('h');
var frames = [];
VPS.forEach(function (v, i) {
  var f = document.createElement('iframe');
  f.id = 'f' + i;
  f.src = '/admin/?c=' + v[0] + '_' + Date.now();
  f.style.width = v[0] + 'px';
  f.style.height = v[1] + 'px';
  host.appendChild(f);
  frames.push(f);
});
__KERNEL__
setTimeout(function(){
  try{
    var res = [];
    for (var i=0;i<frames.length;i++){
      var d = frames[i].contentDocument, w = frames[i].contentWindow;
      if (!d || !w){ res.push({vw: VPS[i][0], err:'no doc'}); continue; }
      var a = audit(d, w, '__SEL__');
      a.vw = w.innerWidth;
      var z = ['login','noapi','dash'], zone = 'none';
      for (var k=0;k<z.length;k++){
        var e2 = d.getElementById(z[k]);
        if (e2 && e2.classList.contains('on')) zone = z[k];
      }
      a.zone = zone;
      res.push(a);
    }
    document.title = JSON.stringify(res);
  }catch(e){ document.title = JSON.stringify({err:String(e)}); }
}, 9000);
</script></body></html>"""


def probe_html():
    """占位符替换必须作用在拼接后的完整串上（U-188 同课，已第 5 次）。"""
    html = PROBE
    html = html.replace('__VPS__', json.dumps(VIEWPORTS))
    html = html.replace('__KERNEL__', KERNEL)
    html = html.replace('__SEL__', SEL)
    html = html.replace('__KEYSTORE__', 'dg-admin-key')
    return html


def free_port():
    s = socketserver.TCPServer(('127.0.0.1', 0), None)
    p = s.server_address[1]
    s.server_close()
    return p


def start_pages_dev(port):
    """起 wrangler pages dev（Functions + 本地 D1）。返回 Popen 或 None。"""
    import urllib.request
    logp = os.path.join(BASE, '_qa', 'pages_dev_contrast.log')
    os.makedirs(os.path.dirname(logp), exist_ok=True)
    log = open(logp, 'w', encoding='utf-8', errors='replace')
    try:
        proc = subprocess.Popen(['npx', 'wrangler', 'pages', 'dev', 'site',
                                 '--port', str(port), '--local'],
                                cwd=BASE, stdout=log, stderr=subprocess.STDOUT,
                                shell=(os.name == 'nt'))
    except Exception:
        return None
    for _ in range(45):
        time.sleep(1.5)
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/admin/' % port,
                                   timeout=5).read()
            return proc
        except Exception:
            if proc.poll() is not None:
                return None
    return proc


def dump_dom(chrome, url, vb=30000, win='1500,1100', attempts=5):
    """chrome 偶发 rc=0 但 stdout 空（U-193），必须重试；仍空返回 None。"""
    for _ in range(attempts):
        udd = os.path.join(tempfile.gettempdir(), 'chr_act_%d' % random.randint(0, 10**6))
        cmd = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
               '--force-device-scale-factor=1', '--window-size=' + win,
               '--user-data-dir=' + udd, '--virtual-time-budget=%d' % vb,
               '--dump-dom', url]
        dom = ''
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=140)
            dom = r.stdout or ''
        except subprocess.TimeoutExpired:
            dom = ''
        finally:
            shutil.rmtree(udd, ignore_errors=True)
        m = re.search(r'<title>(.*?)</title>', dom, re.S)
        raw = (m.group(1) if m else '') or ''
        if raw and raw != 'pending':
            try:
                return json.loads(raw)
            except Exception:
                pass
        time.sleep(1.5)
    return None


def main():
    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe')
        return 0
    # 轮125：后台已静态化（轮109），不再需要 wrangler pages dev + D1。
    # 改用进程内 SiteServer —— 与 CI 同一条路，零 npx、零 D1、零公网。
    # 密钥也不再必需：后台无登录，探针注入的 KEY 已无人读，仅作 hash 占位。
    key = read_admin_key() or ''
    port = free_port()
    print('起进程内静态服务于端口 %d（无需 wrangler/D1）...' % port)
    proc = None
    _srv = None
    try:
        from cdp_client import SiteServer
        _srv = SiteServer(os.path.join(BASE, 'site'), port=port)
    except Exception as _e:
        print('RESULT: SKIP  静态服务起不来: %s —— 未测不等于通过' % _e)
        return 0
    try:
        dst = os.path.join(BASE, 'site', '_admin_probe_contrast.html')
        html = probe_html()
        assert key not in html, '探针本体不得含密钥'
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'w', encoding='utf-8').write(html)
        try:
            rows = dump_dom(chrome, 'http://127.0.0.1:%d/_admin_probe_contrast.html#%s'
                            % (port, key))
        finally:
            try:
                os.remove(dst)
            except Exception:
                pass
        if rows is None:
            print('RESULT: SKIP  无读数（重试 5 次仍空）—— 未测不等于通过')
            return 0
        if isinstance(rows, dict):
            print('RESULT: FAIL  探针错误：%s' % rows.get('err'))
            return 1

        fails = []
        total_checked = 0
        for a in rows:
            if a.get('err'):
                fails.append('vw=%s 无文档' % a.get('vw'))
                continue
            total_checked += a['checked']
            print('  vw=%-5s zone=%-5s 检查 %d 处，不达标 %d（跳渐变%d/透明%d）' % (
                a['vw'], a['zone'], a['checked'], len(a['bad']),
                a['skipG'], a['skipT']))
            for b in a['bad'][:6]:
                print('      - %-18s %.2f < %.1f  %spx  %s' % (
                    b['txt'], b['ratio'], b['need'], b['fs'], b['color']))
            if a['zone'] != 'dash':
                fails.append('vw=%s 未进 dash（zone=%s），静态数据未渲染，读数无意义'
                             % (a['vw'], a['zone']))
            elif a['bad']:
                fails.append('vw=%d：%d 处文本对比度不达 AA' % (a['vw'], len(a['bad'])))

        print()
        if total_checked == 0:
            print('RESULT: SKIP  未检查到任何文本 —— 不计入 PASS')
            return 0
        if fails:
            print('RESULT: FAIL  后台对比度（AA：正文 4.5 / 大字 3.0）')
            for f in fails[:8]:
                print('  -', f)
            return 1
        print('RESULT: PASS  后台 %d 视口共 %d 处文本对比度全部达标'
              % (len(rows), total_checked))
        print('  注意：canvas 内绘制文字（图表轴标签/刻度）本判据测不到，'
              '需与 CSS 令牌手工对齐')
        return 0
    finally:
        # 轮125：proc 已改 SiteServer，关服务不再 kill 子进程
        try:
            if _srv is not None:
                _srv.stop()
        except Exception:
            pass


if __name__ == '__main__':
    # 自写时效戳（轮70 机制）：直跑也要留痕，否则 --status 会报「从未跑过」
    sys.path.insert(0, BASE)
    from tools.gate_stamp import record
    _t0 = time.time()
    _rc = main()
    record(__file__, {0: 'PASS', 1: 'FAIL'}.get(_rc, 'SKIP'), time.time() - _t0)
    sys.exit(_rc)
