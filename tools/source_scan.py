# -*- coding: utf-8 -*-
"""tools/source_scan.py —— 统一的源码扫描层（判据专用）。

## 为什么需要它

轮17 一次踩了两个同源误报：
  1) 字体完整性判据把 HTML 注释里的「声/念/确」当成渲染文本 → 误报缺 3 字
  2) 同一个判据把 JS 注释里的 alt="" 两个引号当成字符串定界符
     → 注释文字「读屏会连续念两遍」被当成内容

根因是**同一个**：判据直接 read() 原始文件就开始匹配，没有区分
「代码」与「注释」「字符串」。注释是写给人看的，写得越详细越容易触发这类误报
（我已经连续两轮被自己的注释坑到）。

## 提供什么

  strip_html_comments(s)  剥 <!-- --> 与 <script>/<style> 块
  visible_text(html)      取标签之间的可见文本（已解实体）
  strip_js_comments(s)    剥 /* */ 与 //（跳过字符串内的 //，如 "https://"）
  js_strings(s)           提取 JS 字符串字面量（已剥注释，不会被注释里的引号干扰）
  stripped(css)           剥 CSS 注释

## 设计原则

- 剥注释要**保守**：宁少剥，不误伤真实内容（例如字符串里的 "//" 不能当注释）
- 所有判据都应通过本模块读取源码，而不是各自 read()
- 每个函数都附带反向用例注释，说明它防的是什么误报

## 用法

    from tools.source_scan import visible_text, js_strings, stripped
    html = open('site/index.html', encoding='utf-8').read()
    text = visible_text(html)          # 不含注释、不含标签
    js = open('site/assets/js/main.js', encoding='utf-8').read()
    for lit in js_strings(js):         # 只拿真正的字符串字面量
        ...
"""
import html as _html
import re


def strip_html_comments(s):
    """剥 HTML 注释与 script/style 块。

    防误报：<!-- 声明 x-default --> 这类注释里的字曾被当作渲染文本，
    导致字体子集误判缺字。
    """
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    return s


def visible_text(html):
    """取 HTML 的可见文本：剥注释、剥标签、解实体。

    保留 data-decorative 元素的单字（首屏水印等来自属性而非普通文本）。
    """
    chars = []
    for m in re.finditer(r'data-decorative="[^"]*"[^>]*>([^<]{1,6})<', html):
        chars.append(m.group(1))
    s = strip_html_comments(html)
    s = re.sub(r'<[^>]+>', ' ', s)
    chars.append(_html.unescape(s))
    return ' '.join(chars)


def strip_js_comments(s):
    """剥 JS 注释，但**不误伤字符串里的 // 与 /* */。

    做法：状态机逐字符扫描，跟踪是否在字符串内。
    防误报：注释里的 alt="" 两个引号会被朴素正则当作字符串定界符，
    把注释文字当成内容（轮17 实测）。
    """
    out = []
    i, n = 0, len(s)
    quote = None          # 当前所在字符串的定界符
    while i < n:
        c = s[i]
        if quote:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        # 不在字符串里
        if c in ('"', "'", '`'):
            quote = c
            out.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n:
            nxt = s[i + 1]
            if nxt == '/':
                while i < n and s[i] != '\n':
                    i += 1
                continue
            if nxt == '*':
                i += 2
                while i + 1 < n and not (s[i] == '*' and s[i + 1] == '/'):
                    i += 1
                i += 2
                continue
        out.append(c)
        i += 1
    return ''.join(out)


def js_strings(s):
    """提取 JS 字符串字面量（已剥注释）。

    返回生成器，产出 (literal_text, start_index)。
    """
    clean = strip_js_comments(s)
    for m in re.finditer(r"['\"\x60]([^'\"\x60\n]{1,400})['\"\x60]", clean):
        yield m.group(1), m.start()


def stripped(css):
    """剥 CSS 注释。

    防误报：CSS 注释里的中文曾被当作渲染内容（如「正确基准」的「确」）。
    """
    return re.sub(r'/\*.*?\*/', ' ', css, flags=re.S)


def selftest():
    """自检：每个函数都应通过其反向用例。"""
    ok = True

    # 1) HTML 注释不得出现在可见文本里
    h = '<p>正文</p><!-- 这条注释里的"声念确"不该出现 -->'
    v = visible_text(h)
    if '声' in v or '念' in v:
        print('[FAIL] visible_text 把 HTML 注释当文本')
        ok = False
    else:
        print('[OK] visible_text 已剥 HTML 注释')

    # 2) JS 注释里的引号不得干扰字符串提取
    js = ('var a = "real";' + chr(10) +          '/* 注释里的 alt="" 不应被当字符串 */' + chr(10) +          'var b = "also-real";')
    lits = [t for t, _ in js_strings(js)]
    if 'real' in lits and 'also-real' in lits and not any('注释' in t for t in lits):
        print('[OK] js_strings 已剥注释（注释里的引号不干扰）')
    else:
        print('[FAIL] js_strings 被注释干扰:', lits[:5])
        ok = False

    # 3) 字符串里的 // 不能被当注释
    js2 = 'var url = "https://example.com/a"; // 尾注释'
    lits2 = [t for t, _ in js_strings(js2)]
    if any('https://example.com' in t for t in lits2):
        print('[OK] js_strings 保留了字符串内的 //')
    else:
        print('[FAIL] js_strings 误删了 URL 字符串:', lits2)
        ok = False

    # 4) CSS 注释不得被当内容
    c = '.a{color:red} /* 正确基准 不该出现 */ .b{color:blue}'
    if '确' not in stripped(c):
        print('[OK] stripped 已剥 CSS 注释')
    else:
        print('[FAIL] stripped 未剥 CSS 注释')
        ok = False

    print()
    print('RESULT: PASS  源码扫描层自检通过' if ok else 'RESULT: FAIL  自检未通过')
    return 0 if ok else 1


if __name__ == '__main__':
    import sys
    sys.exit(selftest())
