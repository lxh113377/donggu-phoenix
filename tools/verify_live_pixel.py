
import os, time, base64, json, hashlib
import numpy as np, cv2
from playwright.sync_api import sync_playwright
BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
OUT = os.path.join(BASE, "_dev", "e2e")
CHROME = r"D:\playwright-cache\chromium-1243\chrome-win64\chrome.exe"
LIVE = "https://lxh113377.github.io/donggu-phoenix/"
poster = cv2.imread(os.path.join(BASE, "素材", "597fa4848ad5fdef17da516d62a85099.jpg"))
truth = poster[340:1628, 341:932]
asset = cv2.imread(os.path.join(BASE, "site", "assets", "img", "statue-cut.webp"), cv2.IMREAD_UNCHANGED)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--force-device-scale-factor=1"])
    pg = b.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=2)
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(LIVE + "?live2=%d" % int(time.time()), wait_until="networkidle", timeout=90000)
    pg.wait_for_timeout(3000)
    print("build:", pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--build').trim()"))
    # 线上 1:1 渲染（验证部署后的引擎+资产组合）
    url = pg.evaluate("""async (targetH) => {
      const E = window.WOOD_TO_STATUE, P = window.STATUE_PROFILE;
      const S = targetH / P.span;
      const iw = S * P.span * P.image.aspect;
      const axis = (P.axis == null ? 0.5 : P.axis);
      const g = E.imageGeom({ cx: iw * axis, cy: 0.62 * S, s: S });
      const W = Math.round(g.w), H = Math.round(g.h);
      const c = document.createElement('canvas'); c.width = W; c.height = H;
      const ctx = c.getContext('2d');
      E.draw(ctx, W, H, 1.0, 0, { box: { cx: iw*axis, cy: 0.62*S, s: S }, backdrop: false, beam: false, tools: false, motes: false });
      return c.toDataURL('image/png');
    }""", float(asset.shape[0]))
    open(os.path.join(OUT, "LIVE_1to1.png"), "wb").write(base64.b64decode(url.split(",",1)[1]))
    # 真实画布（DPR2）
    pg.evaluate("() => document.getElementById('carve-sec').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(900)
    pg.evaluate("() => { window.__carve.set(1); window.__carve.play(false); }")
    pg.wait_for_timeout(1300)
    pg.screenshot(path=os.path.join(OUT, "LIVE_page.png"))
    print("errors:", errs[:4])
    b.close()

got = cv2.imread(os.path.join(OUT, "LIVE_1to1.png"), cv2.IMREAD_UNCHANGED)
print("线上 1:1 渲染", got.shape, "本地资产", asset.shape)
vis = (asset[:,:,3] > 250) & (got[:,:,3] > 250)
d = np.abs(asset[:,:,:3].astype(np.int16) - got[:,:,:3].astype(np.int16)).max(axis=2)[vis]
print("线上 1:1 vs 本地资产：%d 像素，完全相同 %.2f%%，最大误差 %d" % (int(vis.sum()), (d==0).mean()*100, d.max()))
