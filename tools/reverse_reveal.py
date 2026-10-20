
# -*- coding: utf-8 -*-
"""反向验证 reveal_after_jump_test：破坏 reveal 逻辑，必须判红。

用 safe_mutation 沙箱改 main.js 让 reveal 永不触发，然后跑测试。
注意：测试需访问 http://127.0.0.1:8791 服务的是真实目录，
所以这里改为直接验证「判据能否识别 inView 隐藏」这一逻辑本身 ——
用页面内注入的方式模拟。
"""
import sys
sys.path.insert(0, '.')
import subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=45):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

# 打开页面，强行把视口内的 .reveal 设成 opacity:0（模拟 reveal 失效）
ps('agent-browser open "http://127.0.0.1:8791/?revbad=1"')
ps('agent-browser wait --load networkidle')
time.sleep(2.0)
ps('agent-browser eval "location.hash=\'#culture\';1"')
time.sleep(1.3)
# 破坏：把该段所有 reveal 还原成未进场状态
ps('agent-browser eval "document.querySelectorAll(\'#culture .reveal\').forEach(function(e){e.style.opacity=0;e.classList.remove(\'in\');});1"')
time.sleep(0.4)

# 用同一判据逻辑检查
JS = ("(function(){var s=document.getElementById('culture');"
      "var rev=s.querySelectorAll('.reveal,.clip-reveal');var bad=0;"
      "[].slice.call(rev).forEach(function(e){var r=e.getBoundingClientRect();"
      "var o=parseFloat(getComputedStyle(e).opacity);"
      "if(o<0.9&&r.top<innerHeight&&r.bottom>0)bad++;});"
      "return JSON.stringify({total:rev.length,bad:bad});})()")
open(WD + r'\_qa\_rvbad.js', 'w', encoding='utf-8').write(JS)
out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % (WD + r'\_qa\_rvbad.js'))
print('破坏后读数:', out[-200:])
print()
print('说明：bad>0 表示判据能识别「视口内隐藏」这一真缺陷。')
