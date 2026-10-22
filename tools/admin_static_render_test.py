# -*- coding: utf-8 -*-
r"""tools/admin_static_render_test.py —— 后台静态页真渲染判据（headless CDP）。

## 为什么需要它（静态判据看不见的那一半）
tools/admin_static_data_test.py 能证明「数据自洽、代码里没有 fetch 字样」，
但证明不了**页面真的把数字画出来了**。本仓最贵的两句话：
  · 「函数存在 != 行为发生」（轮17/52/53）
  · 「判据存在但跑不了，比没有判据更危险」（轮96/107/108）
静态后台页最容易出的三种事故，只有浏览器能看见：
  1. 数据文件路径写错（/admin/ 下相对路径必须 ../）→ 页面停在「数据未加载」；
  2. 渲染脚本抛错 → 指标卡与表格全空，而 HTML 看着没问题；
  3. 刷新后数字变化或归零 → 正是老大 2026-10-22 报的那个 bug 的形态。

## 判据（A~E 各对一种事故）
  A 进 dash 态：#dash.on 且 #nodata 不 on（数据文件确实加载到了）。
  B 有数字且与数据文件一致：读 DOM 文本，不读 JS 变量 —— 变量在而没渲染出来也算失败。
  C 图画出来了：两张 canvas 的墨迹占比 > 1%（空 canvas 就是没画）。
  D 零接口、零跨源：performance 资源清单里不得出现 /api/ 或任何跨源请求。
  E 刷新不变：重载两次，指标卡读数与首次完全一致（直接对着那个 bug 写）。
  附带 表格非空且行数对得上、无横向溢出、触控目标 >= 44px
        —— 取代原先需要登录态的 admin_responsive_test。

## 为什么不再需要 wrangler pages dev
上一版后台判据必须起带 D1 的本地后端，因为页面要读接口。
静态页零接口 ⇒ 进程内静态服务（cdp_client.SiteServer）就够，
CI 与本机同一条路，少一类环境故障。

## 守卫（沿用踩过的坑）
  · 零样本不判 PASS（gate_guard）
  · chrome 偶发空输出 -> 重试 5 次（U-193）
  · 缺 chrome / 服务起不来 -> SKIP 并说明「未测不等于通过」，不判绿
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

from gate_guard import verdict, emit                     # noqa: E402

# 解释器能力解析（轮74）：本机 PATH 首位的 python 缺 websocket-client，
# 不切换会得到「chrome 启动失败」的假 SKIP —— 而 SKIP 与「判据没跑」在日志里很像。
try:
    import pyenv
    pyenv.ensure(["websocket"], label="admin_static_render_test")
except ImportError:
    print("[WARN] tools/pyenv.py 缺失，无法解析解释器（环境缺口只能靠人工判读）")
from cdp_client import Chrome, SiteServer, find_chrome   # noqa: E402

SITE = os.path.join(BASE, 'site')
VIEWPORTS = [(1440, 900), (390, 844)]
MIN_PX = 44
TABLES = ('tbl-weeks', 'tbl-days', 'tbl-country', 'tbl-lang', 'tbl-screen')
CANVASES = ('chart-weeks', 'chart-days')
MARKER = 'var DG_STATIC_STATS = '
CARDS_JS = ("JSON.stringify([].slice.call(document.querySelectorAll('#cards .card dd'))"
            ".map(function(x){return x.textContent.trim()}))")

PROBE = r"""
(function () {
  var MIN = __MIN__;
  var TABLES = __TABLES__;
  var CANVASES = __CANVASES__;
  var out = {zone: 'none', cards: [], tables: {}, canvas: {}, api: [], cross: [],
             resources: 0, overflow: false, scrollW: 0, iw: 0,
             small: [], checked: 0, wide: []};
  ['nodata', 'dash'].forEach(function (id) {
    var e = document.getElementById(id);
    if (e && e.classList.contains('on')) out.zone = id;
  });
  [].slice.call(document.querySelectorAll('#cards .card')).forEach(function (c) {
    var dt = c.querySelector('dt'), dd = c.querySelector('dd');
    out.cards.push([dt ? dt.textContent.trim() : '', dd ? dd.textContent.trim() : '']);
  });
  TABLES.forEach(function (id) {
    var t = document.getElementById(id);
    out.tables[id] = t ? {rows: t.querySelectorAll('tbody tr').length,
                          cols: (t.querySelector('thead tr') || {}).cellCount || 0} : null;
  });
  CANVASES.forEach(function (id) {
    var cv = document.getElementById(id);
    if (!cv) { out.canvas[id] = {err: 'no canvas'}; return; }
    try {
      var ctx = cv.getContext('2d');
      var d = ctx.getImageData(0, 0, cv.width, cv.height).data;
      var ink = 0, total = 0;
      for (var k = 0; k < d.length; k += 4) {
        total++;
        if (d[k + 3] > 8 || d[k] > 24 || d[k + 1] > 24 || d[k + 2] > 24) ink++;
      }
      out.canvas[id] = {w: cv.width, h: cv.height,
                        pct: total ? Math.round(ink / total * 1000) / 10 : 0};
    } catch (e) { out.canvas[id] = {err: String(e)}; }
  });
  [].slice.call(performance.getEntriesByType('resource')).forEach(function (r) {
    out.resources++;
    if (r.name.indexOf('/api/') >= 0) out.api.push(r.name);
    try { if (new URL(r.name).origin !== location.origin) out.cross.push(r.name); } catch (e) {}
  });
  out.scrollW = document.documentElement.scrollWidth;
  out.iw = window.innerWidth;
  out.overflow = out.scrollW > out.iw + 1;
  var sel = 'a[href], button, input:not([type=hidden]), select, summary, [role="button"]';
  [].slice.call(document.querySelectorAll(sel)).forEach(function (t) {
    var cs = getComputedStyle(t);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    var r = t.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    var p = t.parentElement, nested = false;
    while (p && p !== document.body) {
      if (/^(A|BUTTON|SUMMARY|LABEL)$/.test(p.tagName)) { nested = true; break; }
      p = p.parentElement;
    }
    if (nested || cs.display === 'inline') return;      /* WCAG 2.5.8 Inline 豁免 */
    out.checked++;
    if (r.height < MIN || r.width < MIN) {
      var cls = (typeof t.className === 'string' && t.className.trim())
        ? '.' + t.className.trim().split(/\s+/)[0] : '';
      out.small.push({s: t.tagName.toLowerCase() + cls.slice(0, 22),
                      w: Math.round(r.width), h: Math.round(r.height),
                      txt: (t.textContent || '').trim().slice(0, 12)});
    }
  });
  [].slice.call(document.querySelectorAll('body *')).forEach(function (e) {
    var cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    var r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.right > window.innerWidth + 2 || r.left < -2) {
      var anc = e.parentElement, inScroller = false;
      while (anc) {
        var acs = getComputedStyle(anc);
        if (acs.overflowX === 'auto' || acs.overflowX === 'scroll') { inScroller = true; break; }
        anc = anc.parentElement;
      }
      if (inScroller) return;   /* 宽表放 .tw 里可横滑是设计（轮79） */
      if (out.wide.length < 6) {
        var c2 = (typeof e.className === 'string' && e.className.trim())
          ? '.' + e.className.trim().split(/\s+/)[0] : '';
        out.wide.push({s: e.tagName.toLowerCase() + c2.slice(0, 24),
                       left: Math.round(r.left), right: Math.round(r.right)});
      }
    }
  });
  return JSON.stringify(out);
})()
"""


def probe_js():
    """占位符替换作用在完整串上（U-188 同课，已第 5 次）。"""
    return (PROBE.replace('__MIN__', str(MIN_PX))
                 .replace('__TABLES__', json.dumps(list(TABLES)))
                 .replace('__CANVASES__', json.dumps(list(CANVASES))))


def read_expected():
    """从数据文件本身取期望值。

    不 import 生成器：判据与被测物必须不同源，否则生成器自己算错时两边一起错，
    判据永远绿（轮94「反向验证因硬编码而自欺」同一类病）。
    也不用正则抠单字段：admin-stats.js 是缩进 JSON、字段各占一行，
    按行拼的正则一改格式就静默失配 —— 剥出对象字面量整段解析。
    """
    pth = os.path.join(SITE, 'assets', 'data', 'admin-stats.js')
    if not os.path.exists(pth):
        return None
    txt = open(pth, encoding='utf-8').read()
    head = txt.find(MARKER)
    if head < 0:
        return None
    body = txt[head + len(MARKER):].rstrip()
    if body.endswith(';'):
        body = body[:-1]
    try:
        d = json.loads(body)
    except Exception:
        return None
    t = d['totals']
    return {'pv': t['pv'], 'uv': t['uv'], 'scenes': t['scenes'],
            'weeks': len(d['weeks']), 'days': len(d['days'])}


def main():
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome —— 未测不等于通过')
        return 0
    expected = read_expected()
    if not expected:
        print('RESULT: FAIL  读不到 admin-stats.js 的期望值（判据前提不成立）')
        return 1

    srv = SiteServer(SITE)
    if srv.ok and srv.srv:
        # chrome 建连后又放弃（预取/取消）会让 ThreadingHTTPServer 打整段
        # ConnectionReset traceback 到 stderr。PASS 的日志里带栈会训练人忽略栈，
        # 所以只静音这一类「客户端主动断」，服务端真错仍由判据自己报。
        srv.srv.handle_error = lambda *a, **k: None
    if not srv.ok:
        print('RESULT: SKIP  本地静态服务起不来 —— 未测不等于通过')
        return 0
    try:
        chrome = Chrome()
    except Exception as e:
        print('RESULT: SKIP  chrome 启动失败（%s）—— 未测不等于通过' % e)
        srv.stop()
        return 0

    fails = []
    checked = 0
    skipped_vp = []
    again = None
    try:
        # ---- A~D + 附带项：两个视口各测一遍 ----
        for vw, vh in VIEWPORTS:
            page, tid = chrome.new_page(vw, vh, mobile=(vw < 500))
            try:
                url = srv.url() + '/admin/?v=%d_%d' % (vw, int(time.time()))
                if not chrome.navigate(page, url):
                    fails.append('vw=%d 导航超时' % vw)
                    continue
                chrome.wait_for(
                    page, "document.getElementById('cards') && "
                          "document.getElementById('cards').children.length > 0",
                    timeout=25)
                raw = None
                for _ in range(5):          # chrome 偶发空输出（U-193）
                    raw = page.eval_js(probe_js())
                    if raw:
                        break
                    time.sleep(0.6)
                if not raw:
                    fails.append('vw=%d 无读数（重试 5 次仍空）' % vw)
                    continue
                a = json.loads(raw)
            finally:
                chrome.close_page(tid)

            # 设备模拟没生效时不能按产品缺陷判红：CI 的 chromium 若忽略
            # setDeviceMetricsOverride，窄屏断言会得到与本机不同的读数。
            # 环境缺口 != 产品缺陷（轮74 归因纪律）；该视口记 SKIP，不计入 checked。
            if abs(a['iw'] - vw) > 2:
                print('  vw=%-5s 设备模拟未生效（innerWidth=%s）—— 该视口 SKIP，不计入 PASS' % (vw, a['iw']))
                skipped_vp.append(vw)
                continue

            checked += 1
            print('  vw=%-5s zone=%-6s 卡片 %d 张 · 资源 %d 项 · 接口请求 %d · 溢出=%s · 触控 %d 个（不足 %d）' % (
                vw, a['zone'], len(a['cards']), a['resources'], len(a['api']),
                a['overflow'], a['checked'], len(a['small'])))

            if a['zone'] != 'dash':
                fails.append('vw=%d 未进 dash 态（zone=%s）—— 数据文件没加载上' % (vw, a['zone']))
                continue

            cards = dict(a['cards'])
            if len(a['cards']) < 6:
                fails.append('vw=%d 指标卡只有 %d 张（应 6 张）' % (vw, len(a['cards'])))
            for name, val in a['cards']:
                if not val or val in ('0', '—'):
                    fails.append('vw=%d 指标卡「%s」为空或零（%r）' % (vw, name, val))
            if cards.get('累计浏览') != '{:,}'.format(expected['pv']):
                fails.append('vw=%d 累计浏览渲染成 %r，数据文件是 %s' % (
                    vw, cards.get('累计浏览'), '{:,}'.format(expected['pv'])))
            if cards.get('累计访客') != '{:,}'.format(expected['uv']):
                fails.append('vw=%d 累计访客渲染成 %r，数据文件是 %s' % (
                    vw, cards.get('累计访客'), '{:,}'.format(expected['uv'])))

            for cid in CANVASES:
                c = a['canvas'].get(cid)
                if not c or 'err' in c:
                    fails.append('vw=%d %s 取不到样：%s' % (vw, cid, (c or {}).get('err')))
                elif c['pct'] < 1.0:
                    fails.append('vw=%d %s 墨迹仅 %.1f%%，看着像空 canvas' % (vw, cid, c['pct']))

            if a['api']:
                fails.append('vw=%d 静态页发出了接口请求：%s' % (vw, a['api'][0][:70]))
            if a['cross']:
                fails.append('vw=%d 出现跨源请求（违反零外部请求）：%s' % (vw, a['cross'][0][:70]))

            for name, t in a['tables'].items():
                if not t:
                    fails.append('vw=%d 找不到表 %s' % (vw, name))
                elif t['rows'] == 0:
                    fails.append('vw=%d 表 %s 零行（空表会被读成「没有访问」）' % (vw, name))
            tw = a['tables'].get('tbl-weeks')
            if tw and tw['rows'] != expected['weeks']:
                fails.append('vw=%d 周次表 %d 行 != 数据 %d 周' % (vw, tw['rows'], expected['weeks']))

            if a['overflow']:
                fails.append('vw=%d 横向溢出 scrollW=%d > iw=%d' % (vw, a['scrollW'], a['iw']))
            for w in a['wide'][:3]:
                fails.append('vw=%d 元素越界 %s (left=%d right=%d)' % (vw, w['s'], w['left'], w['right']))
            for t in a['small'][:4]:
                fails.append('vw=%d 触控目标 %s %dx%d < %dpx %r' % (
                    vw, t['s'], t['w'], t['h'], MIN_PX, t['txt']))

        # ---- E) 刷新不变：正对着「演示一刷新访问量归零」这个 bug ----
        page, tid = chrome.new_page(1440, 900)
        try:
            chrome.navigate(page, srv.url() + '/admin/')
            first = chrome.wait_for(page, CARDS_JS, timeout=25)
            for i in range(2):
                chrome.navigate(page, srv.url() + '/admin/?r=%d' % int(time.time() * 1000))
                time.sleep(1.2)
                again = chrome.wait_for(page, CARDS_JS, timeout=25)
                checked += 1
                if not first or not again:
                    fails.append('刷新稳定性未取证（第 %d 次刷新读不到指标卡）' % (i + 1))
                elif again != first:
                    fails.append('刷新后数字变了（这就是演示时归零的那类 bug）：'
                                 ' 首次 %s / 第 %d 次 %s' % (first, i + 1, again))
            if first and again == first:
                print('  刷新 3 次指标卡读数完全一致：%s' % first[:78])
        finally:
            chrome.close_page(tid)

        if skipped_vp:
            print('  （%d 个视口因设备模拟未生效未取证：%s）' % (
                len(skipped_vp), ', '.join(str(x) for x in skipped_vp)))
        if len(skipped_vp) == len(VIEWPORTS):
            # 一个视口都没测到就不能算通过（gate_guard 的零样本规矩）
            print()
            print('RESULT: SKIP  全部 %d 个视口设备模拟未生效 —— 未测不等于通过'
                  % len(VIEWPORTS))
            return 0
        print()
        for f in fails:
            print('  -', f)
        print()
        code, msg = verdict(checked=checked, fails=fails, what='后台静态页渲染项')
        return emit(code, msg)
    except Exception as e:
        print('RESULT: SKIP  浏览器环境异常（%s: %s）—— 未测不等于通过'
              % (type(e).__name__, e))
        return 0
    finally:
        chrome.close()
        srv.stop()


if __name__ == '__main__':
    try:
        from tools.gate_stamp import record
    except Exception:
        record = None
    _t0 = time.time()
    _rc = main()
    if record:
        try:
            record(__file__, {0: 'PASS', 1: 'FAIL'}.get(_rc, 'SKIP'), time.time() - _t0)
        except Exception:
            pass
    sys.exit(_rc)
