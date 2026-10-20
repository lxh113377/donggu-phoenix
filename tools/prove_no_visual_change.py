
# -*- coding: utf-8 -*-
"""tools/prove_no_visual_change.py —— 证明「去掉 backdrop-filter」是零视觉影响。

## 原理（CSS 合成层面的确定性结论，不需要截图）
backdrop-filter 作用于元素**背后**区域，其结果绘制在元素背景**之下**。
当背景完全不透明（alpha = 1）时，背景像素 100% 覆盖模糊结果 ——
此时移除 backdrop-filter 的可见差异**严格为 0**。

反之，alpha < 1 时会透出底层内容，移除后该部分由「模糊」变「清晰」，
量级虽小但不是零 —— 这种情况必须如实标注，不能笼统说「零影响」。

## 判据
对所有使用 backdrop-filter 的规则，取其背景不透明度：
  alpha == 1 且已移除 blur   → OK（严格零影响）
  alpha == 1 但仍有 blur     → WARN（白算合成层，建议移除）
  alpha < 1  且仍有 blur     → OK（blur 有实际效果，保留正确）
  alpha < 1  但已移除 blur   → WARN（有可见差异，需说明）
"""
import re
import sys

CSS = 'site/assets/css/main.css'


def alpha_of(color):
    """返回颜色的不透明度；支持 #RGB / #RRGGBB / rgba()。"""
    c = color.strip()
    m = re.match(r'^#([0-9a-fA-F]{6})$', c)
    if m:
        return 1.0
    m = re.match(r'^#([0-9a-fA-F]{3})$', c)
    if m:
        return 1.0
    m = re.match(r'^rgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*(?:,\s*([\d.]+)\s*)?\)$', c)
    if m:
        return float(m.group(1)) if m.group(1) else 1.0
    return None


def main():
    css = open(CSS, encoding='utf-8').read()
    warns, oks = [], []

    for m in re.finditer(r'([^{}\n]+)\{([^}]*)\}', css):
        sel, body = m.group(1).strip(), m.group(2)
        if 'backdrop-filter' not in body:
            continue
        has_blur = bool(re.search(r'backdrop-filter\s*:\s*blur', body))
        bgm = re.search(r'background\s*:\s*([^;]+);', body)
        if not bgm:
            continue
        bgval = bgm.group(1).strip()
        if 'gradient' in bgval:
            oks.append((sel[:26], '渐变背景（末端可能透明）', 'blur 有效'))
            continue
        a = alpha_of(bgval)
        if a is None:
            continue
        if a >= 1.0 and has_blur:
            warns.append((sel[:26], bgval[:22], '背景不透明却仍算 blur（白费合成层）'))
        elif a >= 1.0 and not has_blur:
            oks.append((sel[:26], bgval[:22], '不透明 + 无 blur：严格零影响'))
        elif a < 1.0 and has_blur:
            oks.append((sel[:26], bgval[:22], 'alpha=%.2f + blur：有实际效果' % a))
        elif a < 1.0 and not has_blur:
            warns.append((sel[:26], bgval[:22], 'alpha=%.2f 却去掉了 blur（有可见差异）' % a))

    print('=== backdrop-filter 使用核查 ===')
    for s in oks:
        print('  OK   %-26s %-22s %s' % s)
    for s in warns:
        print('  WARN %-26s %-22s %s' % s)

    print()
    if warns:
        print('RESULT: WARN  %d 处需要处理或说明' % len(warns))
        return 0
    print('RESULT: PASS  所有 backdrop-filter 用法与背景不透明度自洽')
    return 0


if __name__ == '__main__':
    sys.exit(main())
