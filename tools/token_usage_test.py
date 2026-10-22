# -*- coding: utf-8 -*-
r"""tools/token_usage_test.py —— 令牌必须真被使用（禁「假供给」），但只判可修的那类。

## 为什么需要（轮136 实测）
扫描发现两个间距令牌定义了却零引用：
  --sp-1 (8px)    0 处 var() 引用，但 8px 字面量在间距声明里出现 14 次
  --she-black     0 处引用，值在 CSS 里以字面量写了两处
即设计系统宣称有这一档，代码里却是散落的字面量 —— 改 :root 不传导，
等于一份**假供给**（与 U-395/401/408/428 同族：规则写着没人守）。
本轮已把 15 + 2 处字面量接回令牌，本判据负责让这种事不再悄悄发生。

## 规则必须收窄（轮136 的关键取舍）
第一版规则是「零 var() 引用即判红」，实跑立刻报 8 个死令牌。逐个查后发现
其中 7 个**值在 CSS 里一次都没以字面量写过**：
  · --she-blue #1E3A5F 的值用在 3 个 SVG 与 ar-scenes.js 里 ——
    那些位置结构上无法引用 CSS 变量，令牌是品牌色的文档锚点
  · --she-silver / --she-paper-2 / --she-blue-deep / --red-hi / --ok
    是品牌调色板里尚未上屏的条目
  · --fg-ghost 只有带 alpha 的 rgba 变体在用，无法用 var() 等价替换
把它们判红就是**拿臆断当规格**（U-409），且会逼后人为了变绿
去删合法的品牌调色板 —— 一个只会报红的判据和一个恒绿的判据同样不可信（U-440）。

所以最终规则：
  FAIL  令牌零 var() 引用，**且其值在同一 CSS 作用域内以字面量出现**
        —— 这才是「改令牌不传导」，且可机械修复（值不变）
  INFO  零引用但值未以字面量出现在 CSS 里 —— 属供给冗余/调色板，
        如实报告但不判红（删留是设计决策，不由判据代劳）

## 引用形式（三种都算，实测过才不会漏判）
  var(--x) / var( --x ,) / getComputedStyle().getPropertyValue('--x')
  以及另一个令牌的值里引用它
## 防自伤（U-399）
先剥注释：注释里的出现既不算引用、也不算字面量使用。

## 尺子有效性自检（U-149/U-151）
  S1 令牌零引用且值以字面量写在 CSS 里 -> 必须 FAIL（真缺陷要能抓）
  S2 令牌被 var() 正常引用             -> 不得误报
  S3 令牌零引用且值在 CSS 里没写过      -> 必须只 INFO 不 FAIL
      （这条防的就是第一版那个过紧规则）
  S4 仅被 getPropertyValue 引用         -> 不得误报
  S5 只在注释里出现                     -> 不算引用（否则注释能骗过判据）
  S6 当前两站状态                       -> 不得误报
任一失效即判 FAIL。自检在内存造文本，不写盘。
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
FAMILY = r'(?:sp|sec-y|fs|she|fg|bg|panel|line|gold|red|ok)[\w-]*'
DEF = re.compile(r'(--' + FAMILY + r')\s*:\s*([^;}]+)')
USE_VAR = re.compile(r'var\(\s*(--[\w-]+)\s*[,)]')
USE_GPC = re.compile(r"getPropertyValue\(\s*['\"](--[\w-]+)['\"]")


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    s = re.sub(r'^\s*//.*$', ' ', s, flags=re.M)
    return s


def css_of(text, path):
    if path.endswith('.css'):
        return text
    return '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', text, flags=re.S))


def analyze(css_src):
    """css_src 须已剥注释。返回 (fails, infos, 令牌数)。"""
    i = css_src.find(':root')
    if i < 0:
        return [], [], 0
    j = css_src.find('}', i)
    root = css_src[i:j]
    defs = [(m.group(1), m.group(2).strip()) for m in DEF.finditer(root)]
    if not defs:
        return [], [], 0
    used = set(USE_VAR.findall(css_src)) | set(USE_GPC.findall(css_src))
    for m in DEF.finditer(css_src):
        used |= set(USE_VAR.findall(m.group(2)))
    fails, infos = [], []
    for name, val in defs:
        if name in used:
            continue
        # 值是否以字面量写在 CSS 里（排除 :root 的定义行本身）
        body = css_src[:i] + ' ' * (j - i) + css_src[j:]
        lit = len(re.findall(re.escape(val), body, re.I))
        if lit:
            fails.append('%s 定义了但零引用，其值 %s 仍以字面量写在 CSS 里'
                         '（%d 处）—— 改令牌不传导，应改为 var(%s)'
                         % (name, val, lit, name))
        else:
            infos.append('%s（值 %s）未被引用，但值也没写在 CSS 里 —— '
                         '属调色板/供给冗余，删留是设计决策' % (name, val))
    return fails, infos, len(defs)


def selftest():
    bad = []
    # S1 真缺陷
    s1 = ':root{--sp-9:300px}\n.a{padding:300px}\n'
    f1, i1, _ = analyze(strip_comments(s1))
    ok1 = len(f1) == 1 and '--sp-9' in f1[0]
    print('  [%s] S1 零引用且值以字面量写在 CSS -> %s'
          % ('ok' if ok1 else 'X', 'FAIL' if f1 else '放过（漏判！）'))
    if not ok1:
        bad.append('S1 未抓到真缺陷')
    # S2 正常引用
    s2 = ':root{--sp-9:300px}\n.a{padding:var(--sp-9)}\n'
    f2, _, _ = analyze(strip_comments(s2))
    ok2 = not f2
    print('  [%s] S2 被 var() 引用 -> %s' % ('ok' if ok2 else 'X',
          '不误报' if ok2 else '误报'))
    if not ok2:
        bad.append('S2 误报正常引用')
    # S3 零引用但值没写在 CSS 里 -> 只 INFO
    s3 = ':root{--she-x:#123456}\n.a{color:red}\n'
    f3, i3, _ = analyze(strip_comments(s3))
    ok3 = (not f3) and len(i3) == 1
    print('  [%s] S3 零引用且值未写在 CSS -> %s'
          % ('ok' if ok3 else 'X',
             '只 INFO（正确）' if ok3 else
             ('误判 FAIL（口径过紧）' if f3 else '完全没报告')))
    if not ok3:
        bad.append('S3 把合法调色板条目判成缺陷，或漏报')
    # S4 getPropertyValue 引用
    s4 = (':root{--sp-8:200px}\n'
          ".a{color:getComputedStyle(x).getPropertyValue('--sp-8')}\n")
    f4, _, _ = analyze(strip_comments(s4))
    ok4 = not f4
    print('  [%s] S4 仅 getPropertyValue 引用 -> %s'
          % ('ok' if ok4 else 'X', '不误报' if ok4 else '误报'))
    if not ok4:
        bad.append('S4 误判 getPropertyValue')
    # S5 注释不算引用
    s5 = ':root{--sp-7:140px}\n/* 用 var(--sp-7) 就好了 */\n.a{color:red}\n'
    f5, i5, _ = analyze(strip_comments(s5))
    ok5 = (not f5) and len(i5) == 1
    print('  [%s] S5 只在注释里提到 -> %s'
          % ('ok' if ok5 else 'X',
             '不算引用（正确）' if ok5 else '被注释骗过'))
    if not ok5:
        bad.append('S5 注释里的 var() 被当成引用')
    return bad


def main():
    print('=== 尺子有效性自检 ===')
    bs = selftest()
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1
    fails = []
    infos = []
    untested = []
    total = 0
    for label, path in TARGETS:
        if not os.path.exists(path):
            untested.append(label)
            print('[%s] 读不到文件 -> 未测' % label)
            continue
        src = strip_comments(css_of(io.open(
            path, encoding='utf-8', errors='ignore').read(), path))
        f, inf, n = analyze(src)
        if n == 0:
            untested.append('%s（解析不到令牌）' % label)
            print('[%s] 解析不到 :root 设计令牌 -> 未测' % label)
            continue
        total += n
        print('[%s] 设计令牌 %d 个：可修缺陷 %d、仅提示 %d'
              % (label, n, len(f), len(inf)))
        fails += ['%s：%s' % (label, x) for x in f]
        infos += ['%s：%s' % (label, x) for x in inf]
    print()
    if fails:
        print('RESULT: FAIL  %d 个令牌是「假供给」（值在用但没走令牌）：'
              % len(fails))
        for x in fails:
            print('  -', x)
        return 1
    if infos:
        print('提示（不判红，删留由设计决定）：')
        for x in infos:
            print('  ·', x[:118])
        print()
    if untested:
        print('RESULT: SKIP  未测面：%s（未测不等于通过）' % '、'.join(untested))
        return 0
    print('RESULT: PASS  两站 %d 个设计令牌无「假供给」（零引用且值仍以字面量'
          '写在 CSS 里的情况为 0），且 6 项自检证明该判的判得、不该判的不误伤'
          % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
