# -*- coding: utf-8 -*-
"""tools/cjk_typography_test.py —— 中文排版基线判据（纯静态，CI 可跑）。

## 为什么需要它
这是中文内容站，但中文排版质量很少被工程化检查。
轮35 逐项核查后确认当前**无缺陷**，但结论需要固化成判据：
否则以后改动可能悄悄破坏这些性质。

## 核查过并确认无需改动的项（避免以后重复纠结）
| 项 | 实测 | 判断 |
|---|---|---|
| 标点行首（避头尾） | 0 处 | 浏览器 line-break:auto 已应用 UAX#14 |
| 中西文间距 text-autospace | 正文几乎无混排 | 混排都在设计性副标题，有意为之 |
| 标点挤压 text-spacing-trim | Chrome 123+ | 收益小，不加（避免过度优化）|
| .carve-lineage 77字/行 | 实为 flex 三标签 | 测量误报 |
| word-break:keep-all 于标题 | overflow=false | · 提供断行点 |

## 判据（防回归）
1. html 必须有 lang="zh-CN"（中文语言声明）
2. 中文正文不能设 word-break:break-all（会导致标点行首、词语腰斩）
3. 长文本块必须有 max-width 约束（防止行长过长）
4. 若引入 text-autospace，必须同时确认页面确有中西混排（避免无效属性）
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
HTML = os.path.join(BASE, 'site', 'index.html')


def main():
    if not os.path.exists(CSS) or not os.path.exists(HTML):
        print('RESULT: SKIP  找不到 main.css 或 index.html')
        return 0

    css = re.sub(r'/\*.*?\*/', ' ', open(CSS, encoding='utf-8').read(), flags=re.S)
    html = open(HTML, encoding='utf-8').read()

    fails = []
    checked = 0

    # 1) lang 声明
    checked += 1
    m = re.search(r'<html[^>]*lang="([^"]+)"', html)
    if not m:
        fails.append('html 缺少 lang 声明')
    elif not m.group(1).lower().startswith('zh'):
        fails.append('html lang=%s，应为 zh-CN' % m.group(1))
    else:
        print('[PASS] html lang=%s' % m.group(1))

    # 2) 中文正文不得 break-all
    checked += 1
    bad = []
    for mm in re.finditer(r'([^{}]+)\{([^}]*word-break\s*:\s*break-all[^}]*)\}', css):
        sel = mm.group(1).strip().split(chr(10))[-1]
        # 允许：URL / 二维码回退等西文长串
        if any(k in sel for k in ['url', 'qr-fallback', 'foot-copy']):
            continue
        bad.append(sel[:40])
    if bad:
        fails.append('中文元素用了 word-break:break-all（会标点行首/词语腰斩）: %s' % bad[:3])
    else:
        print('[PASS] word-break:break-all 仅用于西文长串')

    # 3) 长文本块有 max-width
    checked += 1
    # 长文本块需有宽度上限：自身 max-width，或父级 grid/flex 的 minmax/min()
    long_text_blocks = ['.hero-lead', '.carve-note', '.sec-head p']
    missing = []
    for sel in long_text_blocks:
        pat = re.escape(sel) + r'(?:\s*,[^{]*)?\{([^}]*)\}'
        mm = re.search(pat, css)
        if mm and 'max-width' in mm.group(1):
            continue
        # 例外：.sec-head p 由父级 .sec-head 的 grid minmax(0, min(34em,42%)) 约束
        if sel == '.sec-head p':
            if re.search(r'\.sec-head\s*\{[^}]*grid-template-columns[^}]*min\(' , css):
                continue
        missing.append(sel)
    if missing:
        fails.append('长文本块缺 max-width（行长可能过长）: %s' % missing)
    else:
        print('[PASS] %d 个长文本块均有 max-width' % len(long_text_blocks))

    # 4) 若用 text-autospace，必须有中西混排
    checked += 1
    if 'text-autospace' in css:
        # 粗略判断：数据层是否有混排
        has_mix = False
        for f in ['culture.js', 'ar-data.js']:
            p = os.path.join(BASE, 'site', 'assets', 'data', f)
            if os.path.exists(p):
                t = open(p, encoding='utf-8').read()
                if re.search(r'[\u4e00-\u9fff][A-Za-z0-9]', t):
                    has_mix = True
                    break
        if not has_mix:
            fails.append('用了 text-autospace 但正文无中西混排（无效属性）')
        else:
            print('[PASS] text-autospace 有实际作用对象')
    else:
        print('[PASS] 未引入 text-autospace（正文无中西混排，无需）')

    print()
    print('检查 %d 项中文排版基线' % checked)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  中文排版基线 %d 项全部成立' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())