# -*- coding: utf-8 -*-
'''反向验证 merch_image_fill_test（修正版）。

## 上一次的错误
破坏点在「旧的」.merch-item.is-feature .merch-shot img 规则块（文件中部），
但文件**末尾的修复块**优先级更高（同特异性、后写者胜），把破坏覆盖了。
→ 不是缓存问题，是选错了破坏位置。

## 正确做法
破坏**最后一块**（末尾 MERCH-FEATURE-FIX 里那条）。
'''
import hashlib, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
CSS = WD + r'\site\assets\css\main.css'

def sha(): return hashlib.sha256(open(CSS,'rb').read()).hexdigest()

orig = open(CSS, encoding='utf-8', newline='').read()
b0 = sha()

# 定位最后一个 .merch-item.is-feature .merch-shot img{ 块
marker = '.merch-item.is-feature .merch-shot img{'
idx = orig.rfind(marker)
print('最后一块位置:', idx)

try:
    if idx < 0:
        print('未找到')
    else:
        j = orig.find('}', idx)
        broken = orig[:j] + '  max-height:150px;max-width:76%;\n' + orig[j:]
        assert broken != orig, '替换未产生变化'
        open(CSS, 'w', encoding='utf-8', newline='').write(broken)
        print('已破坏最后一块（图片高度压回 150px）')
        r = subprocess.run([sys.executable, 'tools/merch_image_fill_test.py'], cwd=WD,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        out = (r.stdout or '') + (r.stderr or '')
        print('退出码:', r.returncode)
        for l in out.splitlines():
            if 'RESULT' in l or '填充率' in l or l.strip().startswith('- '):
                print('  ', l.strip()[:90])
finally:
    open(CSS, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原:', b0 == sha())