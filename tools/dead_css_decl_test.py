# -*- coding: utf-8 -*-
"""tools/dead_css_decl_test.py —— 同上下文完全相同的重复声明判据（纯静态，CI 可跑）。

## 为什么需要它（轮59 实测抓到真东西）
「同选择器 + 同 media 上下文 + 同属性 + 同值」写两遍 = 纯冗余。
它当下无害，但它是「设计意图静默丢失」的温床：
以后改其中一处，另一处会把它盖回去 —— 改动看起来成功，实则无效。
这类 bug 不报错、不白屏，只能靠读代码发现。

## 轮59 实测：抓到我自己造成的重复
@media (max-height:520px) and (orientation:landscape) 块里
  .hero-grid{...} / .hero-inner{margin:0} / .hero h1 em{display:none}
被完整写了两遍。
根因：轮41 我用脚本追加规则，第一次改完测试仍失败（实为 SW 缓存 U-142），
以为没写进去就又跑一次；幂等检查只查块标记、没查规则本身。
已清理，并把这条做成判据防回退。

## 只判「值完全相同」，不判「值不同」
同属性不同值有两种合法用途：
  · 渐进增强（display:flex; display:grid）
  · 后写的修复块有意覆盖前一条
所以值不同只 WARN 供人工看，不判红 —— 否则必然误报。

## 解析器踩过的两个坑（轮59 实测）
1. @keyframes 的 from/to、@font-face 的 font-style：
   不记录 at-rule 归属就会把不同字体/不同动画的同名声明并成「重复」。
2. @font-face 自身的声明块，其 prelude 是 '@font-face'，
   若只按「选择器不含 @」筛，sel 会被切成 'font-face' 仍然误并。
   → 显式排除 at-rule 关键字作为选择器的情况。

零样本判 SKIP 不判 PASS。
"""
import os
import re
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')

AT_KEYWORDS = {'font-face', 'media', 'supports', 'keyframes', '-webkit-keyframes',
               '-moz-keyframes', 'import', 'charset', 'namespace', 'page'}
INNER_AT = ('keyframes', '-webkit-keyframes', '-moz-keyframes')


def at_ranges(s):
    """所有 at-rule 的 (起点, 终点, 类型, 头部文本)。"""
    out = []
    for m in re.finditer(r'@(media|supports|keyframes|-webkit-keyframes|-moz-keyframes|font-face)[^{]*\{', s):
        kind = m.group(1)
        depth = 0
        start = m.end() - 1
        hdr = s[m.start():m.end()].strip()
        for k in range(start, len(s)):
            if s[k] == '{':
                depth += 1
            elif s[k] == '}':
                depth -= 1
                if depth == 0:
                    out.append((start, k + 1, kind, hdr))
                    break
    return out


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0
    s = open(CSS, encoding='utf-8').read()
    ranges = at_ranges(s)

    def chain_of(pos):
        c = []
        for a, b, kind, hdr in ranges:
            if a <= pos < b:
                c.append((kind, hdr))
        return c

    rules = []
    for m in re.finditer(r'([^{}@]+)\{([^{}]*)\}', s):
        sel = m.group(1).strip()
        if not sel or sel.startswith('@'):
            continue
        # 关键：@font-face 自身块的 sel 会被切成 'font-face'，必须排除
        if sel in AT_KEYWORDS:
            continue
        ch = chain_of(m.start())
        if any(k in INNER_AT for k, _ in ch):
            continue   # keyframes 内部的帧
        media = ' | '.join(h for k, h in ch if k in ('media', 'supports')) or '(顶层)'
        rules.append((sel, [d.strip() for d in m.group(2).split(';') if d.strip()], media))

    key_map = defaultdict(list)
    for sel, decls, media in rules:
        for d in decls:
            mm = re.match(r'([a-zA-Z-]+)\s*:\s*(.*)$', d)
            if not mm:
                continue
            key_map[(sel, media, mm.group(1))].append(mm.group(2).strip())

    dup_same = []
    diff_val = []
    for (sel, media, prop), vals in key_map.items():
        if len(vals) < 2:
            continue
        if len(set(vals)) == 1:
            dup_same.append((sel, media, prop, vals[0]))
        else:
            diff_val.append((sel, media, prop, vals))

    total = sum(len(v) for v in key_map.values())
    print('规则块 %d，声明 %d 条' % (len(rules), total))

    if dup_same:
        print()
        print('完全相同的重复声明（后者覆盖前者=同值，纯冗余）%d 组：' % len(dup_same))
        for sel, media, prop, v in sorted(dup_same):
            print('  - %s @ %s { %s: %s } 写了 %d 遍' % (
                sel, media[:30], prop, v, len(key_map[(sel, media, prop)])))
    if diff_val:
        print()
        print('[WARN] 同上下文同属性但值不同 %d 组（渐进增强或有意覆盖，需人工判断）：' % len(diff_val))
        for sel, media, prop, vals in sorted(diff_val)[:8]:
            print('  ~ %-38s %-14s %s' % (sel[:38], prop[:14], vals))

    print()
    if total == 0:
        print('RESULT: SKIP  未解析到任何声明')
        return 0
    if dup_same:
        print('RESULT: FAIL')
        print('  - %d 组同上下文完全相同的重复声明；改一处会被另一处盖回，'
              '属「设计意图静默丢失」温床' % len(dup_same))
        return 1
    print('RESULT: PASS  无同上下文重复声明（%d 条声明，值不同组仅 WARN）' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
