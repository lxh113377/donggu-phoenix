# -*- coding: utf-8 -*-
"""反向验证 admin_contrast_test：证明它的 zone 守卫双向有效（轮75）。

## 为什么这样验
这条判据最难验的不是对比度内核（那套内核已被 contrast_audit 自检证明），
而是它**特有的链路**：pages dev 起停、sessionStorage 注入密钥、
多视口 iframe、zone 判定。

最容易出「假绿」的是：登录其实没成功、页面停在登录卡，
而登录卡文字对比度是达标的 -> 判据会 PASS 却根本没测仪表盘。
所以 zone 守卫是命门，必须双向证明：
  · 正确密钥 -> zone == dash 且确实测到仪表盘（检查数 > 200）
  · 错误密钥 -> zone != dash（登录失败能被识别）

## 顺序：非破坏性用例先跑（轮75 踩过的坑）
错误密钥会往 auth_fails 表写记录（中间件的失败限流计数），
属破坏性测试。第一版把 A（错密钥）放前面，B 紧随其后拿不到读数，
我一度误判成「A 触发限流把 B 挡了」—— 实测 FAIL_LIMIT=20、我只写 4 条，
根本没触发限流；B 单独重跑 3/3 全绿。真因是 chrome 偶发空输出（U-193）。
教训两条：
  1. 破坏性用例放最后，别让它污染后续用例；
  2. 下结论前先验证假设（我当时差点据此改中间件）。
"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)

from tools.admin_contrast_test import (find_chrome, free_port, read_admin_key,
                                       start_pages_dev, dump_dom, probe_html)

chrome = find_chrome()
key = read_admin_key()
if not chrome or not key:
    print('RESULT: SKIP  缺 chrome 或 .dev.vars')
    sys.exit(0)

port = free_port()
print('起 pages dev 于 %d ...' % port)
proc = start_pages_dev(port)
if proc is None:
    print('RESULT: SKIP  pages dev 起不来')
    sys.exit(0)

path = '_admin_probe_contrast.html'
dst = os.path.join(BASE, 'site', path)


def clear_auth_fails():
    """清掉测试写入的失败计数，不给本地库留噪声。"""
    try:
        subprocess.run(['npx', 'wrangler', 'd1', 'execute', 'donggu-analytics',
                        '--local', '--command', 'DELETE FROM auth_fails', '--yes'],
                       capture_output=True, timeout=120, cwd=BASE, shell=True)
    except Exception:
        pass


try:
    html = probe_html()
    assert key not in html, '探针本体不得含密钥'
    open(dst, 'w', encoding='utf-8').write(html)

    def run(label, use_key, attempts=6):
        """chrome 偶发空输出（U-193），外层再重试。"""
        url = 'http://127.0.0.1:%d/%s#%s' % (port, path, use_key)
        for i in range(attempts):
            rows = dump_dom(chrome, url, attempts=3)
            if rows and not isinstance(rows, dict):
                zones = [r.get('zone') for r in rows if not r.get('err')]
                checked = sum(r.get('checked', 0) for r in rows)
                print('[%s] zone=%s 检查 %d 处（第%d轮拿到）' % (label, zones, checked, i + 1))
                return zones, checked
            time.sleep(2)
        print('[%s] %d 轮仍无读数' % (label, attempts))
        return None, 0

    # === B 先跑：正确密钥（非破坏性）===
    zb, cb = run('B 正确密钥', key)
    ok_b = bool(zb) and all(z == 'dash' for z in zb) and cb > 200
    print('   期望 zone==dash 且检查数>200: %s' % ('OK' if ok_b else '未达成'))

    # === A 后跑：错误密钥（会写 auth_fails，属破坏性）===
    time.sleep(1)
    za, ca = run('A 错误密钥', 'wrong-key-000000000000000000000000')
    ok_a = bool(za) and all(z != 'dash' for z in za) and len(za) > 0
    print('   期望 zone != dash（登录失败可识别）: %s' % ('OK' if ok_a else '未达成'))
    clear_auth_fails()

    print()
    if ok_a and ok_b:
        print('RESULT: PASS  zone 守卫双向有效：'
              '登录成功确实测到仪表盘，登录失败会被识别')
        sys.exit(0)
    print('RESULT: FAIL  zone 守卫不可信（A %s / B %s）' % (
        'OK' if ok_a else '不 OK', 'OK' if ok_b else '不 OK'))
    sys.exit(1)
finally:
    try:
        os.remove(dst)
    except Exception:
        pass
    try:
        proc.terminate()
        time.sleep(1)
        proc.kill()
    except Exception:
        pass
