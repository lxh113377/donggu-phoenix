# -*- coding: utf-8 -*-
"""tools/gate_guard.py —— 门禁零样本守卫（防「没测到 = 通过」）。

## 这是第三次同类错误，所以做成机制而不是提醒

| 轮次 | 工具 | 症状 |
|---|---|---|
| 9  | perf_anim           | 探针抛错 → 解析失败 → 返回 None → 当「环境跳过」→ PASS |
| 15 | reveal_after_jump   | 8 个锚点全 SKIP → fails 为空 → PASS |
| 22 | dead_data_test      | 正则写错 → 匹配 0 个字段 → PASS |

三次的共同结构：
    results = collect()        # 可能返回空
    for r in results:          # 空集合 → 循环不执行
        if bad(r): fails.append(...)
    if fails: FAIL else: PASS  # fails 为空 → PASS

**「检查了 0 个对象」和「检查了 N 个对象且都正常」被当成同一件事。**

## 本模块提供什么

    verdict(checked, fails, allow_zero=False, what='对象')
      → ('PASS' | 'FAIL' | 'SKIP', 消息)

规则（顺序很重要）：
  1. checked == 0 且 allow_zero=False  →  **SKIP**（不是 PASS！）
     · SKIP 退出码为 0（不阻塞 CI，因为可能是环境问题）
     · 但**绝不打印 PASS**，且消息里明说「未测到」
  2. checked == 0 且 allow_zero=True   →  PASS（显式声明「空是合法的」）
  3. fails 非空                        →  FAIL
  4. 其他                              →  PASS

## 为什么 SKIP 不用 FAIL
环境问题（浏览器没起来、文件缺失）和「被测对象有问题」是两件事。
混为一谈会让 CI 因环境抖动红，久而久之人们就学会忽略红灯。
但 SKIP **必须可见**：打印醒目提示，且不计入 PASS 统计。

## 用法

    from gate_guard import verdict
    code, msg = verdict(checked=len(items), fails=fails, what='章节')
    print('[%s] %s' % (code, msg))
    return code  # 0 / 1
"""
import sys

PASS = 'PASS'
FAIL = 'FAIL'
SKIP = 'SKIP'


def verdict(checked, fails, allow_zero=False, what='对象'):
    """返回 (code, message)。code ∈ {'PASS','FAIL','SKIP'}。"""
    fails = fails or []

    if checked == 0:
        if allow_zero:
            return PASS, 'PASS  0 个%s（已显式声明空集合合法）' % what
        return SKIP, ('SKIP  未检查到任何%s —— 不计入 PASS（防止「没测到」被当「通过」）'
                      % what)

    if fails:
        return FAIL, ('FAIL  %d 个%s中有 %d 处问题' % (checked, what, len(fails)))

    return PASS, 'PASS  %d 个%s全部通过' % (checked, what)


def emit(code, message):
    """按约定格式打印，并返回退出码。"""
    print()
    print('RESULT: ' + message)
    return 0 if code in (PASS, SKIP) else 1


def selftest():
    """自检：四种情形必须给出正确判定。"""
    ok = True
    cases = [
        # (checked, fails, allow_zero, 期望 code, 说明)
        (0,  [],        False, SKIP, '零样本 → SKIP（核心用例）'),
        (0,  [],        True,  PASS, '零样本但显式允许 → PASS'),
        (5,  [],        False, PASS, '有样本且无问题 → PASS'),
        (5,  ['x'],     False, FAIL, '有样本且有问题 → FAIL'),
        (0,  ['x'],     False, SKIP, '零样本优先（即便 fails 有值也不该 PASS）'),
    ]
    for checked, fails, allow_zero, want, desc in cases:
        got, msg = verdict(checked, fails, allow_zero, '测试项')
        mark = 'OK ' if got == want else 'FAIL'
        if got != want:
            ok = False
        print('[%s] %-32s 期望 %-4s 实得 %-4s  %s' % (mark, desc, want, got, msg[:40]))
    print()
    print('RESULT: PASS  零样本守卫自检通过' if ok else 'RESULT: FAIL  自检未通过')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selftest())
