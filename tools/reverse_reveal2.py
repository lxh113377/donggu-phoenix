# -*- coding: utf-8 -*-
'''反向验证 reveal_coverage_test：页脚前插入永不触发的 reveal。

## 注意
测试跑的是 http://127.0.0.1:8791，服务的是真实目录，
所以注入必须落到真实文件，跑完还原。
'''
import hashlib, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
HTML = WD + r'\site\index.html'

def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()

orig = open(HTML, encoding='utf-8', newline='').read()
b0 = hashlib.sha256(open(HTML,'rb').read()).hexdigest()

try:
    broken = orig.replace('</body>', '<div class="reveal" style="height:60px">测试永不触发</div></body>', 1)
    if broken == orig:
        print('未找到 </body>')
    else:
        open(HTML, 'w', encoding='utf-8', newline='').write(broken)
        r = subprocess.run([sys.executable, 'tools/reveal_coverage_test.py'], cwd=WD,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        out = (r.stdout or '') + (r.stderr or '')
        print('退出码:', r.returncode)
        for l in out.splitlines():
            if '未触发' in l or 'RESULT' in l or l.strip().startswith('- '):
                print('  ', l.strip()[:80])
finally:
    open(HTML, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('真实文件已还原:', b0 == hashlib.sha256(open(HTML,'rb').read()).hexdigest())