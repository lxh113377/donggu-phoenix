# -*- coding: utf-8 -*-
"""反向验证 engine_behavior_test 的判定逻辑（构造数据法，轮54）。

## 为什么不用「改文件再跑端到端」
试过并诊断清楚了：把 phoenix.js 的 _densFor 改成常量后，
注入确实到了页面（fileHasMark=true、函数源码含 return 2000、调用返回 2000），
但判据仍 PASS —— 实例上的密度状态是构造时算好的，
且浏览器缓存时序会污染这条链路（U-130 同一课）。

结论：**端到端反向验证依赖「改文件+浏览器读到新代码」时不可信**。
正确做法是把判定逻辑抽成纯函数，用构造数据直接证明它能识别坏输入。

## 本文件自己也被抓出过一次错（轮54）
第一版把「极大面积只给 2514（DENS_MAX=2600）」标成期望判红，
实际 2514 是 2600 的 96.7%，在 ±10% 容差内，判据 PASS 是对的 ——
是我造的用例期望值错。教训：反向验证的期望值要按判据口径算过再写。

## judge_hud 返回 (fails, unmeasurable)
帧率低于 MIN_MEASURABLE_FPS 时比率判据失效，
判据必须明确报「不可测」而不是蒙混通过（轮54 构造用例抓到的真实漏洞）。
"""
import sys

sys.path.insert(0, 'tools')
from engine_behavior_test import judge_density, judge_hud, MIN_MEASURABLE_FPS

DENS_CASES = [
    ([1319, 1672, 2514, 2600, 2600, 2600], 2600, '健康曲线（实测基线）', False),
    ([2000, 2000, 2000, 2000, 2000, 2000], 2600, '恒定 2000（自适应被改回固定档）', True),
    ([2600, 2514, 1672, 1319, 900, 520], 2600, '面积越大粒子越少（映射写反）', True),
    ([1319, 1672, 2514, 4200, 9000, 15000], 2600, '突破上限（夹取被删）', True),
    ([1319, 1500, 1800, 2000, 2000, 2000], 2600, '极大面积只给 2000（2000/2600=77%% < 90%%，标定被改坏）', True),
    ([1319, 1672, 2514, 2514, 2514, 2514], 2600, '2514 是 2600 的 96.7%%（容差内，不该判红）', False),
    ([100, 90, 80], None, '无 DENS_MAX 且非单调', True),
    ([1319], 2600, '样本不足', True),
]

HUD_CASES = [
    (257.0, 10.0, False, '健康节流（实测基线）'),
    (208.0, 208.0, True, '节流周期被改成 1ms（每帧都写）'),
    (260.0, 250.0, True, 'calls 未显著高于 writes（节流没在挡）'),
    (200.0, 0.0, True, 'writes 恒为 0（计数器被摘）'),
    (15.0, 20.0, True, '写入超过调用（逻辑不可能）'),
    (9.0, 4.0, True, '低帧率 9/s：绝对值达标但不可测，必须判红而非蒙混'),
    (28.0, 10.0, True, '帧率 %d 以下：比率够但仍不可测' % MIN_MEASURABLE_FPS),
    (45.0, 10.0, False, '帧率 45/s 且比率 4.5 倍：真通过'),
]


def main():
    bad = 0
    print('=== judge_density（曲线, DENS_MAX）===')
    print('%-52s %-6s %-6s %s' % ('用例', '期望', '实得', '判定'))
    print('-' * 76)
    for curve, dmax, desc, should_fail in DENS_CASES:
        fails = judge_density(curve, dmax)
        got = bool(fails)
        ok = (got == should_fail)
        bad += 0 if ok else 1
        print('%-52s %-6s %-6s %s' % (desc, '判红' if should_fail else '通过',
                                        '判红' if got else '通过', 'OK' if ok else '**错**'))
        if not ok and fails:
            print('     实际:', fails[0][:66])

    print()
    print('=== judge_hud（calls/s, writes/s）===')
    print('%-52s %-6s %-6s %s' % ('用例', '期望', '实得', '判定'))
    print('-' * 76)
    for cps, wps, should_fail, desc in HUD_CASES:
        fails, unmeas = judge_hud(cps, wps)
        got = bool(fails)
        ok = (got == should_fail)
        bad += 0 if ok else 1
        print('%-52s %-6s %-6s %s%s' % (desc, '判红' if should_fail else '通过',
                                         '判红' if got else '通过', 'OK' if ok else '**错**',
                                         '  [不可测]' if unmeas else ''))
        if not ok and fails:
            print('     实际:', fails[0][:66])

    total = len(DENS_CASES) + len(HUD_CASES)
    print()
    print('%d 个构造用例中判据行为错误: %d' % (total, bad))
    print()
    if bad:
        print('RESULT: FAIL  判定逻辑与预期不符')
        return 1
    print('RESULT: PASS  判定逻辑能识别全部坏输入（含低帧率不可测场景）')
    return 0


if __name__ == '__main__':
    sys.exit(main())