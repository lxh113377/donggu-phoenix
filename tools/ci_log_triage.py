# -*- coding: utf-8 -*-
r"""tools/ci_log_triage.py —— 把 CI 日志里的 FAIL 分成「真失败」与「期望输出」。

## 为什么需要（轮135，同一个坑踩到第 4 次）
本仓有 11 条反向验证脚本（reverse_*.py），它们**故意注入故障**、
打印形如「[A 退回硬编码] rc=1 RESULT: FAIL」的**期望输出**，
再以 RESULT: PASS 收尾证明判据有牙。
于是 CI 日志里 PASS 82 / FAIL 21 / SKIP 1 这种读数**看着像挂了 21 项**，
而真相是 0 项真失败。

我先后用四种临时办法分类，每次都错：
  ① 按行序把 RESULT 归给最近的 python 命令 —— 错。GitHub 会把整个
     run: | 块先一次性 echo 再执行，命令与输出不相邻（U-414）。
  ② 用 startswith 匹配 —— 错。被 ANSI 颜色码挡住。
  ③ 看行首是否有方括号标签 —— 不可靠。reverse_memory_size 的
     「收紧后再变大 -> rc=1 RESULT: FAIL」就没有方括号，漏成假阳性。
  ④ 直接信 job conclusion —— 对，但拿不到「哪几条真失败」的定位信息。

## 本工具的规则（只用步骤内的真实输出顺序，不做跨行归因）
一条反向验证脚本的设计前提是：**它自己必须以 RESULT: PASS 收尾**
（内部 FAIL 是它证明判据有牙的证据）。因此：

  在同一个步骤（step）内，取 RESULT 序列；
  **只有「该步骤最后一条 RESULT」是 FAIL 时才算真失败**，
  其余 FAIL 一律归为该步骤内部的期望输出。

这条规则不依赖标签格式、不依赖命令与输出的位置关系，
并且天然覆盖 ①②③ 三种错法。

## 尺子有效性自检（U-149/U-151）
  S1 合成一段「中间 FAIL + 末尾 PASS」的步骤 -> 真失败必须为 0
  S2 合成一段「末尾 FAIL」的步骤            -> 必须报出 1 条真失败
  S3 合成一段「只有 PASS」的步骤            -> 必须为 0
任一失效即判 FAIL —— 否则本工具是恒绿的安慰剂。

## 诚实语义
gh 不可用 / 取不到日志 -> SKIP 并说明（未测不等于通过）。
"""
import json
import os
import re
import subprocess
import sys

OWNER = 'lxh113377/donggu-phoenix'
ANSI = re.compile(r'\x1b\[[0-9;]*m')
TS = re.compile(r'^[^\n]*?\d{2}:\d{2}:\d{2}\.\d+Z\s*')
RESULT = re.compile(r'RESULT:\s*(PASS|FAIL|SKIP)\b(.*)')


def gh(args, timeout=280):
    e = dict(os.environ)
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
        e[k] = ''
    e['NO_PROXY'] = '*'
    try:
        r = subprocess.run(['gh'] + args, capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           timeout=timeout, env=e)
        return r.stdout or '', r.returncode
    except Exception as e2:
        return '', 1


def normalize(raw_lines):
    """去 ANSI、去时间戳，返回 (step, text) 列表。"""
    out = []
    for l in raw_lines:
        t = ANSI.sub('', l)
        # GitHub 日志行形如：  Job  Step  2026-..Z  内容
        parts = t.split('\t')
        step = parts[1].strip() if len(parts) >= 2 else ''
        t = TS.sub('', '\t'.join(parts[2:]) if len(parts) >= 3 else t)
        t = t.strip()
        if t:
            out.append((step, t))
    return out


def triage(norm):
    """按步骤分组，返回 (真失败列表, 期望FAIL数, 步骤统计)。"""
    by_step = {}
    order = []
    for step, t in norm:
        m = RESULT.search(t)
        if not m:
            continue
        if step not in by_step:
            by_step[step] = []
            order.append(step)
        by_step[step].append((m.group(1), t))
    real = []
    expected = 0
    stats = []
    for step in order:
        seq = by_step[step]
        last_kind, last_txt = seq[-1]
        fails = [(k, t) for k, t in seq if k == 'FAIL']
        skips = [(k, t) for k, t in seq if k == 'SKIP']
        # 只有末尾 FAIL 才是真失败
        real_here = [t for k, t in fails if (k, t) == (last_kind, last_txt)]
        real += ['[%s] %s' % (step, t) for t in real_here]
        expected += len(fails) - len(real_here)
        stats.append((step, len(seq), len(fails), len(real_here), len(skips)))
    return real, expected, stats


def result_kinds(norm):
    """日志行里的 RESULT 结论种类列表。

    提成独立函数是为了让它可被自检覆盖：main() 靠「空列表」判定
    取数或解码失效，这条防护若没有对应自检项，将来被改回去也不会被发现
    （U-427：防护本身也要有牙）。
    """
    return [m.group(1) for _, t in norm for m in [RESULT.search(t)] if m]


def selftest():
    bad = []
    # S1 中间 FAIL + 末尾 PASS
    n1 = normalize(['a\tVerify\t2026-01-01T00:00:00.0Z\tRESULT: PASS x',
                    'a\tVerify\t2026-01-01T00:00:01.0Z\t[A 注入] rc=1 RESULT: FAIL 故意',
                    'a\tVerify\t2026-01-01T00:00:02.0Z\t[B 注入] rc=1 RESULT: FAIL 故意',
                    'a\tVerify\t2026-01-01T00:00:03.0Z\tRESULT: PASS 反向验证通过'])
    r1, e1, _ = triage(n1)
    ok1 = (not r1) and e1 == 2
    print('  [%s] S1 中间 2 条 FAIL + 末尾 PASS -> 真失败 %d、期望 %d（应 0/2）'
          % ('ok' if ok1 else 'X', len(r1), e1))
    if not ok1:
        bad.append('S1 分类错')
    # S2 末尾 FAIL
    n2 = normalize(['a\tVerify\t2026-01-01T00:00:01.0Z\tRESULT: PASS ok',
                    'a\tVerify\t2026-01-01T00:00:02.0Z\tRESULT: FAIL 真挂了'])
    r2, e2, _ = triage(n2)
    ok2 = len(r2) == 1
    print('  [%s] S2 末尾 FAIL -> 真失败 %d（应 1）%s'
          % ('ok' if ok2 else 'X', len(r2), ('' if ok2 else '，漏了！')))
    if not ok2:
        bad.append('S2 漏报真失败')
    # S3 全 PASS
    n3 = normalize(['a\tVerify\t2026-01-01T00:00:01.0Z\tRESULT: PASS x',
                    'a\tVerify\t2026-01-01T00:00:02.0Z\tRESULT: PASS y'])
    r3, e3, _ = triage(n3)
    ok3 = (not r3) and e3 == 0
    print('  [%s] S3 全 PASS -> 真失败 %d、期望 %d（应 0/0）'
          % ('ok' if ok3 else 'X', len(r3), e3))
    if not ok3:
        bad.append('S3 误报')
    # S4 空读数必须返回空 kinds —— main() 据此判失效。
    # 这条保护的是新增的「非空日志但零 RESULT 不得当通过」防护本身：
    # 它若被改回去（比如哪天有人觉得日志为空没必要报错），S4 会立刻红。
    n4 = normalize(['a\tVerify\t2026-01-01T00:00:01.0Z\tpython tools/x.py',
                    'a\tVerify\t2026-01-01T00:00:02.0Z\t一些没有结论的输出',
                    'a\tVerify\t2026-01-01T00:00:03.0Z\t还在输出'])
    k4 = result_kinds(n4)
    ok4 = (len(n4) == 3) and (k4 == [])
    print('  [%s] S4 日志非空(%d 行)但零 RESULT -> kinds 空（应空）%s'
          % ('ok' if ok4 else 'X', len(n4),
             '' if ok4 else ' -> 实得 %s' % k4))
    if not ok4:
        bad.append('S4 空读数检测失效，「零命中当通过」的防护不成立')
    # S5 反向：正常日志必须能提取到 kinds（证明 S4 的空是内容真没有，
    # 而不是 result_kinds 本身恒返回空）
    k5 = result_kinds(n1)
    ok5 = len(k5) == 4 and k5.count('FAIL') == 2
    print('  [%s] S5 正常日志可提取 kinds（4 条，含 2 条 FAIL）%s'
          % ('ok' if ok5 else 'X', '' if ok5 else ' -> 实得 %s' % k5))
    if not ok5:
        bad.append('S5 kinds 提取失效，S4 的空结论不可信')
    return bad


def latest_runs(limit=6):
    out, rc = gh(['run', 'list', '--limit', str(limit), '--json',
                  'databaseId,status,conclusion,headSha,displayTitle'])
    if rc != 0:
        return []
    try:
        return json.loads(out)
    except Exception:
        return []


def main():
    argv = sys.argv[1:]
    run_id = None
    if argv and argv[0].isdigit():
        run_id = int(argv[0])
    print('=== 尺子有效性自检 ===')
    bs = selftest()
    print()
    if bs:
        print('RESULT: FAIL  本工具自检不通过，读数不可信：')
        for b in bs:
            print('  -', b)
        return 1

    if run_id is None:
        runs = latest_runs()
        done = [x for x in runs if x['status'] == 'completed']
        if not done:
            print('RESULT: SKIP  gh 取不到已完成的 run（未测不等于通过）')
            return 0
        target = done[0]
        run_id = target['databaseId']
        print('未指定 run，取最近一次已完成：%s  %s  %s' % (
            run_id, target['conclusion'],
            target['displayTitle'].splitlines()[0][:44]))
    else:
        print('指定 run %s' % run_id)

    out, rc = gh(['run', 'view', str(run_id), '--log'])
    if rc != 0 or not out.strip():
        print('RESULT: SKIP  取不到 run %s 的日志（未测不等于通过）' % run_id)
        return 0
    norm = normalize(out.splitlines())
    real, expected, stats = triage(norm)

    # job 权威结论
    o2, rc2 = gh(['api', 'repos/%s/actions/runs/%d' % (OWNER, run_id)])
    concl = '?'
    if rc2 == 0:
        try:
            concl = json.loads(o2.decode('utf-8', 'ignore')
                               if isinstance(o2, bytes) else o2)['conclusion']
        except Exception:
            concl = '?'

    kinds = result_kinds(norm)
    print()
    print('=== 原始读数 ===')
    print('  RESULT 行：PASS %d / FAIL %d / SKIP %d'
          % (kinds.count('PASS'), kinds.count('FAIL'), kinds.count('SKIP')))
    print('  job conclusion：%s' % concl)
    print()
    # 空读数必须拦（轮148 我手工踩坑逼出来的）。
    # 上一版只防「取不到日志」（rc!=0 或字节数为 0），不防「取到了却一条
    # RESULT 都没匹配上」—— 后者最容易骗人：编码不对时（PowerShell 的 >
    # 重定向写 UTF-16LE，按 utf-8 读会让每个 ASCII 字符后带一个 NUL，
    # 关键词全部匹配不到），338KB 的日志会被读成「0 行 RESULT」，
    # 于是「0 条 FAIL」被当成「没有任何失败」。真相是解析根本没工作。
    # 属 U-149 假守护同族：空读数不得当通过用。
    if not kinds:
        print('RESULT: FAIL  日志共 %d 行却匹配到 0 条 RESULT —— ' % len(norm))
        print('          这几乎一定是取数或解码失效，而不是「全过」；'
              '先查编码，gh 日志经 PowerShell 重定向会得到 UTF-16LE')
        return 1
    print('=== 按「步骤末条 RESULT」分类 ===')
    print('  真失败 %d 条 ｜ 步骤内期望输出（反向验证注入）%d 条'
          % (len(real), expected))
    for step, n, nf, nreal, ns in stats:
        if nf or ns or nreal:
            print('  %-26s RESULT %3d 条，FAIL %2d（真 %d），SKIP %d'
                  % (step[:26], n, nf, nreal, ns))
    if real:
        print()
        print('RESULT: FAIL  %d 条真失败：' % len(real))
        for r in real[:10]:
            print('  -', r[:130])
        return 1
    print()
    print('RESULT: PASS  %d 条 FAIL 全为反向验证的期望输出，真失败 0 条；'
          'job conclusion=%s' % (expected, concl))
    return 0


if __name__ == '__main__':
    sys.exit(main())
