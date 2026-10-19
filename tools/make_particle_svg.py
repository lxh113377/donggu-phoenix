# -*- coding: utf-8 -*-
"""生成粒子专用 SVG：纯实心剪影（无描边、无外环），供 phoenix.js 像素采样。
复用 make_totem 的几何定义，通过 import 执行其模块级 build 函数的 fill 模式再裁剪。
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_totem as mt

BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"

svg = mt.build("fill")
# 去掉外环组
svg = re.sub(r'<g id="ring">.*?</g>', '', svg, flags=re.S)
# 去掉所有 stroke 属性
svg = re.sub(r'\sstroke="[^"]*"', '', svg)
svg = re.sub(r'\sstroke-width="[^"]*"', '', svg)
svg = re.sub(r'\sstroke-linejoin="[^"]*"', '', svg)
svg = re.sub(r'\sstroke-linecap="[^"]*"', '', svg)
# 去掉眼与银饰细节（粒子不需要）
svg = re.sub(r'<g id="silver">.*?</g>', '', svg, flags=re.S)
# 所有填充统一为白色（粒子颜色在 JS 端按位置重新着色）
svg = re.sub(r'fill="url\([^)]*\)"', 'fill="#FFFFFF"', svg)
svg = re.sub(r'fill="#[0-9A-Fa-f]{6}"', 'fill="#FFFFFF"', svg)
svg = svg.replace('width="1000" height="1000"', 'width="1000" height="1000"', 1)


out = os.path.join(BASE, "site", "assets", "img", "phoenix-particle.svg")
open(out, "w", encoding="utf-8").write(svg)
print("particle svg", len(svg), "bytes ->", out)
