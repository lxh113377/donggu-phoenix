# 文创打样文件包

> 由 tools/make_proof_pack.py 生成；规格事实来源 = site/assets/data/culture.js。
> 打印后先用页底 100mm 比例尺校验未被缩放，再发厂。

- 凤凰徽章（proof-badge.pdf）：O 58 mm（圆形） · 马口铁 0.23 mm + 安全别针 + PET 覆膜
- 凤影纸雕灯（proof-lamp.pdf）：210 × 91 mm（成品）· 内芯 195 × 76 mm · 300g 白卡 ×7 层 + 120g 硫酸纸 ×6 + 亚克力底板 + 暖白 LED 3000K
- 凤纹帆布袋（proof-tote.pdf）：380 × 420 mm（提手 750 mm 双股） · 12oz 本白棉（未漂白），双针缝线，底部加固

## 回样后怎么替换线上图

    python tools/replace_merch_photo.py badge <实拍文件>
    python tools/replace_merch_photo.py --all      # 按 merch/shot/ 命名批量

实拍原件请存 merch/shot/<id>.<ext>，脚本会归档、缩放、编码、生成 -340 小档并跑门禁。
