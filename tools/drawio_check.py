"""drawio 图自查（配套 docs/DrawIO绘图规范.md）。

用法：
    draw.io --export --format svg -o /tmp/x.svg 图.drawio
    python3 drawio_check.py 图.drawio /tmp/x.svg [--containers id1,id2] [--only 前缀1,前缀2]

查 8 项（前 5 项是精确计算，后 3 项是按字宽估算，报出来的要放大看图确认）：
  1 斜线                 2 线穿模块框（容器框除外）   3 线压文字框
  4 框重叠               5 悬空引用（source/target/parent 指向不存在的单元）
  6 线上标签压线/压框/压字  7 线上标签互相重叠          8 框里的字放不下
"""
import html
import re
import sys

args = sys.argv[1:]
drawio_path, svg_path = args[0], args[1]
containers = {"execute", "lp", "sp", "panel", "legend", "fp"}
only = None
if "--containers" in args:
    containers = set(args[args.index("--containers") + 1].split(","))
if "--only" in args:
    only = tuple(args[args.index("--only") + 1].split(","))

model = open(drawio_path, encoding="utf-8").read()
svg = open(svg_path, encoding="utf-8").read()


# ---------------- 模型 ----------------
def attr(s, k):
    m = re.search(r'\b%s="([^"]*)"' % k, s)
    return html.unescape(m.group(1)) if m else ""


cells = {}
for m in re.finditer(r"<mxCell (.*?)(?:/>|>(.*?)</mxCell>)", model, flags=re.S):
    a, inner = m.group(1), m.group(2) or ""
    g = re.search(r"<mxGeometry ([^>]*?)/?>", inner)
    geo = {}
    if g and 'relative="1"' not in g.group(1):
        geo = {k: float(v) for k, v in re.findall(r'\b(x|y|width|height)="([-\d.]+)"', g.group(1))}
    cells[attr(a, "id")] = dict(edge=attr(a, "edge") == "1", style=attr(a, "style"), value=attr(a, "value"),
                                src=attr(a, "source"), tgt=attr(a, "target"), parent=attr(a, "parent"), geo=geo)

# ---------------- SVG ----------------
groups = {}
for m in re.finditer(r'<g data-cell-id="([^"]+)">(.*?)(?=<g data-cell-id=|</svg>)', svg, flags=re.S):
    groups.setdefault(m.group(1), m.group(2))

boxes, texts, lines, labels = {}, {}, {}, []
for cid, body in groups.items():
    c = cells.get(cid)
    if not c:
        continue
    if c["edge"]:
        p = re.search(r'<path d="([^"]+)" fill="none"', body)
        if p:
            lines[cid] = [tuple(map(float, xy)) for xy in re.findall(r"[ML] ([-\d.]+) ([-\d.]+)", p.group(1))]
        continue
    r = re.search(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"', body)
    if r and not c["style"].startswith("text;") and "ellipse" not in c["style"]:
        boxes[cid] = tuple(map(float, r.groups()))

# SVG 相对模型的平移：找一个有 rect 的普通框标定
dx = dy = 0.0
for cid, b in boxes.items():
    g = cells[cid]["geo"]
    if g and "width" in g:
        dx, dy = b[0] - g.get("x", 0), b[1] - g.get("y", 0)
        break

for cid, c in cells.items():
    st, g = c["style"], c["geo"]
    if c["edge"] or not g or "width" not in g:
        continue
    bb = (g.get("x", 0) + dx, g.get("y", 0) + dy, g["width"], g.get("height", 0))
    if st.startswith("text;"):
        texts[cid] = bb
    elif cid not in boxes and "shape=" in st and "ellipse" not in st and cid in groups:
        boxes[cid] = bb   # 梯形等非矩形：SVG 里是 <path>，用模型外框


# ---------------- 字宽估算 ----------------
def char_w(ch, fs):
    o = ord(ch)
    if o >= 0x2E80:
        return fs
    if ch in " ":
        return 0.28 * fs
    if ch in "/.,:;|!'()[]{}ijl-":
        return 0.32 * fs
    if ch.isupper() or ch in "mw@%#&":
        return 0.68 * fs
    return 0.56 * fs


def text_lines(v):
    v = re.sub(r"(?i)<br\s*/?>|</div>\s*<div[^>]*>|</?div[^>]*>", "\n", v)
    v = html.unescape(re.sub(r"<[^>]+>", "", v))
    return [ln.strip() for ln in v.split("\n") if ln.strip()]


def font_size(style, value):
    fs = [float(x) for x in re.findall(r"font-size:\s*([\d.]+)px", value)]
    m = re.search(r"fontSize=([\d.]+)", style)
    base = float(m.group(1)) if m else 12.0
    return max(fs) if fs else base


def est_size(style, value):
    fs = font_size(style, value)
    bold = 1.08 if ("<b>" in value or "fontStyle=1" in style) else 1.0
    lns = text_lines(value)
    if not lns:
        return 0.0, 0.0
    w = max(sum(char_w(ch, fs) for ch in ln) for ln in lns) * bold
    return w, len(lns) * fs * 1.2


# 线上标签：SVG 里 1px×1px 的锚点 div
for cid, body in groups.items():
    c = cells.get(cid)
    if not c:
        continue
    is_edge_label = c["edge"] or "edgeLabel" in c["style"]
    if not is_edge_label or not text_lines(c["value"]):
        continue
    d = re.search(r'width: 1px; height: 1px; padding-top: (-?[\d.]+)px; margin-left: (-?[\d.]+)px', body)
    ai = re.search(r"align-items: unsafe ([\w-]+)", body)
    if not d:
        continue
    y, x = float(d.group(1)), float(d.group(2))
    w, h = est_size(c["style"], c["value"])
    va = ai.group(1) if ai else "center"
    top = y - h if va == "flex-end" else (y if va == "flex-start" else y - h / 2)
    owner = c["parent"] if not c["edge"] else cid
    labels.append((cid, owner, (x - w / 2, top, w, h)))


# ---------------- 几何 ----------------
def seg_hits_box(p, q, box, pad=1.0):
    x, y, w, h = box
    x0, y0, x1, y1 = x + pad, y + pad, x + w - pad, y + h - pad
    (ax, ay), (bx, by) = p, q
    if abs(ay - by) < 0.5:
        return y0 < ay < y1 and max(min(ax, bx), x0) < min(max(ax, bx), x1)
    if abs(ax - bx) < 0.5:
        return x0 < ax < x1 and max(min(ay, by), y0) < min(max(ay, by), y1)
    return False


def boxes_overlap(a, b, pad=1.0):
    return (a[0] + pad < b[0] + b[2] and b[0] + pad < a[0] + a[2] and
            a[1] + pad < b[1] + b[3] and b[1] + pad < a[1] + a[3])


def wanted(*ids):
    return only is None or any(i and i.startswith(only) for i in ids)


out = {k: [] for k in ["斜线", "穿模块框", "压文字框", "框重叠", "悬空引用", "标签压线/框/字", "标签互相重叠", "字放不下"]}
for eid, pts in lines.items():
    c = cells[eid]
    for p, q in zip(pts, pts[1:]):
        if abs(p[0] - q[0]) > 0.5 and abs(p[1] - q[1]) > 0.5 and wanted(eid):
            out["斜线"].append((eid, p, q))
        for bid, box in boxes.items():
            if bid not in containers and bid not in (c["src"], c["tgt"]) and seg_hits_box(p, q, box) and wanted(eid, bid):
                out["穿模块框"].append((eid, bid))
        for tid, tb in texts.items():
            if seg_hits_box(p, q, tb, pad=2.0) and wanted(eid, tid):
                out["压文字框"].append((eid, tid))

ids = [i for i in boxes if i not in containers]
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        if boxes_overlap(boxes[a], boxes[b]) and wanted(a, b):
            out["框重叠"].append((a, b))

known = set(cells)
for cid, c in cells.items():
    for k in ("src", "tgt", "parent"):
        if c[k] and c[k] not in known:
            out["悬空引用"].append((cid, k, c[k]))

for lid, owner, lb in labels:
    for eid, pts in lines.items():
        if eid == owner:
            continue
        for p, q in zip(pts, pts[1:]):
            if seg_hits_box(p, q, lb, pad=1.0) and wanted(lid, eid):
                out["标签压线/框/字"].append((lid, "线", eid))
                break
    for bid, box in boxes.items():
        if bid not in containers and boxes_overlap(lb, box) and wanted(lid, bid):
            out["标签压线/框/字"].append((lid, "框", bid))
    for tid, tb in texts.items():
        if boxes_overlap(lb, tb, pad=2.0) and wanted(lid, tid):
            out["标签压线/框/字"].append((lid, "字", tid))
for i, (a, _, ab) in enumerate(labels):
    for b, _, bb in labels[i + 1:]:
        if boxes_overlap(ab, bb) and wanted(a, b):
            out["标签互相重叠"].append((a, b))

def wrapped(style, value, avail):
    """whiteSpace=wrap：按空格断词（中文可在任意字间断），返回 (最长不可断片段宽, 折行后总高)"""
    fs = font_size(style, value)
    bold = 1.08 if ("<b>" in value or "fontStyle=1" in style) else 1.0
    widest, rows = 0.0, 0
    for ln in text_lines(value):
        for piece in re.split(r"(\s+|[\u2e80-\uffff])", ln):
            if piece and not piece.isspace():
                widest = max(widest, sum(char_w(ch, fs) for ch in piece) * bold)
        lw = sum(char_w(ch, fs) for ch in ln) * bold
        rows += max(1, -(-int(lw) // max(1, int(avail))))
    return widest, rows * fs * 1.2


for cid, c in cells.items():
    st, g = c["style"], c["geo"]
    if c["edge"] or not g or "width" not in g or not text_lines(c["value"]) or st.startswith("text;"):
        continue
    avail, avail_h = g["width"] - 4, g.get("height", 0)
    m = re.search(r"size=([\d.]+)", st)
    if "shape=trapezoid" in st and m:
        s = float(m.group(1))
        if "direction=south" in st or "direction=north" in st:
            avail_h -= 2 * s          # 竖梯形：斜的是上下两条边，宽度不变、高度变窄
        else:
            avail -= 2 * s            # 横梯形：斜的是左右两条边
    if "whiteSpace=wrap" in st:
        w, h = wrapped(st, c["value"], avail)
    else:
        w, h = est_size(st, c["value"])
    if (w > avail * 1.05 or h > avail_h * 1.05) and wanted(cid):
        out["字放不下"].append((cid, f"估计 {w:.0f}×{h:.0f}，可用 {avail:.0f}×{avail_h:.0f}"))

print(f"edges={len(lines)} boxes={len(boxes)} texts={len(texts)} labels={len(labels)} offset=({dx:+.0f},{dy:+.0f})")
bad = 0
for k, v in out.items():
    print(f"{k}: {len(v)}")
    for item in v:
        print("   ", item)
    bad += len(v)
sys.exit(1 if bad else 0)
