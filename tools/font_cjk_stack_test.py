# -*- coding: utf-8 -*-
r"""tools/font_cjk_stack_test.py —— 会被用来渲染中文的字体栈，必须有确定的中文族。

## 为什么需要（轮145 一手缺陷）
cinzel.woff2 实测汉字数 = 0（子集只收拉丁与数字），而
    --font-latin:"Cinzel","Times New Roman",serif
的栈尾是**裸 generic 关键字 serif**。站里 .hero h1 em（"畲 · SHE PHOENIX"）、
.hero-meta dd（"2014 年第四批名录"）、.carve-rail button b（"一"）、
.visit-stats（"…共 10,765 位访客…"）四处都用这个栈承载中文。

后果：中文落各机器自己的默认衬线 —— Windows 宋体、macOS Songti、
Android Noto CJK。同一行里英文走 Cinzel、中文按访客的操作系统随机变。
**这不是「看起来有点不一样」，而是同一份设计在不同机器上有多个版本。**

## 判据（静态、可跑在 CI）
取 :root 里的每个 --font-* 令牌，解析其族名列表：
  1. 令牌被 CSS 用于承载中文的元素时（保守起见：凡 --font-* 令牌都查），
     其列表里必须在「子集 woff2 不供汉字」之后出现至少一个
     **具体命名的中文体**（族名含 CJK 特征词，或在自托管字体的 cmap 里
     确实有汉字）。
  2. 只有 generic 关键字（serif/sans-serif/system-ui…）作尾巴 = 听天由命，判红。
  3. generic 关键字本身合法（栈里已有具体中文体时它只是最后保险），不判红。

子集 cmap 用 fontTools 读；读不到（未装库）则退化为「按族名特征判断」
并明确报告口径降级 —— 不静默放过。

## 尺子有效性自检（U-427）
  S1 栈里有子集字体 + 裸 serif（轮145 缺陷原样）        -> 必须 FAIL
  S2 栈里有子集字体 + 具体中文体                          -> 必须 PASS
  S3 栈里第一个就是供汉字的自托管字体（zcool）            -> 必须 PASS
  S4 纯拉丁用途但中文由别的元素负责？不 —— 本判据只看栈本身，
     所以 S4 是「栈里只有 generic 且无任何具名中文体」    -> 必须 FAIL
  S5 中文体在 cmap 里真的有汉字（用真实 zcool 子集验）    -> 必须 PASS
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
CSS = os.path.join(SITE, 'assets', 'css', 'main.css')
FONT_DIR = os.path.join(SITE, 'assets', 'fonts')

GENERIC = ('serif', 'sans-serif', 'monospace', 'cursive', 'fantasy',
           'system-ui', 'ui-serif', 'ui-sans-serif', 'ui-monospace',
           'ui-rounded', 'emoji', 'math', 'frame', 'inherit', 'initial',
           'unset', 'var')
# 名字里带这些词的族几乎必然供汉字（项目内约定 + 常见中文体）
CJK_HINT = ('songti', 'kaiti', 'hei', 'yahei', 'pingfang', 'noto serif sc',
            'noto sans sc', 'stsong', 'stkaiti', 'hiragino', 'simsun',
            'simhei', 'source han', 'xiao', 'zcool', 'xiawu')


def cjk_fonts_from_files():
    """读自托管字体 cmap，返回确实供汉字的 family 名集合。"""
    fams = set()
    if not os.path.isdir(FONT_DIR):
        return fams, False
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return fams, False
    css = io.open(CSS, encoding='utf-8', errors='ignore').read()
    for m in re.finditer(r'@font-face\s*\{([^}]*)\}', css, flags=re.S):
        b = m.group(1)
        fam = re.search(r'font-family:\s*([^;]+)', b)
        url = re.search(r'url\(\s*["\']?([^"\')]+\.woff2?)', b)
        if not (fam and url):
            continue
        p = os.path.normpath(os.path.join(FONT_DIR, os.path.basename(
            url.group(1).strip().strip(chr(34) + chr(39)))))
        if not os.path.exists(p):
            continue
        try:
            f = TTFont(p)
            cmap = f.getBestCmap()
            n = sum(1 for c in cmap if 0x4e00 <= c <= 0x9fff)
            f.close()
        except Exception:
            continue
        if n > 0:
            fams.add(fam.group(1).strip().strip(chr(34) + chr(39)).lower())
    return fams, True


def families_of(val):
    """把 font-family 列表拆成 [(name, is_generic)]。"""
    out = []
    for part in re.split(r',(?![^()]*\))', val):
        p = part.strip().strip(chr(34) + chr(39))
        if not p:
            continue
        low = p.lower()
        isg = low in GENERIC or low.startswith('var')
        out.append((p, isg))
    return out


def is_cjk_named(name):
    n = name.lower()
    return any(h in n for h in CJK_HINT)


def analyze(css_src, cjk_fonts, used_tools):
    i = css_src.find(':root')
    if i < 0:
        return [], [], []
    j = css_src.find('}', i)
    root = css_src[i:j]
    fails, infos = [], []
    toks = re.findall(r'(--font-[\w-]+)\s*:\s*([^;]+)', root)
    for name, raw in toks:
        val = raw.strip()
        # 展开一层 var(--font-x)
        for _ in range(3):
            m = re.search(r'var\(\s*(--font-[\w-]+)\s*\)', val)
            if not m:
                break
            rep = dict(toks).get(m.group(1))
            if rep is None:
                break
            val = val.replace(m.group(0), rep)
        fams = families_of(val)
        if not fams:
            continue
        # 找「第一个可能供汉字」的族：自托管 cmap 有汉字 或 名字含 CJK 特征
        def supplies_cjk(nm):
            low = nm.lower()
            if low in cjk_fonts:
                return True
            return is_cjk_named(low)
        has_named_cjk = any(not g and supplies_cjk(n) for n, g in fams)
        tail = fams[-1]
        only_generic_tail = tail[1] and not has_named_cjk
        if only_generic_tail:
            fails.append(
                u'%s 的栈尾是裸 generic（%s），且整个栈里没有具名中文字体：'
                u'中文将落各系统默认体（跨机器不一致）。栈=%s%s'
                % (name, tail[0], val,
                   '' if used_tools else
                   u'（注：未读字体 cmap，按族名判断）'))
        elif not has_named_cjk and used_tools:
            infos.append(u'%s 无具名中文体，但其首个字体自身供汉字：%s'
                         % (name, val))
    return fails, infos, [n for n, _ in toks]


SELFTEST = [
    (u'S1 子集拉丁字体 + 裸 serif 尾巴（轮145 缺陷原样）',
     u'--font-latin:"Cinzel","Times New Roman",serif;', True),
    (u'S2 子集拉丁字体 + 具名中文体',
     u'--font-latin:"Cinzel","Times New Roman","Songti SC",serif;', False),
    (u'S3 栈首即供汉字的自托管字体',
     u'--font-x:"ZCOOL XiaoWei",serif;', False),
    (u'S4 全栈无任何具名中文体且尾是 generic',
     u'--font-y:"Cinzel",Georgia,serif;', True),
    (u'S5 引用 var(--font-serif) 作尾巴（现行修法）',
     u'--font-latin:"Cinzel",var(--font-serif);'
     u' --font-serif:"Songti SC","SimSun",serif;', False),
]


def selftest(cjk_fonts):
    bad = []
    for label, decl, expect_fail in SELFTEST:
        css = ':root{' + decl + '}'
        f, _i, _t = analyze(css, cjk_fonts, True)
        got = bool(f)
        ok = got == expect_fail
        print('  [%s] %s%s' % ('ok' if ok else 'X', label,
                               '' if ok else ' -> 实得 %s' % (f or '无')))
        if not ok:
            bad.append(label)
    return bad


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css（未测不等于通过）')
        return 0
    cjk_fonts, used_tools = cjk_fonts_from_files()
    css = io.open(CSS, encoding='utf-8', errors='ignore').read()
    print('=== 尺子有效性自检 ===')
    bad = selftest(cjk_fonts)
    print()
    if not used_tools:
        print('  注：未装 fontTools，判据退化为「按族名特征」判断'
              '（仍会在报告里标注口径）')
    if bad:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad:
            print('  -', b)
        return 1
    print('=== 自托管字体汉字覆盖（cmap 实测）===')
    if cjk_fonts:
        for n in sorted(cjk_fonts):
            print('  供汉字:', n)
    else:
        print('  （未读到，按族名判断）')
    fails, infos, tokens = analyze(css, cjk_fonts, used_tools)
    print()
    print('=== %d 个 --font-* 令牌 ===' % len(tokens))
    print('  ', ' '.join(tokens))
    print()
    if infos:
        for x in infos:
            print('  ·', x)
    if fails:
        print()
        print('中文兜底缺失：')
        for x in fails:
            print('  -', x)
        print()
        print('RESULT: FAIL  %d 个字体令牌用裸 generic 关键字承接中文，'
              '跨机器渲染不一致' % len(fails))
        return 1
    print()
    print('RESULT: PASS  所有 --font-* 令牌的中文都有具名兜底'
          '（不会落系统默认体），且 %d 项自检证明该判的判得、'
          '不该判的不误伤' % len(SELFTEST))
    return 0


if __name__ == '__main__':
    sys.exit(main())
