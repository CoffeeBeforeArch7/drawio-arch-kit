"""深色演示风格 drawio 生成库（规范：docs/DrawIO绘图规范.md 第二节）。

起步：python3 tools/new_diagram.py <输出文件夹>，会把本文件和两个自查脚本复制过去，并放一个能直接跑的
gen_drawio.py。之后按设计写 pages_*.py（或直接改 gen_drawio.py）：

    from drawio_kit import *

    VIEWS = ["Overview", "Datapath"]

    def page1():
        p = Page("p1", "1 · Overview")
        header(p, "名字 · 一句话说明", "关键参数 · 关键参数")
        left_column(p, 1, VIEWS)
        decisions(p, 1656, 92, [(1, "Title", "第一行\\n第二行")])
        p.block("alu", 900, 400, 80, 40, "datapath", "ALU")
        p.edge("e1", [(800, 420), (900, 420)], "data")
        return p

    if __name__ == "__main__":
        run_all([page1], Path(__file__).with_name("xxx.drawio"), sys.argv)

    python3 gen_drawio.py --export --check     # 写 .drawio、导出每页 PNG、跑两个自查脚本

约定：所有单元 parent="1"、绝对坐标；连线是带绝对端点的自由线，只走水平 / 竖直段；
     颜色只按功能取（CAT 给块，LINE 给线），含义写进 design.md 的「图例约定」。
范例：examples/mp_pipeline/（4 页成图 + 生成脚本）

换电脑可用环境变量覆盖：DRAWIO（draw.io 可执行文件）、DRAWIO_TOOLS（自查脚本所在目录，默认本文件旁边）、
DRAWIO_SANS / DRAWIO_MONO（字体）、DRAWIO_AUTHOR（署名）。
"""
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _find_drawio():
    if os.environ.get("DRAWIO"):
        return os.environ["DRAWIO"]
    for c in ("/Applications/draw.io.app/Contents/MacOS/draw.io", r"C:\Program Files\draw.io\draw.io.exe",
              shutil.which("drawio"), shutil.which("draw.io")):
        if c and Path(c).exists():
            return str(c)
    return "drawio"   # 找不到时导出会报错：装 draw.io Desktop，或设环境变量 DRAWIO


DRAWIO = _find_drawio()
def _find_checkers():
    """自查脚本目录：环境变量 → 本文件旁边 → 旁边的 drawio-check/（本机 toolbox 的布局）"""
    here = Path(__file__).resolve().parent
    for d in (os.environ.get("DRAWIO_TOOLS"), here, here.parent / "drawio-check"):
        if d and (Path(d) / "drawio_check.py").exists():
            return Path(d)
    return here


CHECKERS = _find_checkers()
AUTHOR = os.environ.get("DRAWIO_AUTHOR", "by Pinxu Wang")


def drawio_cmd(*args):
    """draw.io 命令行；Linux 没有图形界面时自动套 xvfb-run，并加 --no-sandbox（容器里常以 root 跑）"""
    cmd = [DRAWIO, *args]
    if sys.platform.startswith("linux"):
        cmd.insert(1, "--no-sandbox")
        if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a", *cmd]
    return cmd

BG = "#14161b"
T1, T2, T3 = "#e8eaed", "#a7afba", "#7a828e"   # 主字、次字、弱字
PANEL = ("#191c22", "#2c313b")
CONT = ("#1a1d24", "#3b414d")
CAT = {  # 块：填充, 描边
    "storage": ("#261e3c", "#8e72e0"),
    "datapath": ("#13253a", "#4f93e0"),
    "control": ("#2d240f", "#d4a03a"),
    "recovery": ("#34181b", "#e0606a"),
    "commit": ("#122a1e", "#46b97e"),
    "external": ("#1f232b", "#7d8696"),
}
LINE = {  # 线：颜色, 线宽, 虚线
    "data": ("#9f87f2", 2.4, False),
    "addr": ("#5aa2f0", 1.6, False),
    "ctrl": ("#e0aa3e", 1.6, False),
    "fwd": ("#34c3cc", 2.2, False),
    "flush": ("#ec6b74", 1.8, True),
    "commit": ("#4fc488", 2.2, False),
}
SANS = os.environ.get("DRAWIO_SANS", "Helvetica")
MONO = os.environ.get("DRAWIO_MONO", "Menlo")

# 图例默认文字；换了领域（cache、NPU…）就按功能改名，颜色含义不变
LEGEND_BOX = [("storage", "Storage · regs / buffers"), ("datapath", "Datapath · ALU / mux"),
              ("control", "Control · decode / stall"), ("recovery", "Recovery · flush"),
              ("commit", "Commit · writeback"), ("external", "External unit")]
LEGEND_LINE = [("data", "Data"), ("addr", "Address / PC"), ("ctrl", "Control"),
               ("fwd", "Forwarding / bypass"), ("flush", "Flush / bubble"), ("commit", "Writeback")]


def esc(s):
    return html.escape(s, quote=True)


def font(size, color, mono=False, bold=False):
    return (f"fontFamily={MONO if mono else SANS};fontSize={size};fontColor={color};"
            + ("fontStyle=1;" if bold else ""))


class Page:
    def __init__(self, pid, name, w=1920, h=1080):
        self.pid, self.name, self.w, self.h = pid, name, w, h
        self.cells, self.ids, self.containers = [], set(), []

    def _id(self, cid):
        assert cid not in self.ids, cid
        self.ids.add(cid)
        return f"{self.pid}_{cid}"

    def vertex(self, cid, x, y, w, h, value, style):
        self.cells.append(
            f'<mxCell id="{self._id(cid)}" parent="1" style="{style}" value="{esc(value)}" vertex="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')

    def link_vertex(self, cid, x, y, w, h, value, style, page_id):
        """点一下跳到别的页（draw.io 的页面链接）"""
        self.cells.append(
            f'<UserObject id="{self._id(cid)}" label="{esc(value)}" link="data:page/id,{page_id}">'
            f'<mxCell parent="1" style="{style}" vertex="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell></UserObject>')

    def text(self, cid, x, y, w, h, value, size=11, color=T2, mono=False, bold=False, align="left"):
        self.vertex(cid, x, y, w, h, value,
                    f"text;html=1;align={align};verticalAlign=middle;whiteSpace=nowrap;spacing=0;"
                    + font(size, color, mono, bold))

    def block(self, cid, x, y, w, h, cat, title, sub=None, size=12, mono=True):
        fill, stroke = CAT[cat]
        v = f"<b>{esc(title)}</b>"
        if sub:
            v += f'<br><font style="font-size:10px" color="{T2}">{esc(sub)}</font>'
        self.vertex(cid, x, y, w, h, v,
                    f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                    f"strokeWidth=1.2;" + font(size, T1, mono))

    def container(self, cid, x, y, w, h, title, cn, module):
        """带标题的容器：大字英文名 + 中文小字 + 等宽模块名"""
        fill, stroke = CONT
        self.vertex(cid, x, y, w, h, "",
                    f"rounded=1;arcSize=3;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;")
        self.containers.append(cid)
        self.text(cid + "_t", x + 10, y + 6, 90, 20,
                  f'<b>{esc(title)}</b>&nbsp;&nbsp;<font style="font-size:11px" color="{T2}">{esc(cn)}</font>',
                  size=16, color=T1)
        self.text(cid + "_m", x + 10, y + 26, round(6.2 * len(module)) + 4, 14, module, size=10, color=T3, mono=True)

    def bar(self, cid, x, y, w, h, name):
        """竖条：流水寄存器一类，名字写在上部"""
        fill, stroke = CAT["storage"]
        self.vertex(cid, x, y, w, h, "",
                    f"rounded=1;arcSize=8;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.4;")
        self.text(cid + "_n", x, y + 12, w, 16, name, size=10, color=T1, mono=True, align="center")

    def trap(self, cid, x, y, w, h, direction, label, cat="datapath", size=12):
        """mux：east=宽边在下，west=宽边在上，south=宽边在左，north=宽边在右；数据从宽边进"""
        fill, stroke = CAT[cat]
        self.vertex(cid, x, y, w, h, f"<b>{esc(label)}</b>",
                    f"shape=trapezoid;perimeter=trapezoidPerimeter;fixedSize=1;size={size};direction={direction};"
                    f"whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;"
                    + font(11, T1, True))

    def dot(self, cid, x, y, kind):
        """分叉点，颜色跟线"""
        self.vertex(cid, x - 3.5, y - 3.5, 7, 7, "", f"ellipse;html=1;fillColor={LINE[kind][0]};strokeColor=none;")

    def marker(self, cid, x, y, n):
        """编号圆，跟右栏「关键设计决策」一一对应"""
        self.vertex(cid, x, y, 22, 22, str(n),
                    "ellipse;html=1;fillColor=#e8eaed;strokeColor=none;" + font(12, BG, bold=True))

    def boundary(self, cid, x, y, w, h, name):
        """模块边界：虚线框，框角写模块名"""
        self.vertex(cid, x, y, w, h, "",
                    "rounded=1;arcSize=1;html=1;fillColor=none;strokeColor=#4a515e;strokeWidth=1.2;"
                    "dashed=1;dashPattern=8 5;")
        self.containers.append(cid)
        self.text(cid + "_t", x + 14, y + 6, round(7.5 * len(name)) + 4, 16, name, size=12, color=T3, mono=True)

    def panel(self, cid, x, y, w, h, dashed=False):
        fill, stroke = PANEL
        self.vertex(cid, x, y, w, h, "",
                    f"rounded=1;arcSize=2;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1;"
                    + ("dashed=1;dashPattern=4 4;" if dashed else ""))
        self.containers.append(cid)

    def edge(self, cid, pts, kind, arrow=True, end_size=6):
        """pts：起点、拐点…、终点（绝对坐标，相邻两点必须同 x 或同 y）"""
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            assert x1 == x2 or y1 == y2, (cid, pts)
        color, width, dashed = LINE[kind]
        style = (f"edgeStyle=none;rounded=0;html=1;strokeColor={color};strokeWidth={width};"
                 f"endArrow={'block' if arrow else 'none'};endFill=1;endSize={end_size};")
        if dashed:
            style += "dashed=1;dashPattern=6 4;"
        (sx, sy), (tx, ty) = pts[0], pts[-1]
        mids = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in pts[1:-1])
        arr = f'<Array as="points">{mids}</Array>' if mids else ""
        self.cells.append(
            f'<mxCell id="{self._id(cid)}" edge="1" parent="1" style="{style}" value="">'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{sx}" y="{sy}" as="sourcePoint"/>'
            f'<mxPoint x="{tx}" y="{ty}" as="targetPoint"/>{arr}</mxGeometry></mxCell>')

    def xml(self):
        return (f'<diagram id="{self.pid}" name="{esc(self.name)}">'
                f'<mxGraphModel dx="{self.w}" dy="{self.h}" grid="0" gridSize="10" guides="1" tooltips="1" '
                f'connect="0" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.w}" '
                f'pageHeight="{self.h}" background="{BG}" adaptiveColors="none" math="0" shadow="0">'
                f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(self.cells)
                + "</root></mxGraphModel></diagram>")


# ====================== 标题、左栏（图例 + 页面导航）、右栏（关键设计决策）======================
def header(p, title, subtitle, author=AUTHOR):
    p.text("title", 24, 14, 900, 34,
           f'<b>{esc(title)}</b>&nbsp;&nbsp;&nbsp;<font style="font-size:15px" color="{T3}">{esc(author)}</font>',
           size=26, color=T1)
    p.text("subtitle", 24, 52, 1400, 20, subtitle, size=13, color=T2)


def section_label(p, cid, x, y, s):
    p.text(cid, x, y, 230, 16, s, size=11, color=T3, bold=True)


def legend(p, x, y, rows_box=LEGEND_BOX, rows_line=LEGEND_LINE, w=230):
    n = len(rows_box) + len(rows_line) + 1
    h = 40 + n * 22 + 6
    p.panel("legend", x, y, w, h, dashed=True)
    section_label(p, "legend_t", x + 12, y + 10, "LEGEND")
    yy = y + 36
    for cat, s in rows_box:
        fill, stroke = CAT[cat]
        p.vertex(f"lg_{cat}", x + 14, yy + 3, 26, 14, "",
                 f"rounded=1;arcSize=20;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;")
        p.text(f"lg_{cat}_t", x + 52, yy, 170, 20, s, size=11, color=T2)
        yy += 22
    for kind, s in rows_line:
        p.edge(f"lg_e_{kind}", [(x + 14, yy + 10), (x + 40, yy + 10)], kind, end_size=5)
        p.text(f"lg_e_{kind}_t", x + 52, yy, 170, 20, s, size=11, color=T2)
        yy += 22
    p.marker("lg_mk", x + 16, yy, 1)
    p.text("lg_mk_t", x + 52, yy + 1, 170, 20, "Key design decision", size=11, color=T2)
    return y + h


def views(p, x, y, current, names, w=230):
    """页面导航；非当前页可点，跳到 id 为 p1、p2… 的页"""
    h = 40 + len(names) * 34
    p.panel("views", x, y, w, h, dashed=True)
    section_label(p, "views_t", x + 12, y + 10, "VIEWS IN THIS FILE")
    for i, name in enumerate(names, 1):
        yy = y + 34 + (i - 1) * 34
        on = i == current
        style = (f"rounded=1;arcSize=12;html=1;align=left;spacingLeft=10;"
                 f"fillColor={'#232833' if on else PANEL[0]};strokeColor={'#c9ced6' if on else '#3b414d'};"
                 + font(11, T1 if on else T2, bold=on))
        label = esc(f"{i} · {name}") + ("" if on else "&nbsp;&nbsp;→")
        if on:
            p.vertex(f"view{i}", x + 12, yy, w - 24, 26, label, style)
        else:
            p.link_vertex(f"view{i}", x + 12, yy, w - 24, 26, label, style, f"p{i}")
    return y + h


def left_column(p, current, names, y=96, **legend_rows):
    yl = legend(p, 24, y, **legend_rows)
    views(p, 24, yl + 18, current, names)


def decisions(p, x, y, items, w=240, h=None, step=112):
    """items: [(编号, 英文标题, 说明)]；说明用 \\n 分成两行，每行别超过约 180px（12px 字）"""
    h = h or 56 + len(items) * step
    p.panel("dec", x, y, w, h)
    section_label(p, "dec_t", x + 16, y + 14, "KEY DESIGN DECISIONS")
    for k, (n, title, desc) in enumerate(items):
        yy = y + 46 + k * step
        p.marker(f"dec{n}", x + 16, yy, n)
        p.text(f"dec{n}_h", x + 46, yy + 1, w - 56, 20, title, size=13, color=T1, bold=True)
        p.vertex(f"dec{n}_d", x + 46, yy + 26, w - 56, 44, "<br>".join(esc(t) for t in desc.split("\n")),
                 "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;spacing=0;" + font(12, T2))


# ====================== 小件：同名标签、门、sel 标注 ======================
def tw(s, size=10):
    """等宽字估宽"""
    return round(len(s) * size * 0.62) + 4


def inp(p, cid, x, y, s, kind, gap=30, size=10):
    """标签在左，箭头指向 (x, y)"""
    color = LINE[kind][0] if kind in ("fwd", "flush", "addr") else T2
    w = tw(s, size)
    p.text(cid, x - gap - w - 4, y - 7, w, 14, s, size=size, color=color, mono=True, align="right")
    p.edge(cid + "_e", [(x - gap, y), (x, y)], kind, end_size=5 if gap >= 20 else 4)


def outp(p, cid, x, y, s, kind, gap=30, size=10):
    """从 (x, y) 向右出箭头，标签在箭头右边"""
    color = LINE[kind][0] if kind in ("fwd", "flush", "addr") else T2
    p.edge(cid + "_e", [(x, y), (x + gap, y)], kind, end_size=5)
    p.text(cid, x + gap + 6, y - 7, tw(s, size), 14, s, size=size, color=color, mono=True)


def gate(p, cid, x, y, w, h, label, cat="control"):
    fill, stroke = CAT[cat]
    p.vertex(cid, x, y, w, h, f"<b>{esc(label)}</b>",
             f"rounded=1;arcSize=12;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;"
             + font(11, T1, True))


def sel(p, cid, cx, y, s, w=None):
    w = w or tw(s)
    p.text(cid, cx - w / 2, y, w, 12, s, size=10, color="#7fb6ff", mono=True, align="center")


# ====================== 生成、导出、自查 ======================
def build(pages, out):
    out.write_text('<mxfile host="Electron" type="device">' + "".join(p.xml() for p in pages) + "</mxfile>",
                   encoding="utf-8")


def export_png(pages, out, scale=2):
    for i in range(1, len(pages) + 1):
        png = out.with_name(f"{out.stem}_p{i}.png")
        subprocess.run(drawio_cmd("--export", "--format", "png", "--scale", str(scale), "--border", "24",
                                  "--page-index", str(i), "-o", str(png), str(out)), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("exported", png.name)


def check(pages):
    """每页单独成文件再查，免得检查脚本把别页的字算进来；两个脚本都跑"""
    with tempfile.TemporaryDirectory() as tmp:
        for i, p in enumerate(pages, 1):
            one = Path(tmp) / f"p{i}.drawio"
            one.write_text('<mxfile host="Electron">' + p.xml() + "</mxfile>", encoding="utf-8")
            svg = Path(tmp) / f"p{i}.svg"
            subprocess.run(drawio_cmd("--export", "--format", "svg", "-o", str(svg), str(one)), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ids = ",".join(f"{p.pid}_{c}" for c in p.containers)
            for script, args in [("drawio_check.py", [str(one), str(svg)]), ("drawio_deep_check.py", [str(one)])]:
                r = subprocess.run([sys.executable, str(CHECKERS / script), *args, "--containers", ids],
                                   capture_output=True, text=True)
                print(f"--- page {i} · {script}\n" + r.stdout)


def run_all(page_funcs, out, argv):
    pages = [f() for f in page_funcs]
    build(pages, out)
    print("wrote", out.name, [p.name for p in pages])
    if "--export" in argv:
        export_png(pages, out)
    if "--check" in argv:
        check(pages)
    return pages
