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

## 扫描面必须等于执行面（轮58 修）
第一版把 _qa/ 下的**未跟踪**临时脚本也算 FAIL，造成「本地红、CI 绿」——
_qa/ 在 .gitignore 里，CI 的干净克隆根本没有这些文件，拦不到也修不了。
同一判据在两个环境给出相反结论，会训练人去忽略红灯，比误报更危险。

现按 git 跟踪状态分流：
  · 已跟踪（进仓库、CI 会拦）→ FAIL
  · 未跟踪（本地一次性脚本，使命常已完成）→ WARN，提示但不判红
判据本身不改他人文件（U-127：只清理自己产生的东西）。

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

    # 豁免：反向验证脚本需要「造违规样本」（写入字符串字面量里），
    # 它们本身不会执行那段代码，只是把它写成 _qa 下的临时文件。
    EXEMPT = {'reverse_safe_script.py'}  # 造违规样本的反向验证脚本
    offenders = []   # 已跟踪：会进 CI，必须判红
    local_only = []  # 未跟踪：一次性脚本，只 WARN
    checked = 0

    # 用 git 判定跟踪状态；无 git 环境时保守视为已跟踪（宁可误报不漏报）
    tracked = set()
    try:
        import subprocess
        r = subprocess.run(['git', '-C', BASE, 'ls-files', '-z'],
                           capture_output=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError('git rc=%d' % r.returncode)
        tracked = set(x.decode('utf-8', 'replace') for x in r.stdout.split(b'\0') if x)
        have_git = True
    except Exception:
        have_git = False
    for f in files:
        if os.path.basename(f) in EXEMPT or os.path.basename(f) == 'safe_script_test.py':
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
            rel = os.path.relpath(f, BASE).replace(os.sep, '/')
            entry = (rel, call.replace(chr(10), ' ')[:80])
            if (not have_git) or (rel in tracked):
                offenders.append(entry)
            else:
                local_only.append(entry)

    print('检查 %d 个脚本（_qa/ 与 tools/）' % checked)
    if checked == 0:
        print()
        print('RESULT: SKIP  未找到任何脚本 —— 不计入 PASS')
        return 0

    if local_only:
        print()
        print('[WARN] %d 个未跟踪的本地一次性脚本原地写真实文件（不进 CI，不判红）：'
              % len(local_only))
        for name, call in local_only[:6]:
            print('  ~ %s: %s' % (name, call))
        print('  说明：_qa/ 在 .gitignore 内，CI 干净克隆无这些文件；'
              '此类脚本使命完成后建议归档或删除。')

    print()
    if offenders:
        print('RESULT: FAIL')
        for name, call in offenders[:10]:
            print('  - %s 原地写真实文件: %s' % (name, call))
        print()
        print('处置：改用 tools/safe_mutation.py 的沙箱副本。')
        return 1
    tail = ('（另有 %d 个未跟踪本地脚本，仅 WARN）' % len(local_only)) if local_only else ''
    print('RESULT: PASS  %d 个受 CI 约束的脚本均未原地修改真实站点文件%s' % (checked, tail))
    return 0


if __name__ == '__main__':
    sys.exit(main())