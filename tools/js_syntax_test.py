# -*- coding: utf-8 -*-
"""tools/js_syntax_test.py —— 站点与云函数 JS 语法判据（CI 可跑）。

## 为什么需要（轮96，一手教训）
本轮我把 main.js 改出 SyntaxError（在 JS 字符串里插表达式时漏了续接引号），
main.js **整个不执行**、.merch-grid 一张卡都不渲染 —— 页面等于坏了。
但当时 36 条 CI 判据全部照绿：
  · verify_site.py       PASS（它查文件存在性/引用完整性，不解析 JS）
  · safe_script_test.py  PASS（它查脚本是否改写站点文件）
  · merch_image_fill_test 报「无数据」-> 返回 0 -> 也算绿
实测证据见 _qa/check_js_syntax_gate.py：故意把 main.js 改坏，
两条判据都 PASS。**「JS 全坏而 CI 全绿」是真实存在的缺口。**

浏览器判据能间接发现（读不到数据），但它们依赖 daemon/环境，
读不到数据时按设计返回 SKIP 而非 FAIL（避免环境问题误判产品），
于是「页面坏」和「环境不可用」在结果里长得一样。
语法判据是纯静态的，不需要浏览器，能堵住这个缝。

## 判据
对 site/ 的 JS 与 functions/ 的云函数 JS，逐个用 node --check 解析：
  · 先按 --input-type=module 试（ESM，本站与 CF Functions 都是 ESM）
  · 失败再按 --input-type=script 试（CJS，兼容老写法）
  · 两种模式都报 SyntaxError 才算真坏；任一通过即合法
「两种模式都试」是必要的：只按 module 检会把合法的 CJS 误报为坏。

## 环境依赖必须显式声明
node 缺失时本判据返回 FAIL（不是 SKIP）——
因为 SKIP 会让「判据没跑」伪装成「判据通过」，正是本轮要修的病。
CI 里已加 setup-node 保证 node 存在。
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_ROOTS = [
    os.path.join(BASE, 'site'),
    os.path.join(BASE, 'functions'),
]
# 图片/字体等非代码目录不遍历；assets 单独放行 js 子目录
PRUNE = {'.git', 'node_modules', 'img', 'fonts', 'data'}


def collect_js():
    out = []
    for root in SCAN_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in PRUNE and not d.startswith('.')]
            for f in sorted(files):
                if f.endswith('.js'):
                    out.append(os.path.join(dirpath, f))
    return sorted(set(out))


def node_bin():
    for name in ('node', 'node.exe'):
        try:
            r = subprocess.run([name, '--version'], capture_output=True,
                               timeout=30)
            if r.returncode == 0:
                return name
        except Exception:
            continue
    return None


def check_file(node, path):
    """返回 (ok, mode, msg)。两种解析模式都试，任一通过即合法。"""
    src = open(path, 'rb').read()
    last_err = ''
    # node 的 --input-type 只接受 module / commonjs（'script' 是非法值，
    # 会让第二模式变成从未生效的空壳 —— 轮96 实测踩过）
    for mode in ('module', 'commonjs'):
        try:
            r = subprocess.run([node, '--input-type=' + mode, '--check', '-'],
                               input=src, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            return False, mode, 'node --check 超时'
        if r.returncode == 0:
            return True, mode, ''
        err = (r.stderr or b'').decode('utf-8', 'replace')
        last_err = err
        # 非语法类错误（参数不被支持等）不该判红，交上层区分
        if 'SyntaxError' not in err:
            tail = [l.strip() for l in err.splitlines() if l.strip()]
            return False, mode, (tail[-1][:160] if tail else '未知错误')
    tail = [l.strip() for l in last_err.splitlines() if l.strip()]
    msg = ''
    for l in tail:
        if 'SyntaxError' in l:
            msg = l
            break
    if not msg:
        msg = tail[-1] if tail else '解析失败'
    return False, '-', msg[:200]


def main():
    node = node_bin()
    if not node:
        print('RESULT: FAIL')
        print('  - 找不到 node。本判据**故意不返回 SKIP**：'
              'SKIP 会让「判据没跑」伪装成「判据通过」（轮96 修的正是这个病）。'
              'CI 已配 setup-node；本地跑请先装 node。')
        return 1

    files = collect_js()
    if not files:
        print('RESULT: FAIL  未扫到任何 JS 文件（扫描面失效，不算通过）')
        return 1

    ver = subprocess.run([node, '--version'], capture_output=True,
                         timeout=30).stdout.decode().strip()
    print('node %s，受检 JS %d 个' % (ver, len(files)))
    bad = []
    for f in files:
        ok, mode, msg = check_file(node, f)
        rel = os.path.relpath(f, BASE).replace('\\', '/')
        if ok:
            print('  [ok] %-46s (%s)' % (rel, mode))
        else:
            print('  [X ] %-46s %s' % (rel, msg[:110]))
            bad.append((rel, msg))

    print()
    if bad:
        print('RESULT: FAIL')
        for rel, msg in bad:
            print('  - %s：%s' % (rel, msg[:150]))
        print('  - JS 语法错误会让整个文件不执行：main.js 坏 = 页面数据全不渲染，'
              'sw.js 坏 = 离线缓存失效，functions 坏 = 后台无数据。')
        return 1
    print('RESULT: PASS  %d 个 JS 文件语法全部可解析' % len(files))
    return 0


if __name__ == '__main__':
    sys.exit(main())
