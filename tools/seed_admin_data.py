# -*- coding: utf-8 -*-
"""tools/seed_admin_data.py —— 生成后台访问数据的仿真样本（老大 2026-10-21 指定）。

## 需求
后台访问数据用随机仿真数据，访问数据总量在 1 万到 2 万左右。

## 口径：两个数都落在 1 万~2 万
后台「累计访问」卡显示的是 pageview 计数，而 visits 表总行数含全部事件。
所以目标：pageview ≈ 11,500（累计访问）、总行数 ≈ 17,000（数据总量），
两者都在 1 万~2 万内 —— 不论按哪种口径读都符合要求。

## 必须与真实写入行为一致（否则后台图表会露馅）
读 functions/api/track.js 与 site/assets/js/analytics.js 得出：
  · 事件只有 3 种：pageview / ar_scene / summon
    （analytics.js 的事件面注释；ar_scene 的 scene 取自 /^#ar=([a-z]+)$/，
     即 craft / red / phoenix 三个）
  · vid 是 16 位小写十六进制（crypto 8 字节）
  · screen 形如 "390x844"（screen.width + 'x' + screen.height）
  · lang 是 navigator.language（zh-CN 等）
  · day 必须等于 ts 的 **UTC 日期** —— 真实写入用列默认值
    date('now') 与 strftime('now')，两者同源于同一个 UTC 时刻。
    本脚本按访客本地时区生成小时再折算 UTC，day 由最终 UTC ts 反推，
    保证「今日逐时」与「30 天序列」两张图互相自洽。
  · country/city/tz 由边缘按真实 IP 注入 -> 仿真时与 UA 的语种/机型保持一致

## 分布设计（贴近「扫码看展」的真实形态）
  · 移动端 ~78%（现场二维码 + 微信是主入口），桌面 ~20%，平板 ~2%
  · 微信内浏览器占移动端大头（UA 含 MicroMessenger）
  · referrer：直接访问（扫码无 referer）最多，其次微信图文、百度、必应
  · 地域以江西本地与长三角/珠三角为主，境外少量
  · 日曲线：展期临近收尾时走高（现场活动 + 图文推送），周末小幅上扬
  · 逐时：本地时间 9-11 与 19-22 双峰，凌晨低谷
  · 访客复访率 ~22%（同一 vid 在多天出现）

## 幂等保护
默认拒绝在已有数据（>500 行）的库上重复灌入，需 --force。
"""
import argparse
import datetime as dt
import os
import random
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_SQL = os.path.join(BASE, '_qa', 'seed_visits.sql')

PAGEVIEW_TARGET = 12200
DAYS = 45
SEED = 20261021

# ---- 本地小时的双峰曲线（看展 + 微信阅读习惯）----
HOUR_W = [0.4, 0.2, 0.1, 0.1, 0.1, 0.2, 0.6, 1.4, 2.4, 3.0, 3.2, 2.8,
          2.0, 1.8, 2.2, 2.6, 2.8, 3.0, 2.8, 2.6, 2.4, 2.0, 1.4, 0.8]
HOUR_CUM = []
acc = 0.0
for w in HOUR_W:
    acc += w
    HOUR_CUM.append(acc)
HOUR_TOTAL = acc


def pick_hour(rnd):
    x = rnd.random() * HOUR_TOTAL
    lo, hi = 0, len(HOUR_CUM) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if x <= HOUR_CUM[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


# ---- 设备画像：UA / screen / lang / 地域 必须成套 ----
# (权重, ua, screen, 时区偏移分钟, 语种池, 地域池)
WECHAT_IOS = {
    'ua': ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 '
           '(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003137) NetType/WIFI'),
    'screens': ['390x844', '393x852', '430x932', '375x667', '414x896', '360x780'],
    'share': 0.30,
}
SAFARI_IOS = {
    'ua': ('Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 '
           '(KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'),
    'screens': ['390x844', '430x932', '393x852', '375x812'],
    'share': 0.10,
}
WECHAT_ANDROID = {
    'ua': ('Mozilla/5.0 (Linux; Android 14; 23049RAD8C Build/UKQ1.230924.001; wv) '
           'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.134 '
           'Mobile Safari/537.36 XWEB/1260089 MMWEBSDK/20240801 MicroMessenger/8.0.50'),
    'screens': ['360x780', '393x851', '411x891', '384x854', '320x720'],
    'share': 0.22,
}
CHROME_ANDROID = {
    'ua': ('Mozilla/5.0 (Linux; Android 13; SM-S9110 Build/TP1A.220624.014) '
           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'),
    'screens': ['360x780', '393x873', '412x915', '320x640'],
    'share': 0.08,
}
WIN_EDGE = {
    'ua': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'),
    'screens': ['1920x1080', '1536x864', '2560x1440', '1366x768'],
    'share': 0.13,
}
WIN_CHROME = {
    'ua': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'),
    'screens': ['1920x1080', '1440x900', '1680x1050', '1280x720'],
    'share': 0.05,
}
MAC_SAFARI = {
    'ua': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
           '(KHTML, like Gecko) Version/17.6 Safari/605.1.15'),
    'screens': ['1440x900', '2560x1440', '1680x1050'],
    'share': 0.05,
}
PC_WECHAT = {
    # Windows 微信桌面端内置浏览器（图文转发到电脑上的真实场景）
    'ua': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 QQBrowser/13.5.5087.400 '
           'MicroMessenger/3.9.12.45'),
    'screens': ['1920x1080', '1536x864', '1366x768'],
    'share': 0.05,
}
IPAD = {
    'ua': ('Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 '
           '(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'),
    'screens': ['1024x1366', '820x1180', '1488x2266'],
    'share': 0.02,
}
PROFILES = [WECHAT_IOS, SAFARI_IOS, WECHAT_ANDROID, CHROME_ANDROID,
            WIN_EDGE, WIN_CHROME, MAC_SAFARI, IPAD, PC_WECHAT]
PROFILE_SHARES = [p['share'] for p in PROFILES]
assert abs(sum(PROFILE_SHARES) - 1.0) < 1e-6, sum(PROFILE_SHARES)

# 语种按设备族给权重（中文为主，境外少量）
LANG_BY_FAMILY = {
    'mobile_cn': [('zh-CN', 0.90), ('zh-CN;en-US', 0.04), ('en-US', 0.04), ('zh-TW', 0.02)],
    'desktop_cn': [('zh-CN', 0.82), ('en-US', 0.12), ('ja-JP', 0.03), ('zh-TW', 0.03)],
    'tablet': [('zh-CN', 0.75), ('en-US', 0.25)],
}
FAMILY_OF = {id(WECHAT_IOS): 'mobile_cn', id(SAFARI_IOS): 'mobile_cn',
             id(WECHAT_ANDROID): 'mobile_cn', id(CHROME_ANDROID): 'mobile_cn',
             id(WIN_EDGE): 'desktop_cn', id(WIN_CHROME): 'desktop_cn',
             id(MAC_SAFARI): 'desktop_cn', id(IPAD): 'tablet',
             id(PC_WECHAT): 'desktop_cn'}

# 地域：(国家, 城市, 时区, 偏移分钟, 权重) —— CN 为主，含展期实地与线上
GEO = [
    ('CN', 'Nancheng', 'Asia/Shanghai', 480, 0.20),
    ('CN', 'Ji_an', 'Asia/Shanghai', 480, 0.14),
    ('CN', 'Shanghai', 'Asia/Shanghai', 480, 0.11),
    ('CN', 'Guangzhou', 'Asia/Shanghai', 480, 0.09),
    ('CN', 'Shenzhen', 'Asia/Shanghai', 480, 0.08),
    ('CN', 'Hangzhou', 'Asia/Shanghai', 480, 0.07),
    ('CN', 'Beijing', 'Asia/Shanghai', 480, 0.07),
    ('CN', 'Chengdu', 'Asia/Shanghai', 480, 0.05),
    ('CN', 'Nanjing', 'Asia/Shanghai', 480, 0.04),
    ('CN', 'Wuhan', 'Asia/Shanghai', 480, 0.04),
    ('CN', 'Xian', 'Asia/Shanghai', 480, 0.03),
    ('CN', 'Chongqing', 'Asia/Shanghai', 480, 0.02),
    ('TW', 'Taipei', 'Asia/Taipei', 480, 0.015),
    ('HK', 'Hong_Kong', 'Asia/Hong_Kong', 480, 0.015),
    ('JP', 'Tokyo', 'Asia/Tokyo', 540, 0.015),
    ('SG', 'Singapore', 'Asia/Singapore', 480, 0.015),
    ('US', 'Los_Angeles', 'America/Los_Angeles', -420, 0.01),
    ('US', 'New_York', 'America/New_York', -240, 0.01),
    ('GB', 'London', 'Europe/London', 60, 0.01),
    ('DE', 'Frankfurt', 'Europe/Berlin', 120, 0.01),
    ('AU', 'Sydney', 'Australia/Sydney', 600, 0.01),
    ('KR', 'Seoul', 'Asia/Seoul', 540, 0.01),
    ('CA', 'Toronto', 'America/Toronto', -240, 0.005),
]
GEO_CUM = []
g = 0.0
for row in GEO:
    g += row[4]
    GEO_CUM.append(g)
GEO_TOTAL = g

# referrer：扫码无 referer 最多，其次微信图文与搜索
REFERRERS = [
    ('', 0.44),
    ('https://mp.weixin.qq.com/', 0.20),
    ('https://www.baidu.com/', 0.11),
    ('https://m.baidu.com/s', 0.05),
    ('https://www.bing.com/', 0.04),
    ('https://www.google.com/', 0.04),
    ('https://www.douyin.com/', 0.04),
    ('https://github.com/', 0.025),
    ('https://www.zhihu.com/', 0.02),
    ('https://t.co/', 0.015),
]
REF_CUM = []
r_ = 0.0
for row in REFERRERS:
    r_ += row[1]
    REF_CUM.append(r_)
REF_TOTAL = r_

# 路径：单页站，pages.dev 部署在根
PATHS = [('/', 0.93), ('/index.html', 0.07)]

# 场景热度：图腾（默认入口）> 一木成像 > 红色地标
SCENES = [('phoenix', 0.46), ('craft', 0.33), ('red', 0.21)]


def weighted(rnd, table, cum, total):
    x = rnd.random() * total
    lo, hi = 0, len(cum) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if x <= cum[mid]:
            hi = mid
        else:
            lo = mid + 1
    return table[lo]


def q(s):
    """SQL 字面量（NULL 或单引号转义）。"""
    if s is None or s == '':
        return 'NULL' if s == '' or s is None else "''"
    return "'" + str(s).replace("'", "''") + "'"


def gen(rnd, today_utc, now_utc):
    start = today_utc - dt.timedelta(days=DAYS - 1)
    # 日权重：整体上行 + 展期收尾冲刺 + 周末上扬 + 噪声
    day_weights = []
    for i in range(DAYS):
        d = start + dt.timedelta(days=i)
        trend = 0.34 + 0.66 * (i / float(DAYS - 1))
        ramp = 1.0
        if i >= DAYS - 12:                      # 展期现场活动
            ramp = 1.0 + 0.55 * ((i - (DAYS - 12)) / 11.0)
        wk = 1.14 if d.weekday() >= 5 else 1.0   # 周末
        noise = rnd.uniform(0.84, 1.16)
        day_weights.append(trend * ramp * wk * noise)
    scale = PAGEVIEW_TARGET / sum(day_weights)

    pool = []           # 已出现过的 vid，供复访抽样
    rows = []
    stats = {'pageview': 0, 'ar_scene': 0, 'summon': 0}
    per_day = {}

    for i in range(DAYS):
        d = start + dt.timedelta(days=i)
        pv = max(1, int(round(day_weights[i] * scale)))
        for _ in range(pv):
            # 访客身份：22% 复访已有 vid
            if pool and rnd.random() < 0.22:
                vid = rnd.choice(pool)
            else:
                vid = '%016x' % rnd.getrandbits(64)
                if len(pool) < 9000:
                    pool.append(vid)
            prof = weighted(rnd, PROFILES,
                            [sum(PROFILE_SHARES[:k + 1]) for k in range(len(PROFILES))],
                            sum(PROFILE_SHARES))
            fam = FAMILY_OF[id(prof)]
            lang = weighted(rnd, [x[0] for x in LANG_BY_FAMILY[fam]],
                            [sum(y[1] for y in LANG_BY_FAMILY[fam][:k + 1])
                             for k in range(len(LANG_BY_FAMILY[fam]))],
                            sum(y[1] for y in LANG_BY_FAMILY[fam]))
            geo = weighted(rnd, GEO, GEO_CUM, GEO_TOTAL)
            country, city, tz, off_min, _w = geo
            screen = rnd.choice(prof['screens'])
            ref = weighted(rnd, [x[0] for x in REFERRERS], REF_CUM, REF_TOTAL)
            path = weighted(rnd, [x[0] for x in PATHS],
                            [0.93, 1.0], 1.0)

            # 本地小时 -> UTC 时刻；day 由最终 UTC 反推（与真实默认值同源）
            lh = pick_hour(rnd)
            local_noon = dt.datetime(d.year, d.month, d.day, lh,
                                     rnd.randrange(60), rnd.randrange(60))
            ts_utc = local_noon - dt.timedelta(minutes=off_min)
            # 真实系统不可能写入未来时间戳：西半球本地晚高峰会折算成
            # UTC 次日，落在最后一天时就是「明天」。裁掉。
            if ts_utc > now_utc:
                continue
            # 若折算后落到相邻 UTC 日，以 UTC 日为准（真实行为）
            day = ts_utc.date().isoformat()
            ts = ts_utc.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ' % rnd.randrange(1000)
            rows.append((ts, day, 'pageview', path, None, vid, ref,
                         prof['ua'], lang, screen, country, city, tz))
            stats['pageview'] += 1

            # AR 场景：30% 的访客会进场景，其中部分看两个
            if rnd.random() < 0.30:
                n_scene = 2 if rnd.random() < 0.30 else 1
                chosen = []
                for _k in range(n_scene):
                    sc = weighted(rnd, [x[0] for x in SCENES],
                                  [0.46, 0.79, 1.0], 1.0)
                    if sc in chosen:
                        continue
                    chosen.append(sc)
                    t2 = ts_utc + dt.timedelta(seconds=rnd.randint(25, 400))
                    rows.append((t2.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ'
                                 % rnd.randrange(1000), t2.date().isoformat(),
                                 'ar_scene', path, sc, vid, ref, prof['ua'],
                                 lang, screen, country, city, tz))
                    stats['ar_scene'] += 1
            # 唤凤：站内唯一主动互动入口，12%
            if rnd.random() < 0.12:
                t3 = ts_utc + dt.timedelta(seconds=rnd.randint(6, 120))
                rows.append((t3.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ'
                             % rnd.randrange(1000), t3.date().isoformat(),
                             'summon', path, None, vid, ref, prof['ua'],
                             lang, screen, country, city, tz))
                stats['summon'] += 1
    # 按**落库的 UTC 日**统计（真实 day 列即 ts 的 UTC 日期，
    # 时区折算后可能落到相邻日）—— 这样才与后台 30 天序列图一致
    for r in rows:
        if r[2] == 'pageview':
            per_day[r[1]] = per_day.get(r[1], 0) + 1
    return rows, stats, per_day


COLS = ('ts, day, event, path, scene, vid, referrer, ua, lang, screen,'
        ' country, city, tz')


def write_sql(rows, batch=250):
    lines = ['-- 自动生成：后台访问数据仿真样本（tools/seed_admin_data.py）',
             '-- 事件词表与字段形态对齐 functions/api/track.js 的真实写入',
             '']
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        vals = ',\n  '.join(
            '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)' % (
                q(r[0]), q(r[1]), q(r[2]), q(r[3]), q(r[4]), q(r[5]), q(r[6]),
                q(r[7]), q(r[8]), q(r[9]), q(r[10]), q(r[11]), q(r[12]))
            for r in chunk)
        lines.append('INSERT INTO visits (%s) VALUES\n  %s;' % (COLS, vals))
        lines.append('')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true',
                    help='已有数据时也生成（默认拒绝，避免重复灌入）')
    ap.add_argument('--current', type=int, default=0,
                    help='目标库当前 visits 行数（用于幂等保护）')
    a = ap.parse_args()

    if a.current > 500 and not a.force:
        print('RESULT: FAIL  目标库已有 %d 行，拒绝重复灌入（需 --force）' % a.current)
        return 1

    rnd = random.Random(SEED)
    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    today = now_utc.date()
    rows, stats, per_day = gen(rnd, today, now_utc)

    total = len(rows)
    pv = stats['pageview']
    print('生成 %d 行：pageview %d / ar_scene %d / summon %d' % (
        total, pv, stats['ar_scene'], stats['summon']))
    print('覆盖 %d 天，日均 pageview %.0f，最少 %d，最多 %d' % (
        len(per_day), pv / float(len(per_day)), min(per_day.values()),
        max(per_day.values())))
    ok_pv = 10000 <= pv <= 20000
    ok_total = 10000 <= total <= 20000
    print('口径检查：pageview %s（1万~2万） 总行数 %s（1万~2万）' % (
        'OK' if ok_pv else 'X', 'OK' if ok_total else 'X'))
    if not (ok_pv and ok_total):
        print('RESULT: FAIL  数据量不符合要求')
        return 1

    sql = write_sql(rows)
    os.makedirs(os.path.dirname(OUT_SQL), exist_ok=True)
    open(OUT_SQL, 'w', encoding='utf-8', newline='\n').write(sql)
    print('SQL 写出 %s（%.1f KB，%d 条 INSERT）' % (
        os.path.relpath(OUT_SQL, BASE).replace('\\', '/'),
        len(sql) / 1024.0, (total + 249) // 250))
    print('RESULT: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
