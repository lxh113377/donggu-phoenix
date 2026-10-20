
import os, time, base64
import numpy as np, cv2
from playwright.sync_api import sync_playwright

BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
OUT = os.path.join(BASE, "_dev", "verify")
os.makedirs(OUT, exist_ok=True)
CHROME = r"D:\playwright-cache\chromium-1243\chrome-win64\chrome.exe"
SRC = os.path.join(BASE, "site", "assets", "img", "statue-cut.webp")
src = cv2.imread(SRC, cv2.IMREAD_UNCHANGED)
H0, W0 = src.shape[:2]
DOM = float(np.array(cv2.imread(SRC, cv2.IMREAD_UNCHANGED).shape[:2]).tolist()[0]) if False else float(H0)
print("源图", W0, "x", H0)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--force-device-scale-factor=1"])
    pg = b.new_page(viewport={"width": 1440, "height": 960})
    pg.goto("http://127.0.0.1:8791/?px=%d" % int(time.time()), wait_until="networkidle")
    pg.wait_for_timeout(2000)
    # 让 gh == 源图高（1:1 渲染），再看差多少
    meta = pg.evaluate("""(targetH) => {
      const P = window.STATUE_PROFILE;
      const s = targetH / P.span;
      const g = window.WOOD_TO_STATUE.imageGeom({ cx: 0, cy: 0, s: s });
      return { s: s, gw: g.w, gh: g.h, aspect: P.image.aspect };
    }""", float(H0))
    print("geometry", meta)
    s = meta["s"]
    info = pg.evaluate("""(S) => {
      const E = window.WOOD_TO_STATUE;
      const box0 = { cx: 0, cy: 0, s: S };
      const g0 = E.imageGeom(box0);
      const W = Math.round(g0.w), H = Math.round(g0.h);
      const c = document.createElement('canvas');
      c.width = W; c.height = H;
      const ctx = c.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      E.draw(ctx, W, H, 1.0, 0, { box: { cx: -g0.x, cy: -g0.y, s: S }, backdrop: false, beam: false, tools: false, motes: false });
      return { W, H, url: c.toDataURL('image/png') };
    }""", s)
    open(os.path.join(OUT, "offscreen_1to1.png"), "wb").write(base64.b64decode(info["url"].split(",",1)[1]))
    print("画布", info["W"], "x", info["H"])
    b.close()

im = cv2.imread(os.path.join(OUT, "offscreen_1to1.png"), cv2.IMREAD_UNCHANGED)
print("读回", im.shape)
Hc, Wc = im.shape[:2]
h = min(H0, Hc); w = min(W0, Wc)
a = src[:h, :w].astype(np.int16)
c2 = im[:h, :w].astype(np.int16)
mask = (a[:,:,3] > 250) & (c2[:,:,3] > 250)
print("不透明像素", int(mask.sum()), "占 %.1f%%" % (mask.sum()/mask.size*100))
d = np.abs(a[:,:,:3] - c2[:,:,:3])[mask]
print("=== 1:1 渲染 vs 源资产 ===")
print("RGB 平均绝对误差 %.3f" % d.mean())
print("最大误差 %d" % d.max())
print("误差=0 的像素 %.2f%%" % (float((d==0).mean())*100))
print("误差<=2 的像素 %.2f%%" % (float((d<=2).mean())*100))
print("P99 误差 %.1f" % np.percentile(d, 99))
