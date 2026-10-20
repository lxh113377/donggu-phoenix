# -*- coding: utf-8 -*-
"""tools/critical_path_test.py —— 脚本不得阻塞首屏解析（纯静态，CI 可跑）。

## 为什么需要它（U-11 终于定位到根因）
前几轮反复查 DCL 223ms / FCP 216ms 的构成，排除了字体、backdrop-filter 等假设。
本轮用静态分析找到真正原因：

  HTML 第 377-385 行有 **9 个同步 <script>**（无 defer/async），
  合计 163.4KB 原始 / 58.2KB gzip。
  浏览器必须对每个脚本「下载 → 解析 → 执行」完才继续解析后续 HTML，
  DCL 因此被整条脚本链推后。

改为 defer 后：HTML 解析不再被阻塞，defer 脚本在 DOM 解析完成后按序执行。

## 判据
site/index.html 里所有带 src 的 <script> 必须有 defer 或 async。
inline script 豁免（不能加 defer，且 W3C 不允许）。

## 为什么 async 也放行
async 同样不阻塞解析。但对本仓，async 会打乱执行顺序、破坏依赖链，
所以实际应优先 defer —— 判据只禁止「完全阻塞」这一种情况。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, 'site', 'index.html')


def main():
    if not os.path.exists(HTML):
        print('RESULT: SKIP  找不到 index.html')
        return 0

    s = open(HTML, encoding='utf-8').read()
    fails = []
    checked = 0
    inline = 0

    for m in re.finditer(r'<script([^>]*)>', s):
        attrs = m.group(1)
        src = re.search(r'src="([^"]+)"', attrs)
        if not src:
            inline += 1
            continue
        checked += 1
        if 'defer' not in attrs and 'async' not in attrs:
            fails.append('阻塞解析的脚本: %s' % src.group(1))

    # VERSION_SYNC：改了 index.html 必须同步三处版本（CSS --build / HTML BUILD / SW VERSION）。
    # 一手问题（轮33）：A/B 测试脚本 finally 里整体还原 index.html，把刚 bump 的 BUILD 抹掉了。
    css_p = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
    sw_p = os.path.join(BASE, 'site', 'sw.js')
    if os.path.exists(css_p):
        css_t = open(css_p, encoding='utf-8').read()
        m_css = re.search(r'--build:(\d+);', css_t)
        m_html = re.search(r"var BUILD = '(\d+)';", s)
        if m_css and m_html and m_css.group(1) != m_html.group(1):
            fails.append('版本对账不一致：CSS --build=%s ≠ HTML BUILD=%s' % (m_css.group(1), m_html.group(1)))

    print('检查 %d 个外部脚本（另有 %d 个 inline，豁免）' % (checked, inline))
    if checked == 0:
        print()
        print('RESULT: SKIP  未找到外部脚本')
        return 0

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        print()
        print('处置：加 defer（保持顺序）或 async（可乱序时）。')
        return 1
    print('RESULT: PASS  %d 个外部脚本均不阻塞 HTML 解析' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())