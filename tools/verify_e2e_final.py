
import os, time, base64, json
import numpy as np, cv2
from playwright.sync_api import sync_playwright
BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
OUT = os.path.join(BASE, "_dev", "e2e")
CHROME = r"D:\playwright-cache\chromium-1243\chrome-win64\chrome.exe"
src = cv2.imread(os.path.join(BASE, "site", "assets", "img", "statue-cut.webp"), cv2.IMREAD_UNCHANGED)
poster = cv2.imread(os.path.join(BASE, "素材", "597fa4848ad5fdef17da516d62a85099.jpg"))
px0,py0,px1,py1 = 341,340,931,1627
truth = poster[py0:py1+1, px0:px1+1]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--force-device-scale-factor=1"])
    pg = b.new_page(viewport={"width": 1440, "height": 980})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8791/?fin=%d" % int(time.time()), wait_until="networkidle")
    pg.wait_for_timeout(1800)
    pg.evaluate("() => document.getElementById('carve-sec').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(800)
    pg.evaluate("() => { window.__carve.set(1); window.__carve.play(false); }")
    pg.wait_for_timeout(1300)
    geo = pg.evaluate("""() => {
      const c = document.getElementById('carve-stage');
      const W = c.clientWidth, H = c.clientHeight, wide = W >= 900;
      const box = wide ? { cx: W*0.66, cy: H*0.60, s: Math.min(H*0.84/1.02, W*0.42) }
                       : { cx: W*0.5, cy: H*0.575, s: Math.min(H*0.84/1.02, W*0.86) };
      const g = window.WOOD_TO_STATUE.imageGeom(box);
      return { W, H, x: g.x, y: g.y, w: g.w, h: g.h };
    }""")
    url = pg.evaluate("() => document.getElementById('carve-stage').toDataURL('image/png')")
    open(os.path.join(OUT, "FINAL_canvas.png"), "wb").write(base64.b64decode(url.split(",",1)[1]))
    pg.screenshot(path=os.path.join(OUT, "FINAL_page.png"))
    print("errors:", errs[:3])
    b.close()

print("geo:", geo)
C = cv2.imread(os.path.join(OUT, "FINAL_canvas.png"), cv2.IMREAD_UNCHANGED)
x,y,w,h = int(geo["x"]), int(geo["y"]), int(geo["w"]), int(geo["h"])
reg = C[y:y+h, x:x+w]
t = cv2.resize(truth, (w, h), interpolation=cv2.INTER_AREA)
alpha_s = cv2.resize(src[:,:,3], (w, h), interpolation=cv2.INTER_AREA)
inner = alpha_s > 250
d = np.abs(reg[:,:,:3].astype(np.int16) - t.astype(np.int16)).max(axis=2)[inner]
print("=== 端到端：真实画布 vs 海报原像素（显示 %dx%d）===" % (w, h))
print("内部像素 %d" % int(inner.sum()))
print("完全相同 %.2f%%   <=2 %.2f%%   <=4 %.2f%%   平均 %.2f  P99 %.0f  最大 %d"
      % ((d==0).mean()*100, (d<=2).mean()*100, (d<=4).mean()*100, d.mean(), np.percentile(d,99), d.max()))
