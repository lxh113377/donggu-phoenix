# -*- coding: utf-8 -*-
r"""tools/dead_css_decl_test.py —— 同上下文重复 CSS 声明判据（纯静态，CI 可跑）。

## 判据
「同选择器 + 同 media 上下文 + 同属性 + **同值**」写两遍 = 纯冗余。
当下不改变渲染，但它是「设计意图静默丢失」的温床：
以后只改其中一处，另一处会把它盖回去 —— 改动看起来成功，实则无效。

值不同的情况只 WARN 不判红：同属性不同值有两种合法用途
（渐进增强 display:flex;display:grid、后写的修复块有意覆盖），判红必然误报。

## 轮59 实测抓到 6 组，其中一组是我自己造成的
@media (max-height:520px) and (orientation:landscape) 块里
  .hero-grid / .hero-inner / .hero h1 em 三条规则被完整写了两遍。
根因：轮41 用脚本追加规则，第一次改完测试仍失败（实为 SW 缓存 U-142），
以为没写进去就又跑一次；幂等检查只查块标记、没查规则本身。

## 必须排除 @keyframes 帧与 @font-face（轮59 的假阳性教训）
两处 @font-face、@keyframes 的 from/to 会被切成同一个 key 造成假报，
故按 at-rule 链排除。

## 轮84 两处升级
### ① 必须先剥注释（U-160 同课，这次是真实隐患不是理论）
实测：main.css 的 .hero-tag 注释里写着
  「移动端 .hero-tag 用 justify-content:center」
—— 与该规则的真实声明文本完全相同。判据若不剥注释，
只要注释与声明落在同一 media 上下文就会被判成「同值重复声明」误报。
admin 内联 CSS 里有大量我轮60~80 写的含 outline:none / display:block
字样的注释，风险更高。
本轮用等长空白替换注释（保偏移量，at-rule 链计算不受影响）。

### ② 扫描面从「main.css」扩到「main.css + 后台内联 style」
后台 140 行内联 CSS 此前不在任何重复声明判据的面上；
而轮79 我刚在 admin 的 CSS 里写坏过一条声明（拼接漏分号）。
逐源分别分析（不跨源合并 key）—— 主站与后台是两个页面，
同名选择器在不同页面不构成重复。

## 自检
判据自带违例样本证明尺子有效（U-149/U-151 教训：测不出不等于不存在）。
"""
import os
import re
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AT_KEYWORDS = {'font-face', 'media', 'supports', 'keyframes', '-webkit-keyframes',
               '-moz-keyframes', 'import', 'charset', 'namespace', 'page'}
INNER_AT = ('keyframes', '-webkit-keyframes', '-moz-keyframes')


def strip_comments_keep_len(s):
    """注释替换为等长空白：既剥掉文字，又保住偏移量（at-rule 链依赖偏移）。"""
    out = list(s)
    for m in re.finditer(r'/\*.*?\*/', s, flags=re.S):
        for i in range(m.start(), m.end()):
            if s[i] not in '\r\n':
                out[i] = ' '
    return ''.join(out)


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


def analyze_css(css_text):
    """返回 (规则块数, 声明总数, 同值重复组, 异值组)。"""
    s = strip_comments_keep_len(css_text)
    ranges = at_ranges(s)

    def chain_of(pos):
        return [(kind, hdr) for a, b, kind, hdr in ranges if a <= pos < b]

    rules = []
    for m in re.finditer(r'([^{}@]+)\{([^{}]*)\}', s):
        sel = m.group(1).strip()
        if not sel or sel.startswith('@'):
            continue
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

    dup_same, diff_val = [], []
    for (sel, media, prop), vals in key_map.items():
        if len(vals) < 2:
            continue
        if len(set(vals)) == 1:
            dup_same.append((sel, media, prop, vals[0]))
        else:
            diff_val.append((sel, media, prop, vals))

    total = sum(len(v) for v in key_map.values())
    return len(rules), total, dup_same, diff_val


def admin_inline_css(path):
    raw = open(path, encoding='utf-8', errors='ignore').read()
    return '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', raw, flags=re.S | re.I))


# 自检样本：同值重复必须被抓到，异值与单条必须放过
SELFTEST = [
    (".a{color:red}\n.a{color:red}", True, '同选择器同值重复 -> 应报'),
    (".a{color:flex;color:grid}", False, '同属性不同值（渐进增强）-> 只 WARN 不判红'),
    (".a{color:red}", False, '单条 -> 应放过'),
    (".a{/* 说明 color:red 只是注释 */color:red}", False,
     '注释里的伪声明不得算重复（轮84 真实隐患）-> 应放过'),
]


def selftest():
    bad = []
    for css, should_flag, desc in SELFTEST:
        _n, _t, dup, _d = analyze_css(css)
        flagged = bool(dup)
        if flagged != should_flag:
            bad.append('%s（期望%s 实得%s）' % (
                desc, '报' if should_flag else '放过', '报' if flagged else '放过'))
    return bad


def main():
    bad = selftest()
    if bad:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad:
            print('  -', b)
        return 1
    print('[PASS] 自检 %d 个用例符合预期（含注释伪声明不误判）' % len(SELFTEST))

    sources = []
    cssp = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
    if os.path.exists(cssp):
        sources.append(('main.css', open(cssp, encoding='utf-8').read()))
    adp = os.path.join(BASE, 'site', 'admin', 'index.html')
    if os.path.exists(adp):
        css = admin_inline_css(adp)
        if css.strip():
            sources.append(('admin 内联', css))

    if not sources:
        print('RESULT: SKIP  找不到可扫的 CSS 源')
        return 0

    all_dup = []
    all_diff = []
    total_decl = 0
    for name, text in sources:
        n, total, dup, diff = analyze_css(text)
        total_decl += total
        print('  %-12s 规则块 %d，声明 %d 条，同值重复 %d 组' % (
            name, n, total, len(dup)))
        all_dup.extend((name,) + d for d in dup)
        all_diff.extend((name,) + d for d in diff)

    if all_dup:
        print()
        print('完全相同的重复声明（后者覆盖前者=同值，纯冗余）%d 组：' % len(all_dup))
        for src, sel, media, prop, v in sorted(all_dup):
            print('  - [%s] %s @ %s { %s: %s }' % (src, sel, media[:28], prop, v))
    if all_diff:
        print()
        print('[WARN] 同上下文同属性但值不同 %d 组（渐进增强或有意覆盖，需人工判断）：' % len(all_diff))
        for src, sel, media, prop, vals in sorted(all_diff)[:8]:
            print('  ~ [%s] %-36s %-12s %s' % (src, sel[:36], prop[:12], vals))

    print()
    if total_decl == 0:
        print('RESULT: SKIP  未解析到任何声明')
        return 0
    if all_dup:
        print('RESULT: FAIL')
        print('  - %d 组同上下文完全相同的重复声明；改一处会被另一处盖回，'
              '属「设计意图静默丢失」温床' % len(all_dup))
        return 1
    print('RESULT: PASS  无同上下文重复声明（%d 个源共 %d 条声明，值不同组仅 WARN）'
          % (len(sources), total_decl))
    return 0


if __name__ == '__main__':
    sys.exit(main())
