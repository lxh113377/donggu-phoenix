# -*- coding: utf-8 -*-
"""畲族凤凰图腾 v6 —— 翼骨扇形 + 团花构图（原创矢量，右半定义镜像）。
羽片原语用局部旋转坐标，两侧控制点对称 => 零自交。
"""
import math, os, re

W = 1000.0

def f(v): return f"{v:.2f}"

def rot(x, y, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c

def feather(bx, by, ang, L, w, bias=0.42, tipw=1.0):
    cp1 = (L * 0.09, w * 0.50); cp2 = (L * bias, w * 0.98); cp3 = (L * 0.86, w * 0.40)
    cp4 = (L * 0.86, -w * 0.40); cp5 = (L * bias, -w * 0.98); cp6 = (L * 0.09, -w * 0.50)
    def T(p):
        x, y = rot(p[0], p[1], ang); return f"{f(bx+x)} {f(by+y)}"
    return (f"M {f(bx)} {f(by)} C {T(cp1)} {T(cp2)} {T(cp3)} L {T((L, tipw))} "
            f"L {T((L, -tipw))} C {T(cp4)} {T(cp5)} {T(cp6)} Z")

def mirror(d):
    toks = re.findall(r'[MLCQZ]|-?\d+\.?\d*', d)
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t in ('M', 'L', 'C', 'Q'):
            out.append(t); i += 1
        elif t == 'Z':
            out.append('Z'); i += 1
        else:
            out.append(f"{f(W-float(toks[i]))} {f(float(toks[i+1]))}"); i += 2
    return " ".join(out)

def both(d): return [d, mirror(d)]

def build(mode="line"):
    L = []; add = L.append
    lm = (mode == "line")
    pm = (mode == "particle")
    st = "#D4A24C" if lm else "#2B0B0D"
    sw = "2.4" if lm else "1.7"
    if pm:
        st = "#FFFFFF"; sw = "0"

    add('<?xml version="1.0" encoding="UTF-8"?>')
    add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000" '
        'role="img" aria-label="畲族凤凰图腾">')
    add('<title>畲 · 凤鸣东固 — 畲族凤凰图腾</title>')
    add('<desc>原创矢量团花图腾：凤凰展翅于圆光中，外环为畲族织带纹与银饰点。</desc>')
    add('<defs>'
        '<linearGradient id="gW" x1=".05" y1="1" x2=".95" y2="0">'
        '<stop offset="0" stop-color="#7A1420"/><stop offset=".36" stop-color="#B3202C"/>'
        '<stop offset=".72" stop-color="#D94F2B"/><stop offset="1" stop-color="#E8B761"/></linearGradient>'
        '<linearGradient id="gW2" x1=".05" y1="1" x2=".95" y2="0">'
        '<stop offset="0" stop-color="#4C0B13"/><stop offset="1" stop-color="#A81C29"/></linearGradient>'
        '<linearGradient id="gT" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#E8B761"/><stop offset=".34" stop-color="#D94F2B"/>'
        '<stop offset="1" stop-color="#1E3A5F"/></linearGradient>'
        '<radialGradient id="gB" cx=".5" cy=".26" r=".9">'
        '<stop offset="0" stop-color="#E8735A"/><stop offset=".55" stop-color="#C22B33"/>'
        '<stop offset="1" stop-color="#8C1521"/></radialGradient>'
        '</defs>')

    def path(d, fill="#FFFFFF" if pm else "none", extra=""):
        if pm:
            add(f'<path d="{d}" fill="{fill if fill != "none" else "#FFFFFF"}" stroke="none"/>')
            return
        if lm:
            add(f'<path d="{d}" fill="none" stroke="{st}" stroke-width="{sw}" '
                f'stroke-linejoin="round" stroke-linecap="round" {extra}/>')
        else:
            add(f'<path d="{d}" fill="{fill}" stroke="{st}" stroke-width="{sw}" '
                f'stroke-linejoin="round" stroke-linecap="round" {extra}/>')

    # ---------- 外环 ----------
    if not pm:
      add('<g id="ring">')
    add(f'<circle cx="500" cy="500" r="478" fill="none" stroke="{st}" stroke-width="{3.2 if lm else 4}"/>')
    add(f'<circle cx="500" cy="500" r="452" fill="none" stroke="{st}" stroke-width="1.1" opacity=".5"/>')
    n = 72
    for k in range(n):
        a = 2*math.pi*k/n; a2 = 2*math.pi*(k+.5)/n
        x1, y1 = 500+452*math.cos(a), 500+452*math.sin(a)
        xm, ym = 500+438*math.cos(a2), 500+438*math.sin(a2)
        x3, y3 = 500+452*math.cos(a+2*math.pi/n), 500+452*math.sin(a+2*math.pi/n)
        add(f'<path d="M {f(x1)} {f(y1)} L {f(xm)} {f(ym)} L {f(x3)} {f(y3)}" fill="none" '
            f'stroke="{st}" stroke-width="1.4" opacity=".85"/>')
    for k in range(16):
        a = 2*math.pi*k/16 - math.pi/2
        r = 6.2 if k % 4 == 0 else 4.2
        add(f'<circle cx="{f(500+464*math.cos(a))}" cy="{f(500+464*math.sin(a))}" r="{r}" fill="{st}" opacity=".9"/>')
    add('</g>')

    # ---------- 尾羽（垂落扇形，画在最底） ----------
    add('<g id="tail">')
    TAIL_BASE = (500.0, 598.0)
    for ang, ln, hw in [(-40, 224, 17), (-26, 268, 20), (-13, 306, 22), (0, 326, 24),
                        (13, 306, 22), (26, 268, 20), (40, 224, 17)]:
        a_t = math.radians(90 + ang)
        ex = TAIL_BASE[0] + ln*math.cos(a_t) - 500.0
        ey = TAIL_BASE[1] + ln*math.sin(a_t) - 500.0
        rr = math.hypot(ex, ey)
        if rr > 416.0:
            ln = max(80.0, ln * (416.0/rr) * 0.99)
        d = feather(TAIL_BASE[0], TAIL_BASE[1], 90 + ang, ln, hw, bias=0.44, tipw=1.4)
        path(d, "url(#gT)")
        for fr in (0.30, 0.48, 0.66, 0.82):
            a = math.radians(90 + ang)
            bx = TAIL_BASE[0] + ln*fr*math.cos(a); by = TAIL_BASE[1] + ln*fr*math.sin(a)
            sp = hw*(1.0 - 0.45*fr)
            for s in (-1, 1):
                p1 = rot(-sp*0.55, sp*0.40, 90 + ang)
                p2 = rot(-sp*1.20, sp*1.30, 90 + ang)
                add(f'<path d="M {f(bx)} {f(by)} Q {f(bx+p1[0])} {f(by+p1[1])} '
                    f'{f(bx+p2[0])} {f(by+p2[1])}" fill="none" stroke="{st}" '
                    f'stroke-width="0.9" opacity=".45"/>')
    add('</g>')

    # ---------- 双翼：沿翼骨 fanned 羽片 ----------
    add('<g id="wings">')
    SHOULDER = (524.0, 438.0)
    BONE_LEN = 214.0
    BONE_ANG = -22.0
    # 主飞羽（长度按圆内反算，尖端不越环）
    RMAX = 416.0
    def clamp_len(bx, by, ang_deg, want):
        a = math.radians(ang_deg)
        ex, ey = bx + want*math.cos(a) - 500.0, by + want*math.sin(a) - 500.0
        r = math.hypot(ex, ey)
        return want if r <= RMAX else max(60.0, want * (RMAX / r) * 0.99)
    N = 12
    for k in range(N):
        t = k/(N-1)
        bx = SHOULDER[0] + BONE_LEN*t*math.cos(math.radians(BONE_ANG))
        by = SHOULDER[1] + BONE_LEN*t*math.sin(math.radians(BONE_ANG))
        ang = -98 + 92*t
        ln = clamp_len(bx, by, ang, 176 + 150*t)
        hw = 21 - 6*t
        d = feather(bx, by, ang, ln, hw, bias=0.40, tipw=1.1)
        for dd in both(d): path(dd, "url(#gW2)" if k % 2 else "url(#gW)")
    # 次级覆羽（短，骨内下侧）
    N2 = 8
    for k in range(N2):
        t = k/(N2-1)
        bx = SHOULDER[0] + (BONE_LEN*0.66)*t*math.cos(math.radians(BONE_ANG))
        by = SHOULDER[1] + (BONE_LEN*0.66)*t*math.sin(math.radians(BONE_ANG)) + 26
        ang = -86 + 76*t
        ln = clamp_len(bx, by, ang, 108 + 92*t)
        hw = 19 - 4*t
        d = feather(bx, by, ang, ln, hw, bias=0.44, tipw=0.9)
        for dd in both(d): path(dd, "url(#gW)")
    add('</g>')

    # ---------- 身体 ----------
    add('<g id="body">')
    body = ("M 500 316 C 538 322 562 356 568 410 C 574 470 560 534 524 578 "
            "C 514 590 507 598 500 606 C 493 598 486 590 476 578 "
            "C 440 534 426 470 432 410 C 438 356 462 322 500 316 Z")
    for dd in both(body): path(dd, "url(#gB)")
    # 颈（宽颈短，连头身）
    neck = ("M 500 318 C 512 296 514 274 508 254 L 466 254 "
            "C 472 274 474 296 470 318 Z")
    path(neck, "url(#gB)")
    # 头
    head = ("M 487 202 C 517 200 538 220 540 244 C 542 270 524 288 498 290 "
            "C 472 292 454 274 453 250 C 452 226 465 204 487 202 Z")
    path(head, "url(#gB)")
    # 喙
    add(f'<path d="M 536 238 C 560 238 580 244 596 254 C 574 259 552 255 534 247 Z" '
        f'fill="{"none" if lm else "#E8B761"}" stroke="{st}" stroke-width="{sw}" stroke-linejoin="round"/>')
    # 冠羽 5 支（向上后扬）
    for k, (ang, ln, hw) in enumerate([(-136, 78, 8), (-120, 100, 9), (-104, 116, 10),
                                       (-88, 98, 9), (-72, 74, 7)]):
        d = feather(487 + (k-2)*4, 206, ang, ln, hw, bias=0.38, tipw=0.5)
        for dd in both(d): path(dd, "url(#gW)")
    add('</g>')

    # ---------- 眼 / 银饰 ----------
    eye = "#12100F" if not lm else st
    add(f'<circle cx="512" cy="240" r="5.8" fill="{eye}"/>')
    add(f'<circle cx="512" cy="240" r="11" fill="none" stroke="{st}" stroke-width="1.1" opacity=".5"/>')
    add('<g id="silver">')
    add(f'<circle cx="500" cy="452" r="8" fill="{st}" opacity=".95"/>')
    add(f'<circle cx="500" cy="452" r="25" fill="none" stroke="{st}" stroke-width="1.3" opacity=".8"/>')
    add(f'<circle cx="500" cy="452" r="37" fill="none" stroke="{st}" stroke-width="1.0" opacity=".42"/>')
    for k in range(8):
        a = 2*math.pi*k/8
        add(f'<circle cx="{f(500+25*math.cos(a))}" cy="{f(452+25*math.sin(a))}" r="3.8" fill="{st}" opacity=".9"/>')
    for x, y, r in [(596, 404, 3.6), (628, 384, 3.2), (660, 366, 2.8)]:
        for xx in (x, W-x):
            add(f'<circle cx="{f(xx)}" cy="{f(y)}" r="{r}" fill="{st}" opacity=".72"/>')
    add('</g>')

    add('</svg>')
    return "\n".join(L)

base = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
open(os.path.join(base, "site/assets/img/phoenix-totem.svg"), "w", encoding="utf-8").write(build("line"))
open(os.path.join(base, "merch/print/phoenix-totem-color.svg"), "w", encoding="utf-8").write(build("fill"))
open(os.path.join(base, "merch/print/phoenix-totem-mono.svg"), "w", encoding="utf-8").write(build("line").replace("#D4A24C", "#000000"))
mark = build("line").replace('viewBox="0 0 1000 1000" width="1000" height="1000"', 'viewBox="14 14 972 972" width="64" height="64"')
open(os.path.join(base, "site/assets/img/phoenix-mark.svg"), "w", encoding="utf-8").write(mark)
print("v6 ok")
