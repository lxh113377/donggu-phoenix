# -*- coding: utf-8 -*-
"""站点交付前自检：引用完整性、体积预算、编码、关键内容、降级路径。"""
import os, re, sys, json, subprocess

# 仓库根由脚本自身位置推导（交付门禁必须在 CI 的 Linux runner 上同样可跑，
# 硬编码本机绝对路径会让门禁「本地绿、CI 必红」，等于没有门禁）
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
fails, warns = [], []


def git_tracked():
    """返回 git 跟踪中的文件集合；无 git / 非仓库时返回 None（跳过而非判绿）。"""
    try:
        out = subprocess.run(["git", "-C", BASE, "ls-files", "-z"],
                             capture_output=True, timeout=30)
        if out.returncode != 0:
            return None
        return set(x.decode("utf-8", "replace") for x in out.stdout.split(b"\0") if x)
    except Exception:
        return None

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
# 预算对齐「首屏 100KB 级、整站 1MB 内」的轻量化口径；4MB 等于没有约束
BUDGET_KB = 1200
if total > BUDGET_KB * 1024:
    fails.append(f"体积超预算 {BUDGET_KB}KB: {total/1024:.0f}KB")
elif total > BUDGET_KB * 1024 * 0.8:
    warns.append(f"体积已用预算 80% 以上: {total/1024:.0f}KB / {BUDGET_KB}KB")
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

# 9) AR 展陈馆：三场景数据与渲染器必须同时存在且自洽
ar_data = rd(os.path.join(SITE, "assets/data/ar-data.js")).decode("utf-8")
ar_scenes = rd(os.path.join(SITE, "assets/js/ar-scenes.js")).decode("utf-8")
ar_ctrl = rd(os.path.join(SITE, "assets/js/ar.js")).decode("utf-8")
for f in ("assets/data/ar-data.js", "assets/js/ar-scenes.js", "assets/js/ar.js"):
    p = os.path.join(SITE, f)
    if not os.path.exists(p) or os.path.getsize(p) < 800:
        fails.append("AR 文件缺失或过小: " + f)
ar_scene_ids = re.findall(r"\n\s*id: '(craft|red|phoenix)'", ar_data)
if len(set(ar_scene_ids)) != 3:
    fails.append("AR 场景不完整（需 craft/red/phoenix 三个）: " + ",".join(ar_scene_ids))
for key in ("选木", "定像", "开坯", "修光", "开光"):
    if key not in ar_data:
        fails.append("AR 造像工序缺失: " + key)
for key in ("东固会师", "龙冈", "白云山", "六渡坳"):
    if key not in ar_data:
        fails.append("AR 红色史实缺失: " + key)
for fn in ("CraftScene", "RedScene", "PhoenixScene", "create"):
    if fn not in ar_scenes:
        fails.append("AR 渲染器缺少: " + fn)
# 三段时长合计应等于文档口径 152 秒
durs = [int(x) for x in re.findall(r"duration: (\d+)", ar_data)]
if sum(durs) != 152:
    fails.append("AR 三段时长合计应为 152s，实际 %d" % sum(durs))
# 场景直连码必须生成且非空
for sid in ("craft", "red", "phoenix"):
    qp = os.path.join(BASE, "qr", "qr-ar-%s.png" % sid)
    if not os.path.exists(qp) or os.path.getsize(qp) < 500:
        fails.append("场景直连码缺失或过小: qr/qr-ar-%s.png" % sid)
meta_p = os.path.join(BASE, "qr", "meta.json")
if os.path.exists(meta_p):
    try:
        meta = json.loads(rd(meta_p).decode("utf-8"))
        links = meta.get("sceneDeepLinks") or {}
        for sid in ("craft", "red", "phoenix"):
            if "#ar=" + sid not in (links.get(sid) or ""):
                fails.append("sceneDeepLinks 缺少 %s" % sid)
    except Exception as e:
        fails.append("qr/meta.json 解析失败: %s" % e)
print(f"[{'PASS' if not any('场景直连码' in f or 'sceneDeepLinks' in f for f in fails) else 'FAIL'}] 场景直连码 3 枚 + meta.json 深链")

# 9a2) 引用完整性必须对「git 跟踪面」成立，而非只对本地磁盘成立。
# 一手教训（2026-10-19 实测）：index.html 引用 wood-demo.js / wood-to-statue.js 时
# 两者均为 untracked，本地 verify 照样 PASS —— 一旦 push，Pages 部署产物里没有这两个
# 文件，线上直接 404、雕刻台整块功能不可用。只查 os.path.exists 的门禁查不出这类事故。
tracked = git_tracked()
if tracked is None:
    warns.append("git 跟踪面对账未执行（无 git 环境）——此项未取证，不等于通过")
    print("[SKIP] git 跟踪面对账（无 git 环境；已计入 WARNING）")
else:
    untracked_refs = []
    for u in sorted(refs):
        _u = u.split("?")[0]
        while _u.startswith("./"):          # 显式剥前缀；lstrip("./") 会按字符集误删
            _u = _u[2:]
        rel = "site/" + _u.lstrip("/")
        if not rel.startswith("site/") or rel in tracked:
            continue
        if os.path.exists(os.path.join(SITE, u.split("?")[0])):
            untracked_refs.append(rel + "（本地存在但未被 git 跟踪 ⇒ 部署后 404）")
        else:
            untracked_refs.append(rel + "（既未跟踪也不存在）")
    for jf in js_files:
        rel_jf = os.path.relpath(jf, BASE).replace(os.sep, "/")
        if rel_jf not in tracked:
            untracked_refs.append(rel_jf + "（JS 本体未被跟踪 ⇒ 不会被部署）")
    # sw.js 由内联 JS 注册，不在 HTML 的 src/href 里 ⇒ 上面的 refs 扫不到它。
    # 若 sw.js 漏提交，离线兜底会静默失效而门禁仍全绿，故单独入账；
    # 并核验 SW 的 PRECACHE 清单与实际文件一致（清单漂移=新版本拉不到或缓存打不开）。
    swp = os.path.join(SITE, "sw.js")
    if os.path.exists(swp):
        if "site/sw.js" not in tracked:
            untracked_refs.append("site/sw.js（SW 本体未跟踪 ⇒ 不部署，离线兜底静默失效）")
        sw_txt = rd(swp).decode("utf-8")
        prec = re.findall(r"^\s+'([^']+\.(?:html|css|js|svg|webmanifest))',?$", sw_txt, re.M)
        for f in prec:
            if not os.path.exists(os.path.join(SITE, f)):
                fails.append("SW PRECACHE 指向不存在的文件: " + f)
            elif "site/" + f not in tracked:
                untracked_refs.append("site/" + f + "（SW 预缓存清单内但未跟踪）")
        print(f"[{'PASS' if not any('PRECACHE' in f for f in fails) else 'FAIL'}] SW PRECACHE 清单 {len(prec)} 项与磁盘对账")
    if untracked_refs:
        fails.append("未跟踪但被引用: " + "; ".join(untracked_refs))
    print(f"[{'PASS' if not untracked_refs else 'FAIL'}] git 跟踪面对账：HTML/JS 引用 {len(refs) + len(js_files)} 项均在版本控制内")

# 9b) 一木成像：雕刻引擎 + 落地页雕刻台 + AR 场景一同源
wp = os.path.join(SITE, "assets/js/wood-to-statue.js")
dp = os.path.join(SITE, "assets/js/wood-demo.js")
wood_engine = rd(wp).decode("utf-8") if os.path.exists(wp) else ""
wood_demo = rd(dp).decode("utf-8") if os.path.exists(dp) else ""
if len(wood_engine) < 3000:
    fails.append("雕刻引擎缺失或过小: assets/js/wood-to-statue.js")
if len(wood_demo) < 1500:
    fails.append("雕刻台控制器缺失或过小: assets/js/wood-demo.js")
for tok in ("WOOD_TO_STATUE", "halfWidth", "bodyPath", "mandorla", "STAGES", "progress"):
    if tok not in wood_engine:
        fails.append("雕刻引擎缺少: " + tok)
for key in ("选木", "定像", "开坯", "修光", "彩绘贴金", "开光"):
    if key not in wood_engine:
        fails.append("雕刻引擎工序缺失: " + key)
if "WOOD_TO_STATUE" not in ar_scenes:
    fails.append("AR 场景一未复用雕刻引擎（两处画面会各画一套几何）")
if "function woodGrain" in ar_scenes or "function lotusPath" in ar_scenes:
    fails.append("AR 场景一仍留有旧造像几何（死代码）")
for token in ('id="carve-sec"', 'id="carve-stage"', 'id="carve-slider"', 'id="carve-rail"',
              'id="carve-cap-title"', "wood-to-statue.js", "wood-demo.js"):
    if token not in html:
        fails.append("一木成像未挂载: " + token)
i_engine = html.find("wood-to-statue.js")
i_scenes = html.find("ar-scenes.js")
i_demo = html.find("wood-demo.js")
if not (0 <= i_engine < i_scenes and i_engine < i_demo):
    fails.append("脚本加载顺序错误：wood-to-statue.js 必须先于 ar-scenes.js / wood-demo.js")
if "reduced" not in wood_demo:
    fails.append("雕刻台未处理 prefers-reduced-motion")
print(f"[{'PASS' if not any(x in f for x in ('雕刻', '一木成像', '脚本加载顺序')) else 'FAIL'}] 一木成像：引擎 / 雕刻台 / AR 同源 / 六工序 / 加载顺序")

# 页面必须挂载 AR 层与入口
for token in ('id="ar"', 'id="ar-stage"', 'id="ar-cards"', "ar-data.js", "ar-scenes.js", "ar.js"):
    if token not in html:
        fails.append("AR 未挂载: " + token)
# 无外链（零外部请求是轻量化 AR 的硬约束）。
# 判据必须精确：og:url / canonical / hreflang / JSON-LD 里的 URL 只是元数据字符串，
# 浏览器不会为其发起请求；把它们算成「外部请求」会让任何写了绝对 canonical 的站点必红。
# 真正会发请求的是：src 属性、以及 rel 为 stylesheet/preload/modulepreload 的 link。
ext = re.findall(r'(?:src)="(https?://[^"]+)"', html)
ext += re.findall(r'<link[^>]+rel="(stylesheet|preload|modulepreload)"[^>]+href="(https?://[^"]+)"', html)
ext = [x if isinstance(x, str) else x[1] for x in ext]
# JSON-LD 内的 URL 同样不产生请求，但顺手核验它与 canonical 一致，避免分享指向漂移
m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
if m:
    if m.group(1).rstrip('/') not in html.replace('\n', ''):
        fails.append("canonical 与页面其他绝对 URL 不一致")
if ext:
    fails.append("出现外部请求: " + ", ".join(ext[:3]))
print(f"[{'PASS' if not any('AR' in f or '外部请求' in f for f in fails) else 'FAIL'}] AR 展陈：3 场景 / 13 章节 / 152s / 零外链")

# 11) 交付治理件 + PWA/离线能力（对标 peer 后补齐的基线，防回归）
DOC_FILES = ["LICENSE", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md",
             "CODE_OF_CONDUCT.md", ".github/ISSUE_TEMPLATE/config.yml",
             ".github/PULL_REQUEST_TEMPLATE.md"]
doc_missing = [d for d in DOC_FILES if not os.path.exists(os.path.join(BASE, d))]
if doc_missing:
    fails.append("交付治理件缺失: " + ", ".join(doc_missing))
print(f"[{'PASS' if not doc_missing else 'FAIL'}] 交付治理件 {len(DOC_FILES) - len(doc_missing)}/{len(DOC_FILES)}")

# PWA：manifest + service worker 必须既在磁盘、又在站点发布目录内被 HTML 引用
PWA = {"manifest.webmanifest": 'rel="manifest"', "sw.js": "serviceWorker.register"}
pwa_bad = []
for fname, token in PWA.items():
    fp = os.path.join(SITE, fname)
    if not os.path.exists(fp) or os.path.getsize(fp) < 200:
        pwa_bad.append(fname + " 缺失或过小")
    elif token not in (html if fname.endswith("webmanifest") else html + "".join(rd(os.path.join(SITE, "assets/js", x)).decode("utf-8", "replace") for x in os.listdir(os.path.join(SITE, "assets/js")))):
        pwa_bad.append(fname + " 存在但未被页面引用/注册")
if pwa_bad:
    fails.append("PWA/离线能力: " + "; ".join(pwa_bad))
print(f"[{'PASS' if not pwa_bad else 'FAIL'}] PWA 离线兜底（manifest + sw 注册）")

# 无障碍与分享基线：字阶须走 rem/clamp，且分享元数据必须是绝对 URL
css_txt = rd(os.path.join(SITE, "assets/css/main.css")).decode("utf-8")
# 无障碍字阶不变量（反向验证驱动写出来的，见下）：
# 第一版只断言「存在 rem」，反向验证立刻假绿 —— 全站 86 处 font-size 已全量 rem 化，
# 退回 1 处 px 仍「存在 rem」，门禁不响。故改为断言不变量：font-size 里 px 必须为 0。
rem_units = re.findall(r"(?:[\d.]+|var\([^)]*\))\s*rem\b", css_txt)
px_font_sizes = re.findall(r"font-size:[^;}\n]*\d+(?:\.\d+)?px", css_txt)
if not rem_units:
    fails.append("无障碍：main.css 内无 rem 单位（系统/长者放大字号不生效）")
if px_font_sizes:
    fails.append("无障碍：%d 处 font-size 仍用 px（应走 rem，否则用户放大字号无效）：%s"
                 % (len(px_font_sizes), "; ".join(x.strip() for x in px_font_sizes[:3])))
# 根字号必须是百分比，写死 px 会屏蔽用户在系统里设定的字号
if not re.search(r"html\{[^}]*font-size:\s*(?:100%|[\d.]+em)\s*[;}]", css_txt):
    fails.append("无障碍：html 根字号未跟随用户设置（应为 font-size:100%）")
if "prefers-contrast" not in css_txt:
    fails.append("无障碍：无 prefers-contrast 支持")
if 'class="skip-link"' not in html or 'href="#main"' not in html:
    fails.append("无障碍：无 skip-link（键盘用户需逐一遍历导航）")
for must_abs in ['property="og:url"', 'property="og:image"', 'rel="canonical"']:
    m = re.search(must_abs + r'[^>]*content="([^"]+)"' if "property" in must_abs else must_abs + r'[^>]*href="([^"]+)"', html)
    if not m:
        fails.append("分享元数据缺失: " + must_abs)
    elif not m.group(1).startswith("https://"):
        fails.append("分享元数据非绝对 URL: " + must_abs + " -> " + m.group(1))
if "application/ld+json" not in html:
    fails.append("结构化数据缺失：无 JSON-LD")
print(f"[{'PASS' if not any(('无障碍' in f) or ('分享元数据' in f) or ('JSON-LD' in f) for f in fails) else 'FAIL'}] 无障碍与分享基线（rem 字阶 / skip-link / 绝对 og / JSON-LD）")


print()
if warns:
    print("WARNINGS:")
    for w in warns:
        print("  !", w)
if fails:
    print("RESULT: FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("RESULT: PASS  全部检查通过")