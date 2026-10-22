# -*- coding: utf-8 -*-
r"""tools/type_scale_discipline_test.py —— font-size 必须守字阶纪律（两站两档口径）。

## 为什么需要（轮134 实测发现）
main.css 的 :root 定义了 10 档字阶令牌（--fs-2xs 11px 到 --fs-4xl 44px），
但标题的 font-size 有 8 条是各自随手写的 clamp：

  .sec-head h2      clamp(1.75rem,4.2vw,2.875rem) -> 1440px 下 46px
                    而 --fs-4xl = 44px，差 2px
                    这是**重复 7 次的区块主标题**，全站最重要的重复角色
  .carve-cap h3     上限 1.563rem -> 25.01px，而 .craft-card h3 是 26px
                    —— 差 0.99px 的两种「卡片标题」不是层级设计，是尺度泄漏

同视口下 h3 一度有 10 种字号。目标点名的「排版 / 视觉层级」维度上，
层级应由**角色**决定（h1>h2>h3），不是任意 px。

## 两档口径（轮134 由测量决定，不凭「越严越好」）
先量了两站全部 font-size：
  主站  标题 18 条（收编后脱尺 0）｜ 非标题 88 条，其中 6 条非令牌值
  后台  标题 2 条（脱尺 0）｜ 非标题 18 条（脱尺 0）

那 6 条非标题里，1.875rem=30px、2.25rem=36px、3.25rem=52px 与最近档差
都 >=2px，是**刻意的大装饰字**（章节序号 .sec-idx、文化卡编号 .no 这类
展示性数字）；html{font-size:100%} 是根字号锚点；min(30vw,15rem) 是
hero 大字的尺寸手法。把它们一律判红，就是拿臆断当规格、误伤合理设计
（同 U-409 的纪律）。

所以分两档：
  A 标题（选择器含 h1..h4）—— **严格**：font-size 必须是
      var(--fs-X)  或  clamp(var(--fs-X), <长度>, var(--fs-Y))，两界皆令牌。
  B 非标题 —— 只抓两类真问题：
      B1 悬空引用：用了 :root 里不存在的 --fs-*
      B2 近似泄漏：字面 rem/px 换算后与某档相差 <=1px 却不相等
         —— 差半像素不可能是设计意图，只能是写歪了。
         实测抓到 .hero-lead 的 1.031rem(16.5px) vs --fs-md(16px)，
         差 0.5px，已修；而 30/36/52px 因差 >=2px 不判红。

## 覆盖两个面
主站 site/assets/css/main.css 与后台 site/admin/index.html 的 <style>。
两站各有独立令牌表（后台 --fs-2xs/xs/s/base/m/l），各按自己的表判；
**不做跨站字号比对** —— 后台注释只声明了品牌色三项同源（U-409）。

## 尺子有效性自检（U-149/U-151）
  S1 标题改回字面 rem -> 必须 FAIL
  S2 悬空令牌引用 -> 必须 FAIL
  S3 非标题造一个 16.5px 的近似泄漏 -> 必须 FAIL（B2 有牙）
  S4 非标题的刻意尺寸（36px）-> 不得误报（防过度收紧）
  S5 当前两站状态 -> 不得误报
任一失效即判 FAIL。自检在内存里改文本，不写盘。

## 防自伤（U-399）
扫描前先剥 CSS 注释 —— 注释里会写 clamp 例子（本轮我写的说明就是），
不剥会把历史说明当成代码里的违规。

## 诚实语义
文件读不到 / :root 解析不出足够令牌 -> SKIP 并说明，不判 PASS。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    ('主站 main.css', os.path.join(BASE, 'site', 'assets', 'css', 'main.css')),
    ('后台 admin/index.html', os.path.join(BASE, 'site', 'admin', 'index.html')),
]

DISCRETE = re.compile(r'^var\(--fs-[\w-]+\)$')
CLAMPED = re.compile(
    r'^clamp\(\s*(var\(--fs-[\w-]+\))\s*,\s*'
    r'[\d.]+(?:vw|rem|em|px)\s*,\s*'
    r'(var\(--fs-[\w-]+\))\s*\)$')
RELATIVE = re.compile(r'^\.?\d+(?:\.\d+)?em$')      # 相对父级，豁免
HEADING = re.compile(r'(^|[\s,>+~])h[1-4]([\s,.:>+#]|$)')
# 字面尺寸（只认 rem/px，不认 vw/%，避免把流体系数或根字号当违规）
LITERAL = re.compile(r'(\d+(?:\.\d+)?)(rem|px)\b')
NEAR_PX = 1.0        # 与某档相差 <=1px 却不相等 -> 近似泄漏


def strip_css_comments(s):
    """剥 /* */ 与 HTML 注释。注释里会写 clamp 例子，不剥会误判（U-399）。"""
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    return s


def css_of(text, path):
    """后台样式在 index.html 的 <style> 里；主站直接就是 CSS。"""
    if path.endswith('.css'):
        return text
    blocks = re.findall(r'<style[^>]*>(.*?)</style>', text, flags=re.S)
    return '\n'.join(blocks)


def fs_tokens(css_src):
    """收录 :root 里所有 --fs-* 令牌。

    轮134 实测教训：原先只匹配纯 rem 值，于是漏掉了
    --fs-hero: clamp(3rem,7.6vw,6.5rem) 这种**流体令牌** ——
    结果 .hero h1: var(--fs-hero) 被误判成「引用不存在的令牌」。
    这条误报正是 S5 自检抓出来的（自检的价值所在）。
    """
    i = css_src.find(':root')
    if i < 0:
        return {}
    j = css_src.find('}', i)
    out = {}
    for m in re.finditer(r'--fs-([\w-]+)\s*:\s*([^;}]+)', css_src[i:j]):
        val = m.group(2).strip()
        px = None
        mm = re.fullmatch(r'([\d.]+)rem', val)
        if mm:
            px = round(float(mm.group(1)) * 16, 2)
        out['--fs-' + m.group(1)] = {'raw': val, 'px': px}
    return out


def _ladder(toks):
    """px 令牌梯，用于报错信息。流体令牌（px 无法换算）不计入。"""
    return '/'.join(str(v['px']) for k, v in
                    sorted(toks.items(),
                           key=lambda x: (x[1]['px'] or 0))
                    if v['px'] is not None)


def scan(css_src):
    """返回 (违规清单, 标题合规数, 豁免数, 非标题检查数, 令牌表)。"""
    toks = fs_tokens(css_src)
    pxvals = [v['px'] for v in toks.values() if v['px'] is not None]
    bad = []
    ok = rel = other = 0
    for m in re.finditer(r'([^{}@]+)\{([^{}]*)\}', css_src):
        sel = ' '.join(m.group(1).split())
        if not sel:
            continue
        head = bool(HEADING.search(sel))
        for f in re.finditer(r'font-size\s*:\s*([^;}]+)', m.group(2)):
            val = f.group(1).strip()
            if not val:
                continue
            # B1/A2 悬空令牌引用（两档都抓）
            names = re.findall(r'--fs-[\w-]+', val)
            dangling = [n for n in names if n not in toks]
            if dangling:
                bad.append('%s: %s 引用了不存在的令牌 %s'
                           % (sel, val, ' '.join(sorted(set(dangling)))))
                continue
            if head:
                # A 档：严格
                if DISCRETE.match(val) or CLAMPED.match(val):
                    ok += 1
                elif RELATIVE.match(val):
                    rel += 1
                else:
                    bad.append('%s（标题）: font-size:%s 的边界不在字阶令牌上'
                               '（px 令牌梯 %s）' % (sel, val, _ladder(toks)))
                continue
            # B2 档：非标题只抓近似泄漏
            other += 1
            for mm in LITERAL.finditer(val):
                n = float(mm.group(1)) * (16 if mm.group(2) == 'rem' else 1)
                for t in pxvals:
                    if abs(n - t) <= NEAR_PX and abs(n - t) > 0.01:
                        bad.append('%s: font-size:%s 算得 %.2fpx，'
                                   '与令牌 %spx 差 %.2fpx —— '
                                   '差 1px 内不可能是设计意图（近似泄漏）'
                                   % (sel, val, n, t, abs(n - t)))
                        break
                else:
                    continue
                break
    return bad, ok, rel, other, toks


def selftest(css_src):
    bad = []

    def run(text, tag, needle, expect_hit):
        b, _, _, _, _ = scan(text)
        hit = any(needle in x for x in b)
        want = '被抓到' if expect_hit else '不误报'
        okv = hit == expect_hit
        print('  [%s] %s -> %s' % ('ok' if okv else 'X', tag,
                                   '抓到' if hit else '放过'))
        if not okv:
            bad.append('%s 期望%s，实得%s'
                       % (tag, want, '抓到' if hit else '放过'))

    # S1 标题改回字面 rem
    s1 = css_src.replace('clamp(var(--fs-2xl),4.2vw,var(--fs-4xl))',
                         'clamp(1.75rem,4.2vw,2.875rem)', 1)
    if s1 == css_src:
        bad.append('S1 构造失败：找不到可改的标题 clamp')
    else:
        run(s1, 'S1 标题改回字面 rem', '不在字阶令牌', True)
    # S2 悬空令牌
    s2 = css_src.replace('var(--fs-4xl)', 'var(--fs-9xl)', 1)
    if s2 == css_src:
        bad.append('S2 构造失败：找不到 var(--fs-4xl)')
    else:
        run(s2, 'S2 引用不存在的 --fs-9xl', '不存在的令牌', True)
    # S3 非标题近似泄漏（造一个 16.5px）
    s3 = css_src.replace('.hero-lead{', '.hero-lead{font-size:1.031rem;', 1)
    if s3 == css_src:
        # 后台没有 .hero-lead，退一步用任意规则注入
        s3 = css_src.replace('body{', 'body{font-size:1.031rem;', 1)
    if s3 == css_src:
        bad.append('S3 构造失败：注入不了近似泄漏')
    else:
        run(s3, 'S3 非标题造 16.5px 近似泄漏', '近似泄漏', True)
    # S4 非标题刻意尺寸（36px）不得误报
    s4 = css_src.replace('body{', 'body{font-size:2.25rem;', 1)
    if s4 == css_src:
        bad.append('S4 构造失败：注入不了刻意尺寸')
    else:
        b4, _, _, _, _ = scan(s4)
        hit4 = [x for x in b4 if '近似泄漏' in x]
        print('  [%s] S4 非标题刻意 36px -> %s'
              % ('ok' if not hit4 else 'X',
                 '不误报' if not hit4 else '误报（口径过紧）'))
        if hit4:
            bad.append('S4 把刻意尺寸 36px 误判成违规，口径过紧')
    # S5 现状不得误报
    b5, _, _, _, _ = scan(css_src)
    print('  [%s] S5 当前状态 -> %s'
          % ('ok' if not b5 else 'X', '无误报' if not b5 else str(b5)[:64]))
    if b5:
        bad.append('S5 当前状态被误报：%s' % b5[:1])
    return bad


def check_one(label, path):
    """返回 (fails, 统计)。文件不可用时返回 None 表示未测。"""
    if not os.path.exists(path):
        print('[%s] 读不到文件 -> 未测' % label)
        return None
    raw = strip_css_comments(css_of(io.open(
        path, encoding='utf-8', errors='ignore').read(), path))
    toks = fs_tokens(raw)
    if len(toks) < 2:
        print('[%s] :root 解析到 %d 个 --fs-* 令牌 -> 口径不成立，未测'
              % (label, len(toks)))
        return None
    print('=== %s：字阶令牌 %d 档（%s）==='
          % (label, len(toks), _ladder(toks)))
    bad, ok, rel, other, _ = scan(raw)
    print('  A 标题严格：合规 %d、相对值豁免 %d' % (ok, rel))
    print('  B 非标题：检查 %d 条（只抓悬空引用与 1px 内近似泄漏）' % other)
    return {'bad': bad, 'ok': ok, 'rel': rel, 'other': other, 'raw': raw}


def main():
    results = []
    print('=== 尺子有效性自检（以主站 CSS 为样本）===')
    main_path = TARGETS[0][1]
    if not os.path.exists(main_path):
        print('RESULT: SKIP  找不到主站 CSS，自检无法进行（未测不等于通过）')
        return 0
    main_raw = strip_css_comments(io.open(main_path, encoding='utf-8',
                                          errors='ignore').read())
    if len(fs_tokens(main_raw)) < 5:
        print('RESULT: SKIP  主站 :root 令牌不足 5 档，口径不成立')
        return 0
    bs = selftest(main_raw)
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1

    fails = []
    untested = []
    for label, path in TARGETS:
        r = check_one(label, path)
        if r is None:
            untested.append(label)
            continue
        results.append(r)
        for x in r['bad']:
            fails.append('%s：%s' % (label, x))
        print()

    if fails:
        print('RESULT: FAIL  %d 处不守字阶纪律：' % len(fails))
        for f in fails:
            print('  -', f)
        return 1
    tot_ok = sum(r['ok'] for r in results)
    tot_rel = sum(r['rel'] for r in results)
    tot_other = sum(r['other'] for r in results)
    if untested:
        print('RESULT: SKIP  以下面未测（不等于通过）：%s'
              % '、'.join(untested))
        return 0
    print('RESULT: PASS  两站标题 %d 条全部落在各自字阶令牌上'
          '（豁免 %d 条相对值），非标题 %d 条无悬空引用、无 1px 内近似泄漏，'
          '且 5 项自检证明该松该紧都有效'
          % (tot_ok, tot_rel, tot_other))
    return 0


if __name__ == '__main__':
    sys.exit(main())
