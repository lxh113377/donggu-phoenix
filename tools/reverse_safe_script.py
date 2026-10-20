# -*- coding: utf-8 -*-
'''反向验证 safe_script_test：临时造一个原地写真实文件的脚本。'''
import os, subprocess, sys

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
BAD = os.path.join(WD, '_qa', '_tmp_offender.py')

code = ("# -*- coding: utf-8 -*-" + chr(10) +
        "s = open('site/assets/css/main.css', 'w', encoding='utf-8')" + chr(10) +
        "s.write('broken')" + chr(10) +
        "s.close()" + chr(10))

try:
    open(BAD, 'w', encoding='utf-8').write(code)
    r = subprocess.run([sys.executable, 'tools/safe_script_test.py'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    out = (r.stdout or '') + (r.stderr or '')
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'RESULT' in l or l.strip().startswith('- ') or '检查' in l:
            print('  ', l.strip()[:100])
finally:
    if os.path.exists(BAD):
        os.remove(BAD)
    print()
    print('临时脚本已删除:', not os.path.exists(BAD))