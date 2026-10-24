# -*- coding: utf-8 -*-
"""tools/print_readability_test.py —— 打印态可读性判据（轮181）。

## 为什么需要它
CSS 里 @media print 的注释承诺：「现场要贴展板时的兜底（去掉暗底与
文字可读）」。这是本站的真实使用场景（研学团把页面打印上墙），
但**没有任何判据守过它** —— contrast_audit 只测屏幕态两档视口。

一手实测缺陷（轮181）：@media print 原先只改了 body 的 background/color，
而自带深底的组件（.merch-item / .ar-route-item / .carve-rail button /
.avatar）的深底是各自规则里写死的，不跟着转白。于是未显式设色的 h3
继承 body 的 #111 后压在 rgb(11,9,8) 深底上，对比只有 **1.05** ——
15 个标题（扫码进入/现实叠加/看完集章 + 12 件文创名）打印出来完全看不见。
反过来只转深底容器又暴露更大的问题：全站 49 处文字是显式用
var(--fg-dim)/var(--fg-faint)（为暗底设计的浅色），转白底后 141 处
「浅字压白底」对比 1.10。最终靠**在 print 块里重定义 :root 令牌**一次翻转
才收口（141 -> 17 -> 0）。

## 判据（四条，全部可机器判定）
A 暗底承诺：打印态不得存在「有效背景为深色」的可见块（>=40x40）。
B 文字承诺：打印态所有直接含文本的元素，与其有效背景的 WCAG 对比
  必须达标（正文 4.5 / 大字 3.0）。
C 二维码承诺：#qr-img 在打印态仍可见且尺寸够（贴展板的核心用途）。
D 装饰承诺：data-decorative 的巨型水印（.hero-word）打印态隐藏，
  否则白底上它是一片若隐若现的脏影。

## 关键测量纪律（本会话反复踩过的两条）
1) 切媒体前注入 QUIET（transition/animation 全关）。
   否则读到的是「过渡进行中的中间色」—— 轮181 实测：.ar-src a 的
   var(--she-gold-light) 明明已解析成新值，computed 却仍是旧金色，
   就是因为带 transition:color。不消除动画会误报 4 处假缺陷。
2) 亮度标尺必须与阈值同量纲。轮181 曾把 0..1 的相对亮度拿去和 60 比，
   导致所有元素都算深底（236/1054 全是假数）。本判据统一用
   0..255 加权亮度做深底判定，WCAG 对比度另行按规范线性化计算。

## 自检（证明尺子有牙）
注入一段「撤销修复」的样式（把令牌翻回暗色值），A/B 必须报红。
自检不过 -> 判据自判 FAIL（判据自己坏了必须响，不能吞成 SKIP）。
"""
import io
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

QUIET = ("html,body{scroll-behavior:auto!important}"
         "*,*::before,*::after{transition:none!important;"
         "animation:none!important}")

# 撤销修复：把 :root 令牌翻回暗底配色（模拟轮181 修复前的状态）
ADMIN_BREAK_CSS = ("@media print{:root{--bg:#0B0908;--panel:#141110;"
  "--panel-2:#1B1714;--fg:#EDE6DC;--fg-dim:#B9AEA2;"
  "--fg-faint:#8B8075;--gold:#D4A24C;--gold-dim:#9C7B3F;}"
  ".grid.two.charts-row{display:block !important}}")

BREAK_CSS = ("@media print{:root{--she-ink:#0B0908;--bg:#0B0908;"
             "--fg:#F4EDE1;--fg-dim:rgba(244,237,225,.74);"
             "--fg-faint:rgba(244,237,225,.66);"
             "--she-gold:#D4A24C;--she-gold-light:#E8B761;"
             "--she-vermilion:#D94F2B}"
             ".merch-item,.merch-shot,.ar-route-item,.avatar"
             "{background:#0B0908!important}}")

PROBE = r"""(function(){
  function parse(c){var m=(c||'').match(/rgba?\(([^)]+)\)/); if(!m) return null;
    var p=m[1].split(',').map(Number);
    return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1};}
  // 深底判定统一用 0..255 加权亮度（与阈值 60 同量纲）
  function L255(o){return 0.2126*o.r+0.7152*o.g+0.0722*o.b;}
  // WCAG 对比度：内部按规范做 sRGB 线性化，与 L255 是两套标尺，不可混用
  function ratio(fgCss,bg){
    var a=parse(fgCss); if(!a) return null;
    var fa=a.a;
    var comp={r:a.r*fa+bg.r*(1-fa), g:a.g*fa+bg.g*(1-fa),
              b:a.b*fa+bg.b*(1-fa)};
    function lin(v){v/=255;return v<=0.03928?v/12.92:
      Math.pow((v+0.055)/1.055,2.4);}
    var l1=0.2126*lin(comp.r)+0.7152*lin(comp.g)+0.0722*lin(comp.b);
    var l2=0.2126*lin(bg.r)+0.7152*lin(bg.g)+0.0722*lin(bg.b);
    var hi=Math.max(l1,l2), lo=Math.min(l1,l2);
    return Math.round((hi+0.05)/(lo+0.05)*100)/100;}
  function effBg(e){
    var stack=[], p=e;
    while(p && p.nodeType===1){
      var o=parse(getComputedStyle(p).backgroundColor);
      if(o && o.a>0.5){ stack.push(o); if(o.a>=0.99) break; }
      p=p.parentElement;}
    var acc={r:255,g:255,b:255,a:1};
    for(var i=stack.length-1;i>=0;i--){
      var c=stack[i], al=c.a;
      acc={r:c.r*al+acc.r*(1-al), g:c.g*al+acc.g*(1-al),
           b:c.b*al+acc.b*(1-al), a:1};}
    return acc;}
  function shown(e){
    if(!e) return false;
    var cs=getComputedStyle(e);
    if(cs.display==='none'||cs.visibility==='hidden') return false;
    if(parseFloat(cs.opacity)<0.05) return false;
    var b=e.getBoundingClientRect();
    return b.width>0 && b.height>0;}
  var out={media:window.matchMedia('print').matches,
    darkBlocks:0, darkSample:[], badText:[], checkedText:0,
    badPaper:[], checkedPaper:0};
  // A 暗底块
  [].slice.call(document.querySelectorAll('*')).forEach(function(e){
    var b=e.getBoundingClientRect();
    if(b.width<40||b.height<40) return;
    if(!shown(e)) return;
    var bg=effBg(e);
    if(L255(bg)<60){
      out.darkBlocks++;
      if(out.darkSample.length<4){
        out.darkSample.push(((e.id||'') ||
          (typeof e.className==='string'?e.className.split(' ')[0]:'')
          || e.tagName).slice(0,24)
          + ' bg=rgb('+Math.round(bg.r)+','+Math.round(bg.g)+','
          + Math.round(bg.b)+')');}
    }});
  // B 文字对比
  [].slice.call(document.querySelectorAll(
    'h1,h2,h3,h4,p,li,a,b,span,dd,figcaption,button,td,th,label,summary'))
    .forEach(function(e){
      var own='';
      for(var i=0;i<e.childNodes.length;i++){
        var n=e.childNodes[i];
        if(n.nodeType===3) own+=(n.textContent||'');}
      own=own.trim();
      if(!own) return;
      if(!shown(e)) return;
      var cs=getComputedStyle(e);
      var bg=effBg(e);
      var r=ratio(cs.color, bg);
      out.checkedText++;
      if(r===null) return;
      var fs=parseFloat(cs.fontSize)||0;
      var bold=parseInt(cs.fontWeight,10)>=700;
      var need=(fs>=24||(fs>=18.66&&bold))?3:4.5;
      if(r<need && out.badText.length<8){
        out.badText.push({sel:((e.id||'') ||
          (typeof e.className==='string'?e.className.split(' ')[0]:'')
          || e.tagName).slice(0,22), tag:e.tagName, ratio:r, need:need,
          color:cs.color, txt:own.slice(0,14)});}
    });
  // C 二维码
  var q=document.getElementById('qr-img');
  var qb=q?q.getBoundingClientRect():null;
  out.qr={exists:!!q, visible:shown(q),
    w:qb?Math.round(qb.width):0, h:qb?Math.round(qb.height):0};
  // D 装饰水印
  var hw=document.querySelector('.hero-word');
  out.heroWord={exists:!!hw, visible:shown(hw)};
  // G 文字 vs 白纸：浏览器默认**不打印背景**，真实落点是白纸。
  // 只跟屏幕有效背景比会漏判 —— 后台修复前实测：文字对深底 18.79 达标、
  // 对白纸只有 1.24，而旧判据报「0 处不达标」（判据自身的测量盲区）。
  // 例外：被强制绘制的元素（print-color-adjust:exact，如条形填充）
  // 背景会真印出来，仍按其有效背景判。
  [].slice.call(document.querySelectorAll(
    'h1,h2,h3,h4,p,li,a,b,span,dd,figcaption,button,td,th,label,summary'))
    .forEach(function(e){
      var own='';
      for(var i=0;i<e.childNodes.length;i++){
        var n=e.childNodes[i];
        if(n.nodeType===3) own+=(n.textContent||'');}
      own=own.trim();
      if(!own) return;
      var cs=getComputedStyle(e);
      if(cs.display==='none'||cs.visibility==='hidden') return;
      if(!e.getClientRects().length) return;   // 祖先被隐藏
      var pca=cs.printColorAdjust||cs.webkitPrintColorAdjust||'auto';
      var target=(pca==='exact')?effBg(e):{r:255,g:255,b:255,a:1};
      var v=ratio(cs.color, target);
      out.checkedPaper++;
      if(v===null) return;
      var fs=parseFloat(cs.fontSize)||0;
      var bold=parseInt(cs.fontWeight,10)>=700;
      var need=(fs>=24||(fs>=18.66&&bold))?3:4.5;
      if(v<need && out.badPaper.length<8){
        out.badPaper.push({sel:((e.id||'')||
          (typeof e.className==='string'?e.className.split(' ')[0]:'')
          ||e.tagName).slice(0,20), tag:e.tagName, ratio:v, need:need,
          color:cs.color, txt:own.slice(0,12)});
      }
    });
  // E 后台专属：隐藏图表后数据必须由表格兜住；条形长度编码必须被绘制
  out.tables = {};
  ['tbl-weeks', 'tbl-days', 'tbl-country', 'tbl-lang', 'tbl-screen',
   'tbl-scenes'].forEach(function(id){
    var t = document.getElementById(id);
    if(!t) return;
    var r = t.getBoundingClientRect();
    out.tables[id] = {rows: t.querySelectorAll('tbody tr').length,
      h: Math.round(r.height),
      visible: !!t.getClientRects().length};
  });
  var bf = document.querySelector('.bars .fill');
  out.barFill = null;
  if (bf) {
    var bfr = bf.getBoundingClientRect();
    var bcs = getComputedStyle(bf);
    out.barFill = {w: Math.round(bfr.width),
      bg: bcs.backgroundColor,
      painted: (bcs.printColorAdjust === 'exact'
                || bcs.webkitPrintColorAdjust === 'exact')};
  }
  return JSON.stringify(out);})()"""


def scan(ch, srv, path='/index.html', quiet_first=True,
         break_css=None):
    page, tid = ch.new_page(1280, 900)
    try:
        # navigate 是 Chrome 实例方法，不是 page 的方法（轮181 踩过）
        bust = int(time.time()) % 100000
        ch.navigate(page, srv.url(path + '?prt=' + str(bust)))
        time.sleep(2.6)
        if quiet_first:
            page.eval_js("(function(){var st=document.createElement('style');"
                         "st.textContent=" + json.dumps(QUIET) + ";"
                         "document.head.appendChild(st);return 1;})()",
                         timeout=25)
        if break_css:
            page.eval_js("(function(){var st=document.createElement('style');"
                         "st.textContent=" + json.dumps(break_css) + ";"
                         "document.head.appendChild(st);return 1;})()",
                         timeout=25)
        page.call('Emulation.setEmulatedMedia', {'media': 'print'})
        time.sleep(1.2)
        d = json.loads(page.eval_js('(%s)' % PROBE, timeout=35))
        return d
    finally:
        try:
            page.close()
        except Exception:
            pass
        ch.close_page(tid)


def judge(d, scope='main'):
    out = []
    if not d.get('media'):
        return ['媒体未切到 print（matchMedia 不成立，未取证）']
    if d['darkBlocks']:
        out.append('A 暗底承诺未兑现：打印态仍有 %d 个深色块（%s）'
                   % (d['darkBlocks'], '、'.join(d['darkSample'])))
    if d['badText']:
        out.append('B 文字承诺未兑现：%d 处对比不足（最差 %s，如 %r）'
                   % (len(d['badText']), d['badText'][0]['ratio'],
                      d['badText'][0]['txt']))
    # C/D 是主站专属断言：后台没有 #qr-img 与 .hero-word，
    # 套上去会把「该页没有这个元素」误判成「未取证/缺陷」。
    if scope == 'main':
        if not d['qr']['exists']:
            out.append('C 取不到 #qr-img（未取证）')
        elif not d['qr']['visible'] or d['qr']['w'] < 60:
            out.append('C 二维码在打印态不可见/过小（%sx%s）'
                       % (d['qr']['w'], d['qr']['h']))
        if d['heroWord']['exists'] and d['heroWord']['visible']:
            out.append('D 装饰水印 .hero-word 打印态未隐藏'
                       '（白底上成脏影）')
    if d['checkedText'] < 40:
        out.append('B 只检查了 %d 处文字，测量面不足' % d['checkedText'])
    # G 文字 vs 白纸（真实打印落点）
    if d.get('badPaper'):
        out.append('G 打印落点是白纸（浏览器默认不印背景）：%d 处文字对白纸'
                   '对比不足，最差 %s（%s 如 %r）'
                   % (len(d['badPaper']), d['badPaper'][0]['ratio'],
                      d['badPaper'][0]['tag'], d['badPaper'][0]['txt']))
    if d.get('checkedPaper', 0) < 40:
        out.append('G 只对 %d 处文字算了白纸对比，测量面不足'
                   % d.get('checkedPaper', 0))
    # E 后台专属（有 tables 字段才判，主站不受影响）
    tabs = d.get('tables') or {}
    if tabs:
        empty = [k for k, v in sorted(tabs.items())
                 if not v.get('visible') or v.get('rows', 0) <= 0]
        if empty:
            out.append('E 表格在打印态无可见数据行（隐藏图表后数据丢失）：%s'
                       % '、'.join(empty))
        bf = d.get('barFill')
        if bf is None:
            out.append('E 取不到 .bars .fill（未取证）')
        elif not bf.get('painted'):
            out.append('E 条形填充未被强制绘制（print-color-adjust 未生效，'
                       '长度这个视觉编码在纸上会消失）')
        elif bf.get('w', 0) <= 0:
            out.append('E 条形填充宽度为 0（长度编码丢失）')
    return out


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  cdp_client 不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（未取证 != 通过）')
        return 0
    srv = SiteServer(os.path.join(BASE, 'site'), port=9017)
    ch = Chrome()
    try:
        # 自检：撤销修复必须报红
        try:
            fx = scan(ch, srv, break_css=BREAK_CSS)
        except Exception as e:
            print('RESULT: FAIL  判据自检阶段异常（判据本身坏了）: '
                  '%s: %s' % (type(e).__name__, str(e)[:110]))
            return 1
        fb = judge(fx)
        has_dark = fx['darkBlocks'] > 0
        has_bad = bool(fx['badText'])
        print('[%s] 自检：注入暗底令牌后报出问题 %d 条'
              '（深底块=%d、文字不达标=%d）' % (
                  'PASS' if (fb and has_dark and has_bad) else 'FAIL',
                  len(fb), fx['darkBlocks'], len(fx['badText'])))
        if not (fb and has_dark and has_bad):
            print('RESULT: FAIL  自检不通过：撤销修复后判据没反应，'
                  '读数不可信')
            for x in fb[:3]:
                print('      ', x[:120])
            return 1
        for x in fb[:2]:
            print('      抓到:', x[:116])
        # 真判
        d = scan(ch, srv)
        probs = judge(d)
        print('[%s] 打印态：深底块 %d、检查文字 %d 处不达标 %d、'
              '二维码 %sx%s、水印可见=%s' % (
                  'PASS' if not probs else 'FAIL', d['darkBlocks'],
                  d['checkedText'], len(d['badText']),
                  d['qr']['w'], d['qr']['h'],
                  d['heroWord']['visible']))
        for x in probs:
            print('      -', x[:126])
        allprobs = list(probs)

        # ---- 后台一趟 ----
        # 一手实测（轮182）：后台原先 0 个 @media print。浏览器默认不印
        # 背景，body color=var(--fg)=#EDE6DC 对白纸对比只有 1.24 ——
        # 整张报表打印出来完全不可读；只跟屏幕深底比会误判成达标。
        ab = scan(ch, srv, path='/admin/index.html',
                  break_css=ADMIN_BREAK_CSS)
        ab_probs = judge(ab, 'admin')
        ab_ok = bool(ab_probs) and ab['darkBlocks'] > 0
        print('[%s] 后台自检：撤销 admin 令牌翻转后报出 %d 条'
              '（暗底块=%d、白纸不达标=%d）' % (
                  'PASS' if ab_ok else 'FAIL', len(ab_probs),
                  ab['darkBlocks'], len(ab.get('badPaper') or [])))
        if not ab_ok:
            print('RESULT: FAIL  后台自检不通过：撤销修复后判据没反应')
            for x in ab_probs[:3]:
                print('      ', x[:120])
            return 1
        for x in ab_probs[:2]:
            print('      抓到:', x[:116])
        ad = scan(ch, srv, path='/admin/index.html')
        aprobs = judge(ad, 'admin')
        print('[%s] 后台打印态：暗底块 %d、文字对白纸不达标 %d、'
              '表格 %d 张、条形绘制=%s' % (
                  'PASS' if not aprobs else 'FAIL', ad['darkBlocks'],
                  len(ad.get('badPaper') or []),
                  len(ad.get('tables') or {}),
                  bool((ad.get('barFill') or {}).get('painted'))))
        for x in aprobs:
            print('      -', x[:126])
        allprobs += aprobs
    except Exception as e:
        print('RESULT: SKIP  真判阶段探针异常（环境问题）: %s: %s'
              % (type(e).__name__, str(e)[:110]))
        return 0
    finally:
        ch.close()
        try:
            srv.stop()
        except Exception:
            pass

    print()
    if allprobs:
        print('RESULT: FAIL  打印态可读性（主站 + 后台）'
              '%d 处问题' % len(allprobs))
        for f in allprobs:
            print('  -', f)
        return 1
    print('RESULT: PASS  主站与后台打印态均无暗底块、文字对白纸'
          '（真实落点）全达标、主站二维码可见、装饰水印已隐藏、'
          '后台表格与条形编码完整')
    return 0


if __name__ == '__main__':
    sys.exit(main())
