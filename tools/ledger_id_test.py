# -*- coding: utf-8 -*-
r"""tools/ledger_id_test.py —— 台账 U 号唯一性与完整性判据（纯静态，CI 可跑）。

## 为什么需要它（轮54 实测事故）
升级台账 memory/09-upgrade-ledger.md 是「已登记」的唯一凭据。
本项目有并行端同时在写它，撞号会让两条记录互相覆盖语义 ——
谁都不知道某条改进到底做没做。

轮51 已撞过一次（并行端主动让号并写下教训）。
轮54 又撞 8 对：我在轮52/53 重复使用了轮51 已占用的 U-128~U-135。
两次都是「凭记忆续编」造成的。人工纪律靠不住，所以要有判据。

## 判据
1. 行首条目号不得重复（撞号即 FAIL）
2. 号段连续无空洞（跳号说明有记录被误删）
3. 每条必须有轮次与非空的状态列
4. 正文交叉引用的号必须存在（引用已消失的号 = 断链）

## 本判据第一版自己误报了 4 项（轮54，教训同 U-133）
  · 轮次字段实测有 "3-6"（U-02 那行），正则限死 \d+ 会**整行漏解析**，
    连带误报「号段空洞 U-2」与「U-02 断链」
  · 状态用枚举白名单太窄，把「已核实无问题 / 部分完成 / 已记录」判成缺状态
  → 改为：轮次只要求非空；状态按列位取，非空即合格。
台账本身是健康的，错在判据 —— 记在这里以免下次又去"修数据"。

零样本判 SKIP 不判 PASS（gate_guard 的规矩）。
"""
import collections
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(BASE, "memory", "09-upgrade-ledger.md")

# | U-xx | 轮次 | 问题 | 建议做法 | 状态 | 落地位置 |
ROW = re.compile(r"^\|\s*(U-\d+)\s*\|\s*([^|]+?)\s*\|")
# split('|') 后（去掉首尾空串）的列序
COL_STATE = 4   # 0=ID 1=轮次 2=问题 3=建议 4=状态 [5=落地]


def split_cells(line):
    parts = line.split('|')
    if parts and parts[0].strip() == '':
        parts = parts[1:]
    if parts and parts[-1].strip() == '':
        parts = parts[:-1]
    return [p.strip() for p in parts]


def parse_rows(lines):
    rows = []
    for i, ln in enumerate(lines, 1):
        m = ROW.match(ln)
        if not m:
            continue
        cells = split_cells(ln)
        state = cells[COL_STATE] if len(cells) > COL_STATE else ''
        rows.append((i, m.group(1), m.group(2), state, len(cells)))
    return rows


def main():
    if not os.path.exists(LEDGER):
        print("RESULT: SKIP  找不到台账文件")
        return 0

    lines = open(LEDGER, encoding="utf-8").read().split("\n")
    rows = parse_rows(lines)
    fails = []
    checked = 0

    if not rows:
        print("RESULT: SKIP  台账里没解析到任何 U 条目")
        return 0

    # 1) 撞号
    checked += 1
    cnt = collections.Counter(u for _, u, _, _, _ in rows)
    dups = {k: v for k, v in cnt.items() if v > 1}
    if dups:
        detail = '; '.join('%s×%d(行%s)' % (k, v, ','.join(str(i) for i, u, _, _, _ in rows if u == k))
                           for k, v in sorted(dups.items()))
        fails.append('%d 组撞号：%s' % (len(dups), detail))
    else:
        print('[PASS] %d 个 U 号全部唯一' % len(rows))

    # 2) 号段连续
    checked += 1
    nums = sorted(int(u.split('-')[1]) for u in cnt)
    gaps = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
    if gaps:
        fails.append('号段有空洞（可能有记录被误删）：%s' % ['U-%d' % g for g in gaps[:8]])
    else:
        print('[PASS] 号段连续 U-%d ~ U-%d 无空洞' % (nums[0], nums[-1]))

    # 3) 轮次与状态非空
    checked += 1
    bad = []
    for i, u, rnd, state, ncol in rows:
        if not rnd or not state or ncol <= COL_STATE:
            bad.append('%s(行%d,列%d,状态=%r)' % (u, i, ncol, state[:12]))
    if bad:
        fails.append('%d 条缺轮次或状态列：%s' % (len(bad), ', '.join(bad[:6])))
    else:
        print('[PASS] 每条均有轮次与非空状态列')

    # 4) 交叉引用完整
    checked += 1
    body = '\n'.join(ln for ln in lines if not ROW.match(ln))
    refs = set(re.findall(r'U-\d+', body))
    known = set(cnt)
    dangling = sorted(refs - known)
    if dangling:
        fails.append('正文引用了不存在的号（断链）：%s' % ', '.join(dangling[:8]))
    else:
        print('[PASS] 正文 %d 处交叉引用均指向存在的条目' % len(refs))

    print()
    print('检查 %d 项台账完整性（条目 %d 个）' % (checked, len(rows)))
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  台账 U 号完整性 %d 项全部成立' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())