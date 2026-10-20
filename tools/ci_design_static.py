# -*- coding: utf-8 -*-
"""tools/ci_design_static.py —— 设计审计的静态半部（CI 可跑，无需浏览器）。

对应 tools/design_audit.py 的 static_checks()，单独抽出来是因为 CI 不装 Chromium。
判据来源全部是历史真缺陷：
  · :active 规则数     —— 补齐前是 0，触屏点击零反馈
  · 行长单位不用 ch    —— ch 在中文下按 "0" 宽算，会把行宽砍半（实测 77→18.9 字/行）
  · 无 UI 框架 / 无外链字体 / 无 AI 标配紫 —— 原创性底线
退出码：0 全过 / 1 有失败
"""
import os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')


def main():
    css = open(os.path.join(SITE, 'assets/css/main.css'), encoding='utf-8').read()
    html = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()

    fails, warns = [], []

    n_active = css.count(':active')
    if n_active < 5:
        fails.append('按下态不足：:active 规则 %d 条（触屏点击会零反馈）' % n_active)
    print('[%s] 按下态：%d 条 :active' % ('PASS' if n_active >= 5 else 'FAIL', n_active))

    bad_ch = re.findall(r'max-width:\s*\d+(?:\.\d+)?ch', css)
    if bad_ch:
        fails.append('行长使用 ch 单位 %s（中文下会砍半，应用 em）' % ', '.join(bad_ch[:3]))
    has_em = bool(re.search(r'max-width:\s*\d+(?:\.\d+)?em', css))
    if not has_em:
        fails.append('行长约束缺失：CSS 里没有以 em 为单位的 max-width')
    print('[%s] 行长：%s / 未误用 ch' % ('PASS' if has_em and not bad_ch else 'FAIL',
                                       '有 em 约束' if has_em else '无'))

    framework = [k for k in ('tailwind', 'bootstrap', '@apply', 'cdn.jsdelivr', 'unpkg.com')
                 if k in html or k in css]
    if framework:
        fails.append('引入外部 UI 框架/外链：' + ', '.join(framework))
    print('[%s] 零外部框架' % ('PASS' if not framework else 'FAIL'))

    ext_font = 'fonts.googleapis' in html or 'fonts.gstatic' in html
    if ext_font:
        fails.append('出现 Google Fonts 外链（违反零外部请求）')
    print('[%s] 字体自托管（无 Google Fonts 外链）' % ('PASS' if not ext_font else 'FAIL'))


    # 装饰环不得用会扩大布局盒的写法（轮11 U-07）：
    # 负 inset 会向外扩、超宽 width 会撑大盒子，两者都会让页面出现横向溢出，
    # 只是常被祖先 overflow 裁切掩盖。正解是 transform:scale（不参与布局盒计算）。
    for _sel in ('.hero-ring{', '.hero-ring.b{', '.totem-ring{', '.totem-ring.b{'):
        _i = css.find(_sel)
        if _i < 0:
            continue
        _rule = css[_i: css.find('}', _i)]
        if re.search(r'inset:\s*-', _rule):
            fails.append('装饰环 %s 使用负 inset（会扩大布局盒）' % _sel.rstrip('{'))
        _mw = re.search(r'width:\s*min\(\s*\d+%\s*,\s*(\d+)px\s*\)', _rule)
        if _mw and int(_mw.group(1)) >= 500:
            fails.append('装饰环 %s 的 width 上限 %spx 过大' % (_sel.rstrip('{'), _mw.group(1)))
    _ks = re.search(r'@keyframes slowSpin\{(.*?)\}\}', css, re.S)
    if _ks and 'scale' not in _ks.group(1):
        fails.append('@keyframes slowSpin 未保留 scale（动画会覆盖静态缩放）')
    print('[%s] 装饰环不溢出：无负 inset / 无超宽 width / keyframes 保留 scale' % (
        'PASS' if not any('装饰环' in f or 'slowSpin' in f for f in fails) else 'FAIL'))

    # 手机首屏必须真的是一屏（轮10 修复，轮13 静态化防回退）：
    # 回退根因是 CSS 写法 —— 手机断点若没有「锁一屏高度 + 画布 min-height:0」，
    # .hero{min-height:100svh} 会被 padding 与 .hero-visual{min-height:clamp(...)} 顶破，
    # 首屏再次被撑长（实测曾到 1.32~1.56 屏）。
    HERO_SVH = '100svh'
    _mb = []
    import re as _re
    for _m in _re.finditer(r'@media\s*\(max-width:\s*900px\)\s*\{', css):
        _start = _m.end()
        _depth, _i = 1, _start
        while _i < len(css) and _depth > 0:
            if css[_i] == '{':
                _depth += 1
            elif css[_i] == '}':
                _depth -= 1
            _i += 1
        _mb.append((_m.start(), css[_start:_i - 1]))
    if not _mb:
        fails.append('缺少 @media (max-width:900px) 块（手机首屏无锁定规则）')
    else:
        _pos, _blk = _mb[-1]
        _mh = _re.search(r'\.hero\s*\{([^}]*)\}', _blk)
        if not _mh:
            fails.append('手机断点缺少 .hero 规则')
        else:
            _b = _mh.group(1).replace(' ', '')
            if 'height:' + HERO_SVH not in _b:
                fails.append('.hero 手机端未设 height:' + HERO_SVH + '（首屏会被撑长）')
            if 'min-height:' + HERO_SVH not in _b:
                fails.append('.hero 手机端未设 min-height:' + HERO_SVH)
        _mv = _re.search(r'\.hero-visual\s*\{([^}]*)\}', _blk)
        if not _mv:
            fails.append('手机断点缺少 .hero-visual 规则')
        elif 'min-height:0' not in _mv.group(1).replace(' ', ''):
            fails.append('.hero-visual 手机端未设 min-height:0（clamp 会顶破一屏）')
        _base = css.find('.hero-visual{')
        if _base >= 0 and _pos < _base:
            fails.append('手机断点写在基础 .hero-visual 之前，会被 clamp 覆盖')
    print('[%s] 手机首屏锁定一屏：height/min-height 100svh + visual min-height:0 + 顺序正确' % (
        'PASS' if not any('首屏' in f or 'hero' in f.lower() for f in fails) else 'FAIL'))

    # 不透明背景 + backdrop-filter = 纯浪费合成层（轮13）
    # 背景不透明会把模糊结果完全盖住，但浏览器仍要为它建层、每帧重算。
    OPAQUE_BG = 0.9
    _waste = []
    for _m in _re.finditer(r'([^{}]+)\{([^}]*backdrop-filter[^}]*)\}', css):
        _sel, _body = _m.group(1).strip().split('\n')[-1], _m.group(2)
        if 'backdrop-filter:none' in _body.replace(' ', ''):
            continue
        # 只判「纯色 background」：渐变可能末端透明，blur 在那里是有效果的，
        # 从渐变里抽一个 rgba 当整块背景的透明度会误报（.nav 就是这么被误伤的）。
        _bg = _re.search(r'background\s*:\s*(rgba?\([^)]*\))', _body)
        if _bg:
            _rgba = _re.search(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)', _bg.group(1))
            if _rgba:
                _alpha = float(_rgba.group(4)) if _rgba.group(4) else 1.0
                if _alpha >= OPAQUE_BG:
                    _waste.append(_sel[:40])
    if _waste:
        fails.append('不透明背景下仍保留 backdrop-filter（纯白算合成层）：' + ', '.join(_waste[:3]))
    print('[%s] 无不透明背景 + backdrop-filter 白算组合' % (
        'PASS' if not _waste else 'FAIL'))

    # 段落顶部不得额外补偿顶栏（轮14）
    # 锚点跳转已由 html{scroll-padding-top} 处理；段落内再补一次会把内容整体推低。
    SEC_HARDCODED = []
    for _m in _re.finditer(r'([.#][\w-]*(?:sec|section)[\w-]*)\{([^}]*padding-top:\s*(?:calc|clamp)?\()', css):
        _sel, _body = _m.group(1), _m.group(2)
        if _sel.startswith('.hero'):
            continue
        SEC_HARDCODED.append(_sel)
    if SEC_HARDCODED:
        fails.append('段落顶部写死了补偿值（顶栏已由 scroll-padding-top 处理）：' + ', '.join(SEC_HARDCODED[:3]))
    print('[%s] 段落未重复补偿顶栏留白' % ('PASS' if not SEC_HARDCODED else 'FAIL'))

    purple = [c for c in ('#667eea', '#764ba2', '#8b5cf6', '#a855f7') if c in css.lower()]
    if purple:
        fails.append('出现 AI 标配紫渐变：' + ', '.join(purple))
    print('[%s] 无 AI 标配紫渐变' % ('PASS' if not purple else 'FAIL'))

    if warns:
        print('WARNINGS:')
        for w in warns:
            print('  !', w)
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  设计静态审计全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
