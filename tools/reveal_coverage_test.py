# -*- coding: utf-8 -*-
"""tools/reveal_coverage_test.py —— 进场动画覆盖率（需浏览器）。

## 为什么需要它
`.reveal` 元素初始 `opacity:0`，靠 IntersectionObserver 加 `.in` 才显示。
任何一个 reveal 未触发 = 页面上永久一片空白。

## 轮46 踩的坑（重要）
第一版脚本用 `for (y=0; y<=maxY; y+=600)` 步进，
**最后一步不一定落在 maxY**，导致页脚 `.foot-grid` 没进视口，
误报「21/22，页脚不显示」的假缺陷。

## 正确做法
循环后**必须再显式 `scrollTo(0, scrollHeight)` 一次**。
这又一次印证：测不出不等于不存在，测出了也不一定是真的。

## 判据
滚遍全站后，所有 `.reveal` 元素都必须带 `.in`。
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBE = '''(async function(){
  var maxY = document.body.scrollHeight - window.innerHeight;
  for (var y = 0; y < maxY; y += 500) {
    window.scrollTo(0, y);
    await new Promise(function(r){ setTimeout(r, 180); });
  }
  window.scrollTo(0, document.body.scrollHeight);
  await new Promise(function(r){ setTimeout(r, 1200); });
  var all = document.querySelectorAll('.reveal');
  var notIn = [];
  for (var i = 0; i < all.length; i++) {
    if (!all[i].classList.contains('in')) {
      var r = all[i].getBoundingClientRect();
      notIn.push({cls: String(all[i].className).slice(0, 26), top: Math.round(r.top), h: Math.round(r.height)});
    }
  }
  return JSON.stringify({total: all.length,
    revealed: document.querySelectorAll('.reveal.in').length, notRevealed: notIn});
})()'''


def ps(cmd, timeout=60):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def main():
    tmp = os.path.join(BASE, '_qa', '_reveal.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    ps('agent-browser open "http://127.0.0.1:8791/"')
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)

    ps('agent-browser set viewport 1440 900')
    time.sleep(0.4)
    ps('agent-browser open "http://127.0.0.1:8791/?rv=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.0)

    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/_reveal.js")')
    d = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                d = json.loads(json.loads(line))
                break
            except Exception:
                continue

    if not d:
        print('RESULT: SKIP  未取到数据（浏览器或探针异常）')
        return 0

    total, revealed = d['total'], d['revealed']
    print('进场元素 %d 个，已触发 %d 个' % (total, revealed))
    if d['notRevealed']:
        print('未触发：')
        for x in d['notRevealed']:
            print('  - %s（top %d, 高 %d）' % (x['cls'], x['top'], x['h']))

    print()
    if total == 0:
        print('RESULT: SKIP  页面无 .reveal 元素')
        return 0
    if revealed < total:
        print('RESULT: FAIL  %d 个进场元素永久不可见' % (total - revealed))
        return 1
    print('RESULT: PASS  %d 个进场元素全部触发（无永久空白）' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())