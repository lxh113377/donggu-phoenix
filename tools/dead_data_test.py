# -*- coding: utf-8 -*-
"""tools/dead_data_test.py —— 数据字段必须有消费者（纯静态，CI 可跑）。

## 为什么需要它
轮22 排查发现 8 个数据字段从未被前端引用，其中两处会造成误导：
  · meta.year = '2025' 而页面写 2026 —— 核实后两者都对（2025 田野调研、2026 交付），
    但字段名 year 含义模糊，易被当成展示年份。已改名 fieldworkYear。
  · ar-data.js meta.subtitle / weight 是旧版文案，HTML 已有更完整表述，
    留着会让维护者误以为是当前文案。已删除。
这类问题读者看不见、维护者会踩 —— 与轮21 的出处问题同源。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')

DATA_FILES = ['assets/data/culture.js', 'assets/data/ar-data.js']
FRONT_FILES = ['index.html', 'assets/js/main.js', 'assets/js/ar.js',
               'assets/js/ar-scenes.js', 'assets/js/wood-demo.js',
               'assets/js/wood-to-statue.js', 'assets/js/phoenix.js']

ALLOWLIST = {
    'line1': '首屏水印已在 HTML 写死，数据保留作文案源',
    'stampNew': '集章提示，当前用 stamps，预留',
    'tapScene': '轻触场景提示，当前未到该分支，预留',
    'costumes': '凤凰装三式，culture 段已完整覆盖，数据保留',
    'fieldworkYear': '田野调研年份，仅作文档记录',
    'subtitle': 'meta 副标题，页面静态文案更完整，保留作元数据',
    'en': '拉丁副标题，由 HTML 静态提供',
    'team': '团队署名，由 HTML 静态提供',
    'place': '地点，由 HTML 静态提供',
}


def main():
    front = ''
    for f in FRONT_FILES:
        p = os.path.join(SITE, f)
        if os.path.exists(p):
            front += open(p, encoding='utf-8').read()

    fails = []
    checked = 0
    allowed = 0
    consumed = 0

    for df in DATA_FILES:
        p = os.path.join(SITE, df)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8').read()
        keys = set(re.findall(r'^\s{2,6}(\w+):\s', s, re.M))
        for k in sorted(keys):
            if len(k) < 3:
                continue
            checked += 1
            if k in front:
                consumed += 1
                continue
            if k in ALLOWLIST:
                allowed += 1
                continue
            fails.append(os.path.basename(df) + ' 的字段 `' + k + '` 无任何前端消费者')

    print('检查 %d 个数据字段：%d 有消费者 / %d 预留 / %d 无消费者'
          % (checked, consumed, allowed, len(fails)))
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails[:12]:
            print('  -', f)
        print()
        print('处置：删除死字段，或加入 ALLOWLIST 并写明理由。')
        return 1
    print('RESULT: PASS  所有数据字段都有消费者或已登记为预留')
    return 0


if __name__ == '__main__':
    sys.exit(main())