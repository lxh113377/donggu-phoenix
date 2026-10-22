# -*- coding: utf-8 -*-
r"""tools/admin_static_data_test.py —— 后台演示数据防漂移与「不得回到实时读」判据（纯静态，CI 可跑）。

## 为什么需要它（2026-10-22，老大报的那个 bug）
症状：后台「近 30 天浏览」末端突然跌下去，指标卡与页脚的数随刷新变化；
一旦数据库被清空或读不到，演示现场刷新一次，访问量直接归零。
处置：后台与页脚改读**一次生成的静态演示样本**（按周、九月初至十一月初、总量 1 万~2 万）。

但「改成静态」这个决定很容易在后续迭代里被悄悄改回去 —— 顺手加一句 fetch、
换回 /api/stats、或手工改产物里的某个数字让两边不一致。
本判据把这次决定变成结构约束，五条各守一种退化：

  A 数据漂移：产物必须与生成器逐字节一致（现场重算 + SHA256 比对）。
    手工改过一个数字 = 判红。要改数据必须改生成器再重跑。
  B 口径：窗口必须是 2026-09-01 ~ 2026-11-09、必须按周（十个整周）、
    总量必须落在 1 万~2 万（「浏览」与「全部事件」两种读法都要在区间内）。
  C 对账：周次相加 == 累计、逐日相加 == 该周、各维度相加 == 对应总量。
    后台是给人读数的，两张表互不相等就是假数据（与 U-282/U-288 同一类病）。
  D 静态性：后台页与页脚脚本不得请求统计接口、不得有登录态与定时器。
    这条是本次改动的本体，也最容易被「顺手加个实时刷新」破坏。
  E 一致性：页脚与后台必须同源同数（两处数字不一致会被现场抓包）。

## A 条为什么 import 而不是起子进程
第一版是 subprocess 调「生成器 --check」，实测本机必然失败：PATH 首位的
python 是 LibreOffice 自带那份，它**无法 spawn 自己**（WinError 5），
于是「环境缺口」伪装成「数据漂移」判红 —— 轮74 立过这条归因纪律。
改成 import 生成器调 build()：同一套算法、零子进程、零环境依赖。

## 自检（先证明尺子有效，U-149/U-151 教训）
六类退化样本必须各自被抓到，任一抓不到即判 FAIL。
注释里的字面量不是行为：D 条扫描前先剥注释 —— 本文件与 analytics.js 的
说明里都写着 /api/stats 这个词，不剥会把自己判红（与 U-22/U-24/U-126 同源）。
"""
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_guard import verdict, emit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 一律用「相对仓库根 + 正斜杠」的路径形态。
# 一手事故（轮109，CI run 39731354518 判红而本机全绿）：GEN 原先写成绝对路径，
# 与同列表里其它相对项混用。Windows 上 os.path.join(BASE, 绝对路径) 会直接返回
# 绝对路径所以看不出来；Linux 上 split('/') 得到以空串开头的段，拼出
# BASE + BASE + tools/... 这种双重路径，必然「文件不存在」——
# 典型「本地绿、CI 红」，且红的是判据自己而不是产品。
GEN_REL = 'tools/make_static_admin_data.py'
GEN = os.path.join(BASE, 'tools', 'make_static_admin_data.py')
ADMIN = 'site/admin/index.html'
ANALYTICS = 'site/assets/js/analytics.js'
INDEX = 'site/index.html'
DATA_ADMIN = 'site/assets/data/admin-stats.js'
DATA_FOOTER = 'site/assets/data/footer-stats.js'

WINDOW_START = '2026-09-01'
WINDOW_END = '2026-11-09'
N_WEEKS = 10
LO, HI = 10000, 20000


def read(rel):
    p = os.path.join(BASE, *rel.split('/'))
    return open(p, encoding='utf-8', errors='replace').read()


def strip_comments(text, is_html):
    """剥注释：判据扫的是行为，注释里的字面量不是行为。

    HTML 模式不剥 //（https:// 会被连坐，轮50 实测把「受限时用」整段吃掉）。
    JS 的行注释只认「行首只有空白然后是 //」：若按 // 无条件切到行尾，
    会把字符串里的 URL 一起切掉，让禁用词检查出现**漏报**。
    """
    if is_html:
        text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
        return re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'^[ \t]*//[^\n]*', ' ', text, flags=re.M)


def load_generator():
    spec = importlib.util.spec_from_file_location('dg_make_static', GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_var(text, var):
    m = re.search(r'var %s = (\{.*?\});\s*$' % var, text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def sums_ok(d):
    """C 条：全部求和关系。返回不符项列表。"""
    bad = []
    t = d['totals']
    if sum(w['pv'] for w in d['weeks']) != t['pv']:
        bad.append('周浏览相加 %d != 累计浏览 %d' % (
            sum(w['pv'] for w in d['weeks']), t['pv']))
    if sum(w['uv'] for w in d['weeks']) != t['uv']:
        bad.append('周访客相加 != 累计访客')
    if sum(w['events'] for w in d['weeks']) != t['events']:
        bad.append('周事件相加 != 事件总量')
    for key in ('langs', 'screens', 'referrers'):
        if sum(x['n'] for x in t[key]) != t['pv']:
            bad.append('%s 分布相加 != 累计浏览' % key)
    if sum(x['n'] for x in t['countries']) != t['pv']:
        bad.append('国家浏览相加 != 累计浏览')
    if sum(x['u'] for x in t['countries']) != t['uv']:
        bad.append('国家访客相加 != 累计访客')
    if sum(x['n'] for x in t['sceneRanks']) != t['scenes']:
        bad.append('场景分布相加 != AR 场景总量')
    for w in d['weeks']:
        rows = [x for x in d['days'] if x['week'] == w['idx']]
        if sum(x['pv'] for x in rows) != w['pv']:
            bad.append('第 %d 周逐日相加 != 该周浏览' % w['idx'])
        if len(rows) != 7:
            bad.append('第 %d 周不是七个整日（实得 %d）' % (w['idx'], len(rows)))
    return bad


def window_ok(d):
    """B 条：窗口与量级。返回不符项列表。"""
    bad = []
    w = d['meta']['window']
    if w['start'] != WINDOW_START or w['end'] != WINDOW_END:
        bad.append('统计窗口不是 %s ~ %s（实得 %s ~ %s）' % (
            WINDOW_START, WINDOW_END, w['start'], w['end']))
    if len(d['weeks']) != N_WEEKS:
        bad.append('不是 %d 个整周（实得 %d）' % (N_WEEKS, len(d['weeks'])))
    for nm, v in (('累计浏览', d['totals']['pv']),
                  ('全部事件', d['totals']['events'])):
        if not LO <= v <= HI:
            bad.append('%s %d 不在 %d~%d 区间' % (nm, v, LO, HI))
    return bad


def staticity_problems(admin_html, analytics_js, index_html):
    """D 条：后台与页脚不得再走实时接口 / 登录 / 定时器。入参须已剥注释。"""
    bad = []
    for pat, why in (
        (r'/api/(?:admin|stats|track|events|overview)', '后台请求了统计接口'),
        (r'\bfetch\s*\(', '后台出现 fetch 调用（静态页不该发请求）'),
        (r'sessionStorage', '后台出现登录态存储'),
        (r'setInterval', '后台出现定时器（等于回到实时更新）'),
    ):
        m = re.search(pat, admin_html)
        if m:
            bad.append('%s：%s' % (why, m.group(0)[:40]))
    if 'admin-stats.js' not in admin_html:
        bad.append('后台未引用静态样本 admin-stats.js')
    if re.search(r'/api/stats', analytics_js):
        bad.append('analytics.js 仍在读 /api/stats（页脚计数未静态化）')
    if 'DG_FOOTER_STATS' not in analytics_js:
        bad.append('analytics.js 未使用静态样本 DG_FOOTER_STATS')
    if 'footer-stats.js' not in index_html:
        bad.append('index.html 未加载 footer-stats.js')
    else:
        i_data = index_html.find('footer-stats.js')
        i_an = index_html.find('analytics.js')
        if i_an >= 0 and i_data > i_an:
            bad.append('footer-stats.js 必须在 analytics.js 之前加载（否则读不到全局变量）')
    return bad


def _fake_totals(pv=100):
    return {'pv': pv, 'uv': 60, 'events': 150, 'scenes': 30,
            'langs': [{'l': 'zh', 'n': pv - 1}], 'screens': [{'s': 'a', 'n': pv}],
            'referrers': [{'src': 'x', 'n': pv}],
            'sceneRanks': [{'scene': 'craft', 'n': 30}],
            'countries': [{'c': 'CN', 'n': pv, 'u': 60}]}


def selftest():
    """六类退化样本必须各自被抓到，否则尺子无效。"""
    bad = []
    fake_admin = '<html><body><script>fetch("/api/admin/overview")</script></body></html>'
    hits = staticity_problems(fake_admin, 'var a = 1;', 'footer-stats.js analytics.js')
    if len([h for h in hits if '统计接口' in h or 'fetch' in h or 'admin-stats' in h]) < 3:
        bad.append('D 条自检：注入 fetch + 接口 + 缺数据引用，只抓到 %d 类' % len(hits))
    if not any('/api/stats' in x for x in staticity_problems(
            'admin-stats.js', "fetch('/api/stats')", 'footer-stats.js analytics.js')):
        bad.append('D 条自检：页脚读 /api/stats 未被抓到')
    d = {'meta': {'window': {'start': WINDOW_START, 'end': WINDOW_END}},
         'totals': _fake_totals(),
         'weeks': [{'idx': 1, 'pv': 90, 'uv': 60, 'events': 150}],
         'days': [{'week': 1, 'pv': 90}]}
    if not any('周浏览相加' in x for x in sums_ok(d)):
        bad.append('C 条自检：周次与累计不等未被抓到')
    d_full = json.loads(json.dumps(d))
    d_full['weeks'] = [{'idx': 1, 'pv': 100, 'uv': 60, 'events': 150}]
    d_full['totals']['langs'] = [{'l': 'zh', 'n': 100}]
    if not any('七个整日' in x for x in sums_ok(d_full)):
        bad.append('C 条自检：整周不满七天未被抓到')
    d2 = json.loads(json.dumps(d))
    d2['meta']['window']['start'] = '2026-08-01'
    if not any('统计窗口' in x for x in window_ok(d2)):
        bad.append('B 条自检：窗口左界越界未被抓到')
    d3 = json.loads(json.dumps(d))
    d3['totals'] = _fake_totals(9999)
    if not any('不在' in x for x in window_ok(d3)):
        bad.append('B 条自检：总量越界未被抓到')
    # 注释里的 /api/stats 不得被判成行为（防自伤式误报）
    commented = "/* 真实数据不再读 /api/stats */\nvar x = 1;"
    if any('/api/stats' in x for x in staticity_problems(
            'admin-stats.js', strip_comments(commented, False),
            'footer-stats.js analytics.js')):
        bad.append('D 条自检：注释里的接口名被当成行为（误报）')
    return bad


def main():
    bad_self = selftest()
    if bad_self:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad_self:
            print('  -', b)
        return 1
    print('[PASS] 自检 6 类退化样本全部能被抓到（尺子有效）')

    want = (ADMIN, ANALYTICS, INDEX, DATA_ADMIN, DATA_FOOTER, GEN_REL)
    # 守卫：这个列表只接受相对正斜杠路径，混进绝对路径就当场报错，
    # 而不是等到 CI 才以「文件不存在」的面目暴露（防上面那个坑复发）
    for rel in want:
        assert not os.path.isabs(rel) and '\\' not in rel, \
            '判据内部路径形态不统一（应为相对 + 正斜杠）：%s' % rel
    missing = [rel for rel in want
               if not os.path.exists(os.path.join(BASE, *rel.split('/')))]
    if missing:
        print('RESULT: FAIL\n  - 缺少文件：' + ', '.join(missing))
        return 1

    fails = []
    checked = 0

    # A) 漂移：现场重算，与产物逐字节比 SHA256
    try:
        gen = load_generator()
        d_new = gen.build()
        pairs = [
            (DATA_ADMIN, gen.js_blob('DG_STATIC_STATS', d_new)),
            (DATA_FOOTER, gen.js_blob('DG_FOOTER_STATS', {
                'window': d_new['meta']['window'],
                'uniques': d_new['totals']['uv'],
                'pv': d_new['totals']['pv'],
                'label': '演示样本',
            })),
        ]
        drift = []
        for rel, text in pairs:
            cur = read(rel).replace('\r\n', '\n')
            if hashlib.sha256(cur.encode('utf-8')).hexdigest() != \
               hashlib.sha256(text.encode('utf-8')).hexdigest():
                drift.append(rel)
        checked += 1
        print('[%s] 产物与生成器逐字节一致（现场重算 + SHA256）' % (
            'PASS' if not drift else 'FAIL'))
        if drift:
            fails.append('静态演示数据漂移，需重跑 python tools/make_static_admin_data.py：'
                         + ', '.join(drift))
    except Exception as e:
        print('[FAIL] 产物一致性：生成器不可用（%s: %s）' % (type(e).__name__, e))
        fails.append('A 条无法取证：import 生成器失败 %s: %s' % (type(e).__name__, e))

    d = parse_var(read(DATA_ADMIN), 'DG_STATIC_STATS')
    if not d:
        print()
        print("RESULT: FAIL\n  - admin-stats.js 无法解析（不是 var DG_STATIC_STATS = {json}; 形态）")
        return 1

    # B) 口径
    checked += 1
    bw = window_ok(d)
    w = d['meta']['window']
    print('[%s] 口径：窗口 %s ~ %s / %d 周 / 浏览 %s / 事件 %s（两种读法均在 1 万~2 万）' % (
        'PASS' if not bw else 'FAIL', w['start'], w['end'], len(d['weeks']),
        format(d['totals']['pv'], ','), format(d['totals']['events'], ',')))
    fails.extend('口径不符：' + x for x in bw)

    # C) 对账
    checked += 1
    bs = sums_ok(d)
    print('[%s] 对账：周次 / 逐日 / 各维度求和关系全部成立' % (
        'PASS' if not bs else 'FAIL'))
    fails.extend('数据不自洽：' + x for x in bs)

    # D) 静态性
    checked += 1
    bd = staticity_problems(strip_comments(read(ADMIN), True),
                            strip_comments(read(ANALYTICS), False),
                            strip_comments(read(INDEX), True))
    print('[%s] 静态性：后台与页脚零接口、零登录、零定时器' % (
        'PASS' if not bd else 'FAIL'))
    fails.extend('退回实时更新的风险：' + x for x in bd)

    # E) 页脚与后台同源同数
    checked += 1
    fd = parse_var(read(DATA_FOOTER), 'DG_FOOTER_STATS')
    if not fd:
        fails.append('footer-stats.js 无法解析')
        print('[FAIL] 页脚与后台一致性：数据无法解析')
    elif fd['pv'] != d['totals']['pv'] or fd['uniques'] != d['totals']['uv'] \
            or fd['window']['end'] != w['end']:
        fails.append('页脚与后台数字不一致（页脚 %s/%s，后台 %s/%s）' % (
            fd['pv'], fd['uniques'], d['totals']['pv'], d['totals']['uv']))
        print('[FAIL] 页脚与后台一致性')
    else:
        print('[PASS] 页脚与后台同源同数：访客 %s / 浏览 %s' % (
            format(fd['uniques'], ','), format(fd['pv'], ',')))

    print()
    for f in fails:
        print('  -', f)
    print()
    code, msg = verdict(checked=checked, fails=fails, what='静态演示数据约束')
    return emit(code, msg)


if __name__ == '__main__':
    sys.exit(main())
