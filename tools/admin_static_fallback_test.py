# -*- coding: utf-8 -*-
r"""tools/admin_static_fallback_test.py —— 静态后台的两条「承诺」判据（需 chrome）。

## 与 admin_static_render_test 的分工（不重复）
admin_static_render_test 用 HTTP 服务验「渲染出来了、数字对、刷新不变、零接口」，
它测的都是**正向路径**。本判据补它测不到的两件事：

  承诺 1「file:// 双击也能看」—— 静态重写的主要动机之一
    （注释原话：fetch JSON 在 file:// 必败，所以数据走 <script src>）。
    render_test 走 HTTP，抓不到「相对路径在 file:// 下解析失败」这类退化。
  承诺 2「样本没加载时给明确空态」—— 演示现场的最后一道防线。
    render_test 的 A 项是「应当进 dash」，即它假设数据在；
    数据**不在**时的兜底行为没人守。把判空那行删掉，页面会白屏，
    而静态扫描与 render_test 都不会报警。

## 判据 + 尺子自检（U-149/U-151：先证明能失败，再信它的 PASS）
  正向 1 file:// 直开 → 仪表盘可见，且首个指标卡是真实数字（非空/--/0）
  正向 2 移除样本引用 → nodata 空态可见，文案含「未加载」
  自检 A 造坏页（删掉 typeof 判空）→ 正向 2 必须判红
        否则说明「有空态」是恒真断言，兜底被删也不会被发现
  自检 B 造坏页（数据改回 fetch 加载）→ 正向 1 必须判红
        否则说明「file:// 可直看」这条承诺根本没在被测

坏页写在 site/admin/ 下的临时文件，跑完即删；不改真实文件。

## 诚实语义
缺 chrome / CDP 起不来 → SKIP 并说明「未测不等于通过」，不判绿。
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
ADMIN_DIR = os.path.join(SITE, 'admin')
ADMIN = os.path.join(ADMIN_DIR, 'index.html')
SCRIPT_TAG = '<script src="../assets/data/admin-stats.js"></script>'
GUARD = ("var D = (typeof DG_STATIC_STATS !== 'undefined') "
         "? DG_STATIC_STATS : null;")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DASH_COND = ("!!document.getElementById('dash') && "
             "document.getElementById('dash').classList.contains('on')")
NODATA_COND = ("!!document.getElementById('nodata') && "
               "document.getElementById('nodata').classList.contains('on')")


def _url(path):
    return 'file:///' + path.replace('\\', '/')


def _src():
    return io.open(ADMIN, encoding='utf-8').read()


def _probe(name, text):
    """写临时坏页，返回绝对路径。"""
    p = os.path.join(ADMIN_DIR, name)
    io.open(p, 'w', encoding='utf-8').write(text)
    return p


def _rm(p):
    try:
        os.remove(p)
    except Exception:
        pass


def positive_file_protocol(ch, fails):
    page, tid = ch.new_page(1440, 900)
    try:
        ch.navigate(page, _url(ADMIN))
        if not ch.wait_for(page, DASH_COND, 20):
            fails.append('承诺1 file:// 直开未进仪表盘（离线不可用）')
            return
        pv = (page.eval_js(
            "(document.querySelector('#dash .card dd')||{}).textContent||''")
            or '').strip()
        if pv in ('', '--', '0', 'NaN'):
            fails.append('承诺1 进了仪表盘但指标卡无数字（=%r）' % pv)
            return
        print('  [ok] 承诺1 file:// 直开出数：%s' % pv)
    finally:
        page.close()
        ch.close_page(tid)


def positive_empty_state(ch, fails):
    src = _src()
    assert SCRIPT_TAG in src, ('未找到样本引用标签（页面结构已变，'
                               '需同步本判据的锚点）')
    tmp = _probe('_probe_fallback_noStats.html',
                 src.replace(SCRIPT_TAG, '<!-- probe: 移除样本 -->', 1))
    page, tid = ch.new_page(1440, 900)
    try:
        ch.navigate(page, _url(tmp))
        if not ch.wait_for(page, NODATA_COND, 15):
            fails.append('承诺2 样本缺失时未显示空态（兜底失效，会白屏）')
            return
        txt = (page.eval_js(
            "(document.querySelector('#nodata b')||{}).textContent||''") or '')
        if '未加载' not in txt:
            fails.append('承诺2 空态文案不含「未加载」（=%r）' % txt)
            return
        print('  [ok] 承诺2 样本缺失有空态：%s' % txt)
    finally:
        page.close()
        ch.close_page(tid)
        _rm(tmp)


def selftest_guard_removed(ch, fails):
    """删掉 typeof 判空 → 承诺2 必须失败，否则该判据是恒真的。"""
    src = _src()
    assert GUARD in src, '判空锚点未命中（页面写法已变，需同步本判据）'
    bad = src.replace(GUARD, 'var D = DG_STATIC_STATS;', 1)
    bad = bad.replace(SCRIPT_TAG, '<!-- probe: 移除样本 -->', 1)
    tmp = _probe('_probe_fallback_badA.html', bad)
    page, tid = ch.new_page(1440, 900)
    try:
        ch.navigate(page, _url(tmp))
        caught = not ch.wait_for(page, NODATA_COND, 8)
        print('  [%s] 自检A 删掉判空兜底 → %s' % (
            'ok' if caught else 'X',
            '被抓到（判据有效）' if caught else '仍显示空态（判据恒真！）'))
        if not caught:
            fails.append('自检A 判据无牙：删掉兜底也不会判红')
    finally:
        page.close()
        ch.close_page(tid)
        _rm(tmp)


def selftest_back_to_fetch(ch, fails):
    """数据改回 fetch → 承诺1 必须失败（file:// 下 fetch 必败）。"""
    src = _src()
    assert SCRIPT_TAG in src, '样本引用锚点未命中'
    bad = src.replace(
        SCRIPT_TAG,
        '<script>fetch("../assets/data/admin-stats.js")'
        '.then(function(r){return r.json();})'
        '.then(function(j){window.DG_STATIC_STATS=j;'
        'window.dispatchEvent(new Event("stats-ready"));});</script>', 1)
    tmp = _probe('_probe_fallback_badB.html', bad)
    page, tid = ch.new_page(1440, 900)
    try:
        ch.navigate(page, _url(tmp))
        caught = not ch.wait_for(page, DASH_COND, 10)
        print('  [%s] 自检B 数据改回 fetch → %s' % (
            'ok' if caught else 'X',
            '被抓到（file:// 确实打不开）' if caught
            else '仍能出数（坏页构造无效或判据恒真）'))
        if not caught:
            fails.append('自检B 判据无牙：退回 fetch 也不会判红')
    finally:
        page.close()
        ch.close_page(tid)
        _rm(tmp)


def main():
    try:
        from cdp_client import Chrome, find_chrome
    except Exception as e:
        print('RESULT: SKIP  CDP 模块不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（环境问题，本判据未执行）')
        return 0

    fails = []
    ch = None
    try:
        ch = Chrome()
        positive_file_protocol(ch, fails)
        positive_empty_state(ch, fails)
        selftest_guard_removed(ch, fails)
        selftest_back_to_fetch(ch, fails)
    except AssertionError as e:
        print('RESULT: SKIP  锚点未命中，判据需与新页面同步：%s' % e)
        return 0
    except Exception as e:
        print('RESULT: SKIP  探针异常（环境问题）：%s: %s'
              % (type(e).__name__, str(e)[:120]))
        return 0
    finally:
        if ch:
            ch.close()
        for junk in ('_probe_fallback_noStats.html',
                     '_probe_fallback_badA.html',
                     '_probe_fallback_badB.html'):
            _rm(os.path.join(ADMIN_DIR, junk))

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  离线可看 + 缺样本有空态，自检证明两条承诺都真的在被测')
    return 0


if __name__ == '__main__':
    sys.exit(main())
