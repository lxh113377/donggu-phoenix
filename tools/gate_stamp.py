# -*- coding: utf-8 -*-
"""tools/gate_stamp.py —— 浏览器判据的统一时效戳（轮71）。

## 为什么需要
轮70 加的时效戳只在 **经 run_browser_suite 运行** 时才写。
但实际用法是直接跑单个判据（python tools/multi_viewport_test.py），
于是轮71 出现自相矛盾的读数：multi_viewport 当天真跑 5 次全 PASS，
--status 却显示「从未跑过」。

一个会给出**误导性读数**的时效机制，比没有时效机制更糟。

## 用法
判据在 __main__ 里调一次 record()，把最终结论写进 _qa/gate_runs.json。
SKIP 不记 —— 没验证过就不能算「跑过」。
"""
import json
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAMP = os.path.join(BASE, '_qa', 'gate_runs.json')


def record(script_path, status, dur=None):
    """记录本次真实执行。只记 PASS/FAIL（SKIP 不算验证过）。"""
    if status not in ('PASS', 'FAIL'):
        return
    rel = 'tools/' + os.path.basename(script_path)
    d = {}
    try:
        d = json.load(open(STAMP, encoding='utf-8'))
    except Exception:
        d = {}
    d[rel] = {'ts': int(time.time()), 'status': status,
              'dur': round(dur, 1) if dur is not None else 0}
    try:
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        json.dump(d, open(STAMP, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    except Exception:
        pass
