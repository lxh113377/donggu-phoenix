# -*- coding: utf-8 -*-
# tools/reverse_suite_status.py
# 反向验证 run_browser_suite 的活性判定（轮117）。
#
# needs_daemon() 决定判据被标 RUNNABLE 还是 NEEDS-DAEMON，直接决定
# 「哪些维度算有覆盖」。它误判，读数就是假的：
#   误判成 DEAD（旧版真实发生）：ar_playback_test 轮108 已换 CDP、
#   实跑 rc=0 有 RESULT: PASS，却因 docstring 为解释旧版问题写了命令名、
#   且 CDP 版不含 headless=new，两条件同时命中，永久判 DEAD。
#   误判成 RUNNABLE（本轮修第一版时真实发生）：漏掉 ps('命令名 open') 形态，
#   12 条实际跑不动的判据被算进可跑 —— 统计层面又造一次假通过。
#
# 判据 6 类样本：A docstring 提及->非依赖 B 行内注释->非依赖
# C ps 真调用->依赖 D subprocess 列表->依赖 E 真调用+headless=new->依赖
# F 完全不含->非依赖
#
# 样本用 CMD = 'agent' + '-browser' 拼接构造：本文件要把真实性喂给被测
# 函数，但 browser_test_lint 按「引号紧跟命令名」认定浏览器测试，写成
# 字面量会被误判成浏览器测试。拼接后语义不变、源码不出现该形态。
import importlib.util
import io
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

_p = os.path.join('tools', 'run_browser_suite.py')
_spec = importlib.util.spec_from_file_location('rbs', _p)
rbs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rbs)

CMD = 'agent' + '-browser'
Q = chr(34)   # 双引号，避免源码出现需要转义的引号串

CASES = [
    ('A docstring 提及',
     'def f():' + chr(10) + '    ' + Q*3 + '旧版依赖 ' + CMD + '，不可用' + Q*3 + chr(10) + '    return 1',
     False),
    ('B 行内注释提及',
     'x = 1  # 以前用 ' + CMD + ' 跑',
     False),
    ('C ps 真调用',
     'ps(' + Q + CMD + ' open ' + Q*2 + 'http://127.0.0.1/' + Q*2 + ')' + Q + ')',
     True),
    ('D subprocess 列表调用',
     'subprocess.run([' + Q + CMD + Q + ', ' + Q + 'open' + Q + '])',
     True),
    ('E 真调用 + headless=new',
     'ps(' + Q + CMD + ' open x' + Q + ')  # 启动参数 headless=new',
     True),
    ('F 完全不含',
     'import os' + chr(10) + 'print(1)',
     False),
    # 轮118 新增分支：已改用 ab_compat 兼容层的判据不再依赖 daemon。
    # 它源码里仍保留 AB.run('agent-browser ...') 的字面形态（兼容层输入协议），
    # 若不认 ab_compat，会把已迁移的判据继续判成 NEEDS-DAEMON（迁移白做）。
    ('G 用了 ab_compat 兼容层',
     'from ab_compat import AbSession' + chr(10)
     + 'AB = AbSession()' + chr(10)
     + 'AB.run(' + Q + CMD + ' open x' + Q + ')',
     False),
]

bad = []
for name, body, want in CASES:
    fd, p = tempfile.mkstemp(suffix='.py', text=True)
    os.close(fd)
    io.open(p, 'w', encoding='utf-8').write(body)
    got = rbs.needs_daemon(p)
    os.remove(p)
    ok = (got == want)
    print('  [%s] %-26s 期望依赖=%-5s 实得=%-5s' % (
        'ok' if ok else 'X', name, want, got))
    if not ok:
        bad.append(name)

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  %d 类样本分类全部正确（含真调用+headless=new 这条旧版漏判、'
      'ab_compat 兼容层这条迁移豁免）' % len(CASES))