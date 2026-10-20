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
