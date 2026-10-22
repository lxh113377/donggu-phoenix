# -*- coding: utf-8 -*-
r"""tools/no_js_content_test.py —— 禁用 JS 时，正文内容不得被 CSS 藏起来。

## 为什么需要（轮140 实测，潜伏 140 轮）
.reveal 初始 opacity:0，靠 main.js 的 IntersectionObserver 加 .in 才显形。
用 CDP 禁用页面脚本实测（probeWorks=True 且 pageJsRan=False，证明实验有效）：

    可见文字 24497 -> 6938 字（丢 72%）
    可见 reveal   22 -> 0 个
    文档高度    11368 -> 6789

而 sw.js 注释自己写着「现场首访的瓶颈是 4G」—— main.js 一旦超时或抛错，
站在图腾前扫码的观众看到的就是残缺页面。这恰是本项目的核心使用场景。

## 判据（运行时，不做静态猜测）
禁用页面脚本加载页面，找出「有文字、非浮层、被 opacity 挡住」的元素：
  · 只统计 opacity（不查 display:none —— 那多半是按需展开的 UI）
  · 排除自身或祖先为 position:fixed 的：那是浮层/抽屉/提示，
    默认隐藏是正确设计（菜单、启动屏、toast、摄像头层都属此类）
  · 只报最外层：祖先已被报时不重复计子元素
  · 无文字的容器不计：ar-cards / culture-grid 这类内容由 JS 从
    culture.js、ar-data.js 渲染，index.html 的 noscript 横幅已声明该边界，
    属已声明的设计范围而非缺陷 —— 所以「空容器」不会让本判据误报
命中即 FAIL。

## 尺子有效性自检（U-149/U-151）
  S1 去掉页面自己的兜底（noscript 样式与看门狗）-> 必须报出被藏内容
  S2 保留兜底                                    -> 必须 0 命中
S1 是决定性的：它证明本判据真能抓到轮140 修掉的那个缺陷，
而不是因为「恰好没东西被藏」才恒绿。自检用临时文件，不写盘到站点。

## 诚实语义
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
ENTRY = os.path.join(SITE, 'index.html')

PROBE = r"""(function(){
  function isOverlay(el){
    var n = el, k = 0;
    while (n && n !== document.documentElement && k < 40) {
      if (getComputedStyle(n).position === 'fixed') return true;
      n = n.parentElement; k++;
    }
    return false;
  }
  function blockedByAncestor(el){
    var n = el.parentElement, k = 0;
    while (n && k < 40) {
      var s = getComputedStyle(n);
      if (s.display !== 'none' && parseFloat(s.opacity) < 0.05) return true;
      n = n.parentElement; k++;
    }
    return false;
  }
  var hits = [], chars = 0;
  var all = document.querySelectorAll('body *');
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') continue;
    if (parseFloat(st.opacity) >= 0.05) continue;
    if (isOverlay(el)) continue;
    var txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!txt) continue;
    if (blockedByAncestor(el)) continue;
    var r = el.getBoundingClientRect();
    hits.push({
      cls: ((typeof el.className === 'string' ? el.className : '')
            || el.tagName.toLowerCase()).slice(0, 30),
      sec: (el.closest('section[id]') || {}).id || '?',
      chars: txt.length,
      w: Math.round(r.width), h: Math.round(r.height)
    });
    chars += txt.length;
  }
  var vis = [].slice.call(document.querySelectorAll('body *')).filter(function(e){
    var s = getComputedStyle(e);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    if (parseFloat(s.opacity) < 0.05) return false;
    var b = e.getBoundingClientRect();
    return b.width > 2 && b.height > 2;
  });
  var visChars = vis.map(function(e){ return e.textContent.trim(); })
                    .join(' ').replace(/\s+/g, ' ').length;
  var secs = document.querySelectorAll('section[id]').length;
  var reveals = document.querySelectorAll('.reveal').length;
  return JSON.stringify({
    probeWorks: true,
    // 页面加载自检：404 或被剥到空壳时 body 几乎没有 section，
    // 此时 hidden=0 是「没测到」而不是「没问题」，绝不能当通过处理。
    pageLoaded: secs >= 5 && reveals >= 5,
    sections: secs, revealCount: reveals,
    jsRan: !!window.__site,
    hidden: hits, hiddenChars: chars, visChars: visChars,
    docH: Math.round(document.body.scrollHeight)
  });
})()"""


def load_page(page, srv, ch, url, disable_js):
    if disable_js:
        page.call('Emulation.setScriptExecutionDisabled', {'value': True})
    from cdp_client import Chrome as _C
    ch.navigate(page, srv.url(url))
    ch.wait_for(page, "!!document.querySelector('body *')", 25)
    time.sleep(1.6)
    return json.loads(page.eval_js(PROBE, timeout=40))


def probe_site(file_name, disable_js=True):
    r"""file_name 必须是相对 site/ 的文件名（不是绝对路径）。

    轮140 修：原先 selftest 传了绝对路径进来，拼出的 URL 形如
    /C:\...\_nojs_probe_tmp.html -> 404 -> body 空 -> hidden=0，
    看着像「判据无牙」，其实页面压根没加载。
    """
    if os.path.isabs(file_name):
        return None, 'probe_site 只接受相对 site 的文件名，收到绝对路径'
    from cdp_client import Chrome, SiteServer
    srv = SiteServer(SITE)
    if not srv.ok:
        return None, '静态服务起不来'
    ch = Chrome()
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            d = load_page(page, srv, ch,
                          '/' + file_name + '?v=%d' % int(time.time()),
                          disable_js)
            if not d.get('pageLoaded'):
                return None, ('页面未真正加载（section=%s reveal=%s），'
                              '空壳不得算作通过'
                              % (d.get('sections'), d.get('revealCount')))
            return d, None
        finally:
            page.close()
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()


def selftest():
    """S1 去掉兜底必须报出被藏内容；S2 保留兜底必须 0 命中。"""
    bad = []
    orig = io.open(ENTRY, encoding='utf-8', newline='').read()
    # 名字必须落在 .gitignore 的 site/_probe_*.html 里：
    # 判据写的是「剥掉兜底的首页副本」，进程被杀时 finally 不执行，
    # 残留会被 git add site/ 提交，且 wrangler 部署整个 site/ 目录，
    # 会把这份无兜底副本公开上传。
    tmp_name = '_probe_nojs_tmp.html'
    tmp = os.path.join(SITE, tmp_name)  # 绝对路径仅用于读写，探针传文件名
    if os.path.exists(tmp):
        os.remove(tmp)          # 先清上次崩溃的残留，避免读到旧文件
    try:
        # S1：剥掉 noscript 样式与看门狗，还原成轮140 修复前的形态
        stripped = re.sub(r'<noscript><style>.*?</style></noscript>\n?',
                          '', orig, flags=re.S)
        stripped = re.sub(
            r'<script>\s*/\* 内容可见性看门狗.*?</script>\n?',
            '', stripped, flags=re.S)
        if stripped == orig:
            bad.append('S1 构造失败：剥不掉 noscript 样式与看门狗'
                       '（可能兜底写法变了，判据需同步）')
            return bad
        io.open(tmp, 'w', encoding='utf-8', newline='').write(stripped)
        d1, e1 = probe_site(tmp_name)
        if e1:
            bad.append('S1 未跑成：%s' % e1)
            return bad
        # 期望依据实测：修复前后禁 JS 的可见文字 6938 -> 8194，差 1256 字，
        # 正是 CSS 门控真正藏起来的正文量（其余差额来自内容由 JS 渲染的空容器，
        # 不属本判据范围）。原先拍脑袋写 >3000，把有牙的判据判成了无牙。
        ok1 = (d1['hiddenChars'] > 800 and len(d1['hidden']) >= 10
               and not d1['jsRan'])
        print('  [%s] S1 剥掉兜底（还原修复前）-> 被藏 %d 字、%d 个元素'
              % ('ok' if ok1 else 'X', d1['hiddenChars'], len(d1['hidden'])))
        if not ok1:
            bad.append('S1 未抓到被藏内容，判据可能是恒绿的安慰剂')
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    d2, e2 = probe_site('index.html')
    if e2:
        bad.append('S2 未跑成：%s' % e2)
        return bad
    ok2 = d2['hiddenChars'] == 0 and not d2['jsRan']
    print('  [%s] S2 保留兜底（当前站点）-> 被藏 %d 字'
          % ('ok' if ok2 else 'X', d2['hiddenChars']))
    if not ok2:
        bad.append('S2 当前站点仍有被藏内容：%s'
                   % [(h['sec'], h['cls'], h['chars'])
                      for h in d2['hidden'][:4]])
    return bad


def stray_probe_files():
    """列出 site/ 下残留的判据临时探针页。

    实测（轮140）：这类残留不会被 orphan_asset_test 或 verify_site 拦，
    而 .gitignore 只防提交、不防部署 —— wrangler 上传整个 site/，
    一份「剥掉兜底的首页副本」就这样被公开。
    """
    out = []
    for f in os.listdir(SITE):
        if not f.endswith('.html') or not f.startswith('_'):
            continue
        if (f.startswith('_probe_') or f.startswith('_admin_probe')
                or f.startswith('_admin_diag')):
            out.append(f)
    return sorted(set(out))


def main():
    try:
        from cdp_client import find_chrome
    except Exception as e:
        print('RESULT: SKIP  CDP 模块不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（环境问题，本判据未执行）')
        return 0
    if not os.path.exists(ENTRY):
        print('RESULT: SKIP  找不到入口页（未测不等于通过）')
        return 0

    print('=== 尺子有效性自检 ===')
    bs = selftest()
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1
    d, err = probe_site('index.html')
    if err:
        print('RESULT: SKIP  %s（未测不等于通过）' % err)
        return 0
    print('=== 禁用 JS 时的内容可见性 ===')
    print('  页面脚本运行: %s（应为 False，证明确实禁用了）' % d['jsRan'])
    print('  可见文字 %d 字，文档高 %d px' % (d['visChars'], d['docH']))
    if d['hidden']:
        print('  被 CSS 藏住的正文内容 %d 个、共 %d 字：'
              % (len(d['hidden']), d['hiddenChars']))
        for h in d['hidden'][:12]:
            print('     %-12s %-30s %5d 字  %dx%d'
                  % (h['sec'], h['cls'], h['chars'], h['w'], h['h']))
        print()
        print('RESULT: FAIL  禁用 JS 后有 %d 处正文内容被 opacity 藏住'
              '（共 %d 字）—— 缺无 JS 兜底' % (len(d['hidden']),
                                               d['hiddenChars']))
        return 1
    stray = stray_probe_files()
    if stray:
        print('RESULT: FAIL  site/ 下有判据临时探针页残留：%s'
              '—— 进程被杀时 finally 不执行；这类文件不会被'
              ' orphan_asset/verify_site 拦，且 .gitignore 不防部署'
              '（wrangler 上传整个 site/）' % ', '.join(stray))
        return 1
    print('RESULT: PASS  禁用 JS 时正文内容无一处被 opacity 藏住，'
          '且自检证明「去掉兜底就会报红」（判据有牙，不是恒绿）；'
          '临时探针页无残留')
    return 0


if __name__ == '__main__':
    sys.exit(main())
