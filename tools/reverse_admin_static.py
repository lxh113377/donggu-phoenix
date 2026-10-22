# -*- coding: utf-8 -*-
r"""tools/reverse_admin_static.py —— 反向验证后台静态化的两条判据（破坏必须被抓到）。

## 为什么必须有这一件
本仓反复栽在「判据看着接了其实没接」：轮94 的反向验证自己因硬编码表名而失效、
轮100 的 js_syntax 回退分支一次都没走到、轮108 的 AR 判据退出码恒 0。
一条只会报 PASS 的判据等于没有判据 —— 所以每条新判据的当轮都要证明它有牙。

## 被破坏的对象是**产品行为**，不是探针；每个用例只造它自己要造的那一个错（U-274）
判据 A：tools/admin_static_data_test.py
  A0 基线必须 PASS
  A1 改产物里一个数字（手工调数）   -> FAIL（漂移 + 求和）
  A2 改窗口右界（口径漂移）         -> FAIL
  A3 往后台塞 fetch 接口            -> FAIL（退回实时读）
  A4 往后台塞 setInterval          -> FAIL（回到实时更新）
  A5 页脚偷偷读 /api/stats         -> FAIL
  A6 只改页脚数字（两边打架）       -> FAIL
  A7 末周删掉中间一天               -> FAIL（整周不满七天）
判据 B：tools/admin_static_render_test.py（真浏览器）
  B0 基线必须 PASS
  B9 数据引用路径改错               -> FAIL（zone 停在 nodata）
  B10 渲染调用整批摘除              -> FAIL（指标卡零张）

## 环境缺口与判据不通过必须分开
判据 B 要起 chrome：缺 chrome 时它自己返回 SKIP，本脚本据此把 B0/B9/B10
记为 SKIP 并明说「未取证不等于通过」，绝不把「环境跑不了」写成「防护有效」。
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
_TOOLS = os.path.join(BASE, 'tools')
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

# 入口第一件事：把解释器换成能 spawn 自己的那一个。
# safe_mutation.run_python 用 sys.executable，而本机 PATH 首位那份
# （LibreOffice 自带）**无法 spawn 自己**（WinError 5），不先切换会在第一个
# 用例就崩在 subprocess 上（轮74 同一课）。ensure 只在确有模块缺失时才切换，
# 所以这里声明用例 B 真正要用的 websocket。
try:
    import pyenv
    pyenv.ensure(["websocket"], label="reverse_admin_static")
except ImportError:
    print("[WARN] tools/pyenv.py 缺失，破坏性用例可能因环境缺口失败")

from tools.safe_mutation import mutate_sandbox     # noqa: E402

DATA_TEST = os.path.join('tools', 'admin_static_data_test.py')
RENDER_TEST = os.path.join('tools', 'admin_static_render_test.py')
ADMIN = os.path.join('site', 'admin', 'index.html')
DATA = os.path.join('site', 'assets', 'data', 'admin-stats.js')
FOOTER = os.path.join('site', 'assets', 'data', 'footer-stats.js')
ANALYTICS = os.path.join('site', 'assets', 'js', 'analytics.js')

DATE_RX = '"date": "(2026-11-\\d\\d)"'
DAY_RX = '\\{\\s*"date": "%s",[\\s\\S]*?\\},'

bad = []
skipped = []


def run(sb, script, timeout=200):
    r = sb.run_python(script, timeout=timeout)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    return r.returncode, (res[-1] if res else '(无 RESULT 行)'), out


def expect_fail(sb, script, label, want_kw, timeout=200):
    """要求判据判红，且归因行要点名它声称要防的那件事。"""
    rc, res, out = run(sb, script, timeout)
    print('[%s] rc=%d %s' % (label, rc, res[:66]))
    if res.startswith('RESULT: SKIP'):
        skipped.append('%s：%s' % (label, res[:60]))
        return
    if rc == 0:
        bad.append('%s 未被抓到（判据仍报通过）' % label)
    elif want_kw not in out:
        bad.append('%s 判红了但没点名「%s」（归因不成立）' % (label, want_kw))


def expect_pass(sb, script, label, timeout=200):
    rc, res, _ = run(sb, script, timeout)
    print('[%s] rc=%d %s' % (label, rc, res[:66]))
    if res.startswith('RESULT: SKIP'):
        skipped.append('%s：%s' % (label, res[:60]))
        return False
    if rc != 0:
        bad.append('%s 基线未通过，后续用例前提不成立' % label)
        return False
    return True


# ---------- 判据 A：数据与静态性 ----------
with mutate_sandbox(require_clean=False) as sb:
    if expect_pass(sb, DATA_TEST, 'A0 基线'):
        p = sb.path(DATA)
        t = open(p, encoding='utf-8').read()
        m = re.search('"pv": (\\d+)', t)
        assert m, 'A1 前提：找不到 pv 字段'
        t2 = t.replace(m.group(0), '"pv": %d' % (int(m.group(1)) - 1), 1)
        assert t2 != t, 'A1 替换未生效'
        open(p, 'w', encoding='utf-8', newline='').write(t2)
        expect_fail(sb, DATA_TEST, 'A1 手工改产物数字', '漂移')

with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(DATA)
    t = open(p, encoding='utf-8').read()
    assert '"2026-11-09"' in t, 'A2 前提：找不到窗口右界'
    open(p, 'w', encoding='utf-8', newline='').write(
        t.replace('"2026-11-09"', '"2026-12-20"', 1))
    expect_fail(sb, DATA_TEST, 'A2 窗口越出十一月初', '统计窗口')

with mutate_sandbox(require_clean=False) as sb:
    # 追加而非改写既有标识符：不依赖被测文件的具体内容（轮102 教训）
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    open(p, 'w', encoding='utf-8', newline='').write(
        t.replace('</body>', '<script>fetch("/api/admin/overview")</script></body>', 1))
    expect_fail(sb, DATA_TEST, 'A3 后台注入 fetch', '统计接口')

with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    open(p, 'w', encoding='utf-8', newline='').write(
        t.replace('</body>', '<script>setInterval(function(){},60000)</script></body>', 1))
    expect_fail(sb, DATA_TEST, 'A4 后台注入定时器', '定时器')

with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ANALYTICS)
    t = open(p, encoding='utf-8', newline='').read()
    open(p, 'w', encoding='utf-8', newline='').write(t + "\nfetch('/api/stats');\n")
    expect_fail(sb, DATA_TEST, 'A5 页脚偷读 /api/stats', '/api/stats')

with mutate_sandbox(require_clean=False) as sb:
    # 只改页脚，制造「页脚与后台两个数不一样」——线上被现场抓包的那种事故
    p = sb.path(FOOTER)
    t = open(p, encoding='utf-8').read()
    m = re.search('"pv": (\\d+)', t)
    assert m, 'A6 前提：页脚找不到 pv'
    open(p, 'w', encoding='utf-8', newline='').write(t.replace(m.group(0), '"pv": 999', 1))
    expect_fail(sb, DATA_TEST, 'A6 页脚与后台数字打架', '不一致')

with mutate_sandbox(require_clean=False) as sb:
    # A7 删**中间**那天，不删最后一天：删末尾会把前一个元素的尾逗号变成
    # JSON 尾逗号，解析直接失败 —— 判据虽然也判红，但归因落在「无法解析」上，
    # 这个用例就没在测它声称的那件事（轮94「名实不符」同课）。
    p = sb.path(DATA)
    t = open(p, encoding='utf-8').read()
    days = re.findall(DATE_RX, t)
    assert len(days) >= 3, 'A7 前提：末周日期不足 3 天'
    victim = days[len(days) // 2]
    seg = re.search(DAY_RX % re.escape(victim), t)
    assert seg, 'A7 前提：无法定位中间那天（含尾逗号）'
    t2 = t[:seg.start()] + t[seg.end():]
    head = t2.find('var DG_STATIC_STATS = ') + len('var DG_STATIC_STATS = ')
    try:
        json.loads(t2[head:t2.rstrip().rfind('}') + 1])
    except Exception as e:
        raise AssertionError('A7 造的错必须是「少一天」而不是「JSON 坏掉」：%s' % e)
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    expect_fail(sb, DATA_TEST, 'A7 末周缺一整天', '七个整日')

# ---------- 判据 B：真浏览器渲染 ----------
with mutate_sandbox(require_clean=False) as sb:
    ok = expect_pass(sb, RENDER_TEST, 'B0 基线（需 chrome）', timeout=600)
    if ok:
        with mutate_sandbox(require_clean=False) as sb2:
            # 回到 /admin/assets/... 那个真实坑：路径少了 ../ 就 404
            p = sb2.path(ADMIN)
            t = open(p, encoding='utf-8', newline='').read()
            assert '../assets/data/admin-stats.js' in t, 'B9 前提：找不到数据引用'
            open(p, 'w', encoding='utf-8', newline='').write(
                t.replace('../assets/data/admin-stats.js',
                          'assets/data/admin-stats.js', 1))
            expect_fail(sb2, RENDER_TEST, 'B9 数据路径写错', 'dash', timeout=600)

        with mutate_sandbox(require_clean=False) as sb3:
            # 渲染调用整批摘掉：DOM 结构还在、数字一个不渲染
            p = sb3.path(ADMIN)
            t = open(p, encoding='utf-8', newline='').read()
            t2 = re.sub(r'\n\s*(renderCards|renderWeekTable|renderWeekSelect|'
                        r'renderDays|renderDims|drawWeeks|drawDays)\(\);', '', t)
            assert t2 != t, 'B10 替换未生效'
            open(p, 'w', encoding='utf-8', newline='').write(t2)
            expect_fail(sb3, RENDER_TEST, 'B10 渲染调用被摘除', '指标卡', timeout=600)
    else:
        skipped.append('B9/B10 随 B0 一起未取证')

print()
if skipped:
    print('SKIP（未取证不等于通过）：')
    for s in skipped:
        print('  ~', s)
if bad:
    print('RESULT: FAIL  判据没牙：')
    for b in bad:
        print('  -', b)
    sys.exit(1)
n_b = sum(1 for x in skipped if x.startswith('B'))
print('RESULT: PASS  数据判据 7 类退化全部能抓到；渲染判据 %s'
      % ('2 类已抓到' if n_b == 0 else '因环境未取证（见 SKIP）'))
sys.exit(0)
