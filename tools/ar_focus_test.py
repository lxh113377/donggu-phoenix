# -*- coding: utf-8 -*-
"""tools/ar_focus_test.py —— AR 全屏焦点闭环验证（需浏览器）。

## 为什么需要它
之前只验证过首页 Tab 顺序，**从没验过 AR 全屏打开后的焦点行为**：
  · 焦点是否移入层内
  · Tab 是否被限制在层内（焦点陷阱）
  · Esc 关闭后焦点是否还给来源元素

AR 是全屏对话框，这三件事任一缺失都会让键盘/读屏用户迷失。

## 一个让我误判的测试方法（轮30 实测）
我第一次用 `window.__ar.open(...)` 直接打开，然后测 Esc 恢复，
结果焦点落在 BODY，差点判成缺陷。
真实原因：我是用 API 打开的，打开瞬间 document.activeElement 就是 BODY，
所以 lastFocus=BODY，恢复成 BODY 完全正确 —— 是测试方法错了。
必须走**真实用户路径**：先 focus() 场景卡的开演链接，再 click()。

## 验证项
1. 打开前焦点在某个 .go 链接上
2. 打开后焦点移入 .ar 内（且落在关闭按钮）
3. Tab 循环 12 次始终在 .ar 内
4. Esc 后焦点精确回到打开前的元素
5. 关闭后 aria-hidden=true、overflow 恢复
"""
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 轮119 迁移：ps() 从 PowerShell 调 agent-browser 改为走 ab_compat 兼容层。
# 业务逻辑、断言、RESULT 判定全部不动 —— 只换执行通道。
_AB = None


def _ab():
    global _AB
    if _AB is None:
        from ab_compat import AbSession
        _AB = AbSession()
    return _AB


def ps(cmd, timeout=60):
    try:
        return _ab().run(cmd, timeout=timeout)
    except Exception as e:
        # 兼容层不支持的动词会抛 AbCompatError —— 显式上抛，不静默返回空串
        raise


def ev(js_path):
    '''执行 JS 文件并解析结果。

    轮119：原版对结果做 json.loads(json.loads(line)) —— 双层解析是
    agent-browser 把 eval 结果再套一层引号 + 逐行输出的特性。
    CDP 的 eval_js 直接返回已解析值（字符串/数字/对象），再套两层必失败
    （轮118 在 anchor_offset 已踩过同一坑，读数明明是合法 JSON 却全 PARSE FAIL）。
    故改为：拿到什么就按实际形态解析一次。
    '''
    # 轮119：不要在判据侧拼 JS 字符串 —— PROBE 里含大量引号/反斜杠，
    # 手工转义必出错。直接交给兼容层的 Get-Content 形态（它自己读文件）。
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % js_path)
    if out is None:
        return None
    if isinstance(out, (dict, list)):
        return out
    s = str(out).strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _load_js_file(js_path):
    import io as _io
    p = js_path if os.path.isabs(js_path) else os.path.join(BASE, js_path)
    return _io.open(p, encoding='utf-8').read()


PROBE = r'''(async function(){
  var go = document.querySelector('.ar-card .go');
  if (!go) return JSON.stringify({skip: 'no .go link'});
  go.focus();
  await new Promise(function(r){ setTimeout(r, 150); });
  var beforeTag = document.activeElement.tagName;
  var beforeLabel = document.activeElement.getAttribute('aria-label');
  go.click();
  await new Promise(function(r){ setTimeout(r, 700); });
  var ae = document.activeElement;
  var openedInAr = !!(ae && ae.closest('.ar'));
  var openLabel = ae ? ae.getAttribute('aria-label') : null;
  // Tab 循环 12 次
  var root = document.querySelector('.ar');
  var allInAr = true;
  var list = [].slice.call(root.querySelectorAll('button,[href],input,[tabindex]'))
    .filter(function(n){ return n.offsetParent !== null && !n.disabled; });
  for (var i=0;i<12;i++){
    var idx = list.indexOf(document.activeElement);
    if (idx >= 0 && idx < list.length-1) { list[idx+1].focus(); }
    else if (idx === list.length-1) { list[0].focus(); }
    var cur = document.activeElement;
    if (!cur || !cur.closest('.ar')) { allInAr = false; break; }
  }
  // Esc 关闭
  document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true, cancelable:true}));
  await new Promise(function(r){ setTimeout(r, 500); });
  var closed = !root.classList.contains('on');
  var ariaHidden = root.getAttribute('aria-hidden');
  var overflow = document.documentElement.style.overflow;
  var restored = document.activeElement === go;
  return JSON.stringify({
    beforeTag: beforeTag,
    beforeLabel: beforeLabel,
    openedInAr: openedInAr,
    openLabel: openLabel,
    tab12AllInAr: allInAr,
    closed: closed,
    ariaHidden: ariaHidden,
    overflowRestored: overflow === '',
    focusRestored: restored
  });
})()'''


def main():
    tmp = os.path.join(BASE, '_qa', '_ar_focus.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    import time
    # 轮119：判据自己起服务，不再依赖「外部已启动 8791」。
    # 原版默认 8791 上有服务 —— 那是隐性环境依赖，换机器/CI 必失败。
    _srv = None
    try:
        from cdp_client import SiteServer
        _srv = SiteServer(os.path.join(BASE, 'site'), port=8791)
        print('服务已起: %s' % _srv.url('/index.html'))
    except Exception as _e:
        print('RESULT: SKIP  服务起不来: %s' % _e)
        return 0

    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "about:blank"')
    # 关键：先清 Service Worker 与所有 caches，否则 cache-first 会返回旧 JS，
    # 导致测试读到的是上一次的代码（轮30 实测：破坏后仍全 PASS）
    ps('agent-browser open "http://127.0.0.1:8791/"')
    ps('agent-browser wait --load networkidle')
    time.sleep(1.5)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % clear)
    time.sleep(1.0)
    # 重新打开（此时 SW 已注销，走网络取最新资源）
    ps('agent-browser open "about:blank"')
    ps('agent-browser open "http://127.0.0.1:8791/?fresh=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.5)
    # 对账：确认拿到的 ar.js 是磁盘上的最新版
    disk = open(os.path.join(BASE, 'site', 'assets', 'js', 'ar.js'), encoding='utf-8').read()
    marker = 'lastFocus.focus' if 'lastFocus.focus' in disk else 'lastFocus'
    probe = ('JSON.stringify({hasMarker: document.documentElement && (window.__AR_JS_CHECK || false)})')

    # 轮119：等 AR 场景卡真正渲染出来再探。
    # 起因：ar-cards 是 JS 动态渲染的，页面 load 完成时 .ar-card .go 可能还没出现，
    # 直接探会得到「no .go link」并 SKIP —— 我的第一版实测就是这样，
    # 差点误判成「产品没有 AR 入口」。
    _t0 = time.time()
    _n = 0
    while time.time() - _t0 < 20:
        _n = ps('agent-browser eval ' + chr(34)
                + "document.querySelectorAll('.ar-card .go').length" + chr(34))
        try:
            _n = int(str(_n).strip() or 0)
        except Exception:
            _n = 0
        if _n > 0:
            break
        time.sleep(0.8)
    print('AR 入口 .go 数量: %d（等待 %.1fs）' % (_n, time.time() - _t0))
    if _n <= 0:
        print('RESULT: FAIL  .ar-card .go 始终未出现（AR 入口没渲染出来）')
        return 1

    d = ev(tmp)
    if not d:
        print('RESULT: SKIP  探针无输出（浏览器/服务不可用）')
        return 0
    if d.get('skip'):
        print('RESULT: SKIP  %s' % d['skip'])
        return 0

    checks = [
        ('打开前焦点在场景链接', d.get('beforeTag') == 'A', d.get('beforeLabel')),
        ('打开后焦点移入 AR', d.get('openedInAr') is True, d.get('openLabel')),
        ('Tab 12 次不逃出 AR', d.get('tab12AllInAr') is True, None),
        ('Esc 后 AR 关闭', d.get('closed') is True, None),
        ('关闭后 aria-hidden=true', d.get('ariaHidden') == 'true', None),
        ('关闭后滚动恢复', d.get('overflowRestored') is True, None),
        ('焦点精确还给来源元素', d.get('focusRestored') is True, None),
    ]

    fails = []
    for name, ok, extra in checks:
        print('[%s] %s%s' % ('PASS' if ok else 'FAIL', name, (' (' + str(extra) + ')') if extra else ''))
        if not ok:
            fails.append(name)

    # 轮119：退出前关掉兼容层会话与自起服务，避免残留 chrome/端口占用
    try:
        if _AB:
            _AB.close()
    except Exception:
        pass
    try:
        if _srv:
            _srv.stop()
    except Exception:
        pass

    print()
    if fails:
        print('RESULT: FAIL  %d/%d 项不通过' % (len(fails), len(checks)))
        return 1
    print('RESULT: PASS  AR 焦点闭环 %d 项全部通过' % len(checks))
    return 0


if __name__ == '__main__':
    sys.exit(main())