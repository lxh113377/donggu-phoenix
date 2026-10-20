
# -*- coding: utf-8 -*-
"""反向验证 bilingual_parity_test（沙箱，真实文件零改动）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

DATA = 'site/assets/data/ar-data.js'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(DATA)

cases = [
    ('A 英文被砍短（信息缺失）',
     ("enBody: 'In the first counter-encirclement campaign, Zhang Huizan’s 18th Division was lured into the “cloth bag” at Longgang and wiped out. Mao Zedong wrote in his poem “Pride of Fisherman”: ‘Mist veils Longgang, a thousand peaks in gloom; all cry out — Zhang Huizan is taken at the front.’'",
      "enBody: 'Zhang Huizan’s division was wiped out.'")),
    ('B 引入 Markdown 标记',
     ("enBody: 'It starts with the wood — camphor, thoroughly seasoned, free of cracks and large knots, stood upright along the grain.'",
      "enBody: 'It starts with the wood — *camphor*, seasoned, stood upright along the grain.'")),
    ('C 丢失年份',
     ("enBody: 'On 15 September 1931, Huang Gonglue, commander of the Third Red Army, was killed by strafing aircraft at Liudu’ao. He was 33. His last words: ‘Bury me in Donggu — I love its people, I love its mountains and its waters.’'",
      "enBody: 'Huang Gonglue was killed by aircraft at Liudu’ao. He was 33. His last words: bury me in Donggu, I love its people, I love its mountains and its waters.'")),
]

for label, (old, new) in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(DATA, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:70]))
            continue
        r = sb.run_python('tools/bilingual_parity_test.py', timeout=60)
        out = ((r.stdout or '') + (r.stderr or ''))
        fails = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fails[:2]:
            print('    ', f)

print()
print('真实文件未变:', before == sha(DATA))
