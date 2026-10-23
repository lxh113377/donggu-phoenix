# -*- coding: utf-8 -*-
"""tools/round_anchor_guard.py —— 轮次标注不超权威锚点（轮176 立，带自检）。

## 为什么需要它
本轮发现自己把两批工作的轮次标错：权威轮次（goal_round 头部、
get_goal 的 roundsStarted）是 175 / 176，我却按自己的计数写成 177 / 178，
台账轮次列从 174 直接跳到 177 —— 175、176 整段空号。
这类"账目错"不影响产品，却让交接读到错误时间线，而此前没有任何机器在看：
全靠自觉，而自觉恰恰是不可靠的那个。

## 判据
A 锚点文件可读且为正整数。
B **台账轮次列不得超过锚点** —— 本次错误的准确形状（锚点 176，账本出现 177）。
C **近 4 轮内**的行：正文开头的自标签 "轮NNN" 必须等于该行轮次列。
  （只对近期行判定：历史行普遍含「轮112 补记」「见轮41」这类合法回指，
   全量判定会大面积误报 —— 我第一版就这么误报过，据此收窄。）
D 锚点不得比台账最大值落后超过 2（防锚点长期不更新导致 B 变成永真）。

## 为什么 B 不会误伤正常补记
正常情况是"本轮做完 -> 写本轮台账"，列值等于锚点；补记上一轮则更小。
只有"把未来轮次写进账本"才会 > 锚点 —— 那必然是标注错。
"""
import io
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
LEDGER = os.environ.get('RAG_LEDGER', 'memory/09-upgrade-ledger.md')
ANCHOR = os.environ.get('RAG_ANCHOR', 'memory/round_anchor.json')


def load_anchor(path):
    return int(json.load(io.open(path, encoding='utf-8')).get('round'))


rows = []
fails = []

if not os.path.exists(ANCHOR):
    print('RESULT: FAIL  缺锚点文件 %s（每轮应从 goal_round 头部写入）'
          % ANCHOR)
    sys.exit(1)
try:
    anchor = load_anchor(ANCHOR)
except Exception as e:
    print('RESULT: FAIL  锚点不可读: %s' % str(e)[:80])
    sys.exit(1)
print('A 锚点轮次 = %d' % anchor)
if anchor <= 0:
    fails.append('锚点非正整数: %r' % anchor)

if not os.path.exists(LEDGER):
    print('RESULT: FAIL  缺台账 %s' % LEDGER)
    sys.exit(1)
text = io.open(LEDGER, encoding='utf-8', errors='ignore').read()
for m in re.finditer(r'^\| U-(\d+) \| (\d+) \| (.*?) \|', text, flags=re.M):
    rows.append((int(m.group(1)), int(m.group(2)), m.group(3)))
if not rows:
    print('RESULT: SKIP  未解析到任何台账行（未取证 != 通过）')
    sys.exit(0)
mx = max(r[1] for r in rows)
print('   台账 %d 行，轮次列最大 %d' % (len(rows), mx))

# B 不得超前
over = [(u, rd) for u, rd, _ in rows if rd > anchor]
print('B 无轮次超过锚点: %s' % ('ok' if not over else '** %d 行超前 **' % len(over)))
if over:
    fails.append('轮次标注漂移：%s 的轮次 %s 超过权威锚点 %d'
                 % ('、'.join('U-%d' % u for u, _ in over[:6]),
                    '、'.join(str(rd) for _, rd in over[:6]), anchor))

# C 近 4 轮内自标签一致
recent = [r for r in rows if r[1] > anchor - 4]
mism = []
for u, rd, body in recent:
    m = re.match(r'\s*(?:第?轮|round\s*)(\d{2,3})', body)
    if m and int(m.group(1)) != rd:
        mism.append((u, rd, int(m.group(1))))
print('C 近 4 轮 %d 行，开头自标签与列一致: %s'
      % (len(recent), 'ok' if not mism else '** %d 行不一致 **' % len(mism)))
if mism:
    fails.append('自标签与轮次列不一致：'
                 + '；'.join('U-%d 列%d 正文轮%d' % t for t in mism[:5]))

# D 锚点不要太旧
gap = anchor - mx
print('D 锚点落后台账最大值 %d 轮: %s'
      % (gap, 'ok' if gap <= 2 else '** 锚点疑似长期未更新 **'))
if gap > 2:
    fails.append('锚点 %d 比台账最大 %d 落后 %d 轮，'
                 'B 项会退化成永真 —— 请更新 round_anchor.json'
                 % (anchor, mx, gap))

# 自检（可用 env 关掉，供 CI 只跑真判）
if not os.environ.get('RAG_SKIP_SELFTEST'):
    import tempfile
    tmp = tempfile.mkdtemp(prefix='rag_')
    src = io.open(LEDGER, encoding='utf-8', errors='ignore').read()
    bad = re.sub(r'^(\| U-\d+ \| )%d( \|)' % mx,
                 r'\g<1>%d\g<2>' % (anchor + 3), src, count=1,
                 flags=re.M)
    assert bad != src, '自检注入失败（找不到可改的轮次列）'
    lp = os.path.join(tmp, 'ledger.md')
    ap = os.path.join(tmp, 'anchor.json')
    io.open(lp, 'w', encoding='utf-8').write(bad)
    json.dump({'round': anchor}, io.open(ap, 'w', encoding='utf-8'))
    env = dict(os.environ)
    env.update({'RAG_LEDGER': lp, 'RAG_ANCHOR': ap,
                'RAG_SKIP_SELFTEST': '1'})
    p = subprocess.run([sys.executable, os.path.abspath(__file__)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=120, env=env, cwd=BASE)
    out = (p.stdout or '') + (p.stderr or '')
    caught = p.returncode != 0 and '超过权威锚点' in out
    print('   自检：把轮次列改成 %d（锚点 %d + 3）应报红 -> %s rc=%s'
          % (anchor + 3, anchor, '抓到' if caught else '** 没抓到 **',
             p.returncode))
    if not caught:
        fails.append('自检不通过：轮次超锚点未被抓到，守卫已哑')
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print('RESULT: FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('RESULT: PASS  轮次标注与权威锚点一致，且自检证明「标成未来轮次」会被抓到')
sys.exit(0)
