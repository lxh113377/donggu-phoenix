# -*- coding: utf-8 -*-
"""线上二维码实扫验证：下载线上 qr.png，用 OpenCV 解码，逐字节比对线上 URL。"""
import urllib.request, io, sys
import cv2, numpy as np

URL = "https://lxh113377.github.io/donggu-phoenix/assets/img/qr.png"
EXPECT = "https://lxh113377.github.io/donggu-phoenix/"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
data = urllib.request.urlopen(req, timeout=30).read()
print(f"[INFO] 下载线上 qr.png: {len(data)} bytes")

arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
print(f"[INFO] 图像尺寸: {arr.shape}")
det = cv2.QRCodeDetector()
decoded, pts, _ = det.detectAndDecode(arr)
if not decoded:
    big = cv2.resize(arr, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    decoded, pts, _ = det.detectAndDecode(big)
    print("[INFO] 放大 2x 重试")

ok = (decoded == EXPECT)
print(f"[{'PASS' if ok else 'FAIL'}] 线上二维码解码")
print(f"       期望: {EXPECT!r}")
print(f"       实际: {decoded!r}")
sys.exit(0 if ok else 1)
