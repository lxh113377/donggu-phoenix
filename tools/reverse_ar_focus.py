
# -*- coding: utf-8 -*-
"""反向验证 ar_focus_test：破坏焦点恢复，应判红。

做法：临时注释掉 lastFocus.focus() 调用，跑测试，再还原。
用 git 保证可恢复（先确认工作区干净）。
"""
import os, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
JS = os.path.join(WD, 'site/assets/js/ar.js')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

st = ps('git status --porcelain site/assets/js/ar.js')
if st.strip():
    print('工作区不干净，中止:', st[:80])
    sys.exit(1)

orig = open(JS, encoding='utf-8', newline='').read()
try:
    broken = orig.replace(
        "    if (lastFocus && lastFocus.focus) {",
        "    if (false && lastFocus && lastFocus.focus) {"
    )
    assert broken != orig, '替换失败'
    open(JS, 'w', encoding='utf-8', newline='').write(broken)
    r = subprocess.run([sys.executable, 'tools/ar_focus_test.py'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=200)
    out = (r.stdout or '') + (r.stderr or '')
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'FAIL' in l or 'RESULT' in l or 'PASS]' in l:
            print('  ', l.strip()[:80])
finally:
    open(JS, 'w', encoding='utf-8', newline='').write(orig)
    ps('git checkout -- site/assets/js/ar.js')
    print()
    print('还原:', ps('git status --porcelain site/assets/js/ar.js') or '干净')
