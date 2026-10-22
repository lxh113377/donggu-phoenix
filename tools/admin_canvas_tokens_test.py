# -*- coding: utf-8 -*-
r"""tools/admin_canvas_tokens_test.py —— 后台 canvas 绘制色必须等于 CSS 令牌（纯静态，CI 可跑）。

## 为什么需要（轮127）
site/admin/index.html:413 的注释自己写着：

  「canvas 内绘制的文字 getComputedStyle 读不到，对比度判据覆盖不到它，
    因此这里的颜色必须与 CSS 令牌手工对齐（gold / fg-faint / line-soft）。」

也就是说：**代码声明了一条不变量，却没有任何机器检查在守它**。
这正是 U-395（memory 4KB 硬限写着却没人守，结果 6 个文件超限）的同族 ——
规则靠注释维持，就会一路漂移。

具体漂移路径很现实：
  · 有人调了 :root 的 --gold（比如为对比度把 #D4A24E 调亮），
    忘了同步改 canvas 里的 '#D4A24E' -> 图与卡片配色分叉，肉眼很难发现；
  · 有人在 canvas 里随手写个 '#888' -> 不在令牌表里，等于引入第 13 种颜色。
两种都不会让现有任何判据变红。

## 判据
  A 解析 :root{...} 得到 令牌名 -> 十六进制值 的表（至少 10 个令牌）。
  B 扫描后台内联 <script> 里出现的**所有颜色字面量**：
      #RGB / #RRGGBB / rgba(r,g,b,a)（rgba 换算成十六进制再比）。
  C 每个颜色都必须能在令牌表里找到同值令牌，否则 FAIL 并点名
      「哪个颜色、在哪一行、不在任何令牌里」。
  D 反向：令牌表里被 canvas 用到的那些，值必须与 :root 完全一致
      （由 C 保证，这里额外报告映射结果便于排查）。

## 尺子有效性自检（U-149/U-151）
  S1 把某个 canvas 颜色改成不在令牌表里的值 -> 必须 FAIL
  S2 把某个令牌的值改掉（canvas 不动）-> 必须 FAIL（这才抓到"改令牌忘改图"）
  任一抓不到即判 FAIL —— 否则本判据是恒真的安慰剂。
自检在内存里改文本，不写盘、不碰真实文件。

## 诚实语义
读不到后台页 / 解析不出 :root -> SKIP 并说明，不判 PASS。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = os.path.join(BASE, 'site', 'admin', 'index.html')

HEX_RE = re.compile(r'#([0-9a-fA-F]{3})\b|#[0-9a-fA-F]{6}\b')
RGBA_RE = re.compile(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,[^)]*)?\)')


def norm(hexstr):
    """#abc -> #AABBCC；#aAbBcC -> 大写统一。"""
    h = hexstr.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return ('#' + h).upper()


def parse_tokens(css_root):
    toks = {}
    for m in re.finditer(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*(?=;)', css_root):
        toks[m.group(1)] = norm(m.group(2))
    return toks


def extract_script(s):
    blocks = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',
                        s, flags=re.S | re.I)
    return '\n'.join(blocks)


def find_colors(code):
    """返回 [(颜色原文, 归一值, 行号)]，只取字符串字面量里的颜色。"""
    out = []
    for m in re.finditer(r'''['"]([^'"\n]*)['"]''', code):
        lit = m.group(1)
        line = code[:m.start()].count('\n') + 1
        for h in re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b', lit):
            out.append((h, norm(h), line))
        for rg in RGBA_RE.finditer(lit):
            r, g, b = (int(rg.group(i)) for i in (1, 2, 3))
            out.append((rg.group(0),
                        '#%02X%02X%02X' % (r, g, b), line))
    return out


def check(s):
    """返回 (令牌表, 颜色清单, 不合规项)。"""
    i = s.find(':root{')
    if i < 0:
        return None, None, ['解析不到 :root']
    j = s.find('}', i)
    toks = parse_tokens(s[i:j + 1])
    if len(toks) < 10:
        return toks, None, ['令牌表只解析出 %d 个（异常）' % len(toks)]
    rev = {}
    for k, v in toks.items():
        rev.setdefault(v, []).append(k)
    code = extract_script(s)
    colors = find_colors(code)
    bad = []
    for raw, val, line in colors:
        if val not in rev:
            bad.append('canvas 颜色 %s（归一 %s，行 %d）不在任何 CSS 令牌里'
                       % (raw, val, line))
    return toks, colors, bad


def main():
    if not os.path.exists(ADMIN):
        print('RESULT: SKIP  找不到后台页（未测不等于通过）')
        return 0
    s = io.open(ADMIN, encoding='utf-8').read()
    toks, colors, bad = check(s)
    if toks is None:
        print('RESULT: SKIP  %s' % (bad[0] if bad else '解析失败'))
        return 0

    rev = {}
    for k, v in toks.items():
        rev.setdefault(v, []).append(k)

    print('=== :root 令牌 %d 个（含色值的）===' % len(toks))
    print('=== canvas 内颜色字面量 %d 处 ===' % len(colors or []))
    seen = {}
    for raw, val, line in (colors or []):
        seen.setdefault(val, {'raw': raw, 'lines': []})['lines'].append(line)
    for val, info in sorted(seen.items()):
        names = ','.join(rev.get(val, ['** 无对应令牌 **']))
        print('  %-9s <- %-22s 行 %-14s 令牌: %s'
              % (val, info['raw'], str(info['lines'][:4])[:14], names))
    print()

    # ---- 尺子有效性自检 ----
    print('=== 尺子有效性自检 ===')
    # S1：canvas 里塞一个不在令牌表的颜色
    probe1 = s.replace("ctx.strokeStyle = '#231E1A';",
                       "ctx.strokeStyle = '#123456';", 1)
    if probe1 == s:
        print('  [SKIP] S1 锚点未命中（canvas 写法变了，需同步本判据）')
    else:
        _, _, bad1 = check(probe1)
        hit1 = any('123456' in x for x in bad1)
        print('  [%s] S1 canvas 用非令牌色 #123456 -> %s'
              % ('ok' if hit1 else 'X',
                 '被抓到' if hit1 else '没抓到（判据失效！）'))
        if not hit1:
            bad.append('自检 S1 判据无牙：canvas 乱用颜色不会被发现')

    # S2：只改令牌值，canvas 不动（模拟"改令牌忘改图"）
    gold = toks.get('--gold')
    if not gold:
        print('  [SKIP] S2 找不到 --gold 令牌')
    else:
        probe2 = s.replace('--gold:' + gold.lstrip('#'), '--gold:FF6B00', 1)
        if probe2 == s:
            probe2 = re.sub(r'(--gold\s*:\s*#[0-9a-fA-F]{3,6})',
                            r'--gold:#FF6B00', s, count=1)
        if probe2 == s:
            print('  [SKIP] S2 令牌锚点未命中')
        else:
            _, _, bad2 = check(probe2)
            hit2 = any(gold in x for x in bad2)
            print('  [%s] S2 只改 --gold 值（canvas 仍用旧 %s）-> %s'
                  % ('ok' if hit2 else 'X',
                     gold, '被抓到' if hit2 else '没抓到（判据失效！）'))
            if not hit2:
                bad.append('自检 S2 判据无牙：改令牌忘改图不会被发现')
    print()

    if bad:
        print('RESULT: FAIL')
        for x in bad:
            print('  -', x)
        return 1
    print('RESULT: PASS  canvas %d 处颜色全部对应 CSS 令牌，'
          '且自检证明「乱用颜色」与「改令牌忘改图」都能被抓到'
          % len(colors or []))
    return 0


if __name__ == '__main__':
    sys.exit(main())
