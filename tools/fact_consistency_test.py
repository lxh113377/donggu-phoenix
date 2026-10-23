# -*- coding: utf-8 -*-
r"""tools/fact_consistency_test.py —— 同一个人的生卒年与年龄叙述必须自洽。

## 为什么需要（轮141 一手缺陷）
ar-scenes.js 纪念碑画 "1901 - 1931"，而 ar-data.js 同场景解说写「年仅 33 岁」，
1931 - 1901 = 30 与 33 差 3 —— 同一页两处数据互相矛盾。权威依据（人民日报
2024-09-27《黄公略烈士遗骸在江西吉安安葬》）为「1898 年出生…时年 33 岁」，
故错的是纪念碑生年，已改 1898。

本判据只问「仓库自己说的两句话能不能对上」，**不评判外部史实对错**
（那需权威源，人工核）。红色展陈站后续必然增补更多烈士与人物，
同类错误会复发，所以这条要机器守。

## 人名口径（重要，写错过一次）
人名**只取展示用的姓名**：fillText("黄公略") 这类引号内中文名。
不用「紧邻年龄词前的中文」当姓名 —— 那样会把「年仅 33 岁」前的
「…牺牲」一起吞进捕获组（正则贪婪 {2,4} 会取到「黄公略牺」），
而真实站点里更会取成「红三军长」这种非人名片段，导致永远关联不上、
判据恒绿（自检 S1 就是这样把无牙暴露出来的）。

## 判据（跨文件归集：名字可能在一个文件、解说过在另一个文件）
  1. names  = 所有 fillText("中文名") 与引号内中文姓名
  2. ages   = 对每个 name，取**包含该名**的字符串字面量里的
              （年仅|时年|享年|终年）N 岁
  3. ranges = 对每个四位年份区间 A—B：
              · 同一字面量内出现某 name -> 关联该 name
              · 否则归属「本文件最近的前置 fillText 姓名」（纪念碑式排版：
                日期行就在名字行下面）。不用固定回溯窗 —— 轮141 就是
                160 字魔数差一点漏判，见 gather() 内注释
  4. name 同时有 age 与 range 时才判定：|(B - A) - N| <= 1
     容差 1 留给虚岁/周岁之差；轮141 那个错差 3，远超任何口径差异
  5. 区间倒挂（B < A）判红；单边出现列 INFO（无从对账不判红）
  6. 同一人的多个年龄叙述互斥（既写 33 又写 40）判红

## 尺子有效性自检（U-427）
  S1 同名差 3 岁（复刻轮141 真错）  -> 必须 FAIL
  S2 同名完全自洽                   -> 必须 PASS
  S3 差 1（虚岁/周岁口径）          -> 必须 PASS
  S4 只有年龄、无区间               -> 不得判红
  S5 注释里的历史值（原写 1901）    -> 不得算缺陷（轮141 同族第 3 次踩坑回归）
  S6 生卒区间倒挂                   -> 必须 FAIL
  S7 跨文件关联（解说在另一文件）   -> 必须 FAIL（轮141 的真实形态）

缺文件 -> SKIP 并说明（未测不等于通过）。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')

# 引号一律用 [\x22\x27]：本文件曾因源码里嵌套引号被截断写坏过
RE_NAME_DRAW = re.compile(r'fillText\(\s*[\x22\x27]([一-鿿]{2,4})[\x22\x27]')
RE_CJK_QUOTED = re.compile(r'[\x22\x27]([一-鿿]{2,4})[\x22\x27]')
RE_AGE_NUM = re.compile(r'(?:年仅|时年|享年|终年)\s*(\d{1,3})\s*岁')
RE_RANGE = re.compile(r'(?<![\d-])(\d{4})\s*[-—–]\s*(\d{4})(?![\d])')
RE_STR = re.compile(r'[\x22\x27]([^\x22\x27\n]{4,400})[\x22\x27]')

SCAN = ['assets/data/ar-data.js', 'assets/js/ar-scenes.js',
        'assets/data/culture.js', 'index.html']


def texts():
    out = []
    for rel in SCAN:
        p = os.path.join(SITE, *rel.split('/'))
        if os.path.exists(p):
            out.append((rel, io.open(p, encoding='utf-8',
                                     errors='ignore').read()))
    return out


def strip_blocks(src):
    r"""剥块注释、行注释、HTML 注释。

    轮141 教训（同族第 3 次踩坑）：查字样必须先剥注释 ——
    我写的校正注释里就有「原写 "1901 - 1931"」这句话，
    不剥会把说明文字当成缺陷。S5 就是这条的回归测试。
    """
    s = re.sub(r'/\*.*?\*/', ' ', src, flags=re.S)
    s = re.sub(r'^\s*//.*$', ' ', s, flags=re.M)
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    return s


def gather(pairs):
    """跨文件归集：返回 names / ages / ranges / loose。"""
    names = []
    bodies = []
    for rel, src in pairs:
        b = strip_blocks(src)
        bodies.append((rel, b))
        for m in RE_NAME_DRAW.finditer(b):
            if m.group(1) not in names:
                names.append(m.group(1))
    ages = {}
    ranges = {}
    loose = []
    for rel, b in bodies:
        # 1) 年龄：字面量里含某个已知姓名，才认为那是那个名字的年龄
        for m in RE_STR.finditer(b):
            lit = m.group(1)
            for am in RE_AGE_NUM.finditer(lit):
                for n in names:
                    if n in lit:
                        ages.setdefault(n, []).append(int(am.group(1)))
        # 2) 本文件的姓名锚点（按出现位置排序）
        anchors = sorted([(m.group(1), m.start())
                          for m in RE_NAME_DRAW.finditer(b)],
                         key=lambda x: x[1])
        for m in RE_RANGE.finditer(b):
            a, bb = int(m.group(1)), int(m.group(2))
            hit = None
            for q in RE_STR.finditer(b):
                if q.start() <= m.start() <= q.end():
                    for n in names:
                        if n in q.group(1):
                            hit = n
                            break
                    break
            if hit is None:
                # 归属「最近的前置姓名」：纪念碑式排版里，日期行就在名字行下面。
                # 轮141 漏判的教训：原先用固定回溯窗（160 字），而真实代码里
                # fillText("黄公略") 与 fillText("1898 - 1931") 之间夹着 3 行
                # canvas 设置 + 我的校正注释，剥注释后仍相距 181 字 —— 差一点
                # 就漏。魔数窗口必然在某个排版下失效，改成语义规则：
                # 取位置在该区间之前、且离它最近的姓名锚点（无中间姓名隔断）。
                prior = [(n, pos) for (n, pos) in anchors if pos < m.start()]
                if prior:
                    n0, pos0 = prior[-1]
                    gap = m.start() - pos0
                    # 上限只防「跨整个文件乱关联」，取宽到足以容纳代码排版
                    if n0 in names and gap < 4000:
                        hit = n0
            if hit:
                ranges.setdefault(hit, []).append((a, bb, rel))
            else:
                loose.append((a, bb, m.group(0).strip(), rel,
                              b[max(0, m.start() - 40):m.start()][-24:]))
    return names, ages, ranges, loose


def check(pairs):
    names, ages, ranges, loose = gather(pairs)
    fails, infos = [], []
    for n in sorted(set(ages) | set(ranges)):
        an = sorted(set(ages.get(n, [])))
        rn = ranges.get(n, [])
        if an and len(an) > 1:
            fails.append(u'「%s」的年龄叙述互斥：同时出现 %s 岁'
                         % (n, u'、'.join(str(x) for x in an)))
        if an and not rn:
            infos.append(u'「%s」只有年龄叙述 %s 岁、无年份区间，无从对账'
                         % (n, u'/'.join(str(x) for x in an)))
            continue
        if rn and not an:
            infos.append(u'「%s」只有年份区间、无年龄叙述，无从对账' % n)
            continue
        if not an or not rn:
            continue
        # 关键语义（边界探针逼出来的）：判据分不清哪个是「生卒区间」、
        # 哪个是「任职/战斗时段」。所以规则是：只要**有一个**区间的跨度
        # 能对上某个年龄（±1），就认为这个人自洽 —— 其余区间视作任期时段，
        # 不参与年龄对账。全对不上才判红（轮141 那次：唯一的区间 1901-1931
        # 跨度 30、解说 33，没有任何区间能对上 -> 必须红）。
        ok_any = False
        bad = []
        for (a, b, rel) in rn:
            if b < a:
                bad.append(u'倒挂 %d>%d' % (b, a))
                continue
            calc = b - a
            if any(abs(calc - x) <= 1 for x in an):
                ok_any = True
            else:
                bad.append(u'%d-%d 推 %d 岁' % (a, b, calc))
        if not ok_any and bad:
            fails.append(
                u'「%s」没有任何年份区间能对上年龄叙述 %s 岁：'
                u'对不上的区间 %s（容差 ±1 已涵盖虚岁/周岁之差；'
                u'若其中确有任期时段，请把它改到不与年龄同字面量处）'
                % (n, u'/'.join(str(x) for x in an), u'；'.join(bad)))
    for (a, b, raw, rel, _sp) in loose:
        infos.append(u'游离年份区间「%s」（%s）未关联到具名人物，未纳入对账'
                     % (raw, rel))
    return names, ages, ranges, fails, infos


def draw(name, span):
    q = chr(34)
    return ('ctx.fillText(' + q + name + q + ', mx, 1);' + chr(10)
            + 'ctx.fillText(' + q + span + q + ', mx, 2);')


def narrate(name, age):
    q = chr(34)
    return 'body: ' + q + u'红军指挥员' + name + u'在战斗中牺牲，年仅 ' \
        + str(age) + u' 岁。' + q + ','


SELFTEST = [
    (u'S1 同名差 3 岁（复刻轮141 真错）',
     [(u'f1.js', draw(u'黄公略', '1901 - 1931')),
      (u'f2.js', narrate(u'黄公略', 33))], True),
    (u'S2 同名完全自洽',
     [(u'f1.js', draw(u'黄公略', '1898 - 1931')),
      (u'f2.js', narrate(u'黄公略', 33))], False),
    (u'S3 差 1（虚岁/周岁口径）须放过',
     [(u'f1.js', draw(u'张三志', '1900 - 1931')),
      (u'f2.js', narrate(u'张三志', 31))], False),
    (u'S4 只有年龄无区间不得判红',
     [(u'f2.js', narrate(u'李四光', 29))], False),
    (u'S6 生卒区间倒挂',
     [(u'f1.js', draw(u'王五', '1931 - 1898')),
      (u'f2.js', narrate(u'王五', 33))], True),
    (u'S9 同一人含任期时段（生卒+任职两区间）不得判红',
     [(u'f.js', draw(u'黄公略', '1898 - 1931') + chr(10)
       + 'ctx.fillText(' + chr(34) + '1918 - 1931' + chr(34) + ', mz);'),
      (u'g.js', narrate(u'黄公略', 33))], False),
    (u'S10 多区间但全对不上年龄 -> 必须 FAIL',
     [(u'f.js', draw(u'周八', '1901 - 1931') + chr(10)
       + 'ctx.fillText(' + chr(34) + '1925 - 1931' + chr(34) + ', mz);'),
      (u'g.js', narrate(u'周八', 40))], True),
    (u'S8 同一个人两处年龄互斥',
     [(u'f1.js', draw(u'赵六', '1900 - 1931')),
      (u'f2.js', narrate(u'赵六', 31) + chr(10) + narrate(u'赵六', 40))],
     True),
]


def selftest():
    bad = []
    for label, pairs, expect_fail in SELFTEST:
        _n, _a, _r, fails, _i = check(pairs)
        got = bool(fails)
        ok = got == expect_fail
        print('  [%s] %s%s' % ('ok' if ok else 'X', label,
                               '' if ok else ' -> 实得 %s' % (fails or '无命中')))
        if not ok:
            bad.append(label)
    # S5：注释里的历史值不得算缺陷（轮141 同族第 3 次踩坑的回归）
    q = chr(34)
    cmt = (u'/* 轮141 校正：原写 ' + q + u'1901 - 1931' + q
           + u'，与解说「年仅 33 岁」矛盾。 */' + chr(10))
    _n, _a, _r, fails5, _i = check(
        [(u'f1.js', cmt + draw(u'黄公略', u'1898 - 1931')),
         (u'f2.js', narrate(u'黄公略', 33))])
    ok5 = not fails5
    print('  [%s] S5 注释里的历史值不得算缺陷%s'
          % ('ok' if ok5 else 'X', '' if ok5 else ' -> 实得 %s' % fails5))
    if not ok5:
        bad.append(u'S5 注释未剥净')
    # S7：跨文件关联（轮141 的真实形态：名字区间在 scenes、解说在 data）
    _n7, _a7, _r7, f7, _i7 = check(
        [(u'ar-scenes.js', draw(u'钱七', '1899 - 1930')),
         (u'ar-data.js', narrate(u'钱七', 25))])
    ok7 = bool(f7)
    print('  [%s] S7 跨文件也能关联并报出矛盾%s'
          % ('ok' if ok7 else 'X', '' if ok7 else '（关联失败，判据对真实'
             '排版无效）'))
    if not ok7:
        bad.append(u'S7 跨文件未关联')
    return bad


def main():
    ts = texts()
    if not ts:
        print('RESULT: SKIP  找不到要扫的文件（未测不等于通过）')
        return 0
    print('=== 尺子有效性自检 ===')
    bs = selftest()
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1
    names, ages, ranges, fails, infos = check(ts)
    both = sorted(set(ages) & set(ranges))
    print('=== 对账范围 ===')
    print('  扫 %d 个文件；具名展示人物 %d 位；有关联区间 %d 位、'
          '有年龄叙述 %d 位' % (len(ts), len(names), len(ranges), len(ages)))
    print('  两处都有、真正可对账的人：%s'
          % (u'、'.join(both) if both else u'（本轮扫描范围内无人）'))
    print()
    if infos:
        print(u'提示（不判红，单边无从对账）：')
        for x in infos[:10]:
            print('  ·', x)
        if len(infos) > 10:
            print('  …（共 %d 条）' % len(infos))
        print()
    if fails:
        print(u'发现自相矛盾：')
        for x in fails:
            print('  -', x)
        print()
        print('RESULT: FAIL  %d 处内部矛盾（同项目两处数据对不上，'
              '不涉外部史实判断）' % len(fails))
        return 1
    print('RESULT: PASS  %d 个文件里可对账人物的生卒年与年龄叙述全部自洽，'
          '且 %d 项自检证明该判的判得（含复刻轮141 那个差 3 岁的真错）、'
          '不该判的不误伤' % (len(ts), len(SELFTEST) + 2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
