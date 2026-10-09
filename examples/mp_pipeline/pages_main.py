"""第 1 页总览、第 2 页 EX 级细节。"""
from mp_style import *  # noqa: F401,F403


# ====================== 第 1 页：总览 ======================
def page1():
    p = Page("p1", "1 · Overview")
    header(p, "RV32I · 5-stage in-order · MM→EX / WB→EX forwarding · load-use 1 bubble · "
              "static not-taken, 2-cycle flush · 2000 ps · CoreMark IPC 0.702")

    # ---- 左栏：配置表 ----
    section_label(p, "cfg_t", 24, 96, "CONFIGURATION")
    cfg = [("ISA", "RV32I · 9 opcodes"), ("Pipeline", "5 stages · in-order"), ("Regfile", "32 × 32b"),
           ("Reset PC", "0xaaaaa000"), ("Memory", "imem + dmem · resp"), ("Clock", "2000 ps"),
           ("CoreMark IPC", "0.702 (MAGIC=1)")]
    for i, (k, v) in enumerate(cfg):
        yy = 118 + i * 26
        cell = f"html=1;align=left;spacingLeft=8;fillColor={PANEL[0]};strokeColor={PANEL[1]};"
        p.vertex(f"cfg{i}k", 24, yy, 96, 26, esc(k), cell + font(11, T1, bold=True))
        p.vertex(f"cfg{i}v", 120, yy, 134, 26, esc(v), cell + font(11, T2, mono=(k == "Reset PC")))
        p.containers += [f"cfg{i}k", f"cfg{i}v"]
    yl = legend(p, 24, 316)
    views(p, 24, yl + 18, 1)

    # ---- 右栏：关键设计决策 ----
    decisions(p, 1656, 92, [(i + 1, t, d) for i, (t, d) in enumerate(DECISIONS)])

    # ---- 中间：cpu 边界 ----
    p.vertex("cpu", 276, 196, 1344, 694, "",
             f"rounded=1;arcSize=1;html=1;fillColor=none;strokeColor=#4a515e;strokeWidth=1.2;dashed=1;dashPattern=8 5;")
    p.containers.append("cpu")
    p.text("cpu_t", 290, 202, 60, 16, "cpu", size=12, color=T3, mono=True)

    # 外部：imem、dmem、Spike
    p.block("imem", 400, 104, 320, 52, "external", "imem", "指令存储器", mono=True, size=13)
    p.block("dmem", 1030, 104, 310, 52, "external", "dmem", "数据存储器", mono=True, size=13)
    p.block("spike", 1500, 104, 120, 52, "external", "Spike", "RVFI monitor", mono=False, size=13)

    # 五级容器 + 四个流水寄存器
    Y0, H = 260, 390
    p.container("IF", 296, Y0, 200, H, "IF", "取指", "stage1_fetch")
    p.container("ID", 582, Y0, 170, H, "ID", "译码", "stage2_decode")
    p.container("EX", 838, Y0, 270, H, "EX", "执行", "stage3_execute")
    p.container("MM", 1194, Y0, 170, H, "MM", "访存", "stage4_memory")
    p.container("WB", 1450, Y0, 150, H, "WB", "写回", "stage5_writeback")
    for cid, x in [("id_reg", 512), ("ex_reg", 768), ("mem_reg", 1124), ("wb_reg", 1380)]:
        p.bar(cid, x, 300, 54, 310, cid)
    YM = 455  # 主数据流高度

    # ---- IF ----
    p.text("if_p4", 350, 318, 22, 14, "+4", size=10, color=T2, mono=True, align="center")
    p.text("if_bt", 380, 318, 60, 14, "br_target", size=10, color=LINE["addr"][0], mono=True, align="center")
    p.edge("if_e_p4", [(361, 332), (361, 344)], "addr", end_size=4)
    p.edge("if_e_bt", [(410, 332), (410, 344)], "addr", end_size=4)
    p.trap("pc_next", 340, 344, 90, 34, "west", "pc_next")
    p.text("if_fl", 440, 354, 32, 14, "flush", size=10, color=LINE["flush"][0], mono=True)
    p.edge("if_e_fl", [(440, 361), (425, 361)], "flush", end_size=4)
    p.block("pc_if", 350, 437, 70, 36, "storage", "pc_if")
    p.edge("if_e_mux", [(385, 378), (385, 437)], "addr")
    p.edge("if_e_pc", [(420, YM), (512, YM)], "addr")
    p.dot("if_d_pc", 482, YM, "addr")
    p.edge("if_e_iaddr", [(482, YM), (482, 156)], "addr")
    p.text("if_iaddr_t", 418, 210, 58, 14, "imem_addr", size=10, color=T2, mono=True)
    p.edge("if_e_inst", [(700, 156), (700, 330)], "data")
    p.text("if_inst_t", 706, 228, 40, 14, "inst", size=10, color=T2, mono=True)

    # ---- id_reg / ex_reg 的 flush 入口（同名标签）----
    for cid, cx in [("idr", 539), ("exr", 782)]:
        p.text(f"{cid}_fl", cx - 16, 626, 32, 14, "flush", size=10, color=LINE["flush"][0], mono=True, align="center")
        p.edge(f"{cid}_e_fl", [(cx, 626), (cx, 610)], "flush", end_size=4)

    # ---- ID ----
    p.block("decode", 616, 330, 118, 36, "control", "decode", "opcode → ctrl")
    p.block("immgen", 616, 437, 118, 36, "datapath", "imm gen", "i / s / b / u / j")
    p.block("load_use", 616, 540, 118, 36, "control", "load_use")
    p.edge("id_e_in", [(566, YM), (582, YM)], "data", end_size=5)
    p.edge("id_e_ctrl", [(734, 348), (768, 348)], "ctrl", end_size=5)
    p.edge("id_e_imm", [(734, YM), (768, YM)], "data", end_size=5)
    p.edge("id_e_stall", [(616, 558), (566, 558)], "ctrl", end_size=5)
    p.edge("id_e_bub", [(734, 558), (768, 558)], "flush", end_size=5)
    p.text("id_lu_t", 616, 580, 118, 14, "← stall · bubble →", size=10, color=T2, mono=True, align="center")
    p.marker("mk2", 728, 512, 2)
    # 读地址：直接取指令字段 → regfile
    p.edge("id_e_raddr", [(640, 650), (640, 700)], "addr")
    p.text("id_raddr_t", 552, 668, 80, 14, "rs1_s · rs2_s", size=10, color=T2, mono=True)
    p.marker("mk5", 648, 664, 5)

    # ---- regfile ----
    p.block("regfile", 592, 700, 150, 56, "storage", "regfile", "32 × 32b")
    p.edge("rf_e_rd", [(742, 728), (896, 728), (896, 610)], "data")
    p.text("rf_rd_t", 750, 734, 100, 14, "rs1_v · rs2_v", size=10, color=T2, mono=True)

    # ---- ex_reg → EX ----
    p.edge("ex_e_in", [(822, YM), (838, YM)], "data", end_size=5)

    # ---- EX ----
    p.block("dmemreq", 1020, 272, 78, 32, "datapath", "dmem req")
    p.marker("mk6", 994, 277, 6)
    p.text("ex_fl_t", 895, 322, 32, 14, "flush", size=10, color=LINE["flush"][0], mono=True, align="center")
    p.text("ex_bt_t", 966, 322, 60, 14, "br_target", size=10, color=LINE["addr"][0], mono=True, align="center")
    p.block("flush", 876, 350, 70, 32, "recovery", "flush")
    p.block("brtarget", 956, 350, 80, 32, "datapath", "br_target")
    p.edge("ex_e_fl", [(911, 350), (911, 336)], "flush", end_size=4)
    p.edge("ex_e_bt", [(996, 350), (996, 336)], "addr", end_size=4)
    p.marker("mk3", 846, 355, 3)
    p.block("cmp", 876, 435, 70, 40, "datapath", "CMP")
    p.block("alu", 956, 435, 70, 40, "datapath", "ALU")
    p.marker("mk4", 848, 408, 4)
    p.edge("ex_e_bren", [(911, 435), (911, 382)], "ctrl")
    p.text("ex_bren_t", 916, 400, 40, 14, "br_en", size=10, color=T2, mono=True)
    p.edge("ex_e_alu", [(1026, YM), (1124, YM)], "data")
    p.dot("ex_d_alu", 1059, YM, "data")
    p.edge("ex_e_req", [(1059, YM), (1059, 304)], "addr")
    p.edge("ex_e_dmem", [(1059, 272), (1059, 156)], "addr")
    p.text("ex_req_t", 1066, 200, 120, 14, "addr · mask · wdata", size=10, color=T2, mono=True)
    p.text("ex_rdv_t", 1066, 437, 40, 14, "rd_v", size=10, color=T2, mono=True)
    # 操作数：前递 mux → a / b mux（rs1 / pc / 0，rs2 / imm）→ CMP、ALU 共用
    p.trap("abmux", 896, 512, 110, 28, "east", "a / b", size=14)
    p.edge("ex_e_ab_o", [(951, 512), (951, 494), (911, 494), (911, 475)], "data", end_size=5)
    p.edge("ex_e_ab_o2", [(951, 494), (991, 494), (991, 475)], "data", end_size=5)
    p.dot("ex_d_ab", 951, 494, "data")
    p.trap("fwd", 876, 572, 150, 38, "east", "fwd mux", size=20)
    p.marker("mk1", 846, 580, 1)
    p.edge("ex_e_fwd_o", [(951, 572), (951, 540)], "data", end_size=5)
    # 前递：MM→EX、WB→EX
    p.edge("fw_mm", [(1151, 610), (1151, 680), (976, 680), (976, 610)], "fwd")
    p.edge("fw_wb", [(1407, 610), (1407, 700), (936, 700), (936, 610)], "fwd")
    p.text("fw_mm_t", 1060, 660, 60, 14, "MM→EX", size=10, color=LINE["fwd"][0], mono=True)
    p.text("fw_wb_t", 1180, 706, 60, 14, "WB→EX", size=10, color=LINE["fwd"][0], mono=True)

    # ---- EX → mem_reg → MM ----
    p.edge("mm_e_in", [(1178, YM), (1194, YM)], "data", end_size=5)
    # dmem_rdata 直通 load_val；dmem_rdata_hold 只在流水线被卡住时接住数据（旁路缓冲，不是多一级）
    p.edge("mm_e_rdata", [(1320, 156), (1320, 437)], "data")
    p.text("mm_rdata_t", 1244, 228, 66, 14, "dmem_rdata", size=10, color=T2, mono=True)
    p.block("hold", 1198, 342, 110, 30, "storage", "dmem_rdata_hold", size=10)
    p.dot("mm_d_hold", 1320, 357, "data")
    p.edge("mm_e_tohold", [(1320, 357), (1308, 357)], "data", end_size=4)
    p.marker("mk7", 1328, 328, 7)
    p.edge("mm_e_hold", [(1253, 372), (1253, 437)], "data")
    p.block("loadval", 1210, 437, 138, 36, "datapath", "load_val", "选字节 · 扩展")
    p.edge("mm_e_out", [(1348, YM), (1380, YM)], "data", end_size=5)

    # ---- WB ----
    p.block("rvfi", 1466, 330, 124, 36, "commit", "RVFI × 16")
    p.edge("wb_e_rvfi", [(1434, 348), (1466, 348)], "commit", end_size=5)
    p.edge("wb_e_spike", [(1580, 330), (1580, 156)], "commit")
    p.block("regwr", 1466, 437, 124, 36, "commit", "regfile write")
    p.edge("wb_e_in", [(1434, YM), (1466, YM)], "data", end_size=5)
    p.edge("wb_e_wr", [(1490, 473), (1490, 790), (667, 790), (667, 756)], "commit")
    p.text("wb_wr_t", 1000, 794, 160, 14, "WB write: rd_s · rd_v", size=10, color=LINE["commit"][0], mono=True)

    # ---- pipe_en ----
    p.vertex("pipe_en", 296, 830, 1304, 34,
             f'<b>pipe_en</b> = imem_accept &amp; dmem_accept&nbsp;&nbsp;·&nbsp;&nbsp;'
             f'<font color="{T2}">门控全部流水寄存器</font>',
             f"rounded=1;arcSize=20;html=1;fillColor={CAT['control'][0]};strokeColor={CAT['control'][1]};"
             f"strokeWidth=1.2;" + font(12, T1, mono=True))
    return p


# ====================== 第 2 页：EX 级细节 ======================
def page2():
    p = Page("p2", "2 · Execute & forwarding")
    subtitle_page(p, "EX stage detail · forwarding → ALU / CMP → rd_v · br_target · flush · dmem request")
    left_column(p, 2)
    decisions(p, 1656, 92, [(n, *DECISIONS[n - 1]) for n in (1, 3, 4, 6)])

    # EX 容器
    p.container("EX", 280, 150, 1340, 800, "EX", "执行", "stage3_execute")
    # 前递优先级小表（放在前递 mux 下面）
    p.panel("prio", 330, 660, 330, 140, dashed=True)
    section_label(p, "prio_t", 346, 672, "FORWARDING PRIORITY")
    for i, (k, v) in enumerate([("MM → EX", "mem_reg.rd_v，load除外"), ("WB → EX", "wb_reg.rd_v，含load"),
                                ("else", "regfile rs1_v / rs2_v")]):
        yy = 700 + i * 30
        p.text(f"prio{i}k", 346, yy, 70, 16, k, size=11, color=LINE["fwd"][0] if i < 2 else T2, mono=True, bold=True)
        p.text(f"prio{i}v", 430, yy, 220, 16, v, size=11, color=T2)

    # ---- 前递 mux ×2 ----
    for k, (y0, rs) in enumerate([(270, "rs1_v"), (447, "rs2_v")], 1):
        p.trap(f"fwd{k}", 450, y0, 50, 92, "south", "", size=10)
        inp(p, f"fwd{k}_i0", 450, y0 + 23, rs, "data", gap=36)
        inp(p, f"fwd{k}_i1", 450, y0 + 46, "mem_reg.rd_v", "fwd", gap=36)
        inp(p, f"fwd{k}_i2", 450, y0 + 69, "wb_reg.rd_v", "fwd", gap=36)
        sel(p, f"fwd{k}_s", 475, y0 + 100, "MM > WB > rf")
    p.marker("mk1", 424, 236, 1)
    p.text("fwd_t", 452, 238, 80, 16, "fwd mux", size=11, color=T1, mono=True, bold=True)

    # ---- a / b mux ----
    p.trap("amux", 600, 270, 50, 92, "south", "a", size=10)
    p.edge("rs1fwd", [(500, 316), (600, 316)], "data")
    p.text("rs1fwd_t", 508, 320, 56, 14, "rs1_fwd", size=10, color=T2, mono=True)
    inp(p, "a_pc", 600, 293, "ex_reg.pc", "addr", gap=24)
    inp(p, "a_0", 600, 339, "'0", "data", gap=24)
    sel(p, "amux_s", 625, 366, "sel = alu_a_src")
    p.trap("bmux", 600, 470, 50, 92, "south", "b", size=10)
    p.edge("rs2fwd", [(500, 493), (600, 493)], "data")
    p.text("rs2fwd_t", 508, 497, 56, 14, "rs2_fwd", size=10, color=T2, mono=True)
    inp(p, "b_imm", 600, 539, "ex_reg.imm", "data", gap=24)
    sel(p, "bmux_s", 625, 566, "sel = alu_b_src")

    # ---- ALU / CMP 共用 a、b ----
    fill, stroke = CAT["datapath"]
    p.vertex("alucmp", 720, 250, 130, 320, "",
             f"rounded=1;arcSize=4;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;dashed=1;dashPattern=4 3;")
    p.containers.append("alucmp")
    p.block("alu", 740, 263, 90, 80, "datapath", "ALU", "aluop")
    p.block("cmp", 740, 470, 90, 80, "datapath", "CMP", "cmpop")
    p.text("alucmp_t", 726, 398, 118, 16, "a / b共用", size=11, color=T2, align="center")
    p.edge("a_out", [(650, 316), (690, 316), (690, 386), (720, 386)], "data")
    p.edge("b_out", [(650, 516), (700, 516), (700, 426), (720, 426)], "data")
    p.marker("mk4", 726, 222, 4)

    # ---- 写回值 mux ----
    p.edge("aluout", [(830, 303), (1030, 303)], "data")
    p.text("aluout_t", 890, 287, 44, 14, "aluout", size=10, color=T2, mono=True)
    p.edge("bren", [(830, 510), (900, 510), (900, 326), (1030, 326)], "ctrl")
    p.text("bren_t", 906, 414, 36, 14, "br_en", size=10, color=T2, mono=True)
    p.trap("rdvmux", 1030, 280, 50, 92, "south", "rd_v", size=10)
    inp(p, "pc4_in", 1030, 349, "ex_reg.pc + 4", "data", gap=26)
    sel(p, "rdvmux_s", 1055, 376, "sel = rd_src")
    outp(p, "rdv_o", 1080, 326, "mem_reg.rd_v", "data", gap=40)

    # ---- dmem 请求（组合发出）----
    p.block("dmem", 920, 94, 504, 38, "external", "dmem", size=13)
    p.panel("dreq", 900, 168, 540, 92, dashed=True)
    p.marker("mk6", 868, 170, 6)
    p.block("d_addr", 920, 196, 150, 50, "datapath", "dmem_addr", "{aluout[31:2], 2'b00}", size=11)
    p.block("d_mask", 1086, 196, 150, 50, "datapath", "rmask / wmask", "按宽度和aluout[1:0]", size=11)
    p.block("d_wdata", 1252, 196, 172, 50, "datapath", "dmem_wdata", "rs2_fwd移到对应字节", size=11)
    for k, cx in [("a", 995), ("m", 1161), ("w", 1338)]:
        p.edge(f"d_up_{k}", [(cx, 196), (cx, 132)], "addr")
    p.edge("aluout_tap", [(880, 303), (880, 221), (920, 221)], "addr")
    p.dot("aluout_d", 880, 303, "data")
    p.text("dmem_note1", 1452, 200, 160, 16, "dmem request · 组合发出", size=11, color=T2)
    p.text("dmem_note2", 1452, 220, 160, 16, "只在pipe_en那拍有效", size=11, color=T3)

    # ---- 分支目标 ----
    p.block("pcimm", 1000, 640, 170, 36, "datapath", "ex_reg.pc + ex_reg.imm", size=10)
    p.trap("btmux", 1220, 635, 50, 92, "south", "", size=10)
    p.edge("pcimm_o", [(1170, 658), (1220, 658)], "addr")
    inp(p, "bt_alu", 1220, 704, "{aluout[31:1], 1'b0}", "addr", gap=30)
    sel(p, "btmux_s", 1245, 731, "sel = ex_reg.jalr")
    p.text("btmux_t", 1206, 614, 90, 16, "br_target mux", size=11, color=T1, mono=True, bold=True)
    p.edge("bt_o", [(1270, 681), (1360, 681)], "addr")
    p.text("bt_o_t", 1366, 674, 120, 14, "br_target → IF", size=10, color=LINE["addr"][0], mono=True)
    p.dot("bt_d", 1310, 681, "addr")

    # ---- flush 门 ----
    p.edge("bren_tap", [(900, 510), (900, 780), (1000, 780)], "ctrl")
    p.dot("bren_d", 900, 510, "ctrl")
    gate(p, "and1", 1000, 772, 34, 34, "&")
    inp(p, "g_branch", 1000, 798, "ex_reg.branch", "ctrl", gap=14)
    gate(p, "or1", 1070, 764, 34, 50, "OR")
    p.edge("and1_o", [(1034, 789), (1070, 789)], "ctrl", end_size=5)
    p.text("g_jal", 1052, 740, 70, 14, "ex_reg.jal", size=10, color=T2, mono=True, align="center")
    p.edge("g_jal_e", [(1087, 754), (1087, 764)], "ctrl", end_size=4)
    p.text("g_jalr", 1048, 824, 78, 14, "ex_reg.jalr", size=10, color=T2, mono=True, align="center")
    p.edge("g_jalr_e", [(1087, 824), (1087, 814)], "ctrl", end_size=4)
    gate(p, "and2", 1150, 772, 34, 34, "&")
    p.edge("or1_o", [(1104, 789), (1150, 789)], "ctrl", end_size=5)
    p.text("g_valid", 1128, 816, 78, 14, "ex_reg.valid", size=10, color=T2, mono=True, align="center")
    p.edge("g_valid_e", [(1167, 816), (1167, 806)], "ctrl", end_size=4)
    outp(p, "fl_o", 1184, 789, "flush", "flush", gap=30)
    p.marker("mk3", 970, 732, 3)

    # ---- pc_wdata（报 RVFI）----
    p.block("pc4", 1000, 870, 110, 36, "datapath", "ex_reg.pc + 4", size=10)
    p.trap("pcwmux", 1340, 760, 50, 92, "south", "", size=10)
    p.edge("bt_tap", [(1310, 681), (1310, 783), (1340, 783)], "addr")
    p.edge("pc4_o", [(1110, 888), (1326, 888), (1326, 829), (1340, 829)], "addr")
    sel(p, "pcw_s", 1365, 856, "sel = flush")
    p.text("pcwmux_t", 1320, 740, 96, 16, "pc_wdata mux", size=11, color=T1, mono=True, bold=True)
    outp(p, "pcw_o", 1390, 806, "mem_reg.pc_wdata", "addr", gap=40)
    p.text("pcw_note", 1404, 826, 120, 14, "下一条PC，报RVFI", size=10, color=T3)
    return p
