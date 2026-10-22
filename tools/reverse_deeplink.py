# -*- coding: utf-8 -*-
'''反向验证：临时移除 hash 修复，DEEPLINK 判据应判红。'''
import hashlib, os, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
JS = os.path.join(WD, 'site/assets/js/ar.js')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

st = ps('git status --porcelain site/assets/js/ar.js')
print('工作区状态:', st or '有未提交改动（预期，因为本轮刚修）')

orig = open(JS, encoding='utf-8', newline='').read()
try:
    # 把修复注释掉：恢复成原来的 if (!id) { return; }
    broken = orig.replace('if (!id) {', 'if (!id) { return; /*reverted*/', 1)
    if broken == orig:
        print('未找到目标')
    else:
        # 需要把后面的块也注释掉，简单做法：让 _closingByHash 永远 false 且跳过 close
        broken = broken.replace('if (state.open && !_closingByHash) {', 'if (false) {', 1)
        open(JS, 'w', encoding='utf-8', newline='').write(broken)
        print('已临时移除修复')
        r = subprocess.run([sys.executable, 'tools/ar_e2e_test.py'], cwd=WD,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=200)
        out = (r.stdout or '') + (r.stderr or '')
        print('退出码:', r.returncode)
        for l in out.splitlines():
            if '深链接' in l or 'RESULT' in l or l.strip().startswith('- '):
                print('  ', l.strip()[:90])
finally:
    open(JS, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原')