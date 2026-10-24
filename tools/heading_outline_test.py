# -*- coding: utf-8 -*-
"""tools/heading_outline_test.py —— 文档大纲判据（轮184）。

## 为什么需要它
一手实测（轮184）：后台 admin/index.html 的 **h1 数量为 0** —— 页面主标识
「访问后台」用 <b> 承载（纯强调元素，无语义层级），下面 9 个 h2 平铺无上级。
读屏用户靠 heading 跳转浏览长页，后台大纲里没有一级标题，等于目录缺首页；
而 87 条判据里**没有一条**管标题层级。

修法是把 <b> 升格为 <h1>（显式重置 margin/font-size/line-height），
像素级 A/B 证明视觉零变化（改前/改后截图 sha256 逐字节相同）。

## 判据（四条，全部可机器判定）
A 唯一性：每个 HTML 页面恰好一个 h1（0 个 = 大纲缺一级；>1 = 主标题不唯一）
B 不跳级：不得出现 h(n) -> h(n+2) 及以上（跳级 = 大纲缺章节）
C 非空：h1 必须有可见文本
D 不得隐藏：h1 渲染后必须真的可见 —— 这条专门防「塞一个 display:none 的
  h1 凑数」：那能过 A，但对读屏用户毫无用处，是把无障碍做成数字游戏。
  无障碍判据必须测**可达性**，不是测**存在性**。

## 自检（证明尺子有牙）
合成页造五种缺陷各一（无 h1 / 两个 h1 / 跳级 / 空 h1 / 隐藏 h1）+ 一个合规页。
缺陷必须各自报红，合规页不得误报。自检不过 -> 判据自判 FAIL。
"""
import io
import json
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

SITE = 'site'


def strip_noise(h):
    return re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S | re.I)


def outline(hh):
    out = []
    for m in re.finditer(r'<(h[1-6])\b[^>]*>(.*?)</\1>', hh, re.S | re.I):
        txt = ' '.join(re.sub(r'<[^>]+>', ' ', m.group(2)).split())
        out.append((int(m.group(1)[1]), txt))
    return out


def judge_static(path, seq):
    out = []
    n1 = sum(1 for l, _ in seq if l == 1)
    if n1 == 0:
        out.append('A %s 没有 h1（大纲缺一级标题，读屏无法定位页面主标识）'
                   % path)
    elif n1 > 1:
        out.append('A %s 有 %d 个 h1（主标题不唯一）' % (path, n1))
    prev = None
    for lvl, txt in seq:
        if prev is not None and lvl > prev + 1:
            out.append('B %s 标题跳级 h%d -> h%d（于 %r）'
                       % (path, prev, lvl, txt[:18]))
        prev = lvl
    for lvl, txt in seq:
        if lvl == 1 and not txt:
            out.append('C %s 的 h1 无文本内容' % path)
    return out


# 可见性判定：首选标准 API Element.checkVisibility（Chrome 105+/FF 106+/
# Safari 17.4+），它能正确穿透 display/visibility/content-visibility/opacity，
# 不必自己猜 clip 组合 —— 我第一版自己解析 clip 就误报了合规页（自检抓到）。
VIS_JS = r"""(function(){
  var out=[];
  [].slice.call(document.getElementsByTagName('h1')).forEach(function(e){
    var cs=getComputedStyle(e);
    var r=e.getBoundingClientRect();
    var txt=(e.textContent||'').trim();
    var hidden=false, why='';
    var hasApi=(typeof e.checkVisibility==='function');
    if(hasApi){
      if(!e.checkVisibility({visibilityProperty:true,
                             opacityProperty:true,
                             contentVisibilityAuto:true})){
        hidden=true; why='checkVisibility=false';
      }
    } else {
      if(cs.display==='none'){hidden=true;why='display:none';}
      else if(cs.visibility==='hidden'||cs.visibility==='collapse'){
        hidden=true;why='visibility:'+cs.visibility;}
      else if(parseFloat(cs.opacity)<0.05){hidden=true;why='opacity~0';}
    }
    if(!hidden && (r.width<1||r.height<1)){hidden=true;why='rect=0';}
    if(!hidden && (r.bottom<=0||r.top>=window.innerHeight
                   ||r.right<=0||r.left>=window.innerWidth)){
      hidden=true;why='视口外';}
    out.push({txt:txt.slice(0,24), hidden:hidden, why:why, api:hasApi?1:0,
      w:Math.round(r.width), h:Math.round(r.height)});
  });
  return JSON.stringify(out);})()"""


def check_visible(ch, srv, url_path):
    page, tid = ch.new_page(1440, 900)
    try:
        ch.navigate(page, srv.url(url_path + '?ho='
                                  + str(int(time.time()) % 99999)))
        time.sleep(2.6)
        got = page.eval_js(VIS_JS, timeout=30)
        if not isinstance(got, str):
            return None
        return json.loads(got)
    finally:
        try:
            page.close()
        except Exception:
            pass
        ch.close_page(tid)


def selftest_cases():
    return [
        ('_ho_no_h1.html',
         '<!doctype html><html><head><title>t</title></head><body>'
         '<h2>只有二级</h2><h3>三级</h3></body></html>', 'A'),
        ('_ho_two_h1.html',
         '<!doctype html><html><head><title>t</title></head><body>'
         '<h1>第一个</h1><h1>第二个</h1></body></html>', 'A'),
        ('_ho_skip.html',
         '<!doctype html><html><head><title>t</title></head><body>'
         '<h1>一级</h1><h4>直接跳四级</h4></body></html>', 'B'),
        ('_ho_empty.html',
         '<!doctype html><html><head><title>t</title></head><body>'
         '<h1>   </h1></body></html>', 'C'),
        ('_ho_hidden.html',
         '<!doctype html><html><head><title>t</title>'
         '<style>h1{display:none}</style></head><body>'
         '<h1>藏起来的标题</h1><p>x</p></body></html>', 'D'),
        ('_ho_ok.html',
         '<!doctype html><html><head><title>t</title></head><body>'
         '<h1>正常一级</h1><h2>二级</h2><h3>三级</h3>'
         '</body></html>', None),
    ]


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  cdp_client 不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（未取证 != 通过）')
        return 0

    pages = []
    for root, dirs, fs in os.walk(SITE):
        dirs[:] = [d for d in dirs if d not in ('.git',)]
        for f in fs:
            if f.endswith('.html') and not f.startswith('_ho_'):
                pages.append(os.path.join(root, f)
                             .replace(chr(92), '/'))
    pages.sort()

    cases = selftest_cases()
    for name, html, _exp in cases:
        io.open(os.path.join(SITE, name), 'w',
                encoding='utf-8', newline='').write(html)
    srv = SiteServer(os.path.join(BASE, 'site'), port=9042)
    ch = Chrome()
    try:
        self_ok = True
        detail = []
        api_seen = 0
        for name, _html, expect in cases:
            h2 = io.open(os.path.join(SITE, name), encoding='utf-8').read()
            probs = judge_static(name, outline(strip_noise(h2)))
            vis = check_visible(ch, srv, '/' + name)
            if vis is None:
                detail.append('%s 探针无返回（判据自身失效）' % name)
                self_ok = False
                continue
            for v in vis:
                api_seen = max(api_seen, v.get('api') or 0)
                if v['hidden']:
                    probs.append('D %s h1 不可见（%s）' % (name, v['why']))
            got = sorted({p[0] for p in probs})
            if expect is None:
                if probs:
                    detail.append('%s 合规页被误报：%s'
                                  % (name, probs[0][:60]))
                    self_ok = False
            elif expect not in got:
                detail.append('%s 应报 %s，实报 %s'
                              % (name, expect, got or '无'))
                self_ok = False
        print('[%s] 自检：6 个合成用例（无 h1/两 h1/跳级/空 h1/隐藏 h1/'
              '合规）全部符合预期；checkVisibility API %s'
              % ('PASS' if self_ok else 'FAIL',
                 '可用' if api_seen else '不可用（走回退分支）'))
        for d in detail[:4]:
            print('      ', d[:118])
        if not self_ok:
            print('RESULT: FAIL  判据自检不通过，读数不可信')
            return 1
    finally:
        ch.close()
        try:
            srv.stop()
        except Exception:
            pass
        for name, _h, _e in cases:
            try:
                os.remove(os.path.join(SITE, name))
            except OSError:
                pass

    fails = []
    srv2 = SiteServer(os.path.join(BASE, 'site'), port=9043)
    ch2 = Chrome()
    try:
        for p in pages:
            h = io.open(p, encoding='utf-8', errors='ignore').read()
            seq = outline(strip_noise(h))
            probs = judge_static(p, seq)
            urlp = '/' + os.path.relpath(p, SITE).replace(chr(92), '/')
            vis = check_visible(ch2, srv2, urlp)
            if vis is None:
                fails.append('%s 可见性探针无返回（未取证）' % p)
                print('[FAIL] %-26s 探针无返回' % p)
                continue
            if not vis:
                probs.append('A %s 渲染后取不到任何 h1' % p)
            for v in vis:
                if v['hidden']:
                    probs.append('D %s 的 h1 %r 实际不可见（%s）—— '
                                 '隐藏 h1 对读屏无用，不算达标'
                                 % (p, v['txt'][:14], v['why']))
            print('[%s] %-26s h1=%d 标题 %d 个，h1 可见 %d/%d' % (
                'PASS' if not probs else 'FAIL', p,
                sum(1 for l, _ in seq if l == 1), len(seq),
                sum(1 for v in vis if not v['hidden']), len(vis)))
            for x in probs:
                print('      -', x[:126])
                fails.append(x)
    finally:
        ch2.close()
        try:
            srv2.stop()
        except Exception:
            pass

    print()
    if not pages:
        print('RESULT: SKIP  未找到任何 HTML 页面（未取证 != 通过）')
        return 0
    if fails:
        print('RESULT: FAIL  文档大纲 %d 处问题' % len(fails))
        for f in fails[:8]:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个页面：h1 唯一、层级不跳、h1 非空且渲染后可见'
          % len(pages))
    return 0


if __name__ == '__main__':
    sys.exit(main())
