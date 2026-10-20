# -*- coding: utf-8 -*-
"""tools/make_srcset.py — 为 12 件文创实物效果图生成响应式小档（I-6，2026-10-20 轮50）。

为什么需要它：对标实测 srcset=0、loading="lazy" 仅 1 处（docs/对标分析报告.md §3.1 缺口 4）。
文创卡片在网格里实际只有 ~150px 高（DPR 2 → 300px），却整张拉 620px 原图；
移动端首访走 4G，r-badge 一张 51KB 而它只需要 15KB。

档位选择（不贪多，两档足够）：
  · 620w 原图 —— 留给「全部」视图首件的 2x2 特写大格（76% × 420px ≈ 320px，DPR2 = 640px）；
  · 340w 小档 —— 覆盖窄屏与归一网格（232px 列宽 × DPR2 = 464px 取不到，340w 在 150px 展示位有冗余）。
  不做第三档：多一档就多一倍部署文件，而本站只有两种展示尺寸。

用法: python tools/make_srcset.py [--dry]
"""
import os, re, sys
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
SMALL_W = 340


def merch_images():
    """从唯一内容源 culture.js 读取 image 字段，不另立一份清单（防清单与数据漂移）。"""
    s = open(os.path.join(SITE, "assets", "data", "culture.js"), encoding="utf-8").read()
    return re.findall(r"image: '([^']+\.(?:webp|png|jpg))'", s)


def small_path(rel):
    root, ext = os.path.splitext(rel)
    return root + "-340" + ext


def main():
    dry = "--dry" in sys.argv
    rels = merch_images()
    if not rels:
        print("culture.js 未读到任何 image 字段（判据失配，不静默通过）")
        return 1
    saved = 0
    rows = []
    for rel in rels:
        p = os.path.join(SITE, rel.replace("/", os.sep))
        if not os.path.exists(p):
            print("  MISSING", rel)
            return 1
        sp = os.path.join(SITE, small_path(rel).replace("/", os.sep))
        im = Image.open(p)
        # 一律出同目录 -340 兄弟档（不放大：原图窄于 340 就按原宽重编）。
        # 为什么不留"窄图跳档"的空隙：前端 main.js 只看得到路径、看不到像素宽，
        # 一旦约定是「有档就写 srcset」，漏一件就是线上 404。让命名约定无条件成立，
        # 前端就能无条件引用。
        tw = min(SMALL_W, im.width)
        h = int(round(im.height * tw / im.width))
        out = im.convert("RGBA").resize((tw, h), Image.LANCZOS)
        if not dry:
            out.save(sp, "WEBP", quality=80, method=6)
        ns = os.path.getsize(sp) if not dry else 0
        rows.append((rel, os.path.getsize(p), ns, "%dx%d -> %dx%d" % (im.width, im.height, SMALL_W, h)))
        saved += os.path.getsize(p) - ns if not dry else 0
    print(("DRY RUN " if dry else "生成 ") + "%d 档" % len(rows))
    for r in rows:
        print("  %-38s %6dB %6dB  %s" % (r[0], r[1], r[2], r[3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())