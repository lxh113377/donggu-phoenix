# -*- coding: utf-8 -*-
r"""tools/cjk_punctuation_test.py —— 中文标点规范判据（纯静态，CI 可跑）。

## 为什么需要它（轮57 首查）
中文排版有硬规范（GB/T 15834）：中文语境必须用全角标点。
同族问题里字阶/行长/避头尾/中西文空格都查过，唯独标点没查。
「扫描它,让三百年」这种半角逗号，评委一眼能看出没走规范。

## 轮57 实测结论：无缺陷
  · 中文后跟半角 , ; : ? ! . ：0 处
  · 直角引号「」30/30 配对；半角括号 0/0
  · 半角连字符 -- ：0 处（破折号一律用 —— ，6 处）
  · 数量表达：正文用汉字（三段/一枚/四个），数据条用阿拉伯（3 段 · 13 章）
    —— 这是**符合规范的分工**（计量数值用阿拉伯、定型词组用汉字），不是不一致。
    故数字用法不设为机械判据：规范本身允许两种写法，机械判必然误报。

## 判据（只收可机械判定的三条）
1. 中文后不得紧跟半角 , ; : ? !（应为全角）
2. 中文后不得紧跟半角句号 .（但 2014.05 / v2.3 这类点后接数字合法，须放过）
3. 成对符号必须配平（直角引号、中文弯引号、括号）
4. 不得用 -- 代替中文破折号

## 自检先证明尺子有效（U-149/U-151 教训）
本项目已 12 次遇到「测不出 ≠ 不存在」。判据自带违例样本，
任一用例不符即判 FAIL —— 先证明尺子能抓到，再信它的 0。
自检必须走与实判完全相同的链路（U-151）。
"""
import html as H
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

CJK = r'[\u4e00-\u9fff]'
TIGHT_PUNCT = re.compile(CJK + r'[,;:?!]')
# 半角句号：后面不能是数字（2014.05、v2.3 合法）
TIGHT_DOT = re.compile(CJK + r'\.(?!\d)')
# 半角连字符当破折号用：中文 -- 中文
BAD_DASH = re.compile(CJK + r'--' + CJK)

PAIRS = [
    ('\u300c', '\u300d', '直角引号「」'),
    ('\u201c', '\u201d', '中文弯引号“”'),
    ('\u3010', '\u3011', '方头括号【】'),
    ('(', ')', '半角括号'),
]

# (样本, 是否应被抓到, 说明)
SELFTEST = [
    ('扫描它,让三百年', True, '中文后跟半角逗号'),
    ('国家级非遗:2014', True, '中文后跟半角冒号'),
    ('真的吗?是的', True, '中文后跟半角问号'),
    ('一句话结束.', True, '中文后跟半角句号'),
    ('一段--很好的话', True, '用 -- 代替破折号'),
    ('扫描它，让三百年', False, '正确全角逗号'),
    ('国家级非遗：2014', False, '正确全角冒号'),
    ('2014.05 发布', False, '点后接数字（日期）合法'),
    ('AR 展陈 v2.3', False, '版本号里的点合法'),
    ('一段——很好的话', False, '正确破折号'),
]

ESCAPES = re.compile(r"\\[nrtbfv0\\]|\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}")


def unescape_js(s):
    """JS 源码里的 \n 是 反斜杠+n 两个字符，运行时才是换行。
    不剥掉会污染判定（轮56 同类误报 U-150）。"""
    return ESCAPES.sub(' ', s)


def _js_string_literals(text):
    """从 JS 源码里抽含中文的字符串字面量。

    必须只抽字面量而不是整段扫：JS 里大量半角逗号/冒号是语法符号，
    整段扫会海量误报。
    """
    t = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    t = re.sub(r'//[^\n]*', ' ', t)
    out = []
    # 两条正则各自只排除自己那种引号：
    # HTML 模板串常含另一种引号（'<td colspan="9">暂无数据</td>'），
    # 若同时排除两种就漏掉最常承载中文 UI 文案的那类字面量（轮83）。
    # 量词必须是 {0,600}：{1,600} 无法识别空串 ''，
    # 会让 join('') : '<串>' 这种写法的引号配对整体错位，真串漏检（轮83）
    for rx in (r"'([^'\n]{0,600})'", r'"([^"\n]{0,600})"'):
        for m in re.finditer(rx, t):
            seg = m.group(1)
            if re.search(CJK, seg):
                out.append(unescape_js(seg))
    return out


def _scan_html_file(path):
    """一个 HTML：可见文本 + 内联 <script> 的中文字面量。

    轮83 前只取可见文本（把 <script> 整段剥掉），
    于是内联脚本里的对外文案（JSON-LD 的 name/description 等）漏检。
    """
    raw = open(path, encoding='utf-8', errors='ignore').read()
    no_comment = re.sub(r'<!--.*?-->', ' ', raw, flags=re.S)
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', no_comment,
                         flags=re.S | re.I)
    visible = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', no_comment,
                     flags=re.S | re.I)
    chunks = [H.unescape(re.sub(r'<[^>]+>', ' ', visible))]
    for body in scripts:
        chunks.extend(_js_string_literals(body))
    return chunks


def scan_text():
    """部署面会呈现的中文文本：主站 + 后台 + 数据脚本。"""
    chunks = []
    for rel in ('index.html', os.path.join('admin', 'index.html')):
        hp = os.path.join(SITE, *rel.split('/'))
        if os.path.exists(hp):
            chunks.extend(_scan_html_file(hp))
    d = os.path.join(SITE, 'assets', 'data')
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith('.js'):
                t = open(os.path.join(d, f), encoding='utf-8',
                         errors='ignore').read()
                chunks.extend(_js_string_literals(t))
    return ' '.join(chunks)


def hits_of(body):
    hits = []
    for rx, nm in ((TIGHT_PUNCT, '中文后跟半角标点'),
                   (TIGHT_DOT, '中文后跟半角句号'),
                   (BAD_DASH, '用 -- 代替破折号')):
        for m in rx.finditer(body):
            hits.append((nm, body[max(0, m.start() - 6):m.end() + 4]))
    return hits


def main():
    # 1) 自检：走与实判相同的链路
    bad = 0
    for txt, should, desc in SELFTEST:
        found = bool(hits_of(unescape_js(txt)))
        if found != should:
            bad += 1
            print('  [自检不符] %s 期望%s 实得%s' % (
                desc, '抓到' if should else '放过', '抓到' if found else '放过'))
    if bad:
        print('RESULT: FAIL')
        print('  - 判据自检 %d/%d 不符，读数不可信' % (bad, len(SELFTEST)))
        return 1
    print('[PASS] 自检 %d 个用例符合预期（尺子有效，0 不是恒零）' % len(SELFTEST))

    body = scan_text()
    if not re.search(CJK, body):
        print('RESULT: SKIP  扫描面里没有中文')
        return 0

    fails = []
    hits = hits_of(body)
    print('扫描中文文本 %d 字符' % len(body))
    if hits:
        for nm, ctx in hits[:8]:
            print('   - [%s] %s' % (nm, ctx.replace('\n', ' ')[:36]))
        fails.append('%d 处中文语境用了半角标点/半角破折号' % len(hits))

    for a, b, nm in PAIRS:
        ca, cb = body.count(a), body.count(b)
        if ca or cb:
            if ca != cb:
                fails.append('%s 不配对：%d / %d' % (nm, ca, cb))
            else:
                print('[PASS] %s 配对 %d/%d' % (nm, ca, cb))

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  中文标点规范全部成立（半角违例 0、成对符号配平）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
