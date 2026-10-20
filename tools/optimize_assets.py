# -*- coding: utf-8 -*-
"""素材优化：抽取采访实拍照 -> 圆形头像 320 / 正文图 1200 webp；生成 og 封面。"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

# 仓库根由脚本位置推导（硬编码本机绝对路径 → 换机器/CI 必失败，与 verify_site.py 同规则）
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
 # 正文大图 scene-interview-1/2、merch-badge、merch-sketch 已停出（2026-10-20 轮50 · I-6）：
 # 部署面（HTML/JS/manifest/sw）零引用，却占 322KB 体积。判据见 tools/orphan_asset_test.py；
 # 页面将来要放正文大图，恢复这几行并在 culture.js 加消费点，两侧一起改。

liu2 = Image.open(os.path.join(SRC, "18a24570c9bea0bf1a08a89f431d04e5.jpg"))
w, h = liu2.size
crop2 = liu2.crop((int(w*0.38), int(h*0.32), int(w*0.68), int(h*0.80)))
save_webp(circle(crop2, 320), "craft-lei.webp", q=86)  # 占位：同为采访现场

# （徽章/草图正文图停出，见上；原 3.6MB/3.1MB PNG 源仍在 素材/，随时可恢复）

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
