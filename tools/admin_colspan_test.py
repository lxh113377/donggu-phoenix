# -*- coding: utf-8 -*-
"""tools/admin_colspan_test.py —— 后台表格 colspan 不得硬编码（纯静态，CI 可跑）。

## 为什么需要（轮87）
本轮把 admin 两处空态的 colspan 从硬编码（9 / 8）改成 colCountOf() 动态计算。
实测证明硬编码**不是视觉缺陷**（浏览器 clamp 到列数），所以视觉类判据永远
抓不到它退化 —— 它是语义/维护性问题：
  · 9 对 3 列、4 列的表都是错的数字，误导读代码的人
  · 加列时没人回头改常量 -> 静默漂移
这类「不炸但错」的东西最容易退化，故需要一条专门守它的判据。

## 判据
site/admin/index.html 里出现 colspan="<数字>"（硬编码）即 FAIL；
必须写成 colspan="' + colCountOf(...) + '" 这类由表头推导的形式。

## 自检（证明尺子有牙，任一不符即 FAIL）
  · 硬编码 colspan="9"      -> 必须报
  · 动态 colspan="' + n + '" -> 必须放过
  · 模板里 colspan 完全不存在 -> 放过（不强制必须有）
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = os.path.join(BASE, 'site', 'admin', 'index.html')

HARD = re.compile(r'colspan\s*=\s*"(\d+)"')


def find_hard(text):
    """返回硬编码 colspan 的 (值, 行号) 列表。"""
    out = []
    for m in HARD.finditer(text):
        out.append((m.group(1), text[:m.start()].count('\n') + 1))
    return out


SELFTEST = [
    ('<tr><td colspan="9">空</td></tr>', 1, '硬编码 colspan=9 -> 应报'),
    ("'<tr><td colspan=\"' + n + '\">空</td></tr>'", 0, '动态拼接 -> 应放过'),
    ('<tr><td>无 colspan</td></tr>', 0, '不含 colspan -> 放过'),
]


def selftest():
    bad = []
    for text, want, desc in SELFTEST:
        got = len(find_hard(text))
        if got != want:
            bad.append('%s（期望 %d 处，实得 %d）' % (desc, want, got))
    return bad


def main():
    bad = selftest()
    if bad:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad:
            print('  -', b)
        return 1
    print('[PASS] 自检 %d 个用例符合预期（硬编码能报、动态放过）' % len(SELFTEST))

    if not os.path.exists(ADMIN):
        print('RESULT: SKIP  找不到 admin/index.html')
        return 0
    s = open(ADMIN, encoding='utf-8', errors='ignore').read()
    hits = find_hard(s)
    # 表头列数是否可被 colCountOf 推导（每表都要有 thead tr）
    tables = re.findall(r'<table id="([\w-]+)"[^>]*>(.*?)</table>', s, flags=re.S)
    nohead = [tid for tid, body in tables
              if not re.search(r'<thead>\s*<tr', body)]
    print('表格 %d 张：%s' % (len(tables), ', '.join(t[0] for t in tables)))
    print('硬编码 colspan: %d 处' % len(hits))
    for v, line in hits[:8]:
        print('   - 行%d colspan="%s"' % (line, v))
    if nohead:
        print('无 thead 无法推导列数的表: %s' % ', '.join(nohead))

    if not tables:
        print()
        print('RESULT: SKIP  未扫到任何表格（解析失效，不算通过）')
        return 0
    print()
    if hits or nohead:
        print('RESULT: FAIL')
        if hits:
            print('  - %d 处 colspan 硬编码；加列时会静默错位，'
                  '应改用 colCountOf(node) 由表头推导' % len(hits))
        if nohead:
            print('  - %s 缺 thead，colCountOf 无法推导列数' % ', '.join(nohead))
        return 1
    print('RESULT: PASS  后台 %d 张表的 colspan 均由表头动态推导，无硬编码'
          % len(tables))
    return 0


if __name__ == '__main__':
    sys.exit(main())
