"""drawio 补充自查（配套 docs/DrawIO绘图规范.md 第五节），查 drawio_check.py 查不到的：
  字压字、字压框、线穿编号圆、箭头终点 / 起点悬空、线与线交叉 / 共线重叠、中英之间多空格

用法：python3 drawio_deep_check.py 图.drawio [--containers id1,id2,...]
  - 多页文件逐页报告；--containers 给出容器框 id（不传就按样式猜：无填充、虚线、arcSize≤3）
  - 文字 id 以「某块 id + _」开头的，算这个块自己的标签，不报字压框
"""
import html, re, sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
given = set(sys.argv[sys.argv.index("--containers") + 1].split(",")) if "--containers" in sys.argv else None
root = ET.parse(path).getroot()

def strip(v):
    v = re.sub(r"(?i)<br\s*/?>", "\n", v or "")
    return [ln.strip() for ln in html.unescape(re.sub(r"<[^>]+>", "", v)).split("\n") if ln.strip()]

def sty(s, k, d=None):
    m = re.search(r"(?:^|;)%s=([^;]*)" % re.escape(k), s or "")
    return m.group(1) if m else d

def est_w(line, size, mono, bold):
    w = 0
    for ch in line:
        if ord(ch) >= 0x2E80: w += size
        elif mono: w += 0.61 * size
        elif ch in "il.,:;|!'()[]{}": w += 0.3 * size
        elif ch.isupper(): w += 0.68 * size
        else: w += 0.55 * size
    return w * (1.08 if bold else 1)

def overlap(a, b, pad=1):
    return a[0] + pad < b[0] + b[2] and b[0] + pad < a[0] + a[2] and a[1] + pad < b[1] + b[3] and b[1] + pad < a[1] + a[3]

def seg_hits(p, q, box, pad=1):
    x, y, w, h = box
    (ax, ay), (bx, by) = p, q
    if abs(ay - by) < .5:
        return y + pad < ay < y + h - pad and max(min(ax, bx), x + pad) < min(max(ax, bx), x + w - pad)
    return x + pad < ax < x + w - pad and max(min(ay, by), y + pad) < min(max(ay, by), y + h - pad)

def on_border(pt, box, tol=2.5):
    x, y, w, h = box
    px, py = pt
    inside_x = x - tol <= px <= x + w + tol
    inside_y = y - tol <= py <= y + h + tol
    return inside_x and inside_y and (abs(px - x) <= tol or abs(px - x - w) <= tol or abs(py - y) <= tol or abs(py - y - h) <= tol
                                      or (x <= px <= x + w and y <= py <= y + h))

CJK = r"[一-鿿]"
total = 0
for d in root.iter("diagram"):
    name = d.get("name")
    verts, edges = [], []
    for el in d.iter():
        if el.tag not in ("mxCell", "UserObject"):
            continue
        cell = el if el.tag == "mxCell" else el.find("mxCell")
        cid = el.get("id") if el.tag == "UserObject" else cell.get("id")
        if el.tag == "mxCell" and el in [u.find("mxCell") for u in d.iter("UserObject")]:
            continue
        val = el.get("label") if el.tag == "UserObject" else cell.get("value")
        st = cell.get("style") or ""
        g = cell.find("mxGeometry")
        if cell.get("vertex") == "1":
            box = tuple(float(g.get(k)) for k in ("x", "y", "width", "height"))
            verts.append(dict(id=cid, box=box, style=st, val=val or ""))
        elif cell.get("edge") == "1":
            pts = [(float(p.get("x")), float(p.get("y"))) for p in g.iter("mxPoint")]
            sp = [p for p in g.iter("mxPoint") if p.get("as") == "sourcePoint"][0]
            tp = [p for p in g.iter("mxPoint") if p.get("as") == "targetPoint"][0]
            mids = [(float(p.get("x")), float(p.get("y"))) for p in g.iter("mxPoint") if p.get("as") is None]
            path_pts = [(float(sp.get("x")), float(sp.get("y")))] + mids + [(float(tp.get("x")), float(tp.get("y")))]
            edges.append(dict(id=cid, pts=path_pts, style=st, arrow=sty(st, "endArrow") != "none"))
    issues = []
    texts, blocks, markers, dots, containers = [], [], [], [], []
    for v in verts:
        st = v["style"]
        if st.startswith("text;"):
            lines = strip(v["val"])
            if not lines:
                continue
            size = float(sty(st, "fontSize", 12))
            fs = [float(x) for x in re.findall(r"font-size:\s*([\d.]+)px", html.unescape(v["val"]))]
            size = max([size] + fs)
            mono = sty(st, "fontFamily") == "Menlo"
            bold = sty(st, "fontStyle") == "1" or "<b>" in html.unescape(v["val"])
            w = max(est_w(l, size, mono, bold) for l in lines)
            h = len(lines) * size * 1.2
            x, y, bw, bh = v["box"]
            al = sty(st, "align", "left")
            tx = x if al == "left" else (x + bw - w if al == "right" else x + (bw - w) / 2)
            va = sty(st, "verticalAlign", "middle")
            ty = y if va == "top" else y + (bh - h) / 2
            if sty(st, "whiteSpace") == "wrap":
                tx, w, ty, h = x, bw, y, bh
            texts.append(dict(id=v["id"], box=(tx, ty, w, h), val=" / ".join(lines)))
        elif st.startswith("ellipse"):
            (markers if v["box"][2] > 10 else dots).append(v)
        elif (v["id"] in given) if given is not None else (
                "fillColor=none" in st or "dashed=1" in st or "arcSize=2;" in st or "arcSize=3;" in st or "arcSize=1;" in st):
            containers.append(v)
        else:
            blocks.append(v)
    # 1 字压字
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if overlap(a["box"], b["box"], 0.5):
                issues.append(("字压字", a["id"], b["id"], a["val"][:24], b["val"][:24]))
    # 2 字压框（文字落进别的块）
    for t in texts:
        for b in blocks + markers:
            if t["id"].startswith(b["id"] + "_"):
                continue
            if overlap(t["box"], b["box"], 1):
                issues.append(("字压框", t["id"], b["id"], t["val"][:24]))
    # 3 线穿编号圆
    for e in edges:
        for p, q in zip(e["pts"], e["pts"][1:]):
            for m in markers:
                if seg_hits(p, q, m["box"], 0):
                    issues.append(("线穿编号圆", e["id"], m["id"]))
    # 4 箭头终点 / 起点悬空
    anchors = [v["box"] for v in blocks + containers + markers] + [t["box"] for t in texts]
    dotpts = [(v["box"][0] + 3.5, v["box"][1] + 3.5) for v in dots]
    def touches(pt):
        if any(abs(pt[0] - dx) < 2 and abs(pt[1] - dy) < 2 for dx, dy in dotpts):
            return True
        if any(on_border(pt, b) for b in anchors):
            return True
        for t in texts:   # 箭头指向标签：终点离标签左/右缘 ≤ 8px
            x, y, w, h = t["box"]
            if y - 3 <= pt[1] <= y + h + 3 and (abs(pt[0] - x) <= 8 or abs(pt[0] - x - w) <= 8):
                return True
            if x - 3 <= pt[0] <= x + w + 3 and (abs(pt[1] - y) <= 8 or abs(pt[1] - y - h) <= 8):
                return True
        for e in edges:   # 接在别的线上（汇合点）
            for p, q in zip(e["pts"], e["pts"][1:]):
                if abs(p[0] - q[0]) < .5 and abs(pt[0] - p[0]) < 1 and min(p[1], q[1]) - 1 <= pt[1] <= max(p[1], q[1]) + 1:
                    return True
                if abs(p[1] - q[1]) < .5 and abs(pt[1] - p[1]) < 1 and min(p[0], q[0]) - 1 <= pt[0] <= max(p[0], q[0]) + 1:
                    return True
        return False
    for e in edges:
        if "lg_e_" in e["id"]:
            continue
        if not touches(e["pts"][-1]):
            issues.append(("终点悬空", e["id"], e["pts"][-1]))
        if not touches(e["pts"][0]):
            issues.append(("起点悬空", e["id"], e["pts"][0]))
    # 5 线与线交叉（垂直相交，交点不在端点 / 汇合点）
    segs = [(e["id"], p, q) for e in edges if "lg_e_" not in e["id"] for p, q in zip(e["pts"], e["pts"][1:])]
    for i, (ia, p1, q1) in enumerate(segs):
        for ib, p2, q2 in segs[i + 1:]:
            if ia == ib:
                continue
            h1 = abs(p1[1] - q1[1]) < .5
            h2 = abs(p2[1] - q2[1]) < .5
            if h1 == h2:
                # 共线重叠
                if h1 and abs(p1[1] - p2[1]) < .5:
                    lo, hi = max(min(p1[0], q1[0]), min(p2[0], q2[0])), min(max(p1[0], q1[0]), max(p2[0], q2[0]))
                    if hi - lo > 1:
                        issues.append(("线重叠", ia, ib, round(lo), round(hi)))
                elif not h1 and abs(p1[0] - p2[0]) < .5:
                    lo, hi = max(min(p1[1], q1[1]), min(p2[1], q2[1])), min(max(p1[1], q1[1]), max(p2[1], q2[1]))
                    if hi - lo > 1:
                        issues.append(("线重叠", ia, ib, round(lo), round(hi)))
                continue
            hs, vs = ((p1, q1), (p2, q2)) if h1 else ((p2, q2), (p1, q1))
            y = hs[0][1]; x = vs[0][0]
            if min(hs[0][0], hs[1][0]) + 1 < x < max(hs[0][0], hs[1][0]) - 1 and min(vs[0][1], vs[1][1]) + 1 < y < max(vs[0][1], vs[1][1]) - 1:
                issues.append(("线交叉", ia, ib, (x, y)))
    # 6 中英之间空格
    for v in verts:
        for ln in strip(v.get("val") if v.get("val") else ""):
            if re.search(CJK + r" [A-Za-z0-9]|[A-Za-z0-9] " + CJK, ln):
                issues.append(("中英空格", v["id"], ln))
    print(f"=== {name}: texts={len(texts)} blocks={len(blocks)} markers={len(markers)} edges={len(edges)} issues={len(issues)}")
    for it in issues:
        print("   ", it)
    total += len(issues)
print("TOTAL", total)
sys.exit(1 if total else 0)
