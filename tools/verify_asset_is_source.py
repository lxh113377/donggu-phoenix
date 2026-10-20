
import os, json
import numpy as np, cv2
BASE = r"C:\Users\37533\Desktop\workspace\项目\新建文件夹"
meta = json.load(open(os.path.join(BASE, "_dev", "mate", "statue_asset_meta.json"), encoding="utf-8"))
print("meta:", meta)
x0, y0, x1, y1 = meta["bboxInSrc"]
poster = cv2.imread(os.path.join(BASE, "素材", "597fa4848ad5fdef17da516d62a85099.jpg"))
asset = cv2.imread(os.path.join(BASE, "site", "assets", "img", "statue-cut.webp"), cv2.IMREAD_UNCHANGED)
crop = poster[y0:y1+1, x0:x1+1]
print("海报裁切", crop.shape, "资产", asset.shape)
assert crop.shape[:2] == asset.shape[:2], "尺寸必须逐像素对应"

# 只看资产 alpha 完全不透明的内部（边缘 1px 羽化与 JPEG 振铃不可避免）
inner = cv2.erode((asset[:,:,3] > 250).astype(np.uint8), np.ones((5,5), np.uint8)) > 0
print("内部像素", int(inner.sum()))
d = np.abs(asset[:,:,:3].astype(np.int16) - crop[:,:,:3].astype(np.int16)).max(axis=2)[inner]
print("=== 成品资产 vs 海报原像素（成品内部）===")
print("完全相同 %.2f%%" % ((d==0).mean()*100))
print("误差<=2   %.2f%%" % ((d<=2).mean()*100))
print("误差<=5   %.2f%%" % ((d<=5).mean()*100))
print("误差>10   %.2f%%   平均 %.2f   最大 %d" % ((d>10).mean()*100, d.mean(), d.max()))

# 若把资产再编码成无损，证明确实只是 WebP 有损那一步带来的差
lossless = os.path.join(BASE, "_dev", "e2e", "asset_lossless.webp")
cv2.imwrite(lossless, asset, [int(cv2.IMWRITE_WEBP_QUALITY), 101])
print("当前资产 %d B；无损版 %d B" % (os.path.getsize(os.path.join(BASE, "site/assets/img/statue-cut.webp")), os.path.getsize(lossless)))
