# -*- coding: utf-8 -*-
"""tools/make_merch_renders.py — 文创实物效果图统一渲染（v3）

为什么重做：v2 的 12 件里有 6 件没图（只显示占位图腾），其余 6 张是「平底色 + 一枚图腾」
——读起来像设计稿，不像产品。本轮改成统一的「样品台」渲染：
  纸张/金属/织物质感 + 定向光 + 接触阴影 + 轻微景深，一件一图，12 件全齐。

约束（沿用项目硬线）：
  * 零外部素材：所有质感全部代码生成（噪声纸纹/环向金属/织物经纬），只有图腾线稿来自 _dev 渲染件；
  * 零外链：产出直接进 site/assets/img/merch/；
  * 图腾三版（单色/线描/全彩）严格按工艺分配：蚀刻、丝印用单色，UV/数码印用全彩。

用法：python tools/make_merch_renders.py [只生成某个 id]
"""
import os, math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = os.path.join(BASE, '_dev')
OUT = os.path.join(BASE, 'site', 'assets', 'img', 'merch')
TMP = os.path.join(BASE, '_dev', 'merch-render')
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

rng = np.random.default_rng(20261020)
S = 1200  # 统一画布：站点展示 232~430px，2.8x 余量

# ---------------------------------------------------------------- 基础工具
def totem_ink(name, color, gamma=1.0):
    """从白底线稿反解「着墨覆盖度」并着色。
    注意：三版渲染件的 alpha 通道是全 255（白底不透明），
    直接用 alpha 当蒙版会得到一整块实心方块 —— 必须按亮度反相取覆盖度。"""
    p = os.path.join(DEV, name)
    im = Image.open(p).convert('RGB')
    a = np.asarray(im, dtype=np.float32)
    lum = a[:, :, 0] * .299 + a[:, :, 1] * .587 + a[:, :, 2] * .114
    cover = np.clip((252.0 - lum) / 210.0, 0.0, 1.0) ** gamma
    rgba = np.dstack([np.full_like(cover, color[0]), np.full_like(cover, color[1]),
                      np.full_like(cover, color[2]), cover * 255.0]).astype(np.uint8)
    out = Image.fromarray(rgba, 'RGBA')
    return out.crop(out.split()[-1].getbbox())

def totem_color():
    """全彩版：保留原色，白底转透明（用于 UV/数码印花）。"""
    im = Image.open(os.path.join(DEV, 'render-totem-color.png')).convert('RGB')
    a = np.asarray(im, dtype=np.float32)
    lum = a[:, :, 0] * .299 + a[:, :, 1] * .587 + a[:, :, 2] * .114
    # 白底 → 透明；彩色区域保留
    alpha = np.clip((250.0 - lum) / 90.0, 0.0, 1.0)
    rgba = np.dstack([a, alpha * 255.0]).astype(np.uint8)
    out = Image.fromarray(rgba, 'RGBA')
    return out.crop(out.split()[-1].getbbox())

def noise_field(w, h, scale, seed=0):
    """低频噪声场（用于纸纹/织物起伏）：小图随机 → 双三次放大。"""
    r = np.random.default_rng(seed)
    small = r.normal(0, 1, (max(2, h // scale), max(2, w // scale))).astype(np.float32)
    span = float(small.max() - small.min()) + 1e-6
    img = Image.fromarray(((small - small.min()) / span * 255).astype(np.uint8))
    img = img.resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0

def paper_surface(w, h, base=(240, 234, 222), grain=3.0, fibers=700, seed=1):
    arr = np.tile(np.array(base, np.float32), (h, w, 1))
    arr += rng.normal(0, grain, (h, w, 1)).astype(np.float32)
    for _ in range(fibers):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        L = int(rng.integers(5, 22))
        arr[y:y + 1, x:min(w, x + L)] += rng.uniform(3, 9)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vr = 1.0 - 0.10 * (((xx - w / 2) / (w * .72)) ** 2 + ((yy - h / 2) / (h * .72)) ** 2)
    arr *= np.clip(vr, .72, 1.0)[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def fabric_surface(w, h, base=(236, 231, 219), thread=2, seed=3):
    """平纹棉布：经纬细纹 + 低频起伏 + 边缘压暗。"""
    yy, xx = np.mgrid[0:h, 0:w]
    warp = 0.5 + 0.5 * np.cos(xx * (math.pi / thread))
    weft = 0.5 + 0.5 * np.cos(yy * (math.pi / thread))
    weave = (warp * weft) * 2.0 - 1.0
    low = (noise_field(w, h, 40, seed) - .5) * 2
    arr = np.tile(np.array(base, np.float32), (h, w, 1))
    arr += (weave * 7.0 + low * 9.0)[:, :, None]
    arr += rng.normal(0, 2.2, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def rounded_mask(w, h, r, blur=1.2, inset=0):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([inset, inset, w - 1 - inset, h - 1 - inset], radius=r, fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m

def ellipse_mask(w, h, blur=1.2):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).ellipse([0, 0, w - 1, h - 1], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m

def shadow(w, h, mask, blur=30, dx=0, dy=18, alpha=110, at=(0, 0)):
    """mask 允许是局部尺寸（部件自身），统一按 (at) 贴到画布再模糊偏移。"""
    full = Image.new('L', (w, h), 0)
    full.paste(mask, (int(at[0]), int(at[1])))
    sh = full.filter(ImageFilter.GaussianBlur(blur))
    sh = ImageChops.offset(sh, dx, dy)
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    layer.putalpha(sh.point(lambda v: int(v * alpha / 255)))
    return layer

def as_int_point(p):
    return (int(p[0]), int(p[1]))

def box4(a, b, c, d):
    return [int(a), int(b), int(c), int(d)]

def obj_shadow(alpha, blur=26, dx=0, dy=16, opacity=118):
    """按部件自身 alpha 生成接触阴影。v3 的 bug 就出在拿整块画布椭圆当遮罩。"""
    a = alpha.filter(ImageFilter.GaussianBlur(blur))
    a = ImageChops.offset(a, dx, dy)
    sh = Image.new('RGBA', a.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * opacity / 255)))
    return sh


def compose_on_desk(desk, obj, pos=None, blur=28, dy=20, opacity=118):
    """把部件按自身轮廓投影后合成到台面。"""
    w, h = desk.size
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    layer = Image.alpha_composite(layer, obj_shadow(obj.split()[-1], blur=blur, dy=dy, opacity=opacity))
    if pos is None:
        pos = ((w - obj.width) // 2, (h - obj.height) // 2)
    layer.alpha_composite(obj, pos)
    return Image.alpha_composite(desk.convert('RGBA'), layer)


def directional_light(w, h, cx=0.34, cy=0.26, strength=0.22, spread=1.25):
    """左上 45° 主光：径向亮部叠加（明暗靠乘法+叠加，物体才有体积）。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w - cx) * spread) ** 2 + ((yy / h - cy) * spread) ** 2)
    k = np.clip(1.0 - d / 0.95, 0, 1) ** 2
    return Image.fromarray((np.clip(k, 0, 1) * 255 * strength).astype(np.uint8))

def add_light(im, w, h, **kw):
    """主光只提亮不改色：用 screen 叠加，避免 composite 把整张压灰（首版实测）。"""
    light = directional_light(w, h, **kw)
    warm = Image.new('RGB', (w, h), (255, 244, 220))
    lit = ImageChops.screen(im.convert('RGB'), Image.merge('RGB', (light, light, light)))
    return Image.blend(im.convert('RGB'), lit, 0.85)

def vignette(im, k=0.16):
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * .62)) ** 2 + ((yy - h / 2) / (h * .62)) ** 2)
    v = np.clip(1.0 - k * np.clip(d - .55, 0, 2) ** 1.6, 0, 1)
    arr = np.asarray(im.convert('RGB'), np.float32) * v[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def font(size, kai=True):
    names = [r'C:\Windows\Fonts\STKAITI.TTF', r'C:\Windows\Fonts\simkai.ttf'] if kai else [r'C:\Windows\Fonts\msyh.ttc']
    for n in names:
        if os.path.exists(n):
            try:
                return ImageFont.truetype(n, size)
            except Exception:
                pass
    return None

def text_center(d, s, y, f, fill, W, spacing=0):
    if not f:
        return
    t = ' '.join(s) if spacing else s
    tw = d.textlength(t, font=f)
    d.text(((W - tw) / 2, y), t, font=f, fill=fill)

def contact_desk(w=S, h=S):
    """样品台：中性暖灰纸面 + 台面暗角。所有单件都放在同一张台上，整套才有统一感。"""
    base = paper_surface(w, h, (236, 229, 216), 2.6, 520, seed=11)
    base = vignette(base, 0.07)
    return base.convert('RGBA')

def finish(im, name, light=True):
    w, h = im.size
    out = im.convert('RGB')
    if light:
        out = add_light(out, w, h)
    out = vignette(out, 0.045)
    p = os.path.join(OUT, name)
    out.save(p, 'WEBP', quality=88, method=6)
    print('%-26s %s %d KB' % (name, out.size, os.path.getsize(p) // 1024))
    return p

def stamp_ink(canvas, ink, box_w, cx, cy, opacity=1.0):
    """把墨稿按目标宽度缩放并贴到中心 (cx, cy)。"""
    ratio = box_w / ink.width
    im = ink.resize((int(ink.width * ratio), int(ink.height * ratio)), Image.LANCZOS)
    if opacity < 1.0:
        a = im.split()[-1].point(lambda v: int(v * opacity))
        im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
    return im


# ---------------------------------------------------------------- v4 辅助层
# v4 的函数体用了简短名（paper/fabric/ink/fbm/rmask/emask/font/text_center/desk_bg/save），
# 而文件上半部分保留的是 v3 的长名实现 —— 这里做一层薄别名，避免重复实现两套质感代码。
def fbm(w, h, scale, seed=0):
    return noise_field(w, h, scale, seed)

def paper(w, h, base=(242, 236, 224), grain=2.4, fibers=500, seed=1):
    return paper_surface(w, h, base, grain, fibers, seed)

def fabric(w, h, base=(238, 233, 222), period=2, relief=6.0, seed=3):
    return fabric_surface(w, h, base, period, seed)

def rmask(w, h, r, blur=1.0):
    return rounded_mask(w, h, int(r), blur)

def emask(w, h, blur=1.0):
    return ellipse_mask(w, h, blur)

def ink(name, color, gamma=1.0):
    return totem_ink(name, color, gamma)

def full_color_totem():
    return totem_color()

def font(size, kai=True):
    names = ([r'C:\Windows\Fonts\STKAITI.TTF', r'C:\Windows\Fonts\simkai.ttf'] if kai
             else [r'C:\Windows\Fonts\msyh.ttc'])
    for n in names:
        if os.path.exists(n):
            try:
                return ImageFont.truetype(n, int(size))
            except Exception:
                pass
    return None

def text_center(d, text, cy, f, fill, box_w):
    """在宽度 box_w 内水平居中（box_w 可取大于画布的值做视觉微调）。"""
    if not f:
        return
    t = ' '.join(list(text))
    tw = d.textlength(t, font=f)
    d.text(((box_w - tw) / 2, cy), t, font=f, fill=fill)

TRANSPARENT_OUT = True   # 产品图输出透明底；纸台只在渲染期用于定位与阴影落点


def desk_bg(w=None, h=None):
    """样品台：统一暖纸底 + 轻暗角（预览口径）。
    产品图输出走透明底 —— 图放进深色卡片时，自带台面色会变成一块浅方块（目检抓到过）。"""
    w = S if w is None else w
    h = S if h is None else h
    if TRANSPARENT_OUT:
        return Image.new('RGBA', (w, h), (0, 0, 0, 0))
    base = paper(w, h, (238, 231, 218), 2.0, 380, seed=11)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * .70)) ** 2 + ((yy - h / 2) / (h * .70)) ** 2)
    v = np.clip(1.0 - .13 * np.clip(d - .55, 0, 2) ** 1.5, 0, 1)
    arr = np.asarray(base, np.float32) * v[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')


def apply_light(im, strength=.28):
    """左上主光：只提亮不改色（v3 用 composite 把整张压灰过）。"""
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w - .34) * 1.15) ** 2 + ((yy / h - .26) * 1.15) ** 2)
    k = np.clip(1 - d, 0, 1) ** 2.0
    mask = Image.fromarray((k * 255 * strength).astype(np.uint8))
    warm = Image.new('RGB', (w, h), (255, 246, 228))
    return Image.composite(Image.blend(im.convert('RGB'), warm, .45), im.convert('RGB'), mask)

def compose_on_desk(desk, obj, pos=None, blur=28, dy=20, opacity=118, scale=1.0):
    """部件按自身轮廓投影后合成到台面。

    v3 的两个坑都在这里：
      ① 阴影模糊若在「部件尺寸」画布内做，四周没有留白 ⇒ 模糊被裁成方块硬边，
         图上会看到物体外圈一个方形 halo（首轮目检直接抓到）；
      ② 阴影图与桌面画布尺寸不等时不能直接 alpha_composite（会抛 images do not match）。
    现在先给部件加 pad 再模糊，最后按 pad 反推坐标贴回桌面。"""
    w, h = desk.size
    if scale != 1.0:
        obj = obj.resize((max(1, int(obj.width * scale)), max(1, int(obj.height * scale))), Image.LANCZOS)
    pad = max(12, int(blur * 2.2))
    canvas = Image.new('RGBA', (obj.width + 2 * pad, obj.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(obj, (pad, pad))
    a = canvas.split()[-1].filter(ImageFilter.GaussianBlur(blur))
    a = ImageChops.offset(a, 0, int(dy))
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * opacity / 255)))
    if pos is None:
        pos = ((w - obj.width) // 2, (h - obj.height) // 2)
    pos = (int(pos[0]), int(pos[1]))
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    layer.alpha_composite(sh, (pos[0] - pad, pos[1] - pad))
    layer.alpha_composite(obj, pos)
    return Image.alpha_composite(desk.convert('RGBA'), layer)

def save(im, name, light=0, keep_bg=False):
    """输出产品图。

    只保留「物体 + 它自己的阴影」，台面透明 —— 这样同一张图放进深色卡片、
    放进浅色文章、印在物料上都成立。早前试过从纸台反推 alpha：纸纹噪声会让整张
    变半透明，体积从 167KB 爆到 3MB 且边缘发雾，已弃用。

    keep_bg=True 用于纸雕灯与手机壁纸：它们本身就是发光体/深色屏幕，透明会丢效果。
    """
    out = im.convert('RGBA')
    if keep_bg:
        r, g, b = out.split()[:3]
        out = Image.merge('RGBA', (r, g, b, Image.new('L', out.size, 255)))
    if light:
        out = apply_light(out, light)
    bbox = out.split()[-1].point(lambda v: 255 if v > 6 else 0).getbbox()
    if bbox:
        pad = 20
        out = out.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                        min(out.width, bbox[2] + pad), min(out.height, bbox[3] + pad)))
    scale = 860.0 / max(out.size)
    out = out.resize((max(1, int(out.width * scale)), max(1, int(out.height * scale))), Image.LANCZOS)
    q = os.path.join(OUT, name)
    out.save(q, 'WEBP', quality=88, method=6)
    print('%-24s %s %3d KB' % (name, out.size, os.path.getsize(q) // 1024))



def r_badge():
    R = int(S * .30)
    D = 2 * R + 6
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    c = D / 2
    rr = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    ang = np.arctan2(yy - c, xx - c)
    shade = .60 + .40 * np.cos(ang + math.radians(44))
    band = (rr <= R) & (rr >= R - D * .028)
    ring = np.zeros((D, D, 4), np.uint8)
    metal = np.array([210, 214, 220], np.float32)
    ring[band, :3] = np.clip(metal[None, None, :] * shade[:, :, None], 0, 255)[band].astype(np.uint8)
    ring[band, 3] = 255
    im = Image.alpha_composite(im, Image.fromarray(ring, 'RGBA').filter(ImageFilter.GaussianBlur(.6)))
    face = paper(D, D, (250, 246, 238), 1.8, 240, seed=5).convert('RGBA')
    fm = Image.new('L', (D, D), 0)
    ImageDraw.Draw(fm).ellipse([c - R + D * .026, c - R + D * .026, c + R - D * .026, c + R - D * .026], fill=255)
    im.paste(face, (0, 0), fm.filter(ImageFilter.GaussianBlur(.7)))
    d = ImageDraw.Draw(im)
    r2 = R - D * .046
    d.ellipse([c - r2, c - r2, c + r2, c + r2], outline=(202, 192, 174), width=2)
    t = ink('render-totem-mono.png', (150, 27, 39))
    tw = int(R * 1.48)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, (int(c - tw / 2), int(c - tw / 2)))
    hl = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([c - R * .92, c - R * .99, c + R * .92, c + R * .30], fill=(255, 255, 255, 50))
    hm = Image.new('L', (D, D), 0)
    ImageDraw.Draw(hm).ellipse([c - R, c - R, c + R, c + R], fill=255)
    im = Image.alpha_composite(im, Image.composite(hl.filter(ImageFilter.GaussianBlur(28)),
                                                   Image.new('RGBA', (D, D), (0, 0, 0, 0)), hm))
    save(compose_on_desk(desk_bg(), im, blur=30, dy=20, opacity=125), 'r-badge.webp')

# ---------------------------------------------------------------- 02 笔筒
def r_pen():
    W, H = int(S * .34), int(S * .40)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    body = rmask(W, H, int(W * .035), 1.0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    grain = np.sin(xx * .16 + fbm(W, H, 26, 21) * 4.6) * .5 + .5
    arr = np.tile(np.array([201, 162, 112], np.float32), (H, W, 1))
    arr += ((grain - .5) * 20 + (fbm(W, H, 30, 22) - .5) * 22)[:, :, None]
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'), (0, 0), body)
    # 柱面明暗
    u = (xx / max(1, W - 1))
    dark = np.clip((0.5 - np.cos((u - .30) * math.pi * 1.35) * .5) ** 1.3, 0, 1) * 120
    sh = np.zeros((H, W, 4), np.uint8)
    sh[:, :, 3] = dark.astype(np.uint8)
    im = Image.alpha_composite(im, Image.composite(Image.fromarray(sh, 'RGBA'),
                                                   Image.new('RGBA', (W, H), (0, 0, 0, 0)), body))
    d = ImageDraw.Draw(im)
    ew, eh = W * .045, H * .048
    d.ellipse([ew, -eh * .55, W - ew, eh * 1.0], fill=(214, 178, 128), outline=(176, 138, 92), width=2)
    d.ellipse([ew + W * .035, -eh * .10, W - ew - W * .035, eh * .82], fill=(88, 62, 38))
    t = ink('render-totem-mono.png', (94, 64, 36), gamma=.82)
    tw = int(W * .58)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, ((W - tw) // 2, int(H * .28)))
    save(compose_on_desk(desk_bg(), im, blur=26, dy=18, opacity=120), 'r-pen.webp')

# ---------------------------------------------------------------- 03 笔记本
def r_note():
    W, H = int(S * .38), int(S * .50)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    body = rmask(W, H, int(W * .014), 1.0)
    cloth = fabric(W, H, (58, 49, 44), 2, 4.0, seed=31).convert('RGBA')
    im.paste(cloth, (0, 0), body)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([-4, 5, W + 1, H - 5], radius=int(W * .014), outline=(230, 224, 212), width=4)
    sx = int(W * .085)
    d.line([(sx, 6), (sx, H - 6)], fill=(26, 21, 19), width=4)
    d.line([(sx + 5, 6), (sx + 5, H - 6)], fill=(88, 76, 68), width=1)
    t = ink('render-totem-line.png', (216, 174, 104), gamma=.92)
    tw = int(W * .40)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, (int(W * .56 - tw / 2), int(H * .24)))
    f = font(int(H * .040))
    if f:
        text_center(d, '凤鸣东固', int(H * .60), f, (212, 170, 100), int(W * 1.14))
    d.polygon([(int(W * .80), H - 5), (int(W * .86), H - 5), (int(W * .855), int(H * 1.05)),
               (int(W * .83), int(H * 1.03))], fill=(152, 36, 46))
    save(compose_on_desk(desk_bg(), im, blur=28, dy=20, opacity=120), 'r-note.webp')

# ---------------------------------------------------------------- 04 纸雕灯
def r_lamp():
    W, H = int(S * .36), int(S * .46)
    face = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(face)
    d.rectangle([0, 0, W, H], fill=(254, 242, 216))
    d.polygon([(0, H * .80), (W * .26, H * .56), (W * .52, H * .80)], fill=(244, 218, 174))
    d.polygon([(W * .20, H * .84), (W * .58, H * .48), (W * .96, H * .84)], fill=(230, 194, 140))
    d.polygon([(0, H * .95), (W * .42, H * .76), (W, H * .97)], fill=(212, 170, 114))
    d.ellipse([W * .16, H * .10, W * .84, H * .70], outline=(226, 196, 150), width=2)
    t = ink('render-totem-line.png', (132, 80, 26), gamma=.80)
    tw = int(W * .54)
    t = t.resize((tw, tw), Image.LANCZOS)
    face.alpha_composite(t, (int(W / 2 - tw / 2), int(H * .15)))
    face.putalpha(rmask(W, H, int(W * .018), 1.0))
    glow = Image.new('RGB', (S, S), (9, 8, 7))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle([(S - W) // 2, (S - H) // 2, (S + W) // 2, (S + H) // 2],
                         radius=int(W * .02), fill=(255, 214, 152))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    # 透明底：黑底 alpha=0，只留下暖光晕与灯体
    dark = Image.new('RGBA', (S, S), (10, 9, 8, 0))
    glow_a = glow.convert('RGBA')
    ga = glow_a.split()[-1].point(lambda v: v)
    gm = Image.new('L', (S, S), 0)
    gd2 = ImageDraw.Draw(gm)
    gd2.rounded_rectangle([(S - W) // 2 - 40, (S - H) // 2 - 40, (S + W) // 2 + 40, (S + H) // 2 + 40],
                          radius=90, fill=255)
    gm = gm.filter(ImageFilter.GaussianBlur(70))
    stage = Image.new('RGBA', (S, S), (10, 9, 8, 0))
    stage.paste(glow_a, (0, 0), gm)
    top = Image.new('RGBA', (W + 6, max(6, int(H * .026))), (146, 106, 62, 255))
    bot = Image.new('RGBA', (W + 6, max(5, int(H * .022))), (118, 84, 50, 255))
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    x0, y0 = (S - W) // 2, (S - H) // 2
    layer.alpha_composite(face, (x0, y0))
    layer.alpha_composite(top, (x0 - 3, y0 - top.height + 1))
    layer.alpha_composite(bot, (x0 - 3, y0 + H - 1))
    save(Image.alpha_composite(stage, layer), 'r-lamp.webp', light=0, keep_bg=False)

# ---------------------------------------------------------------- 05 团扇
def r_fan():
    W, H = int(S * .52), int(S * .64)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    R = int(W * .45)
    cx, cy = W // 2, int(H * .38)
    d = ImageDraw.Draw(im)
    hw = max(6, int(W * .026))
    d.rounded_rectangle([cx - hw // 2, cy, cx + hw // 2, H - 6], radius=hw // 2, fill=(152, 112, 66))
    d.rounded_rectangle([cx - hw // 2 + 3, cy, cx - hw // 2 + 6, H - 18], radius=2, fill=(180, 140, 92))
    silk = paper(2 * R, 2 * R, (251, 246, 236), 1.4, 140, seed=8).convert('RGBA')
    im.paste(silk, (cx - R, cy - R), emask(2 * R, 2 * R, 1.0))
    d = ImageDraw.Draw(im)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(200, 160, 94), width=4)
    d.ellipse([cx - R + 9, cy - R + 9, cx + R - 9, cy + R - 9], outline=(226, 194, 142), width=1)
    t = ink('render-totem-line.png', (158, 46, 44), gamma=.92)
    tw = int(R * 1.16)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, (cx - tw // 2, int(cy - R * .54)))
    f = font(int(R * .145))
    if f:
        text_center(d, '凤鸣东固', int(cy + R * .44), f, (152, 42, 42), W)
    hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([cx - R * .82, cy - R * .92, cx + R * .16, cy - R * .06], fill=(255, 255, 255, 34))
    hm = Image.new('L', (W, H), 0)
    ImageDraw.Draw(hm).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im = Image.alpha_composite(im, Image.composite(hl.filter(ImageFilter.GaussianBlur(30)),
                                                   Image.new('RGBA', (W, H), (0, 0, 0, 0)), hm))
    save(compose_on_desk(desk_bg(), im, blur=28, dy=22, opacity=118), 'r-fan.webp')

# ---------------------------------------------------------------- 06 冰箱贴（三枚一组）
def r_magnet():
    TW, TH = int(S * .26), int(S * .20)
    tiles = [(S * .50, S * .335, (150, 27, 39), '大凤凰装'),
             (S * .285, S * .605, (44, 78, 116), '小凤凰装'),
             (S * .715, S * .605, (128, 88, 40), '老凤凰装')]
    desk = desk_bg()
    for cx, cy, tint_rgb, label in tiles:
        im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, TW - 1, TH - 1], radius=int(TH * .15), fill=(250, 246, 236))
        t = ink('render-totem-mono.png', tint_rgb)
        tw = int(TH * .74)
        t = t.resize((tw, tw), Image.LANCZOS)
        im.alpha_composite(t, ((TW - tw) // 2, int(TH * .12)))
        f = font(int(TH * .105))
        if f:
            text_center(d, label, int(TH * .74), f, tint_rgb, TW)
        d.rounded_rectangle([0, 0, TW - 1, TH - 1], radius=int(TH * .15), outline=(214, 207, 194), width=2)
        hl = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
        ImageDraw.Draw(hl).rounded_rectangle([5, 4, int(TW * .40), int(TH * .40)], radius=int(TH * .10),
                                             fill=(255, 255, 255, 46))
        im = Image.alpha_composite(im, Image.composite(hl.filter(ImageFilter.GaussianBlur(6)),
                                                       Image.new('RGBA', (TW, TH), (0, 0, 0, 0)),
                                                       rmask(TW, TH, int(TH * .15), 1.0)))
        # 阴影带 pad：不加 pad 模糊会被裁成方块硬边（首轮目检就是这个）
        pad = 26
        big = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        big.alpha_composite(im, (pad, pad))
        a = big.split()[-1].filter(ImageFilter.GaussianBlur(14))
        a = ImageChops.offset(a, 0, 9)
        sh = Image.new('RGBA', big.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 112 / 255)))
        px, py = int(cx - TW / 2), int(cy - TH / 2)
        desk.alpha_composite(sh, (px - pad, py - pad))
        desk.alpha_composite(im, (px, py))
    save(desk, 'r-magnet.webp')

# ---------------------------------------------------------------- 07 黄铜书签
def r_bookmark():
    W, H = int(S * .185), int(S * .62)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    body = rmask(W, H, int(W * .085), 1.0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    arr = np.tile(np.array([208, 170, 102], np.float32), (H, W, 1))
    arr += (fbm(W, H, 2, 44)[:, :, None] - .5) * 16
    arr *= np.clip(1.06 - .30 * (xx / max(1, W - 1)), .55, 1.14)[:, :, None]
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'), (0, 0), body)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([5, 5, W - 6, H - 6], radius=int(W * .07), outline=(150, 112, 58), width=2)
    t = ink('render-totem-mono.png', (58, 38, 22), gamma=.78)
    tw = int(W * .72)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, ((W - tw) // 2, int(H * .12)))
    d.ellipse([W * .36, H * .42, W * .64, H * .452], outline=(64, 44, 26), width=3)
    f = font(int(W * .38))
    if f:
        text_center(d, '畲', int(H * .55), f, (64, 44, 26), W)
    d.line([(W * .26, H * .72), (W * .74, H * .72)], fill=(148, 110, 56), width=2)
    save(compose_on_desk(desk_bg(), im, blur=24, dy=20, opacity=120), 'r-bookmark.webp')

# ---------------------------------------------------------------- 08 AR 明信片
def r_postcard():
    W, H = int(S * .56), int(S * .38)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    arr = np.tile(np.array([12, 10, 9], np.float32), (H, W, 1))
    arr += np.array([44, 15, 25], np.float32) * np.clip(1 - np.abs(yy - .32) * 2.2, 0, 1)
    arr += (fbm(W, H, 80, 91)[:, :, None] - .5) * 8
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'), (0, 0),
             rmask(W, H, int(W * .012), 1.0))
    d = ImageDraw.Draw(im)
    d.rectangle([16, 16, W - 17, H - 17], outline=(104, 82, 56), width=2)
    t = full_color_totem()
    tw = int(W * .30)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, (int(W * .08), int(H * .20)))
    f1 = font(int(H * .115))
    f2 = font(int(H * .038), kai=False)
    if f1:
        text_center(d, '凤鸣东固', int(H * .26), f1, (232, 183, 97), W)
    if f2:
        text_center(d, '扫码 · 见凤凰起舞', int(H * .55), f2, (196, 168, 128), W)
    back = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(back).rounded_rectangle([0, 0, W - 1, H - 1], radius=int(W * .012), fill=(232, 226, 214))
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    x0, y0 = (S - W) // 2, (S - H) // 2
    layer.alpha_composite(obj_shadow(im.split()[-1], blur=26, dy=18, opacity=115), (x0, y0))
    layer.alpha_composite(back, (x0 + 9, y0 + 11))
    layer.alpha_composite(im, (x0, y0))
    save(Image.alpha_composite(desk_bg(), layer), 'r-postcard.webp')

# ---------------------------------------------------------------- 09 帆布袋
def r_tote():
    W, H = int(S * .40), int(S * .44)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    body = rmask(W, H, int(W * .018), 1.4)
    cloth = fabric(W, H, (241, 236, 226), 2, 4.6, seed=51).convert('RGBA')
    im.paste(cloth, (0, 0), body)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fold = np.sin(xx * .014 + fbm(W, H, 26, 61) * 4.4) * .6 + np.cos(yy * .018) * .4
    arr = np.asarray(cloth.convert('RGB'), np.float32) + (fold * 12)[:, :, None]
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'), (0, 0), body)
    d = ImageDraw.Draw(im)
    d.line([(3, int(H * .05)), (W - 3, int(H * .05))], fill=(226, 220, 207), width=2)
    t = ink('render-totem-mono.png', (52, 43, 36), gamma=.84)
    tw = int(W * .38)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, ((W - tw) // 2, int(H * .18)))
    f = font(int(H * .046))
    if f:
        text_center(d, '凤鸣东固', int(H * .64), f, (52, 43, 36), W)
    hw = max(4, int(W * .032))
    for off in (-.16, +.16):
        hx = int(W * (.5 + off))
        d.rounded_rectangle([hx - hw // 2, -int(H * .26), hx + hw // 2, int(H * .09)], radius=hw // 2,
                            fill=(234, 228, 216))
        d.line([(hx - hw // 2 + 2, -int(H * .24)), (hx - hw // 2 + 2, int(H * .07))], fill=(246, 241, 231), width=2)
    d.arc([int(W * .21), -int(H * .36), int(W * .79), int(H * .10)], 186, 354, fill=(230, 224, 211), width=hw)
    im.putalpha(Image.new('L', im.size, 0))
    alpha = Image.new('L', im.size, 0)
    ImageDraw.Draw(alpha).rounded_rectangle([0, -int(H * .30), W - 1, H - 1], radius=int(W * .018), fill=255)
    im = Image.merge('RGBA', im.split()[:3] + (alpha,))
    save(compose_on_desk(desk_bg(), im, blur=30, dy=24, opacity=118), 'r-tote.webp')

# ---------------------------------------------------------------- 10 丝巾
def r_scarf():
    W = H = int(S * .54)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wave = np.sin((xx * .011 + yy * .008) + fbm(W, H, 28, 71) * 3.2) * .5 + .5
    arr = np.tile(np.array([182, 34, 46], np.float32), (H, W, 1))
    arr *= (.80 + .32 * wave)[:, :, None]
    arr += (fbm(W, H, 56, 72)[:, :, None] - .5) * 12
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'), (0, 0),
             rmask(W, H, 4, 1.2))
    d = ImageDraw.Draw(im)
    for inset, col, wd in ((18, (212, 162, 76), 3), (44, (234, 198, 136), 1)):
        d.rectangle([inset, inset, W - inset, H - inset], outline=col, width=wd)
    t = full_color_totem()
    tw = int(W * .46)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, ((W - tw) // 2, int(H * .20)))
    f = font(int(H * .044))
    if f:
        text_center(d, '凤鸣东固', int(H * .79), f, (248, 226, 190), W)
    hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).polygon([(0, H * .12), (W, H * .02), (W, H * .20), (0, H * .30)], fill=(255, 255, 255, 28))
    im = Image.alpha_composite(im, Image.composite(hl.filter(ImageFilter.GaussianBlur(24)),
                                                   Image.new('RGBA', (W, H), (0, 0, 0, 0)), rmask(W, H, 4, 1.0)))
    save(compose_on_desk(desk_bg(), im, blur=34, dy=26, opacity=112), 'r-scarf.webp')

# ---------------------------------------------------------------- 11 礼盒
def r_box():
    W, H = int(S * .46), int(S * .30)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    body = rmask(W, H, int(W * .014), 1.0)
    hard = paper(W, H, (38, 32, 30), 1.6, 200, seed=13).convert('RGBA')
    im.paste(hard, (0, 0), body)
    d = ImageDraw.Draw(im)
    d.line([(0, int(H * .30)), (W, int(H * .30))], fill=(76, 64, 58), width=3)
    d.line([(0, int(H * .30) + 3), (W, int(H * .30) + 3)], fill=(22, 18, 16), width=2)
    t = ink('render-totem-line.png', (210, 168, 96), gamma=.94)
    tw = int(H * .36)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, (int(W * .5 - tw / 2), int(H * .40)))
    f = font(int(H * .10))
    if f:
        text_center(d, '东固文创', int(H * .78), f, (208, 166, 94), W)
    d.ellipse([W * .47, int(H * .33), W * .53, int(H * .375)], fill=(214, 180, 118))
    d.ellipse([W * .487, int(H * .34), W * .513, int(H * .366)], fill=(168, 136, 82))
    save(compose_on_desk(desk_bg(), im, blur=30, dy=24, opacity=125), 'r-box.webp')

# ---------------------------------------------------------------- 12 数字壁纸
def r_wallpaper():
    W, H = int(S * .26), int(S * .54)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=int(W * .13), fill=(38, 36, 35))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt(((xx - W / 2) / (W * .62)) ** 2 + ((yy - H * .40) / (H * .44)) ** 2)
    glow = np.clip(1 - dist, 0, 1) ** 1.7
    arr = np.tile(np.array([12, 10, 9], np.float32), (H, W, 1))
    arr += np.array([198, 60, 44], np.float32) * glow[:, :, None] * .88
    arr += (fbm(W, H, 50, 81)[:, :, None] - .5) * 9
    scr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')
    inset = int(W * .038)
    iw, ih = W - 2 * inset, H - 2 * inset
    scr = scr.resize((iw, ih), Image.LANCZOS)
    im.paste(scr, (inset, inset), rmask(iw, ih, int(W * .11), 1.0))
    t = full_color_totem()
    tw = int(W * .50)
    t = t.resize((tw, tw), Image.LANCZOS)
    im.alpha_composite(t, ((W - tw) // 2, int(H * .25)))
    f1 = font(int(W * .105))
    f2 = font(int(W * .030), kai=False)
    if f1:
        text_center(d, '凤鸣东固', int(H * .56), f1, (240, 208, 152), W)
    if f2:
        text_center(d, 'SHE PHOENIX · WALLPAPER', int(H * .635), f2, (198, 156, 104), W)
    d.rounded_rectangle([W * .32, inset + 8, W * .68, inset + 20], radius=6, fill=(24, 22, 21))
    d.rounded_rectangle([W * .30, H - inset - 16, W * .70, H - inset - 10], radius=3, fill=(216, 208, 196))
    hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).polygon([(inset, H * .12), (W - inset, H * .03), (W - inset, H * .17), (inset, H * .30)],
                               fill=(255, 255, 255, 22))
    im = Image.alpha_composite(im, Image.composite(hl.filter(ImageFilter.GaussianBlur(16)),
                                                   Image.new('RGBA', (W, H), (0, 0, 0, 0)),
                                                   rmask(W, H, int(W * .13), 1.0)))
    stage = Image.new('RGBA', (S, S), (12, 11, 10, 0))
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    px, py = (S - W) // 2, (S - H) // 2
    layer.alpha_composite(obj_shadow(im.split()[-1], blur=38, dy=20, opacity=160), (px, py))
    layer.alpha_composite(im, (px, py))
    save(Image.alpha_composite(stage, layer), 'r-wallpaper.webp', light=0, keep_bg=True)


JOBS = {
    'badge': r_badge, 'pen': r_pen, 'note': r_note, 'lamp': r_lamp, 'fan': r_fan,
    'magnet': r_magnet, 'bookmark': r_bookmark, 'postcard': r_postcard,
    'tote': r_tote, 'scarf': r_scarf, 'box': r_box, 'wallpaper': r_wallpaper,
}

def main():
    only = sys.argv[1:] or list(JOBS)
    for k in only:
        if k not in JOBS:
            print('unknown id', k); continue
        try:
            JOBS[k]()
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAILED', k, e)
    return 0

if __name__ == '__main__':
    sys.exit(main())
