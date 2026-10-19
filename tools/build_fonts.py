# -*- coding: utf-8 -*-
"""tools/build_fonts.py — 生成自托管 woff2 子集（展示字体 + 拉丁展示字体）。
源字体不入仓（体积大且需许可声明），本机已下载到 _dev/fonts/（见 docs/交付说明.md 的字体许可段）。
用法: python tools/build_fonts.py
输出: site/assets/fonts/{zcool-display,cinzel}.woff2 + site/assets/fonts/glyphs.txt（字符清单，供 verify 对账）
"""
import glob, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
FONT_SRC = os.path.join(BASE, '_dev', 'fonts')
OUT = os.path.join(SITE, 'assets', 'fonts')

sys.path.insert(0, os.path.join(BASE, 'tools'))


def scan_chars():
    """展示层字符集：HTML 可见文本 + 数据层中文串 + 全站 JS/CSS 文本。"""
    import re
    chars = set()
    for p in glob.glob(os.path.join(SITE, '**', '*.*'), recursive=True):
        if p.endswith(('.html', '.js', '.css', '.webmanifest', '.svg')):
            chars |= set(open(p, encoding='utf-8', errors='ignore').read())
    return {c for c in chars if c.strip()}


def build(src, text, out):
    from fontTools import subset
    subset.main([src, '--text=' + text, '--layout-features=', '--no-hinting',
                 '--desubroutinize', '--flavor=woff2', '--output-file=' + out])
    return os.path.getsize(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    zcool = os.path.join(FONT_SRC, 'ZCOOLXiaoWei-Regular.ttf')
    cinzel = os.path.join(FONT_SRC, 'Cinzel.ttf')
    if not (os.path.exists(zcool) and os.path.exists(cinzel)):
        print('缺少源字体：请先按 docs/交付说明.md「字体」段下载到 _dev/fonts/')
        return 2
    chars = scan_chars()
    text = ''.join(sorted(chars))
    with open(os.path.join(OUT, 'glyphs.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    size = build(zcool, text, os.path.join(OUT, 'zcool-display.woff2'))
    print('zcool-display.woff2', size, 'bytes /', len(text), 'chars')
    latin = ''.join(chr(c) for c in range(32, 127)) + '·—–…“”‘’×'
    size2 = build(cinzel, latin, os.path.join(OUT, 'cinzel.woff2'))
    print('cinzel.woff2', size2, 'bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
