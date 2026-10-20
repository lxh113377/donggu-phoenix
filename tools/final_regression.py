# -*- coding: utf-8 -*-
import json, subprocess, time
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=90):
    r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                       cwd=WD, timeout=timeout, encoding='utf-8', errors='replace')
    return (r.stdout or '').strip()

def ev_file(path):
    out = ps("agent-browser eval (Get-Content -Raw -Encoding UTF8 '%s')" % path)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try: return json.loads(json.loads(line))
            except Exception: continue
    return out

# 0) 先关掉可能残留的调试会话：agent-browser 是常驻 daemon，
#    上一次异常退出留下的会话会让后续 set viewport 卡到超时（本轮实测踩到）。
ps('agent-browser close', timeout=40)

# 1) 门禁
r = subprocess.run([PS, '-NoProfile', '-Command', 'python tools/verify_site.py'], capture_output=True, text=True, cwd=WD, encoding='utf-8', errors='replace')
tail = [l for l in r.stdout.splitlines() if l.startswith('[PASS]') or l.startswith('[FAIL]') or 'RESULT' in l or '首屏关键路径' in l]
print('[门禁] rc=%d 通过=%d 失败=%d | %s' % (r.returncode,
      sum(1 for l in tail if l.startswith('[PASS]')),
      sum(1 for l in tail if l.startswith('[FAIL]')),
      [l for l in tail if 'RESULT' in l or '首屏关键路径' in l]))

# 2) 多视口 + 字体 + 溢出
for w, h in [(360, 780), (390, 844), (768, 1024), (1440, 900), (1920, 1080)]:
    ps('agent-browser set viewport %d %d' % (w, h))
    ps('agent-browser open "http://127.0.0.1:8791/?rg=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(1.4)
    d = ev_file('_qa/probe_viewport.js')
    if isinstance(d, dict):
        print('  %dx%d: sw=%s docH=%s toggle=%s minTap=%s overflow=%s font=%s' % (
            w, h, d.get('sw'), d.get('docH'), d.get('toggle'), d.get('minTap'),
            'OK' if not d.get('overflow') else d.get('overflow'), (d.get('h1') or {}).get('ff')))
    else:
        print('  %dx%d: PARSE-FAIL' % (w, h))

# 3) 交互回归
ps('agent-browser set viewport 1440 900')
ps('agent-browser open "http://127.0.0.1:8791/?rg=it"')
ps('agent-browser wait --load networkidle')
time.sleep(1.5)
d = ev_file('_qa/final_interaction.js')
print('[交互]', json.dumps(d, ensure_ascii=False) if isinstance(d, dict) else d)
