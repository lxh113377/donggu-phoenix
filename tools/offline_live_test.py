# -*- coding: utf-8 -*-
"""tools/offline_live_test.py —— 线上真实环境「断网仍可用」判据（验收判据 2 的复验）。

为什么必须重跑
  docs/对标分析报告.md §9.3 那次离线复验是 2026-10-20 做的。之后站点从 35 个文件
  长到 56 个、字体换成自托管 220KB、新增后台与真机自检页 —— PRECACHE 清单变了、
  体积逼近险线，而「现场断网仍能开」是**交付承诺**（01-goal 验收判据 2）。
  承诺过期不重验 = 拿两年前的体检报告说今天健康。

口径
  同一个 chrome 实例、同一个 user-data-dir 走完 联网预热 -> 断网重载 -> 恢复，
  中间绝不重启（SW 的 CacheStorage 落在 profile 里，重启就前功尽弃）。
  断网用 CDP Network.emulateNetworkConditions(offline:true) —— 浏览器侧与拔网线等价，
  且能自动跑（真拔网线需要人，违反 no-manual-steps）。

诚实边界
  本机到 GitHub Pages 是跨境链路，与东固现场当地网络不同；本判据证的是
  「SW 缓存策略本身成立」，不证「现场一定快」。

用法
  python tools/offline_live_test.py            # 测线上两面
  python tools/offline_live_test.py --local    # 测本地同源服务（对照）
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))
import preflight_device_test as G  # noqa: E402  复用 find_chrome / launch_chrome

DRIVER = os.path.join(BASE, "tools", "offline_live.mjs")

TARGETS = [
    ("github-pages", "https://lxh113377.github.io/donggu-phoenix/"),
    ("cloudflare", "https://donggu-phoenix.pages.dev/"),
]


def run_one(url, extra_args=None):
    proc, dport, udd = G.launch_chrome(G.find_chrome(), extra_args)
    try:
        if not dport:
            return {"ok": False, "error": "chrome 未开出调试端口"}
        node = shutil_which_node()
        if not node:
            return {"ok": False, "error": "找不到 node"}
        r = subprocess.run([node, DRIVER, str(dport), url],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        m = re.search(r"__OL_JSON__(.*)", r.stdout or "")
        if not m:
            return {"ok": False, "error": "驱动无 JSON 输出；stderr=" + (r.stderr or "")[-300:]}
        try:
            return json.loads(m.group(1))
        except Exception as e:
            return {"ok": False, "error": "JSON 解析失败 %s" % e}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "驱动超时 300s"}
    finally:
        G.stop_chrome(proc, udd)


def shutil_which_node():
    import shutil
    return shutil.which("node") or shutil.which("node.exe")


def judge(d):
    """返回违规清单。断网后必须：首屏出得来、引擎在、区块齐、AR 能推进、零报错。"""
    # 一律返回四元组 (violations, warm, offline, sw)。
    # 返回形状随分支变化，调用方就得写一堆 isinstance 去猜 —— 那是 bug 温床。
    v = []
    if not d.get("ok"):
        return ["无读数：%s" % d.get("error")], {}, {}, {}
    ph = d.get("phases") or {}
    warm = ph.get("warm") or {}
    off = ph.get("offline") or {}
    if not off:
        return ["断网阶段无读数（可能整页没起来）"], warm, {}, d.get("sw") or {}
    sw = d.get("sw") or {}
    if not sw.get("count"):
        v.append("SW 未注册（预热阶段就没装上，断网必挂）：%s" % json.dumps(sw, ensure_ascii=False)[:90])
    elif not sw.get("entries"):
        v.append("SW 缓存条目为 0：%s" % json.dumps(sw, ensure_ascii=False)[:90])
    if off.get("fcp") is None:
        v.append("断网后 FCP 取不到（首屏没画出来）")
    elif off["fcp"] > 3000:
        v.append("断网后 FCP %sms > 3000ms" % off["fcp"])
    if not off.get("ready"):
        v.append("断网后 __site.ready 为假（引擎未初始化）")
    if not off.get("particles"):
        v.append("断网后粒子数为 0")
    if (off.get("merch") or 0) < 8:
        v.append("断网后文创 %s 件 < 8" % off.get("merch"))
    if (off.get("arCards") or 0) != 3:
        v.append("断网后 AR 卡 %s != 3" % off.get("arCards"))
    ar = off.get("ar") or {}
    if ar.get("err"):
        v.append("断网后 AR 打开失败：%s" % ar["err"])
    elif not ar.get("moved"):
        v.append("断网后 AR 进度未推进（t1=%s t2=%s）" % (ar.get("t1"), ar.get("t2")))
    errs = off.get("errors") or []
    if errs:
        v.append("断网后页面报错 %d 条：%s" % (len(errs), " | ".join(errs)[:160]))
    return v, warm, off, sw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(DRIVER):
        print("RESULT: FAIL  驱动缺失 tools/offline_live.mjs")
        return 1
    if not G.find_chrome():
        print("RESULT: SKIP  找不到 chrome.exe")
        return 0

    targets = TARGETS
    httpd = port = None
    if args.local:
        httpd, port = G.start_server()
        targets = [("local", "http://%s:%d/site/index.html" % (G.TEST_HOST, port))]

    fails, rows = [], []
    try:
        for name, url in targets:
            print()
            print("--- %s  %s ---" % (name, url))
            d = run_one(url)
            v, warm, off, sw = judge(d)
            if True:
                print("  SW: %s" % json.dumps(sw, ensure_ascii=False)[:150])
                print("  预热  FCP=%sms 传输=%sKB 粒子=%s merch=%s ar=%s" % (
                    warm.get("fcp"), warm.get("transferKB"), warm.get("particles"),
                    warm.get("merch"), (warm.get("ar") or {}).get("moved")))
                print("  断网  FCP=%sms 传输=%sKB 粒子=%s merch=%s ar=%s loadType=%s" % (
                    off.get("fcp"), off.get("transferKB"), off.get("particles"),
                    off.get("merch"), (off.get("ar") or {}).get("moved"), off.get("loadType")))
                for x in v:
                    print("  [FAIL] " + x)
                if v:
                    fails.append("%s：%d 条违规" % (name, len(v)))
                else:
                    print("  [PASS] 断网后首屏/引擎/区块/AR 推进全部成立且零报错")
                rows.append((name, off.get("fcp"), off.get("transferKB")))
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()

    print()
    if fails:
        print("RESULT: FAIL  线上断网复验未通过")
        for f in fails:
            print("  -", f)
        return 1
    print("RESULT: PASS  %d 个部署面断网后均可完整使用（含 AR 推进）" % len(rows))
    print("口径：CDP offline（浏览器侧等价拔网线）；证的是 SW 缓存策略成立，不证现场一定快。")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, BASE)   # 顶部只加了 tools/，tools.gate_stamp 需要仓库根在路径上
    from tools.gate_stamp import record
    _t0 = time.time()
    _rc = main()
    record(__file__, {0: "PASS", 1: "FAIL"}.get(_rc, "SKIP"), time.time() - _t0)
    sys.exit(_rc)
