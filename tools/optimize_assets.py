# -*- coding: utf-8 -*-
"""素材优化：抽取采访实拍照 -> 圆形头像 320 / 正文图 1200 webp；生成 og 封面。"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
SRC = os.path.join(BASE, "素材")
OUT = os.path.join(BASE, "site", "assets", "img", "photos")
os.makedirs(OUT, exist_ok=True)

def save_webp(im, name, w=None, q=82):
    if w and im.width > w:
        h = int(im.height * w / im.width)
        im = im.resize((w, h), Image.LANCZOS)
    p = os.path.join(OUT, name)
    im.save(p, "WEBP", quality=q, method=6)
    print(name, os.path.getsize(p), "bytes", im.size)
    return p

def circle(im, size=320):
    im = im.convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s)//2, (im.height - s)//2, (im.width + s)//2, (im.height + s)//2))
    im = im.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size*4, size*4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size*4-1, size*4-1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out

# 刘节明：采访现场正面照 96682e...jpg（2364x1773 已缩略，原 5760x4320）
liu = Image.open(os.path.join(SRC, "96682e925857cd70e7d96aef552c8743.jpg"))
# 裁出中间的刘老师区域（原图中心偏下）
w, h = liu.size
crop = liu.crop((int(w*0.36), int(h*0.30), int(w*0.66), int(h*0.78)))
save_webp(circle(crop, 320), "craft-liu.webp", q=86)
save_webp(crop, "scene-interview-1.webp", 1000)

liu2 = Image.open(os.path.join(SRC, "18a24570c9bea0bf1a08a89f431d04e5.jpg"))
w, h = liu2.size
crop2 = liu2.crop((int(w*0.38), int(h*0.32), int(w*0.68), int(h*0.80)))
save_webp(circle(crop2, 320), "craft-lei.webp", q=86)  # 占位：同为采访现场
save_webp(crop2, "scene-interview-2.webp", 1000)

# 文化用图：凤凰装静态图（用图腾替代） + 徽章实拍
badge = Image.open(os.path.join(SRC, "000557355a872aeedb5660fd8a947421.png")).convert("RGB")
save_webp(badge, "merch-badge.webp", 1200)

sketch = Image.open(os.path.join(SRC, "a29d83e23df67a5f9bb2feac7e785843.png")).convert("RGB")
save_webp(sketch, "merch-sketch.webp", 1200)

# og 封面 1200x630：生成渐变色块 + 图腾叠加
og = Image.new("RGB", (1200, 630), (11, 9, 8))
d = ImageDraw.Draw(og)
for y in range(630):
    t = y / 630
    r = int(11 + 40 * (1 - abs(t - 0.35) * 2) ** 2)
    g = int(9 + 10 * (1 - abs(t - 0.35) * 2) ** 2)
    b = int(8 + 18 * (1 - abs(t - 0.35) * 2) ** 2)
    d.line([(0, y), (1200, y)], fill=(max(r, 11), max(g, 9), max(b, 8)))
ogp = os.path.join(BASE, "site", "assets", "img", "og-cover.jpg")
og.save(ogp, "JPEG", quality=88)
print("og-cover", os.path.getsize(ogp))
