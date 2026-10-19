# -*- coding: utf-8 -*-
import os
from PIL import Image
BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
SRC = os.path.join(BASE, "merch", "mock")
DST = os.path.join(BASE, "site", "assets", "img", "merch")
os.makedirs(DST, exist_ok=True)
for name in ["mock-badge.png","mock-lamp.png","mock-tote.png","mock-bookmark.png","mock-fan.png","poster-a4.png"]:
    p = os.path.join(SRC, name)
    if not os.path.exists(p):
        print("skip", name); continue
    im = Image.open(p).convert("RGB")
    W = 760
    if im.width > W:
        im = im.resize((W, int(im.height*W/im.width)), Image.LANCZOS)
    out = os.path.join(DST, name.replace(".png", ".webp"))
    im.save(out, "WEBP", quality=84, method=6)
    print(os.path.basename(out), os.path.getsize(out), "bytes")
