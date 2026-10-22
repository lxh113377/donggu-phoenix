# -*- coding: utf-8 -*-
r"""tools/microinteraction_test.py —— 微交互反馈判据（纯静态，CI 可跑，两站）。

## 为什么需要它
轮31 静态审查 13 类可交互元素的 hover/active 覆盖，发现两处缺口：
  #cam .close   摄像头关闭按钮（44×44 常驻可见）—— hover 与 active 都没有
  .nav-toggle   移动端菜单按钮 —— 有 active 缺 hover
鼠标悬停毫无反馈，用户不确定它可点。这是「看起来能点但没反应」的典型。

## 轮137 扩展到后台
原判据只读 main.css，**后台 admin/index.html 完全不在覆盖内** ——
于是后台唯一导航出口「返回展馆首页」零反馈，长期无人发现。
本轮用 CDP 的 CSS.forcePseudoState 实测坐实：常态 color
rgb(156,123,63)，强制 :hover 与 :active 后计算值**完全不变**。
（静态只能看「有没有写规则」；写了但被更高优先级覆盖成同值，
 同样等于没反馈 —— 那种情况要靠伪类实测，见 _qa/verify_admin_hover.py。）

## 判据
  A 两站各自的全局 :focus-visible 兜底必须存在（键盘焦点可见）
  B 主站核心交互元素：同时具备 :hover 与 :active（或由全局规则提供）
  C 后台核心交互元素：同上（选择器形态与主站不同，逐个给正则）
    tr 只要 :hover —— 表格行不是链接，按下无「执行」语义，
    机械要求 :active 属过度约束（同 brand 的豁免理由）

## 白名单（有特殊设计的元素）
  brand —— hover 是图标旋转 rotate(-8deg) scale(1.06)，已是有设计感的反馈，
           不需要再加 active。机械要求 active 反而是过度约束。
  tr    —— 行悬停高亮已足够，行本身不可点。

## 已确认的全局兜底
  :focus-visible  主站统一 outline:2px solid var(--she-gold)、
                  后台统一 outline:2px solid var(--gold)，
  所以各元素不必各自声明焦点样式。

## 尺子有效性自检（U-149/U-151；本判据原先没有自检，轮137 补上）
  S1 摘掉主站某核心元素的 :hover 规则 -> 必须 FAIL
  S2 摘掉后台 footer a 的 :hover 规则 -> 必须 FAIL（后台面真在被检查）
  S3 当前两站状态 -> 不得误报
任一失效即判 FAIL —— 否则本判据是恒绿的安慰剂。
自检在内存里改文本，不写盘。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
ADMIN = os.path.join(BASE, 'site', 'admin', 'index.html')

# 主站：需要 hover + active 的核心交互元素（类名）
CORE = [
    'ar-btn', 'hero-cta', 'btn', 'btn-ask', 'ar-icon',
    'carve-play', 'nav-toggle', 'totem-hit', 'close',
]
# 有特殊 hover 设计、豁免 active 的元素
EXEMPT_ACTIVE = {'brand'}

# 后台：选择器形态多样（元素/后代），逐个给正则
# (名称, hover 正则, 是否要求 active)
ADMIN_TARGETS = [
    ('.btn', r'\.btn[^{},]*:hover', True),
    ('select', r'(?<![\w-])select[^{},;]*:hover', True),
    ('footer a', r'footer\s+a[^{},;]*:hover', True),
    ('tr（表格行）', r'(?<![\w-])tr[^{},;]*:hover', False),
]


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    return s


def admin_css():
    raw = io.open(ADMIN, encoding='utf-8', errors='ignore').read()
    return strip_comments('\n'.join(
        re.findall(r'<style[^>]*>(.*?)</style>', raw, flags=re.S)))


def check_core(css):
    """主站核心元素 -> fails。"""
    fails = []
    for cls in CORE:
        esc = re.escape(cls)
        # 要求规则**以该选择器开头**（允许前导 .a .b 这类祖先），
        # 避免被组合选择器里顺带提到的同类名误判。
        has_hover = bool(re.search(r'(^|[,}\s])\.%s[^{},]*:hover' % esc,
                                   css, re.M))
        has_active = bool(re.search(r'(^|[,}\s])\.%s[^{},]*:active' % esc,
                                    css, re.M))
        if not has_hover:
            fails.append('.%s 缺 :hover 反馈' % cls)
        if not has_active and cls not in EXEMPT_ACTIVE:
            fails.append('.%s 缺 :active 反馈' % cls)
    return fails


def check_admin(css):
    """后台核心元素 -> fails。"""
    fails = []
    for name, pat, need_active in ADMIN_TARGETS:
        if not re.search(pat, css):
            fails.append('%s 缺 :hover 反馈' % name)
        if need_active and not re.search(pat.replace(':hover', ':active'), css):
            fails.append('%s 缺 :active 反馈' % name)
    return fails


def has_global_focus(css):
    # 只认「行首的 :focus-visible」（全局兜底）；
    # 局部规则如 #carve-stage:focus-visible 不能当全局兜底。
    return bool(re.search(r'(^|\})\s*:focus-visible\s*\{', css))


def _strip_pseudo(css, sel_pat, pseudo=':hover'):
    """把匹配 sel_pat 的选择器里的伪类本身去掉。

    轮137 自检第一版失败的原因：当时是改选择器名
    （.ar-btn -> .ar-btn-x），而检测正则 \\.ar-btn[^{},]*:hover 里的
    [^{},]* 正好能吃掉 -x 后缀，于是「摘掉」之后依然匹配 ——
    是构造错，不是判据无牙。**要摘就得摘伪类本身。**
    """
    return re.sub(sel_pat,
                  lambda m: m.group(0).replace(pseudo, ':gone'), css)


def selftest(main_css, adm_css):
    bad = []
    base_main = check_core(main_css)
    base_adm = check_admin(adm_css)
    # S1 摘掉主站一个核心元素的 :hover（所有匹配处一起摘）
    pat1 = r'(^|[,}\s])\.ar-btn[^{},]*:hover'
    s1_css = _strip_pseudo(main_css, pat1)
    if s1_css == main_css:
        bad.append('S1 构造失败：主站找不到 .ar-btn 的 :hover 规则')
    else:
        got = [x for x in check_core(s1_css) if 'ar-btn' in x and 'hover' in x]
        ok = bool(got) and not base_main
        print('  [%s] S1 摘掉主站 .ar-btn 的 :hover -> %s'
              % ('ok' if ok else 'X', '被抓到' if got else '没抓到'))
        if not ok:
            bad.append('S1 主站面未抓到缺失的 :hover')
    # S2 摘掉后台 footer a 的 :hover
    pat2 = r'footer\s+a[^{},;]*:hover'
    s2 = _strip_pseudo(adm_css, pat2)
    if s2 == adm_css:
        bad.append('S2 构造失败：后台没有 footer a:hover（后台面可能没在被检查）')
    else:
        got2 = [x for x in check_admin(s2) if 'footer a' in x and 'hover' in x]
        ok2 = bool(got2) and not base_adm
        print('  [%s] S2 摘掉后台 footer a 的 :hover -> %s'
              % ('ok' if ok2 else 'X',
                 '被抓到' if got2 else '没抓到（后台面形同虚设）'))
        if not ok2:
            bad.append('S2 后台面未抓到缺失的 :hover')
    # S3 现状不得误报
    f3 = check_core(main_css) + check_admin(adm_css)
    print('  [%s] S3 两站当前状态 -> %s'
          % ('ok' if not f3 else 'X', '无误报' if not f3 else str(f3)[:70]))
    if f3:
        bad.append('S3 当前状态被误报：%s' % f3[:1])
    return bad


def main():
    if not os.path.exists(CSS):
        print('RESULT: SKIP  找不到 main.css')
        return 0
    main_css = strip_comments(io.open(CSS, encoding='utf-8',
                                      errors='ignore').read())
    if not os.path.exists(ADMIN):
        print('RESULT: SKIP  找不到后台页，后台面无法检查（未测不等于通过）')
        return 0
    adm_css = admin_css()
    if len(adm_css) < 200:
        print('RESULT: SKIP  后台内联样式解析异常（%d 字符）' % len(adm_css))
        return 0

    print('=== 尺子有效性自检 ===')
    bs = selftest(main_css, adm_css)
    print()
    if bs:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1

    fails = []
    for label, css in (('主站', main_css), ('后台', adm_css)):
        if not has_global_focus(css):
            fails.append('%s 缺少全局 :focus-visible 兜底（键盘焦点将不可见）'
                         % label)
        else:
            print('  %s 全局 :focus-visible 兜底存在' % label)
    fails += check_core(main_css)
    fails += check_admin(adm_css)
    print('检查 主站 %d 个核心元素 + 后台 %d 个'
          % (len(CORE), len(ADMIN_TARGETS)))
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  两站 %d 个核心交互元素均有 hover/active 反馈，'
          '全局焦点兜底齐备，且自检证明两面的缺失都能被抓到'
          % (len(CORE) + len(ADMIN_TARGETS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
