# -*- coding: utf-8 -*-
'''反向验证 ledger_id_test：造撞号 / 造空洞 / 造缺状态，必须判红。'''
import hashlib, shutil, subprocess, sys, os

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
LED = os.path.join(WD, 'memory', '09-upgrade-ledger.md')
BAK = LED + '.revbak'

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

orig = open(LED, encoding='utf-8', newline='').read()
b0 = sha(LED)
shutil.copy(LED, BAK)

def run():
    r = subprocess.run([sys.executable, 'tools/ledger_id_test.py'], cwd=WD, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')][:1]
    return r.returncode, (res[-1] if res else '(无)'), fl

try:
    # A 造撞号：把 U-147 那行改成 U-146（与上一行同号）
    broken = orig.replace('| U-147 |', '| U-146 |', 1)
    assert broken != orig
    open(LED, 'w', encoding='utf-8', newline='').write(broken)
    rc, res, fl = run()
    print('[A 造撞号] rc=%d %s' % (rc, res[:40]))
    for f in fl: print('     ', f[:88])
    open(LED, 'w', encoding='utf-8', newline='').write(orig)

    # B 造空洞：删掉 U-140 整行
    ls = orig.split(chr(10))
    out2 = [l for l in ls if not l.startswith('| U-140 |')]
    assert len(out2) < len(ls)
    open(LED, 'w', encoding='utf-8', newline='').write(chr(10).join(out2))
    rc, res, fl = run()
    print('[B 造空洞] rc=%d %s' % (rc, res[:40]))
    for f in fl: print('     ', f[:88])
    open(LED, 'w', encoding='utf-8', newline='').write(orig)

    # C 造缺状态：把某行状态列清空
    tgt = [l for l in ls if l.startswith('| U-141 |')][0]
    cells = tgt.split('|')
    cells[5] = '  '
    broken = orig.replace(tgt, '|'.join(cells), 1)
    assert broken != orig
    open(LED, 'w', encoding='utf-8', newline='').write(broken)
    rc, res, fl = run()
    print('[C 造缺状态] rc=%d %s' % (rc, res[:40]))
    for f in fl: print('     ', f[:88])
    open(LED, 'w', encoding='utf-8', newline='').write(orig)
finally:
    shutil.copy(BAK, LED)
    os.remove(BAK)
    print()
    print('台账已还原:', b0 == sha(LED))