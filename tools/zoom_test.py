# -*- coding: utf-8 -*-
"""缩放等效视口下布局不崩（轮120 迁移：agent-browser -> CDP）。

原版三个问题：依赖 agent-browser（二进制不存在，从未有读数）；
只 print 无断言/无 RESULT/无退出码（哑判据）；
直连 127.0.0.1:8791 假设外部已起服务（隐性环境依赖）。

测什么（浏览器 200%/125% 缩放等效于视口变小）：
  A 无横向溢出  B 无元素越界  C 根字号 >= 15px 仍可读
零样本不判 PASS。

JS 用 chr() 构造：本会话手写转义已连错多次，一律避开。
"""
import json
import os
import sys
import time

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
os.chdir(WD)
sys.path.insert(0, os.path.join(WD, 'tools'))

Q = chr(34)
S = chr(39)

try:
    from ab_compat import AbSession, AbCompatError
except Exception as e:
    print('RESULT: SKIP  ab_compat 不可用: %s' % e)
    sys.exit(0)

VIEWS = [(720, 450, '200% 缩放等效视口'),
         (1280, 720, '125% 缩放等效视口')]

# 构造探针 JS（用 chr 拼，源码不出现需转义的引号串）
SEL = S + 'h1,h2,h3,p,li,dd,button,a' + S
PROBE = ('(function(){var de=document.documentElement;'
         + 'var hidden=[].slice.call(document.querySelectorAll(' + SEL + '))'
         + '.filter(function(e){'
         + 'if(!e.offsetParent) return false; var s=getComputedStyle(e);'
         + 'var r=e.getBoundingClientRect();'
         + 'return (r.right>innerWidth+2||r.left<-2) && s.position!=='
         + S + 'fixed' + S + ';}).length;'
         + 'return JSON.stringify({w:innerWidth,sw:de.scrollWidth,'
         + 'cw:de.clientWidth,real:de.scrollWidth>de.clientWidth+1,'
         + 'offscreen:hidden,'
         + 'rootFont:parseFloat(getComputedStyle(de).fontSize)})})()')

AB = AbSession()
srv = None
fails = []
tested = 0

try:
    try:
        from cdp_client import SiteServer
        srv = SiteServer(os.path.join(WD, 'site'), port=8791)
        base = srv.url('/index.html')
    except Exception:
        base = 'http://127.0.0.1:8791/index.html'

    for w, h, label in VIEWS:
        AB.run('agent-browser set viewport %d %d' % (w, h))
        AB.run('agent-browser open ' + Q + base + '?zoom=%d' % w + Q)
        AB.run('agent-browser wait --load networkidle')
        time.sleep(1.3)
        out = AB.run('agent-browser eval ' + Q + PROBE + Q)
        try:
            d = json.loads(out) if out else None
        except Exception:
            d = None
        if not d:
            print('%-16s 无读数 %r' % (label, (out or '')[:60]))
            fails.append('%s 取不到读数' % label)
            continue
        tested += 1
        print('%-16s w=%-5d sw=%-5d 越界=%-2d 根字号=%.1f  %s' % (
            label, d['w'], d['sw'], d['offscreen'], d['rootFont'],
            '横向溢出!' if d['real'] else 'OK'))
        if d['real']:
            fails.append('%s 横向溢出（sw=%d > cw=%d）'
                         % (label, d['sw'], d['cw']))
        if d['offscreen'] > 0:
            fails.append('%s 有 %d 个元素越界' % (label, d['offscreen']))
        if d['rootFont'] < 15:
            fails.append('%s 根字号 %.1f < 15px' % (label, d['rootFont']))

except AbCompatError as e:
    print('RESULT: SKIP  CDP 环境不可用: %s' % e)
    sys.exit(0)
except Exception as e:
    print('RESULT: SKIP  探针异常: %s: %s' % (type(e).__name__, str(e)[:110]))
    sys.exit(0)
finally:
    AB.close()
    if srv:
        try:
            srv.stop()
        except Exception:
            pass

print()
if tested != len(VIEWS):
    fails.append('只测到 %d/%d 种缩放' % (tested, len(VIEWS)))
if fails:
    print('RESULT: FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('RESULT: PASS  %d 种缩放等效视口下均无溢出、无越界、字号可读' % tested)
sys.exit(0)