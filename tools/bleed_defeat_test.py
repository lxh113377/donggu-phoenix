# -*- coding: utf-8 -*-
r"""tools/bleed_defeat_test.py —— 破格出血是否被祖先 overflow 静默抵消。

## 为什么需要（轮159 新开维度）
「破格」是本仓有意用的排版手法：让画布左右越出正文栏，视觉上更展陈。
实现方式是负外边距（margin-inline:calc(var(--gut) * -1)）。
但负外边距打在**被祖先 overflow:hidden 包着的元素**上时，
布局照常算出更宽的盒子，**可见部分却被裁回原宽** —— 出血静默失效。

这类缺陷的特征是「所有常规判据都看不见」：
  · 没有横向滚动条（内容被裁而不是溢出）
  · DOM 结构正常、无报错
  · 对比度/字号/触控目标全部达标
  · 响应式判据只查「有没有溢出」，而它恰好是溢出被抹平
轮159 实测：桌面每边被切 48px、手机 18px，79 条判据一条都没报。
是我截屏实读时偶然发现的。所以把它变成判据。

## 判据
元素同时满足三条即判红：
  1. 计算后存在负的 inline 外边距（破格意图）
  2. 最近的 overflow 为 hidden/clip 的祖先（auto/scroll 不算 —— 那是可滚的
     滚动容器，用户能自己拖出来，不是静默裁切）
  3. 自身边框盒超出该祖先的内容盒（= 超出部分真的看不见）

## 为什么第 3 条不可省
有负外边距 + 祖先 overflow:hidden 但元素**并未**超出祖先（例如祖先自己也
向外破格、或负边距被 padding 吸收），那是正常布局，不该报。
只有「真的被切掉一块」才是缺陷。

用法：python tools/bleed_defeat_test.py
"""
import io
import json
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
sys.path.insert(0, os.path.join(BASE, 'tools'))

VIEWPORTS = [(1440, 900, '桌面'), (1024, 768, '笔记本'),
             (768, 1024, '平板'), (390, 844, '手机')]
PAGES = [('主站', '/index.html'), ('后台', '/admin/index.html')]

PROBE = r"""(function(){
  function num(v){var n=parseFloat(v);return isNaN(n)?0:n;}
  var hits=[];
  var all=[].slice.call(document.querySelectorAll('body *'));
  all.forEach(function(el){
    var cs=getComputedStyle(el);
    var ml=num(cs.marginLeft), mr=num(cs.marginRight);
    if(ml>=0 && mr>=0) return;                 // 无破格意图
    var r=el.getBoundingClientRect();
    if(r.width<1 || r.height<1) return;
    // 最近一个 overflow 为 hidden/clip 的祖先
    var p=el.parentElement, clip=null;
    while(p && p!==document.body.parentElement){
      var pc=getComputedStyle(p);
      var ox=pc.overflowX, oy=pc.overflowY;
      if(ox==='hidden'||ox==='clip'||oy==='hidden'||oy==='clip'){
        clip=p;break;
      }
      if(ox==='auto'||ox==='scroll'||oy==='auto'||oy==='scroll') return;
      p=p.parentElement;
    }
    if(!clip) return;                          // 没有裁切祖先，出血自由
    var cr=clip.getBoundingClientRect();
    var pcs=getComputedStyle(clip);
    var padL=num(pcs.paddingLeft), padR=num(pcs.paddingRight);
    var inner={l:cr.left+padL, r:cr.right-padR};
    var outL=Math.max(0,Math.round(inner.l-r.left));
    var outR=Math.max(0,Math.round(r.right-inner.r));
    if(outL<=1 && outR<=1) return;             // 并未真的超出，正常布局
    hits.push({tag:el.tagName.toLowerCase(),
      cls:(typeof el.className==='string'?el.className:'').slice(0,36),
      id:el.id||'', ml:ml, mr:mr,
      w:Math.round(r.width), outL:outL, outR:outR,
      clipCls:(typeof clip.className==='string'
               ?clip.className:'').slice(0,30)});
  });
  return JSON.stringify(hits);
})()"""


def scan(chrome_dir=None):
    """返回 (每视口的命中列表, 覆盖到的视口数)。"""
    from cdp_client import Chrome, SiteServer, find_chrome
    if not find_chrome():
        return None, 0
    out, seen = [], 0
    srv = SiteServer(SITE, port=8971)
    ch = Chrome()
    try:
        for vw, vh, vlabel in VIEWPORTS:
            for plabel, path in PAGES:
                page, tid = ch.new_page(vw, vh)
                try:
                    srv.url(path)
                    ch.navigate(page, srv.url(path + '?bleed=1'))
                    time.sleep(2.2)
                    if 'index.html' == path.rsplit('/', 1)[-1] \
                            and plabel == '主站':
                        # 让隐藏界面也参与（AR 面板展开后内部布局不同）
                        try:
                            page.eval_js(
                                "var a=document.getElementById('ar');"
                                "if(a)a.classList.add('on')", timeout=25)
                            time.sleep(0.6)
                        except Exception:
                            pass
                    hits = json.loads(page.eval_js(PROBE, timeout=30))
                    seen += 1
                    for h in hits:
                        h['at'] = '%s %dx%d / %s' % (vlabel, vw, vh, plabel)
                        out.append(h)
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
                    ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()
    return out, seen


# ---------------- 自检：证明判据有牙 ----------------
def selftest():
    """两项都必须成立，否则判据不可信。

    S1 反向验证（造一个真缺陷）：负外边距元素被 overflow:hidden 祖先
       裁掉 —— 必须报出。这是轮159 那个真实缺陷的最小复刻。
    S2 不误伤（合法破格）：出血层自己带负边距、祖先不裁 —— 必须不报。
       这正是修好之后的 .carve-clip 形态。
    S3 不误伤（滚动容器）：祖先 overflow-x:auto 时用户能自己拖出来，
       不属静默裁切 —— 必须不报。
    """
    from cdp_client import Chrome, SiteServer, find_chrome
    if not find_chrome():
        print('  自检跳过（无 chrome）')
        return None
    fx = os.path.join(SITE, '_bleed_fixture.html')
    io.open(fx, 'w', encoding='utf-8', newline='').write(
        '<!doctype html><html><head><meta charset="utf-8">'
        '<style>'
        'body{margin:0;background:#000}'
        '.wrap8{width:400px;margin:0 auto;padding:0 40px}'
        # S1 复刻真缺陷：裁切框不向外扩，子元素负边距被裁
        '.clipA{position:relative;overflow:hidden;background:#111}'
        '.bleedA{margin-inline:-40px;height:60px;background:#222}'
        # S2 修好后的形态：裁切框自己负边距，子元素与它等宽
        '.clipB{position:relative;overflow:hidden;margin-inline:-40px;'
        'background:#111;height:60px}'
        '.kidB{width:100%;height:60px;background:#333}'
        # S3 滚动容器：能拖出来，不算静默裁切
        '.clipC{position:relative;overflow-x:auto;background:#111}'
        '.bleedC{margin-inline:-40px;height:60px;background:#444}'
        '</style></head><body>'
        '<div class="wrap8">'
        '<div class="clipA"><div class="bleedA" id="s1"></div></div>'
        '<div class="clipB"><div class="kidB" id="s2"></div></div>'
        '<div class="clipC"><div class="bleedC" id="s3"></div></div>'
        '</div></body></html>')
    bad = []
    srv = SiteServer(SITE, port=8972)
    ch = Chrome()
    try:
        page, tid = ch.new_page(1024, 700)
        try:
            ch.navigate(page, srv.url('/_bleed_fixture.html'))
            time.sleep(1.2)
            hits = json.loads(page.eval_js(PROBE, timeout=30))
            ids = {h['cls'].split()[0] for h in hits}
            got = [h for h in hits if h['cls'].startswith('bleedA')]
            print('  [%s] S1 复刻真缺陷（负边距被 overflow:hidden 裁掉）'
                  '-> %s' % ('ok' if got else 'X',
                             '报出 %d 处（切掉 %d/%dpx）'
                             % (len(got), got[0]['outL'], got[0]['outR'])
                             if got else '没报出（判据恒绿）'))
            if not got:
                bad.append('S1 真缺陷没被抓到，判据可能恒绿')
            s2 = [h for h in hits if h['cls'].startswith('bleed')
                  and 'clipB' in h['clipCls']]
            s2b = [h for h in hits if h['clipCls'].startswith('clipB')]
            print('  [%s] S2 合法破格（裁切框自己外扩）-> %s'
                  % ('ok' if not s2b else 'X',
                     '不误伤' if not s2b else '误报 %d 处' % len(s2b)))
            if s2b:
                bad.append('S2 把合法破格误判成缺陷')
            s3 = [h for h in hits if h['clipCls'].startswith('clipC')]
            print('  [%s] S3 滚动容器（用户能拖出来）-> %s'
                  % ('ok' if not s3 else 'X',
                     '不误伤' if not s3 else '误报 %d 处' % len(s3)))
            if s3:
                bad.append('S3 把可滚动容器误判成静默裁切')
        finally:
            try:
                page.close()
            except Exception:
                pass
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()
        try:
            os.remove(fx)
        except OSError:
            pass
    return bad


def main():
    print('=== 破格出血被静默抵消（负外边距 + overflow:hidden 祖先）===')
    st = selftest()
    if st is None:
        print('RESULT: SKIP  找不到 chrome（环境问题，非判据通过）')
        return 0
    if st:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in st:
            print('  -', b)
        return 1
    print()
    hits, seen = scan()
    if hits is None:
        print('RESULT: SKIP  无 chrome')
        return 0
    print('=== 全站扫描（覆盖 %d 个 视口×页面 组合）===' % seen)
    if seen < len(VIEWPORTS) * len(PAGES):
        print('RESULT: FAIL  只覆盖到 %d/%d 组合，覆盖不足不能算通过'
              % (seen, len(VIEWPORTS) * len(PAGES)))
        return 1
    if not hits:
        print('  未发现「破格被裁」')
        print()
        print('RESULT: PASS  所有负外边距破格都真的可见地越出了栏，'
              '且三项自检证明该报的报得出、合法破格与滚动容器不误伤')
        return 0
    print('发现 %d 处出血被静默抵消：' % len(hits))
    for h in hits[:12]:
        print('  - %s: %s.%s 负边距 %g/%g 宽 %d，被 %s 裁掉 左%d 右%dpx'
              % (h['at'], h['tag'], h['cls'] or h['id'], h['ml'], h['mr'],
                 h['w'], h['clipCls'], h['outL'], h['outR']))
    print()
    print('RESULT: FAIL  %d 处破格意图被祖先 overflow 抵消'
          '（布局变宽但可见宽度未变，常规判据看不见）' % len(hits))
    return 1


if __name__ == '__main__':
    sys.exit(main())
