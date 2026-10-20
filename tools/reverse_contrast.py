
# -*- coding: utf-8 -*-
"""反向验证 contrast_audit：把正文颜色改成几乎同色，必须判红。

用 safe_mutation 沙箱改 CSS，然后跑工具。
注意：工具访问的是 http://127.0.0.1:8791 服务的真实目录，
沙箱改的是副本 —— 所以这里改为「直接改真实文件 → 测 → 立即还原」，
但用 git 保证可恢复（当前工作区干净）。
"""
import subprocess, sys, time, os

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
CSS = 'site/assets/css/main.css'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

# 确认工作区干净（可安全还原）
st = ps('git status --porcelain site/assets/css/main.css')
if st.strip():
    print('工作区不干净，拒绝执行破坏性测试:', st[:100])
    sys.exit(1)

orig = open(os.path.join(WD, CSS), encoding='utf-8').read()
try:
    # 把正文色改成与背景几乎相同
    broken = orig.replace('color:var(--fg-dim)', 'color:#151210')
    if broken == orig:
        # 换一个目标
        broken = orig.replace('--fg-dim:', '--fg-dim:#151210;/*', 1)
    open(os.path.join(WD, CSS), 'w', encoding='utf-8', newline='').write(broken)
    r = subprocess.run([sys.executable, 'tools/contrast_audit.py'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    out = (r.stdout or '') + (r.stderr or '')
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'RESULT' in l or '不达标' in l or l.strip().startswith('- '):
            print('  ', l.strip())
finally:
    open(os.path.join(WD, CSS), 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原，工作区状态:', ps('git status --porcelain site/assets/css/main.css') or '干净')
