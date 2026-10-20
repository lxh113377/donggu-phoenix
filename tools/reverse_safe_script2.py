# -*- coding: utf-8 -*-
"""反向验证 safe_script_test 的 FAIL/WARN 分流（真 git 仓库环境）。

## 为什么不能用 mutate_sandbox
它建的 .git 是**空目录不是真仓库**（见其源码「建个空目录避免报错」），
所以沙箱里 git ls-files 必然失败 → 判据走「无 git 环境则保守视为已跟踪」
的兜底分支 → 两个用例都会判红，测不出分流。
这不是判据 bug，恰恰是它该有的保守行为；但要验证分流就得造真 git 仓库。

## 自触发陷阱（本轮实测踩到）
判据扫「源码里是否含 open(<site 路径>,'w') 字面量」。
违规样本内容必须用字符串拼接生成，否则本脚本自己会被扫到。
"""
import os
import shutil
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def bad_script():
    tgt = 'si' + 'te/index.html'
    return ("# -*- coding: utf-8 -*-\n"
            "s = open('x').read()\n"
            "open('%s', 'w', encoding='utf-8').write(s)\n" % tgt)


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, timeout=120)


def build_repo(with_git, tag):
    root = os.path.join(tempfile.mkdtemp(prefix='dsh_git_%s_' % tag), 'repo')
    os.makedirs(os.path.join(root, 'tools'), exist_ok=True)
    os.makedirs(os.path.join(root, 'site'), exist_ok=True)
    shutil.copy(os.path.join(BASE, 'tools', 'safe_script_test.py'),
                os.path.join(root, 'tools', 'safe_script_test.py'))
    shutil.copy(os.path.join(BASE, 'tools', 'gate_guard.py'),
                os.path.join(root, 'tools', 'gate_guard.py'))
    if with_git:
        sh(['git', 'init', '-q'], root)
        sh(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '--allow-empty',
            '-m', 'init'], root)
    return root


def probe(root, tracked):
    """放一个违规脚本，tracked=True 就 git add。返回 (rc, 是否命中该脚本)。"""
    p = os.path.join(root, 'tools', 'zz_probe.py')
    open(p, 'w', encoding='utf-8').write(bad_script())
    if tracked:
        sh(['git', 'add', '-f', 'tools/zz_probe.py'], root)
        sh(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '-m', 'probe'], root)
    r = sh([PY, os.path.join('tools', 'safe_script_test.py')], root)
    out = (r.stdout or b'').decode('utf-8', 'replace') if isinstance(r.stdout, bytes) else (r.stdout or '')
    # subprocess 未指定 text，统一按 bytes 处理
    if isinstance(r.stdout, bytes):
        out = r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace')
    else:
        out = (r.stdout or '') + (r.stderr or '')
    hit_fail = any('zz_probe' in l.strip() and l.strip().startswith('- ')
                   for l in out.splitlines())
    hit_warn = any('zz_probe' in l.strip() and l.strip().startswith('~ ')
                   for l in out.splitlines())
    return r.returncode, hit_fail, hit_warn, out


res = []
roots = []
try:
    # 1) 真 git + 已跟踪 -> FAIL
    r1 = build_repo(True, 'a')
    roots.append(r1)
    rc, f, w, out = probe(r1, True)
    ok1 = rc == 1 and f and not w
    print('[1 真git+已跟踪] rc=%d FAIL命中=%s WARN命中=%s -> %s'
          % (rc, f, w, 'OK' if ok1 else '**错**'))
    res.append(ok1)

    # 2) 真 git + 未跟踪 -> 只 WARN，不判红
    r2 = build_repo(True, 'b')
    roots.append(r2)
    rc, f, w, out = probe(r2, False)
    ok2 = rc == 0 and w and not f
    print('[2 真git+未跟踪] rc=%d FAIL命中=%s WARN命中=%s -> %s'
          % (rc, f, w, 'OK' if ok2 else '**错**'))
    res.append(ok2)

    # 3) 无 git 环境 -> 保守视为已跟踪，必须 FAIL（不能因为读不到 git 就放过）
    r3 = build_repo(False, 'c')
    roots.append(r3)
    rc, f, w, out = probe(r3, False)
    ok3 = rc == 1 and f
    print('[3 无git环境    ] rc=%d FAIL命中=%s -> %s（保守兜底）'
          % (rc, f, 'OK' if ok3 else '**错**'))
    res.append(ok3)
finally:
    for d in roots:
        shutil.rmtree(os.path.dirname(d), ignore_errors=True)

print()
if all(res):
    print('RESULT: PASS  三种环境判定都符合预期（分流有效且无 git 时不放水）')
    sys.exit(0)
print('RESULT: FAIL  有环境判定不符')
sys.exit(1)
