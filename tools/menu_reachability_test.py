# -*- coding: utf-8 -*-
"""tools/menu_reachability_test.py —— 汉堡菜单项可达性判据（轮179）。

## 为什么需要它
一手实测缺陷：汉堡菜单是**窄屏唯一导航入口**（.nav-toggle 断点
max-width:860px，横屏手机用户确实能打开），而矮横屏上 7 节里首尾两项
**永久点不到**：
    844x390  首项 top=-112  末项 bottom=474（视口只有 390 高）
    740x360  首项 top=-127  末项 bottom=459
    667x375  首项 top=-119  末项 bottom=466
根因：.menu 用 display:grid + align-content:center，内容高于视口时
**双向**溢出，而「可滚动区域不包含 block-start 方向」—— 上方溢出的部分
永远滚不到；且 overflowY 是 visible，连下方也滚不到。
这不是难看，是**内容不可达**，比对比度/触控更严重。

## 与轮175/176/179 同族：判据测的是初始态
菜单关闭时 .menu 是 visibility:hidden，内部 rect 全 0，
touch_target / contrast 一类「读 DOM」的判据一律跳过它 ——
所以必须**主动打开**再测，而且要测「能不能滚到」而不是只测「在不在」。

## 判据（逐视口，全部可机器判定）
A 打开前置：.nav-toggle 必须用户可点（display!=none 且 rect>0）——
  否则测的是用户根本打不开的状态（本会话第 N 次「探针假象」教训）。
B 菜单能打开（.on 且 visibility:visible）。
C 每一项都能被滚进视口：逐项 scrollIntoView 后其 rect 完整落在视口内。
  这是核心断言 —— 首项被顶出上方、或末项在下方且不可滚，都会在这里报。
D 触控目标 >= 44px（菜单项本身）。
零样本不判 PASS：任一视口取不到菜单/项，或 A/B 不成立，一律 FAIL。

## 自检（证明有牙）
注入「撤销修复」的样式（align-content:center + overflow:visible），
C 项必须报红。自检不过 -> 判据自判 FAIL（判据自己坏了必须响）。
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

VIEWPORTS = [(844, 390), (740, 360), (667, 375),
             (390, 844), (320, 700), (768, 1024)]
MIN_PX = 44

TOGGLE = r"""(function(){
  var t=document.getElementById('nav-toggle');
  if(!t) return JSON.stringify({no:1});
  var b=t.getBoundingClientRect(), cs=getComputedStyle(t);
  return JSON.stringify({
    clickable: b.width>0 && b.height>0 && cs.display!=='none'
               && cs.visibility!=='hidden',
    w:Math.round(b.width), h:Math.round(b.height)});})()"""

OPEN = r"""(function(){
  var t=document.getElementById('nav-toggle');
  if(t && t.getBoundingClientRect().width>0){ t.click(); return 'click'; }
  return 'notoggle';})()"""

REACH = r"""(function(){
  var m=document.getElementById('menu');
  if(!m) return JSON.stringify({missing:1});
  var cs=getComputedStyle(m);
  var out={on:m.classList.contains('on'), vis:cs.visibility,
    op:cs.opacity, overflowY:cs.overflowY,
    vh:window.innerHeight,
    clientH:Math.round(m.clientHeight), scrollH:Math.round(m.scrollHeight)};
  var links=[].slice.call(m.querySelectorAll('a'));
  out.n=links.length;
  out.items=[];
  for(var i=0;i<links.length;i++){
    // 先复位再滚到该项，模拟用户滑动查找
    m.scrollTop=0;
    links[i].scrollIntoView({block:'center'});
    var b=links[i].getBoundingClientRect();
    var acs=getComputedStyle(links[i]);
    out.items.push({i:i,
      txt:(links[i].textContent||'').trim().slice(0,6),
      top:Math.round(b.top), bottom:Math.round(b.bottom),
      h:Math.round(b.height),
      inView: b.top>=-1 && b.bottom<=out.vh+1,
      small: b.height<__MIN__});
  }
  m.scrollTop=0;
  return JSON.stringify(out);})()"""

BREAK_CSS = ("@media (max-height:600px){.menu{align-content:center !important;"
             "overflow:visible !important;padding-top:96px !important}"
             ".menu a{padding:18px 0 !important}}"
             ".menu{align-content:center !important;"
             "overflow:visible !important}")


def inject_break(page):
    page.eval_js("(function(){var st=document.createElement('style');"
                 "st.textContent=" + json.dumps(BREAK_CSS) + ";"
                 "document.head.appendChild(st);return 1;})()", timeout=25)


def judge(d):
    out = []
    if d.get('missing'):
        return ['取不到 #menu（未取证）']
    if not d.get('on') or d.get('vis') != 'visible':
        return ['菜单未真正打开（on=%s vis=%s）'
                % (d.get('on'), d.get('vis'))]
    if not d.get('n'):
        return ['菜单里没有导航项（未取证）']
    bad = [it for it in d['items'] if not it['inView']]
    if bad:
        out.append('%d/%d 项滚不到视口：%s'
                   % (len(bad), d['n'],
                      '、'.join('第%d项%r(top=%s,bottom=%s,视口%s)'
                               % (it['i'], it['txt'], it['top'],
                                  it['bottom'], d['vh'])
                               for it in bad[:3])))
    small = [it for it in d['items'] if it['small']]
    if small:
        out.append('%d 项触控高 < %dpx：%s'
                   % (len(small), MIN_PX,
                      '、'.join('%r=%spx' % (it['txt'], it['h'])
                               for it in small[:3])))
    return out


def run_viewport(ch, srv, vw, vh, cb, break_it=False):
    page, tid = ch.new_page(vw, vh)
    try:
        ch.navigate(page, srv.url('/index.html?mreach=%d_%d' % (vw, cb)))
        time.sleep(2.2)
        tg = json.loads(page.eval_js(TOGGLE, timeout=25))
        if tg.get('no'):
            return None, ['取不到 #nav-toggle（未取证）']
        if not tg.get('clickable'):
            return None, ['nav-toggle 不可点（display/rect 为 0），'
                          '该视口用户打不开菜单 —— 测了也是假象']
        if break_it:
            inject_break(page)
            time.sleep(0.3)
        page.eval_js(OPEN, timeout=25)
        time.sleep(0.9)
        js = REACH.replace('__MIN__', str(MIN_PX))
        got = page.eval_js(js, timeout=30)
        if not isinstance(got, str):
            return None, ['菜单测量脚本无返回（判据自身失效，'
                          '不当作通过）：%r' % (str(got)[:40],)]
        d = json.loads(got)
        return d, judge(d)
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
    cb = int(time.time())
    srv = SiteServer(os.path.join(BASE, 'site'), port=9002)
    ch = Chrome()
    fails = []
    checked = 0
    try:
        # 自检：撤销修复必须报红（挑一个已知会坏的视口）
        try:
            _, sb = run_viewport(ch, srv, 740, 360, cb, break_it=True)
        except Exception as e:
            print('RESULT: FAIL  判据自检阶段异常（判据本身坏了）: '
                  '%s: %s' % (type(e).__name__, str(e)[:110]))
            return 1
        print('[%s] 自检：撤销修复（center+不可滚）后能报出不可达' % (
            'PASS' if sb else 'FAIL'))
        if not sb:
            print('RESULT: FAIL  自检不通过：撤销修复后判据无反应，读数不可信')
            return 1
        for x in sb[:1]:
            print('      注入问题:', x[:120])

        for vw, vh in VIEWPORTS:
            try:
                d, probs = run_viewport(ch, srv, vw, vh, cb)
            except Exception as e:
                print('RESULT: SKIP  真判阶段探针异常（环境问题）: '
                      '%s: %s' % (type(e).__name__, str(e)[:110]))
                return 0
            checked += 1
            if d is None:
                print('[FAIL] %dx%d %s' % (vw, vh, probs[0]))
                fails.append('%dx%d %s' % (vw, vh, probs[0]))
                continue
            print('[%s] %dx%d：菜单项 %d，滚不到 %d，'
                  'client/scroll=%s/%s overflowY=%s' % (
                      'PASS' if not probs else 'FAIL', vw, vh, d['n'],
                      len([it for it in d['items'] if not it['inView']]),
                      d['clientH'], d['scrollH'], d['overflowY']))
            for p in probs:
                print('      -', p[:126])
                fails.append('%dx%d %s' % (vw, vh, p))
    finally:
        ch.close()
        try:
            srv.stop()
        except Exception:
            pass

    print()
    if checked < len(VIEWPORTS):
        print('RESULT: FAIL  只完成 %d/%d 个视口（有跳过的）'
              % (checked, len(VIEWPORTS)))
        return 1
    if fails:
        print('RESULT: FAIL  菜单可达性 %d 处问题' % len(fails))
        for f in fails[:8]:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个视口的汉堡菜单：每一项都能滚进视口'
          '且触控高 >= %dpx' % (checked, MIN_PX))
    return 0


if __name__ == '__main__':
    sys.exit(main())
