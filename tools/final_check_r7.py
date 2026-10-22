# -*- coding: utf-8 -*-
import json, subprocess, sys, os, time
BASE = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
def ps(cmd, timeout=300):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=BASE,timeout=timeout,encoding='utf-8',errors='replace')
    return (r.stdout or '') + (r.stderr or '')

print('=== 1) 干净克隆门禁 ===')
print(ps('$t = Join-Path $env:TEMP ("dg_fin_"+[guid]::NewGuid().ToString("N").Substring(0,6)); git clone -q --depth 1 --no-hardlinks . $t; Push-Location $t; python tools/verify_site.py 2>&1 | Select-String -Pattern "RESULT|^\\[FAIL|部署体积|首屏"; python tools/ci_design_static.py 2>&1 | Select-String -Pattern "RESULT"; Pop-Location; Remove-Item -Recurse -Force $t')[-1200:])

print('=== 2) 线上实测 ===')
print(ps('''$js = Get-Content -Raw -Encoding UTF8 '_qa/clear_sw.js'; agent-browser eval $js 2>$null; agent-browser set viewport 1440 900; agent-browser open "https://lxh113377.github.io/donggu-phoenix/?final=%d"; agent-browser wait --load networkidle; agent-browser wait 2600; $p = Get-Content -Raw -Encoding UTF8 '_qa/probe_viewport.js'; agent-browser eval $p''')[-600:])
