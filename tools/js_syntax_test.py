# -*- coding: utf-8 -*-
"""tools/js_syntax_test.py —— 站点与云函数 JS 语法判据（CI 可跑）。

## 为什么需要（轮96，一手教训）
本轮我把 main.js 改出 SyntaxError（在 JS 字符串里插表达式时漏了续接引号），
main.js 整个不执行、.merch-grid 一张卡都不渲染 —— 页面等于坏了。
但当时 36 条 CI 判据全部照绿：
  · verify_site.py       PASS（它查文件存在性/引用完整性，不解析 JS）
  · safe_script_test.py  PASS（它查脚本是否改写站点文件）
  · 浏览器判据读不到数据时按设计返回 SKIP（避免环境问题误判产品）
于是「页面坏」和「环境不可用」在结果里长得一样。
实测证据：故意把 main.js 改坏，verify_site 与 safe_script_test 都 PASS。
「JS 全坏而 CI 全绿」是真实缺口，这条纯静态判据堵住它。

## 实现：按扩展名让 node 自己决定解析模式
把源码写成临时文件，用 .mjs（ESM）与 .cjs（CJS）各跑一次 node --check，
任一通过即语法合法。
  · 不用 --input-type，也不用 --check 加短横线从 stdin 读。
    第一版正是这么写的，本机 node 24 可用，CI 的 node 20 判红
    （run 39609685793，22 秒即失败）。
    我刚在 workflow 注释里写过「本机装了依赖所以本地全绿，CI 干净环境判红」，
    下一轮就亲手踩了同一条 —— 教训写在注释里不等于长进脑子里。
  · 双模式都试是必要的：只按 ESM 检会把 sloppy-CJS 才合法的写法
    （八进制字面量 0755、with 语句）误报为坏。
  · 扩展名决定模式是 node 长期稳定的公开行为，版本不敏感。

## 环境依赖必须显式声明
node 缺失时返回 FAIL（不是 SKIP）—— SKIP 会让「判据没跑」伪装成
「判据通过」，正是本判据要修的那种病。CI 已加 setup-node 保证 node 存在。
"""
import os
import shutil
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_ROOTS = [
    os.path.join(BASE, 'site'),
    os.path.join(BASE, 'functions'),
]
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


def check_file(node, path, workdir):
    """返回 (ok, mode, msg)。.mjs 与 .cjs 各检一次，任一通过即合法。"""
    src = open(path, 'rb').read()
    last_err = ''
    for ext, label in (('mjs', 'ESM'), ('cjs', 'CJS')):
        tmp = os.path.join(workdir, 'probe.' + ext)
        with open(tmp, 'wb') as fh:
            fh.write(src)
        try:
            r = subprocess.run([node, '--check', tmp],
                               capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            return False, label, 'node --check 超时'
        if r.returncode == 0:
            return True, label, ''
        last_err = (r.stderr or b'').decode('utf-8', 'replace')
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
        print('  - 找不到 node。本判据故意不返回 SKIP：'
              'SKIP 会让「判据没跑」伪装成「判据通过」。CI 已配 setup-node。')
        return 1

    files = collect_js()
    if not files:
        print('RESULT: FAIL  未扫到任何 JS 文件（扫描面失效，不算通过）')
        return 1

    ver = subprocess.run([node, '--version'], capture_output=True,
                         timeout=30).stdout.decode().strip()
    print('node %s，受检 JS %d 个' % (ver, len(files)))
    workdir = tempfile.mkdtemp(prefix='jssyn_')
    bad = []
    try:
        for f in files:
            ok, mode, msg = check_file(node, f, workdir)
            rel = os.path.relpath(f, BASE).replace('\\', '/')
            if ok:
                print('  [ok] %-46s (%s)' % (rel, mode))
            else:
                print('  [X ] %-46s %s' % (rel, msg[:110]))
                bad.append((rel, msg))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

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
