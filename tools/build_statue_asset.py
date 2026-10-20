
# -*- coding: utf-8 -*-
"""build_statue_asset.py — 从宣传海报抠出「东固传统造像」成品（RGBA），供像素级复刻。

存在的问题（本版修的）：
  v1 用 GrabCut + 「距离变换 7px 定确定前景」，把造像身上的暗部衣褶判成了背景 ——
  成品图上出现几十个绿洞（衣褶暗沟 b* 144~147，超出像身阈值）。一刀切的阈值法在
  「白像身 + 暗衣褶」这类高动态对象上必然漏，因为暗部与木墙在 L 上重叠。

本版思路：先「闭合」把暗沟桥接成实心，再只填「被前景完全包住的孔」（真镂空不填），
最后用 GrabCut 在 trimap 上修边界（它的颜色模型能把左侧光柱这类木色区域剔掉）。

步骤：
  1) LAB 阈值取候选（像身中性白 b* 低 / 莲座偏暖在底座带放宽）；
  2) 闭运算 K=21 桥接暗沟 → 面积+位置筛连通域 → 只填「不连通边界」的封闭孔；
  3) 由实心掩膜生成 trimap（腐蚀=确定前景 / 膨胀外=确定背景 / 之间未知）；
  4) GrabCut 细化边界（剔除光柱等木色泄漏，保留真镂空）；
  5) 引导滤波 + 1px 保边羽化；
  6) 输出 WebP RGBA + 由 alpha 反解的左右不对称轮廓剖面 statue-profile.js。

产物：
  site/assets/img/statue-cut.webp       成品（像素级复刻的唯一真源）
  site/assets/data/statue-profile.js    轮廓剖面（引擎矢量段与成品共用，防轮廓跳变）
  _dev/mate/*.png                        每一步中间件（可复核）
"""
import os
import json
import numpy as np
import cv2

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "素材", "597fa4848ad5fdef17da516d62a85099.jpg")
DEV = os.path.join(BASE, "_dev", "mate")
OUT_IMG = os.path.join(BASE, "site", "assets", "img", "statue-cut.webp")
OUT_PROFILE = os.path.join(BASE, "site", "assets", "data", "statue-profile.js")
os.makedirs(DEV, exist_ok=True)

# 海报里造像所在的中带（标题/水印/边框外一律不作为前景）
Y_TOP, Y_BOT = 0.145, 0.985
X_LEFT, X_RIGHT = 0.11, 0.89


def fill_enclosed(mask):
    """只填「被前景完全包住」的孔；与边界连通的区域一律不填（那是真镂空/背景）。"""
    H, W = mask.shape
    ff = mask.copy()
    mk = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(ff, mk, (0, 0), 2)
    holes = (ff == 0).astype(np.uint8)
    return ((mask > 0) | (holes > 0)).astype(np.uint8)


def main():
    im = cv2.imread(SRC)
    if im is None:
        raise SystemExit("找不到参考件: " + SRC)
    H, W = im.shape[:2]

    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, B = lab[:, :, 0], lab[:, :, 2]

    # --- 1) 候选：像身用严阈值定「中轴与体宽」，莲座再按这个范围放宽 ---
    #   一手教训：莲座带（y 0.78~0.97）放宽到 b*<152 & L>55 时，把底部整条木墙亮带
    #   一起吃进来，连通块 bbox 宽达 795px（比像身还宽一倍），中轴偏到 0.63。
    #   故先用像身块定横向范围，再在该范围内收莲座。
    body = ((B < 144) & (L > 110)).astype(np.uint8)
    body[:int(H * Y_TOP)] = 0
    body[int(H * Y_BOT):] = 0
    body[:, :int(W * X_LEFT)] = 0
    body[:, int(W * X_RIGHT):] = 0
    body = cv2.morphologyEx(body, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    nb, lb, sb, cb = cv2.connectedComponentsWithStats(body, 8)
    if nb < 2:
        raise SystemExit("像身候选为空")
    body_id = 1 + int(np.argmax(sb[1:, 4]))
    body_cx = float(cb[body_id][0])
    body_w = float(sb[body_id, 2])
    print("像身块 id=%d 宽=%d 中轴=%.0f" % (body_id, int(body_w), body_cx))

    # 莲座只在「像身中轴 ± 0.72 体宽」内收；这条带同时覆盖莲瓣外张与头顶侧化佛
    half_span = 0.72 * body_w
    xa, xb = int(max(0, body_cx - half_span)), int(min(W, body_cx + half_span))
    y_a, y_b = int(H * 0.78), int(H * 0.97)
    lotus_narrow = ((B < 152) & (L > 55)).astype(np.uint8)
    band_mask = np.zeros((H, W), np.uint8)
    band_mask[y_a:y_b, xa:xb] = 1
    cand = body.copy()
    cand[(band_mask > 0) & (lotus_narrow > 0)] = 1
    print("莲座带 x=[%d,%d] y=[%d,%d]" % (xa, xb, y_a, y_b))

    # --- 2) 先「筛连通域」再「闭运算」：顺序反了会把左侧光柱闭合粘连进来 ---
    #   一手教训：先在 cand 上做 K=21 闭运算再筛连通域，光柱与造像被桥接成一块，
    #   成品 bbox 从 563 宽涨到 783 宽、中轴偏到 0.63 —— 抠出来的像是歪的。
    #   正确顺序：候选 → 筛「像身/莲座/莲台底沿」三块 → 对保留块做闭运算桥接暗沟
    #   → 只填被包住的孔。光柱从来不在保留块里，闭运算也就不会把它收进来。
    n, lbl, st, cen = cv2.connectedComponentsWithStats(cand, 8)
    keep = [i for i in range(1, n) if st[i, 4] >= 2000 and 0.25 * W <= cen[i][0] <= 0.75 * W]
    if not keep:
        raise SystemExit("没有任何连通块满足面积/位置判据")
    keep.sort(key=lambda i: -st[i, 4])
    print("保留连通块:", [(i, int(st[i, 4])) for i in keep])
    parts = np.isin(lbl, keep).astype(np.uint8)

    # 只对「每个保留块自己的外接区域」做闭运算，进一步限制它向木墙扩张
    K = 21
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (K, K))
    closed = np.zeros_like(parts)
    for i in keep:
        x, y, ww, hh, _ = st[i]
        pad = K
        xa, ya = max(0, x - pad), max(0, y - pad)
        xb, yb = min(W, x + ww + pad), min(H, y + hh + pad)
        sub = parts[ya:yb, xa:xb]
        sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, kernel)
        closed[ya:yb, xa:xb] = np.maximum(closed[ya:yb, xa:xb], sub)
    solid = fill_enclosed(closed)
    ys, xs = np.where(solid > 0)
    print("实心掩膜 bbox (%d,%d,%d,%d) %dx%d area=%d"
          % (xs.min(), ys.min(), xs.max(), ys.max(),
             xs.max() - xs.min() + 1, ys.max() - ys.min() + 1, int(solid.sum())))
    cv2.imwrite(os.path.join(DEV, "step0_solid.png"), solid * 255)

    # --- 3) trimap ---
    sure_fg = cv2.erode(solid, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    near = cv2.dilate(solid, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    sure_bg = ((solid == 0) & (near == 0)).astype(np.uint8)
    sure_bg[:int(H * Y_TOP)] = 1          # 标题金字绝不作为前景
    sure_bg[:, :int(W * 0.05)] = 1
    sure_bg[:, int(W * 0.95):] = 1

    trimap = np.full((H, W), cv2.GC_PR_BGD, np.uint8)
    trimap[solid > 0] = cv2.GC_PR_FGD
    trimap[sure_fg > 0] = cv2.GC_FGD
    trimap[sure_bg > 0] = cv2.GC_BGD
    cv2.imwrite(os.path.join(DEV, "step1_trimap.png"), (trimap * 40).astype(np.uint8))

    # --- 4) GrabCut：颜色模型负责剔掉木色光柱；内部暗褶在确定前景内，不会被挖掉 ---
    gc = trimap.copy()
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(im, gc, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    fg = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # 去孤片 + 重新填封闭孔（GrabCut 可能在暗部啃出小洞）
    n2, lbl2, st2, cen2 = cv2.connectedComponentsWithStats((fg > 0).astype(np.uint8), 8)
    if n2 < 2:
        raise SystemExit("GrabCut 没有产出前景")
    keep2 = [i for i in range(1, n2)
             if st2[i, 4] >= 1500 and 0.25 * W <= cen2[i][0] <= 0.75 * W]
    if not keep2:
        raise SystemExit("GrabCut 结果无合格连通块")
    fg = np.isin(lbl2, keep2).astype(np.uint8)
    fg = fill_enclosed(fg)
    # 与 solid 求交：GrabCut 不该凭空长出 solid 之外的东西
    fg = ((fg > 0) & (near > 0)).astype(np.uint8)
    fg = fill_enclosed(fg)
    print("GrabCut 前景像素", int(fg.sum()))

    # --- 4b) 去「木色残留」：莲座带里混进的木地板与背景山体是暖褐色（b* 高），
    #   造像是中性米白。GrabCut 偶有漏网，这里按颜色再剔一遍，只作用于边缘带（不伤内部暗褶：
    #   内部像素周围全是米白，其 b* 已被前面的闭运算+填洞保护）。
    lab2 = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    B2 = lab2[:, :, 2]
    L2 = lab2[:, :, 0]
    brown = ((B2 > 150) & (L2 < 150)).astype(np.uint8)
    brown = cv2.dilate(brown, np.ones((3, 3), np.uint8))
    fg = ((fg > 0) & (brown == 0)).astype(np.uint8)
    fg = fill_enclosed(fg)
    print("去木色后前景像素", int(fg.sum()))

    # --- 5) alpha：引导滤波定边，再做 1px 保边羽化 ---
    guide = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    alpha = guided_filter(guide, fg.astype(np.float32), 8, 1e-4)
    hard = (alpha > 0.5).astype(np.uint8) * 255
    hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    soft = cv2.GaussianBlur(hard.astype(np.float32) / 255.0, (0, 0), 1.0)
    inner = cv2.erode(hard, np.ones((3, 3), np.uint8))
    outer = cv2.dilate(hard, np.ones((3, 3), np.uint8))
    alpha = np.where(inner > 0, 1.0, np.where(outer == 0, 0.0, soft)).astype(np.float32)

    ys, xs = np.where(hard > 0)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    print("成品 bbox (%d,%d,%d,%d) %dx%d" % (x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1))

    rgba = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = (alpha * 255.0 + 0.5).astype(np.uint8)
    crop = rgba[y0:y1 + 1, x0:x1 + 1].copy()
    cv2.imwrite(os.path.join(DEV, "step2_rgba.png"), crop)

    # --- 6) 输出 WebP ---
    os.makedirs(os.path.dirname(OUT_IMG), exist_ok=True)
    if not cv2.imwrite(OUT_IMG, crop, [int(cv2.IMWRITE_WEBP_QUALITY), 90]):
        raise SystemExit("WebP 写入失败: " + OUT_IMG)
    size = os.path.getsize(OUT_IMG)
    cov = float((crop[:, :, 3] > 127).sum()) / float(crop.shape[0] * crop.shape[1])

    # 回读校验：写盘后 alpha 必须与内存一致（有损 WebP 会破坏 alpha 的假设在这里被证伪/证实）
    back = cv2.imread(OUT_IMG, cv2.IMREAD_UNCHANGED)
    if back is None or back.shape[2] != 4:
        raise SystemExit("回读失败或丢 alpha 通道")
    a_diff = int(np.abs(back[:, :, 3].astype(np.int16) - crop[:, :, 3].astype(np.int16)).max())
    print("alpha 回读最大偏差 %d（0=无损）" % a_diff)

    meta = {
        "src": os.path.relpath(SRC, BASE).replace("\\", "/"),
        "out": os.path.relpath(OUT_IMG, BASE).replace("\\", "/"),
        "srcSize": [W, H],
        "outSize": [int(crop.shape[1]), int(crop.shape[0])],
        "bboxInSrc": [x0, y0, x1, y1],
        "bytes": size,
        "alphaCoverage": round(cov, 4),
        "alphaMaxDiffAfterEncode": a_diff,
    }
    with open(os.path.join(DEV, "statue_asset_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("输出", OUT_IMG, size, "B", "alpha 覆盖 %.3f" % cov)

    if cov < 0.35:
        raise SystemExit("alpha 覆盖率过低(%.3f)，抠图失败" % cov)
    if size < 20000:
        raise SystemExit("输出体积异常(%d B)" % size)
    if a_diff > 2:
        raise SystemExit("编码后 alpha 偏差过大(%d)，成品会有前色透出" % a_diff)

    write_profile(crop)


def write_profile(crop):
    """由 alpha 反解「左右不对称」轮廓剖面，供 wood-to-statue.js 与成品图共用。

    引擎几何：u=0 冠顶 → u=1 莲座底，y = cy + (TOP + u*SPAN)*s。
    半宽以引擎尺度 s 为单位 = (像素距离 / 图高) * SPAN。
    """
    SPAN = 1.02
    h_img, w_img = crop.shape[0], crop.shape[1]

    rows = []
    for y in range(h_img):
        xs = np.where(crop[y, :, 3] > 127)[0]
        if len(xs) == 0:
            continue
        rows.append((y, int(xs.min()), int(xs.max())))
    if len(rows) < h_img * 0.5:
        raise SystemExit("alpha 有效行过少(%d/%d)，剖面不可信" % (len(rows), h_img))

    axis_px = float(np.median([(a + b) / 2.0 for _, a, b in rows]))
    print("中轴 x = %.1f px（图宽 %d）" % (axis_px, w_img))

    left, right, total = [], [], []
    prevL = prevR = 0.0
    for y, a, b in rows:
        hl = (axis_px - a) / float(h_img) * SPAN
        hr = (b - axis_px) / float(h_img) * SPAN
        hl = max(prevL * 0.86, min(prevL * 1.14, hl)) if prevL > 0 else hl
        hr = max(prevR * 0.86, min(prevR * 1.14, hr)) if prevR > 0 else hr
        prevL, prevR = hl, hr
        u = round(y / float(h_img - 1), 5)
        left.append((u, round(hl, 6)))
        right.append((u, round(hr, 6)))
        total.append((u, round((hl + hr) / 2.0, 6)))

    def thin(tbl, n=140):
        step = max(1, len(tbl) // n)
        out = tbl[::step]
        if out[-1] != tbl[-1]:
            out.append(tbl[-1])
        return out

    left, right, total = thin(left), thin(right), thin(total)
    landmarks = {"crown": 0.0, "face": 0.10, "shoulder": 0.22, "waist": 0.55,
                 "seat": 0.78, "feet": 0.83, "lotusBottom": 1.0}

    lines = [
        "/* statue-profile.js — 由 tools/build_statue_asset.py 从参考成品 alpha 反解生成，请勿手改。",
        " * 数据源：素材/597fa4848ad5fdef17da516d62a85099.jpg 抠出的 site/assets/img/statue-cut.webp。",
        " * u = 0 冠顶 → 1 莲座底；左右半宽各自独立（造像非镜像体），单位 = 引擎尺度 s。",
        " * 引擎的矢量雕刻与栅格成品共用这一份剖面 + 同一个中轴，两处轮廓严格同源。 */",
        "(function (global) {",
        "  'use strict';",
        "  global.STATUE_PROFILE = {",
        "    left: " + json.dumps(left, separators=(",", ":")) + ",",
        "    right: " + json.dumps(right, separators=(",", ":")) + ",",
        "    halfWidth: " + json.dumps(total, separators=(",", ":")) + ",",
        "    span: " + repr(SPAN) + ",",
        "    axis: " + repr(round(axis_px / float(w_img), 6)) + ",",
        "    image: {",
        "      src: 'assets/img/statue-cut.webp',",
        "      w: " + str(w_img) + ",",
        "      h: " + str(h_img) + ",",
        "      aspect: " + repr(round(w_img / float(h_img), 6)) + "",
        "    },",
        "    landmarks: " + json.dumps(landmarks, ensure_ascii=False) + ",",
        "  };",
        "})(window);",
        "",
    ]
    with open(OUT_PROFILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("剖面已写", os.path.relpath(OUT_PROFILE, BASE), "点数", len(left),
          "中轴占比 %.4f" % (axis_px / w_img),
          "左最大 %.4f 右最大 %.4f" % (max(p[1] for p in left), max(p[1] for p in right)))


def guided_filter(guide_u8, src, radius, eps):
    """快速引导滤波（He et al. 简化版）。"""
    g = guide_u8.astype(np.float32) / 255.0
    mean_I = cv2.boxFilter(g, -1, (radius, radius))
    mean_p = cv2.boxFilter(src, -1, (radius, radius))
    mean_Ip = cv2.boxFilter(g * src, -1, (radius, radius))
    cov_Ip = mean_Ip - mean_I * mean_p
    mean_II = cv2.boxFilter(g * g, -1, (radius, radius))
    var_I = mean_II - mean_I * mean_I
    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I
    return cv2.boxFilter(a, -1, (radius, radius)) * g + cv2.boxFilter(b, -1, (radius, radius))


if __name__ == "__main__":
    main()
