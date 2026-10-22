# -*- coding: utf-8 -*-
# tools/ab_compat.py —— agent-browser 命令到 CDP 的兼容层（轮118）。
#
# ## 为什么需要
# tools/ 下有 12 条判据仍写成 ps('agent-browser <cmd> ...') 形态，
# 而 agent-browser 二进制在本机根本不存在（CommandNotFoundException），
# 它们从来没有读数 —— 却在 --status 里被当成「非 RUNNABLE」静置（轮117 已改为诚实标注）。
#
# 逐条重写成本高、易引入新错。勘察后发现它们只用 4 个动词：
#   open / set viewport / wait --load / eval
# 且 av() 调用形态高度一致，故做一层「命令翻译」：把 ps('agent-browser ...')
# 的语义映射到 cdp_client，判据的业务逻辑一行不动。
#
# ## 设计约束
# · 不静默降级：不支持的命令必须抛异常并点名，绝不返回空字符串冒充成功
#   （否则又是一次「判据存在但跑不了」）
# · 保留 ps() 返回的字符串形态：判据下游都是 out.strip() / re.search，
#   兼容层返回字符串，下游代码零改动
#
# ## 用法（判据内替换 ps 的实现）
#   from ab_compat import AbSession
#   AB = AbSession()          # 惰性启动，首次命令时才起 chrome
#   def ps(cmd, timeout=60): return AB.run(cmd, timeout)
#   ... 其余代码不动 ...
#   AB.close()                # 结束时关闭

import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(BASE, 'tools')
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)


class AbCompatError(RuntimeError):
    '''不支持的命令 / 无法映射 —— 必须显式报错，不得静默通过。'''


class AbSession(object):
    '''把 agent-browser 命令翻译成 CDP 调用。惰性启动 chrome。'''

    def __init__(self, width=1440, height=900):
        self.width = width
        self.height = height
        self._ch = None
        self._page = None
        self._tid = None
        self.calls = 0

    # ---- 内部 ----
    def _ensure(self):
        if self._page is not None:
            return
        from cdp_client import Chrome, find_chrome
        if not find_chrome():
            raise AbCompatError('找不到 chrome（环境问题，判据未执行）')
        self._ch = Chrome()
        self._page, self._tid = self._ch.new_page(self.width, self.height)

    def _viewport(self, w, h):
        '''set viewport -> 用设备指标覆盖（不重建页，保留已加载的文档）。'''
        self._ensure()
        self.width, self.height = int(w), int(h)
        self._page.call('Emulation.setDeviceMetricsOverride', {
            'width': int(w), 'height': int(h),
            'deviceScaleFactor': 1, 'mobile': int(w) < 800})

    def _load_js(self, spec):
        '''解析 eval 的实参：'"JS"' 或 PowerShell 的 (Get-Content -Raw file)。'''
        spec = spec.strip()
        m = re.match(r'^\(Get-Content\s+-Raw\s+-Encoding\s+UTF8\s+["\'](.+?)["\']\)$', spec)
        if m:
            path = m.group(1)
            p = path if os.path.isabs(path) else os.path.join(BASE, path)
            with open(p, encoding='utf-8') as f:
                return f.read()
        # 去掉最外层引号（单或双），保留内部内容
        m2 = re.match(r'^"(.*)"$', spec, re.S)
        if m2:
            return m2.group(1)
        m3 = re.match(r"^'(.*)'$", spec, re.S)
        if m3:
            return m3.group(1)
        return spec

    def _navigate(self, url):
        self._ensure()
        if not self._ch.navigate(self._page, url):
            raise AbCompatError('导航失败: %s' % url[:80])

    def _wait_networkidle(self):
        self._ensure()
        # CDP 版没有 networkidle 事件订阅，用「文档就绪 + main.js 初始化」近似
        self._ch.wait_for(self._page, 'document.readyState === "complete"', 30)
        self._ch.wait_for(
            self._page, '!!(window.__ar || window.__phoenix || document.body)', 30)
        time.sleep(0.6)   # 给 rAF 首帧与 reveal 观察器一点时间

    # ---- 对外 ----
    def run(self, cmd, timeout=60):
        '''执行一条 agent-browser 命令，返回等价于原 ps() 的字符串。'''
        self.calls += 1
        cmd = cmd.strip()
        if not cmd.startswith('agent-browser'):
            raise AbCompatError('非 agent-browser 命令: %s' % cmd[:60])
        rest = cmd[len('agent-browser'):].strip()
        m = re.match(r'^([a-z-]+)\s*(.*)$', rest, re.S)
        if not m:
            raise AbCompatError('命令解析失败: %s' % cmd[:60])
        verb, arg = m.group(1), m.group(2).strip()

        if verb == 'open':
            url = arg.strip('"')
            self._navigate(url)
            return 'ok'
        if verb == 'set':
            mm = re.match(r'^viewport\s+(\d+)\s+(\d+)', arg)
            if not mm:
                raise AbCompatError('不支持的 set 子命令: %s' % arg[:40])
            self._viewport(mm.group(1), mm.group(2))
            return 'ok'
        if verb == 'wait':
            if 'networkidle' in arg or 'load' in arg:
                self._wait_networkidle()
                return 'ok'
            raise AbCompatError('不支持的 wait: %s' % arg[:40])
        if verb == 'eval':
            self._ensure()
            js = self._load_js(arg)
            out = self._page.eval_js(js, timeout=max(5, min(timeout, 60)))
            return _stringify(out)
        raise AbCompatError('不支持的动词: %s（兼容层只实现 open/set/wait/eval）' % verb)

    def close(self):
        try:
            if self._page is not None:
                self._page.close()
        except Exception:
            pass
        try:
            if self._ch is not None and self._tid:
                self._ch.close_page(self._tid)
        except Exception:
            pass
        try:
            if self._ch is not None:
                self._ch.close()
        except Exception:
            pass
        self._page = self._ch = self._tid = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def _stringify(v):
    '''让返回值形态贴近 agent-browser eval 的输出（字符串）。'''
    if v is None:
        return ''
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    import json
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)