"""第 3 页冒险时序、第 4 页访存与停顿。"""
from mp_style import *  # noqa: F401,F403


# ====================== 第 3 页：冒险时序 ======================
CELL = {  # 填充, 描边, 字色, 虚线
    "plain": ("#20242c", "#3b414d", T2, False),
    "fwd": ("#0f2a2d", LINE["fwd"][0], T1, False),
    "prod": ("#20242c", LINE["fwd"][0], T2, True),
    "rf": (CAT["commit"][0], CAT["commit"][1], T1, False),
    "stall": (CAT["control"][0], CAT["control"][1], T1, False),
    "bubble": ("#1a1d24", LINE["flush"][0], T3, True),
    "kill": (CAT["recovery"][0], CAT["recovery"][1], T1, False),
    "flush": (CAT["recovery"][0], CAT["recovery"][1], T1, False),
    "redir": (CAT["datapath"][0], CAT["datapath"][1], T1, False),
}


def timing_panel(p, cid, px, py, n, title, sub, rows, notes, w=522, h=370):
    """rows: [(指令, {周期: (文字, 小字, 样式)})]"""
    p.panel(cid, px, py, w, h)
    p.marker(cid + "_mk", px + 16, py + 16, n)
    p.text(cid + "_t", px + 46, py + 15, w - 60, 20, title, size=14, color=T1, bold=True)
    p.text(cid + "_s", px + 46, py + 38, w - 60, 16, sub, size=11, color=T2)
    gx, gy = px + 116, py + 74
    for k in range(1, 8):
        p.text(f"{cid}_c{k}", gx + (k - 1) * 56, gy, 46, 16, f"c{k}", size=10, color=T3, mono=True, align="center")
    for r, (name, cells) in enumerate(rows):
        ry = gy + 22 + r * 44
        p.text(f"{cid}_r{r}", px + 14, ry + 8, 100, 16, name, size=11, color=T1, mono=True)
        for k, (t, small, kind) in cells.items():
            fill, stroke, fc, dashed = CELL[kind]
            v = f"<b>{esc(t)}</b>" + (f'<br><font style="font-size:10px">{esc(small)}</font>' if small else "")
            p.vertex(f"{cid}_r{r}c{k}", gx + (k - 1) * 56, ry, 46, 32, v,
                     f"rounded=1;arcSize=14;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                     f"strokeWidth=1.2;{'dashed=1;dashPattern=3 3;' if dashed else ''}" + font(11, fc, True))
    for i, (txt, color) in enumerate(notes):
        p.text(f"{cid}_n{i}", px + 18, py + 282 + i * 24, w - 36, 18, txt, size=12, color=color)


def stages(start, names, kinds=None, smalls=None):
    kinds = kinds or {}
    smalls = smalls or {}
    return {start + i: (s, smalls.get(start + i, ""), kinds.get(start + i, "plain")) for i, s in enumerate(names)}


def page3():
    p = Page("p3", "3 · Hazards & flush")
    header(p, "Hazard timing · forwarding: 0 stall · load-use: 1 bubble · taken branch / jal / jalr: 2-cycle flush")
    left_column(p, 3)
    S = ["IF", "ID", "EX", "MM", "WB"]
    timing_panel(p, "ta", 280, 96, 1, "RAW forwarding", "普通数据相关：零气泡", [
        ("add x1, ...", stages(1, S, {4: "prod", 5: "prod"})),
        ("add x2, x1", stages(2, S, {4: "fwd"}, {4: "← MM"})),
        ("add x3, x1", stages(3, S, {5: "fwd"}, {5: "← WB"})),
        ("add x4, x1", stages(4, S[:4], {5: "rf"}, {5: "← WB"})),
    ], [("c4：x1从mem_reg.rd_v前递（MM→EX）", LINE["fwd"][0]),
        ("c5：x1从wb_reg.rd_v前递（WB→EX）", LINE["fwd"][0]),
        ("c5：ID读x1时WB正在写，regfile透明读", LINE["commit"][0])])
    timing_panel(p, "tb", 826, 96, 2, "Load-use", "load后面紧跟着用：停1拍", [
        ("lw  x1, 0(x2)", stages(1, S, {5: "prod"})),
        ("add x3, x1", {2: ("IF", "", "plain"), 3: ("ID", "检测", "stall"), 4: ("ID", "stall", "stall"),
                        5: ("EX", "← WB", "fwd"), 6: ("MM", "", "plain"), 7: ("WB", "", "plain")}),
        ("(bubble)", {4: ("EX", "", "bubble"), 5: ("MM", "", "bubble"), 6: ("WB", "", "bubble")}),
        ("next", {3: ("IF", "", "plain"), 4: ("IF", "stall", "stall"), 5: ("ID", "", "plain"),
                  6: ("EX", "", "plain"), 7: ("MM", "", "plain")}),
    ], [("c3：EX是load且rd_s命中 → front_en=0", CAT["control"][1]),
        ("c3：ex_reg收bubble（valid=0）", LINE["flush"][0]),
        ("c5：load已到WB，经WB→EX前递", LINE["fwd"][0])])
    timing_panel(p, "tc", 1372, 96, 3, "Taken branch / jal / jalr", "静态不跳转预测猜错：作废2条", [
        ("beq (taken)", stages(1, S, {3: "flush"}, {3: "flush"})),
        ("pc+4", {2: ("IF", "", "plain"), 3: ("ID", "", "plain"), 4: ("✕", "", "kill")}),
        ("pc+8", {3: ("IF", "", "plain"), 4: ("✕", "", "kill")}),
        ("target", {4: ("IF", "跳转", "redir"), 5: ("ID", "", "plain"), 6: ("EX", "", "plain")}),
    ], [("c3：flush=1 → ex_reg、id_reg的valid←0", LINE["flush"][0]),
        ("c3：pc_if←br_target，order_if←id_reg.order", LINE["addr"][0]),
        ("jal、jalr必跳，同样损失2拍", T2)])

    # 代价小结
    for i, (num, lab, kind) in enumerate([("0", "stall · forwarding", "fwd"), ("1", "bubble · load-use", "ctrl"),
                                          ("2", "cycles lost · taken branch / jal / jalr", "flush")]):
        px = 280 + i * 546
        p.panel(f"cost{i}", px, 490, 522, 64)
        p.text(f"cost{i}_n", px + 20, 498, 40, 48, num, size=34, color=LINE[kind][0], bold=True)
        p.text(f"cost{i}_l", px + 70, 514, 430, 18, lab, size=13, color=T1)
    # 作废规则
    p.panel("killrule", 280, 574, 1614, 54)
    p.text("killrule_t", 300, 592, 1580, 18,
           "作废 = valid←0：写regfile、发dmem请求、报RVFI都先看valid，bubble不用清其他字段", size=13, color=T1)
    return p



# ====================== 第 4 页：访存与停顿 ======================
def lanes(p, cid, x, y, on, kind="data"):
    """一个 32 位字的 4 个字节道：b3 b2 b1 b0，on 里的道高亮"""
    for k, b in enumerate([3, 2, 1, 0]):
        hot = b in on
        fill, stroke = (CAT["storage"] if hot else ("#20242c", "#3b414d"))
        p.vertex(f"{cid}_b{b}", x + k * 48, y, 44, 26, f"b{b}",
                 f"rounded=1;arcSize=12;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;"
                 + font(10, T1 if hot else T3, True, hot))


def page4():
    p = Page("p4", "4 · Memory & stall")
    header(p, "Memory & stall · byte lanes · pipe_en / front_en · hold registers · memory model")
    left_column(p, 4)

    # ---- A：字节道 ----
    px, py = 280, 96
    p.panel("pa", px, py, 800, 440)
    p.marker("pa_mk", px + 16, py + 16, 6)
    p.text("pa_t", px + 46, py + 15, 700, 20, "Byte lanes · load / store", size=14, color=T1, bold=True)
    p.text("pa_s", px + 46, py + 38, 700, 16, "dmem_addr = {aluout[31:2], 2'b00}：按字访问，mask选字节", size=11, color=T2)
    rows = [("STORE · EX发出", None, None, None),
            ("sb   off=1", {1}, "wmask 0010", "wdata = rs2_fwd << 8"),
            ("sh   off=2", {3, 2}, "wmask 1100", "wdata = rs2_fwd << 16"),
            ("sw   off=0", {3, 2, 1, 0}, "wmask 1111", "wdata = rs2_fwd"),
            ("LOAD · MM回来", None, None, None),
            ("lb / lbu  off=3", {3}, "rmask 1000", "byte_sel = dmem_rdata_use[31:24]"),
            ("lh / lhu  off=2", {3, 2}, "rmask 1100", "half_sel = dmem_rdata_use[31:16]"),
            ("lw   off=0", {3, 2, 1, 0}, "rmask 1111", "load_val = dmem_rdata_use")]
    y = py + 70
    for i, (name, on, mask, note) in enumerate(rows):
        if on is None:
            section_label(p, f"pa_h{i}", px + 20, y + 4, name)
            y += 30
            continue
        p.text(f"pa_n{i}", px + 20, y + 5, 150, 16, name, size=11, color=T1, mono=True)
        lanes(p, f"pa_l{i}", px + 180, y, on)
        p.text(f"pa_m{i}", px + 392, y + 5, 100, 16, mask, size=11, color=LINE["addr"][0], mono=True)
        p.text(f"pa_w{i}", px + 504, y + 5, 280, 16, note, size=11, color=T2, mono=True)
        y += 38
    p.text("pa_f", px + 20, py + 404, 760, 18, "mask = 宽度（funct3[1:0]）<< aluout[1:0]；lb / lh补符号位，lbu / lhu补0",
           size=12, color=T2)

    # ---- B：推进控制 ----
    bx, by = 1104, 96
    p.panel("pb", bx, by, 790, 440)
    p.marker("pb_mk", bx + 16, by + 16, 2)
    p.text("pb_t", bx + 46, by + 15, 700, 20, "Stall control · pipe_en / front_en", size=14, color=T1, bold=True)
    p.text("pb_s", bx + 46, by + 38, 700, 16, "任何一侧没放行就整条停；load-use只停前端", size=11, color=T2)
    p.block("ia", 1128, 186, 200, 44, "control", "imem_accept", "imem_resp | ~imem_busy", size=11)
    p.block("da", 1128, 262, 200, 44, "control", "dmem_accept", "req ? (resp | saved) : 1", size=11)
    gate(p, "pand", 1364, 223, 40, 50, "&")
    p.edge("ia_o", [(1328, 208), (1346, 208), (1346, 235), (1364, 235)], "ctrl", end_size=5)
    p.edge("da_o", [(1328, 284), (1346, 284), (1346, 261), (1364, 261)], "ctrl", end_size=5)
    p.text("pe_t", 1356, 202, 60, 16, "pipe_en", size=11, color=CAT["control"][1], mono=True, bold=True)
    p.edge("pe_trunk", [(1440, 192), (1440, 442)], "ctrl", arrow=False)
    p.edge("pe_in", [(1404, 248), (1440, 248)], "ctrl", arrow=False)
    targets = [("t1", 172, "storage", "ex_reg · mem_reg · wb_reg", "regfile read（read_en）"),
               ("t2", 228, "datapath", "dmem rmask / wmask", "只在pipe_en那拍发出"),
               ("t3", 284, "commit", "regf_we · rvfi_valid", None),
               ("t4", 340, "storage", "dmem_rdata_saved清零", None)]
    for cid, ty, cat, t, sub in targets:
        p.block(cid, 1480, ty, 390, 40, cat, t, sub, size=11)
        p.edge(cid + "_e", [(1440, ty + 20), (1480, ty + 20)], "ctrl", end_size=5)
        if ty + 20 not in (192,):
            p.dot(cid + "_d", 1440, ty + 20, "ctrl")
    p.block("fe", 1480, 420, 220, 44, "control", "front_en", "pipe_en & ~load_use", size=11)
    p.edge("fe_in", [(1440, 442), (1480, 442)], "ctrl", end_size=5)
    p.text("lu_in", 1540, 480, 100, 14, "load_use (ID)", size=10, color=T2, mono=True, align="center")
    p.edge("lu_in_e", [(1590, 480), (1590, 464)], "ctrl", end_size=4)
    p.block("fe_t", 1730, 420, 140, 44, "storage", "pc_if · id_reg", "inst_saved清零", size=11)
    p.edge("fe_o", [(1700, 442), (1730, 442)], "ctrl", end_size=5)

    # ---- C：保持寄存器 ----
    cx, cy = 280, 556
    p.panel("pc", cx, cy, 800, 290)
    p.marker("pc_mk", cx + 16, cy + 16, 7)
    p.text("pc_t", cx + 46, cy + 15, 700, 20, "Hold registers", size=14, color=T1, bold=True)
    p.text("pc_s", cx + 46, cy + 38, 700, 16, "imem / dmem响应只有效一拍：被另一侧卡住时先存下", size=11, color=T2)
    for k, (ry, src, reg, selsig, out, rule1, rule2) in enumerate([
            (650, "imem_rdata", "inst_hold", "inst_saved", "inst → ID", "存：front_en=0且imem_accept", "清：front_en=1"),
            (760, "dmem_rdata", "dmem_rdata_hold", "dmem_rdata_saved", "dmem_rdata_use", "存：pipe_en=0且dmem_resp",
             "清：pipe_en=1")]):
        p.text(f"h{k}_in", 430 - tw(src) - 4, ry - 7, tw(src), 14, src, size=10, color=T2, mono=True, align="right")
        p.edge(f"h{k}_d0", [(430, ry), (640, ry)], "data")
        p.dot(f"h{k}_dot", 470, ry, "data")
        p.edge(f"h{k}_d1", [(470, ry), (470, ry + 40), (500, ry + 40)], "data", end_size=5)
        p.block(f"h{k}_r", 500, ry + 24, 120, 32, "storage", reg, size=10)
        p.edge(f"h{k}_d2", [(620, ry + 40), (640, ry + 40)], "data", end_size=4)
        p.trap(f"h{k}_m", 640, ry - 16, 44, 72, "south", "", size=10)
        sel(p, f"h{k}_s", 662, ry + 60, f"sel = {selsig}", w=130)
        outp(p, f"h{k}_o", 684, ry + 20, out, "data", gap=36)
        p.text(f"h{k}_r1", 880, ry + 2, 190, 16, rule1, size=11, color=T2)
        p.text(f"h{k}_r2", 880, ry + 22, 190, 16, rule2, size=11, color=T3)

    # ---- D：存储模型（testbench）----
    dx, dy = 1104, 556
    p.panel("pd", dx, dy, 790, 290)
    p.text("pd_t", dx + 20, dy + 15, 700, 20, "Memory model（tb）", size=14, color=T1, bold=True)
    p.text("pd_s", dx + 20, dy + 38, 700, 16, "tb/common/memory_model.sv · imem、dmem两个通道", size=11, color=T2)
    p.text("pd_m1", dx + 20, dy + 74, 120, 18, "MAGIC=1", size=12, color=T1, mono=True, bold=True)
    p.text("pd_m1v", dx + 140, dy + 74, 400, 18, "不加延迟", size=12, color=T2)
    p.text("pd_m0", dx + 20, dy + 106, 120, 18, "MAGIC=0", size=12, color=T1, mono=True, bold=True)
    p.text("pd_m0v", dx + 140, dy + 106, 600, 18, "地址跟模型内部tag不匹配时，随机延迟：", size=12, color=T2)
    for i, (d, wt) in enumerate([("2", "1%"), ("5", "94%"), ("6", "4%"), ("7", "1%")]):
        tx = dx + 140 + i * 150
        p.panel(f"pd_d{i}", tx, dy + 142, 130, 80)
        p.text(f"pd_d{i}n", tx + 14, dy + 152, 60, 40, d, size=30, color=CAT["external"][1] if d != "5" else T1, bold=True)
        p.text(f"pd_d{i}u", tx + 52, dy + 166, 40, 16, "拍", size=12, color=T2)
        p.text(f"pd_d{i}w", tx + 14, dy + 196, 100, 16, wt, size=12, color=T3, mono=True)
    return p
