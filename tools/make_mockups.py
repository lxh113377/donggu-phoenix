# -*- coding: utf-8 -*-
"""文创效果图 v2：用真实矢量渲染的图腾位图合成到实物模板。"""
import os, math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
SM = os.path.join(BASE, "merch", "mock")
DEV = os.path.join(BASE, "_dev")
os.makedirs(SM, exist_ok=True)

TOTEM_LINE = os.path.join(DEV, "render-totem-line.png")
TOTEM_COLOR = os.path.join(DEV, "render-totem-color.png")
TOTEM_MONO = os.path.join(DEV, "render-totem-mono.png")

GOLD = (212, 162, 76)
RED = (179, 32, 44)
INK = (11, 9, 8)
PAPER = (246, 241, 231)

def totem(path, size, tint=None, opacity=255):
    """加载图腾位图 -> 去除白底 -> 可选着色 -> 缩放"""
    im = Image.open(path).convert("RGBA")
    # 白底/黑线处理：把接近白与接近黑的像素处理成目标色
    px = im.load()
    w, h = im.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            lum = (r * 299 + g * 587 + b * 114) // 1000
            if lum > 246:
                continue                     # 纯白背景 -> 透明
            if tint:
                # 保留明暗层次，映射到目标色
                k = max(0.0, 1.0 - lum / 255.0)
                op[x, y] = (tint[0], tint[1], tint[2], int(min(255, 90 + 175 * k) * opacity / 255))
            else:
                op[x, y] = (r, g, b, int(a * opacity / 255))
    return out.resize((size, size), Image.LANCZOS)

def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return None

def center(d, text, y, f, fill, W):
    if not f:
        return
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)

# ---------- 1. 徽章（58mm，马口铁包边）----------
def badge():
    S = 1000
    im = Image.new("RGB", (S, S), (236, 228, 214))
    d = ImageDraw.Draw(im)
    for y in range(0, S, 3):
        d.line([(0, y), (S, y)], fill=(231, 222, 208))
    cx = cy = S // 2
    R = 340
    d.ellipse([cx - R - 30, cy - R - 30, cx + R + 30, cy + R + 30], fill=(186, 190, 196))
    d.ellipse([cx - R - 20, cy - R - 20, cx + R + 20, cy + R + 20], fill=(228, 231, 236))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(250, 246, 238))
    # 内环
    d.ellipse([cx - R + 22, cy - R + 22, cx + R - 22, cy + R - 22], outline=(196, 186, 168), width=2)
    t = totem(TOTEM_MONO, int(R * 1.72), tint=(150, 26, 38))
    im.paste(t, (cx - t.width // 2, cy - t.height // 2), t)
    f = font(r"C:\Windows\Fonts\STKAITI.TTF", 54)
    center(d, "东 固 凤 凰", cy + R - 96, f, (150, 26, 38), S)
    im.save(os.path.join(SM, "mock-badge.png"))
    print("badge ok")

# ---------- 2. 纸雕灯（七层镂空）----------
def paper_lamp():
    W, H = 1000, 1200
    base = Image.new("RGB", (W, H), (16, 14, 13))
    glow = Image.new("RGB", (W, H), (16, 14, 13))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle([240, 290, 760, 910], radius=26, fill=(255, 222, 168))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    im = Image.blend(base, glow, 0.70)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([250, 300, 750, 900], radius=12, fill=(253, 238, 208))
    # 远山（两层）
    d.polygon([(258, 890), (400, 720), (560, 890)], fill=(232, 198, 148))
    d.polygon([(430, 890), (600, 690), (742, 890)], fill=(216, 176, 122))
    # 凤凰层
    t = totem(TOTEM_LINE, 400, tint=(146, 92, 30))
    im.paste(t, (300, 330), t)
    # 顶盖与底座
    d.rectangle([250, 288, 750, 300], fill=(150, 112, 66))
    d.rounded_rectangle([250, 900, 750, 920], radius=5, fill=(128, 94, 54))
    im.save(os.path.join(SM, "mock-lamp.png"))
    print("lamp ok")

# ---------- 3. 帆布包 ----------
def tote():
    W, H = 1000, 1100
    im = Image.new("RGB", (W, H), (232, 227, 216))
    d = ImageDraw.Draw(im)
    # 布纹
    for y in range(0, H, 4):
        d.line([(0, y), (W, y)], fill=(228, 223, 212))
    d.arc([280, 110, 720, 340], 195, 345, fill=(206, 199, 184), width=44)
    d.rounded_rectangle([200, 250, 800, 950], radius=14, fill=(243, 238, 228))
    d.rectangle([200, 250, 800, 268], fill=(234, 228, 216))
    t = totem(TOTEM_MONO, 400, tint=(52, 42, 36))
    im.paste(t, (300, 400), t)
    f = font(r"C:\Windows\Fonts\STKAITI.TTF", 50)
    center(d, "凤 鸣 东 固", 800, f, (52, 42, 36), W)
    im.save(os.path.join(SM, "mock-tote.png"))
    print("tote ok")

# ---------- 4. 黄铜书签 ----------
def bookmark():
    W, H = 480, 1040
    im = Image.new("RGB", (W, H), (240, 234, 222))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([118, 50, 362, 990], radius=16, fill=(206, 168, 100))
    d.rounded_rectangle([126, 58, 354, 982], radius=12, outline=(176, 134, 66), width=2)
    for y in range(90, 950, 24):
        d.line([(142, y), (338, y)], fill=(192, 152, 84))
    t = totem(TOTEM_MONO, 200, tint=(62, 40, 24))
    im.paste(t, (140, 240), t)
    # 尾羽镂空孔
    d.ellipse([218, 640, 262, 684], outline=(62, 40, 24), width=3)
    f = font(r"C:\Windows\Fonts\STKAITI.TTF", 34)
    center(d, "畲", 750, f, (62, 40, 24), W)
    im.save(os.path.join(SM, "mock-bookmark.png"))
    print("bookmark ok")

# ---------- 5. 团扇 ----------
def fan():
    W, H = 900, 1100
    im = Image.new("RGB", (W, H), (238, 232, 220))
    d = ImageDraw.Draw(im)
    cx, cy, R = W // 2, 430, 330
    # 扇柄
    d.rounded_rectangle([cx - 12, cy + 300, cx + 12, H - 40], radius=8, fill=(148, 108, 62))
    # 扇面
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(250, 245, 235))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(198, 158, 92), width=6)
    t = totem(TOTEM_LINE, int(R * 1.5), tint=(158, 40, 40))
    im.paste(t, (cx - t.width // 2, cy - t.height // 2), t)
    f = font(r"C:\Windows\Fonts\STKAITI.TTF", 44)
    center(d, "凤 鸣 东 固", cy + R - 96, f, (150, 36, 40), W)
    im.save(os.path.join(SM, "mock-fan.png"))
    print("fan ok")

# ---------- 6. A4 海报 ----------
def poster():
    W, H = 1240, 1754
    im = Image.new("RGB", (W, H), (11, 9, 8))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t2 = y / H
        k = max(0.0, 1 - abs(t2 - 0.28) * 2) ** 2
        d.line([(0, y), (W, y)],
               fill=(max(11, int(11 + 34 * k)), max(9, int(9 + 10 * k)), max(8, int(8 + 16 * k))))
    d.rectangle([46, 46, W - 46, H - 46], outline=(72, 58, 42), width=2)
    t = totem(TOTEM_COLOR, 660)
    # 深底需要提亮：把暗部映射为金色系
    im.paste(t, ((W - t.width) // 2, 210), t)
    f1 = font(r"C:\Windows\Fonts\STKAITI.TTF", 104)
    f2 = font(r"C:\Windows\Fonts\msyh.ttc", 32)
    f3 = font(r"C:\Windows\Fonts\msyh.ttc", 24)
    center(d, "凤 鸣 东 固", 950, f1, (232, 183, 97), W)
    center(d, "扫 描 畲 族 凤 凰 图 腾 · 见 凤 凰 起 舞", 1110, f2, (212, 162, 76), W)
    qr = Image.open(os.path.join(BASE, "qr", "qr-512.png")).convert("RGB").resize((280, 280), Image.NEAREST)
    qx, qy = W // 2 - 140, 1250
    d.rectangle([qx - 14, qy - 14, qx + 294, qy + 294], fill=(246, 241, 231))
    im.paste(qr, (qx, qy))
    d.rectangle([qx - 14, qy - 14, qx + 294, qy + 294], outline=(212, 162, 76), width=2)
    center(d, "扫码 · 打开凤凰展陈", 1600, f3, (150, 132, 112), W)
    center(d, "江西科技学院 · 薪火寰行实践团　|　东固畲族乡 · 东固传统造像", 1690, f3, (128, 112, 96), W)
    im.save(os.path.join(SM, "poster-a4.png"))
    print("poster ok")

badge(); paper_lamp(); tote(); bookmark(); fan(); poster()
print("all done")
