# -*- coding: utf-8 -*-
r"""tools/focus_ring_contrast_test.py —— 键盘焦点环必须可见且对比达标。

## 为什么需要（轮146）
本仓此前 145 轮测过 hover / active 的反馈（microinteraction_test 用
CSS.forcePseudoState），也测过文字对比度（contrast_audit 测正文），
但**从未测过「Tab 键走到某个元素时，焦点环自己看不看得见」**。

WCAG 两条同时管这件事：
  · 2.4.7 Focus Visible —— 键盘焦点必须有可见指示
  · 1.4.11 Non-text Contrast —— 焦点环与其相邻背景对比 >= 3:1

后台有 outline:none 的写法（select 基础规则里），一旦它上面没有
特异性更高的 :focus-visible 兜住，焦点环就被抹掉 —— 键盘用户完全
看不出焦点在哪。这正是 1.4.7 上最常见的回归路径，而文字对比判据
（contrast_audit）只看文字、看不到环。

## 口径（含诚实边界）
  1. 两站全部可聚焦元素（a[href]/button/select/input/textarea）
  2. 焦点环由 :focus-visible 提供，默认态读不到 —— 必须先用
     CSS.forcePseudoState 强制该伪态、用 getComputedStyleForNode
     取回此刻生效的 outline-style/width/color/offset
  3. 环的**相邻背景按几何取**（轮146 我第一版在这里算错过）：
     outline 永远画在 border box 之外，offset >= 0 时环外侧相邻的是
     祖先有效背景；offset < 0 时环压进元素内部，相邻的是元素自身背景。
     取与环不相邻的那个颜色当参照会得出假阳性 —— 实测把 .skip-link
     的 16.53:1 误判成 1.93:1（它是「获焦时出现的高对比实心块」，
     自身背景浅、环在块外面）。
  4. alpha 先合成到有效底色再算亮度（rgba 环色直接比会偏）
  5. 边界（明确标注，不假装覆盖）：本判据以 outline 为焦点指示。
     若某处改用 box-shadow 或 border 画焦点环，这里会报「无指示」——
     那属口径局限而非缺陷；当前两站都用 outline，故按此口径。

## 尺子有效性自检（U-427：报 0 必须先证明能抓到非 0）
  S1 注入暗环 #141210（对深色页面 ~1:1）-> 必须报出多个不达标
  S2 不注入（真实站点）-> 必须 0 个不达标（否则恒红）
  S3 注入 outline:none 抹掉焦点环 -> 必须报「无可见焦点指示」
关键：注入必须打在 :focus-visible 上（即被测态）。轮146 我第一版
把注入规则写在 :focus-visible 却在不聚焦时读 computed，得到 style:none，
误判成「探测器无牙」—— 反向验证要让违规进入被测态。

缺 chrome / 起不了服务 -> SKIP 并说明（未测不等于通过）。
"""
import io
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')

SEL = 'a[href],button,select,input,textarea'
RATIO_MIN = 3.0          # WCAG 1.4.11 非文本对比
WIDTH_MIN = 1.0          # 小于 1px 视为不可辨

PAGES = [('assets/css/main.css 所在主站', '/index.html'),
         ('后台 admin/index.html', '/admin/index.html')]

# 强制伪态后回写 inline，再用普通 JS 计算（一次算完全部，避免逐个往返）
APPLY = """(function(list){
  var els = document.querySelectorAll('%s');
  list.forEach(function(x){
    var el = els[x.i];
    if (!el) { return; }
    el.style.outlineStyle = x.style;
    el.style.outlineWidth = x.w;
    el.style.outlineColor = x.color;
    el.style.outlineOffset = x.off;
    el.setAttribute('data-ring', '1');
  });
  return list.length;
})""" % SEL

MEASURE = r"""(function(){
  function parse(c){
    var m = String(c).match(/[\d.]+/g);
    if (!m) { return null; }
    return {r:+m[0], g:+m[1], b:+m[2],
            a: m.length >= 4 ? parseFloat(m[3]) : 1};
  }
  function lum(c){
    var f = [c.r, c.g, c.b].map(function(v){
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126*f[0] + 0.7152*f[1] + 0.0722*f[2];
  }
  function cr(a, b){
    var l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }
  function blend(f, bg){
    var al = f.a;
    return {r: f.r*al + bg.r*(1-al), g: f.g*al + bg.g*(1-al),
            b: f.b*al + bg.b*(1-al), a: 1};
  }
  function stackBg(n){
    var base = parse(getComputedStyle(document.body).backgroundColor)
            || {r:11, g:9, b:8, a:1};
    if (base.a < 1) { base = blend(base, {r:0, g:0, b:0, a:1}); }
    var k = 0;
    while (n && k < 14) {
      var c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.01) { return blend(c, base); }
      n = n.parentElement;
      k++;
    }
    return base;
  }
  var rings = [], noRing = [];
  [].slice.call(document.querySelectorAll('[data-ring]')).forEach(function(el){
    var st = getComputedStyle(el);
    var name = el.tagName.toLowerCase();
    var cls = ((typeof el.className === 'string' ? el.className : '') || '')
              .split(' ')[0].slice(0, 16);
    var txt = (el.textContent || '').trim().slice(0, 12);
    var oc = parse(st.outlineColor);
    var ow = parseFloat(st.outlineWidth) || 0;
    if (!oc || st.outlineStyle === 'none' || ow < 1) {
      noRing.push({tag: name, cls: cls, txt: txt,
                   why: st.outlineStyle + ' ' + st.outlineWidth});
      return;
    }
    var off = parseFloat(st.outlineOffset) || 0;
    // 几何正确的相邻色：outline 画在 border box 之外
    var adj = off >= 0 ? stackBg(el.parentElement) : stackBg(el);
    var ring = blend(oc, adj);
    rings.push({tag: name, cls: cls, txt: txt,
                w: ow, off: off,
                ratio: Math.round(cr(ring, adj) * 100) / 100,
                ring: [Math.round(ring.r), Math.round(ring.g),
                       Math.round(ring.b)],
                adj: [Math.round(adj.r), Math.round(adj.g),
                      Math.round(adj.b)]});
  });
  return JSON.stringify({rings: rings, noRing: noRing});
})()"""

INJECT_DARK = ('a[href]:focus-visible,button:focus-visible,'
               'select:focus-visible,input:focus-visible,'
               'textarea:focus-visible{'
               'outline:2px solid #141210 !important;'
               'outline-offset:2px !important}')
INJECT_NONE = ('a[href]:focus-visible,button:focus-visible,'
               'select:focus-visible,input:focus-visible,'
               'textarea:focus-visible{outline:none !important}')


def collect(page, CDP_PAGE, url, inject=None):
    """完整管线：加载 -> （可选注入）-> 强制伪态取 outline -> 量对比。"""
    CDP_PAGE.navigate(page, url)
    CDP_PAGE.wait_for(page, "document.querySelectorAll('%s').length>0" % SEL,
                      30)
    time.sleep(2.2)
    if inject:
        page.eval_js('(function(){var st=document.createElement("style");'
                     'st.id="rev";st.textContent=' + json.dumps(inject) +
                     ';document.head.appendChild(st);return 1;})()',
                     timeout=20)
    # 顺序要紧：CSS agent 依赖 DOM agent 先启用
    page.call('DOM.enable')
    page.call('CSS.enable')
    doc = page.call('DOM.getDocument', {'depth': -1})
    res = page.call('DOM.querySelectorAll',
                    {'nodeId': doc['root']['nodeId'], 'selector': SEL})
    listv = []
    for i, nid in enumerate(res['nodeIds']):
        try:
            page.call('CSS.forcePseudoState',
                      {'nodeId': nid,
                       'forcedPseudoClasses': ['focus-visible']})
            cs = page.call('CSS.getComputedStyleForNode', {'nodeId': nid})
        except Exception:
            continue
        finally:
            try:
                page.call('CSS.forcePseudoState',
                          {'nodeId': nid, 'forcedPseudoClasses': []})
            except Exception:
                pass
        pr = {p['name']: p['value'] for p in cs['computedStyle']}
        # 不跳过隐藏元素（轮146 自纠）：
        # 第一版按 display:none 跳过，于是主站 57 个可聚焦只测了 49 个，
        # 却报「49/49 全部达标」—— 把没测的当成通过，是假绿。
        # 实测证明：元素自身或其祖先 display:none 时，
        # getComputedStyleForNode 仍返回它在 :focus-visible 下生效的
        # outline 值（57 个全部读通、0 失败），而这些值正是该界面展开后
        # 键盘用户实际会看到的焦点环，所以照测不误。
        # 唯一代价是背景参照取的是「展开后」的祖先背景 —— 与真实一致。
        hidden = (pr.get('display') == 'none'
                  or pr.get('visibility') == 'hidden')
        listv.append({'i': i,
                      'style': pr.get('outline-style', 'none'),
                      'w': pr.get('outline-width', '0px'),
                      'color': pr.get('outline-color', ''),
                      'off': pr.get('outline-offset', '0px'),
                      'hidden': 1 if hidden else 0})
    if not listv:
        return None, None, 0
    # 竞态守卫：APPLY 用 document.querySelectorAll(SEL)[i] 按索引回写，
    # 而索引来自刚才 DOM.getDocument 的快照。若测量期间页面自己新增了
    # 可聚焦元素（异步渲染），索引就会错位 —— 把 A 的焦点环算到 B 头上，
    # 且不会报错，只会给出错误读数。所以回写前复核数量，不符就报未覆盖。
    now = page.eval_js("document.querySelectorAll('%s').length" % SEL,
                       timeout=20)
    if now != len(res['nodeIds']):
        return [], [], len(res['nodeIds'])
    page.eval_js(APPLY + '(' + json.dumps(listv) + ')', timeout=30)
    d = json.loads(page.eval_js(MEASURE, timeout=40))
    # 覆盖率必须回报：读到的节点数 / DOM 里可聚焦总数。
    # 差额说明有些元素根本没被强制伪态读到（CDP 取不到节点等），
    # 那属于「未测」，不能算通过。
    return d['rings'], d['noRing'], len(res['nodeIds']), len(listv)


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  CDP 模块不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（环境问题，本判据未执行）')
        return 0
    if not os.path.isdir(SITE):
        print('RESULT: SKIP  找不到站点目录（未测不等于通过）')
        return 0

    srv = SiteServer(SITE)
    if not srv.ok:
        print('RESULT: SKIP  静态服务起不来（未测不等于通过）')
        return 0
    ch = Chrome()
    results = {}
    inj_dark = inj_none = None
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            for label, path in PAGES:
                u = srv.url(path + '?ring=%d' % int(time.time()))
                got = collect(page, ch, u)
                rings, no_ring, total, read = got
                if rings is None:
                    print('  %s: 无可聚焦元素（跳过）' % label)
                    results[label] = (None, None, 0, 0)
                    continue
                results[label] = (rings, no_ring, total, read)
                if inj_dark is None:
                    g2 = collect(page, ch, u, INJECT_DARK)
                    inj_dark = (g2[0] or [])
                if inj_none is None:
                    g3 = collect(page, ch, u, INJECT_NONE)
                    inj_none = g3[1] if g3[1] else []
        finally:
            page.close()
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()

    print('=== 尺子有效性自检 ===')
    bad_selftest = []
    dark_below = [x for x in inj_dark if x['ratio'] < RATIO_MIN] \
        if inj_dark else []
    ok1 = len(dark_below) > 0
    print('  [%s] S1 注入暗环 #141210 -> 抓到 %d 个 <%.1f:1'
          % ('ok' if ok1 else 'X', len(dark_below), RATIO_MIN))
    if not ok1:
        bad_selftest.append('S1 注入的低对比环未被抓到，判据可能恒绿')
    ok3 = len(inj_none or []) > 0
    print('  [%s] S3 注入 outline:none -> 抓到 %d 个「无可见焦点指示」'
          % ('ok' if ok3 else 'X', len(inj_none or [])))
    if not ok3:
        bad_selftest.append('S3 抹掉焦点环未被抓到，2.4.7 侧可能恒绿')
    real_bad = 0
    for label, (rings, no_ring, _t, _r) in results.items():
        if rings is None:
            continue
        real_bad += len([x for x in rings if x['ratio'] < RATIO_MIN])
        real_bad += len(no_ring or [])
    ok2 = real_bad == 0
    print('  [%s] S2 真实站点不注入 -> 无报红（应 0，实 %d）'
          % ('ok' if ok2 else 'X', real_bad))
    if not ok2:
        bad_selftest.append('S2 真实站点已被判出问题，见下方明细')
    print()
    if bad_selftest:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad_selftest:
            print('  -', b)
        return 1

    fails = []
    print('=== 焦点环实测（两站）===')
    for label, (rings, no_ring, total, read) in results.items():
        if rings is None:
            continue
        low = [x for x in rings if x['ratio'] < RATIO_MIN]
        # 覆盖率明算：DOM 里可聚焦数、读到计算值数、其中隐藏态数
        print('  %s：可聚焦 %d 个，读到生效样式 %d 个，'
              '有可见焦点环 %d 个'
              % (label, total, read, len(rings)))
        if read < total:
            fails.append('%s：%d 个可聚焦元素读不到生效样式（未测，'
                         '不能算通过），实际读到 %d 个'
                         % (label, total - read, read))
        if rings:
            worst = min(rings, key=lambda x: x['ratio'])
            print('     最低对比 %.2f:1  于 %s.%s「%s」环=%s 相邻底=%s'
                  % (worst['ratio'], worst['tag'], worst['cls'],
                     worst['txt'], worst['ring'], worst['adj']))
        for x in low:
            fails.append('%s %s.%s「%s」焦点环 %.2f:1 < 3:1'
                         % (label, x['tag'], x['cls'], x['txt'], x['ratio']))
        for x in (no_ring or []):
            fails.append('%s %s.%s「%s」强制 :focus-visible 后'
                         '无可见焦点指示（outline %s）'
                         % (label, x['tag'], x['cls'], x['txt'], x['why']))
    print()
    if fails:
        print('发现键盘可达性问题（WCAG 2.4.7 / 1.4.11）：')
        for f in fails[:20]:
            print('  -', f)
        print()
        print('RESULT: FAIL  %d 处焦点环缺失、对比不达标或未覆盖'
              % len(fails))
        return 1
    n_all = sum(len(r or []) for r, _n, _t, _rd in results.values())
    t_all = sum(t for _r, _n, t, _rd in results.values())
    print('RESULT: PASS  两站 %d 个可聚焦元素全部读到生效样式并覆盖 '
          '%d 个焦点环（含未展开界面的隐藏元素），对比均 >= %.1f:1'
          '（WCAG 2.4.7 + 1.4.11），且三项自检证明该报的报得出'
          % (t_all, n_all, RATIO_MIN))
    return 0


if __name__ == '__main__':
    sys.exit(main())
