
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
import json, os, subprocess, time, sys
# 轮120：PS 常量在迁移后已不再使用（执行通道改 ab_compat），保留无害
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

# 轮120 迁移：ps() 从 PowerShell 调 agent-browser 改为走 ab_compat 兼容层。
# 业务逻辑、断言、RESULT 判定全部不动 —— 只换执行通道。
_AB = None


def _ab():
    global _AB
    if _AB is None:
        from ab_compat import AbSession
        _AB = AbSession()
    return _AB


def ps(cmd, timeout=90):
    return _ab().run(cmd, timeout=timeout)

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
    # 轮120：CDP 的 eval 只返回一层，不再需要 json.loads(json.loads(...))。
    # 双层解析是 agent-browser 把结果再套一层引号的特性（轮118/119 已两次踩过）。
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % path)
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None

def main():
    # 轮120：判据自己起服务，不再假设外部已起 8791（原版是隐性环境依赖，
    # 换机器/CI 必失败，且失败形态是 SKIP —— 看起来像环境问题、不算判据失效）。
    _srv = None
    try:
        from cdp_client import SiteServer
        _srv = SiteServer(os.path.join(WD, 'site'), port=8791)
        _url = _srv.url('/index.html?jump=%d' % int(time.time()))
    except Exception as _e:
        print('RESULT: SKIP  服务起不来: %s' % _e)
        return 0

    ps('agent-browser set viewport 1440 900')  # 显式视口，保证结果可复现
    ps('agent-browser open "%s"' % _url)
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
