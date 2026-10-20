# -*- coding: utf-8 -*-
"""原创性/反模板自检：扫常见「通用 AI 页」特征。"""
import os, re
BASE = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
os.chdir(BASE)
import sys as _sys; _sys.path.insert(0, 'tools')
from source_scan import stripped as _strip_css, strip_html_comments as _strip_html
css = _strip_css(open('site/assets/css/main.css', encoding='utf-8').read())
html = _strip_html(open('site/index.html', encoding='utf-8').read())
js = ''.join(open(os.path.join('site/assets/js', f), encoding='utf-8').read()
             for f in os.listdir('site/assets/js') if f.endswith('.js'))

checks = {
  '无外部 UI 框架/Tailwind/Bootstrap': not any(k in html + css for k in
      ('tailwind','bootstrap','bulma','materialize','@apply','class="container"','cdn.jsdelivr','unpkg.com')),
  '无 Google Fonts 外链': 'fonts.googleapis' not in html and 'fonts.gstatic' not in html,
  '无 Inter/Roboto/Space Grotesk 作为首选字体': not any(
      f in css.split('--font-')[1][:2000] for f in ('"Inter"','"Roboto"','"Space Grotesk"')),
  '无紫色渐变 AI 默认色 (#667eea/#764ba2)': not any(c in css.lower() for c in ('#667eea','#764ba2','#8b5cf6','#a855f7')),
  '无 glassmorphism 泛滥（backdrop-filter 用量克制）': css.count('backdrop-filter') <= 8,
  '无三张等宽卡片并排（feature-grid 三连）': css.count('repeat(3,1fr)') <= 1,
  '图表/图标非 emoji 堆砌': len(re.findall(r'[\U0001F300-\U0001FAFF]', html + js)) == 0,
  '自绘 SVG/Canvas 而非位图堆砌': ('<svg' in html or '.svg' in html) and 'getContext' in js,
}
for k, v in checks.items():
    print(('[OK]   ' if v else '[WARN] ') + k)

# 统计
print()
print('backdrop-filter 次数:', css.count('backdrop-filter'))
print('repeat(3,1fr) 次数:', css.count('repeat(3,1fr)'))
print('emoji 数:', len(re.findall(r'[\U0001F300-\U0001FAFF]', html + js)))
print('外部 URL 请求（应仅 og/canonical 元数据）:',
      len([m for m in re.findall(r'(?:src|href)="(https?://[^"]+)"', html)]))
