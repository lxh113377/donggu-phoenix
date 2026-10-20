# -*- coding: utf-8 -*-
"""tools/narration_gate_test.py —— 旁白音道（I-5）静态判据（CI 可跑，零浏览器依赖）。

对标报告 §3.1 明确缺失 1：speechSynthesis=0、<track>=0、音视频字幕文件 0，
152 秒叙事完全依赖视觉阅读。乡村展陈现场嘈杂、受众含长者与视障，无声道是真实缺口。
I-5 用浏览器内置 speechSynthesis 补上（零音频文件、零外部请求）。

本判据守六种退化方式：
  1) 开关被删（页面再没有旁白入口）
  2) 无 TTS 引擎时未降级（按钮可点却毫无反应 / 抛错）
  3) 语音与画面脱节（切场景、暂停、关闭不 cancel）
  4) 切章不念（只在开启瞬间念一次）
  5) 不监听 voiceschanged（iOS/微信内核语音列表异步填充，挑不到中文语音）
  6) **破了零外部请求**（引入音频文件或 CDN TTS）—— 本项目硬约束，必须盯死

实现口径（一手教训）：
  · 判据不依赖浏览器（U-10：浏览器通道不稳，挂在浏览器上的门禁迟早变成红灯噪声源）；
  · 检查「函数体内有没有 cancel」必须按大括号配对取函数体。
    第一版用 \\s\\S{0,900}? 的滑动窗口，实测 loadScene→close 两处 cancel 相距 620 字符，
    窗口跨函数吞掉了 close() 的那句 —— 删掉 loadScene 的 cancel 判据仍然 PASS（假绿）。
    这类「判据自己写松了」正是台账 U-04/U-18/U-22 反复记录的病。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_guard import verdict, emit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

AUDIO_EXT = (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus", ".vtt", ".srt")
TTS_CDN_HINTS = ("translate.googleapis", "voice.speech", "cognito", "azure", "speech.googleapis")


def rd(p):
    return open(p, encoding="utf-8", errors="replace").read()


def strip_comments(s):
    """剥注释后再做「反模式/外链」扫描（U-24 同课：注释里的字不是代码行为）。
    例外：本文件的云端 TTS 判据用剥注释后的文本 —— 注释里写「不用 translate.googleapis」
    这种说明句不该把 CI 判红，但真的把 URL 写进字符串就必红。
    """
    s = re.sub(r"/\\*.*?\\*/", " ", s, flags=re.S)
    s = re.sub(r"//[^\\n]*", " ", s)
    return s


def func_body(src, header):
    """按大括号配对取函数体（含嵌套）；找不到返回 None。"""
    i = src.find(header)
    if i < 0:
        return None
    j = src.find("{", i)
    if j < 0:
        return None
    depth = 0
    for k in range(j, len(src)):
        ch = src[k]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[j + 1:k]
    return None


def main():
    html = rd(os.path.join(SITE, "index.html"))
    arjs = rd(os.path.join(SITE, "assets", "js", "ar.js"))
    css = rd(os.path.join(SITE, "assets", "css", "main.css")).replace("\r\n", "\n")
    fails = []
    checked = 0

    # 1) 入口存在且语义正确
    for tok, why in (
        (chr(39) + 'id="ar-narrate"' + chr(39), "旁白开关按钮"),
    ):
        checked += 1
        if 'id="ar-narrate"' not in html:
            fails.append("页面缺少旁白开关 #ar-narrate（%s）" % why)
    checked += 1
    if 'aria-pressed="false"' not in html:
        fails.append("旁白开关缺 aria-pressed 初始态（读屏无法区分开关与普通按钮）")

    # 2) 内置 TTS：必须真的用 speechSynthesis 念出来
    checked += 1
    if "speechSynthesis" not in arjs:
        fails.append("ar.js 未使用 speechSynthesis（旁白未落地）")
    checked += 1
    if "SpeechSynthesisUtterance" not in arjs:
        fails.append("ar.js 未创建 SpeechSynthesisUtterance（只判支持没真念）")
    checked += 1
    if not re.search(r"speechSynthesis\.speak\(u\)", arjs):
        fails.append("ar.js 未调用 speak()（建了 utterance 却没说）")

    # 3) 零外部请求：不得出现音频/字幕文件，也不得引用任何云端 TTS
    audio_files = []
    for r, _, fs_ in os.walk(SITE):
        for f in fs_:
            if f.lower().endswith(AUDIO_EXT):
                audio_files.append(os.path.relpath(os.path.join(r, f), SITE))
    checked += 1
    if audio_files:
        fails.append("出现音频/字幕文件 %d 个（I-5 必须用内置 TTS 守住零外部请求）: %s"
                     % (len(audio_files), ", ".join(audio_files[:4])))
    checked += 1
    hit_cdn = [h for h in TTS_CDN_HINTS if h in strip_comments(arjs)]
    if hit_cdn:
        fails.append("旁白引用了云端 TTS 域名（违反零外部请求）: " + ", ".join(hit_cdn))

    # 4) 不支持环境降级：置 disabled + 可见文案，不能静默「可用」
    checked += 1
    if "narr.supported" not in arjs or "disabled = true" not in arjs:
        fails.append("无 TTS 引擎时未降级（应置 disabled 并给出可读文案）")

    # 5) 语音与画面同步：三处 cancel 必须在**各自函数体**内
    for header, why in (("function loadScene(id, autoplay)", "切场景"),
                        ("function close()", "关闭播放层")):
        checked += 1
        body = func_body(arjs, header)
        if body is None:
            fails.append("找不到 %s（判据锚点失配，需同步更新本判据）" % header)
        elif "narr.cancel()" not in body:
            fails.append("旁白未在「%s」处 cancel（声音会与画面脱节）" % why)

    checked += 1
    # 暂停（按钮 + 空格）两处都要停声
    n_pause_cancel = len(re.findall(r"state\.playing = !state\.playing;[\s\S]{0,140}?narr\.cancel\(\)", arjs))
    if n_pause_cancel < 2:
        fails.append("暂停/空格未停旁白（实得 %d 处，需 >=2）" % n_pause_cancel)

    # 6) 切章即念
    checked += 1
    if not re.search(r"if \(ci !== lastChapter\)[\s\S]{0,420}?narr\.chapter\(ch\)", arjs):
        fails.append("章节切换未触发旁白（narr.chapter 未在切章分支调用）")

    # 7) 语音列表异步：必须监听 voiceschanged
    checked += 1
    if "voiceschanged" not in arjs:
        fails.append("未监听 voiceschanged（iOS/微信内核语音列表异步填充）")

    # 8) 视觉反馈：开启态必须有样式
    checked += 1
    if ".ar-btn.narrate.on" not in css.replace(" ", ""):
        fails.append("旁白开关缺开启态样式（用户看不出旁白是否正在播）")

    # 8b) 旁白可视态必须独立于 paintHud 同步（U-134 一手缺陷：
    #     原先只在 paintHud 里写 aria-pressed，而 paintHud 开头 if (!state.scene) return;
    #     ⇒ AR 未打开时点旁白，narr.on 已 true 但按钮不变、读屏也不知道。
    #     实测证据：点击后 narr.on=true 而 aria-pressed 仍是 "false"。）
    checked += 1
    if "function syncNarrBtn()" not in arjs:
        fails.append("旁白按钮状态未独立成 syncNarrBtn()（会被 paintHud 的无场景早退吞掉）")
    checked += 1
    n_sync = len(re.findall(r"syncNarrBtn\(\)", arjs))
    # 定义处 1 + paintHud 1 + 点击 1 + API 1 = 4；少于 3 说明某个入口漏同步
    if n_sync < 3:
        fails.append("syncNarrBtn 调用点仅 %d 处（点击/API/paintHud 三处都需同步）" % n_sync)
    checked += 1
    # aria 同步不得写在 paintHud 的早退之后（否则等于没有）
    hud_body = func_body(arjs, "function paintHud(now)") or ""
    if "syncNarrBtn();" not in hud_body:
        fails.append("paintHud 未调用 syncNarrBtn（逐帧回同步缺失）")

    # 9) 自动化验收面
    checked += 1
    if not re.search(r"narr: narr\.supported", arjs):
        fails.append("__ar.stats 未暴露旁白状态（无法自动验收）")
    checked += 1
    if "narrate: function" not in arjs:
        fails.append("__ar 未暴露 narrate() 控制口（无法自动开关旁白做验收）")

    # 10) 正则字面量里不许写中文（会被「按引号配对收集渲染字符」的字体判据当成待渲染文本）
    checked += 1
    cjk_in_regex = re.findall(r"/[^/\n]*[\u4e00-\u9fff][^/]*/[a-z]*\.test", arjs)
    if cjk_in_regex:
        fails.append("正则字面量含中文 %d 处（污染字体子集口径）: %s"
                     % (len(cjk_in_regex), cjk_in_regex[0][:40]))

    print("旁白判据：HTML / ar.js / CSS 三侧共 %d 项" % checked)
    for f in fails:
        print("  -", f)
    code, msg = verdict(checked=checked, fails=fails, what="旁白音道判据")
    return emit(code, msg)


if __name__ == "__main__":
    sys.exit(main())
