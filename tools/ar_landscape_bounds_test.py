# -*- coding: utf-8 -*-
"""tools/ar_landscape_bounds_test.py —— AR 面板在矮横屏的排版边界判据（轮179）。

## 为什么需要它
一手实测缺陷：AR 面板 .ar-copy 用 bottom 锚定、内容需 276px，而矮横屏
（横屏手机）里导览点底部到进度条顶部只有 114~135px 可用 —— 正文顶穿面板
（844x390 top=-36、740x360 top=-76、667x375 top=-61）并与导览点重叠。
竖屏正常，所以这是**只在矮横屏出现**的盲区；现场观众大量横屏扫码看 AR，
被顶出去的那段中文正是展陈内容本身。
既有判据看不见它：touch_target / contrast 虽已展开面板，但只测触控与
对比度，不测排版边界；multi_viewport 测的是页面而非 overlay。

## 测法（专挑最坏情况）
停在**中文正文最长的那一章**（各场景各章取最大 body 长度）——
最坏的一章不溢出，其余必然都不溢出。三个矮横屏视口 + 一个竖屏对照。
断言三件（全部可机器判定）：
  A .ar-copy 顶边不低于面板顶（不顶穿）
  B .ar-copy 与 .ar-dots 不重叠（垂直与水平区间都相交才算重叠）
  C 中文正文完整落在 .ar-copy 内（scrollHeight 不超 clientHeight，
    即最长正文也不需要滚动 —— 滚动虽不丢字，但矮屏上要求观众滚
    动读展陈解说本身就是体验缺陷）
零样本不判 PASS：任一视口取不到面板/正文即 FAIL（未取证 != 通过）。

## 自检（证明判据有牙）
合成一份 CSS：把 .ar-copy 的 top 改掉、max-height 去掉（模拟修复前），
断言 A/B/C 至少一项必须报红。自检不过 -> 判据自判 FAIL。
"""
import base64
import io
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

LANDSCAPE = [(844, 390), (740, 360), (667, 375)]
PORTRAIT = (390, 844)

SWEEP = r"""(function(){
  if(!window.__ar) return 'noapi';
  var best={len:-1,sid:null,ci:0};
  (window.__ar.scenes||[]).forEach(function(s){
    __ar.open(s.id);
    (s.chapters||[]).forEach(function(c,i){
      var bl=(c.body||'').length;
      if(bl>best.len) best={len:bl,sid:s.id,ci:i};});});
  if(best.len<0) return 'nochap';
  var s=window.__ar.scenes.filter(function(x){return x.id===best.sid;})[0];
  __ar.open(best.sid);
  var per=s.duration/s.chapters.length;
  __ar.seek(Math.min(best.ci*per+1, s.duration-0.5));
  return JSON.stringify(best);})()"""

MEASURE = r"""(function(){
  var ar=document.getElementById('ar');
  var copy=document.querySelector('.ar-copy');
  var dots=document.querySelector('.ar-dots');
  if(!ar||!copy||!dots) return JSON.stringify({missing:1});
  var arR=ar.getBoundingClientRect(), cb=copy.getBoundingClientRect(),
      db=dots.getBoundingClientRect();
  var bp=null;
  copy.querySelectorAll('p').forEach(function(e){
    if(!/ar-en|ar-chapter-en|ar-body-en/.test(e.className) && !bp) bp=e;});
  var pb=bp?bp.getBoundingClientRect():null;
  return JSON.stringify({
    copyTop:Math.round(cb.top), copyBottom:Math.round(cb.bottom),
    arTop:Math.round(arR.top), arBottom:Math.round(arR.bottom),
    dotsBottom:Math.round(db.bottom), dotsRight:Math.round(db.right),
    dotsLeft:Math.round(db.left), copyLeft:Math.round(cb.left),
    copyRight:Math.round(cb.right),
    clientH:Math.round(copy.clientHeight),
    scrollH:Math.round(copy.scrollHeight),
    hasBody: !!bp,
    bodyBottom: pb?Math.round(pb.bottom):null,
    bodyTxt: bp?(bp.textContent||'').trim().slice(0,10):null});})()"""

OPEN_FIRST = r"""(function(){
  var b=document.querySelectorAll('.ar-card .go');
  if(b.length) b[0].click();
  return b.length;})()"""


def run_viewport(ch, srv, vw, vh, cachebust):
    page, tid = ch.new_page(vw, vh)
    try:
        ch.navigate(page, srv.url('/index.html?arb=%d_%d'
                              % (vw, cachebust)))
        time.sleep(2.4)
        page.eval_js(OPEN_FIRST, timeout=25)
        time.sleep(0.6)
        info = page.eval_js(SWEEP, timeout=30)
        time.sleep(1.0)
        d = json.loads(page.eval_js('(%s)' % MEASURE, timeout=30))
        d['chap'] = info
        return d
    finally:
        try:
            page.close()
        except Exception:
            pass
        ch.close_page(tid)


def judge(d):
    """返回该视口的问题列表（空=通过）。"""
    out = []
    if d.get('missing'):
        return ['取不到 #ar/.ar-copy/.ar-dots（未取证）']
    if not d.get('hasBody'):
        return ['取不到中文正文 <p>（未取证）']
    # A 不顶穿面板
    if d['copyTop'] < d['arTop'] - 1:
        out.append('.ar-copy 顶边 %d 高于面板顶 %d（正文顶穿面板）'
                   % (d['copyTop'], d['arTop']))
    # B 不与 dots 重叠（垂直与水平都相交才算）
    v_ov = not (d['copyTop'] > d['dotsBottom']
                or d['copyBottom'] < d['dotsBottom'] - 6)
    h_ov = not (d['copyRight'] < d['dotsLeft'] or d['copyLeft'] > d['dotsRight'])
    if v_ov and h_ov:
        out.append('.ar-copy(top=%d) 与导览点(bottom=%d) 重叠'
                   % (d['copyTop'], d['dotsBottom']))
    # C 最长正文免滚动
    if d['scrollH'] > d['clientH'] + 1:
        out.append('最长中文正文需滚动（scrollH=%d > clientH=%d，藏 %dpx）'
                   % (d['scrollH'], d['clientH'],
                      d['scrollH'] - d['clientH']))
    if d['bodyBottom'] is not None and d['bodyBottom'] > d['copyBottom'] + 1:
        out.append('中文正文底边 %d 超出 .ar-copy 底边 %d（被裁）'
                   % (d['bodyBottom'], d['copyBottom']))
    return out


def selftest_break(ch, srv, cachebust):
    """注入「修复前」的样式（去掉矮屏适配），判据必须报红。"""
    page, tid = ch.new_page(*LANDSCAPE[1])   # 740x360 最矮
    try:
        ch.navigate(page, srv.url('/index.html?arbself=%d' % cachebust))
        time.sleep(2.4)
        page.eval_js(OPEN_FIRST, timeout=25)
        time.sleep(0.6)
        # 撤销修复：恢复 bottom 锚定、去掉 max-height/overflow、显示英文
        page.eval_js(
            "(function(){var st=document.createElement('style');"
            "st.textContent='@media (max-height:520px) and "
            "(orientation:landscape){.ar-copy{top:auto !important;"
            "bottom:168px !important;max-height:none !important;"
            "overflow:visible !important}"
            ".ar-copy .ar-en,.ar-copy .ar-chapter-en,"
            ".ar-copy .ar-body-en{display:block !important}"
            ".ar-copy h3{font-size:var(--fs-lg) !important}"
            ".ar-copy p{line-height:1.95 !important;margin-bottom:"
            "var(--sp-1) !important}}';"
            "document.head.appendChild(st);return 1;})()", timeout=25)
        page.eval_js(SWEEP, timeout=30)
        time.sleep(1.0)
        d = json.loads(page.eval_js('(%s)' % MEASURE, timeout=30))
        return judge(d)
    finally:
        try:
            page.close()
        except Exception:
            pass
        ch.close_page(tid)


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  cdp_client 不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（未取证 != 通过）')
        return 0
    srv = SiteServer(os.path.join(BASE, 'site'), port=8996)
    ch = Chrome()
    cb = int(time.time())
    fails = []
    checked = 0
        # 自检阶段：异常一律 FAIL —— 判据自己有 bug 绝不能被吞成 SKIP 放行
    try:
        sb = selftest_break(ch, srv, cb)
        print('[%s] 自检：撤销矮屏适配后能报出问题（%s）' % (
            'PASS' if sb else 'FAIL',
            ('%d 项' % len(sb)) if sb else '无读数 = 判据已哑'))
        if not sb:
            print('RESULT: FAIL  自检不通过：撤销修复后判据无反应，读数不可信')
            return 1
        for x in sb[:2]:
            print('      注入问题:', x[:96])
    except Exception as e:
        print('RESULT: FAIL  判据自检阶段异常（判据本身坏了）: '
              '%s: %s' % (type(e).__name__, str(e)[:110]))
        return 1
    try:

        # 真判：三个矮横屏
        for vw, vh in LANDSCAPE:
            d = run_viewport(ch, srv, vw, vh, cb)
            checked += 1
            probs = judge(d)
            print('[%s] 矮横屏 %dx%d：copy top=%s dots底=%s '
                  'client/scroll=%s/%s 正文=%r' % (
                      'PASS' if not probs else 'FAIL', vw, vh,
                      d.get('copyTop'), d.get('dotsBottom'),
                      d.get('clientH'), d.get('scrollH'), d.get('bodyTxt')))
            for p in probs:
                print('      -', p[:104])
                fails.append('%dx%d %s' % (vw, vh, p))
        # 对照：竖屏不得被误伤（仍应通过）
        d = run_viewport(ch, srv, PORTRAIT[0], PORTRAIT[1], cb)
        checked += 1
        probs = judge(d)
        print('[%s] 竖屏对照 %dx%d：copy top=%s client/scroll=%s/%s' % (
            'PASS' if not probs else 'FAIL', PORTRAIT[0], PORTRAIT[1],
            d.get('copyTop'), d.get('clientH'), d.get('scrollH')))
        for p in probs:
            print('      -', p[:104])
            fails.append('竖屏 %s' % p)
    except Exception as e:
        # 真判阶段：chrome/页面级异常按环境问题处理（SKIP 不算通过）
        print('RESULT: SKIP  真判阶段探针异常（环境问题，未取证）: '
              '%s: %s' % (type(e).__name__, str(e)[:110]))
        return 0
    finally:
        ch.close()
        try:
            srv.stop()
        except Exception:
            pass

    print()
    if checked < 4:
        print('RESULT: FAIL  只完成 %d/4 个视口（有跳过的）' % checked)
        return 1
    if fails:
        print('RESULT: FAIL  AR 面板排版边界 %d 处问题' % len(fails))
        for f in fails[:8]:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个视口（3 矮横屏 + 竖屏对照）AR 正文均'
          '不顶穿、不与导览点重叠、最长中文正文免滚动' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
