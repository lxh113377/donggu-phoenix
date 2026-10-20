# -*- coding: utf-8 -*-
"""tools/reverse_new_gates.py —— 本轮新判据的反向验证（该红必红）。

台账 U-04/U-22/U-86 的硬规矩：任何新判据上线前必须证明它抓得住真缺陷，
否则它的 PASS 只代表「什么都没检查」。本脚本在 safe_mutation 副本上破坏，
真实工作区一个字节都不动（U-09 根治）。

破坏一律选「语义破坏」：改坏后代码仍可解析/可运行。
U-101 的教训是制造语法错误会让测试因别的原因失败，反而证明不了判据有效。

前置检查为什么自己写（不用 mutate_sandbox 的 require_clean）：
  本机有并行端同时在同一仓工作，tools/ 下常年存在他人未跟踪脚本，
  整站「必须干净」的前提让反向验证**永远跑不起来** —— 而「跑不起来」和
  「跑过且全绿」在报告里长得太像，这是更糟的失败模式。
  真正的风险（U-09）是**被破坏的目标文件自身有未提交修改**：那种情况下
  副本拿不到最新代码，验的是旧版。所以这里逐目标文件核 git 状态，
  只有目标脏/未跟踪才拒绝，其余照常执行。
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safe_mutation import mutate_sandbox

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    # (名称, 判据脚本, 目标文件, 旧串, 新串)
    ("旁白开关被删", "tools/narration_gate_test.py", "site/index.html",
     'id="ar-narrate"', 'data-narrate-x'),
    ("切场景不再停声", "tools/narration_gate_test.py", "site/assets/js/ar.js",
     "narr.cancel();\r\n    state.t = 0;", "state.t = 0;"),
    ("云端 TTS 混进来", "tools/narration_gate_test.py", "site/assets/js/ar.js",
     'var STORE_KEY = "donggu-ar-v1";',
     'var STORE_KEY = "donggu-ar-v1"; var _tts = "https://translate.googleapis.com/tts";'),
    ("密度改回硬档位", "tools/engine_polish_test.py", "site/assets/js/phoenix.js",
     "var _byArea = this._densFor(_area);",
     "var _byArea = (this.isMobile ? 1500 : 2600);"),
    ("HUD 丢 trailing", "tools/engine_polish_test.py", "site/assets/js/ar.js",
     "hud.pending = setTimeout", "hud.pendingT = setTimeout"),
    ("frame 不传时基", "tools/engine_polish_test.py", "site/assets/js/ar.js",
     "paintHud(now);", "paintHud();"),
    ("create 退回 if 链", "tools/engine_polish_test.py", "site/assets/js/ar-scenes.js",
     "var Ctor = SCENE_REGISTRY[id];",
     'var Ctor = (id === "craft" ? CraftScene : null);'),
    ("srcset 候选名推导改坏", "tools/orphan_asset_test.py", "site/assets/js/main.js",
     "'-340.$1'", "'-340X.$1'"),
    ("旁白态不即时同步", "tools/narration_gate_test.py", "site/assets/js/ar.js",
     "function syncNarrBtn() {", "function syncNarrBtnOff() {"),
]


def target_status():
    """返回 (问题列表, 目标数)。只关心本脚本要破坏的文件。"""
    rels = sorted(set(c[2] for c in CASES))
    problems = []
    for rel in rels:
        r = subprocess.run(["git", "status", "--porcelain", "--", rel],
                           cwd=BASE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        line = (r.stdout or "").strip()
        if not line:
            continue
        if line.startswith("??"):
            problems.append(rel + " 未被 git 跟踪")
        else:
            problems.append(rel + " 有未提交修改")
    return problems, len(rels)


def main():
    problems, n_targets = target_status()
    if problems:
        print("RESULT: SKIP  目标文件不干净，拒绝破坏性测试（U-09）：")
        for x in problems:
            print("  -", x)
        return 1
    print("前置检查：%d 个目标文件均已提交且无本地修改（并行端的未跟踪文件不影响本判据）"
          % n_targets)

    caught = 0
    missed = []
    with mutate_sandbox(require_clean=False) as sb:
        for name, gate, rel, old, new in CASES:
            fp = sb.path(rel)
            s = open(fp, encoding="utf-8", newline="").read()
            # 行尾归一后再比：文本模式读取会把 CRLF 变 LF，
            # 破坏串按 LF 拼而文件是 CRLF 时「替换没生效」会被误读成「判据无效」（U-129）
            if old not in s:
                s_lf = s.replace("\r\n", "\n")
                if old.replace("\r\n", "\n") in s_lf:
                    print("[锚点行尾不符] %s：源文件行尾与用例不一致" % name)
                    missed.append(name + "(行尾失配)")
                    continue
                print("[锚点失配] %s：副本里找不到待破坏文本，判据锚点需同步更新" % name)
                missed.append(name + "(锚点失配)")
                continue
            open(fp, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
            r = sb.run_python(gate, timeout=150)
            out = (r.stdout or "") + (r.stderr or "")
            red = r.returncode != 0
            detail = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("- ")]
            print("[%s] %-22s -> %s" % ("OK  " if red else "MISS", name,
                                        "判红" if red else "仍然 PASS（判据无效）"))
            if red:
                caught += 1
                print("        抓到: %s" % (detail[0][:120] if detail else "(无明细)"))
            else:
                missed.append(name)
            open(fp, "w", encoding="utf-8", newline="").write(s)
    print()
    print("反向验证：%d/%d 被抓到" % (caught, len(CASES)))
    if missed:
        print("未抓到: " + ", ".join(missed))
        print("RESULT: FAIL  存在无效判据")
        return 1
    print("RESULT: PASS  本轮新判据都能识别真实破坏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
