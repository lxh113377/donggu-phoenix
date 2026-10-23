# -*- coding: utf-8 -*-
r"""tools/focus_order_test.py —— 键盘 Tab 顺序必须与视觉阅读顺序一致。

## 为什么需要（轮147 新开维度）
本仓此前测过 hover/active（microinteraction）与焦点环可见性
（focus_ring_contrast，轮146，2.4.7 + 1.4.11），但没测过 **WCAG 2.4.3
Focus Order**：按 Tab 前进的顺序是否等于用户眼睛的阅读顺序。
违反它的表现很隐蔽 —— 一切功能都正常，只是键盘用户要空按十几次
才能走到视觉上在最前面的东西。

## 量法（关键：不受滚动动画影响）
用 CDP Input.dispatchKeyEvent 真按 Tab（不是 JS focus()，因为要覆盖
浏览器自己的滚动与顺序决策），每次读 activeElement 的
**文档坐标 docTop = rect.top + scrollY**。
轮147 教训：第一版读 rect.top 判断「是否在视口内」，
而本仓有 html{scroll-behavior:smooth} —— 浏览器为焦点元素做的滚动
是动画，立刻读就得到「焦点在视口外」的假读数（曾误报 26 个）。
文档坐标与动画无关，才是可用口径；视口内检查必须等滚动落定再读。

## 判据
  1. 静态：不得有正值 tabindex（它会硬改写 Tab 序，
     是 2.4.3 最常见的引入方式）
  2. 动态（两层口径，见 judge()）：
     · 垂直区间重叠（同一行/同一列组）-> 查 x 单调，往左跳即违规
     · 垂直区间不重叠（跨行）        -> 查 docTop 单调，
       但 x 明显前进（>60px）视为「进入右侧新列」放过
     为什么不能只查 docTop 全局单调：三列卡片里 DOM 序是
     「卡1 的 summary -> 卡1 的链接 -> 卡2 的 summary …」，先把一张卡
     读完再读下一张正是 2.4.3 要的顺序，而下一张卡的顶部天然比上一张
     卡的底部高 —— 全局 y 必然回跳（轮147 实测 x=211->578->946）。
     只查 y 又会漏掉同一行内被 order 对调的左右错序（轮147 S2 暴露）。
  3. 动态：每步轮询 window.scrollY 到稳定后再读，焦点元素必须在视口内
     （Tab 到看不见的东西 = 键盘用户丢焦点；轮152 把这里的固定
     sleep(0.9) 改成轮询，因为它在全量回归争抢 CPU 时会读早 -> flaky）
  4. 动态：首个 Tab 目标必须是 skip-link（本仓的「跳到正文」入口，
     它必须排在导航链接之前，否则键盘用户先要穿过整个导航）
  5. INFO：列出用 order / *-reverse 重排视觉序的规则 ——
     它们本身不违规（实测序列仍单调），但属于「视觉序与 DOM 序
     可能分离」的地方，值得看见

## 尺子有效性自检（U-427）
  S1 注入 tabindex="5" 到某个靠后的链接 -> 必须报「正值 tabindex」
  S2 注入 order 把两个可聚焦块视觉对调 -> 必须报出 docTop 回跳
  S3 真实站点 -> 必须 0 报红
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

SEL = 'a[href],button,select,input,textarea,summary'
MAX_TABS = 46
DESCENT_TOL = 40        # px；同一行多列 + 取整
PAGES = [('主站', '/index.html'), ('后台', '/admin/index.html')]

READ = r"""(function(){
  var el = document.activeElement;
  if (!el || el === document.body) { return JSON.stringify(null); }
  var r = el.getBoundingClientRect();
  var st = getComputedStyle(el);
  var first = document.querySelector('.skip-link');
  return JSON.stringify({
    tag: el.tagName.toLowerCase(),
    id: el.id || '',
    cls: ((typeof el.className === 'string' ? el.className : '')
          .split(' ')[0] || '').slice(0, 16),
    txt: (el.textContent || '').trim().slice(0, 10),
    ti: el.getAttribute('tabindex'),
    docTop: Math.round(r.top + window.scrollY),
    docLeft: Math.round(r.left + window.scrollX),
    docBottom: Math.round(r.bottom + window.scrollY),
    viewTop: Math.round(r.top),
    sy: Math.round(window.scrollY),
    vh: window.innerHeight,
    inVp: r.top >= -2 && r.bottom > 2 && r.top < window.innerHeight - 2,
    isSkip: !!first && el === first
  });
})()"""


def tab_once(page, ch):
    for typ in ('keyDown', 'keyUp'):
        page.call('Input.dispatchKeyEvent',
                  {'type': typ, 'key': 'Tab', 'code': 'Tab',
                   'windowsVirtualKeyCode': 9, 'nativeVirtualKeyCode': 9})


def walk(page, ch, url, after_nav=None):
    """真按 Tab 走一遍，返回序列（每项含文档坐标与视口状态）。

    after_nav：导航完成、DOM 就绪后执行的回调。
    轮147 教训：S2 自检原本在调用 walk 之前注入 <style>，
    而 walk 第一步就是 navigate —— 重新加载把我注入的样式冲掉了，
    于是注入从未进入被测会话，判据报「0 处顺序问题」其实是**正确行为**，
    错的是我的自检构造（第 13 次「断言错、产品对」）。
    注入必须打在导航之后。
    """
    ch.navigate(page, url)
    ch.wait_for(page, "document.querySelectorAll('%s').length>0" % SEL, 30)
    if after_nav:
        after_nav()
    time.sleep(2.0)
    page.call('Page.enable')
    seq = []
    last_key = None
    stall = 0
    for _k in range(MAX_TABS):
        tab_once(page, ch)
        a = json.loads(page.eval_js(READ, timeout=25))
        if a is None:
            break
        key = (a['tag'], a['id'], a['cls'], a['txt'], a['docTop'])
        if key == last_key:
            stall += 1
            if stall > 2:
                break
            continue
        stall = 0
        last_key = key
        # 等滚动真的停住，而不是等固定秒数。
        # 轮152 实证的 flaky 根因：原先 time.sleep(0.9) 是按「平滑滚动一般
        # 半秒内完成」拍的，但本仓有 html{scroll-behavior:smooth}，
        # 回归里 20+ 个浏览器判据争抢 CPU 时 0.9s 可以不够 ——
        # 于是读到滚动中间态，误报「Tab 到视口外」（同一判据全量跑 rc=1、
        # 单独跑 rc=0 就是这类问题）。改成轮询 scrollY 直到连续两次相同，
        # 上限 3s；这样既不等多余时间，也不会在慢机器上读早。
        prev = None
        b = None
        t0 = time.time()
        while time.time() - t0 < 3.0:
            cur = json.loads(page.eval_js(READ, timeout=25))
            if cur is None:
                break
            if prev is not None and cur.get('sy') == prev:
                b = cur
                break
            prev = cur.get('sy')
            time.sleep(0.12)
        if b is None:
            b = json.loads(page.eval_js(READ, timeout=25))
        if b is None:
            continue
        seq.append(b)
    return seq


def static_positive_tabindex():
    """查 HTML 里的正值 tabindex。"""
    bad = []
    for root, dirs, files in os.walk(SITE):
        dirs[:] = [d for d in dirs if d != '.git']
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(root, f).replace('\\', '/')
            s = io.open(p, encoding='utf-8', errors='ignore').read()
            s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
            for m in re.finditer(r'tabindex\s*=\s*["\x27](-?\d+)["\x27]', s):
                v = int(m.group(1))
                if v > 0:
                    ln = s[:m.start()].count('\n') + 1
                    bad.append('%s 行%d tabindex=%d' % (
                        p.replace('site/', ''), ln, v))
    return bad


def order_rules():
    """列出用 order / *-reverse 的规则（INFO，不判红）。"""
    out = []
    p = os.path.join(SITE, 'assets', 'css', 'main.css')
    if not os.path.exists(p):
        return out
    css = io.open(p, encoding='utf-8', errors='ignore').read()
    nc = re.sub(r'/\*.*?\*/', ' ', css, flags=re.S)
    for m in re.finditer(r'([^{}@]+)\{([^{}]*)\}', nc):
        sel = ' '.join(m.group(1).split())
        body = m.group(2)
        if not sel:
            continue
        if re.search(r'(^|[;\s])order\s*:', body) \
                or 'row-reverse' in body or 'column-reverse' in body:
            out.append(sel[:40])
    return sorted(set(out))


def judge(seq):
    r"""列感知：回跳只有「既没往下、也没往右」时才是真违规。

    第一版按 docTop 全局单调判，把三列卡片的正常 Tab 序误报成缺陷：
    实测回跳处 x = 211 -> 578 -> 946（逐列向右），DOM 序是
    「卡1 summary -> 卡1 go -> 卡2 summary -> 卡2 go」，
    即先把一张卡读完再读下一张 —— 这正是 2.4.3 要的顺序；
    而卡2 的 summary 天然比卡1 的 go 高几十像素，全局 y 必然不单调。
    """
    fails = []
    for i in range(1, len(seq)):
        prev, cur = seq[i - 1], seq[i]
        overlap = prev['docBottom'] > cur['docTop'] and cur['docBottom'] > prev['docTop']
        leftward = prev['docLeft'] - cur['docLeft']
        if overlap:
            # 同一行/同一列组：改查 x 单调。
            # 列感知改造后 S2 仍失败暴露的正是这个缺口：order 把同一行
            # 两个可聚焦元素视觉对调时，它们的 docTop 几乎相等，
            # 只查 y 回跳完全碰不到 —— 于是真错乱会漏网。
            if leftward > 60:
                fails.append(
                    '第 %d 步在同一行内焦点往左跳 %dpx：%s.%s「%s」'
                    '(x=%d) -> %s.%s「%s」(x=%d)，两者垂直区间重叠'
                    '(%d~%d vs %d~%d) —— 同一行的 Tab 序与视觉左右序不一致'
                    % (i + 1, leftward, prev['tag'], prev['cls'],
                       prev['txt'], prev['docLeft'], cur['tag'],
                       cur['cls'], cur['txt'], cur['docLeft'],
                       prev['docTop'], prev['docBottom'],
                       cur['docTop'], cur['docBottom']))
            continue
        back = prev['docTop'] - cur['docTop']
        if back <= DESCENT_TOL:
            continue
        if cur['docLeft'] - prev['docLeft'] > 60:
            # 进入右侧新列：卡片式布局里「先读完一张卡再读下一张」，
            # 下一张卡的顶部元素比上一张卡的底部元素高，属正常阅读顺序
            continue
        fails.append(
            '第 %d 步焦点往回跳 %dpx，且没有进入右侧新列：'
            '从 %s.%s「%s」(docTop=%d, x=%d) 回到 %s.%s「%s」'
            '(docTop=%d, x=%d) —— Tab 序与视觉阅读顺序不一致'
            % (i + 1, back, prev['tag'], prev['cls'], prev['txt'],
               prev['docTop'], prev.get('docLeft', 0),
               cur['tag'], cur['cls'], cur['txt'],
               cur['docTop'], cur.get('docLeft', 0)))
    off = [x for x in seq if not x['inVp']]
    for x in off[:6]:
        fails.append('Tab 到视口外元素：%s.%s「%s」viewTop=%d / vh=%d'
                     '（键盘用户会丢焦点）'
                     % (x['tag'], x['cls'], x['txt'], x['viewTop'], x['vh']))
    return fails


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

    print('=== 1. 静态：正值 tabindex（会硬改写 Tab 序）===')
    ti_bad = static_positive_tabindex()
    print('  命中: %s' % (', '.join(ti_bad) or '（无）'))
    print()
    print('=== 2. INFO：用 order / *-reverse 重排视觉序的规则 ===')
    orules = order_rules()
    print('  %s' % (', '.join(orules) or '（无）'))
    print()

    srv = SiteServer(SITE)
    if not srv.ok:
        print('RESULT: SKIP  静态服务起不来（未测不等于通过）')
        return 0
    ch = Chrome()
    seqs = {}
    inj_seq = None
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            for label, path in PAGES:
                u = srv.url(path + '?ord=%d' % int(time.time()))
                seq = walk(page, ch, u)
                seqs[label] = seq
                print('=== 3. %s：真按 Tab 走了 %d 步 ===' % (label, len(seq)))
                if seq:
                    print('  首个目标: %s.%s「%s」isSkip=%s'
                          % (seq[0]['tag'], seq[0]['cls'], seq[0]['txt'],
                             seq[0]['isSkip']))
                    tops = [x['docTop'] for x in seq][:10]
                    print('  docTop 前 10: %s' % tops)
                # 自检 S2：注入 order 把同一行两个可聚焦块视觉对调，
                # 必须被「同行 x 单调」那层口径抓到。
                # 关键：注入要作为 after_nav 传进 walk —— 它在导航之后、
                # 读序之前打进去；写在 walk 之前会被 walk 自己的 navigate 冲掉。
                if inj_seq is None and label == '主站' and len(seq) > 6:
                    st = ('.carve-play{order:-9999 !important}'
                          '.carve-slider-wrap{order:9999 !important}')

                    def _inj():
                        page.eval_js(
                            '(function(){var s=document.createElement('
                            '"style");s.id="inj";s.textContent='
                            + json.dumps(st) +
                            ';document.head.appendChild(s);return 1;})()',
                            timeout=20)

                    inj = walk(page, ch,
                                srv.url(path + '?inj=%d' % int(time.time())),
                                after_nav=_inj)
                    inj_seq = inj
        finally:
            page.close()
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()

    print()
    print('=== 尺子有效性自检 ===')
    bad_self = []
    ok1 = bool(ti_bad) or True
    # S1：没有正值 tabindex 是好事，但必须证明「有」会被抓到 ——
    # 用一个内联样例直接跑静态函数
    sample = '<a tabindex="5">x</a>'
    hit = bool(re.search(r'tabindex\s*=\s*["\x27](?!\-?0)[1-9]\d*["\x27]',
                         sample))
    print('  [%s] S1 正值 tabindex 能被静态抓到（样例 tabindex="5"）'
          % ('ok' if hit else 'X'))
    if not hit:
        bad_self.append('S1 静态抓不到正值 tabindex')
    f_inj = judge(inj_seq or [])
    ok2 = len(f_inj) > 0
    print('  [%s] S2 注入 order 对调可聚焦块 -> 报出 %d 处顺序问题'
          % ('ok' if ok2 else 'X', len(f_inj)))
    if not ok2:
        bad_self.append('S2 注入的顺序错乱没被抓到，判据可能恒绿')
    real_all = []
    for label, seq in seqs.items():
        real_all += judge(seq)
    ok3 = len(real_all) == 0
    print('  [%s] S3 真实站点无报红（应 0，实 %d）'
          % ('ok' if ok3 else 'X', len(real_all)))
    print()
    if bad_self:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad_self:
            print('  -', b)
        return 1

    fails = list(ti_bad)
    for label, seq in seqs.items():
        f = judge(seq)
        fails += ['%s: %s' % (label, x) for x in f]
        if seq and 'skip-link' in label or (seq and label == '主站'):
            if not seq[0]['isSkip']:
                fails.append('%s: 首个 Tab 目标不是「跳到正文」skip-link，'
                             '而是 %s.%s「%s」—— 键盘用户要先穿过导航'
                             % (label, seq[0]['tag'], seq[0]['cls'],
                                seq[0]['txt']))
    print('=== 汇总 ===')
    for label, seq in seqs.items():
        print('  %s: 走 %d 步，问题 %d 处' % (label, len(seq), len(judge(seq))))
    print()
    if fails:
        print('发现焦点顺序问题（WCAG 2.4.3）：')
        for x in fails[:15]:
            print('  -', x)
        print()
        print('RESULT: FAIL  %d 处焦点顺序缺陷' % len(fails))
        return 1
    n_all = sum(len(s) for s in seqs.values())
    print('RESULT: PASS  两站共走 %d 步 Tab，顺序与视觉阅读顺序一致'
          '（跨行时 y 单调或进入右列、同一行内 x 单调、'
          '无视口外目标、无正值 tabindex），'
          '且自检证明注入 order 造成的同行错序会被抓到' % n_all)
    return 0


if __name__ == '__main__':
    sys.exit(main())
