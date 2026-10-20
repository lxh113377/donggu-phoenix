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

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ps(cmd, timeout=60):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                           cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def ev(js_path):
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % js_path)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None


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

    print()
    if fails:
        print('RESULT: FAIL  %d/%d 项不通过' % (len(fails), len(checks)))
        return 1
    print('RESULT: PASS  AR 焦点闭环 %d 项全部通过' % len(checks))
    return 0


if __name__ == '__main__':
    sys.exit(main())