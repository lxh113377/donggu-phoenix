# -*- coding: utf-8 -*-
'''反向验证：注入一个失败项，聚合判定必须 FAIL。

## 为什么必须验
聚合 runner 最经典的 bug 是「用一个失败被多数通过洗白」。
必须亲眼看到它判红，才能相信它。
'''
import hashlib, os, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
HTML = WD + r'\site\index.html'

b0 = hashlib.sha256(open(HTML,'rb').read()).hexdigest()
orig = open(HTML, encoding='utf-8', newline='').read()

try:
    # 注入永不触发的 reveal -> reveal_coverage_test 应 FAIL
    broken = orig.replace('</body>', '<div class="reveal" style="height:60px">测试</div></body>', 1)
    open(HTML, 'w', encoding='utf-8', newline='').write(broken)
    print('已注入永不触发的 reveal')
    r = subprocess.run([sys.executable, 'tools/run_browser_suite.py', '--fast'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=560)
    out = (r.stdout or '') + (r.stderr or '')
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'FAIL' in l or 'RESULT' in l or '通过' in l:
            print('  ', l.strip()[:90])
finally:
    open(HTML, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原:', b0 == hashlib.sha256(open(HTML,'rb').read()).hexdigest())