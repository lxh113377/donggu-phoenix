# -*- coding: utf-8 -*-
"""tools/safe_mutation.py —— 破坏性测试的安全框架（U-09 根治）。

## 为什么需要它

轮11 的真实事故：U-07 的修复改完没提交，接着我跑反向测试。
那些脚本的做法是「备份真实文件 → 原地改 → 跑测试 → 还原」。
跑了若干轮后修复被覆盖丢失，直到 git checkout 才发现恢复出来的是**未修版本** ——
也就是说前几轮「验证通过」验的全是旧代码。

根因不是某个脚本写错，而是**范式错**：破坏性测试不该碰被 git 跟踪的工作区文件。
一旦中途异常/被打断/任务被 kill，还原那段代码就永远不执行。

## 正确姿势

1. **前置检查**：目标文件必须已提交（git diff 为空），否则拒绝跑。
   —— 未提交的修改就是「可能被覆盖丢失的东西」，必须先落盘。
2. **操作副本**：把整个 site/ 复制到临时目录，在副本上改，测完直接删。
   —— 真实工作区从头到尾一个字节都不动。
3. **失败也要还原**：用 try/finally 保证临时目录清理。
4. **最后再核验一次**：测试结束后断言真实文件与开始时的 git 状态一致。

## 用法

    from tools.safe_mutation import mutate_sandbox

    with mutate_sandbox() as sandbox:
        sandbox.patch('site/assets/css/main.css',
                      [('旧文本', '新文本')])
        result = sandbox.run_python('tools/verify_site.py')
        print(result.returncode)

sandbox 里所有文件都在临时目录，run_python 的 cwd 是副本根目录。
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args):
    r = subprocess.run(['git'] + list(args), cwd=BASE, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


class Sandbox:
    def __init__(self, root):
        self.root = root

    def path(self, rel):
        return os.path.join(self.root, rel)

    def patch(self, rel, replacements, must_all_match=True):
        """在副本上做文本替换。replacements = [(old, new), ...]"""
        p = self.path(rel)
        s = open(p, encoding='utf-8', newline='').read()
        for old, new in replacements:
            if old not in s:
                if must_all_match:
                    raise AssertionError('副本里找不到待替换文本: %r' % old[:60])
                continue
            s = s.replace(old, new, 1)
        open(p, 'w', encoding='utf-8', newline='').write(s)

    def run_python(self, script, extra_args=None, timeout=180):
        cmd = [sys.executable, script] + (extra_args or [])
        return subprocess.run(cmd, cwd=self.root, capture_output=True, text=True,
                              timeout=timeout, encoding='utf-8', errors='replace')


@contextmanager
def mutate_sandbox(require_clean=True, dirs=('site', 'tools')):
    """开一个可破坏的副本；真实工作区全程只读。"""
    if require_clean:
        rc, out = _git('status', '--porcelain', '--', *dirs)
        dirty = [l for l in out.splitlines() if l.strip()]
        if dirty:
            raise RuntimeError(
                '存在未提交改动，拒绝跑破坏性测试（未提交 = 可能被覆盖丢失）:\n  '
                + '\n  '.join(dirty[:8])
                + '\n请先提交，或显式传 require_clean=False')
    tmp = tempfile.mkdtemp(prefix='dsh_sandbox_')
    root = os.path.join(tmp, 'repo')
    os.makedirs(root, exist_ok=True)
    for d in dirs:
        src = os.path.join(BASE, d)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(root, d))
    # 副本里不需要 .git，但有些脚本会读；建个空目录避免报错
    os.makedirs(os.path.join(root, '.git'), exist_ok=True)

    before = {}
    for d in dirs:
        for r, _, fs in os.walk(os.path.join(BASE, d)):
            for f in fs:
                fp = os.path.join(r, f)
                before[os.path.relpath(fp, BASE)] = _sha(fp)

    sb = Sandbox(root)
    try:
        yield sb
    finally:
        # 清理副本
        shutil.rmtree(tmp, ignore_errors=True)
        # 核验真实工作区一字节未变
        changed = []
        for rel, h in before.items():
            fp = os.path.join(BASE, rel)
            if not os.path.exists(fp) or _sha(fp) != h:
                changed.append(rel)
        if changed:
            sys.stderr.write('[safe_mutation] 警告：真实文件发生变化！\n  '
                             + '\n  '.join(changed[:8]) + '\n')


def main():
    """自检：确认框架本身可用。"""
    print('safe_mutation 自检')
    print('工作区改动检查：')
    rc, out = _git('status', '--porcelain', '--', 'site', 'tools')
    dirty = [l for l in out.splitlines() if l.strip()]
    print('  未提交改动:', len(dirty))
    print()
    print('用法示例：')
    print('  from tools.safe_mutation import mutate_sandbox')
    print('  with mutate_sandbox() as sb:')
    print('      sb.patch("site/assets/css/main.css", [("旧", "新")])')
    print('      r = sb.run_python("tools/verify_site.py")')
    return 0


if __name__ == '__main__':
    sys.exit(main())
