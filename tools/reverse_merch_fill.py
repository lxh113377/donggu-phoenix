# -*- coding: utf-8 -*-
"""反向验证 merch_image_fill_test（dominant 版）。

## 破坏点必须打在「最终生效」的规则上（轮48 教训）
文件末尾 MERCH-FEATURE-FIX 里有 .merch-item.is-feature .merch-shot img{...}，
它覆盖了中部旧规则。破坏要打在最后这一块。

## 新判据自带 cacheBust
measure() 里注入带时间戳的 <link>，绕开 HTTP/SW 缓存，
所以撤销 CSS 后能读到真实变化（轮48 曾因缓存误判）。
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

marker = '.merch-item.is-feature .merch-shot img{'
idx = orig.rfind(marker)

try:
    if idx < 0:
        print('未找到末块，判据可能已改名')
    else:
        j = orig.find('}', idx)
        # 把末块内容替换成旧的 150px 约束（合法 CSS，但禁用放大）
        broken = orig[:idx] + marker + '\n  width:auto;height:auto;max-width:76%;max-height:150px;\n' + orig[j:]
        assert broken != orig
        open(CSS, 'w', encoding='utf-8', newline='').write(broken)
        print('已把末块压回 max-height:150px')
        r = subprocess.run([sys.executable, 'tools/merch_image_fill_test.py'], cwd=WD,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=200)
        out = (r.stdout or '') + (r.stderr or '')
        print('退出码:', r.returncode)
        for l in out.splitlines():
            if 'dominant' in l or 'RESULT' in l or l.strip().startswith('- '):
                print('  ', l.strip()[:95])
finally:
    open(CSS, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原:', b0 == sha())
