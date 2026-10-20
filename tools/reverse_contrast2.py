
# -*- coding: utf-8 -*-
"""反向验证 contrast_audit：把 --fg-dim 的全部定义改成接近背景色。

上次失败原因：--fg-dim 在三处定义（44/1010/1019 行），只改一处会被后面的覆盖。
这次用正则替换所有定义。
"""
import os, re, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
CSS = os.path.join(WD, 'site/assets/css/main.css')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

st = ps('git status --porcelain site/assets/css/main.css')
if st.strip():
    print('工作区不干净，拒绝执行'); sys.exit(1)

orig = open(CSS, encoding='utf-8', newline='').read()
try:
    # 把所有 --fg-dim 定义改成几乎等于背景色 #0B0908
    broken = re.sub(r'--fg-dim:\s*[^;}]+', '--fg-dim:#12100E', orig)
    changed = broken != orig
    print('替换生效:', changed)
    open(CSS, 'w', encoding='utf-8', newline='').write(broken)
    r = subprocess.run([sys.executable, 'tools/contrast_audit.py'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=200)
    out = (r.stdout or '') + (r.stderr or '')
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'RESULT' in l or '不达标' in l or l.strip().startswith('- '):
            print('  ', l.strip()[:110])
finally:
    open(CSS, 'w', encoding='utf-8', newline='').write(orig)
    ps('git checkout -- site/assets/css/main.css')
    print()
    print('还原后状态:', ps('git status --porcelain site/assets/css/main.css') or '干净')
