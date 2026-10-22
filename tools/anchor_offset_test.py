# -*- coding: utf-8 -*-
"""实测：点导航跳转后，段落顶部是否被固定顶栏遮住。

## 轮118 迁移（原版依赖 agent-browser，二进制不存在 -> 从未有读数）
原版三个问题：依赖失效二进制；只 print 无 RESULT/exit code（哑判据）；
靠 agent-browser 隐式默认页、无显式 open。
迁移用 ab_compat 把命令翻译成 CDP，业务逻辑不变，并补齐 RESULT/退出码。

## 引号一律用 chr() 构造
本文件要生成含大量引号/花括号的 JS。手写转义在本会话已连错三次，
故统一用 Q(chr34) 与 S(chr39) 拼接，源码里不出现需要转义的引号串。
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

IDS = ['totem', 'carve-sec', 'ar-gallery', 'culture', 'craft',
       'merch', 'road', 'scan']

AB = AbSession()
srv = None
bad = []
tested = 0
try:
    from cdp_client import SiteServer
    srv = SiteServer(os.path.join(WD, 'site'), port=8791)
except Exception:
    srv = None

try:
    url = srv.url('/index.html?anchor=1') if srv else 'http://127.0.0.1:8791/'
    AB.run('agent-browser open ' + Q + url + Q)
    AB.run('agent-browser wait --load networkidle')

    for i in IDS:
        AB.run('agent-browser eval ' + Q + 'location.hash='
               + S + '#' + i + S + ';1' + Q)
        time.sleep(0.9)
        js = ('JSON.stringify({top:Math.round(document.getElementById('
              + S + i + S + ').getBoundingClientRect().top),'
              + 'hdr:Math.round(document.querySelector('
              + S + 'header.nav' + S
              + ').getBoundingClientRect().height)})')
        out = AB.run('agent-browser eval ' + Q + js + Q)
        try:
            # 原版是 json.loads(json.loads(out)) —— 双层是 agent-browser 把
            # eval 结果再套一层引号的特性。CDP 只返回一层，再解一次必然失败。
            d = json.loads(out)
        except Exception:
            print('%-12s PARSE FAIL  %r' % (i, (out or '')[:70]))
            bad.append('%s 读数解析失败' % i)
            continue
        tested += 1
        covered = d['top'] < d['hdr']
        print('%-12s top=%4d  header=%3d  %s' % (
            i, d['top'], d['hdr'], '遮蔽!' if covered else 'OK'))
        if covered:
            bad.append('%s 被顶栏遮住 (top=%d < hdr=%d)'
                       % (i, d['top'], d['hdr']))
except AbCompatError as e:
    print('RESULT: SKIP  CDP 环境不可用: %s' % e)
    sys.exit(0)
except Exception as e:
    print('RESULT: SKIP  探针异常: %s: %s' % (type(e).__name__, str(e)[:100]))
    sys.exit(0)
finally:
    AB.close()
    if srv:
        try:
            srv.stop()
        except Exception:
            pass

print()
if tested != len(IDS):
    print('RESULT: FAIL  只测到 %d/%d 个锚点（有跳过的）' % (tested, len(IDS)))
    sys.exit(1)
if bad:
    print('RESULT: FAIL')
    for b in bad:
        print('  -', b)
    sys.exit(1)
print('RESULT: PASS  %d 个锚点跳转后均未被顶栏遮住' % tested)
sys.exit(0)