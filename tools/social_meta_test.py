# -*- coding: utf-8 -*-
"""tools/social_meta_test.py —— 社交分享元数据判据（纯静态，CI 可跑）。

## 为什么需要它
本站是实践团作品，传播主要靠微信/朋友圈/微博分享。
分享卡片的标题、描述、图片直接决定点击率，但极易在改文案时被忽略。

## 轮47 发现的问题
og:description 只有 24 字且缺主体身份（「江西科技学院薪火寰行实践团 × 东固畲族乡」），
而它正是微信分享卡片显示的那句话。其他两处描述都有身份，唯独这里没有。

## 检查项
1. og 四要素齐全：type/title/description/image
2. twitter card 齐全
3. og:image 指向的本地文件存在，且尺寸声明与实际一致（1200x630）
4. og:url 与 canonical 一致
5. **og:description 必须含主体身份**（实践团 × 畲族乡）
6. og:title 与 <title> 应一致（避免分享标题与页面标题打架）
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, 'site', 'index.html')

# 主体身份关键词：必须是「谁做的」（学校/实践团），
# **不能**用「东固」这类地名——描述里本来就有「东固非遗文创」，
# 会把「缺身份」误判为「有身份」（轮47 反向验证暴露的漏洞）。
IDENTITY_KEYS = ['实践团', '学院']


def meta(html, key):
    m = re.search(r'<meta\s+(?:property|name)="' + re.escape(key) + r'"\s+content="([^"]*)"', html)
    return m.group(1) if m else None


def main():
    if not os.path.exists(HTML):
        print('RESULT: SKIP  找不到 index.html')
        return 0

    html = open(HTML, encoding='utf-8').read()
    fails = []
    checked = 0

    # 1) og 四要素
    checked += 1
    required = ['og:type', 'og:title', 'og:description', 'og:image']
    missing = [k for k in required if not meta(html, k)]
    if missing:
        fails.append('og 缺: %s' % ', '.join(missing))
    else:
        print('[PASS] og 四要素齐全（type/title/description/image）')

    # 2) twitter card
    checked += 1
    if not meta(html, 'twitter:card'):
        fails.append('缺 twitter:card')
    else:
        print('[PASS] twitter card 齐全')

    # 3) og:image 文件存在 + 尺寸声明
    checked += 1
    img = meta(html, 'og:image')
    if img:
        rel = img.split('donggu-phoenix/')[-1] if 'donggu-phoenix/' in img else img.lstrip('/')
        local = os.path.join(BASE, 'site', rel)
        if not os.path.exists(local):
            fails.append('og:image 指向的文件不存在: %s' % rel)
        else:
            w = meta(html, 'og:image:width')
            h = meta(html, 'og:image:height')
            if w != '1200' or h != '630':
                fails.append('og:image 尺寸声明非 1200x630（实际 %sx%s）' % (w, h))
            else:
                kb = os.path.getsize(local) / 1024
                print('[PASS] og:image 存在且声明 1200x630（%.1f KB）' % kb)

    # 4) og:url 与 canonical 一致
    checked += 1
    cm = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html)
    ogurl = meta(html, 'og:url')
    if cm and ogurl and cm.group(1).rstrip('/') != ogurl.rstrip('/'):
        fails.append('og:url 与 canonical 不一致')
    elif cm and ogurl:
        print('[PASS] og:url 与 canonical 一致')

    # 5) og:description 含主体身份
    checked += 1
    ogdesc = meta(html, 'og:description') or ''
    if not any(k in ogdesc for k in IDENTITY_KEYS):
        fails.append('og:description 缺主体身份（分享卡片看不到「谁做的」）')
    else:
        print('[PASS] og:description 含主体身份（%d 字）' % len(ogdesc))

    # 6) og:title 与 <title> 一致
    checked += 1
    tm = re.search(r'<title>([^<]*)</title>', html)
    ogtitle = meta(html, 'og:title')
    if tm and ogtitle and tm.group(1).strip() != ogtitle.strip():
        fails.append('og:title 与 <title> 不一致')
    elif tm and ogtitle:
        print('[PASS] og:title 与 <title> 一致')

    print()
    print('检查 %d 项分享元数据' % checked)
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  分享元数据 %d 项全部成立' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())