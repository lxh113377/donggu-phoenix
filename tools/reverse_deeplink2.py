# -*- coding: utf-8 -*-
'''重做反向验证：用合法的破坏方式（只禁用 close 调用）。

## 上次的错误
把 `if (!id) {` 替换成 `if (!id) { return;` 会导致语法错误，
浏览器加载失败 → 用的是旧缓存 JS → 判据自然 PASS。

## 正确破坏方式
只把 `if (state.open && !_closingByHash) {` 改成 `if (false) {`，
语法仍然合法，但功能被禁用。
'''
import os, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
JS = os.path.join(WD, 'site/assets/js/ar.js')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

orig = open(JS, encoding='utf-8', newline='').read()
try:
    old = 'if (state.open && !_closingByHash) {'
    new = 'if (false) {'
    if old not in orig:
        print('未找到目标')
    else:
        broken = orig.replace(old, new, 1)
        open(JS, 'w', encoding='utf-8', newline='').write(broken)
        # 验证语法合法
        r0 = subprocess.run(['node', '--check', JS], capture_output=True, text=True, encoding='utf-8', errors='replace')
        print('破坏后语法检查:', 'OK' if r0.returncode == 0 else 'FAIL')
        if r0.returncode == 0:
            r = subprocess.run([sys.executable, 'tools/ar_e2e_test.py'], cwd=WD,
                               capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=250)
            out = (r.stdout or '') + (r.stderr or '')
            print('退出码:', r.returncode)
            for l in out.splitlines():
                if '深链接' in l or 'RESULT' in l or l.strip().startswith('- '):
                    print('  ', l.strip()[:90])
finally:
    open(JS, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原')