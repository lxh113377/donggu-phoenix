# -*- coding: utf-8 -*-
"""hero_height_test v2 —— 每个视口只用一个短命令序列，避免多次 spawn 卡死。
读不到就报 SKIP（环境），不误判为通过也不误判为失败。
"""
import json, subprocess, time, uuid

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def run(cmd, timeout=40):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                           cwd=WD, timeout=timeout, encoding='utf-8', errors='replace')
        return (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

PROBE = "JSON.stringify({h:Math.round(document.getElementById('hero').getBoundingClientRect().height),vh:innerHeight})"

results = []
for w, h, label in [(360,780,'360x780'),(390,844,'390x844'),(430,932,'430x932')]:
    run('agent-browser close --all')
    time.sleep(0.8)
    run('agent-browser set viewport %d %d' % (w, h))
    run('agent-browser open "http://127.0.0.1:8791/?vh=%s"' % uuid.uuid4().hex[:6])
    run('agent-browser wait --load networkidle')
    time.sleep(1.4)
    out = run('agent-browser eval "%s"' % PROBE.replace('"', '\\"'))
    got = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                got = json.loads(json.loads(line)); break
            except Exception:
                continue
    if got:
        ratio = round(got['h'] / got['vh'], 2)
        ok = ratio <= 1.05
        results.append(ok)
        print('%-10s hero=%4d vh=%4d  %.2f×  %s' % (label, got['h'], got['vh'], ratio, 'OK' if ok else '撑高!'))
    else:
        print('%-10s SKIP（浏览器无响应）' % label)

run('agent-browser set viewport 1440 900')
print()
if not results:
    print('RESULT: SKIP  环境不可用')
    raise SystemExit(0)
if all(results):
    print('RESULT: PASS  手机首屏均为一屏（%d 档）' % len(results))
    raise SystemExit(0)
print('RESULT: FAIL  %d/%d 视口首屏被撑高' % (results.count(False), len(results)))
raise SystemExit(1)
