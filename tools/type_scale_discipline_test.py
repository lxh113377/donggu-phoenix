# -*- coding: utf-8 -*-
r"""tools/type_scale_discipline_test.py —— 标题字号必须落在字阶令牌上。

## 为什么需要（轮134 实测发现）
main.css 的 :root 定义了 10 档字阶令牌（--fs-2xs 11px 到 --fs-4xl 44px），
但标题的 font-size 有 4 条是各自随手写的 clamp：

  .sec-head h2      clamp(1.75rem,4.2vw,2.875rem)  -> 1440px 下 46px
                    而 --fs-4xl = 44px，差 2px
                    这是**重复 7 次的区块主标题**，全站最重要的重复角色
  .totem-copy h3    上限 2.375rem -> 38px（令牌 34/44 两边都不等）
  .culture-card h3  上限 1.875rem -> 30px
  .road-item h3     上限 1.75rem  -> 28px
  .carve-cap h3     上限 1.563rem -> 25.01px，而 .craft-card h3 是 26px
                    —— 差 0.99px 的两种「卡片标题」，不是层级设计，是尺度泄漏

同视口下 h3 一度有 10 种字号。目标点名的「排版 / 视觉层级」维度上，
这不是风格选择：层级应由**角色**决定（h1>h2>h3），而不是任意 px。

## 判据（纯静态，不依赖浏览器）
  A 解析 :root 的 --fs-* 令牌表（用于报告数值，也用于校验引用存在）。
  B 扫描所有含 h1..h4 的规则块里的 font-size，要求形式为：
       var(--fs-X)
       clamp(var(--fs-X), <长度>, var(--fs-Y))     上下界都必须是令牌
     即「离散档」或「两档之间的流体插值」，不允许出现字面 rem/px 边界。
  C 豁免：以 em 结尾且不含 rem 的相对值（如 .hero h1 em 的 .185em）——
     那是相对父级的比例手法，本身不引入新的绝对档位。
  D 引用了不存在的 --fs-* 令牌 -> 判红（悬空引用比脱尺更糟）。

## 尺子有效性自检（U-149/U-151）
  S1 把某条改回字面 rem -> 必须 FAIL
  S2 引用不存在的令牌 -> 必须 FAIL
  S3 当前状态不得误报
任一失效即判 FAIL。自检在内存里改文本，不写盘。

## 防自伤（U-399）
扫描前先剥 CSS 注释 —— 注释里会举 clamp 的例子（本轮我写的说明就是），
不剥会把历史说明当成代码里的违规。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')

DISCRETE = re.compile(r'^var\(--fs-[\w-]+\)$')
CLAMPED = re.compile(
    r'^clamp\(\s*(var\(--fs-[\w-]+\))\s*,\s*'
    r'[\d.]+(?:vw|rem|em|px)\s*,\s*'
    r'(var\(--fs-[\w-]+\))\s*\)$')
RELATIVE = re.compile(r'^\.?\d+(?:\.\d+)?em$')   # 相对父级，豁免
HEADING = re.compile(r'(^|[\s,>+~])h[1-4]([\s,.:>+#]|$)')


def strip_css_comments(s):
    """剥 /* */。注释里会写 clamp 例子，不剥会误判（U-399）。"""
    return re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)


def fs_tokens(css_src):
    """收录 :root 里所有 --fs-* 令牌。

    轮134 实测教训：原先只匹配纯 rem 值，于是漏掉了
    --fs-hero: clamp(3rem,7.6vw,6.5rem) 这种**流体令牌** ——
    结果 .hero h1: var(--fs-hero) 被误判成「引用不存在的令牌」。
    这条误报正是 S3 自检抓出来的（自检的价值所在）。
    现在收录所有 --fs-*；px 数值只在能换算时给出，供报告展示。
    """
    i = css_src.find(':root')
    if i < 0:
        return {}
    j = css_src.find('}', i)
    out = {}
    for m in re.finditer(r'--fs-([\w-]+)\s*:\s*([^;}]+)', css_src[i:j]):
        name = '--fs-' + m.group(1)
        val = m.group(2).strip()
        px = None
        mm = re.fullmatch(r'([\d.]+)rem', val)
        if mm:
            px = round(float(mm.group(1)) * 16, 1)
        out[name] = {'raw': val, 'px': px}
    return out


def scan(css_src):
    """返回 (违规清单, 合规数, 豁免数)。"""
    toks = fs_tokens(css_src)
    bad = []
    ok = rel = 0
    for m in re.finditer(r'([^{}@]+)\{([^{}]*)\}', css_src):
        sel = ' '.join(m.group(1).split())
        if not sel or not HEADING.search(sel):
            continue
        for f in re.finditer(r'font-size\s*:\s*([^;}]+)', m.group(2)):
            val = f.group(1).strip()
            if not val:
                continue
            # 悬空令牌引用
            for name in re.findall(r'--fs-[\w-]+', val):
                if name not in toks:
                    bad.append('%s: 引用了不存在的令牌 %s（%s）'
                               % (sel, name, val))
                    break
            else:
                if DISCRETE.match(val) or CLAMPED.match(val):
                    ok += 1
                elif RELATIVE.match(val):
                    rel += 1
                else:
                    ladder = '/'.join(
                        str(v['px']) for k, v in
                        sorted(toks.items(),
                               key=lambda x: (x[1]['px'] or 0)))
                    bad.append('%s: font-size:%s 的边界不在字阶令牌上'
                               '（px 令牌梯 %s）' % (sel, val, ladder))
    return bad, ok, rel, toks


def selftest(css_src):
    bad = []
    # S1 改回字面 rem
    s1 = css_src.replace('clamp(var(--fs-2xl),4.2vw,var(--fs-4xl))',
                         'clamp(1.75rem,4.2vw,2.875rem)', 1)
    if s1 == css_src:
        bad.append('S1 构造失败：找不到 .sec-head h2 的 clamp')
    else:
        b1, _, _, _ = scan(s1)
        hit = any('sec-head h2' in x and '不在字阶令牌' in x for x in b1)
        print('  [%s] S1 把 .sec-head h2 改回字面 rem -> %s'
              % ('ok' if hit else 'X', '被抓到' if hit else '没抓到'))
        if not hit:
            bad.append('S1 未抓到字面 rem 脱尺')
    # S2 悬空令牌
    s2 = css_src.replace('var(--fs-4xl)', 'var(--fs-9xl)', 1)
    if s2 == css_src:
        bad.append('S2 构造失败：找不到 var(--fs-4xl)')
    else:
        b2, _, _, _ = scan(s2)
        hit2 = any('不存在的令牌' in x for x in b2)
        print('  [%s] S2 引用不存在的 --fs-9xl -> %s'
              % ('ok' if hit2 else 'X', '被抓到' if hit2 else '没抓到'))
        if not hit2:
            bad.append('S2 未抓到悬空令牌引用')
    # S3 现状不得误报
    b3, _, _, _ = scan(css_src)
    print('  [%s] S3 当前状态 -> %s'
          % ('ok' if not b3 else 'X', '无误报' if not b3 else str(b3)[:70]))
    if b3:
        bad.append('S3 当前状态被误报：%s' % b3[:1])
    return bad


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css（未测不等于通过）')
        return 0
    raw = strip_css_comments(io.open(CSS, encoding='utf-8',
                                     errors='ignore').read())
    toks = fs_tokens(raw)
    if len(toks) < 5:
        print('RESULT: SKIP  :root 里解析到的 --fs-* 令牌只有 %d 个，'
              '口径不成立（未测不等于通过）' % len(toks))
        return 0
    print('=== 字阶令牌 %d 档 ===' % len(toks))
    for k, v in sorted(toks.items(), key=lambda x: (x[1]['px'] or 0)):
        print('  %-12s %s' % (
            k.replace('--fs-', ''),
            ('%spx' % v['px']) if v['px'] is not None
            else v['raw'] + '  （流体令牌）'))
    print()
    print('=== 尺子有效性自检 ===')
    bs = selftest(raw)
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1
    bad, ok, rel, _ = scan(raw)
    print('=== 标题字号纪律 ===')
    print('  合规 %d 条（离散令牌或 clamp 两界皆令牌）｜ 相对值豁免 %d 条'
          % (ok, rel))
    if bad:
        print('RESULT: FAIL  %d 条标题字号脱尺：' % len(bad))
        for b in bad:
            print('  -', b)
        return 1
    print('RESULT: PASS  全部 %d 条标题字号都落在字阶令牌上，'
          '且自检证明「改回字面值」与「悬空令牌引用」都能被抓到' % (ok + rel))
    return 0


if __name__ == '__main__':
    sys.exit(main())
