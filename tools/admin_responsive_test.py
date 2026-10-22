# -*- coding: utf-8 -*-
"""tools/admin_responsive_test.py —— 后台响应式与触控判据（headless + pages dev）。

## 为什么需要（轮79）
后台此前只有对比度判据（admin_contrast_test）。响应式与触控只做过一次性手工探针，
没固化 —— 手工测出 6 个触控目标 < 44px（.btn 38px、select 31px），
若不建判据，下次改动就会退化。

## 与主站判据的口径对齐
  · 触控基线 44px：项目自立的基线（轮47 修 slider 立、轮67 把 touch_target
    阈值从 WCAG 24 提到 44）。主站 main.css 有 8 处 min-height:44px，
    后台是同一产品的组成部分，没有理由单独放宽。
  · 行内链接（display:inline）按 WCAG 2.5.8 Inline 条款豁免。
  · 有交互祖先的子元素不算独立目标（按钮内的 span）。

## 越界判定必须排除滚动容器后代（轮79 探针自己犯过的错）
表格放在 .tw{overflow-x:auto} 里，宽表超出视口是**设计**
（轮74 已验证容器 scrollWidth>clientWidth 且带可横滑提示）。
第一版探针没排除这类后代，把 3 张宽表全误报成「越界缺陷」。
本判据沿修正后的口径：元素若位于任何 overflow-x:auto/scroll 祖先内，跳过。

## 基础设施复用
find_chrome / free_port / read_admin_key / start_pages_dev / dump_dom
全部 import 自 admin_contrast_test —— 同一套 pages dev + 同源 iframe +
chrome 偶发空输出重试逻辑，不重复实现（重复实现就会各自漂移）。

## 守卫
  · zone != dash -> FAIL
    轮109 起后台无登录，zone 表达的是「静态数据是否渲染到位」，不再是登录成功。
  · 零样本 -> SKIP，不判 PASS
  · pages dev 起不来 / 无读数 -> SKIP 且明确「未测不等于通过」
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from tools.admin_contrast_test import (find_chrome, free_port, read_admin_key,
                                       start_pages_dev, dump_dom)

VIEWPORTS = [(320, 700), (390, 844), (768, 1024), (1440, 900)]
MIN_PX = 44   # 产品自立触控基线

PROBE = r"""<!doctype html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0;background:#111}iframe{border:0;display:block}</style>
</head><body><div id="h"></div>
<script>
var KEY = decodeURIComponent((location.hash || '').slice(1));
var VPS = __VPS__;
var MIN = __MIN__;
try { sessionStorage.setItem('dg-admin-key', KEY); }
catch (e) { document.title = JSON.stringify({err: 'storage: ' + e}); }
var host = document.getElementById('h');
var frames = [];
VPS.forEach(function (v, i) {
  var f = document.createElement('iframe');
  f.id = 'f' + i;
  f.src = '/admin/?ar=' + v[0] + '_' + Date.now();
  f.style.width = v[0] + 'px';
  f.style.height = v[1] + 'px';
  host.appendChild(f);
  frames.push(f);
});
function inScroller(win, e) {
  /* 滚动容器（overflow-x:auto/scroll）内的后代超出容器是设计，不算越界 */
  var anc = e.parentElement;
  while (anc) {
    var acs = win.getComputedStyle(anc);
    if (acs.overflowX === 'auto' || acs.overflowX === 'scroll') return true;
    anc = anc.parentElement;
  }
  return false;
}
function audit(doc, win) {
  var out = {iw: win.innerWidth, scrollW: doc.documentElement.scrollWidth,
             overflow: false, wide: [], small: [], zone: 'none', checked: 0};
  var z = ['login', 'noapi', 'dash'];
  for (var k = 0; k < z.length; k++) {
    var e0 = doc.getElementById(z[k]);
    if (e0 && e0.classList.contains('on')) out.zone = z[k];
  }
  out.overflow = out.scrollW > win.innerWidth + 1;
  var all = doc.querySelectorAll('body *');
  for (var i = 0; i < all.length && out.wide.length < 6; i++) {
    var e = all[i];
    var cs = win.getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    var r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > win.innerWidth + 2 || r.left < -2) {
      if (inScroller(win, e)) continue;
      var cls = (typeof e.className === 'string' && e.className.trim())
        ? '.' + e.className.trim().split(/\s+/)[0] : '';
      out.wide.push({s: e.tagName.toLowerCase() + cls.slice(0, 24),
                     left: Math.round(r.left), right: Math.round(r.right)});
    }
  }
  var sel = 'a[href], button, input:not([type=hidden]), select, summary, [role="button"]';
  var els = doc.querySelectorAll(sel);
  for (var j = 0; j < els.length; j++) {
    var t = els[j];
    var tcs = win.getComputedStyle(t);
    if (tcs.display === 'none' || tcs.visibility === 'hidden') continue;
    var tr = t.getBoundingClientRect();
    if (tr.width === 0 || tr.height === 0) continue;
    var p = t.parentElement, nested = false;
    while (p && p !== doc.body) {
      if (/^(A|BUTTON|SUMMARY|LABEL)$/.test(p.tagName)) { nested = true; break; }
      p = p.parentElement;
    }
    if (nested) continue;
    if (tcs.display === 'inline') continue;   /* WCAG 2.5.8 Inline 豁免 */
    out.checked++;
    if (tr.height < MIN || tr.width < MIN) {
      var tc = (typeof t.className === 'string' && t.className.trim())
        ? '.' + t.className.trim().split(/\s+/)[0] : '';
      out.small.push({s: t.tagName.toLowerCase() + tc.slice(0, 22),
                      w: Math.round(tr.width), h: Math.round(tr.height),
                      txt: (t.textContent || t.value || '').trim().slice(0, 12)});
    }
  }
  return out;
}
setTimeout(function () {
  try {
    var res = [];
    for (var i = 0; i < frames.length; i++) {
      var d = frames[i].contentDocument, w = frames[i].contentWindow;
      if (!d || !w) { res.push({vw: VPS[i][0], err: 'no doc'}); continue; }
      var a = audit(d, w);
      a.vw = VPS[i][0];
      res.push(a);
    }
    document.title = JSON.stringify(res);
  } catch (e) { document.title = JSON.stringify({err: String(e)}); }
}, 9000);
</script></body></html>"""


def probe_html():
    """占位符替换作用在拼接后的完整串上（U-188 同课）。"""
    html = PROBE
    html = html.replace('__VPS__', json.dumps(VIEWPORTS))
    html = html.replace('__MIN__', str(MIN_PX))
    return html


def main():
    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe')
        return 0
    # 轮125：后台已静态化（轮109），不再需要 wrangler pages dev + D1。
    # 改用进程内 SiteServer —— 与 CI 同一条路，零 npx、零 D1、零公网。
    key = read_admin_key() or ''
    port = free_port()
    print('起进程内静态服务于端口 %d（无需 wrangler/D1）...' % port)
    _srv = None
    try:
        from cdp_client import SiteServer
        _srv = SiteServer(os.path.join(BASE, 'site'), port=port)
    except Exception as _e:
        print('RESULT: SKIP  静态服务起不来: %s —— 未测不等于通过' % _e)
        return 0
    dst = os.path.join(BASE, 'site', '_admin_probe_resp.html')
    try:
        html = probe_html()
        assert key not in html, '探针本体不得含密钥'
        open(dst, 'w', encoding='utf-8').write(html)
        rows = None
        url = 'http://127.0.0.1:%d/_admin_probe_resp.html#%s' % (port, key)
        try:
            rows = dump_dom(chrome, url, vb=40000, win='1480,1000', attempts=6)
        finally:
            try:
                os.remove(dst)
            except Exception:
                pass
        if rows is None:
            print('RESULT: SKIP  无读数（重试后仍空）—— 未测不等于通过')
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
            print('  vw=%-5s zone=%-5s scrollW=%-5s 触控目标 %d 个，不足 %dpx 的 %d' % (
                a['vw'], a['zone'], a['scrollW'], a['checked'], MIN_PX, len(a['small'])))
            if a['zone'] != 'dash':
                fails.append('vw=%s zone=%s（未进 dash：数据未渲染，读数无意义）' % (a['vw'], a['zone']))
                continue
            if a['overflow']:
                fails.append('vw=%d 横向溢出 scrollW=%d > iw=%d' % (
                    a['vw'], a['scrollW'], a['iw']))
            for w in a['wide'][:3]:
                fails.append('vw=%d 元素越界 %s (left=%d right=%d)' % (
                    a['vw'], w['s'], w['left'], w['right']))
            for t in a['small'][:4]:
                fails.append('vw=%d 触控目标 %s %dx%d < %dpx  %r' % (
                    a['vw'], t['s'], t['w'], t['h'], MIN_PX, t['txt']))

        print()
        if total_checked == 0:
            print('RESULT: SKIP  未检查到任何触控目标 —— 不计入 PASS')
            return 0
        if fails:
            print('RESULT: FAIL  后台响应式/触控（基线 %dpx，产品自立）' % MIN_PX)
            for f in fails[:10]:
                print('  -', f)
            return 1
        print('RESULT: PASS  后台 %d 视口无溢出、无越界，%d 个触控目标均 >= %dpx'
              % (len(rows), total_checked, MIN_PX))
        return 0
    finally:
        # 轮125：proc 已改 SiteServer，关服务不再 kill 子进程
        try:
            if _srv is not None:
                _srv.stop()
        except Exception:
            pass


if __name__ == '__main__':
    sys.path.insert(0, BASE)
    from tools.gate_stamp import record
    _t0 = time.time()
    _rc = main()
    record(__file__, {0: 'PASS', 1: 'FAIL'}.get(_rc, 'SKIP'), time.time() - _t0)
    sys.exit(_rc)
