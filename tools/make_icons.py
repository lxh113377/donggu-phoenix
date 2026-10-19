# -*- coding: utf-8 -*-
"""生成 PWA 应用图标（原创绘制，无外部素材）。

设计取自站点 hero 已有的「畲」字印章：深底 #0B0908 + 金环 + 楷体「畲」。
输出到 site/assets/img/icons/，供 manifest.webmanifest 与 apple-touch-icon 使用。

用法：python tools/make_icons.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "site", "assets", "img", "icons")

BG = (11, 9, 8)          # --ink，与 index.html 的 theme-color 一致
BG_SOFT = (26, 20, 18)   # --ink-2
GOLD = (212, 162, 76)    # --gold
GOLD_L = (232, 183, 97)  # --gold-l
FG = (242, 233, 220)     # --fg

# 只出必要尺寸：PWA 要求 192/512（含 maskable），apple-touch-icon 180，256 作高分兜底。
# 实测 64/96 档「畲」字笔画已糊成一团，出它反而拉低观感，故不生成。
SIZES = [180, 192, 256, 512]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simkai.ttf",   # 楷体：与站点 --font-kai 同族
    r"C:\Windows\Fonts\STHUPO.TTF",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/Kaiti.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
]


def find_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make(size):
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)

    cx = cy = size / 2
    # 外金环（maskable 安全区内：内容整体留 20% 边距）
    inset = size * 0.11
    d.ellipse([inset, inset, size - inset, size - inset],
              outline=GOLD, width=max(2, round(size * 0.016)))
    inset2 = size * 0.17
    d.ellipse([inset2, inset2, size - inset2, size - inset2],
              outline=GOLD_L, width=max(1, round(size * 0.008)))

    # 内底稍亮，托住字形
    d.ellipse([size * 0.19, size * 0.19, size * 0.81, size * 0.81], fill=BG_SOFT)

    # 「畲」字居中
    f = find_font(int(size * 0.46))
    try:
        box = d.textbbox((0, 0), "畲", font=f)
        tw, th = box[2] - box[0], box[3] - box[1]
        d.text((cx - tw / 2 - box[0], cy - th / 2 - box[1]), "畲", font=f, fill=FG)
    except Exception:
        d.text((cx, cy), "畲", font=f, fill=FG)

    # 四角银点（呼应凤凰装银饰鸣啭）
    for sx in (0.26, 0.74):
        for sy in (0.26, 0.74):
            r = max(1.2, size * 0.012)
            d.ellipse([size * sx - r, size * sy - r, size * sx + r, size * sy + r],
                      fill=GOLD_L)
    # 图标只有深底/金/白数色，量化到 256 色调色板可省约一半体积且观感无损
    return im.quantize(colors=256, method=Image.MEDIANCUT)


def main():
    os.makedirs(OUT, exist_ok=True)
    for s in SIZES:
        img = make(s)
        img.save(os.path.join(OUT, "icon-%d.png" % s), optimize=True)
    # 512 另出一张 maskable：四周补安全边距，供 Android 自适应图标裁切
    m = make(512)
    base = Image.new("RGB", (512, 512), BG)
    base.paste(m.resize((392, 392), Image.LANCZOS), (60, 60))
    base.convert("P", palette=Image.ADAPTIVE, colors=256).save(os.path.join(OUT, "icon-maskable-512.png"), optimize=True)
    # apple-touch-icon 固定 180（iOS 不支持透明，深底已满足）
    make(180).save(os.path.join(OUT, "apple-touch-icon.png"), optimize=True)
    print("icons ->", OUT, "| 生成", len(SIZES) + 2, "个")


if __name__ == "__main__":
    main()
