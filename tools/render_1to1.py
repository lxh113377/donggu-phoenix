# -*- coding: utf-8 -*-
"""render_1to1.py — 用引擎按「源图高度」离屏渲染一次，落 _dev/e2e/render_1to1.png。

这是 verify_pixel_exact 层4 的取证器：把「引擎画出来的像素」与「资产文件」放在一起比。
必须在浏览器里渲染（引擎是 Canvas 2D），故用 Playwright 驱动本地 Chromium。

关键实现细节（都踩过）：
  - 必须先 scrollIntoView，否则 IntersectionObserver 判定不可见、raf 直接 return；
  - 图片要 await decode()，否则首帧 drawImage 画的是空白；
  - 用 p=1 且只开成品层（关 backdrop/beam/tools/motes），把变量收敛到「照片有没有被画对」；
  - 画布尺寸取整（Math.round），避免半像素带来额外重采样。
"""
import os
import sys
import base64
import time

import numpy as np
import cv2
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "_dev", "e2e")
OUT = os.path.join(OUT_DIR, "render_1to1.png")
CHROME = os.environ.get("CHROME_PATH", r"D:\playwright-cache\chromium-1243\chrome-win64\chrome.exe")
URL = os.environ.get("SITE_URL", "http://127.0.0.1:8791/")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    asset_path = os.path.join(BASE, "site", "assets", "img", "statue-cut.webp")
    asset = cv2.imread(asset_path, cv2.IMREAD_UNCHANGED)
    if asset is None:
        raise SystemExit("找不到资产: " + asset_path)
    target_h = float(asset.shape[0])

    with sync_playwright() as pw:
        launch = {"args": ["--force-device-scale-factor=1"]}
        if os.path.exists(CHROME):
            launch["executable_path"] = CHROME
        b = pw.chromium.launch(**launch)
        pg = b.new_page(viewport={"width": 1440, "height": 980})
        pg.goto(URL + "?r1=%d" % int(time.time()), wait_until="networkidle")
        pg.wait_for_timeout(1800)
        # 让引擎把自己初始化完（IntersectionObserver 需要元素在视口里才会装驱动）
        pg.evaluate("() => document.getElementById('carve-sec').scrollIntoView({block:'center'})")
        pg.wait_for_timeout(900)

        url = pg.evaluate("""async (targetH) => {
          const E = window.WOOD_TO_STATUE, P = window.STATUE_PROFILE;
          if (!E || !P) throw new Error('engine/profile missing');
          const S = targetH / P.span;
          const g = E.imageGeom({ cx: 0, cy: 0, s: S });
          const W = Math.round(g.w), H = Math.round(g.h);
          const c = document.createElement('canvas');
          c.width = W; c.height = H;
          const ctx = c.getContext('2d');
          /* 反解 box，使图片左上角落在 (0,0)。
           * imageGeom 的关系是 x = round(cx - iw*axis)、y = round(cy + TOP*s)，
           * 而 g 是用 cx=0, cy=0 探出来的，它只是「在该 box 下的落点」，不是绝对坐标 ——
           * 直接拿 -g.x/-g.y 当平移量会算错（实测渲染落在 y=783，画布只有 1288 高，
           * 于是层4 判 0% 相同）。正解是按定义反解：cx = iw*axis，cy = -TOP*s。 */
          const TOP = -0.62;
          const iw = S * P.span * P.image.aspect;
          const axis = (P.axis == null ? 0.5 : P.axis);
          const box = { cx: iw * axis, cy: -TOP * S, s: S };
          E.draw(ctx, W, H, 1.0, 0, {
            box: box, backdrop: false, beam: false, tools: false, motes: false
          });
          return c.toDataURL('image/png');
        }""", target_h)
        raw = base64.b64decode(url.split(",", 1)[1])
        with open(OUT, "wb") as f:
            f.write(raw)
        b.close()

    got = cv2.imread(OUT, cv2.IMREAD_UNCHANGED)
    print("渲染完成:", OUT)
    print("  资产 %dx%d / 渲染 %dx%d" % (asset.shape[1], asset.shape[0], got.shape[1], got.shape[0]))
    if got.shape[:2] != asset.shape[:2]:
        print("  ⚠ 尺寸不一致，层4 会判红")
        return 1
    vis = (asset[:, :, 3] > 250) & (got[:, :, 3] > 250)
    d = np.abs(asset[:, :, :3].astype(np.int16) - got[:, :, :3].astype(np.int16)).max(axis=2)[vis]
    print("  共同像素 %d，完全相同 %.2f%%，最大误差 %d"
          % (int(vis.sum()), (d == 0).mean() * 100, d.max()))
    return 0 if d.max() == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
