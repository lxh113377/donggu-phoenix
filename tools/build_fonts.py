# -*- coding: utf-8 -*-
"""tools/build_fonts.py — 生成自托管 woff2 子集（展示字体 + 拉丁展示字体）。
源字体不入仓（体积大且需许可声明），本机已下载到 _dev/fonts/（见 docs/交付说明.md 的字体许可段）。
用法: python tools/build_fonts.py
输出: site/assets/fonts/{zcool-display,cinzel}.woff2 + site/assets/fonts/glyphs.txt（字符清单，供 verify 对账）
"""
import glob, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
FONT_SRC = os.path.join(BASE, "_dev", "fonts")
OUT = os.path.join(SITE, "assets", "fonts")

sys.path.insert(0, os.path.join(BASE, "tools"))


def strip_comments(s, is_html):
    """剥掉注释 —— 注释里的字符永远不会被渲染。

    一手问题（2026-10-20 轮50）：scan_chars 原先把整份文件的字符收进子集，
    于是「在源码里新写一段中文注释」会直接放大线上 woff2（实测 +117KB，越过 260KB 险线），
    而 verify 第 20 项字体完整性判据是**剥注释后**再查缺字的，两侧口径不一致：
    生成物在为不会显示的字付体积，判据又抓不到这种膨胀。口径必须统一。
    与 verify 用同一套规则（块注释、// 到行尾、HTML 注释），不再各写一份。
    """
    if is_html:
        s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
        # HTML 模式不做 // 剥离：// 在 HTML 属性里是 URL 协议符（https://…），
        # 剥了会把 URL 之后的渲染文本整段误删（2026-10-21 实测：escape-link 的
        # 「受限时用」四字被连坐，子集缺字、门禁 FAIL）。
        return re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"//[^\n]*", " ", s)
    return s


def scan_chars():
    """展示层字符集：全站 HTML/JS/CSS/SVG/manifest 的非注释文本。"""
    chars = set()
    n = 0
    for p in glob.glob(os.path.join(SITE, "**", "*.*"), recursive=True):
        if not p.endswith((".html", ".js", ".css", ".webmanifest", ".svg")):
            continue
        raw = open(p, encoding="utf-8", errors="ignore").read()
        chars |= set(strip_comments(raw, p.endswith((".html", ".svg"))))
        n += 1
    scan_chars.files = n
    return {c for c in chars if c.strip()}


def build(src, text, out):
    from fontTools import subset
    subset.main([src, "--text=" + text, "--layout-features=", "--no-hinting",
                 "--desubroutinize", "--flavor=woff2", "--output-file=" + out])
    return os.path.getsize(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    zcool = os.path.join(FONT_SRC, "ZCOOLXiaoWei-Regular.ttf")
    cinzel = os.path.join(FONT_SRC, "Cinzel.ttf")
    if not (os.path.exists(zcool) and os.path.exists(cinzel)):
        print("缺少源字体：请先按 docs/交付说明.md「字体」段下载到 _dev/fonts/")
        return 2
    chars = scan_chars()
    text = "".join(sorted(chars))
    with open(os.path.join(OUT, "glyphs.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    size = build(zcool, text, os.path.join(OUT, "zcool-display.woff2"))
    zh = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    print("zcool-display.woff2", size, "bytes /", len(text), "chars /", zh, "汉字"
          "（扫描", getattr(scan_chars, "files", 0), "文件，已剥注释）")
    latin = "".join(chr(c) for c in range(32, 127)) + "·—–…“”‘’×"
    size2 = build(cinzel, latin, os.path.join(OUT, "cinzel.woff2"))
    print("cinzel.woff2", size2, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
