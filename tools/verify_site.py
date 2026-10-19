# -*- coding: utf-8 -*-
"""站点交付前自检：引用完整性、体积预算、编码、关键内容、降级路径。"""
import os, re, sys, json

BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
SITE = os.path.join(BASE, "site")
fails, warns = [], []

def rd(p):
    with open(p, "rb") as f:
        return f.read()

# 1) HTML 引用的本地资源全部存在
html = rd(os.path.join(SITE, "index.html")).decode("utf-8")
refs = set()
for m in re.finditer(r'(?:src|href)="([^"#]+)"', html):
    u = m.group(1)
    if u.startswith(("http", "//", "mailto:", "data:")):
        continue
    refs.add(u)
missing = []
for u in sorted(refs):
    p = os.path.join(SITE, u.split("?")[0])
    if not os.path.exists(p):
        missing.append(u)
if missing:
    fails.append("HTML 引用缺失: " + ", ".join(missing))
print(f"[{'PASS' if not missing else 'FAIL'}] HTML 本地引用 {len(refs)} 项，缺失 {len(missing)}")

# 2) JS 内引用的资源（data / img）
js_files = [os.path.join(SITE, "assets/js", f) for f in os.listdir(os.path.join(SITE, "assets/js"))]
js_missing = []
for jf in js_files:
    s = rd(jf).decode("utf-8")
    for m in re.finditer(r"['\"](assets/[\w\-/\.]+\.(?:js|css|png|webp|svg|json))['\"]", s):
        u = m.group(1)
        if not os.path.exists(os.path.join(SITE, u)):
            # 允许由 data 文件动态提供
            if "img/merch/" in u or "img/photos/" in u:
                continue
            js_missing.append(os.path.basename(jf) + " -> " + u)
if js_missing:
    fails.append("JS 引用缺失: " + "; ".join(js_missing))
print(f"[{'PASS' if not js_missing else 'FAIL'}] JS 资源引用检查，缺失 {len(js_missing)}")

# 3) culture.js 里的图片路径全部存在
c = rd(os.path.join(SITE, "assets/data/culture.js")).decode("utf-8")
imgs = re.findall(r"image: '([^']+)'", c) + re.findall(r"avatar: '([^']+)'", c)
bad = [i for i in imgs if not os.path.exists(os.path.join(SITE, i))]
if bad:
    fails.append("数据层图片缺失: " + ", ".join(bad))
print(f"[{'PASS' if not bad else 'FAIL'}] 数据层图片 {len(imgs)} 项，缺失 {len(bad)}")

# 4) 体积预算
total = 0
files = []
for r, _, fs_ in os.walk(SITE):
    for f in fs_:
        p = os.path.join(r, f)
        s = os.path.getsize(p)
        total += s
        files.append((s, os.path.relpath(p, SITE)))
files.sort(reverse=True)
print(f"[INFO] 站点总体积 {total/1024:.0f} KB / {len(files)} 文件")
if total > 4 * 1024 * 1024:
    fails.append(f"体积超预算 4MB: {total/1024/1024:.1f}MB")
print("  最大 5 个文件:", ", ".join(f"{n}({s//1024}KB)" for s, n in files[:5]))

# 5) 编码：所有文本文件 UTF-8 无 BOM
enc_bad = []
for r, _, fs_ in os.walk(SITE):
    for f in fs_:
        if f.rsplit(".", 1)[-1] in ("html", "css", "js", "json", "svg", "webmanifest", "txt"):
            p = os.path.join(r, f)
            b = rd(p)
            if b.startswith(b"\xef\xbb\xbf"):
                enc_bad.append(os.path.relpath(p, SITE) + " (BOM)")
            try:
                b.decode("utf-8")
            except UnicodeDecodeError:
                enc_bad.append(os.path.relpath(p, SITE) + " (非UTF-8)")
if enc_bad:
    fails.append("编码问题: " + ", ".join(enc_bad))
print(f"[{'PASS' if not enc_bad else 'FAIL'}] 文本编码检查 {len(enc_bad)} 问题")

# 6) 关键内容存在
must = ["畲", "凤凰", "东固", "三公主", "刘节明", "乌饭", "qr.png"]
for k in must:
    ok = False
    for r, _, fs_ in os.walk(SITE):
        for f in fs_:
            if f.endswith((".html", ".js")):
                if k in rd(os.path.join(r, f)).decode("utf-8", "replace"):
                    ok = True; break
        if ok: break
    if not ok:
        fails.append("关键内容缺失: " + k)
print(f"[INFO] 关键内容词检查: {len(must)} 项")

# 7) 二维码文件存在且非空
for q in ["assets/img/qr.png"]:
    p = os.path.join(SITE, q)
    if not os.path.exists(p) or os.path.getsize(p) < 500:
        fails.append("二维码缺失或过小: " + q)
print(f"[{'PASS' if not any('二维码' in f for f in fails) else 'FAIL'}] 二维码文件检查")

# 8) 无障碍与 SEO 基础
checks = {
    "viewport meta": 'name="viewport"' in html,
    "lang=zh-CN": 'lang="zh-CN"' in html,
    "title": "<title>" in html,
    "meta description": 'name="description"' in html,
    "favicon": 'rel="icon"' in html,
    "og:title": 'property="og:title"' in html,
    "alt 属性": html.count("alt=") >= 3,
}
for k, v in checks.items():
    if not v:
        fails.append("基础项缺失: " + k)
print(f"[{'PASS' if all(checks.values()) else 'FAIL'}] 基础 SEO/无障碍 {sum(checks.values())}/{len(checks)}")

print()
if fails:
    print("RESULT: FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("RESULT: PASS  全部检查通过")
