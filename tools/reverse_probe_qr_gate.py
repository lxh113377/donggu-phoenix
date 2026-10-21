# -*- coding: utf-8 -*-
"""tools/reverse_probe_qr_gate.py —— verify_site 第 7b 项（真机自检入口码）的反向验证。

为什么必须反向验
  7b 是 U-01 唯一真机入口的守卫。但「加了一段检查」不等于「检查真的会红」——
  本仓已被这类事故咬过多次（U-222 / U-224 / U-225：判据写了却没生效，
  或写反了自己不知道）。不造一次错，就永远不知道它是真闸还是装饰。

用例（全部在 safe_mutation 沙箱副本里跑，真实工作区一字节不动）
  A 基线：不改动 -> 7b 必须 PASS（排除「怎么改都判红」的过度反应）
  B 删自检页：site/_device_probe.html 移走 -> 必须判红且点名自检页
  C 码漂移：把入口码换成指向别的 URL 的合法二维码 -> 必须判红且说「解码不等于」
  D 码缺失：删掉 qr/qr-device-probe.png -> 必须判红

C 是关键用例：它证明判据真的**解码了像素**，而不是只看文件在不在。
（只看存在性的话，换成任何一张能扫出别的内容的码都会蒙混过关。）
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))
from safe_mutation import mutate_sandbox  # noqa: E402
import make_qr  # noqa: E402

GATE_MARK = "真机自检入口码"


def find_line(text):
    for ln in text.splitlines():
        if GATE_MARK in ln:
            return ln.strip()
    return None


def run(sb):
    r = sb.run_python("tools/verify_site.py", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    line = find_line(out)
    return r.returncode, out, line


def gate_specific_failures(out):
    """只取与本判据相关的 FAIL 行（自检页 / 入口码）。"""
    return [ln.strip() for ln in out.splitlines()
            if "[FAIL]" in ln and ("自检" in ln or "入口码" in ln)]


def report(tag, rc, out, line, want_red, want_kw):
    """统一判定：行在不在、颜色对不对、有没有点名。

    刻意**不**断言总门禁 RESULT：沙箱只拷 site/tools/qr，仓根的 7 份治理件与 .git
    都不在里面，「交付治理件 0/7」必然判红（_qa/dbg_sandbox_verify.py 实测）。
    拿总门禁当基线，会把沙箱的构造缺陷误读成产品缺陷 —— 第一版就犯了这个错，
    现改为只断言「本判据相关 FAIL 为空」（见 A 用例）。
    """
    bad = []
    if line is None:
        bad.append("判据行未出现（可能整项没跑 = 静默失效）")
        return bad
    got_red = "[FAIL]" in line
    if got_red != want_red:
        bad.append("颜色不对：期望 %s 实得 %s（%s）" % (
            "FAIL" if want_red else "PASS", "FAIL" if got_red else "OK", line[:90]))
    if want_red and want_kw and want_kw not in line and want_kw not in out:
        bad.append("判红了但没点名 %r（归因不清）" % want_kw)
    if not bad:
        print("  [PASS] %s -> %s" % (tag, line[:110]))
    else:
        for b in bad:
            print("  [FAIL] %s：%s" % (tag, b))
    return bad


def main():
    fails = []
    # require_clean=False 是本仓 40+ 个 reverse_* 脚本的统一约定：
    # 沙箱只改临时副本，且 mutate_sandbox 的 finally 会逐文件 SHA256 核验真实工作区未变
    # （真变了会立刻报警），所以「工作区有未提交改动」不影响这里的安全性。
    with mutate_sandbox(require_clean=False, dirs=("site", "tools", "qr")) as sb:
        print("A 基线（不改动：7b 必须绿，且不得有本判据相关 FAIL）")
        rc, out, line = run(sb)
        fails += report("A", rc, out, line, want_red=False, want_kw=None)
        own = gate_specific_failures(out)
        if own:
            print("  [FAIL] A：基线里本判据自己判红：%s" % own[0][:110])
            fails.append("A 基线不干净")
        else:
            print("  [PASS] A：基线无本判据相关 FAIL（总门禁红仅因沙箱未拷治理件/.git，与本判据无关）")

        print("B 删自检页（必须红且点名自检页）")
        page = sb.path(os.path.join("site", "_device_probe.html"))
        os.remove(page)
        rc, out, line = run(sb)
        fails += report("B", rc, out, line, want_red=True, want_kw="自检页缺失")

        print("C 入口码漂移（换成指向别的 URL 的合法码，必须红）")
        # 重新生成一个**能正常解码**但内容不同的码：这才能证明判据真的读了像素
        other = "https://example.com/wrong-page"
        make_qr.make(other, sb.path(os.path.join("qr", "qr-device-probe.png")), box=10)
        ok, got = make_qr.verify(sb.path(os.path.join("qr", "qr-device-probe.png")), other)
        print("    （已确认替换码可解码且内容 == 目标错误 URL：%s）" % ok)
        rc, out, line = run(sb)
        fails += report("C", rc, out, line, want_red=True, want_kw="解码不等于")

        print("D 入口码缺失（必须红）")
        os.remove(sb.path(os.path.join("qr", "qr-device-probe.png")))
        rc, out, line = run(sb)
        fails += report("D", rc, out, line, want_red=True, want_kw="入口码缺失")

    print()
    if fails:
        print("RESULT: FAIL  反向验证未通过：")
        for f in fails:
            print("  -", f)
        return 1
    print("RESULT: PASS  4 项反向验证全过（基线绿 / 删页红 / 码漂移红 / 码缺失红）")
    print("关键：C 用「可正常解码但内容错误」的码，证明判据真的解码像素，而非只看文件存在。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
