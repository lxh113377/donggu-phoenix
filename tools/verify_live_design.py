# -*- coding: utf-8 -*-
import urllib.request, hashlib, json
BASE = 'https://lxh113377.github.io/donggu-phoenix/'
def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()
checks = ['index.html', 'assets/css/main.css', 'assets/js/main.js',
          'assets/fonts/zcool-display.woff2', 'assets/fonts/cinzel.woff2', 'sw.js']
for c in checks:
    try:
        st, body = get(BASE + c)
        print(c, st, len(body), hashlib.sha256(body).hexdigest()[:12])
    except Exception as e:
        print(c, 'ERR', e)
st, html = get(BASE)
h = html.decode('utf-8', 'replace')
for token in ['ZCOOL', 'nav-toggle', 'id="menu"', 'ink-divider', 'sec-idx', 'hero-meta', 'zcool-display.woff2']:
    print('html has', token, token in h)
