#!/usr/bin/env python3
"""新建一张图的工作文件夹：复制 drawio_kit.py 和两个自查脚本，放一个能直接跑的 gen_drawio.py 起步模板。

用法：python3 tools/new_diagram.py <输出文件夹>
  例：python3 tools/new_diagram.py ~/proj/diagrams/l1_dcache
然后：cd <输出文件夹> && python3 gen_drawio.py --export --check
文件夹已存在且不是空的就停下（规范第一节：先问用户）。
"""
import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
FILES = ("drawio_kit.py", "drawio_check.py", "drawio_deep_check.py")

TEMPLATE = '''#!/usr/bin/env python3
"""__NAME__ 架构图。python3 gen_drawio.py --export --check
起步模板：一页总览，演示边界框、容器、块、竖条、mux、连线、同名标签、编号和决策栏。
照 design.md 改内容；页数多了就拆成 pages_*.py，每个文件不超过 400 行。
"""
from drawio_kit import *  # noqa: F401,F403

TITLE = "__NAME__ · 一句话说明这个设计"
VIEWS = ["Overview"]
DECISIONS = [
    (1, "Decision title", "做了什么\\n为什么，代价是什么"),
]


def page1():
    p = Page("p1", "1 · Overview")
    header(p, TITLE, "关键参数 · 关键参数 · 关键参数")
    left_column(p, 1, VIEWS)
    decisions(p, 1656, 92, DECISIONS)

    p.boundary("top", 276, 196, 1344, 420, "top_module")
    p.container("A", 300, 250, 360, 330, "A", "前级", "stage_a")
    p.block("x", 380, 380, 140, 40, "storage", "x_reg")
    inp(p, "x_in", 380, 400, "in_data", "data", gap=30)
    p.bar("r", 700, 280, 64, 260, "pipe_reg")
    p.edge("x_o", [(520, 400), (700, 400)], "data")

    p.container("B", 790, 250, 440, 330, "B", "后级", "stage_b")
    p.trap("mux", 850, 354, 50, 92, "south", "", size=10)
    p.edge("r_o", [(764, 377), (850, 377)], "data")
    inp(p, "imm", 850, 423, "imm", "data", gap=24)
    sel(p, "mux_s", 875, 450, "sel = op_sel")
    p.block("alu", 960, 370, 90, 60, "datapath", "ALU", "op")
    p.edge("mux_o", [(900, 400), (960, 400)], "data")
    p.marker("mk1", 994, 336, 1)
    outp(p, "alu_o", 1050, 400, "result", "data", gap=40)
    return p


if __name__ == "__main__":
    run_all([page1], Path(__file__).with_name("__NAME__.drawio"), sys.argv)
'''


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    out = Path(sys.argv[1]).expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} 已存在且不是空的：先确认要不要用它（规范第一节）")
    out.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy2(TOOLS / f, out / f)
    (out / "gen_drawio.py").write_text(TEMPLATE.replace("__NAME__", out.name), encoding="utf-8")
    print("created", out)
    print("next:   cd", out, "&& python3 gen_drawio.py --export --check")


if __name__ == "__main__":
    main()
