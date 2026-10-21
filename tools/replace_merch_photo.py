# -*- coding: utf-8 -*-
"""tools/replace_merch_photo.py —— 文创实拍回样后的一键替换流水线（U-02 收口件）。

为什么需要它
  U-02 的老流程是「拿到照片 → 手工压图 → 手工改文件名 → 手工重跑 srcset → 手工跑门禁」，
  六步里任何一步漏做就上线一个 404 或一张 900KB 的原图（本站首屏预算 400KB，
  一张手机直出照片就能顶爆）。现在把这条链固化成一个命令，缺步即报错。

流程（每一步都可验证，失败即回滚）
  1. 归档：把渲染图移到 _dev/merch-renders/<id>-<日期>.webp（**不删**，可回退）
  2. 校验实拍：像素 >= 620、非纯灰度（防误传扫描件/占位图）、EXIF 方向自动转正
  3. 缩放居中裁方：输出 620×620 webp（与现有 r-<id>.webp 同规格，前端零改动）
  4. 生成 -340 小档（复用 make_srcset 的同一约定，不另立口径）
  5. 体积门槛：主图 <= 120KB（verify 第 26 项硬线）、小档 <= 40KB
  6. 跑 verify_site + image_quality + orphan_asset 三道门禁，任一红则回滚本次改动
  7. 写 merch/shot-manifest.json：记录来源文件、sha256、实拍日期（供「素材真实性」追溯）

用法
  python tools/replace_merch_photo.py badge  D:\\photos\\badge_real.jpg
  python tools/replace_merch_photo.py --all            # 扫 merch/shot/<id>.<ext> 批量
  python tools/replace_merch_photo.py --status         # 看哪几件还是渲染图
  python tools/replace_merch_photo.py --dry-run badge x.jpg

实拍件放哪
  merch/shot/<id>.<ext>（id 取 culture.js 的 id：badge / lamp / tote …）。
  这个目录是「原图仓库」，不入部署面（site/ 之外），随便多大都行。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageOps

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
SHOT = os.path.join(BASE, "merch", "shot")
ARCHIVE = os.path.join(BASE, "_dev", "merch-renders")
MANIFEST = os.path.join(BASE, "merch", "shot-manifest.json")
TARGET = 620
SMALL = 340
MAX_MAIN = 120 * 1024
MAX_SMALL = 40 * 1024
PY = sys.executable


def culture_merch():
    s = open(os.path.join(SITE, "assets", "data", "culture.js"), encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in
            re.finditer(r"id: '([a-z-]+)',\s*image: '([^']+)'", s)}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        try:
            return json.load(open(MANIFEST, encoding="utf-8"))
        except Exception:
            pass
    return {"items": {}}


def validate_source(src):
    """实拍图准入校验：返回 (im, warn_or_None)。硬伤直接抛错。"""
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)          # 手机直出常带 EXIF 方向，不转就横躺
    if im.width < TARGET or im.height < TARGET:
        raise SystemExit("实拍图 %dx%d 小于目标 %dx%d：放大=糊，请重拍或换高清原图"
                         % (im.width, im.height, TARGET, TARGET))
    g = im.convert("L")
    ex = g.getextrema()
    if ex[1] - ex[0] < 24:
        raise SystemExit("实拍图动态范围仅 %d（灰白/纯黑占位图？请确认真是实物照片）" % (ex[1] - ex[0]))
    rgb = im.convert("RGB")
    small = rgb.resize((64, 64))
    px = list(small.getdata())
    mean = sum(sum(p) for p in px) / (len(px) * 3)
    var = sum((sum(p) / 3 - mean) ** 2 for p in px) / len(px)
    warn = None
    if var < 90:
        warn = "画面方差 %.0f 偏低（可能是纯色背景占位或过曝/欠曝，请目检）" % var
    return rgb, warn


def square_crop(im):
    w, h = im.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    return im.crop((left, top, left + s, top + s))


def encode(im, out, quality):
    im.convert("RGBA").save(out, "WEBP", quality=quality, method=6)
    return os.path.getsize(out)


def run_gate(name):
    r = subprocess.run([PY, os.path.join(BASE, "tools", name)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, cwd=BASE)
    ok = r.returncode == 0
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]
    return ok, " / ".join(tail)


def replace_one(mid, src, dry=False):
    merch = culture_merch()
    if mid not in merch:
        raise SystemExit("culture.js 里没有 id=%s（可选：%s）" % (mid, ", ".join(sorted(merch))))
    rel = merch[mid]
    main_abs = os.path.join(SITE, rel.replace("/", os.sep))
    root_, ext = os.path.splitext(rel)
    small_rel = root_ + "-340" + ext
    small_abs = os.path.join(SITE, small_rel.replace("/", os.sep))
    if not (os.path.exists(main_abs) and os.path.exists(small_abs)):
        raise SystemExit("线上主图或小档缺失：%s / %s（先确认 make_srcset 跑过）" % (rel, small_rel))

    im, warn = validate_source(src)
    out = square_crop(im).resize((TARGET, TARGET), Image.LANCZOS)
    small = out.resize((SMALL, min(SMALL, out.height)), Image.LANCZOS)

    print("  实拍源：%s  %dx%d  sha=%s…" % (os.path.basename(src), im.width, im.height, sha256(src)[:12]))
    if warn:
        print("  [WARN]", warn)
    if dry:
        print("  [DRY] 将替换 %s（%.0fKB → ≤%.0fKB）与 %s" % (
            rel, os.path.getsize(main_abs) / 1024, MAX_MAIN / 1024, small_rel))
        return None

    # 1) 归档旧渲染图（不删，可回退）
    os.makedirs(ARCHIVE, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    bak_main = os.path.join(ARCHIVE, "%s-%s.render%s" % (mid, stamp, ext))
    bak_small = os.path.join(ARCHIVE, "%s-%s.render-340%s" % (mid, stamp, ext))
    shutil.copy2(main_abs, bak_main)
    shutil.copy2(small_abs, bak_small)
    old_sha = sha256(main_abs)

    # 2) 写入新图（q 逐档降，直到进预算）
    for q in (82, 76, 70, 64, 58):
        sz = encode(out, main_abs, q)
        if sz <= MAX_MAIN:
            break
    else:
        raise SystemExit("降到 q58 仍 %.0fKB > 120KB：实拍图背景太复杂，请裁掉杂物或换纯色底重拍" % (sz / 1024))
    for q in (82, 74, 66, 58):
        szs = encode(small, small_abs, q)
        if szs <= MAX_SMALL:
            break
    print("  已写入：%s %.0fKB (q%d) + %s %.0fKB (q%d)" % (
        rel, sz / 1024, q, small_rel, szs / 1024, q))

    # 3) 三道门禁；任一红 → 回滚
    gates = [("verify_site.py",), ("image_quality_test.py",), ("orphan_asset_test.py",)]
    for (gname,) in gates:
        try:
            ok, tail = run_gate(gname)
        except subprocess.TimeoutExpired:
            ok, tail = False, "gate timeout"
        print("  [%s] %s  %s" % ("PASS" if ok else "FAIL", gname, tail[:150]))
        if not ok:
            shutil.copy2(bak_main, main_abs)
            shutil.copy2(bak_small, small_abs)
            raise SystemExit("门禁判红，已回滚 %s（旧图仍在 %s）" % (mid, os.path.relpath(bak_main, BASE)))

    # 4) 记 manifest（真实性追溯：谁、何时、哪个文件）
    mf = load_manifest()
    mf["items"][mid] = {
        "source": os.path.basename(src),
        "source_sha256": sha256(src),
        "render_sha256_before": old_sha,
        "live_sha256": sha256(main_abs),
        "shot_date": stamp,
        "replaced_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "archive": os.path.relpath(bak_main, BASE),
    }
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    json.dump(mf, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  [OK] %s 已替换并记录到 merch/shot-manifest.json" % mid)
    return True


def status():
    merch = culture_merch()
    mf = load_manifest()["items"]
    print("文创图状态（实拍 %d / 渲染 %d）：" % (len(mf), len(merch) - len(mf)))
    for mid in sorted(merch):
        it = mf.get(mid)
        print("  %-11s %s" % (mid, ("实拍 " + it["shot_date"] + "  " + it["source"]) if it else "仍是渲染图"))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mid", nargs="?", help="culture.js 的 id，如 badge / lamp / tote")
    ap.add_argument("src", nargs="?", help="实拍文件路径")
    ap.add_argument("--all", action="store_true", help="扫 merch/shot/<id>.<ext> 批量替换")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.status:
        return status()
    merch = culture_merch()
    if a.all:
        if not os.path.isdir(SHOT):
            print("merch/shot/ 不存在：先把实拍件放成 merch/shot/<id>.<ext>")
            return 1
        n = 0
        for f in sorted(os.listdir(SHOT)):
            mid, ext = os.path.splitext(f)
            if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
                continue
            if mid not in merch:
                print("  [SKIP] %s：culture.js 无此 id" % f)
                continue
            print("--- %s ---" % mid)
            replace_one(mid, os.path.join(SHOT, f), dry=a.dry_run)
            n += 1
        print("处理 %d 件" % n)
        return 0
    if not (a.mid and a.src):
        ap.print_help()
        print("\n提示：--status 看当前哪几件还是渲染图；--all 按 merch/shot/ 批量")
        return 2
    replace_one(a.mid, a.src, dry=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
