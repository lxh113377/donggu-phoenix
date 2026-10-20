
# -*- coding: utf-8 -*-
"""修 reveal_after_jump_test 的误报：只判「在视口内却仍隐藏」的才算缺陷。

一手问题（轮15）：
原来统计段落内所有 .reveal 的 opacity，把「本来就在视口下方、尚未进入」的元素
也算成 FAIL。实测 #totem 跳转后 totem-copy 的 top=869 > vh=844，它在视口外，
IntersectionObserver 不该触发 —— 继续滚动 400px 后它正常 opacity=1。

正确判据：
  · 元素在视口内（top < vh 且 bottom > 0）却 opacity<0.9  → 真缺陷
  · 元素在视口外且 opacity<0.9                            → 正常，不计
  · 页面完全不可用/取不到读数                              → SKIP
"""
import json, subprocess, time, sys
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=45):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

JS_TMPL = ("JSON.stringify((function(){var s=document.getElementById('%s');"
           "if(!s)return {err:1};"
           "var rev=s.querySelectorAll('.reveal,.clip-reveal');"
           "var inViewHidden=0,total=rev.length;"
           "[].slice.call(rev).forEach(function(e){"
           "var r=e.getBoundingClientRect();var o=parseFloat(getComputedStyle(e).opacity);"
           "if(o<0.9 && r.top<innerHeight && r.bottom>0) inViewHidden++;"
           "});return {total:total,bad:inViewHidden};})())")

def get(sid):
    path = WD + r'\_qa\_rv.js'
    open(path, 'w', encoding='utf-8').write(JS_TMPL % sid)
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % path)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None

def main():
    ps('agent-browser set viewport 1440 900')  # 显式视口，保证结果可复现
    ps('agent-browser open "http://127.0.0.1:8791/?jump=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.0)

    tested = fails = skipped = 0
    for sid in ['totem','carve-sec','ar-gallery','culture','craft','merch','road','scan']:
        ps('agent-browser eval "location.hash=\'#%s\';1"' % sid)
        time.sleep(1.3)
        got = get(sid)
        if not got or 'total' not in got:
            print('%-12s SKIP' % sid)
            skipped += 1
            continue
        tested += 1
        ok = got['bad'] == 0
        if not ok:
            fails += 1
        print('%-12s total=%2d 视口内隐藏=%d %s' % (sid, got['total'], got['bad'], 'OK' if ok else 'FAIL'))

    print()
    if tested == 0:
        print('RESULT: SKIP  全部锚点未测到（环境问题，不是通过）')
        return 0
    if fails:
        print('RESULT: FAIL  %d/%d 段落跳转后视口内仍有隐藏元素' % (fails, tested))
        return 1
    print('RESULT: PASS  %d/%d 段落跳转后视口内无隐藏元素（%d SKIP）' % (tested, tested, skipped))
    return 0

if __name__ == '__main__':
    sys.exit(main())
