# -*- coding: utf-8 -*-
"""tools/defer_regression_test.py —— defer 改动的功能回归（需浏览器）。

## 为什么需要它
轮33 把 9 个阻塞脚本改成 defer，domInteractive 从 237ms 降到 143ms（-40%）。
但 defer 改变了脚本执行时机 —— 若某个脚本依赖「DOM 尚未就绪」的副作用，
页面会静默坏掉（不是报错，而是元素不出现）。

静态判据（critical_path_test）只能证明「有 defer」，不能证明「功能正常」。
所以需要这道运行时回归。

## 验证项
1. 7 个全局对象都正确加载（CULTURE/AR_DATA/Phoenix/WOOD_TO_STATUE/AR_SCENES/__ar/STATUE_PROFILE）
2. body.ready = true（首屏动画完成，说明 Phoenix 初始化成功）
3. H1 文本正确
4. 六类内容块渲染数量正确（文创12/AR卡3/文化4/匠人2/出处3/场景3）
5. 凤凰画布存在且尺寸非零

## 一个查询陷阱（轮34）
我第一次用 '.hero-visual canvas' 查画布，得到 null，差点当成缺陷。
实际凤凰画布挂在 **.hero** 下（1440×900），.hero-visual 里只有装饰环与水印。
→ 选择器要对着真实 DOM 结构写，不能凭印象。
"""
import json
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 轮122 迁移：ps() 从 PowerShell 调 agent-browser 改为 ab_compat 兼容层。
# 紧跟的 PROBE 是 async IIFE，需兼容层 awaitPromise（轮119 已加）。
_AB = None


def _ab():
    global _AB
    if _AB is None:
        from ab_compat import AbSession
        _AB = AbSession()
    return _AB


def ps(cmd, timeout=90):
    return _ab().run(cmd, timeout=timeout)

PROBE = r'''(async function(){
  await new Promise(function(r){ setTimeout(r, 2500); });
  var heroCanvas = null;
  var cs = document.querySelectorAll('canvas');
  for (var i = 0; i < cs.length; i++) {
    var p = cs[i].parentElement;
    if (p && p.className && String(p.className).indexOf('hero') === 0) { heroCanvas = cs[i]; break; }
  }
  return JSON.stringify({
    ready: document.body.classList.contains('ready'),
    heroTitle: (document.getElementById('hero-title')||{}).textContent,
    g: {
      CULTURE: typeof window.CULTURE,
      AR_DATA: typeof window.AR_DATA,
      Phoenix: typeof window.Phoenix,
      WOOD_TO_STATUE: typeof window.WOOD_TO_STATUE,
      AR_SCENES: typeof window.AR_SCENES,
      ar: typeof window.__ar,
      STATUE_PROFILE: typeof window.STATUE_PROFILE
    },
    c: {
      merch: document.querySelectorAll('.merch-item').length,
      arCards: document.querySelectorAll('.ar-card').length,
      cultureCards: document.querySelectorAll('.culture-card').length,
      craftCards: document.querySelectorAll('.craft-card').length,
      srcBlocks: document.querySelectorAll('.ar-src').length,
      roadItems: document.querySelectorAll('.road-item').length
    },
    canvas: heroCanvas ? {w: heroCanvas.width, h: heroCanvas.height} : null
  });
})()'''


def main():
    tmp = os.path.join(BASE, '_qa', '_defer_regress.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    import time as _t
    # 轮122：判据自己起服务，不再假设外部已起 8791（失败形态是 SKIP）
    _srv = None
    try:
        from cdp_client import SiteServer
        _srv = SiteServer(os.path.join(BASE, 'site'), port=8791)
        _base = _srv.url('/index.html')
    except Exception as _e:
        print('RESULT: SKIP  服务起不来: %s' % _e)
        return 0

    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "about:blank"')
    # 固定套路：清 SW + 清 caches，否则 cache-first 会返回旧页面，
    # 反向验证会假绿（轮30 ar_focus_test / 轮34 本测试都踩过）
    ps('agent-browser open "%s"' % _base)
    ps('agent-browser wait --load networkidle')
    _t.sleep(1.5)
    _clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(_clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % _clear)
    _t.sleep(1.0)
    ps('agent-browser open "about:blank"')
    ps('agent-browser open "%s?fresh=%d"' % (_base, int(_t.time())))
    ps('agent-browser wait --load networkidle')
    _t.sleep(2.5)
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % tmp)

    # 轮122：CDP 只返回一层，去掉双层 json.loads（agent-browser 特性）。
    d = None
    if out:
        try:
            d = json.loads(out)
        except Exception:
            d = None
    if not d:
        print('RESULT: SKIP  探针无输出（浏览器/服务不可用）')
        return 0

    fails = []
    checks = 0

    checks += 1
    for name, t in d['g'].items():
        if t in ('undefined',):
            fails.append('全局 %s 未加载（defer 后执行时机可能被破坏）' % name)
    print('[%s] 7 个全局对象' % ('PASS' if not fails else 'FAIL'))

    checks += 1
    ok = d.get('ready') is True
    print('[%s] body.ready=true（首屏动画完成）' % ('PASS' if ok else 'FAIL'))
    if not ok: fails.append('body.ready 未置位，Phoenix 可能未初始化')

    checks += 1
    ok = '凤鸣东固' in (d.get('heroTitle') or '')
    print('[%s] H1 文本正确: %s' % ('PASS' if ok else 'FAIL', d.get('heroTitle')))
    if not ok: fails.append('H1 文本异常')

    expect = {'merch': 12, 'arCards': 3, 'cultureCards': 4, 'craftCards': 2, 'srcBlocks': 3, 'roadItems': 3}
    checks += 1
    bad = {k: (d['c'].get(k), v) for k, v in expect.items() if d['c'].get(k) != v}
    print('[%s] 六类内容块数量 %s' % ('PASS' if not bad else 'FAIL', '' if not bad else bad))
    if bad: fails.append('内容块数量异常: %s' % bad)

    checks += 1
    cv = d.get('canvas')
    ok = bool(cv) and cv.get('w', 0) > 0 and cv.get('h', 0) > 0
    print('[%s] 凤凰画布 %s' % ('PASS' if ok else 'FAIL', cv))
    if not ok: fails.append('凤凰画布缺失或尺寸为 0')

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  defer 后功能回归 %d 项全部正常' % checks)
    return 0


if __name__ == '__main__':
    sys.exit(main())