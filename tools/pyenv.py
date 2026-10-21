# -*- coding: utf-8 -*-
"""pyenv.py — 站点门禁的「解释器确定性解析」层（2026-10-21 轮74 新建）。

## 为什么要有这一层（三个实证事故）

本机 PATH 首位的 python 是 LibreOffice 自带解释器
（D:/LibreOffice/program/python-core-3.13.15），实测它：
  1. 缺 cv2 / brotli / PIL —— 依赖它们的判据在 import 期就崩；
  2. **无法 spawn 自己** —— subprocess.run([sys.executable, ...]) 抛
     PermissionError [WinError 5]（spawn git 或别的解释器正常，只有自身不行）；
  3. 而父门禁把「子进程没起来」写成「未知原因」—— 把可归因的环境缺口伪装成谜团
     （轮51 修了 rc=2/stderr 分支，漏了异常分支）。

本层负责把「环境缺口」与「产品缺陷」彻底分开：
  - 当前解释器能力足够  -> 原样继续（CI 走这条，零行为变化）；
  - 能力不足但存在可用解释器 -> 自动切换（env 变量防循环），打印一行 [ENV]；
  - 都不可用 -> 打 ENV 块并以 rc=2 退出，**禁止写未知原因**。

## 候选顺序（确定性，不依赖 PATH 顺序）

  1. 环境变量 SITE_PY（显式覆盖，最高优先）
  2. 当前解释器 sys.executable
  3. py 启动器：py -3.12 / -3.13 / -3.11
  4. ~/.workbuddy/binaries/python/envs/*/Scripts/python.exe
  5. %APPDATA%/uv/python/*/python.exe
  6. where python 的全部命中

## 用法

    import pyenv
    pyenv.ensure(["numpy", "cv2", "fontTools", "brotli"])      # 入口脚本第一件事
    exe = pyenv.best_for(["numpy", "cv2"]) or sys.executable   # 需要指定子进程解释器时

## 退出码约定

  2 = 环境缺口（与「判据不通过」(1) 区分，沿用 verify_pixel_exact.py 的既有口径）。
"""
import os
import sys
import glob
import shutil
import subprocess

REEXEC_FLAG = "SITE_PY_REEXECED"      # 防循环：本进程已是切换后的解释器
NO_REEXEC = "SITE_PY_NO_REEXEC"       # 测试钩子：强制不切换（验「环境缺口」报错块）
ASSUME_OK = "SITE_PY_ASSUME_OK"       # 测试钩子：跳过能力检查（验「能力不足时的归因」分支）

# 轮74 实测的真根因：LibreOffice 的 python.exe 启动器会给**自身进程**注入
#   PYTHONHOME=D:\LibreOffice\program\python-core-3.13.15
#   PYTHONPATH=D:\LibreOffice\program\; ...python-core-3.13.15\lib;...site-packages
# 任何子解释器继承这两个变量后，3.12 子进程会去加载 3.13 的标准库，报
#   AssertionError: SRE module mismatch
# 于是 numpy/cv2/fontTools 全部 import 失败（brotli 是纯模块，侥幸幸存）——
# 「缺依赖」是假象，真相是「被毒化的环境变量」。故所有探测与切换都必须先净化。
_POISON = ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONEXECUTABLE",
           "PYTHONNOUSERSITE", "PYTHONUSERBASE")


def clean_env(base=None):
    """返回剥掉 PYTHON* 注入变量的环境副本，供子进程/切换使用。"""
    env = dict(os.environ if base is None else base)
    for k in _POISON:
        env.pop(k, None)
    return env


def scrub_own_env():
    """把注入变量从本进程环境里真正删掉（os.execv 继承的是本进程环境和它）。

    返回被删掉的变量名，用于日志；不删就会带着 3.13 的 PYTHONHOME 切进 3.12，
    切换后的进程照样崩 —— 白切。
    """
    removed = []
    for k in _POISON:
        if k in os.environ:
            del os.environ[k]
            removed.append(k)
    return removed
_PROBE_CODE = (
    "import sys\n"
    "miss = []\n"
    "for m in sys.argv[1:]:\n"
    "    try:\n"
    "        __import__(m)\n"
    "    except Exception:\n"
    "        miss.append(m)\n"
    "print('PYENV_MISS:' + ','.join(miss))\n"
)
_cache = {}


def _norm(exe):
    try:
        return os.path.normcase(os.path.abspath(exe))
    except Exception:
        return os.path.normcase(exe)


def inproc_missing(modules):
    """当前进程内直接 import，返回缺失模块。快路径：够用就不起子进程。"""
    miss = []
    for m in modules:
        try:
            __import__(m)
        except Exception:
            miss.append(m)
    return miss


def probe(exe, modules, extra_args=()):
    """在指定解释器里试 import，返回 (ok, missing)。探测失败视为不可用（不抛）。"""
    key = (_norm(exe), tuple(modules), tuple(extra_args))
    if key in _cache:
        return _cache[key]
    cmd = [exe] + list(extra_args) + ["-c", _PROBE_CODE] + list(modules)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=clean_env())
        line = ""
        for ln in (r.stdout or "").splitlines():
            if ln.startswith("PYENV_MISS:"):
                line = ln
        if r.returncode != 0 or not line:
            res = (False, list(modules))
        else:
            miss = [m for m in line[len("PYENV_MISS:"):].split(",") if m]
            res = (not miss, miss)
    except Exception:
        res = (False, list(modules))
    _cache[key] = res
    return res


def candidates():
    """按确定性顺序产出 (exe, extra_args) 候选，去重。"""
    out = []
    seen = set()

    def add(exe, extra=(), label=""):
        if not exe:
            return
        k = (_norm(exe), tuple(extra))
        if k in seen:
            return
        seen.add(k)
        out.append((exe, tuple(extra), label))

    add(os.environ.get("SITE_PY"), label="env SITE_PY")
    add(sys.executable, label="current")
    launcher = shutil.which("py")
    if launcher:
        for ver in ("-3.12", "-3.13", "-3.11"):
            add(launcher, (ver,), label="py " + ver)
    home = os.path.expanduser("~")
    for pat in (os.path.join(home, ".workbuddy", "binaries", "python", "envs", "*", "Scripts", "python.exe"),
                os.path.join(os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming")),
                             "uv", "python", "*", "python.exe")):
        for p in sorted(glob.glob(pat)):
            add(p, label="glob")
    for name in ("python3", "python"):
        w = shutil.which(name)
        if w:
            add(w, label="which " + name)
    return out


def diagnose(modules):
    """返回候选体检表，供日志与报错使用。"""
    rows = []
    for exe, extra, label in candidates():
        try:
            r = subprocess.run([exe] + list(extra) + ["-c", "import sys;print(sys.version.split()[0],sys.executable)"],
                               capture_output=True, text=True, timeout=90, env=clean_env())
            ver = (r.stdout or "").strip().replace(" ", " | ") or ("rc=%s" % r.returncode)
        except Exception as e:
            ver = "启动失败:" + type(e).__name__
        ok, miss = probe(exe, modules, extra)
        rows.append({"exe": exe, "extra": list(extra), "label": label, "version": ver,
                     "ok": ok, "missing": miss})
    return rows


def best_cmd_for(modules):
    """返回第一个能力足够解释器的「完整命令」(list)；无则 None。当前解释器优先。

    与 best_for 的差别：py 启动器这类候选必须连版本选择器一起给出
    (['C:\\Windows\\py.EXE', '-3.12'])——只给 exe 会丢掉版本约束，
    落到 launcher 默认版本上就是「碰巧能跑」，不是「确定能跑」。
    """
    if not inproc_missing(modules):
        return [sys.executable]
    for exe, extra, _label in candidates():
        ok, _miss = probe(exe, modules, extra)
        if ok:
            return [exe] + list(extra)
    return None


def best_for(modules):
    """返回第一个能力足够解释器的可执行路径（无则 None）。需要完整命令用 best_cmd_for。"""
    cmd = best_cmd_for(modules)
    return cmd[0] if cmd else None


def classify_child(rc, stdout, stderr, exc=""):
    """把子进程结果归类为 (kind, detail)；kind in {ok, product_fail, env_gap, crashed}。

    这个函数本身就是轮74 的教训：父门禁原先把「失败原因归类」散写在调用点里，
    只接了 rc==2 一支，于是异常分支与零输出分支都掉进「未知原因」——
    把可归因的环境缺口伪装成谜团。抽成纯函数后可被逐例单测（见
    tools/reverse_env_attribution.py），断言「它必须报出我故意造的那一类」。

    归类规则（顺序有意义）：
      [FAIL] 行存在        -> product_fail（判据真的判了，且判红）
      rc == 0 且无 FAIL    -> ok
      rc 是 None（未启动） -> env_gap（调用期异常）
      报错文本含缺库/权限/SRE -> env_gap
      其余非零退出         -> crashed（判据自身崩了，同样不是产品缺陷）
    """
    out = stdout or ""
    err = stderr or ""
    fails = [ln.strip() for ln in out.splitlines() if ln.startswith("[FAIL]")]
    if fails:
        return "product_fail", "; ".join(fails[:3])
    if rc == 0:
        return "ok", ""
    bits = []
    if exc:
        bits.append("子进程调用异常 " + exc)
    bits.append("rc=%s" % ("未启动" if rc is None else rc))
    tail = [ln.strip() for ln in (err or out).splitlines() if ln.strip()]
    bits.append(" | ".join(tail[:2]) if tail else "子进程零输出（疑似启动期即崩）")
    blob = " ".join(bits)
    env_gap = ("No module named" in blob or "PermissionError" in blob
               or "WinError 5" in blob or "SRE module mismatch" in blob
               or "缺少图像依赖" in blob or "请先运行" in blob)
    if env_gap:
        return "env_gap", "; ".join(bits)
    return "crashed", "; ".join(bits)


def _env_fail(modules, missing, extra_note=""):
    rows = diagnose(modules)
    sys.stderr.write("\n[ENV] 环境缺口（不是判据不通过、更不是产品缺陷）：\n")
    sys.stderr.write("  当前解释器: %s\n" % sys.executable)
    sys.stderr.write("  缺失模块  : %s\n" % ", ".join(missing or modules))
    if extra_note:
        sys.stderr.write("  说明      : %s\n" % extra_note)
    _poisoned = [k for k in _POISON if k in os.environ]
    if _poisoned:
        sys.stderr.write("  环境毒化  : %s 指向别处解释器，会让所有子解释器 import 失败"
                         "（SRE module mismatch）\n" % ", ".join(_poisoned))
    sys.stderr.write("  候选体检:\n")
    for r in rows:
        sys.stderr.write("    %-42s %-8s %s\n" % (r["version"][:42], "OK" if r["ok"] else "缺 " + ",".join(r["missing"]),
                                                  r["exe"]))
    sys.stderr.write("  修法(任选其一):\n")
    sys.stderr.write("    a) 用有依赖的解释器跑: SITE_PY=<python.exe> 或 python -m pip install %s\n"
                     % " ".join(modules))
    sys.stderr.write("    b) 本脚本会自动切换；若仍失败说明本机确实没有任何可用解释器。\n")
    sys.stderr.flush()
    sys.exit(2)


def ensure(modules, argv=None, label=""):
    """入口脚本第一件事：保证当前解释器具备 modules，否则自动切换。

    返回 True 表示「无需切换」（CI 与正常环境走这条，零行为变化）。
    切换成功时不返回（os.execv 替换进程）。
    """
    if os.environ.get(ASSUME_OK) == "1":
        return True          # 测试钩子：跳过检查，让脚本在「能力不足」的解释器下继续跑
    missing = inproc_missing(modules)
    if not missing:
        return True
    if os.environ.get(NO_REEXEC) == "1" or os.environ.get(REEXEC_FLAG) == "1":
        _env_fail(modules, missing,
                  extra_note="已禁用自动切换(%s=1)，故如实报环境缺口。" % (
                      NO_REEXEC if os.environ.get(NO_REEXEC) == "1" else REEXEC_FLAG))
    target = None
    for exe, extra, _lab in candidates():
        ok, _miss = probe(exe, modules, extra)
        if ok:
            target = (exe, extra)
            break
    if target is None:
        _env_fail(modules, missing, extra_note="自定义切换路径未能找到可用解释器。")
    exe, extra = target
    args = list(argv if argv is not None else sys.argv)
    script = os.path.abspath(args[0]) if args else os.path.abspath(sys.argv[0])
    # 关键：先净化本进程环境再 execv —— 否则带着 3.13 的 PYTHONHOME 切进 3.12，
    # 切换后的进程会以 SRE module mismatch 崩在启动期（实测，见 _POISON 注释）。
    removed = scrub_own_env()
    os.environ[REEXEC_FLAG] = "1"
    note = "[ENV] %s解释器 %s 缺 %s → 自动切换到 %s%s\n" % (
        label + "：" if label else "", sys.executable, ",".join(missing), exe,
        ("（已净化环境变量 %s）" % ",".join(removed)) if removed else "")
    sys.stdout.write(note)
    sys.stdout.flush()
    os.execv(exe, [exe] + list(extra) + [script] + args[1:])


if __name__ == "__main__":
    mods = sys.argv[1:] or ["numpy", "cv2", "fontTools", "brotli"]
    for r in diagnose(mods):
        print("%-46s %-10s %s" % (r["version"][:46], "OK" if r["ok"] else "缺 " + ",".join(r["missing"]), r["exe"]))
    print()
    print("best_for(%s) = %s" % (",".join(mods), best_for(mods)))
