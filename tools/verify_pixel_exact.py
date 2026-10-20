# -*- coding: utf-8 -*-
"""verify_pixel_exact.py — 「像素级一比一复刻」的可复核判据（不靠肉眼）。

## 四层判据与「在哪能跑」

| 层 | 判什么 | 需要什么 | 本地 | CI |
|----|--------|----------|------|----|
| L1 | 资产内部像素 == 素材原像素（逐像素相等） | 素材/*.jpg（.gitignore 排除） | 可跑 | SKIP |
| L1' | 资产 SHA256 == 提交的锁值（防漂移） | 只有仓库 | 可跑 | 可跑 |
| L2 | 资产是无损编码（体积比 ≥95% 于无损重编码） | 只有仓库 | 可跑 | 可跑 |
| L3 | 剖面绑定资产 / 左右不对称 / 尺寸一致 | 只有仓库 | 可跑 | 可跑 |
| L4 | 引擎 1:1 渲染像素 == 资产像素 | Playwright + Chromium | 可跑 | SKIP |
| L4' | 引擎源码具备 1:1 通路（整像素对齐 / high 重采样 / 揭示层） | 只有仓库 | 可跑 | 可跑 |

## 为什么要有 L1' / L4' 这对「静态替身」

L1、L4 是真正回答「像不像」的两层，但它们分别依赖素材原件（不进仓库）与浏览器（CI 不装）。
若把它们写成硬 FAIL，CI 就恒红 —— 那是把「环境缺件」误报成「交付缺陷」，
和把红判成绿一样有害。故：
  - 缺件 ⇒ SKIP（明确打印原因，且计入「未取证」，绝不当 PASS）；
  - 同时给一层 commit-able 的替身（L1' 锁值、L4' 源码特征），让「有人动了资产/通路」在 CI 也能红。
L1' 的口径必须说清楚：它证明的是「资产自上次逐像素核验以来没变」，
不是「资产等于素材」—— 后者的证据只存在于本地那一次真实比对。

## 一手教训（本文件是修出来的）

1. L2 曾写成「finally 删掉 tmp 之后再读 tmp 体积」⇒ lossless_size 恒 0 ⇒ 有损永判绿；
2. L2 还曾拿「内存数组无损往返」比 RGB —— 内存本来就无损，等于自己比自己；
3. L3 的两条正则不同形（right 多一层 ]）⇒ 解析必失败；
4. 行首标签曾写死 [PASS]（判据已红但打印绿）⇒ 反向验证当场暴露。
以上四条都是「门禁装饰化」的典型形态，已由 tools/test_pixel_gate.py 的逐层破坏守住。

退出码：0 无 FAIL / 1 有 FAIL / 2 内部错误
用法：python tools/verify_pixel_exact.py [--json] [--require-full]
      --require-full：要求 L1/L4 也必须 PASS（缺件即 FAIL），供本地/发布前使用
"""
import os
import sys
import json
import hashlib
import argparse
import tempfile
try:
    import numpy as np
    import cv2
except ImportError as _e:      # pragma: no cover
    # CI 曾只装 Pillow ⇒ 本脚本 import 期就崩，父脚本把它读成「判据未通过」。
    # 明确的依赖缺口必须能被一眼认出来，别让它伪装成判据失败。
    sys.stderr.write(
        "缺少图像依赖（%s）。请先运行：python -m pip install numpy opencv-python-headless\n"
        "  CI（.github/workflows/deploy-pages.yml）必须与本脚本同依赖，否则本地绿、CI 红。\n" % _e)
    sys.exit(2)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_POSTER = os.path.join(BASE, "素材", "597fa4848ad5fdef17da516d62a85099.jpg")
ASSET = os.path.join(BASE, "site", "assets", "img", "statue-cut.webp")
PROFILE = os.path.join(BASE, "site", "assets", "data", "statue-profile.js")
ENGINE = os.path.join(BASE, "site", "assets", "js", "wood-to-statue.js")
LOCK = os.path.join(BASE, "tools", "statue-lock.json")
META = os.path.join(BASE, "_dev", "mate", "statue_asset_meta.json")
RENDER = os.path.join(BASE, "_dev", "e2e", "render_1to1.png")

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


class Result:
    def __init__(self, name, state, detail, data=None):
        self.name, self.state, self.detail, self.data = name, state, detail, data or {}

    def line(self):
        return "[%s] %s：%s" % (self.state, self.name, self.detail)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_asset():
    if not os.path.exists(ASSET):
        return None
    img = cv2.imread(ASSET, cv2.IMREAD_UNCHANGED)
    if img is None or img.ndim != 3 or img.shape[2] != 4:
        return None
    return img


# ---------------- L1：资产 == 素材原像素（需素材原件） ----------------
def layer1(asset):
    if asset is None:
        return Result("L1 资产==素材原像素", FAIL, "成品资产缺失或不是 RGBA")
    if not os.path.exists(SRC_POSTER):
        return Result("L1 资产==素材原像素", SKIP,
                      "素材原件不在（素材/*.jpg 被 .gitignore 排除）——本层未取证，不等于通过")
    if not os.path.exists(META):
        return Result("L1 资产==素材原像素", SKIP, "缺少 _dev/mate/statue_asset_meta.json（无法定位裁切区）")
    meta = json.load(open(META, encoding="utf-8"))
    poster = cv2.imread(SRC_POSTER)
    x0, y0, x1, y1 = meta["bboxInSrc"]
    crop = poster[y0:y1 + 1, x0:x1 + 1]
    if crop.shape[:2] != asset.shape[:2]:
        return Result("L1 资产==素材原像素", FAIL,
                      "资产 %s 与素材裁切 %s 尺寸不一致" % (asset.shape[:2], crop.shape[:2]))
    # 只看内部：边缘 1px 羽化与 JPEG 振铃是抠图固有，不属于「不像」
    inner = cv2.erode((asset[:, :, 3] > 250).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if inner.sum() < 10000:
        return Result("L1 资产==素材原像素", FAIL, "内部像素仅 %d，判据不成立" % int(inner.sum()))
    d = np.abs(asset[:, :, :3].astype(np.int16) - crop[:, :, :3].astype(np.int16)).max(axis=2)[inner]
    stat = {"pixels": int(inner.sum()), "identical": float((d == 0).mean() * 100),
            "mean": float(d.mean()), "max": int(d.max())}
    if d.max() == 0:
        return Result("L1 资产==素材原像素", PASS,
                      "%d 像素逐点相等，PSNR ∞" % stat["pixels"], stat)
    return Result("L1 资产==素材原像素", FAIL,
                  "%d 像素，完全相同 %.2f%%，最大误差 %d" % (stat["pixels"], stat["identical"], stat["max"]), stat)


# ---------------- L1'：资产 SHA256 == 提交锁值（CI 可跑） ----------------
def layer1_lock():
    if not os.path.exists(ASSET):
        return Result("L1' 资产未漂移（SHA256 锁）", FAIL, "成品资产缺失")
    if not os.path.exists(LOCK):
        return Result("L1' 资产未漂移（SHA256 锁）", FAIL,
                      "缺少 tools/statue-lock.json —— 无锁则资产被换掉也无人知")
    lock = json.load(open(LOCK, encoding="utf-8"))
    got = sha256_of(ASSET)
    want = lock.get("sha256", "")
    stat = {"sha256": got, "locked": want}
    if got == want:
        return Result("L1' 资产未漂移（SHA256 锁）", PASS, got[:16] + "…", stat)
    return Result("L1' 资产未漂移（SHA256 锁）", FAIL,
                  "资产被改动（%s… ≠ 锁 %s…）；若确属有意更新，跑 tools/build_statue_asset.py 重出锁"
                  % (got[:12], want[:12]), stat)


# ---------------- L2：无损编码 ----------------
def webp_chunks(path, limit=8):
    """读 WebP 的 RIFF chunk 列表（只读文件头，不解码）。

    WebP 的编码类型在比特流里是确定性的，比「体积比」这种间接判据可靠得多：
      无损          顶层 chunk = VP8L，文件里没有 ALPH / VP8；
      有损（带 alpha）顶层 chunk = VP8X（扩展头）+ ALPH（alpha 平面）+ VP8（RGB）
      有损（不带 alpha）顶层 chunk = VP8
    一手教训：v1 用「当前体积 / 无损重编码体积 ≥95%」判定无损，
    而实际文件是 Pillow 编的、重编码用的是 OpenCV，两者压缩率不同 ⇒ 真无损也只到 96.5%，
    余量只剩 1.5 个点；换成别的编码器就可能误伤成红。判据要打在最直接的证据上。
    """
    with open(path, "rb") as f:
        head = f.read(4096)
    if head[:4] != b"RIFF" or head[8:12] != b"WEBP":
        return None
    out = []
    i = 12
    while i + 8 <= len(head) and len(out) < limit:
        name = head[i:i + 4]
        if not all(32 <= c < 127 for c in name):
            break
        size = int.from_bytes(head[i + 4:i + 8], "little")
        out.append((name.decode("ascii", "replace"), size))
        i += 8 + size + (size & 1)
    return out


def layer2(asset):
    if asset is None:
        return Result("L2 编码无损", FAIL, "成品资产缺失")
    size = os.path.getsize(ASSET)
    chunks = webp_chunks(ASSET)
    if chunks is None:
        return Result("L2 编码无损", FAIL, "不是合法 WebP（RIFF/WEBP 头不符）")
    names = [c[0] for c in chunks]
    stat = {"bytes": size, "chunks": names}
    # 无损的硬标志：顶层就是 VP8L；出现 VP8X/ALPH/VP8 任一即有损
    if names and names[0] == "VP8L" and "ALPH" not in names and "VP8 " not in names:
        return Result("L2 编码无损", PASS, "%d B，chunk=VP8L（无损）" % size, stat)
    return Result("L2 编码无损", FAIL,
                  "%d B，chunk=%s ⇒ 有损编码" % (size, "/".join(names)), stat)


# ---------------- L3：剖面绑定 ----------------
def layer3(asset):
    if not os.path.exists(PROFILE):
        return Result("L3 剖面绑定", FAIL, "缺少 site/assets/data/statue-profile.js")
    txt = open(PROFILE, encoding="utf-8").read()
    miss = [k for k in ("left:", "right:", "halfWidth:", "axis:", "aspect:") if k not in txt]
    if miss:
        return Result("L3 剖面绑定", FAIL, "剖面缺字段 " + ", ".join(miss))
    if "statue-cut.webp" not in txt:
        return Result("L3 剖面绑定", FAIL, "剖面未绑定成品资产（引擎会回退手写几何）")
    import re
    try:
        # 两条正则必须同形，且 DOTALL：剖面是单行 JSON，元素形如 [0.02797,0.073649]
        left = json.loads(re.search(r"left:\s*(\[\[.*?\]\])", txt, re.S).group(1))
        right = json.loads(re.search(r"right:\s*(\[\[.*?\]\])", txt, re.S).group(1))
    except Exception as e:
        return Result("L3 剖面绑定", FAIL, "剖面解析失败 %s" % e)
    if asset is not None:
        if ("w: %d" % asset.shape[1]) not in txt or ("h: %d" % asset.shape[0]) not in txt:
            return Result("L3 剖面绑定", FAIL, "剖面尺寸与资产(%dx%d)不一致" % (asset.shape[1], asset.shape[0]))
    ml, mr = max(v for _, v in left), max(v for _, v in right)
    asym = abs(ml - mr) / max(ml, mr) * 100
    stat = {"points": len(left), "leftMax": round(ml, 4), "rightMax": round(mr, 4),
            "asymmetry": round(asym, 2)}
    if asym <= 0.5:
        return Result("L3 剖面绑定", FAIL,
                      "左右几乎对称（%.2f%%）—— 造像非镜像体，轮廓会画歪" % asym, stat)
    return Result("L3 剖面绑定", PASS,
                  "%d 点，左 %.4f / 右 %.4f（不对称 %.2f%%）" % (len(left), ml, mr, asym), stat)


# ---------------- L4：1:1 渲染（需浏览器取证） ----------------
def layer4(asset):
    if asset is None:
        return Result("L4 1:1 渲染", FAIL, "成品资产缺失")
    if not os.path.exists(RENDER):
        return Result("L4 1:1 渲染", SKIP,
                      "缺少 _dev/e2e/render_1to1.png（先跑 tools/render_1to1.py）——本层未取证")
    got = cv2.imread(RENDER, cv2.IMREAD_UNCHANGED)
    if got is None:
        return Result("L4 1:1 渲染", FAIL, "渲染图读取失败")
    if got.shape[:2] != asset.shape[:2]:
        return Result("L4 1:1 渲染", FAIL,
                      "渲染 %s ≠ 资产 %s（未走 1:1 通路）" % (got.shape[:2], asset.shape[:2]))
    vis = (asset[:, :, 3] > 250) & (got[:, :, 3] > 250)
    d = np.abs(asset[:, :, :3].astype(np.int16) - got[:, :, :3].astype(np.int16)).max(axis=2)[vis]
    stat = {"pixels": int(vis.sum()), "identical": float((d == 0).mean() * 100),
            "mean": float(d.mean()), "max": int(d.max())}
    if d.max() == 0:
        return Result("L4 1:1 渲染", PASS, "%d 像素逐点相等" % stat["pixels"], stat)
    return Result("L4 1:1 渲染", FAIL,
                  "%d 像素，完全相同 %.2f%%，最大误差 %d" % (stat["pixels"], stat["identical"], stat["max"]), stat)


# ---------------- L4'：引擎静态通路（CI 可跑） ----------------
def layer4_static():
    if not os.path.exists(ENGINE):
        return Result("L4' 引擎 1:1 通路", FAIL, "引擎文件缺失")
    t = open(ENGINE, encoding="utf-8").read()
    need = {
        "revealStatue": "成品揭示函数",
        "drawImage": "真正贴图",
        "imageGeom": "几何换算",
        "STATUE_PROFILE": "读取剖面",
        "takeover": "接管权重（矢量段退场）",
    }
    miss = [v for k, v in need.items() if k not in t]
    if miss:
        return Result("L4' 引擎 1:1 通路", FAIL, "缺少 " + "、".join(miss))
    # 整像素对齐：半像素落点会让整张图二次重采样（实测把误差从 0.02 抬到 6.40）
    if not all(s in t for s in ("Math.round(box.cx", "Math.round(box.cy", "Math.round(iw)", "Math.round(ih)")):
        return Result("L4' 引擎 1:1 通路", FAIL, "imageGeom 未做整像素对齐（会二次重采样）")
    if "imageSmoothingQuality = 'high'" not in t:
        return Result("L4' 引擎 1:1 通路", FAIL, "drawImage 未设高质量重采样")
    # 浮尘必须画在成品之前（画在之后会落金点污染像身像素）
    i_mote = t.rfind("motes(ctx")
    i_rev = t.rfind("revealStatue(ctx")
    if not (0 <= i_mote < i_rev):
        return Result("L4' 引擎 1:1 通路", FAIL, "浮尘层在成品之后（会污染像身像素）")
    return Result("L4' 引擎 1:1 通路", PASS, "揭示层 / 整像素对齐 / high 重采样 / 浮尘在前")


def write_lock(asset):
    """生成/刷新资产锁。只在 build_statue_asset.py 重出资产后调用。"""
    data = {
        "asset": "site/assets/img/statue-cut.webp",
        "sha256": sha256_of(ASSET),
        "bytes": os.path.getsize(ASSET),
        "size": [int(asset.shape[1]), int(asset.shape[0])],
        "note": "此锁证明「资产自上次本地逐像素核验以来未被改动」；不等于「资产等于素材」，后者需素材原件在本地复验。",
    }
    with open(LOCK, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-full", action="store_true", help="L1/L4 缺件即 FAIL（本地发布前用）")
    ap.add_argument("--write-lock", action="store_true", help="重出资产锁")
    args = ap.parse_args()

    asset = load_asset()
    if args.write_lock:
        if asset is None:
            print("资产缺失，无法建锁", file=sys.stderr)
            return 2
        d = write_lock(asset)
        print("锁已写: tools/statue-lock.json  sha256=%s  %d B" % (d["sha256"][:16] + "…", d["bytes"]))
        return 0

    results = [layer1(asset), layer1_lock(), layer2(asset), layer3(asset),
               layer4(asset), layer4_static()]

    if args.require_full:
        for r in results:
            if r.state == SKIP:
                r.state = FAIL
                r.detail += "（--require-full：缺件视为未达标）"

    if args.json:
        print(json.dumps({"pass": not any(r.state == FAIL for r in results),
                          "results": [{"name": r.name, "state": r.state,
                                       "detail": r.detail, "data": r.data} for r in results]},
                         ensure_ascii=False, indent=2, default=str))
    else:
        for r in results:
            print(r.line())
        fails = [r for r in results if r.state == FAIL]
        skips = [r for r in results if r.state == SKIP]
        print()
        if fails:
            print("RESULT: FAIL  %d 层未通过" % len(fails))
            for r in fails:
                print("  - %s：%s" % (r.name, r.detail))
            return 1
        if skips:
            print("RESULT: PASS（%d 层取证 / %d 层因缺件未取证：%s）"
                  % (len(results) - len(skips), len(skips), "、".join(r.name for r in skips)))
            return 0
        print("RESULT: PASS  四层判据全部成立（像素级一比一）")
    return 0 if not any(r.state == FAIL for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
