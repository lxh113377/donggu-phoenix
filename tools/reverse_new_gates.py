# -*- coding: utf-8 -*-
"""tools/reverse_new_gates.py —— 本轮新判据的反向验证（该红必红）。

台账 U-04/U-22/U-86 的硬规矩：任何新判据上线前必须证明它抓得住真缺陷，
否则它的 PASS 只代表「什么都没检查」。本脚本在 safe_mutation 副本上破坏，
真实工作区一个字节都不动（U-09 根治）。

破坏一律选「语义破坏」：改坏后代码仍可解析/可运行。
U-101 的教训是制造语法错误会让测试因别的原因失败，反而证明不了判据有效。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safe_mutation import mutate_sandbox

CASES = [
    ("旁白开关被删", "tools/narration_gate_test.py", "site/index.html",
     'id="ar-narrate"', 'data-narrate-x'),
    ("切场景不再停声", "tools/narration_gate_test.py", "site/assets/js/ar.js",
     "narr.cancel();\r\n    state.t = 0;", "state.t = 0;"),
    ("云端 TTS 混进来", "tools/narration_gate_test.py", "site/assets/js/ar.js",
     "var STORE_KEY = \"donggu-ar-v1\";",
     "var STORE_KEY = \"donggu-ar-v1\"; var _tts = \"https://translate.googleapis.com/tts\";"),
    ("密度改回硬档位", "tools/engine_polish_test.py", "site/assets/js/phoenix.js",
     "var _byArea = this._densFor(_area);",
     "var _byArea = (this.isMobile ? 1500 : 2600);"),
    ("HUD 丢 trailing", "tools/engine_polish_test.py", "site/assets/js/ar.js",
     "hud.pending = setTimeout", "hud.pendingT = setTimeout"),
    ("frame 不传时基", "tools/engine_polish_test.py", "site/assets/js/ar.js",
     "paintHud(now);", "paintHud();"),
    ("create 退回 if 链", "tools/engine_polish_test.py", "site/assets/js/ar-scenes.js",
     "var Ctor = SCENE_REGISTRY[id];",
     "var Ctor = (id === \"craft\" ? CraftScene : null);"),
    ("srcset 候选名推导改坏", "tools/orphan_asset_test.py", "site/assets/js/main.js",
     "'-340.$1'", "'-340X.$1'"),
    ("文创图被当孤儿留着", "tools/orphan_asset_test.py", "site/assets/js/main.js",
     "loading=\"lazy\" decoding=\"async\" width=\"380\"", "width=\"380\""),
]


def main():
    caught = 0
    missed = []
    with mutate_sandbox() as sb:
        for name, gate, rel, old, new in CASES:
            fp = sb.path(rel)
            s = open(fp, encoding="utf-8", newline="").read()
            if old not in s:
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
