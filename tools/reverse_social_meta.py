# -*- coding: utf-8 -*-
"""反向验证 social_meta_test。

## 修正记录（轮47）
第一版只用 replace(old, '', 1) 删身份串，结果判据仍 PASS。
原因：身份串在 index.html 出现 **2 次**（description 与 og:description），
replace 只改第一个（description），og:description 没变 → 判据当然 PASS。
→ 测试脚本的 bug，不是判据的 bug。

改为精确替换 og:description 整条 meta。
"""
import hashlib, re, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
HTML = WD + r'\site\index.html'

def sha():
    return hashlib.sha256(open(HTML,'rb').read()).hexdigest()

orig = open(HTML, encoding='utf-8', newline='').read()
b0 = sha()

def replace_og_desc(text, new_content):
    return re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                  r'\g<1>' + new_content + r'\g<2>', text, count=1)

cases = [
    ('A 去掉 og:description 身份', replace_og_desc(orig, '动态凤凰飞舞 × 畲族文化 × 东固非遗文创'),
     lambda t: t),
    ('B 尺寸声明改成 800x400', orig.replace('og:image:width" content="1200', 'og:image:width" content="800', 1),
     lambda t: t),
]

try:
    for label, broken, _ in cases:
        if broken == orig:
            print('[%s] 未产生变化，跳过' % label)
            continue
        open(HTML, 'w', encoding='utf-8', newline='').write(broken)
        r = subprocess.run([sys.executable, 'tools/social_meta_test.py'], cwd=WD,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        out = (r.stdout or '') + (r.stderr or '')
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fl[:2]:
            print('    ', f[:85])
finally:
    open(HTML, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原:', b0 == sha())