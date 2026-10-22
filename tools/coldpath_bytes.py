# -*- coding: utf-8 -*-
"""真实首屏关键路径：直接 HTTP 取，不看浏览器缓存。
首屏 = HTML + CSS + 首屏字体 + 首屏脚本 + 首屏图片（凤凰/图腾/logo）。
"""
import urllib.request, re, gzip, io, sys

BASE = 'http://127.0.0.1:8791/'
def get(path):
    req = urllib.request.Request(BASE + path.lstrip('/'), headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'gzip, br'})
    with urllib.request.urlopen(req, timeout=20) as r:
        b = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            b = gzip.decompress(b)
        return b

html = get('index.html').decode('utf-8', 'replace')

# 找出 <head> 里的阻塞资源 + 首屏可见的图
css = re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)
pre = re.findall(r'<link[^>]+rel="preload"[^>]+href="([^"]+)"', html)
scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)

seen = []
def add(lst, kind):
    for p in lst:
        if p.startswith('http'): continue
        seen.append((kind, p))

add(css, 'css'); add(pre, 'preload'); add(scripts, 'js'); add(imgs[:6], 'img')

total = len(get('index.html'))
print('index.html: %d KB' % (total // 1024))
by_kind = {}
for kind, p in seen:
    try:
        n = len(get(p.lstrip('./')))
    except Exception as e:
        print('  MISS', kind, p, e); continue
    by_kind[kind] = by_kind.get(kind, 0) + n
    print('  %-8s %7d B  %s' % (kind, n, p))
    total += n

print()
print('首屏合计: %d KB' % (total // 1024))
print('分项:', {k: str(v // 1024) + 'KB' for k, v in by_kind.items()})
