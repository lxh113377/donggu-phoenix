# -*- coding: utf-8 -*-
r"""tools/admin_export_test.py —— 后台导出 CSV 的产出物判据（headless CDP）。

## 为什么需要（轮171 新开维度）
轮170 真跑一次导出，抓到三处不一致（day key 填周号导致 48 行只有 7 个
唯一键、lang 行导裸码与界面口径分裂、toast 少报 40 行明细）。
这三处**任何读 DOM 的判据都测不到** —— 导出在页面不留痕迹，
点了就下载、DOM 不变。所以它长期无人守。

本判据的做法与轮170 一致：**劫持副作用，验产出物**。
  1. 包 window.Blob，从 parts[0] 拿到完整 CSV 文本（不真下载）
  2. URL.createObjectURL 换 stub
  3. MutationObserver 盯 toast 容器，拿到用户实际看到的提示

## 判据（每条都对着轮170 的一处真实缺陷写）
  A 导出可触发：点击后有 CSV 产出（拿不到 = 功能已死）
  B BOM 正确：首字符为 \ufeff（Excel 打开中文不乱码的前提）
  C 表头齐：含 section,key,start,end,pageview,visitors,ar_scene,summon,events
  D key 唯一性：day 行的 key 不得重复（48 天必须 48 个唯一值）
  E 语言行可读：lang 行不得只有裸码，须带中文名（与界面口径一致）
  F toast 说实话：toast 报的行数必须属实。支持两种写法并按语义匹配 ——
    单段「N 行」比对总数据行数；分段「A 行时间序列 + B 行明细」则
    A == week+day 行数、B == 其余 5 类 section 行数。
    （不做数字盲求和：文案一改就假报，轮171 我自己踩过一次。）
  G 数据自洽：每条 week 行必须 events == pv + ar_scene + summon。
    轮171 自查时从 >= 改成 ==：实测 7 周与合计全部严格相等，所以真不变式
    是相等；只查 < 会漏掉「events 偏大」，而那正是列错位/串行的症状。

## 为什么 F 也要判
「少报」不是排版问题而是诚信问题：用户据 toast 判断导出内容，
少报 40 行会让人以为只拿到时间序列，不会去找明细。

## 自检名册（结论文案按它动态计数，不写死「三项」）
S1 复刻轮170 三处缺陷、S2 修好后形态不误伤、S3 缺 BOM 报出、
S4a/S4b 给 G 双向覆盖（合法 week 行不误伤 + events 偏大必报）。
G 原本零自检覆盖 —— 合成数据里没有 week 行，等于写了条没人验过的检查。

用法：python tools/admin_export_test.py
"""

# 自检项名册：供结论文案动态计数（写死数字会变成假话，U-431 同族）
SELFTEST_LABELS = [
    'S1 复刻轮170 三处缺陷', 'S2 合法导出不误伤', 'S3 缺 BOM 报出',
    'S4a 自洽 week 行不误伤', 'S4b events 偏大报出',
]
import json
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
sys.path.insert(0, os.path.join(BASE, 'tools'))

HOOK = r'''(function(){
  window.__csv=null; window.__toast=null;
  var B=window.Blob;
  window.Blob=function(parts,opts){
    try{ window.__csv=String(parts[0]||''); }catch(e){}
    return new B(parts,opts);
  };
  URL.createObjectURL=function(){ return 'blob:stub'; };
  document.addEventListener('DOMContentLoaded', function(){
    var mo=new MutationObserver(function(){
      var c=document.querySelectorAll(
        '.toast,#toast,[class*=toast],[role=status]');
      for(var i=0;i<c.length;i++){
        var t=(c[i].textContent||'').trim();
        if(t && /导出/.test(t)){ window.__toast=t; }
      }
    });
    mo.observe(document.body,{childList:true,subtree:true,
      characterData:true});
  });
  return 1;})()'''

CLICK = r'''(function(){
  var b=document.getElementById('btn-export');
  if(!b) return JSON.stringify({missing:1});
  b.click(); return JSON.stringify({ok:1});})()'''

READ = r'''JSON.stringify({csv:window.__csv||"", toast:window.__toast||""})'''

HEADER = ('section,key,start,end,pageview,visitors,ar_scene,summon,events')


def parse_csv(csv):
    """CSV -> {header, rows:[(cells)], bySection:{name:[rows]}}"""
    lines = [l for l in csv.replace('\ufeff', '').split('\n')]
    rows = []
    for l in lines:
        if not l.strip() or l.startswith('#'):
            continue
        rows.append(l.split(','))
    if not rows:
        return None
    return {'header': rows[0], 'rows': rows[1:]}


def judge(csv, toast):
    """纯函数：产出物 -> 缺陷列表。自检直接喂合成数据验牙。"""
    fails = []
    if not csv:
        return ['A 导出无产出（点击后拿不到 CSV，功能已死）']
    if not csv.startswith('\ufeff'):
        fails.append('B 缺 UTF-8 BOM，Excel 打开中文会乱码')
    p = parse_csv(csv)
    if not p:
        return fails + ['C 导出内容为空（只有 BOM 没有数据）']
    if ','.join(p['header']) != HEADER:
        fails.append('C 表头不符：期望 %s，实得 %s'
                     % (HEADER, ','.join(p['header'])[:80]))
    # D day 行 key 唯一
    day_keys = [r[1] for r in p['rows'] if r and r[0] == 'day']
    if day_keys and len(set(day_keys)) != len(day_keys):
        dup = len(day_keys) - len(set(day_keys))
        fails.append('D day 行 key 重复 %d 个（%d 行只有 %d 个唯一键）'
                     % (dup, len(day_keys), len(set(day_keys))))
    # E lang 行须带中文名（第 3 字段）
    lang_rows = [r for r in p['rows'] if r and r[0] == 'lang']
    bad_lang = [r for r in lang_rows if len(r) < 3 or not r[2].strip()]
    if bad_lang:
        fails.append('E %d 个 lang 行只有裸码没有中文名（%s）'
                     % (len(bad_lang), bad_lang[0][1] if bad_lang else ''))
    # F toast 报的行数须属实。
    # 支持两种形态（都不苛求写法，只校验语义）：
    #   单段「N 行…」          -> N 应等于总数据行数
    #   分段「A 行时间序列 + B 行明细」-> A 应等于 week+day 行数，
    #                                    B 应等于其余 5 类 section 行数
    # 用「分段语义匹配」而不是数字盲求和：盲求和在文案改动后容易假报
    # （本轮就踩过：S2 的合成 toast 多写了一段，求和立刻对不上）。
    n_ts = sum(1 for r in p['rows'] if r and r[0] in ('week', 'day'))
    n_dt = len(p['rows']) - n_ts
    parts = re.findall(r'(\d+)\s*行(时间序列|明细)?', toast or '')
    if not parts:
        fails.append('F toast 里找不到行数播报（用户无法判断导出了什么）')
    else:
        for num_s, kind in parts:
            num = int(num_s)
            if kind == '时间序列':
                if num != n_ts:
                    fails.append('F toast 说 %d 行时间序列，实际 %d 行'
                                 % (num, n_ts))
            elif kind == '明细':
                if num != n_dt:
                    fails.append('F toast 说 %d 行明细，实际 %d 行'
                                 % (num, n_dt))
            else:
                if num != len(p['rows']):
                    fails.append('F toast 说 %d 行，实际 %d 行（差 %d）'
                                 % (num, len(p['rows']),
                                    len(p['rows']) - num))
    # G week 段自洽：events 必须 == pv + ar_scene + summon。
    # 轮171 自查时把这里从 >= 改成 ==：实测 7 周与合计全部严格相等
    # （W1 1484+577+154=2215=events ...），所以真不变式是相等。
    # 只查 < 会漏掉「events 偏大」—— 而那正是列错位/串行的症状，
    # 恰是导出物最该防的错。且不 break：每行都查，别只报第一条。
    for r in p['rows']:
        if len(r) >= 9 and r[0] == 'week':
            try:
                pv_, ar, su, ev = (int(r[4]), int(r[6]), int(r[7]),
                                   int(r[8]))
            except (ValueError, IndexError):
                fails.append('G week 行字段不是数字：%s' % ','.join(r)[:40])
                continue
            if ev != pv_ + ar + su:
                fails.append('G %s 行 events(%d) != pv+ar+summon(%d)'
                             % (r[1] if len(r) > 1 else 'week',
                                ev, pv_ + ar + su))
    return fails


def selftest():
    """三项自检：证明该报的报得出、合法的放得过。

    S1 复刻轮170 三处真实缺陷（day key 重复 + lang 裸码 + toast 少报）
       -> 必须全部报出。
    S2 修好后的形态（58 行、key 唯一、lang 带名、toast 数字对得上）
       -> 必须零缺陷。
    S3 缺 BOM -> 必须报出（Excel 乱码是真实事故）。
    """
    bad = []
    H = HEADER
    mk = lambda n: '\ufeff' + H + '\n' + '\n'.join(
        'day,2026-09-%02d,2026-09-%02d,周二,1,1,,,' % (i + 1, i + 1)
        for i in range(n))
    # S1 缺陷形态
    broken = ('\ufeff' + H + '\n'
              'day,W1,2026-09-01,周二,1,1,,,\n'
              'day,W1,2026-09-02,周三,1,1,,,\n'
              'lang,zh-CN,,,,1,,,\n')
    # toast 故意少报（说 2 行、实际 3 行）—— 轮170 的真实形态是
    # 少报 40 行；这里只要数字对不上，F 项就该报。
    # toast 故意少报：说 1 行时间序列、实际 2 行 day。
    f1 = judge(broken, '已导出 1 行时间序列 + 1 行明细')
    s1 = (any('D ' in x for x in f1) and any('E ' in x for x in f1)
          and any('F ' in x for x in f1))
    print('  [%s] S1 复刻轮170 三处缺陷 -> 报出 %d 条'
          % ('ok' if s1 else 'X', len(f1)))
    for x in f1:
        print('        -', x[:96])
    if not s1:
        bad.append('S1 复刻的三处真实缺陷没被全部报出')
    # S2 健康形态
    good = mk(3) + '\nlang,zh-CN,简体中文,,,,10,,,\n'
    f2 = judge(good, '已导出 3 行时间序列 + 1 行明细（场景/语言/屏幕/来源/国家）')
    s2 = not f2
    print('  [%s] S2 修好后的形态 -> %d 条缺陷'
          % ('ok' if s2 else 'X', len(f2)))
    for x in f2:
        print('        -', x[:96])
    if not s2:
        bad.append('S2 把合法导出误判成缺陷')
    # S3 缺 BOM
    f3 = judge(good.replace('\ufeff', '', 1),
               '已导出 3 行时间序列 + 1 行明细（场景/语言/屏幕/来源/国家）')
    s3 = any('B ' in x for x in f3)
    print('  [%s] S3 缺 BOM -> %s'
          % ('ok' if s3 else 'X', '报出' if s3 else '没报出'))
    if not s3:
        bad.append('S3 缺 BOM 没报出，Excel 乱码会漏网')
    # S4 G 项双向覆盖（轮171 自查发现 G 原本零自检覆盖 —— 合成数据里
    #     根本没有 week 行，等于写了一条没人验过的检查）。
    # S4a 合法 week 行（events == pv+ar+summon）不得误报；
    # S4b events 偏大（列错位/串行的症状，正是把 >= 改成 == 要抓的东西）
    #     必须报出。只测 S4b 不够：那样 G 若被写成恒报，也发现不了。
    okweek = ('\ufeff' + H + '\n'
              'week,W1,2026-09-01,2026-09-06,1484,1183,577,154,2215\n')
    g4a = judge(okweek, '已导出 1 行时间序列')
    s4a = not any('G ' in x for x in g4a)
    print('  [%s] S4a 合法 week 行（1484+577+154=2215）-> %s'
          % ('ok' if s4a else 'X', '不误伤' if s4a
             else '误报：%s' % [x for x in g4a if 'G ' in x][:1]))
    if not s4a:
        bad.append('S4a 把自洽的 week 行误判成缺陷')
    bigweek = ('\ufeff' + H + '\n'
               'week,W1,2026-09-01,2026-09-06,1484,1183,577,154,9999\n')
    g4b = judge(bigweek, '已导出 1 行时间序列')
    s4b = any('G ' in x for x in g4b)
    print('  [%s] S4b events 偏大（列错位症状）-> %s'
          % ('ok' if s4b else 'X', '报出' if s4b else '没报出'))
    if not s4b:
        bad.append('S4b events 偏大没报出，G 项等于没牙')
    return bad


def main():
    print('=== 后台导出 CSV 产出物判据 ===')
    print()
    print('=== 尺子有效性自检 ===')
    bad = selftest()
    if bad:
        print()
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad:
            print('  -', b)
        return 1
    print()
    from cdp_client import Chrome, SiteServer, find_chrome
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（环境问题，非判据通过）')
        return 0
    srv = SiteServer(SITE, port=8974)
    ch = Chrome()
    csv = toast = ''
    try:
        page, tid = ch.new_page(1440, 900)
        try:
            page.call('Page.enable')
            page.call('Page.addScriptToEvaluateOnNewDocument',
                      {'source': HOOK})
            ch.navigate(page, srv.url('/admin/index.html?exp=1'))
            time.sleep(3.0)
            d = json.loads(page.eval_js(CLICK, timeout=25))
            if d.get('missing'):
                print('RESULT: FAIL  页面上找不到 #btn-export（导出入口消失）')
                return 1
            time.sleep(1.2)
            r = json.loads(page.eval_js(READ, timeout=25))
            csv = r.get('csv') or ''
            toast = r.get('toast') or ''
        finally:
            try:
                page.close()
            except Exception:
                pass
            ch.close_page(tid)
    finally:
        ch.close()
        srv.stop()

    print('=== 实跑导出 ===')
    print('  CSV 字节:', len(csv.encode('utf-8')))
    print('  toast  :', repr(toast[:80]))
    fails = judge(csv, toast)
    if fails:
        print()
        print('RESULT: FAIL  %d 处导出缺陷：' % len(fails))
        for f in fails:
            print('  -', f)
        return 1
    n = len(parse_csv(csv)['rows'])
    print()
    print('RESULT: PASS  %d 行导出全部合规（BOM/表头/day key 唯一/'
          'lang 带中文名/toast 行数属实/week 自洽），'
          '且 %d 项自检证明该报的报得出'
          % (n, len(SELFTEST_LABELS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
