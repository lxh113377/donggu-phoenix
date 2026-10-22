# -*- coding: utf-8 -*-
r"""tools/memory_size_test.py —— memory/ 文件 4KB 硬限判据（棘轮式，纯静态）。

## 为什么需要（轮125 发现）
老大定的硬规则：active-core 记忆文件 <= 4096 字节（R161 零豁免）。
但这条规则**没有任何机器检查** —— 结果本轮实测发现 6 个文件超限，
最严重的 08-verify.md 已 263 KB。规则写着、没人守，就会一路漂移到
这个量级（与 U-160/204/237/265/307/322「静默无人守」同一族）。

## 为什么不直接「超限即红」
03-status.md 等文件由**本会话与并行端共同写入**，单方面拆分会造成
记忆分裂（对方继续往旧路径追加）。所以本轮先把问题**变成可见且不再恶化**：

  · 棘轮（ratchet）：存量超限记入基线文件，只禁止「继续变大」；
    一旦有人把它拆小，基线自动收紧（下次以实际值为准）。
  · 新文件：active-core 新增文件必须 <= 4096，否则直接 FAIL。
  · append-only 日志/台账（08/09）：按 R48 归档类豁免拆分，
    但仍报告体积，并在超过软上限时提示归档。

这样判据今天就能绿（不误伤），但从此刻起漂移被堵住。

## 分类口径
  active-core（受 4096 硬限）：00~07 编号文件
  append-only 日志（R48 豁免，仅报告）：08-verify.md、09-upgrade-ledger.md
  日期命名文件（08 的分卷，同豁免）：YYYY-MM-DD-*.md

## 诚实语义
读不到 memory/ 目录 -> SKIP 并说明，不判 PASS。
"""
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMDIR = os.path.join(BASE, 'memory')
LEDGER = os.path.join(BASE, 'memory', '.size_baseline.json')
HARD_LIMIT = 4096            # 老大定的 active-core 硬限
LOG_SOFT_LIMIT = 400 * 1024  # append-only 日志的归档提醒线

ACTIVE_RE = re.compile(r'^[0-9]{2}-[\w-]+\.md$')
LOG_FILES = {'08-verify.md', '09-upgrade-ledger.md'}
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-[\w-]+\.md$')


def classify(name):
    if name in LOG_FILES or DATE_RE.match(name):
        return 'log'
    if ACTIVE_RE.match(name):
        return 'active'
    return 'other'


def load_baseline():
    if not os.path.exists(LEDGER):
        return {}
    try:
        return json.load(io.open(LEDGER, encoding='utf-8'))
    except Exception:
        return {}


def save_baseline(b):
    io.open(LEDGER, 'w', encoding='utf-8', newline='').write(
        json.dumps(b, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def main():
    if not os.path.isdir(MEMDIR):
        print('RESULT: SKIP  找不到 memory/ 目录（未测不等于通过）')
        return 0

    names = [f for f in sorted(os.listdir(MEMDIR)) if f.endswith('.md')]
    # first_run：基线文件此前不存在（或为空）-> 本轮是首次建档，
    # 存量超限记为债务；基线已存在时冒出的新文件超限必须 FAIL。
    first_run = (not os.path.exists(LEDGER)) or (not load_baseline())
    baseline = load_baseline()
    fails = []
    warns = []
    new_baseline = {}
    rows = []

    for f in names:
        p = os.path.join(MEMDIR, f)
        if not os.path.isfile(p):
            continue
        # 用 LF 归一字节而非 os.path.getsize：Windows 工作树若被 git
        # 转成 CRLF，同一文件在 CI(Linux/LF) 上会少 (行数) 字节，
        # 导致基线被误判「收紧」或「变大」。归一后两平台恒等。
        # （实测本仓 memory/*.md 目前都是纯 LF，此处是防今后漂移。）
        with open(p, 'rb') as _fh:
            size = len(_fh.read().replace(b'\r\n', b'\n'))
        kind = classify(f)
        rows.append((f, kind, size))

        if kind == 'log':
            # 归档类：不受 4096 约束，但超软上限要提示归档
            if size > LOG_SOFT_LIMIT:
                warns.append('%s 已 %.1f KB，超过归档提醒线 %d KB，'
                             '建议按 R48 归档旧条目'
                             % (f, size / 1024.0, LOG_SOFT_LIMIT // 1024))
            continue

        if kind != 'active':
            continue

        cap = baseline.get(f)
        if cap is None:
            # 基线里没有这个文件，两种情况要分开：
            #  · first_run（本轮首次建基线）-> 存量超限记为债务，不判红
            #  · 基线已存在、这是新增文件 -> 超限必须 FAIL（不能记成债务）
            # 早先版本把「新建超限」的检查写在 else 分支里，而 else 分支的
            # f 必然已在 baseline 中 -> 那个条件恒不成立，等于没写（轮125
            # 反向验证用例 C 当场抓到：新建 5013 字节的 active-core 仍判 PASS）。
            new_baseline[f] = size
            if size > HARD_LIMIT:
                if first_run:
                    warns.append('%s 超限 %.1f KB（存量债务，已记入基线；'
                                 '拆分需与并行端协调，见 U-209）'
                                 % (f, size / 1024.0))
                else:
                    fails.append('%s 是基线建立后新增的 active-core 文件，'
                                 '%d 字节 > 硬限 %d。新建必须合规，'
                                 '要写入请直接用 bigfile-split 拆成 leaves'
                                 % (f, size, HARD_LIMIT))
        else:
            if size > cap:
                fails.append('%s 比基线变大：%d -> %d 字节（+%d）。'
                             'active-core 受 4KB 硬限，禁止继续增长；'
                             '要写入请先按 bigfile-split 拆成 leaves'
                             % (f, cap, size, size - cap))
                new_baseline[f] = size
            elif size < cap:
                # 拆小了 -> 棘轮自动收紧
                new_baseline[f] = size
                print('  [棘轮收紧] %s 基线 %d -> %d 字节' % (f, cap, size))
            else:
                new_baseline[f] = cap

    # 基线里有、文件已不存在的条目清掉（避免陈旧）
    for f in list(baseline):
        if f not in names:
            print('  [基线清理] %s 已不存在，移除' % f)

    if new_baseline != baseline:
        save_baseline(new_baseline)
        print('  基线已更新：%d 项' % len(new_baseline))

    print('=== memory/ 体积（active-core 硬限 %d 字节）===' % HARD_LIMIT)
    for f, kind, size in rows:
        cap = baseline.get(f)
        mark = ''
        if kind == 'active':
            if size > HARD_LIMIT:
                mark = '  ** 超限（债务 %.1f KB）**' % (
                    (size - HARD_LIMIT) / 1024.0)
            else:
                mark = '  ok'
        elif kind == 'log':
            mark = '  （归档类，R48 豁免）'
        print('  %-34s %-6s %8d 字节%s' % (f, kind, size, mark))

    print()
    if warns:
        print('提示：')
        for w in warns:
            print('  -', w)
        print()
    if fails:
        print('RESULT: FAIL')
        for x in fails:
            print('  -', x)
        return 1
    n_active = sum(1 for _, k, _ in rows if k == 'active')
    print('RESULT: PASS  %d 个 active-core 文件均未超过基线'
          '（硬限 %d 字节，漂移已堵住）' % (n_active, HARD_LIMIT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
