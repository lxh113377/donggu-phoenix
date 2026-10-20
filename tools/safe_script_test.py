# -*- coding: utf-8 -*-
"""tools/safe_script_test.py —— 测试脚本不得原地修改真实站点文件（纯静态，CI 可跑）。

## 为什么需要它
轮12 曾出现：反向测试脚本直接改真实文件，中途失败导致工作区被污染、
一个未提交的修复被静默覆盖。此后引入 tools/safe_mutation.py（沙箱副本）。

轮32 双重复核确认当前已无风险：
  · 43 个脚本使用 safe_mutation
  · 8 个用 git checkout 还原
  · 0 处脚本会写入真实 site/ 文件

但这是**靠自觉维持的**。本判据把它变成结构约束：
任何人往 _qa/ 或 tools/ 加脚本时，若直接写 site/ 下真实文件，CI 判红。

## 判据
扫 _qa/*.py 与 tools/*.py，找 open(<site 路径>, 'w'|'a'|'w+'|'a+'|'wb') 这类调用。
命中即判红（应改用 safe_mutation 或先备份再写）。

## 豁免
tools/safe_mutation.py 自身需要写副本（但写的是临时目录，路径不含 site/）。
以 _qa 开头的输出路径（如 _qa/xxx.txt）不算。
"""
import glob
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    dirs = [os.path.join(BASE, '_qa'), os.path.join(BASE, 'tools')]
    files = []
    for d in dirs:
        if os.path.isdir(d):
            files.extend(glob.glob(os.path.join(d, '*.py')))

    offenders = []
    checked = 0
    for f in files:
        if os.path.basename(f) == 'safe_script_test.py':
            continue
        try:
            s = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        checked += 1
        for m in re.finditer(r'open\((.{0,140}?)\)', s, re.S):
            call = m.group(1)
            if not re.search(r"['\"](?:w|a|wb|ab|w\+|a\+)['\"]", call):
                continue
            if 'site/' not in call and 'site\\\\' not in call:
                continue
            if '_qa' in call:
                continue
            offenders.append((os.path.relpath(f, BASE), call.replace(chr(10), ' ')[:80]))

    print('检查 %d 个脚本（_qa/ 与 tools/）' % checked)
    if checked == 0:
        print()
        print('RESULT: SKIP  未找到任何脚本 —— 不计入 PASS')
        return 0

    print()
    if offenders:
        print('RESULT: FAIL')
        for name, call in offenders[:10]:
            print('  - %s 原地写真实文件: %s' % (name, call))
        print()
        print('处置：改用 tools/safe_mutation.py 的沙箱副本。')
        return 1
    print('RESULT: PASS  %d 个脚本均未原地修改真实站点文件' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())