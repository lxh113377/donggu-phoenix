# -*- coding: utf-8 -*-
"""tools/reverse_replace_merch_photo.py —— replace_merch_photo 的反向验证（沙箱副本，绝不碰真站）。

为什么必须反向验
  这条流水线会**直接覆盖线上图片**。它自己说「门禁判红就回滚」，
  不造一次门禁红，永远不知道回滚是真是假（U-222/U-224 同族教训：
  「加了回滚代码」不等于「回滚真的把文件恢复了」）。

用例（全部在 _qa/rmp_sandbox/ 里跑，真站文件零改动）
  A validate_source：小于 620 的图必须拒
  B validate_source：纯灰占位图必须拒
  C square_crop + encode：输出必须正好 620×620 且 <= 120KB
  D 门禁判红 -> 必须回滚：主图与小档 SHA256 必须逐字回到替换前
  E manifest 只在成功时写；D 之后不得出现该条目
  F 未知 id 必须拒（防把 r-<拼错>.webp 写进部署面变成孤儿资产）
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import traceback

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(BASE, "_qa", "rmp_sandbox")
SITE = os.path.join(SANDBOX, "site")
MERCH = os.path.join(SITE, "assets", "img", "merch")
DATA = os.path.join(SITE, "assets", "data")
SRC = os.path.join(SANDBOX, "src")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_mod():
    spec = importlib.util.spec_from_file_location(
        "rmp", os.path.join(BASE, "tools", "replace_merch_photo.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.BASE = SANDBOX
    m.SITE = SITE
    m.SHOT = os.path.join(SANDBOX, "merch", "shot")
    m.ARCHIVE = os.path.join(SANDBOX, "_dev", "merch-renders")
    m.MANIFEST = os.path.join(SANDBOX, "merch", "shot-manifest.json")
    return m


def build_sandbox():
    shutil.rmtree(SANDBOX, ignore_errors=True)
    for d in (MERCH, DATA, SRC, os.path.join(SANDBOX, "merch")):
        os.makedirs(d, exist_ok=True)
    open(os.path.join(DATA, "culture.js"), "w", encoding="utf-8").write(
        "var CULTURE = { merch: [\n"
        "  { id: 'badge', image: 'assets/img/merch/r-badge.webp', name: '凤凰徽章' },\n"
        "  { id: 'tote',  image: 'assets/img/merch/r-tote.webp', name: '凤纹帆布袋' },\n"
        "]};\n")
    from PIL import Image
    # 现网「旧图」：两个可辨识的小 webp
    for f in ("r-badge.webp", "r-tote.webp"):
        Image.new("RGB", (620, 620), (200, 30, 30)).save(os.path.join(MERCH, f), "WEBP")
    for f in ("r-badge-340.webp", "r-tote-340.webp"):
        Image.new("RGB", (340, 340), (200, 30, 30)).save(os.path.join(MERCH, f), "WEBP")
    # 合格「实拍」：620+ 且有内容方差
    im = Image.new("RGB", (900, 700), (10, 20, 30))
    dr_px = im.load()
    for y in range(700):
        for x in range(0, 900, 7):
            dr_px[x, y] = ((x * 7 + y) % 251, (x * 3) % 253, (y * 5) % 249)
    im.save(os.path.join(SRC, "good.jpg"), quality=92)
    Image.new("RGB", (300, 300), (120, 120, 120)).save(os.path.join(SRC, "small.png"))
    Image.new("RGB", (900, 900), (128, 128, 128)).save(os.path.join(SRC, "flat.png"))


def expect_reject(m, path, tag, want):
    try:
        m.validate_source(path)
    except SystemExit as e:
        msg = str(e)
        if want in msg:
            print("  [PASS] %s 被拒：%s" % (tag, msg[:70]))
            return True
        print("  [FAIL] %s 拒了但理由不对：%s" % (tag, msg[:90]))
        return False
    print("  [FAIL] %s 没被拒（坏图混进线上了）" % tag)
    return False


def main():
    build_sandbox()
    m = load_mod()
    fails = []

    print("A/B 坏图准入校验")
    if not expect_reject(m, os.path.join(SRC, "small.png"), "小于 620", "小于目标"):
        fails.append("A")
    if not expect_reject(m, os.path.join(SRC, "flat.png"), "纯灰占位", "动态范围"):
        fails.append("B")

    print("C 规格与预算")
    try:
        im, _ = m.validate_source(os.path.join(SRC, "good.jpg"))
        out = m.square_crop(im).resize((m.TARGET, m.TARGET), m.Image.LANCZOS)
        tmp = os.path.join(SANDBOX, "enc.webp")
        sz = m.encode(out, tmp, 82)
        from PIL import Image as I
        w, h = I.open(tmp).size
        if (w, h) != (620, 620):
            fails.append("C 尺寸 %dx%d" % (w, h))
        elif sz > m.MAX_MAIN:
            fails.append("C 超预算 %.0fKB" % (sz / 1024))
        else:
            print("  [PASS] 620x620 / %.0fKB <= 120KB" % (sz / 1024))
    except Exception as e:
        fails.append("C 异常 " + str(e))

    print("D/E 门禁判红必须回滚（伪造 gate 失败）")
    before_main = sha(os.path.join(MERCH, "r-badge.webp"))
    before_small = sha(os.path.join(MERCH, "r-badge-340.webp"))
    real_run_gate = m.run_gate
    m.run_gate = lambda name: (False, "forced-fail（反向验证注入）")
    rolled_back = False
    try:
        m.replace_one("badge", os.path.join(SRC, "good.jpg"))
        print("  [FAIL] 门禁判红却正常返回（回滚是假的）")
        fails.append("D 未抛错")
    except SystemExit as e:
        msg = str(e)
        after_main = sha(os.path.join(MERCH, "r-badge.webp"))
        after_small = sha(os.path.join(MERCH, "r-badge-340.webp"))
        if after_main == before_main and after_small == before_small:
            print("  [PASS] 主图与小档 SHA 逐字回到替换前：%s" % msg[:60])
            rolled_back = True
        else:
            print("  [FAIL] 抛了错但文件没还原：main %s→%s" % (before_main[:8], after_main[:8]))
            fails.append("D 回滚不彻底")
    except Exception:
        print("  [FAIL] 非预期异常：\n" + traceback.format_exc()[-300:])
        fails.append("D 异常类型")
    finally:
        m.run_gate = real_run_gate
    mf_path = os.path.join(SANDBOX, "merch", "shot-manifest.json")
    if os.path.exists(mf_path):
        d = json.load(open(mf_path, encoding="utf-8"))
        if "badge" in d.get("items", {}):
            print("  [FAIL] 回滚后 manifest 仍写了 badge（E）")
            fails.append("E")
        else:
            print("  [PASS] 失败未污染 manifest")
    else:
        print("  [PASS] 失败未生成 manifest")

    print("F 未知 id")
    try:
        m.replace_one("badg", os.path.join(SRC, "good.jpg"))
        print("  [FAIL] 拼错的 id 混进去了（会在部署面造孤儿资产）")
        fails.append("F")
    except SystemExit as e:
        print("  [PASS] 未知 id 被拒：%s" % str(e)[:60])

    print("G 成功路径（真跑沙箱门禁桩）")
    m.run_gate = lambda name: (True, "stub-pass")
    try:
        m.replace_one("tote", os.path.join(SRC, "good.jpg"))
        from PIL import Image as I
        w, h = I.open(os.path.join(MERCH, "r-tote.webp")).size
        d = json.load(open(mf_path, encoding="utf-8"))
        if (w, h) == (620, 620) and "tote" in d.get("items", {}) and d["items"]["tote"]["source_sha256"]:
            print("  [PASS] 替换成功且 manifest 记全（source/live/render 三 sha + 日期）")
        else:
            fails.append("G manifest/尺寸不完整")
    except Exception as e:
        fails.append("G 异常 " + str(e))

    print()
    if fails:
        print("RESULT: FAIL  反向验证未通过：" + "; ".join(fails))
        return 1
    print("RESULT: PASS  7 项反向验证全过（坏图拒收 / 规格预算 / 门禁红必回滚 / 不污染 manifest / 未知 id 拒 / 成功路径留痕）")
    return 0


if __name__ == "__main__":
    rc = main()
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(rc)
