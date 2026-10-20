# -*- coding: utf-8 -*-
"""反向验证 touch_target_test：撤销滑块命中区修复，必须判红。

破坏点打在文件末尾 TOUCH-SLIDER-FIX 块（最终生效的那条，轮48 教训）。
"""
import hashlib
import subprocess
import sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
CSS = WD + r'\site\assets\css\main.css'


def sha():
    return hashlib.sha256(open(CSS, 'rb').read()).hexdigest()


orig = open(CSS, encoding='utf-8', newline='').read()
b0 = sha()

marker = '.carve-slider{'
idx = orig.rfind(marker)

try:
    if idx < 0:
        print('未找到修复块')
    else:
        j = orig.find('}', idx)
        # 把命中区高度改回 3px（合法 CSS，但禁用修复）
        broken = orig[:idx] + '.carve-slider{\n  height:3px;\n' + orig[j:]
        assert broken != orig
        open(CSS, 'w', encoding='utf-8', newline='').write(broken)
        print('已把滑块命中区压回 3px')
        r = subprocess.run([sys.executable, 'tools/touch_target_test.py'], cwd=WD,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=400)
        out = (r.stdout or '') + (r.stderr or '')
        print('退出码:', r.returncode)
        for l in out.splitlines():
            if '小于' in l or 'RESULT' in l or l.strip().startswith('- '):
                print('  ', l.strip()[:95])
finally:
    open(CSS, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原:', b0 == sha())
