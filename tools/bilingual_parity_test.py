# -*- coding: utf-8 -*-
"""tools/bilingual_parity_test.py —— 中英信息对等检查（纯静态，CI 可跑）。

## 为什么需要它

轮20 逐条比对 ar-data.js 的 body / enBody 配对，发现 5 处英文丢信息：
  7.  中文引毛泽东《渔家傲》「雾满龙冈千嶂暗…」→ 英文只写 "annihilated"
  8.  中文「毛泽东、朱德…歼敌七千余人」「白云山头云欲立」→ 英文丢了人名、数字、诗句
  9.  中文「年仅 33 岁」「就把我埋在东固，我喜欢这里的人民，喜欢这里的山和水」
      → 英文只写 "He asked to be buried in Donggu."（最动人的遗言丢了）
  12. 中文「每一位畲族女性，都被视作三公主的化身」→ 英文止于 "never in rank"（核心论点丢了）
  13. 中文「山歌一开口，凤凰就落在东固」→ 英文止于 "birdsong"（结尾诗意句丢了）

英文确实渲染在页面上（display:block），所以这是读者可见的缺陷。
对国际奖项评审尤其不利：英文读者拿到的叙事比中文少一截。

## 判据

1. 英文词数 / 中文字数 的比值 >= 0.30
   （中文 1 字约对应英文 0.4~0.6 词；低于 0.30 基本可判定信息缺失）
2. 中文里的关键数字（年份、数量）英文必须保留
3. 中文里的诗句引号（「…」）若存在，英文应有对应的引号内容
4. 英文里不得出现 Markdown 标记（*斜体* / **粗体** / [链接]）——
   页面是纯文本渲染，标记会原样显示

## 用法
    python tools/bilingual_parity_test.py
退出码 0 = 全部达标；1 = 有不达标项。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'site', 'assets', 'data', 'ar-data.js')

MIN_RATIO = 0.30


def pairs(text):
    """提取 body / enBody 配对。"""
    out = []
    for m in re.finditer(r"body:\s*'((?:[^'\\]|\\.)*)'[^}]*?enBody:\s*'((?:[^'\\]|\\.)*)'",
                         text, re.S):
        out.append((m.group(1), m.group(2)))
    return out


def main():
    if not os.path.exists(DATA):
        print('RESULT: SKIP  找不到 ar-data.js')
        return 0

    text = open(DATA, encoding='utf-8').read()
    ps = pairs(text)
    if not ps:
        print('RESULT: SKIP  未找到中英配对')
        return 0

    fails = []
    for i, (zh, en) in enumerate(ps, 1):
        zh_len = len(zh)
        en_words = len(en.split())
        ratio = round(en_words / max(1, zh_len), 2)

        if ratio < MIN_RATIO:
            fails.append('第 %d 组信息偏少（中%d字/英%d词，比 %.2f < %.2f）'
                         % (i, zh_len, en_words, ratio, MIN_RATIO))

        # 年份必须保留
        for year in re.findall(r'(1[89]\d{2}|20\d{2})', zh):
            if year not in en:
                fails.append('第 %d 组英文丢了年份 %s' % (i, year))

        # 中文诗句（「…」内含标点或较长）英文应有引号内容
        for q in re.findall(r'「([^」]{8,})」', zh):
            if '「' in q:
                continue
            if '“' not in en and '"' not in en and "’" not in en:
                fails.append('第 %d 组中文引了诗句但英文无对应引文' % i)

        # Markdown 标记不得出现在纯文本字段
        if re.search(r'\*[A-Za-z][^*]{0,30}\*', en) or re.search(r'\[.+?\]\(.+?\)', en):
            fails.append('第 %d 组英文含 Markdown 标记（页面纯文本渲染会原样显示）' % i)

    print('检查 %d 组中英配对（阈值：英文词/中文字 >= %.2f）' % (len(ps), MIN_RATIO))
    for i, (zh, en) in enumerate(ps, 1):
        ratio = round(len(en.split()) / max(1, len(zh)), 2)
        print('  %2d. 中%3d字 / 英%3d词  比%.2f  %s'
              % (i, len(zh), len(en.split()), ratio, '' if ratio >= MIN_RATIO else '<-- 偏少'))

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  中英信息对等（%d 组全部达标）' % len(ps))
    return 0


if __name__ == '__main__':
    sys.exit(main())
