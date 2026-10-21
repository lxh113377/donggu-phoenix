# -*- coding: utf-8 -*-
r"""tools/secret_leak_test.py —— 部署面密钥泄漏门禁（纯静态，CI 可跑）。

## 为什么需要（轮73 我自己制造的真实风险）
给后台做视觉质检时，需要让 headless 探针带着 ADMIN_KEY 登录。
探针页必须与 /admin/ 同源，于是我把探针写进了 site/_admin_probe.html
—— 结果那个文件里带着**明文密钥**躺在部署目录里。

侥幸没出事的原因有两个，但都不是我的设计：
  · 探针文件恰好没被 git add（我提交时列了显式路径）
  · Pages 从 git 部署，未跟踪文件不会上线
只要我当时习惯性敲一句 git add site/，密钥就永久进公开仓库了。

**靠运气不算防护。** 本门禁把「部署面不得含密钥」变成机器检查。

## 判据
扫 site/ 全部文本文件，命中以下任一即 FAIL：
  1. 出现 .dev.vars 里的任何键的**值**（真密钥，最强信号）
     —— 只在能读到 .dev.vars 时检查（CI 干净克隆没有它，跳过该条）
  2. 出现疑似硬编码密钥的字面量模式：
     形如 KEY/SECRET/TOKEN/PASSWORD = '<至少 16 位非空白>' 的赋值
  3. 部署目录里出现 .dev.vars / *.pem / id_rsa 这类密钥文件本体

## 自检（证明尺子有牙，任一不符即 FAIL）
  · 明文密钥样本 -> 必须报
  · 长字面量赋值 KEY = 'xxxx...' -> 必须报
  · 正常业务文案（含 "key" 字样但非密钥）-> 必须放过
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')

TEXT_EXT = ('.html', '.css', '.js', '.json', '.svg', '.txt', '.webmanifest',
            '.md', '.xml', '.map')
SECRET_FILE_NAMES = ('.dev.vars', 'id_rsa', 'id_ed25519', '.pem', '.key')

# 疑似硬编码密钥：KEY/SECRET/TOKEN/PASSWORD 等 = '至少 16 位无空白'
HARD = re.compile(
    r'\b([A-Za-z_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL)[A-Za-z_]*)'
    r'\s*[:=]\s*'
    r'(["\'][^"\']{16,})["\']', re.I)

# 白名单：这些值虽长但不是密钥
ALLOW_VALUES = ('http://', 'https://', 'data:', 'assets/', 'application/')


def load_dev_key_values():
    """读 .dev.vars 的键值（本地有、CI 无）。只取长度 >= 8 的值。"""
    p = os.path.join(BASE, '.dev.vars')
    out = {}
    if not os.path.exists(p):
        return out
    try:
        for line in open(p, encoding='utf-8', errors='ignore'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            v = v.strip().strip('"').strip("'")
            if len(v) >= 8:
                out[k.strip()] = v
    except Exception:
        pass
    return out


def scan_text(css_text):
    """返回 (命中密钥值列表, 疑似硬编码列表)。"""
    vals, hard = [], []
    kv = load_dev_key_values()
    for k, v in kv.items():
        if v and v in css_text:
            vals.append(k)
    for m in HARD.finditer(css_text):
        name, lit = m.group(1), m.group(2)
        if any(a in lit for a in ALLOW_VALUES):
            continue
        hard.append('%s = %s...' % (name, lit[:10]))
    return vals, hard


SELFTEST = [
    ("var KEY = '8f20a1b2c3d4e5f60718293a4b5c6d7e';", True,
     '明文密钥赋值 -> 应报'),
    ('const ADMIN_TOKEN = "abcdefghijklmnopqrst";', True,
     '长 TOKEN 字面量 -> 应报'),
    ('var apiKey = get("x");', False, '短/非字面量 -> 应放过'),
    ('<meta name="keywords" content="畲族,凤凰,东固">', False,
     '业务文案含 key 字样 -> 应放过'),
    ('var url = "https://example.com/a.png";', False,
     'URL 字面量 -> 应放过（白名单）'),
]


def selftest():
    bad = []
    for text, should_flag, desc in SELFTEST:
        _v, hard = scan_text(text)
        flagged = bool(hard)
        if flagged != should_flag:
            bad.append('%s（期望%s 实得%s）' % (
                desc, '报' if should_flag else '放过', '报' if flagged else '放过'))
    return bad


def main():
    if not os.path.isdir(SITE):
        print('RESULT: SKIP  找不到 site/')
        return 0

    bad = selftest()
    if bad:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad:
            print('  -', b)
        return 1
    print('[PASS] 自检 %d 个用例符合预期' % len(SELFTEST))

    kv = load_dev_key_values()
    print('本机 .dev.vars 可读键数：%d%s' % (
        len(kv), '' if kv else '（CI 干净克隆无此文件，跳过真密钥比对）'))

    problems = []
    n = 0
    for root, dirs, files in os.walk(SITE):
        dirs[:] = [d for d in dirs if d not in ('.git',)]
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, BASE).replace('\\', '/')
            # 3) 密钥文件本体不得出现在部署目录
            for pat in SECRET_FILE_NAMES:
                if fn == pat or fn.endswith(pat):
                    problems.append('%s：部署目录含密钥文件本体' % rel)
            if not fn.endswith(TEXT_EXT):
                continue
            try:
                s = open(full, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            n += 1
            vals, hard = scan_text(s)
            for k in vals:
                problems.append('%s：含 .dev.vars 中 %s 的明文值' % (rel, k))
            for hh in hard:
                problems.append('%s：疑似硬编码密钥 %s' % (rel, hh))

    print('扫描 %d 个文本文件' % n)
    if n == 0:
        print('RESULT: SKIP  未扫到文件（解析失效）')
        return 0
    print()
    if problems:
        print('RESULT: FAIL  部署面密钥泄漏 %d 处' % len(problems))
        for p in problems[:10]:
            print('  -', p)
        return 1
    print('RESULT: PASS  部署面（site/）无任何密钥泄漏')
    return 0


if __name__ == '__main__':
    sys.exit(main())
