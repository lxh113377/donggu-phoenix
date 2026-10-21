# -*- coding: utf-8 -*-
"""reverse_env_attribution.py — 反向验证「环境缺口归因」这组修复（轮74）。

判据只有在「能报出你故意造的那一类错」时，它的 PASS 才有意义。本脚本对四个改动点
各造一次错/一次真实缺口，断言输出里出现应有的归因，且**永不出现「未知原因」**。

用例：
  C1 classify_child 单测        —— 用真实环境读数当向量，断言归类为 env_gap / crashed / product_fail
  C2 环境缺口报错块（NO_REEXEC）—— 在 LibreOffice 解释器下强制不切换，必须打 ENV 块，禁「未知原因」
  C3 字体判据归因（ASSUME_OK）  —— 必须报「缺 Python 模块 brotli」，禁「fontTools 未安装」
  C4 像素归因端到端（沙箱副本） —— 子判据替换成「静默 rc=3」，必须报 rc=3 + 零输出，禁「未知原因」
  C5 自动切换真的把两条判据跑起来 —— 正常跑必须出现字体完整性 PASS 与像素 6 层 PASS

退出码：0 全部符合预期 / 1 有不符合。
用法：python tools/reverse_env_attribution.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))
import pyenv  # noqa: E402

results = []


def check(name, cond, detail=""):
    detail = "" if not detail else str(detail)
    results.append((name, bool(cond), detail))
    print("[%s] %s%s" % ("PASS" if cond else "FAIL", name, ("  -- " + detail) if detail else ""))


def run_site(py, env_extra, cwd=None):
    env = pyenv.clean_env()
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_extra)
    p = subprocess.run([py, os.path.join(cwd or BASE, "tools", "verify_site.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=cwd or BASE, timeout=600, env=env)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


# C2-C5 必须在「真实故障现场」跑：LibreOffice 自带解释器 + 被它毒化的 PYTHONHOME。
# 那是本机特有的环境，CI（Linux runner）没有 —— 故显式 SKIP，而不是伪造一个替代现场。
LO = r"D:\LibreOffice\program\python.exe"
HAVE_SCENE = sys.platform.startswith("win") and os.path.exists(LO)

# ---- C1: classify_child 单测（向量取自真实事故读数）----
vec = [
    ((None, "", "", "PermissionError: [WinError 5] access denied"),
     "env_gap", "轮74 真实：LibreOffice 解释器不能 spawn 自己"),
    ((2, "", "缺少图像依赖（No module named 'cv2'）。请先运行：pip install ..."),
     "env_gap", "轮74 真实：子判据缺 cv2（rc=2）"),
    ((0, "[PASS] L1'\n[PASS] L2\n[SKIP] L1", "", ""), "ok", "正常取证"),
    ((1, "[FAIL] L2 有损编码", "", ""), "product_fail", "判据判红（产品缺陷）"),
    ((3, "", "", ""), "crashed", "子判据静默崩（零输出）"),
    ((-1073741819, "", "Traceback ... AssertionError: SRE module mismatch", ""),
     "env_gap", "环境毒化：子解释器加载错版标准库"),
]
for (args, want, why) in vec:
    got = pyenv.classify_child(*args)[0]
    check("C1 classify_child -> %s (%s)" % (want, why), got == want, "got=%s" % got)

if not HAVE_SCENE:
    for _n in ("C2 环境缺口报错块", "C3 字体判据归因", "C4 像素归因端到端", "C5 自动切换激活两条判据"):
        print("[SKIP] %s：本机无 LibreOffice 故障现场（CI 上必然如此，C1 单测已覆盖归类逻辑）" % _n)
    print()
    print("RESULT: %s  %d/%d（含 SKIP %d 例）" % (
        "PASS" if all(r[1] for r in results) else "FAIL",
        sum(1 for r in results if r[1]), len(results), 4))
    sys.exit(0 if all(r[1] for r in results) else 1)

# ---- C2: 环境缺口报错块（在 LibreOffice 解释器上强制不切换）----
rc2, out2, err2 = run_site(LO, {pyenv.NO_REEXEC: "1"})
blob2 = out2 + err2
check("C2 强制不切换 -> rc=2（环境缺口，不冒充判据失败）", rc2 == 2, "rc=%s" % rc2)
check("C2 报错块含「环境缺口」并点名缺失模块",
      ("环境缺口" in blob2) and re.search(r"缺失模块\s*:\s*\S+", blob2) is not None)
check("C2 报错块点出环境毒化变量", "环境毒化" in blob2 or "PYTHONHOME" in blob2)
check("C2 禁「未知原因」", "未知原因" not in blob2)

# ---- C3: 字体判据归因（ASSUME_OK 让脚本在缺 brotli 的解释器下继续）----
rc3, out3, err3 = run_site(LO, {pyenv.ASSUME_OK: "1"})
blob3 = out3 + err3
check("C3 字体判据显式 [SKIP] 且点名真实缺的模块 brotli",
      "[SKIP] 字体完整性" in out3 and "brotli" in out3,
      [ln for ln in out3.splitlines() if "字体完整性" in ln][:1])
check("C3 禁把 brotli 缺依赖说成「fontTools 未安装」", "fontTools 未安装" not in blob3)

# ---- C4: 像素归因端到端（沙箱副本 + 静默崩掉的子判据）----
tmp = tempfile.mkdtemp(prefix="rev_env_")
try:
    shutil.copytree(os.path.join(BASE, "site"), os.path.join(tmp, "site"))
    os.makedirs(os.path.join(tmp, "tools"))
    for f in ("verify_site.py", "pyenv.py"):
        shutil.copy2(os.path.join(BASE, "tools", f), os.path.join(tmp, "tools", f))
    # 子判据替换成「静默 rc=3」：判据没跑到，父门禁必须归因而不是写「未知原因」
    with open(os.path.join(tmp, "tools", "verify_pixel_exact.py"), "w", encoding="utf-8") as fh:
        fh.write("import sys\nsys.exit(3)\n")
    rc4, out4, err4 = run_site(LO, {pyenv.ASSUME_OK: "1"}, cwd=tmp)
    blob4 = out4 + err4
    line4 = [ln for ln in out4.splitlines() if "像素级数值判据" in ln and ln.startswith("[FAIL]")]
    check("C4 子判据静默崩 -> 父门禁报出 rc=3 与零输出",
          bool(line4) and ("rc=3" in line4[0]) and ("零输出" in line4[0]),
          line4[:1])
    check("C4 禁「未知原因」", "未知原因" not in blob4)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---- C5: 正常跑：自动切换 + 两条判据真的跑起来 ----
rc5, out5, err5 = run_site(LO, {})
check("C5 自动切换生效（打印 [ENV] 行）", "[ENV]" in out5 and "自动切换到" in out5,
      [ln for ln in out5.splitlines() if ln.startswith("[ENV]")][:1])
check("C5 字体完整性判据真的跑起来了", "[PASS] 字体完整性：渲染汉字全部在子集内" in out5)
check("C5 像素级数值判据真的跑起来了（6 层）", "[PASS] 像素级数值判据：6 层全部成立" in out5)
check("C5 总结果为 PASS", ("RESULT: PASS" in out5) and rc5 == 0, "rc=%s" % rc5)

bad = [r for r in results if not r[1]]
print()
print("RESULT: %s  %d/%d" % ("PASS" if not bad else "FAIL", len(results) - len(bad), len(results)))
if bad:
    for n, _c, d in bad:
        print("  - 不符合预期: %s (%s)" % (n, d))
    sys.exit(1)
