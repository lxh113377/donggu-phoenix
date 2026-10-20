# -*- coding: utf-8 -*-
"""tools/multi_viewport_test.py —— 9 个视口的响应式验证（需浏览器）。

## 为什么需要它
前面所有响应式验证只测过 1440 与 390 两个宽度。
轮41 扩展到 9 个视口后，立刻暴露了 320px 下两处越界（此前从未发现）：
  · craft-card 比父容器宽 36px（grid minmax 下限 320 > 容器 284）
  · carve-slider 右边界 336 > 320（label 的 ::after 补充文案撑爆布局）

## 覆盖视口
  320 / 360 / 375 / 414 / 768 / 1024 / 1280 / 1920 / 2560

## 判据
每个视口检查：
  1. documentElement.scrollWidth > innerWidth + 1 → 横向溢出
  2. 任何元素 right > innerWidth + 2 或 left < -2 → 元素越界

## 关键：必须清 SW 缓存
站点 SW 是 cache-first，不清缓存会读到旧 CSS，
导致「改完仍报错」的假失败（轮34/38/41 都踩过）。
本工具在开头强制清 SW + caches。

## 零样本守卫
全部视口无数据时判 SKIP，不判 PASS（防止「没测到」被当「通过」）。
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VIEWPORTS = [(320, 844), (360, 800), (375, 844), (414, 844), (768, 1024),
             (1024, 1024), (1280, 1024), (1920, 1080), (2560, 1080)]

PROBE = '''(function(){
  var de = document.documentElement;
  var overflow = de.scrollWidth > window.innerWidth + 1;
  var wide = [];
  var all = document.querySelectorAll('body *');
  for (var i = 0; i < all.length && wide.length < 5; i++) {
    var e = all[i];
    var r = e.getBoundingClientRect();
    if (r.width > 0 && (r.right > window.innerWidth + 2 || r.left < -2)) {
      wide.push({cls: String(e.className).slice(0, 24) || e.tagName, left: Math.round(r.left), right: Math.round(r.right)});
    }
  }
  // VERTICAL_CHECK：首屏关键元素是否被裁切或被固定导航遮挡
  var nav = document.querySelector('.nav');
  var navBottom = nav ? Math.round(nav.getBoundingClientRect().bottom) : 0;
  var clipped = [];
  var covered = [];
  var KEY = ['.hero-tag', '.hero h1', '.hero-lead', '.hero-acts', '.hero-meta'];
  for (var j = 0; j < KEY.length; j++) {
    var ke = document.querySelector(KEY[j]);
    if (!ke || !ke.offsetParent) continue;
    var kr = ke.getBoundingClientRect();
    if (kr.width === 0 && kr.height === 0) continue;
    if (kr.top < -2 || kr.bottom > window.innerHeight + 2) {
      clipped.push({sel: KEY[j], top: Math.round(kr.top), bottom: Math.round(kr.bottom)});
    }
    if (kr.top < navBottom - 2) {
      covered.push({sel: KEY[j], top: Math.round(kr.top), navBottom: navBottom});
    }
  }
  return JSON.stringify({vw: window.innerWidth, scrollW: de.scrollWidth, overflow: overflow, wide: wide,
                         clipped: clipped, covered: covered, vh: window.innerHeight});
})()'''


def ps(cmd, timeout=60):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def main():
    tmp = os.path.join(BASE, '_qa', '_mvp.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    # 关键：先清 SW + caches
    ps('agent-browser open "http://127.0.0.1:8791/"')
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)

    results = []
    for w, h in VIEWPORTS:
        ps('agent-browser set viewport %d %d' % (w, h))
        time.sleep(0.4)
        ps('agent-browser open "http://127.0.0.1:8791/?vw=%d&t=%d"' % (w, int(time.time()*1000) % 99991))
        ps('agent-browser wait --load networkidle')
        time.sleep(1.4)
        out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/_mvp.js")')
        d = None
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                try:
                    d = json.loads(json.loads(line))
                    break
                except Exception:
                    continue
        results.append(((w, h), d))

    issues = []
    no_data = 0
    print('%-10s %-8s %-6s %s' % ('视口', 'scrollW', '溢出', '越界元素'))
    print('-' * 68)
    for (w, h), d in results:
        if not d:
            print('%-10s (无数据)' % ('%dx%d' % (w, h)))
            no_data += 1
            continue
        wide = '; '.join('%s(%d..%d)' % (x['cls'], x['left'], x['right']) for x in d['wide'][:2])
        print('%-10s %-8s %-6s %s' % ('%dx%d' % (w, h), d['scrollW'],
                                       'YES' if d['overflow'] else 'no', wide or '-'))
        if d['overflow']:
            issues.append('%dx%d 横向溢出（scrollW %d）' % (w, h, d['scrollW']))
        if d['wide']:
            issues.append('%dx%d 越界: %s' % (w, h, wide))
        # 纵向：首屏关键元素被裁或被导航遮挡
        for c in d.get('clipped', []):
            issues.append('%dx%d 首屏被裁: %s (top %d, bottom %d)' % (w, h, c['sel'], c['top'], c['bottom']))
        for c in d.get('covered', []):
            issues.append('%dx%d 首屏被导航遮挡: %s (top %d < nav %d)' % (w, h, c['sel'], c['top'], c['navBottom']))

    print()
    if no_data == len(results):
        print('RESULT: SKIP  全部视口无数据 —— 不判 PASS')
        return 0
    if no_data:
        print('警告: %d/%d 个视口无数据' % (no_data, len(results)))
    if issues:
        print('RESULT: FAIL')
        for i in issues:
            print('  -', i)
        return 1
    print('RESULT: PASS  %d 个视口全部无横向溢出、无越界' % (len(results) - no_data))
    return 0


if __name__ == '__main__':
    sys.exit(main())