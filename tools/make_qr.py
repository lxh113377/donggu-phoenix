# -*- coding: utf-8 -*-
"""二维码生成 + 强制回读自检（qrcode 生成 -> OpenCV 解码，逐字节比对）。"""
import os, sys, json, re, argparse
import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_Q
import cv2

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_URL = "https://lxh113377.github.io/donggu-phoenix/"

def make(url, out_png, box=10, border=4, ecc=ERROR_CORRECT_H, fill="#0B0908", back="#F6F1E7"):
    qr = qrcode.QRCode(version=None, error_correction=ecc, box_size=box, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back)
    img.save(out_png)
    return out_png

def verify(path, expect):
    arr = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if arr is None:
        return False, "cannot read image"
    det = cv2.QRCodeDetector()
    data, pts, _ = det.detectAndDecode(arr)
    if not data:
        # 放大 2 倍重试
        big = cv2.resize(arr, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        data, pts, _ = det.detectAndDecode(big)
    return (data == expect), data

# 场景清单由唯一内容源 ar-data.js 派生（I-8，2026-10-20 轮50）。
# 原先此处把 ("craft","red","phoenix") 写死两处，加一段场景就要同时改生成器与门禁；
# 忘改的后果是「新场景上线但没有直连码」或反过来「二维码指向不存在的场景」。
def scene_list():
    """从 ar-data.js 取 [(id, 场景名)]，顺序即数据层顺序。取不到就直接失败（不静默降级）。"""
    ap = os.path.join(BASE, "site", "assets", "data", "ar-data.js")
    s = open(ap, encoding="utf-8").read()
    ids = re.findall(r"^\s+id: '([a-z][a-z0-9_-]*)',", s, re.M)
    names = re.findall(r"^\s+name: '([^']+)',", s, re.M)
    if not ids:
        raise SystemExit("ar-data.js 未解析到任何场景 id（生成器不能对着空清单出码）")
    out = []
    for i, sid in enumerate(ids):
        # scenes 之前还有 meta.name / route.title 等 name 字段，故用「同场景块内」的启发式：
        # id 出现位置之后的第一个 name 就是该场景名。
        pos = s.find("id: '" + sid + "'")
        m = re.search(r"^\s+name: '([^']+)',", s[pos:], re.M)
        out.append((sid, m.group(1) if m else sid))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    url = args.url.strip()

    targets = [
        (os.path.join(BASE, "qr", "qr-1024.png"), 20),
        (os.path.join(BASE, "qr", "qr-512.png"), 10),
        (os.path.join(BASE, "qr", "qr-256.png"), 5),
        (os.path.join(BASE, "site", "assets", "img", "qr.png"), 12),
    ]
    ok_all = True
    for path, box in targets:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        make(url, path, box=box)
        ok, decoded = verify(path, url)
        size = os.path.getsize(path)
        print(f"[{'PASS' if ok else 'FAIL'}] {os.path.relpath(path, BASE)}  {size}B  decoded={decoded!r}")
        if not ok:
            ok_all = False

    # 深色物料版：码区保持「深码浅底」（保证任何扫码器可解），外侧加畲族深底圆角承托
    dark = os.path.join(BASE, "qr", "qr-poster.png")
    make(url, dark, box=14, fill="#0B0908", back="#F6F1E7")
    ok, decoded = verify(dark, url)
    print(f"[{'PASS' if ok else 'FAIL'}] qr/qr-poster.png  decoded={decoded!r}")
    ok_all = ok_all and ok

    # 场景直连二维码：现场展签/文创上贴「直接开演第 N 段」，省一次点击，减少中途退出
    scene_variants = []
    for sid, label in scene_list():
        p = os.path.join(BASE, "qr", "qr-ar-%s.png" % sid)
        target = url.rstrip("/") + "/#ar=" + sid
        make(target, p, box=12)
        ok, decoded = verify(p, target)
        print(f"[{'PASS' if ok else 'FAIL'}] qr/qr-ar-{sid}.png（{label}直连） decoded={decoded!r}")
        ok_all = ok_all and ok
        scene_variants.append(os.path.relpath(p, BASE))

    # 元数据落盘，供站点/文档引用
    meta = {"url": url, "generated": targets[0][0],
            "variants": [os.path.relpath(t[0], BASE) for t in targets] + ["qr/qr-poster.png"] + scene_variants,
            "sceneDeepLinks": {sid: url.rstrip("/") + "/#ar=" + sid for sid, _ in scene_list()}}
    with open(os.path.join(BASE, "qr", "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("URL:", url)
    sys.exit(0 if ok_all else 1)

if __name__ == "__main__":
    main()