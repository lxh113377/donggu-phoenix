# -*- coding: utf-8 -*-
"""tools/orphan_asset_test.py —— 部署面资产对账（I-6，2026-10-20 轮50）。

## 为什么需要它（不是洁癖，是量化差距）
对标报告 §3.1 缺口 4 实测：站点 srcset=0、loading="lazy" 仅 1 处。
补 srcset 时扫出更严重的事实：site/ 里有一批位图从未被部署面任何文件引用
（merch-sketch / scene-interview-1 / scene-interview-2 / merch-badge / icon-180，
实测合计 322KB）。它们被 git 跟踪、计入体积预算、随 Pages 一起部署，
却一次也不会被浏览器请求 —— 这正是报告批评的「本地存在但未提交 ⇒ 线上 404」的
镜像问题：「已提交但无人引用 ⇒ 线上死重」。**判据必须在清退之前存在，否则清退无法被证明。**

## 三条判据
  1) 零孤儿：site/assets/img 下每个位图，必须被部署面文本（index.html / manifest /
     sw.js / assets/js|data|css 内文件）按整路径或文件名引用。
     例外：srcset 派生档（<名>-340.webp）由第 2 条校验，不算孤儿。
  2) srcset 可解析：12 件文创件件有 -340 档，且磁盘 + git 跟踪面都在
     （前端只看路径不看像素，漏一件就是线上 404）。
  3) 响应式基线成规模：srcset >= 1 处、loading=lazy >= 3 处，
     且 main.js 里保留候选名推导通路（-340.$1）。

聚合判定守 audit-runner-safe-aggregate 的规矩：任一子项 FAIL 即整体 FAIL，
零样本一律 SKIP（不把「没测到」洗成 PASS）。无 git 环境时跟踪面核对走 SKIP 提示。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_guard import verdict, emit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

SMALL_SUFFIX = "-340"
RASTER = (".webp", ".png", ".jpg", ".jpeg", ".gif")


def surface_files():
    out = ["index.html", "manifest.webmanifest", "sw.js"]
    for d in ("assets/js", "assets/data", "assets/css"):
        p = os.path.join(SITE, d.replace("/", os.sep))
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.endswith((".js", ".css")):
                    out.append(d + "/" + f)
    return out


def blob(files):
    parts = []
    for rel in files:
        p = os.path.join(SITE, rel.replace("/", os.sep))
        if os.path.exists(p):
            parts.append(open(p, encoding="utf-8", errors="ignore").read())
    return "\n".join(parts)


def git_tracked():
    """无 git 环境返回 None：调用方走 SKIP 提示，既不判红也不判绿。"""
    import subprocess
    try:
        r = subprocess.run(["git", "-C", BASE, "ls-files", "-z"],
                           capture_output=True, timeout=30)
        if r.returncode != 0:
            return None
        return set(x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x)
    except Exception:
        return None


def raster_rows():
    root = os.path.join(SITE, "assets", "img")
    rows = []
    for r, _, fs_ in os.walk(root):
        for f in fs_:
            if f.lower().endswith(RASTER):
                rows.append(os.path.relpath(os.path.join(r, f), SITE).replace(os.sep, "/"))
    return sorted(rows)


def main():
    files = surface_files()
    text = blob(files)
    tracked = git_tracked()
    fails = []
    checked = 0

    rows = raster_rows()
    derived = [r for r in rows if SMALL_SUFFIX in os.path.splitext(r)[0]]

    # 1) 零孤儿
    for rel in rows:
        if rel in derived:
            continue
        checked += 1
        if rel not in text and os.path.basename(rel) not in text:
            kb = os.path.getsize(os.path.join(SITE, rel.replace("/", os.sep))) / 1024
            fails.append("孤儿资产（部署面零引用）: %s（%.0fKB）" % (rel, kb))

    # 2) srcset 可解析：12 件件件有档，且都在磁盘与 git 跟踪面
    culture_p = os.path.join(SITE, "assets", "data", "culture.js")
    cul = open(culture_p, encoding="utf-8").read() if os.path.exists(culture_p) else ""
    merch_imgs = re.findall(r"image: '([^']+\.(?:webp|png|jpg))'", cul)
    checked += 1
    if len(merch_imgs) < 12:
        fails.append("culture.js 文创 image 字段少于 12 件（实得 %d）" % len(merch_imgs))
    for rel in merch_imgs:
        root, ext = os.path.splitext(rel)
        for cand in (root + SMALL_SUFFIX + ext, rel):
            checked += 1
            if not os.path.exists(os.path.join(SITE, cand.replace("/", os.sep))):
                fails.append("srcset 候选档不存在（线上 404）: %s" % cand)
            elif tracked is not None and ("site/" + cand) not in tracked:
                fails.append("srcset 候选档未入版本控制（线上 404）: %s" % cand)

    # 3) 响应式基线成规模
    mj_p = os.path.join(SITE, "assets", "js", "main.js")
    mj = open(mj_p, encoding="utf-8").read() if os.path.exists(mj_p) else ""
    n_srcset = text.count("srcset=")
    n_lazy = text.count('loading="lazy"')
    checked += 1
    if n_srcset < 1:
        fails.append("全站 srcset 引用 0 处（响应式图片未落地）")
    checked += 1
    if n_lazy < 3:
        fails.append("全站 loading=lazy 仅 %d 处（懒加载未铺开）" % n_lazy)
    checked += 1
    # 候选名是前端用 replace() 拼出来的，必须与 SMALL_SUFFIX 约定一致；
    # 只查 "-340." 不够（注释里也有这三个字符），要查带引号的完整推导串。
    expect_derive = "'" + SMALL_SUFFIX + ".$1'"
    if expect_derive not in mj:
        fails.append("main.js 未见 srcset 候选名推导 %s（改坏即线上 404）" % expect_derive)

    print("部署面文本 %d 文件；位图 %d 个（其中 srcset 派生档 %d）；文创 %d 件" % (
        len(files), len(rows), len(derived), len(merch_imgs)))
    print("srcset 引用 %d 处 / loading=lazy %d 处" % (n_srcset, n_lazy))
    if tracked is None:
        print("提示：无 git 环境，跟踪面核对跳过（未取证不等于通过）")
    for f in fails[:14]:
        print("  - " + f)
    code, msg = verdict(checked=checked, fails=fails, what="资产对账项")
    return emit(code, msg)


if __name__ == "__main__":
    sys.exit(main())
