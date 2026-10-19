# -*- coding: utf-8 -*-
"""二维码生成 + 强制回读自检（qrcode 生成 -> OpenCV 解码，逐字节比对）。"""
import os, sys, json, argparse
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

    # 元数据落盘，供站点/文档引用
    meta = {"url": url, "generated": targets[0][0], "variants": [os.path.relpath(t[0], BASE) for t in targets] + ["qr/qr-poster.png"]}
    with open(os.path.join(BASE, "qr", "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("URL:", url)
    sys.exit(0 if ok_all else 1)

if __name__ == "__main__":
    main()
