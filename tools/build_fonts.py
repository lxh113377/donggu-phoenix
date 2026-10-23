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
    # --layout-features=kern：只保留字距调整，其余（liga/calt/ss01…）仍裁掉，
    # 体积代价实测仅 +2~3KB/字体（cinzel 13.7->16.4，zcool 219.5->221.8）。
    #
    # 原先这里是 "--layout-features="（空值）= 主动裁掉全部排版特性，
    # 后果是站里所有拉丁展示文字（标题、章节序号、时间、页脚计数）
    # 都失去 kerning，只能靠 letter-spacing 粗调 —— 而这类失效是静默的：
    # CSS 合法、浏览器不报错、DevTools 看着像生效，只有量字距对才发现为零。
    # 顺带查清一件事：Cinzel 源字体本身没有 tnum 特性（只有 calt/dlig/locl/
    # onum/ss01/ss02），所以 CSS 里 5 处 font-variant-numeric:tabular-nums
    # 无论怎么裁都不会生效，那是另一条要单独处理的问题（见台账）。
    subset.main([src, "--text=" + text, "--layout-features=kern",
                 "--no-hinting", "--desubroutinize", "--flavor=woff2",
                 "--output-file=" + out])
    # 产出校验：子集库在某些版本下会静默忽略 --layout-features，
    # 所以不能假设参数写了就生效 —— 直接读回产物数字距查找数。
    from fontTools.ttLib import TTFont
    f = TTFont(out)
    try:
        n = 0
        if "GPOS" in f and f["GPOS"].table.LookupList:
            n = len(f["GPOS"].table.LookupList.Lookup)
        has_kern_table = "kern" in f
    finally:
        f.close()
    if n == 0 and not has_kern_table:
        raise SystemExit("子集 %s 没有字距数据：--layout-features 未生效，"
                         "不要让无 kern 的字体上线" % out)
    print("  %s 字距查找(GPOS)=%d kern表=%s" % (os.path.basename(out), n,
                                                has_kern_table))
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
