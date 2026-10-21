# -*- coding: utf-8 -*-
"""tools/make_proof_pack.py —— 生成「可直接发厂」的文创打样文件包（U-02 的自动化面）。

为什么需要它
  U-02 卡了很久：评审一眼能看出「像设计稿不像产品」，因为文创图是代码渲染的效果图。
  但「打样」里能自动化的部分一直没做 —— 工厂要的不是效果图，而是带尺寸/出血/
  材质/工艺/验收点的规格文件。以前每次都要现写现排，于是干脆没发过厂。

  本脚本一键生成三份规格 PDF（badge / lamp / tote，点名的三件），每页含：
  成品尺寸 + 出血/咬口 + 材质工艺 + 印刷文件指向 + 逐条验收勾 + 100mm 实物比例尺。
  打印到 A4 实际尺寸即可当「回样核对卡」；比例尺用于校验 PDF 未被缩放。

边界（诚实口径）
  生成本包 != 已打样。工厂回样与实拍是物理动作，由 tools/replace_merch_photo.py 收口。
  PDF 不入部署面（merch/ 不在 site/ 下），不占 1600KB 预算，verify_site 不受影响。

中文字体（第一版踩的坑，别再踩）
  reportlab 内置 Helvetica **不含中文字形**：不注册字体的第一版 PDF，所有中文
  在文本层直接变成字母 I（PyMuPDF 抽文本实测 'IIIII · IIII (badge)'），
  发给工厂等于发一张全是豆腐块的纸。现按优先级注册系统 TTF/TTC（simsun/msyh/simhei），
  全不可用时降级 CID 字体 STSong-Light；一个都没有就拒绝生成并报错，绝不静默出豆腐。

用法
  python tools/make_proof_pack.py            # 生成到 merch/proof/
  python tools/make_proof_pack.py --check    # 只校验规格自洽，不写文件
"""
import argparse
import datetime
import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "merch", "proof")

# 规格的唯一事实来源 = site/assets/data/culture.js（页面展示什么，工厂就按什么做）。
# 另写一份尺寸必然漂移，所以启动时与 culture.js 对账，不一致直接拒绝生成。
ITEMS = [
    dict(id="badge", cn="凤凰徽章",
         cut="O 58 mm（圆形）", bleed="外扩 3 mm（即 O 64 mm 下料）",
         material="马口铁 0.23 mm + 安全别针 + PET 覆膜",
         process="UV 四色 + 光油；包边压合后不得露铁",
         art="merch/print/phoenix-totem-color.svg",
         art_note="全彩渐变版，图腾居中，四周留 4 mm 不印区（包边会吃掉）",
         accept=["直径实测 58±0.5 mm", "包边无毛刺、不刮手", "别针焊点拉 5N 不脱",
                 "色值与线上 r-badge.webp 目视一致", "背面留别针位不压图"],
         qty="首样 5 件"),
    dict(id="lamp", cn="凤影纸雕灯",
         cut="210 × 91 mm（成品）· 内芯 195 × 76 mm", bleed="每层四边留 2 mm 咬口",
         material="300g 白卡 ×7 层 + 120g 硫酸纸 ×6 + 亚克力底板 + 暖白 LED 3000K",
         process="激光镂空（以 300g 白卡切透不焦边为准）；层间间距 6 mm",
         art="merch/print/phoenix-totem-mono.svg",
         art_note="单色线稿版：镂空路径必须闭合，线宽 >= 0.3 mm 否则激光切不断",
         accept=["七层套准误差 <= 0.5 mm", "切边无焦黄（试切角留样比对）",
                 "点亮后无漏光缝、3000K 不偏绿", "连续点亮 30 min 外壳 <= 45℃",
                 "USB 出口与底板开孔对齐"],
         qty="首样 3 件"),
    dict(id="tote", cn="凤纹帆布袋",
         cut="380 × 420 mm（提手 750 mm 双股）", bleed="印刷区四周各留 10 mm 安全边",
         material="12oz 本白棉（未漂白），双针缝线，底部加固",
         process="丝网印单色（或热转印，二选一报价）；印后水洗 3 次不掉色",
         art="merch/print/phoenix-totem-mono.svg",
         art_note="单色线稿版，印于正面居中，图上沿距袋口 120 mm",
         accept=["成品尺寸 380×420 ±5 mm", "提手缝合拉力 10 kg 不脱",
                 "水洗 3 次色牢度 >= 4 级", "无异味（甲醛/荧光剂不得检出）",
                 "本白不偏蓝（与线上 r-tote.webp 比色）"],
         qty="首样 5 件"),
]


def load_culture_specs():
    """从 culture.js 抠 id -> (name, spec)，作为规格对账基准。"""
    p = os.path.join(BASE, "site", "assets", "data", "culture.js")
    s = open(p, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"id: '([a-z-]+)',\s*image: '[^']+',\s*name: '([^']*)',\s*spec: '([^']*)'", s):
        out[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
    return out


def check_specs():
    """PDF 里的尺寸必须与页面展示的 spec 同源，否则工厂按 A 做、观众看 B。"""
    cs = load_culture_specs()
    bad = []
    for it in ITEMS:
        if it["id"] not in cs:
            bad.append("%s：culture.js 里没有这件（数据漂移）" % it["id"])
            continue
        name, spec = cs[it["id"]]
        if name and name not in it["cn"] and it["cn"] not in name:
            bad.append("%s：品名不一致 PDF=%r vs 页面=%r" % (it["id"], it["cn"], name))
        # 只比「成品尺寸串」，不比工艺参数。页面 spec 形如
        #   "Ø 58 mm · 马口铁包边 …" / "210 × 91 mm · 七层激光镂空 · 暖白 3000K"
        # 首段（第一个 · 之前）才是尺寸；后面的数字是层数/色温/克重，
        # 拿去比尺寸会把正常数据判成漂移（第一版误报 lamp/tote；
        # 第二版又因圆形只有 1 个数字而误报 badge —— 按语义切段才对）。
        page_size = spec.split("·")[0]
        pdf_size = re.split(r"[（(·]", it["cut"])[0]
        nums_page = re.findall(r"\d+(?:\.\d+)?", page_size)
        nums_pdf = re.findall(r"\d+(?:\.\d+)?", pdf_size)
        if not nums_page:
            bad.append("%s：页面 spec 首段读不到尺寸数字：%s" % (it["id"], spec))
        elif nums_pdf != nums_page:
            bad.append("%s：成品尺寸对不上 PDF=%s(%s) vs 页面=%s(%s)"
                       % (it["id"], pdf_size, nums_pdf, page_size, nums_page))
        ap = os.path.join(BASE, it["art"].replace("/", os.sep))
        if not os.path.exists(ap):
            bad.append("%s：印刷文件缺失 %s" % (it["id"], it["art"]))
    return bad


def register_cjk():
    """注册一套能渲染中文的字体，返回 (regular, bold)。全失败返回 None。

    TTC 必须带 subfontIndex（simsun.ttc 是多字重集合，不指索引 reportlab 会抛错）。
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    cands = [
        (r"C:\Windows\Fonts\simsun.ttc", 0, "cn-regular"),
        (r"C:\Windows\Fonts\msyh.ttc", 0, "cn-regular"),
        (r"C:\Windows\Fonts\simhei.ttf", None, "cn-regular"),
    ]
    bolds = [
        (r"C:\Windows\Fonts\msyhbd.ttc", 0, "cn-bold"),
        (r"C:\Windows\Fonts\simhei.ttf", None, "cn-bold"),
        (r"C:\Windows\Fonts\simsun.ttc", 0, "cn-bold"),
    ]
    def reg(lst):
        for path, idx, name in lst:
            if not os.path.exists(path):
                continue
            try:
                pdfmetrics.registerFont(
                    TTFont(name, path, subfontIndex=idx) if idx is not None else TTFont(name, path))
                return name
            except Exception:
                continue
        return None
    r0 = reg(cands)
    if not r0:
        try:
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            return ("STSong-Light", "STSong-Light")
        except Exception:
            return None
    b0 = reg(bolds) or r0
    return (r0, b0)


def build_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as cv
    from reportlab.lib.colors import HexColor
    from PIL import Image

    fonts = register_cjk()
    if not fonts:
        raise RuntimeError("本机没有任何可嵌入的中文字体（simsun/msyh/simhei/STSong 全不可用），"
                           "拒绝生成豆腐块 PDF")
    F, FB = fonts
    print("  中文字体：%s（粗体 %s）" % (F, FB))

    os.makedirs(OUT, exist_ok=True)
    # 印刷文件本体随包交付：工厂拿不到仓库，只给他们仓库路径等于没给。
    art_dir = os.path.join(OUT, "artwork")
    shutil.rmtree(art_dir, ignore_errors=True)
    os.makedirs(art_dir, exist_ok=True)
    ink = HexColor("#1A1409")
    dim = HexColor("#6B5F52")
    acc = HexColor("#C9A227")
    warn = HexColor("#D94331")
    W, H = A4

    def wrap(c, text, x, y, width, size=9, lh=4.6 * mm):
        c.setFont(F, size)
        c.setFillColor(ink)
        parts = re.split(r"(?<=[ \-/])", text)
        line = ""
        for wd in parts:
            t = line + wd
            if c.stringWidth(t, F, size) > width:
                c.drawString(x, y, line.strip())
                y -= lh
                line = wd
            else:
                line = t
        if line.strip():
            c.drawString(x, y, line.strip())
            y -= lh
        return y

    made = []
    for it in ITEMS:
        path = os.path.join(OUT, "proof-%s.pdf" % it["id"])
        c = cv.Canvas(path, pagesize=A4)
        c.setTitle("Donggu Phoenix proof pack - %s" % it["id"])
        c.setFillColor(ink)
        c.setFont(FB, 15)
        c.drawString(18 * mm, H - 20 * mm, "打样规格卡 · %s (%s)" % (it["cn"], it["id"]))
        c.setFont(F, 8)
        c.setFillColor(dim)
        c.drawString(18 * mm, H - 25.5 * mm,
                     "donggu-phoenix / %s · %s · print at 100%% (verify with the 100mm ruler)"
                     % (it["id"], datetime.date.today().isoformat()))
        c.setStrokeColor(acc)
        c.setLineWidth(1.2)
        c.line(18 * mm, H - 29 * mm, W - 18 * mm, H - 29 * mm)

        y = H - 38 * mm
        for k, v in [("成品尺寸", it["cut"]), ("出血/咬口", it["bleed"]),
                     ("材质", it["material"]), ("工艺", it["process"]),
                     ("印刷文件", it["art"]), ("用图说明", it["art_note"]),
                     ("数量", it["qty"])]:
            c.setFont(FB, 9)
            c.setFillColor(acc)
            c.drawString(18 * mm, y, k)
            y = wrap(c, v, 46 * mm, y, W - 64 * mm)
            y -= 1.4 * mm

        c.setFont(FB, 9)
        c.setFillColor(warn)
        c.drawString(18 * mm, y, "验收点（回样逐条勾）")
        y -= 5.4 * mm
        for i, a in enumerate(it["accept"], 1):
            c.setFont(F, 9)
            c.setFillColor(ink)
            c.rect(18 * mm, y - 1.3 * mm, 3.4 * mm, 3.4 * mm, stroke=1, fill=0)
            y = wrap(c, "%d. %s" % (i, a), 24 * mm, y, W - 42 * mm)

        y -= 7 * mm
        c.setStrokeColor(ink)
        c.setLineWidth(0.8)
        x0 = 18 * mm
        c.line(x0, y, x0 + 100 * mm, y)
        for i in range(11):
            h = 3 * mm if i % 5 == 0 else 1.8 * mm
            c.line(x0 + i * 10 * mm, y, x0 + i * 10 * mm, y + h)
        c.setFont(F, 7.5)
        c.setFillColor(dim)
        c.drawString(x0 + 103 * mm, y - 1 * mm, "100 mm 实物比例尺")

        mock = os.path.join(BASE, "merch", "mock", "mock-%s.png" % it["id"])
        if os.path.exists(mock):
            iw, ih = Image.open(mock).size
            s = min(60 * mm / iw, 60 * mm / ih)
            c.drawImage(mock, W - 18 * mm - iw * s, max(24 * mm, y - 66 * mm - ih * s),
                        iw * s, ih * s, mask='auto')
            c.setFont(F, 7)
            c.setFillColor(dim)
            c.drawString(W - 18 * mm - iw * s, max(20 * mm, y - 68 * mm - ih * s),
                         "参照效果图（渲染，非印刷文件）")

        art_src = os.path.join(BASE, it["art"].replace("/", os.sep))
        art_name = "%s-%s" % (it["id"], os.path.basename(it["art"]))
        shutil.copy2(art_src, os.path.join(art_dir, art_name))
        c.setFont(F, 7)
        c.setFillColor(dim)
        c.drawString(18 * mm, 16 * mm,
                     "印刷文件本体已随包交付：artwork/%s（无需另行索取）" % art_name)
        c.drawString(18 * mm, 12 * mm,
                     "畲·凤鸣东固 · 薪火寰行实践团 · 本页由 tools/make_proof_pack.py 生成，"
                     "改规格请改脚本与 culture.js，勿手改 PDF")
        c.showPage()
        c.save()
        made.append((path, os.path.getsize(path)))

    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write("# 文创打样文件包\n\n")
        f.write("> 由 tools/make_proof_pack.py 生成；规格事实来源 = site/assets/data/culture.js。\n")
        f.write("> 打印后先用页底 100mm 比例尺校验未被缩放，再发厂。\n\n")
        for it in ITEMS:
            f.write("- %s（proof-%s.pdf）：%s · %s\n" % (it["cn"], it["id"], it["cut"], it["material"]))
        f.write("\n## 印刷文件本体（已随包拷入 artwork/，工厂无需访问仓库）\n\n")
        for it in ITEMS:
            f.write("- artwork/%s-%s ← 仓库 %s\n"
                    % (it["id"], os.path.basename(it["art"]), it["art"]))
        f.write("\n## 回样后怎么替换线上图\n\n")
        f.write("    python tools/replace_merch_photo.py badge <实拍文件>\n")
        f.write("    python tools/replace_merch_photo.py --all      # 按 merch/shot/ 命名批量\n")
        f.write("\n实拍原件请存 merch/shot/<id>.<ext>，脚本会归档、缩放、编码、生成 -340 小档并跑门禁。\n")
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    bad = check_specs()
    if bad:
        print("RESULT: FAIL  规格与页面数据不同源：")
        for b in bad:
            print("  -", b)
        return 1
    print("[PASS] 规格对账：3 件与 culture.js 尺寸/品名一致，印刷文件均在位")
    if args.check:
        return 0
    for p, sz in build_pdf():
        print("  生成 %s  %.0fKB" % (os.path.relpath(p, BASE), sz / 1024))
    print("RESULT: PASS  打样包已生成于 merch/proof/（不入部署面）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
