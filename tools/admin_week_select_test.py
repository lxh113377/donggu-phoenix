# -*- coding: utf-8 -*-
r"""tools/admin_week_select_test.py —— 后台周次下拉与周图的联动判据（CDP 读像素）。

## 为什么需要（轮172 新开维度）
轮172 发现后台周次图没有选中态：切周次时下方逐日图与日表都变，
周图毫无反应，两张图视觉脱节。修好之后必须守住 ——
而这条回归**任何读 DOM 的判据都测不到**：
  · canvas 是位图，画了什么不在 DOM 里；
  · 下拉的 value 一定变（那是浏览器原生行为），所以「select 变了」
    不能证明「图跟着变」。
本仓判据此前几乎全测单一初始状态，交互之后是系统性盲区。

## 判据
切三个周次（下标 0/2/5），每次读 chart-weeks 每列的亮像素数取最亮列：
  A 三次的最亮列必须互不相同（高亮真的在移动）
  B 最亮列必须随周次下标严格递增（导引线落在正确的点上，
    而不是随机乱跳 —— 只查「不同」会放过画错位置的实现）

## 自检（证明有牙，不是恒绿）
  S1 造回归：把 change 处理器里的 drawWeeks() 调用删掉，
     生成临时 fixture 页服务化 —— 此时高亮停在初始周，
     判据必须报「最亮列没移动」。抓不到即判 FAIL。
  S2 真实页面必须零缺陷。
fixture 写在 site/ 下、跑完删除，不碰跟踪文件。

用法：python tools/admin_week_select_test.py
"""
import json
import io
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
sys.path.insert(0, os.path.join(BASE, 'tools'))

PICK = (0, 2, 5)

PROF = r"""(function(){
  var cv=document.getElementById('chart-weeks');
  if(!cv) return JSON.stringify({missing:1});
  var ctx=cv.getContext('2d');
  var d=ctx.getImageData(0,0,cv.width,cv.height).data;
  var W=cv.width,H=cv.height,bright=[];
  for(var x=0;x<W;x++){
    var b=0;
    for(var y=0;y<H;y++){
      var i=(y*W+x)*4;
      if(0.2126*d[i]+0.7152*d[i+1]+0.0722*d[i+2]>140) b++;
    }
    bright.push(b);
  }
  var best=0;
  for(var x=1;x<W-1;x++){ if(bright[x]>bright[best]) best=x; }
  return JSON.stringify({W:W,best:best,peak:bright[best]});
})()"""

SWITCH = r"""(function(i){
  var s=document.getElementById('sel-week');
  if(!s) return 'nosel';
  s.value=String(i);
  s.dispatchEvent(new Event('change',{bubbles:true}));
  return s.value;
})"""


def sample(page, url, ch, picks=PICK):
    """打开页面，依次切到 picks 里的周次，返回最亮列列表。"""
    ch.navigate(page, url)
    time.sleep(3.0)
    out = []
    for i in picks:
        page.eval_js('(%s)(%d)' % (SWITCH, i), timeout=25)
        time.sleep(0.8)
        d = json.loads(page.eval_js(PROF, timeout=30))
        if d.get('missing'):
            return None
        out.append(d['best'])
    return out


def judge(cols):
    """最亮列序列 -> 缺陷列表（纯函数，自检直接喂）。"""
    if cols is None:
        return ['找不到 #chart-weeks（周图不存在）']
    if len(set(cols)) != len(cols):
        return ['A 切换周次后最亮列未全部移动 %s —— '
                '周图选中态缺失或 change 未重绘周图' % cols]
    if any(cols[i + 1] <= cols[i] for i in range(len(cols) - 1)):
        return ['B 最亮列未随周次递增：%s —— '
                '高亮落在了错误的点上' % cols]
    return []


def selftest():
    """S1 造回归必须抓到，S2 真页面必须零缺陷。"""
    from cdp_client import Chrome, SiteServer, find_chrome
    if not find_chrome():
        return None
    src = os.path.join(SITE, 'admin', 'index.html')
    html = io.open(src, encoding='utf-8', errors='ignore').read()
    # 定位 change 处理器里的 drawWeeks() 调用并删除（保留注释行）
    m = re.search(r'(      // 周图也要重绘[^\n]*\n)      drawWeeks\(\);\n',
                  html)
    if not m:
        return ['S1 找不到 change 里的 drawWeeks() 调用，'
                '无法构造回归样本（判据前提已变）']
    broken = html[:m.start()] + m.group(1) + html[m.end():]
    fx_rel = '_weeksel_fixture.html'
    fx = os.path.join(SITE, fx_rel)
    with open(fx, 'w', encoding='utf-8', newline='') as f:
        f.write(broken)
    bad = []
    srv = SiteServer(SITE, port=8975)
    ch = Chrome()
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            cols_b = sample(page, srv.url('/%s?fx=1' % fx_rel), ch)
            f_b = judge(cols_b)
            s1 = bool(f_b)
            print('  [%s] S1 删掉 change 里的 drawWeeks() -> 最亮列 %s，'
                  '判据报 %d 条'
                  % ('ok' if s1 else 'X', cols_b, len(f_b)))
            for x in f_b:
                print('        -', x[:100])
            if not s1:
                bad.append('S1 造出的真实回归没被抓到，判据可能恒绿')
            cols_r = sample(page, srv.url('/admin/index.html?real=1'), ch)
            f_r = judge(cols_r)
            s2 = not f_r
            print('  [%s] S2 真实页面 -> 最亮列 %s，%d 条缺陷'
                  % ('ok' if s2 else 'X', cols_r, len(f_r)))
            for x in f_r:
                print('        -', x[:100])
            if not s2:
                bad.append('S2 把正常联动误判成缺陷')
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
    print('=== 后台周次下拉与周图联动（读 canvas 像素）===')
    print()
    print('=== 尺子有效性自检 ===')
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
    print('=== 真实页面 ===')
    from cdp_client import Chrome, SiteServer, find_chrome
    if not find_chrome():
        print('RESULT: SKIP  无 chrome')
        return 0
    srv = SiteServer(SITE, port=8976)
    ch = Chrome()
    cols = None
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            cols = sample(page, srv.url('/admin/index.html?m=1'), ch)
        finally:
            try:
                page.close()
            except Exception:
                pass
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()
    print('  切周次 %s -> 最亮列 %s' % (list(PICK), cols))
    fails = judge(cols)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  周图选中态随下拉切换按序移动（%s），'
          '且自检证明删掉重绘调用会被抓到' % cols)
    return 0


if __name__ == '__main__':
    sys.exit(main())
