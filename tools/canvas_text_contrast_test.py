# -*- coding: utf-8 -*-
r"""tools/canvas_text_contrast_test.py —— canvas 里承担信息职责的文字必须读得清。

## 为什么需要（轮149-151 一手缺陷）
本仓 150 轮的对比度判据（contrast_audit / admin_contrast）都只读 CSS
计算样式，而 ar-scenes.js、wood-to-statue.js 用 ctx.fillText 画的文字
（章节名、烈士姓名与生卒年、工序步骤、部位标注）**完全在它之外** ——
admin_contrast_test 自己就写着「canvas 内绘制文字本判据测不到」。

实测抓到的真缺陷（轮151 修）：纪念碑上
    ctx.fillStyle = "rgba(246,241,231,.6)"     近白、alpha .6
    ctx.fillText("1898 - 1931", mx, …)         烈士生卒年
画在石碑
    ctx.fillStyle = "rgba(198,190,176,.94)"    浅色
上 —— 浅字浅石，像素实测对比 **1.47:1**，游客在 AR 纪念碑前
根本读不到烈士生卒年。同一个 alpha .6 是给深色页底设计的 fg-dim，
被直接搬到了浅色碑面上。修后 6.97:1。

## 怎么测（关键：不能静态推断，必须采真实像素）
读代码算不出最终观感：canvas 上是多层叠加绘制，文字底下压着什么
取决于此前所有 fill/stroke 与渐变。所以包裹
CanvasRenderingContext2D.prototype.fillText，在**每次调用前**用
getImageData 取该文字将要覆盖的那块像素 —— 那一刻它正是"背景"，
含所有已画图层。取中位色，再把 fillStyle 乘 globalAlpha 合成上去，
算 WCAG 对比度。

两个必须处理的坑（都是本轮实测踩出来的）：
  · canvas 未绘制区是**透明**像素，直接当黑色算会得出假低对比
    （印章那条就被算成 2.93:1）。故 alpha=0 的像素要合成到该 canvas
    元素的有效页面背景（沿祖先找第一层不透明底色）。
  · fillStyle 可能是十六进制。只用 [\d.]+ 去 match 会把 #E8B761
    解析成垃圾数并产出 None 对比度。

## 判与不判的边界（这一条决定判据会不会 flaky）
按「峰值 alpha」分三类，只有第一类承担信息职责、才用静态阈值判：
  A 峰值 alpha >= 0.85  —— 文字在稳态下承担信息，要求 >= 4.5:1
  B 峰值 alpha < 0.85   —— 淡变标注/水印（如部位标签颈肩腰膝座
    实测峰值仅 .43，年份水印恒定 .14），是刻意的低不透明度装饰，
    按静态阈值判必然误报，只报数不判红
  C 一次都没采到        —— 覆盖不足，判红（不能把「没测到」当通过）

## 覆盖怎么保证（本轮另一处教训）
只进 AR 面板不 seek，采到的全是第一章，其余章节的字根本没进画面 ——
报「全部达标」就是假绿。所以逐个场景 seek 遍各章时间点，
并**在页内按文字去重**（每帧重绘会把记录数打爆，
实测 6 秒就填满 700 条上限，纪念碑从没轮到）。
最后要求采到的文字种类数 >= 预期下限（章节标签 13 个起步），
否则按覆盖不足判红。

## 尺子有效性自检（U-427）
  S1 合成一个"浅字压浅底"的记录 -> 分类器必须判 FAIL
  S2 水印（峰值 alpha .14、对比 1.33）-> 必须判 B 类豁免，不判红
  S3 章节名（峰值 .92、对比 8.3）-> 必须判 A 类且 PASS
  S4 只采到 2 种文字 -> 必须判「覆盖不足」而非通过
  S5 端到端：在真实页面上用固定 alpha 画一次已知的浅字压浅底
      -> 探针必须量出 < 1.5:1（证明像素管线真的在工作，
        而不只是分类器自洽）

缺 chrome / 起不了服务 -> SKIP 并说明（未测不等于通过）。
"""
import io
import json
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
DATA = os.path.join(SITE, 'assets', 'data', 'ar-data.js')

RATIO_MIN = 4.5        # WCAG AA 正文
# 峰值 alpha 到此才算「承担信息」（轮151 由 0.85 收紧到 0.60）。
# 原值 0.85 是拍的，敏感性分析证明它过保守：把阈值降到 0.50，
# 纳入判定的文字从 16 种升到 23 种、低于 4.5:1 的仍为 0 种 ——
# 也就是说部位标签（颈/肩/腰/膝/座，峰值 alpha 实测 0.68、对比 5.0:1）
# 本可以被检查，却被 0.85 白白豁免了。
# 取 0.60：纳入那批峰值>=0.6 的淡变标注（它们是承担信息的部位名称），
# 仍豁免恒定 0.14 的年份水印（实测 1.33:1，是刻意的背景大字，
# 轮138 已核实设计意图；0 豁免下它会误报）。
STABLE_MIN = 0.60
# 覆盖下限不写死：由 ar-data.js 的章节总数推导（轮151 自查——原先硬编码
# 10，章节一旦增删，要么加场景后覆盖率被悄悄放宽、要么减到 9 章时误判
# 「覆盖不足」。MIN_FLOOR 只是「推导失败也必须有个底」的保护，不是阈值。
MIN_FLOOR = 5

HOOK = r"""
(function(){
  window.__m = {};
  var P = CanvasRenderingContext2D.prototype;
  var orig = P.fillText;
  function parse(c){
    var s = String(c).trim();
    var hx = s.match(/^#([0-9a-f]{6})$/i);
    if (hx) { var n = parseInt(hx[1],16);
      return {r:(n>>16)&255,g:(n>>8)&255,b:n&255,a:1}; }
    var m = s.match(/[\d.]+/g);
    if (!m || m.length < 3) { return null; }
    var v = [parseFloat(m[0]),parseFloat(m[1]),parseFloat(m[2])];
    for (var q=0;q<3;q++){ if (isNaN(v[q])) { return null; } }
    var a = m.length >= 4 ? parseFloat(m[3]) : 1;
    if (isNaN(a)) { a = 1; }
    return {r:v[0],g:v[1],b:v[2],a:a};
  }
  function med(l){ var s=l.slice().sort(function(a,b){return a-b;});
                   return s[Math.floor(s.length/2)]; }
  function lum(c){
    var f=[c.r,c.g,c.b].map(function(v){ v=v/255;
      return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); });
    return 0.2126*f[0]+0.7152*f[1]+0.0722*f[2];
  }
  function cr(a,b){ var l1=lum(a),l2=lum(b);
    return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05); }
  function blend(f,bg){ var al=f.a;
    return {r:f.r*al+bg.r*(1-al), g:f.g*al+bg.g*(1-al),
            b:f.b*al+bg.b*(1-al), a:1}; }
  function pageBg(el){
    var base = {r:11,g:9,b:8,a:1};
    var n = el, k = 0;
    while (n && k < 12) {
      var c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.01) { return blend(c, base); }
      n = n.parentElement; k++;
    }
    return base;
  }
  P.fillText = function(txt){
    try {
      var cv = this.canvas;
      var sc = cv.width / (cv.clientWidth || cv.width);
      if (!(sc > 0.2)) { sc = 1; }
      var fs = parseFloat((String(this.font).match(
          /(\d+(?:\.\d+)?)px/) || [0,12])[1]) || 12;
      var x = +arguments[1] || 0, y = +arguments[2] || 0;
      var wpx = Math.max(8, String(txt).length * fs * 0.62);
      var sx = Math.max(0, Math.round(x * sc - 2));
      var sy = Math.max(0, Math.round((y - fs * 0.8) * sc));
      var sw = Math.max(4, Math.min(cv.width - sx, Math.round(wpx * sc)));
      var sh = Math.max(4, Math.min(cv.height - sy, Math.round(fs*1.2*sc)));
      if (sx + sw <= cv.width && sy + sh <= cv.height) {
        var d = this.getImageData(sx, sy, sw, sh).data;
        var pb = pageBg(cv);
        var R=[],G=[],B=[];
        for (var i = 0; i < d.length; i += 4) {
          var pa = d[i+3] / 255;
          R.push(d[i]*pa + pb.r*(1-pa));
          G.push(d[i+1]*pa + pb.g*(1-pa));
          B.push(d[i+2]*pa + pb.b*(1-pa));
        }
        var bg = {r:med(R), g:med(G), b:med(B), a:1};
        var fg = parse(this.fillStyle);
        if (fg) {
          var ga = (this.globalAlpha == null ? 1 : this.globalAlpha);
          var a = Math.round(fg.a * ga * 100) / 100;
          var eff = blend({r:fg.r,g:fg.g,b:fg.b,a:a}, bg);
          var ratio = Math.round(cr(eff, bg)*100)/100;
          var key = String(txt).slice(0,16) + '@' + (cv.id || '?');
          var m = window.__m[key];
          if (!m) {
            window.__m[key] = m = {txt: String(txt).slice(0,16),
              canvas: cv.id || '?', n: 0,
              aMin: a, aMax: a, rAtMaxA: ratio, rMin: ratio,
              bg: [Math.round(bg.r),Math.round(bg.g),Math.round(bg.b)]};
          }
          m.n++;
          if (a > m.aMax) { m.aMax = a; m.rAtMaxA = ratio;
            m.bg = [Math.round(bg.r),Math.round(bg.g),Math.round(bg.b)]; }
          if (a < m.aMin) { m.aMin = a; }
          if (ratio < m.rMin) { m.rMin = ratio; }
        }
      }
    } catch (e) {}
    return orig.apply(this, arguments);
  };
})();
"""


def chapter_secs():
    """从 ar-data.js 读每场景各章的 at 秒数，构造 seek 计划。"""
    if not os.path.exists(DATA):
        return {}
    s = io.open(DATA, encoding='utf-8', errors='ignore').read()
    plan = {}
    for m in re.finditer(r"id:\s*'([a-z]+)'", s):
        sid = m.group(1)
        nxt = s.find("id: '", m.end())
        seg = s[m.start():nxt if nxt > 0 else len(s)]
        cm = re.search(r'chapters:\s*\[', seg)
        if not cm:
            continue
        depth, j = 1, cm.end()
        while j < len(seg) and depth > 0:
            if seg[j] == '[':
                depth += 1
            elif seg[j] == ']':
                depth -= 1
            j += 1
        arr = seg[cm.end():j - 1]
        ats = [int(x) for x in re.findall(r'at:\s*(\d+)', arr)]
        dm = re.search(r'duration:\s*(\d+)', seg)
        if not ats:
            continue
        pts = []
        for a in ats:
            pts.append(a + 3.5)     # 停在章内而非章首，让淡入走到峰值
        if dm:
            pts.append(max(pts or [0]) + 1.0)
        plan[sid] = pts
    return plan


def walk_scene(page, ch, srv, scene, pts):
    ch.navigate(page, srv.url('/index.html?cv=%s%d'
                              % (scene, int(time.time()))))
    ch.wait_for(page, "!!document.getElementById('ar-stage')", 30)
    time.sleep(1.0)
    page.eval_js("""(function(){
      var r = document.getElementById('ar');
      if (r) { r.classList.add('on'); }
      var b = document.querySelector('.ar-card .go[data-ar="%s"]')
           || document.querySelector('[data-ar="%s"]');
      if (b) { b.click(); }
      return 1;
    })()""" % (scene, scene), timeout=25)
    time.sleep(1.4)
    for sec in pts:
        page.eval_js("(function(){var a=window.__ar;"
                     "if(a&&a.seek){a.play(false);a.seek(%s);}"
                     "return 1;})()" % sec, timeout=20)
        time.sleep(1.15)
    return json.loads(page.eval_js("JSON.stringify(window.__m||{})",
                                   timeout=40))


def coverage_gap(records, floor):
    """覆盖不足时返回说明文字，足够则返回 None。

    单独成函数 + 收 floor 参数，是为了让自检能显式传值去验它真在判，
    而不是只 print 一个期望值（那会写成恒绿自检）。
    """
    if len(records) < floor:
        return ('只采到 %d 种文字（下限 %d，取自 ar-data.js 章节数），'
                '覆盖不足不能算通过' % (len(records), floor))
    return None


def chapter_count():
    """ar-data.js 里 chapters 数组的 title 总数 = 覆盖下限。"""
    if not os.path.exists(DATA):
        return 0
    s = io.open(DATA, encoding='utf-8', errors='ignore').read()
    n = 0
    for m in re.finditer(r'chapters:\s*\[', s):
        depth, j = 1, m.end()
        while j < len(s) and depth > 0:
            if s[j] == '[':
                depth += 1
            elif s[j] == ']':
                depth -= 1
            j += 1
        n += len(re.findall(r"title:\s*['\"]", s[m.end():j - 1]))
    return n


def classify(records):
    """返回 (A 类需判的, B 类豁免的)。"""
    must, exempt = [], []
    for v in records:
        (must if v['aMax'] >= STABLE_MIN else exempt).append(v)
    return must, exempt


def selftest_records():
    """S1-S4 用合成记录测分类器；S5 在调用处做端到端。"""
    bad = []
    # S1 浅字压浅底、峰值 alpha 高 -> 必须进 must 且低于阈值
    s1 = [{'txt': '注入浅字', 'aMax': 0.95, 'aMin': 0.95,
           'rAtMaxA': 1.5, 'rMin': 1.5}]
    must, _ex = classify(s1)
    ok1 = bool(must) and must[0]['rAtMaxA'] < RATIO_MIN
    print('  [%s] S1 高 alpha 低对比记录 -> 进入待判且判红'
          % ('ok' if ok1 else 'X'))
    if not ok1:
        bad.append('S1 分类器抓不到浅字压浅底')
    # S2 水印：峰值 alpha 0.14 -> 必须豁免
    s2 = [{'txt': '1929', 'aMax': 0.14, 'aMin': 0.14,
           'rAtMaxA': 1.33, 'rMin': 1.32}]
    must, ex = classify(s2)
    ok2 = (not must) and len(ex) == 1
    print('  [%s] S2 水印（峰值 a=.14、对比 1.33）-> 豁免不判红'
          % ('ok' if ok2 else 'X'))
    if not ok2:
        bad.append('S2 装饰性淡字被误判，判据会 flaky')
    # S3 正常章节名 -> 进 must 且 PASS
    s3 = [{'txt': '一九二九 · 东固会师', 'aMax': 0.92, 'aMin': 0.50,
           'rAtMaxA': 10.15, 'rMin': 3.95}]
    must, _ex = classify(s3)
    ok3 = bool(must) and must[0]['rAtMaxA'] >= RATIO_MIN
    print('  [%s] S3 章节名（峰值 a=.92、10.15:1）-> 待判且达标'
          % ('ok' if ok3 else 'X'))
    if not ok3:
        bad.append('S3 正常文字被误判')
    # S4 覆盖不足必须判红（不能把「没采到」当成通过）。
    # 这条自检本身差点写成假的：原先只是 print 一句 ok、没做任何断言，
    # 正是本仓反复抓的「恒绿自检」形态。现在真的调用覆盖判定函数比对结果。
    # 覆盖下限必须真判（不能把「没采到」当通过），且不得恒红。
    # 这里显式传 floor=10 来验函数本身，不依赖全局推导值。
    weak = [{'txt': '甲', 'aMax': 0.95, 'aMin': 0.95,
             'rAtMaxA': 12.0, 'rMin': 12.0},
            {'txt': '乙', 'aMax': 0.95, 'aMin': 0.95,
             'rAtMaxA': 11.0, 'rMin': 11.0}]
    ok4 = coverage_gap(weak, 10) is not None
    print('  [%s] S4 只采到 2 种（下限 10）-> 判覆盖不足而非通过'
          % ('ok' if ok4 else 'X'))
    if not ok4:
        bad.append('S4 覆盖不足不会被判红，阴性结论不可信')
    strong = [{'txt': 'x%d' % i, 'aMax': 0.95, 'aMin': 0.95,
               'rAtMaxA': 9.0, 'rMin': 9.0}
              for i in range(10)]
    ok4b = coverage_gap(strong, 10) is None
    print('  [%s] S4b 采到 10 种（下限 10）-> 不误判覆盖不足'
          % ('ok' if ok4b else 'X'))
    if not ok4b:
        bad.append('S4b 正常覆盖被误判，判据会恒红')
    # S6 阈值边界：峰值恰在 STABLE_MIN 上下的两条，必须一进一免。
    # 这条锁住「为什么是 0.60」这个取舍 —— 没有它，将来有人把阈值调回
    # 0.85（悄悄放宽覆盖、把部位标签又豁免掉）或 0.0（把刻意水印也算红）
    # 都不会被发现。
    edge_in = [{'txt': u'颈', 'aMax': STABLE_MIN, 'aMin': 0.07,
                'rAtMaxA': 5.17, 'rMin': 1.9}]
    edge_out = [{'txt': '1929', 'aMax': STABLE_MIN - 0.01,
                 'aMin': STABLE_MIN - 0.01, 'rAtMaxA': 1.35,
                 'rMin': 1.32}]
    m_in, _x1 = classify(edge_in)
    m_out, _x2 = classify(edge_out)
    ok6 = bool(m_in) and not m_out
    print('  [%s] S6 阈值边界：峰值=%.2f 纳入判定、%.2f 豁免'
          % ('ok' if ok6 else 'X', STABLE_MIN, STABLE_MIN - 0.01))
    if not ok6:
        bad.append('S6 阈值边界行为不符，STABLE_MIN 的取舍未被锁住')
    return bad


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
    plan = chapter_secs()
    if not plan:
        print('RESULT: SKIP  读不到章节时间点（未测不等于通过）')
        return 0
    print('=== 尺子有效性自检 ===')
    bad = selftest_records()
    if bad:
        print('RESULT: FAIL  分类器不可信：')
        for b in bad:
            print('  -', b)
        return 1

    srv = SiteServer(SITE)
    if not srv.ok:
        print('RESULT: SKIP  静态服务起不来（未测不等于通过）')
        return 0
    ch = Chrome()
    merged = {}
    e2e = None
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            page.call('Page.addScriptToEvaluateOnNewDocument',
                      {'source': HOOK})
            for scene, pts in sorted(plan.items()):
                m = walk_scene(page, ch, srv, scene, pts)
                for k, v in m.items():
                    if k not in merged or v['aMax'] > merged[k]['aMax']:
                        merged[k] = v
            # S5 端到端：在 carve-stage 上画一次已知的浅字压浅底
            e2e = json.loads(page.eval_js(r"""(function(){
              var cv = document.getElementById('carve-stage');
              if (!cv) { return JSON.stringify({missing:true}); }
              var c = cv.getContext('2d');
              var w = cv.width, h = cv.height;
              c.save();
              c.globalAlpha = 1;
              c.fillStyle = 'rgba(220,214,200,1)';
              c.fillRect(40, 40, 260, 60);          // 浅底
              c.globalAlpha = 1;
              c.fillStyle = 'rgba(246,241,231,.6)'; // 浅字，正是修前的配比
              c.font = '20px sans-serif';
              var before = Object.keys(window.__m).length;
              c.fillText('注入对照', 52, 82);
              var after = Object.keys(window.__m).length;
              var rec = null;
              for (var k in window.__m) {
                if (window.__m[k].txt === '注入对照') { rec = window.__m[k]; }
              }
              c.restore();
              return JSON.stringify({added: after - before, rec: rec});
            })()""", timeout=30))
        finally:
            page.close()
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()

    rec = (e2e or {}).get('rec')
    ok5 = bool(rec) and rec['rAtMaxA'] < 1.5
    print('  [%s] S5 端到端：画一次「浅字压浅底」探针量得 %s:1（应 <1.5）'
          % ('ok' if ok5 else 'X',
             rec['rAtMaxA'] if rec else '无读数'))
    if not ok5:
        print('RESULT: FAIL  像素管线未复现已知低对比，读数不可信')
        return 1
    print()

    must, exempt = classify(list(merged.values()))
    print('=== canvas 文字对比度（三场景去重 %d 种）===' % len(merged))
    for v in sorted(merged.values(), key=lambda x: x['rAtMaxA']):
        cls = 'A 承担信息' if v in must else 'B 装饰/淡变'
        print('  %-16s %-10s a%.2f~%.2f 对比 %6.2f:1 底 %-15s %s'
              % (v['txt'], v['canvas'], v['aMin'], v['aMax'],
                 v['rAtMaxA'], str(v['bg']), cls))
    print()
    print('=== 判定 ===')
    fails = []
    # 下限取「ar-data.js 章节总数」（每章至少一个标签必须出现在画面里），
    # 推导失败才退回 MIN_FLOOR；不再用拍脑袋的固定数。
    chs = chapter_count()
    floor = chs if chs >= MIN_FLOOR else MIN_FLOOR
    print('  覆盖下限：%d 种（取自 ar-data.js 章节数 %d；推导失败才用底 %d）'
          % (floor, chs, MIN_FLOOR))
    gap = coverage_gap(list(merged.values()), floor)
    if gap:
        fails.append(gap)
    for v in sorted(must, key=lambda x: x['rAtMaxA']):
        if v['rAtMaxA'] < RATIO_MIN:
            fails.append('「%s」(canvas %s) 峰值 alpha %.2f 下对比仅 '
                         '%.2f:1 < %.1f:1，底 %s'
                         % (v['txt'], v['canvas'], v['aMax'],
                            v['rAtMaxA'], RATIO_MIN, v['bg']))
    print('  A 类（承担信息）%d 种；B 类豁免 %d 种'
          % (len(must), len(exempt)))
    if fails:
        for x in fails:
            print('  -', x)
        print()
        print('RESULT: FAIL  %d 项 canvas 文字可读性问题' % len(fails))
        return 1
    print('  无覆盖缺口')
    print()
    print('RESULT: PASS  三场景 %d 种 canvas 文字中 %d 种承担信息的'
          '全部 >= %.1f:1（最低 %.2f:1），%d 种淡变/装饰按设计豁免；'
          '端到端注入对照亦被像素级量出低对比（管线有牙）'
          % (len(merged), len(must), RATIO_MIN,
             min(v['rAtMaxA'] for v in must), len(exempt)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
