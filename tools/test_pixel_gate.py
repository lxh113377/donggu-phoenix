
import os, sys, shutil, subprocess, re
import numpy as np, cv2
BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
ASSET = os.path.join(BASE, "site", "assets", "img", "statue-cut.webp")
PROF = os.path.join(BASE, "site", "assets", "data", "statue-profile.js")
R1 = os.path.join(BASE, "_dev", "e2e", "render_1to1.png")
LOCK = os.path.join(BASE, "tools", "statue-lock.json")
BAK = os.path.join(BASE, "_dev", "e2e", "_bak")
os.makedirs(BAK, exist_ok=True)

# 🔴 备份只能建一次，且必须与「权威源」一致，否则会自我污染。
# 一手事故（2026-10-20 轮6）：第一轮跑完把当时状态的资产存进 _bak；
# 后来资产被合法更新（无损编码换 Pillow，342KB→330KB），
# 第二轮跑反向验证时 finally 把**旧备份**写回 —— 复原成了 342KB 的过期版本，
# 于是「复原后」永远判红，而人只会怀疑门禁写错了。
# 修法：每次运行前若 _bak 与工作区不一致，就以工作区为准刷新备份（工作区=权威），
# 并在结束时用 SHA256 断言「已回到运行前状态」。
import hashlib
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

START_SHA = {}
for p in (ASSET, PROF, R1, LOCK):
    if os.path.exists(p):
        START_SHA[p] = sha(p)
        d = os.path.join(BAK, os.path.basename(p))
        shutil.copy2(p, d)   # 无条件以工作区为准刷新

def run(extra=None):
    cmd = [sys.executable, os.path.join(BASE, "tools", "verify_pixel_exact.py")] + (extra or [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def bk(p):
    d = os.path.join(BAK, os.path.basename(p))
    if not os.path.exists(d): shutil.copy2(p, d)
    return d
def rs(p):
    d = os.path.join(BAK, os.path.basename(p))
    if os.path.exists(d): shutil.copy2(d, p)

for p in (ASSET, PROF, R1, LOCK): bk(p)
try:
    print("=== 反向验证：逐层破坏，门禁必须判红 ===")
    rc, out = run()
    print("基线:", rc, "|", [l for l in out.splitlines() if l.startswith("RESULT")])

    im = cv2.imread(ASSET, cv2.IMREAD_UNCHANGED)

    bad = im.copy(); bad[:,:,:3] = np.clip(bad[:,:,:3].astype(np.int16)+6, 0, 255).astype(np.uint8)
    cv2.imwrite(ASSET, bad, [int(cv2.IMWRITE_WEBP_QUALITY), 101])
    rc, out = run()
    print("破L1(偏色+6):     ", rc, "|", [l for l in out.splitlines() if l.startswith("[FAIL]") and "L1 " in l][:1])
    rs(ASSET)

    cv2.imwrite(ASSET, im, [int(cv2.IMWRITE_WEBP_QUALITY), 90])
    rc, out = run()
    print("破L2(有损q90):    ", rc, "|", [l for l in out.splitlines() if l.startswith("[FAIL]") and "L2" in l][:1])
    rs(ASSET)

    # 破坏 L1'：只改资产但不更新锁
    im2 = im.copy(); im2[600, 300, :3] = 255 - im2[600, 300, :3]
    cv2.imwrite(ASSET, im2, [int(cv2.IMWRITE_WEBP_QUALITY), 101])
    rc, out = run()
    print("破L1'(改1像素):   ", rc, "|", [l for l in out.splitlines() if l.startswith("[FAIL]") and "L1'" in l][:1])
    rs(ASSET)

    t = open(PROF, encoding="utf-8").read()
    left = re.search(r"left:\s*(\[\[.*?\]\])", t, re.S).group(1)
    open(PROF, "w", encoding="utf-8").write(re.sub(r"right:\s*\[\[.*?\]\]", "right: " + left, t, count=1, flags=re.S))
    rc, out = run()
    print("破L3(左右对称):   ", rc, "|", [l for l in out.splitlines() if l.startswith("[FAIL]") and "L3" in l][:1])
    rs(PROF)

    r_im = cv2.imread(R1, cv2.IMREAD_UNCHANGED)
    M = np.float32([[1,0,3],[0,1,0]])
    cv2.imwrite(R1, cv2.warpAffine(r_im, M, (r_im.shape[1], r_im.shape[0])))
    rc, out = run()
    print("破L4(偏移3px):    ", rc, "|", [l for l in out.splitlines() if l.startswith("[FAIL]") and "L4 " in l][:1])
    rs(R1)

    eng = os.path.join(BASE, "site", "assets", "js", "wood-to-statue.js")
    bk(eng)
    et = open(eng, encoding="utf-8").read()
    open(eng, "w", encoding="utf-8").write(et.replace("Math.round(box.cx", "Math.floor(box.cx"))
    rc, out = run()
    print("破L4'(去整像素):  ", rc, "|", [l for l in out.splitlines() if l.startswith("[FAIL]") and "L4'" in l][:1])
    rs(eng)

    print()
    rc, out = run(); print("复原后:", rc, "|", [l for l in out.splitlines() if l.startswith("RESULT")])
    rc, out = run(["--require-full"]); print("发布前口径:", rc, "|", [l for l in out.splitlines() if l.startswith("RESULT")])
finally:
    for p in (ASSET, PROF, R1, LOCK):
        rs(p)
    # 断言真的回到了运行前状态（不然「复原后 PASS」是假的）
    bad = []
    for p, want in START_SHA.items():
        if not os.path.exists(p) or sha(p) != want:
            bad.append(os.path.basename(p))
    if bad:
        print("⚠ 复原未完成（SHA 不符）：", "、".join(bad))
    else:
        print("复原校验：SHA256 与运行前一致（%d 个文件）" % len(START_SHA))
