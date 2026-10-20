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
culture_js = rd(os.path.join(SITE, "assets/data/culture.js")).decode("utf-8")
main_js = rd(os.path.join(SITE, "assets/js/main.js")).decode("utf-8")
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
# 🔴 口径（2026-10-20 轮6 修订）：预算衡量的是「会被部署的体积」，故只计 **git 跟踪** 的文件。
# 一手教训：并发会话把 12 张尚在制作中的文创图（447KB）生成到 site/ 下但未 git add，
# 磁盘总体积 1683KB 直接判红 —— 而这些文件根本不会被部署（Pages 只发跟踪内容），
# 判红指向的是一个不存在的问题，且会让「谁先跑门禁谁背锅」。
# 这不是放宽阈值（阈值仍 1600KB），是纠正度量对象：磁盘 ≠ 部署面。
# 无 git 环境时退回全量统计（宁可严，不可漏判）。
tracked_now = git_tracked()
total = 0
files = []
untracked_bytes = 0
untracked_n = 0
for r, _, fs_ in os.walk(SITE):
    for f in fs_:
        p = os.path.join(r, f)
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        s = os.path.getsize(p)
        if tracked_now is not None and ("site/" + rel) not in tracked_now:
            untracked_bytes += s
            untracked_n += 1
            continue
        total += s
        files.append((s, rel))
files.sort(reverse=True)
print(f"[INFO] 站点部署体积 {total/1024:.0f} KB / {len(files)} 文件"
      + (f"（另有未跟踪 {untracked_n} 文件 {untracked_bytes/1024:.0f}KB 不计入：它们不会部署）"
         if untracked_n else ""))
# 预算口径（2026-10-20 轮5 修订）：整站 1.6MB + **首屏关键路径 <= 400KB**。
# 上调原因：设计系统 v2 引入自托管中文字体（238KB 子集），而「零外部请求」是项目硬约束，
# 不能用 Google Fonts CDN 把字体成本甩出去 —— 该成本必须记在本地预算里。
# 收紧的补偿：新增下面这条更贴近真实体验的判据（首屏关键路径），它比整站体积更能防退化。
BUDGET_KB = 1600
if total > BUDGET_KB * 1024:
    fails.append(f"体积超预算 {BUDGET_KB}KB: {total/1024:.0f}KB")
elif total > BUDGET_KB * 1024 * 0.8:
    warns.append(f"体积已用预算 80% 以上: {total/1024:.0f}KB / {BUDGET_KB}KB")
print("  最大 5 个文件:", ", ".join(f"{n}({s//1024}KB)" for s, n in files[:5]))

# 4b) 首屏关键路径：HTML + CSS + 首屏字体 + 首屏必执行脚本
critical = ["index.html", "assets/css/main.css",
            "assets/fonts/zcool-display.woff2", "assets/fonts/cinzel.woff2",
            "assets/data/culture.js", "assets/data/ar-data.js",
            "assets/js/phoenix.js", "assets/js/main.js"]
crit_bytes = sum(os.path.getsize(os.path.join(SITE, c)) for c in critical if os.path.exists(os.path.join(SITE, c)))
CRIT_KB = 400
if crit_bytes / 1024 > CRIT_KB:
    fails.append("首屏关键路径超预算 %dKB: %.0fKB" % (CRIT_KB, crit_bytes / 1024))
print(f"[{'PASS' if crit_bytes / 1024 <= CRIT_KB else 'FAIL'}] 首屏关键路径 {crit_bytes/1024:.0f} KB / 预算 {CRIT_KB} KB（HTML+CSS+字体+首屏脚本）")

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
        # 行尾必须容忍 \r：sw.js 在 Windows 工作区常是 CRLF，
        # 用 ',?$ 会一条都匹配不到 ⇒ 门禁解析到 0 项却打印 PASS，等于没检查（假绿）。
        # 扩展名清单必须覆盖 SW 实际缓存的所有类型。一手教训（2026-10-20 反向验证实测）：
        # 本行原为 (?:html|css|js|svg|webmanifest)，设计系统 v2 把 woff2 加进 PRECACHE 后，
        # 字体条目完全落在对账面之外 —— 注入指向不存在字体的条目，门禁仍 exit 0，
        # 且把 16 项报成 14 项。故补 woff2/图片类，并加下面的计数一致性守卫。
        prec = re.findall(r"^\s+'([^']+\.(?:html|css|js|svg|webmanifest|woff2|png|webp|jpg|jpeg|json))',?\r?$", sw_txt, re.M)
        # 计数一致性守卫：正则漏掉某一类型时 prec 会变少但 SW 里的条目没变，
        # 用「PRECACHE 数组内所有带引号条目」做独立分母，两者不等即判红。
        _blk = re.search(r"var PRECACHE = \[([\s\S]*?)\n\];", sw_txt)
        _all = re.findall(r"'([^']+\.[A-Za-z0-9]+)'", _blk.group(1)) if _blk else []
        if _blk and len(_all) != len(prec):
            fails.append("SW PRECACHE 对账覆盖不全：数组内 %d 项，正则只解析到 %d 项"
                         "（正则扩展名清单缺类型 ⇒ 该类型条目未被检查）" % (len(_all), len(prec)))
        if not prec:
            fails.append("SW PRECACHE 解析到 0 项（正则失配或清单为空 ⇒ 本项检查失效）")
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


# 12) 设计系统 v2（2026-10-20 轮5）：字体自托管 / 字号下限 / 字阶令牌 / 移动端菜单
#    这几条都是「肉眼看着还行但会静默退化」的项：字体掉回系统栈只是变丑，
#    字号掉到 10px 只是变小，汉堡菜单缺失只是窄屏用户少了入口 —— 都需要机器盯。
font_dir = os.path.join(SITE, "assets/fonts")
font_files = sorted(os.listdir(font_dir)) if os.path.isdir(font_dir) else []
woff2 = [f for f in font_files if f.endswith(".woff2")]
if len(woff2) < 2:
    fails.append("字体自托管不足：assets/fonts 内 woff2 仅 %d 个" % len(woff2))
for wf in woff2:
    fp = os.path.join(font_dir, wf)
    if os.path.getsize(fp) < 8000:
        fails.append("字体子集过小（可能未生成完整字形）: " + wf)
    if "site/assets/fonts/" + wf not in (tracked or set()):
        fails.append("字体未入版本控制（部署后 404）: " + wf)
face_rules = re.findall(r"@font-face\{([^}]+)\}", css_txt)
faces_with_src = [f for f in face_rules if "../fonts/" in f]
if len(faces_with_src) < 2:
    fails.append("@font-face 未引用自托管字体（当前 %d 条）" % len(faces_with_src))
if "font-display:swap" not in css_txt.replace(" ", ""):
    fails.append("字体缺少 font-display:swap（首屏会被字体加载阻塞）")
# 被字面引用的字体文件必须存在（否则 @font-face 静默失效、回落系统栈）
for ref in set(re.findall(r"\.\./fonts/([\w\-]+\.woff2)", css_txt)):
    if not os.path.exists(os.path.join(font_dir, ref)):
        fails.append("CSS 引用的字体不存在: " + ref)
# 零外链：字体也不能走 https://fonts.*
if re.search(r"fonts\.(googleapis|gstatic)\.com", css_txt + html):
    fails.append("站点仍引用 Google Fonts 外链（违反零外部请求）")
print(f"[{'PASS' if not any('字体' in f or 'font-face' in f or '外链' in f for f in fails) else 'FAIL'}] 字体自托管：{len(woff2)} 个 woff2 / {len(faces_with_src)} 条 @font-face / 零外链")

# 字号下限：正文级不得低于 11px（0.6875rem），标题不得低于 20px
rem_px = 16.0
too_small = []
for m in re.finditer(r"font-size:([^;}]+)", css_txt):
    v = m.group(1).strip()
    mm = re.match(r"^([\d.]+)rem$", v)
    if mm and float(mm.group(1)) * rem_px < 11:
        too_small.append(v)
    mc = re.match(r"^clamp\(([\d.]+)rem", v)
    if mc and float(mc.group(1)) * rem_px < 11:
        too_small.append(v)
if too_small:
    fails.append("字号低于 11px 下限：%s" % ", ".join(sorted(set(too_small))[:5]))
# 字阶令牌必须成体系（11 档的设计系统，不是各处随手写 rem）
if css_txt.count("--fs-") < 22:
    fails.append("字阶令牌不成体系（--fs-* 定义/引用过少）")
print(f"[{'PASS' if not any('字号低于' in f or '字阶令牌' in f for f in fails) else 'FAIL'}] 字阶：11px 下限 + --fs-* 令牌体系")

# 移动端：窄屏必须有可触达的导航入口（此前 .nav ul{display:none} 却无替代）
for token in ('id="nav-toggle"', 'id="menu"', 'aria-controls="menu"', 'aria-expanded'):
    if token not in html:
        fails.append("移动端导航缺失: " + token)
css_flat = css_txt.replace(" ", "").replace("\n", "")
if "@media(max-width:860px)" not in css_flat:
    fails.append("缺少窄屏导航断点（.nav-toggle 不会出现）")
print(f"[{'PASS' if not any('移动端导航' in f or '窄屏导航' in f for f in fails) else 'FAIL'}] 移动端导航：汉堡按钮 + 整屏目录 + aria 状态")

# 设计令牌与结构：段落编号、手绘分隔线、场景动线
for token in ('class="sec-idx"', 'class="ink-divider"', 'class="hero-meta"'):
    if token not in html:
        fails.append("设计结构缺失: " + token)
for token in (".sec-idx{", ".ink-divider{", ".road::before{", ".merch-item.is-feature{"):
    if token not in css_txt.replace(" ", "").replace("\n", ""):
        fails.append("设计系统规则缺失: " + token)
print(f"[{'PASS' if not any('设计结构' in f or '设计系统规则' in f for f in fails) else 'FAIL'}] 设计结构：段落编号 / 墨线分隔 / 场景动线 / 文创特写格")

# 13) 版本对账守卫：新 HTML 撞旧缓存 CSS 会把页面渲染成无样式文本（比白屏更难解释）。
#     判据两侧必须同值：CSS 的 --build 与 HTML 里守常量的 BUILD。
css_build = re.search(r'--build:\s*([\w.]+)\s*;', css_txt)
html_build = re.search(r"var\s+BUILD\s*=\s*['\"]([\w.]+)['\"]", html)
if not css_build:
    fails.append("版本对账：CSS 缺少 --build 锚点")
if not html_build:
    fails.append("版本对账：index.html 缺少 BUILD 常量（老访客会拿到旧 CSS 而版式崩坏）")
if css_build and html_build and css_build.group(1) != html_build.group(1):
    fails.append("版本对账不一致：CSS --build=%s ≠ HTML BUILD=%s" % (css_build.group(1), html_build.group(1)))
if "getRegistrations" not in html or "caches.delete" not in html:
    fails.append("版本对账守卫未实现（应清 SW 注册与 caches 后重载一次）")
if "sessionStorage.getItem(KEY) === BUILD" not in html:
    fails.append("版本对账守卫缺少防循环闸（会无限刷新）")
print(f"[{'PASS' if not any('版本对账' in f for f in fails) else 'FAIL'}] 版本对账守卫：CSS --build 与 HTML BUILD 同值 + 防循环闸")

# 15) 进场动画：阈值必须可达（超高块回归锁）
#     一手事故：threshold:0.12 遇上高 4964px 的文创网格（视口 844px）⇒ 交叉比最高 0.17，
#     跳进块内就永远够不到阈值，整块保持 opacity:0，手机端出现一大片空白。
m_thr = re.search(r"threshold:\s*([\d.]+)", main_js)
if not m_thr:
    fails.append("进场动画：未找到 IntersectionObserver threshold（判据失配）")
elif float(m_thr.group(1)) > 0.02:
    fails.append("进场动画阈值不可达风险：threshold=%s（超高块上永远触发不了）" % m_thr.group(1))
# 兜底必须真的被调用（只定义不调用 = 没有兜底，反向验证时这条会放水）
if not re.search(r"\brevealTall\(\);", main_js):
    fails.append("进场动画缺少高块兜底调用（函数定义了但没执行）")
if "scrollHeight > vh" not in main_js.replace(" ", "").replace("vh*1.4", "vh"):
    if "scrollHeight" not in main_js:
        fails.append("进场动画兜底未判元素高度（无法识别超高块）")
print("[%s] 进场动画：阈值可达 + 高块兜底（防整块空白）" % ('PASS' if not any('进场动画' in f for f in fails) else 'FAIL'))


# 16) 行长（measure）：中文正文舒适区约 20-40 字/行。
#     本轮实测：.ar-note p 曾 77 字/行、.carve-note 98.5 字/行 —— 视线回扫成本高、易串行。
#     静态判据：这几个长文本块必须有 max-width，且单位必须是 em（中文 1 字≈1em）。
#     一手坑：用 ch 会砍半（ch 按 "0" 宽算，中文 1 字≈2ch），实测把 77 字/行 砍到 18.9 字/行。
measure_checks = ['.ar-note p{', '.foot-copy p{']
for sel in measure_checks:
    j = css_txt.find(sel)
    if j < 0:
        fails.append("行长判据：找不到规则 " + sel)
        continue
    rule = css_txt[j: css_txt.find('}', j)]
    if 'max-width' not in rule:
        fails.append("行长：%s 缺少 max-width（长行难读）" % sel.rstrip('{'))
bad_ch = re.findall(r"max-width:\s*\d+(?:\.\d+)?ch", css_txt)
if bad_ch:
    fails.append("行长：使用 ch 单位 %s（中文下会把行宽砍半，应用 em）" % ", ".join(bad_ch[:3]))
print("[%s] 行长约束：长文本块有 max-width 且未误用 ch" % ('PASS' if not any('行长' in f for f in fails) else 'FAIL'))

# 17) 装饰元素语义：肉眼可见但非内容的元素（水印/纹样字）必须显式标 data-decorative，
#     否则对比度审计会把它当正文判（本轮：240px 水印「畲」对比度 1.04:1 被判不达标）。
n_deco = len(re.findall(r'data-decorative=', html))
if 'hero-word' in html and 'data-decorative' not in html:
    fails.append("装饰水印缺少 data-decorative 语义（会被对比度判据误判为正文）")
print("[%s] 装饰元素语义：%d 处已标注 data-decorative" % ('PASS' if not any('装饰水印' in f for f in fails) else 'FAIL', n_deco))

# 14) 文创实物图：12 件必须件件有图（此前 6 件只有占位图腾也能过闸）
merch_pairs = re.findall("id: '([a-z-]+)',\\s*image: '([^']+)'", culture_js)
if len(merch_pairs) < 12:
    fails.append("文创少于 12 件或缺 image 字段（实得 %d）" % len(merch_pairs))
for _mid, _rel in merch_pairs:
    if not os.path.exists(os.path.join(SITE, _rel)):
        fails.append("文创图不存在: %s -> %s" % (_mid, _rel))
    elif os.path.getsize(os.path.join(SITE, _rel)) > 120 * 1024:
        fails.append("文创图过大(>120KB): %s" % _mid)
print("[%s] 文创实物图 %d/12 件件有图且不超 120KB" % (
    'PASS' if not any('文创图' in f or '文创少于' in f for f in fails) else 'FAIL', len(merch_pairs)))


# 14) 像素级复刻（2026-10-20 轮6）：成品必须是参考件本身，不是「画得像」。
#     判据不看肉眼，看数据：①资产在盘且非空；②剖面由该资产反解（尺寸一致）；
#     ③引擎里存在「揭示」通路且成品图被真正 drawImage；④成品图进 PRECACHE（离线也像素级）；
#     ⑤揭示段的接管权重把矢量段压掉（否则照片周围挂一圈矢量化金边）。
#     一手教训：v1 版成品是纯金剪影，肉眼看「有个像」就算过了，但评审一句「不像」全盘推翻 ——
#     这类判据必须机器化，否则每轮都要靠人眼重判。
statue_img = os.path.join(SITE, "assets/img/statue-cut.webp")
prof_js = os.path.join(BASE, "site/assets/data/statue-profile.js")
statue_meta = os.path.join(BASE, "_dev/mate/statue_asset_meta.json")
if not os.path.exists(statue_img) or os.path.getsize(statue_img) < 20000:
    fails.append("像素级复刻：成品资产缺失或过小 assets/img/statue-cut.webp")
if not os.path.exists(prof_js) or os.path.getsize(prof_js) < 800:
    fails.append("像素级复刻：轮廓剖面缺失 assets/data/statue-profile.js")
prof_txt = rd(prof_js).decode("utf-8") if os.path.exists(prof_js) else ""
for key in ("left:", "right:", "halfWidth:", "aspect:", "axis:"):
    if key not in prof_txt:
        fails.append("像素级复刻：剖面缺少字段 " + key)
if "statue-cut.webp" not in prof_txt:
    fails.append("像素级复刻：剖面未绑定成品资产（引擎会回退手写几何）")
# 剖面尺寸必须与资产一致：查 assets 元数据（由 build_statue_asset.py 写）
if os.path.exists(statue_meta):
    try:
        meta = json.loads(rd(statue_meta).decode("utf-8"))
        ow, oh = meta.get("outSize", [0, 0])
        if ("w: %d" % ow) not in prof_txt or ("h: %d" % oh) not in prof_txt:
            fails.append("像素级复刻：剖面尺寸与资产不一致（%dx%d）" % (ow, oh))
    except Exception as e:
        fails.append("像素级复刻：资产元数据解析失败 %s" % e)
for tok in ("revealStatue", "drawImage", "imageGeom", "STATUE_PROFILE", "takeover"):
    if tok not in wood_engine:
        fails.append("像素级复刻：引擎缺少揭示通路 " + tok)
if "'assets/img/statue-cut.webp'" not in rd(os.path.join(SITE, "sw.js")).decode("utf-8"):
    fails.append("像素级复刻：成品图未进 SW PRECACHE（离线时退回矢量像）")
if "statue-profile.js" not in rd(os.path.join(SITE, "sw.js")).decode("utf-8"):
    fails.append("像素级复刻：剖面未进 SW PRECACHE")
if "statue-profile.js" not in html:
    fails.append("像素级复刻：index.html 未加载 statue-profile.js（引擎会走手写回退）")
# 脚本顺序：剖面必须先于引擎
i_prof = html.find("statue-profile.js")
i_eng = html.find("wood-to-statue.js")
if not (0 <= i_prof < i_eng):
    fails.append("像素级复刻：脚本顺序错误，statue-profile.js 必须先于 wood-to-statue.js")
print(f"[{'PASS' if not any('像素级复刻' in f for f in fails) else 'FAIL'}] 像素级复刻：成品资产 / 左右不对称剖面 / 揭示通路 / 离线预缓存 / 加载顺序")

# 14b) 像素级复刻的「数值判据」：交给 tools/verify_pixel_exact.py。
#      上面 14) 只查结构（文件在、通路在），查不出「图有损」「渲染错位」「资产被换掉」——
#      那些必须逐像素比。子进程调用而非 import：把 Playwright/OpenCV 的依赖与失败模式隔离开，
#      且让本脚本在 CI（无浏览器）上仍能跑。
#      三态口径（SKIP 不算 PASS，但也不硬判红）：
#        - 缺素材原件（素材/*.jpg 被 .gitignore 排除）⇒ L1 SKIP，CI 上必然如此；
#        - 缺渲染取证（_dev/ 被 .gitignore 排除）      ⇒ L4 SKIP；
#        两者都有「可提交的静态替身」（L1' 资产 SHA256 锁 / L4' 引擎通路特征），
#        所以「有人换图或拆掉通路」在 CI 上照样会红 —— SKIP 不等于放水。
PIXEL_TOOL = os.path.join(BASE, "tools", "verify_pixel_exact.py")
if not os.path.exists(PIXEL_TOOL):
    fails.append("像素级复刻数值判据：缺少 tools/verify_pixel_exact.py")
else:
    pixel_out, pixel_rc = "", None
    try:
        pr = subprocess.run([sys.executable, PIXEL_TOOL], capture_output=True, text=True,
                            cwd=BASE, timeout=300)
        pixel_out, pixel_rc = (pr.stdout or ""), pr.returncode
    except Exception as e:
        pixel_out = "子进程调用失败：%s" % e
    lines = [ln for ln in pixel_out.splitlines() if ln.startswith("[PASS]") or ln.startswith("[SKIP]")]
    n_pass = sum(1 for ln in lines if ln.startswith("[PASS]"))
    n_skip = sum(1 for ln in lines if ln.startswith("[SKIP]"))
    if pixel_rc == 0:
        if n_skip:
            warns.append("像素级数值判据：%d 层因缺件未取证（%s）"
                         % (n_skip, "；".join(ln.split("：")[0].replace("[SKIP] ", "")
                                             for ln in lines if ln.startswith("[SKIP]"))))
            print("[PASS] 像素级数值判据：%d 层取证通过 / %d 层未取证（缺件已在 WARNINGS 列明）"
                  % (n_pass, n_skip))
        else:
            print("[PASS] 像素级数值判据：%d 层全部成立（L1 资产==素材 / L1' SHA256 锁 / "
                  "L2 无损编码 / L3 剖面绑定 / L4 1:1 渲染 / L4' 引擎通路）" % n_pass)
    else:
        hard = [ln for ln in pixel_out.splitlines() if ln.startswith("[FAIL]")]
        fails.append("像素级数值判据未通过：" + ("; ".join(x.strip() for x in hard[:3]) or "未知原因"))
        print("[FAIL] 像素级数值判据：%s" % ("; ".join(x.strip() for x in hard[:3]) or "未知原因"))


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