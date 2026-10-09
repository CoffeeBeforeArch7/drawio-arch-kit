"""这张图自己的标题、页面名、关键设计决策和图例文字；配色、版式部件全用 tools/drawio_kit.py。"""
import drawio_kit as _kit
from drawio_kit import *  # noqa: F401,F403

TITLE = "mp_pipeline · 5-Stage RV32I Pipeline"
VIEWS = ["Overview", "Execute & forwarding", "Hazards & flush", "Memory & stall"]

DECISIONS = [
    ("Zero-bubble forwarding", "MM→EX、WB→EX\nregfile透明读，普通相关不停顿"),
    ("Load-use stalls front only", "IF、id_reg停1拍，EX往后照走\nex_reg收bubble"),
    ("Static not-taken, flush in EX", "跳转作废IF、ID两条，代价2拍\n作废只清valid"),
    ("CMP shares ALU's a / b", "分支目标另用pc + imm加法器\njalr借ALU算rs1 + imm"),
    ("Regfile read skips decode", "读地址直接取inst字段\n省掉译码，缩短关键路径"),
    ("dmem request from EX", "组合发出，不在cpu里打拍\nload数据在MM当拍可用"),
    ("Hold regs for 1-cycle resp", "imem / dmem响应只有效一拍\n被卡住时先存进hold寄存器"),
]

LEGEND_BOX = [("storage", "Storage · pipeline regs"), ("datapath", "Datapath · ALU / mux"),
              ("control", "Control · decode / stall"), ("recovery", "Recovery · flush"),
              ("commit", "Commit · writeback"), ("external", "External unit")]
LEGEND_LINE = [("data", "Data"), ("addr", "Address / PC"), ("ctrl", "Control"),
               ("fwd", "Forwarding"), ("flush", "Flush / bubble"), ("commit", "Writeback")]


def header(p, subtitle):
    _kit.header(p, TITLE, subtitle)


def subtitle_page(p, s):
    header(p, s)


def legend(p, x, y, w=230):
    return _kit.legend(p, x, y, LEGEND_BOX, LEGEND_LINE, w)


def views(p, x, y, current, w=230):
    return _kit.views(p, x, y, current, VIEWS, w)


def left_column(p, current, y=96):
    yl = legend(p, 24, y)
    views(p, 24, yl + 18, current)
