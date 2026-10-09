# mp_pipeline：5级顺序流水RV32I CPU（设计说明）

> 来源：EWS `~/Desktop/ece411/mp_pipeline/`，提交版`fe5a258 CP3 done`。括号里的文件默认相对`rtl/`。
> 性能、面积数字来自`~/Desktop/localrun/mp_pipeline_进度.md`（2026-09-27实测记录）。
> ASCII图线型：`===>`数据，`--->`地址/控制，`~~>`和`:`前递，`xx`作废。

## 1. 功能与关键参数

- 5级顺序流水：IF → ID → EX → MM → WB，每级一条指令（cpu.sv）
- 指令：RV32I的9类opcode：lui、auipc、jal、jalr、branch、load、store、op-imm、op（pkg/types.sv:7-17）
  - 其他opcode走默认值：不写寄存器、不访存（stage2_decode.sv:79-92, 232）
- 寄存器堆：32 × 32bit，x0恒为0（regfile.sv）
- 复位PC：`0xaaaaa000`（stage1_fetch.sv:73）
- 存储：imem、dmem两个独立端口，按32位字访问，用`resp`握手（cpu.sv:7-19）
- 时钟周期：2000 ps，仿真和综合共用（configs/config.yaml `top_tb.sim.clock_period`；syn/SConscript:173）
- 实测（进度记录）：
  - CoreMark IPC 0.702（MAGIC=1）
  - 无控制指令、无load-use的2000条密集相关序列：IPC 0.998
  - 综合MET，slack +0.000051（单位待确认）；面积12438（单位待确认）

## 2. 组成部件

| 部件 | 职责 | 实现 |
|---|---|---|
| `stage1_fetch` | 维护`pc_if`/`order_if`，发imem请求，选下一个PC，写`id_reg` | `pc_next = flush ? br_target : pc_if + 32'd4`；`inst_hold`存住停顿期间到手的指令（stage1_fetch.sv:42-60） |
| `id_reg` | IF/ID寄存器，只存`pc`/`order`/`valid` | 指令位不另存，由memory模型内部的响应寄存器充当（pkg/types.sv:160；stage2_decode.sv:12） |
| `stage2_decode` | 生成5种立即数，按opcode译出控制信号，检测load-use，写`ex_reg` | 组合译码 + `always_ff`（stage2_decode.sv:30-268） |
| `regfile` | 32 × 32bit，ID读、WB写 | 读出端是寄存器，就是`ex_reg`的`rs1_v`/`rs2_v`部分；同拍写读同号时透传写入值（regfile.sv:10-47） |
| `stage3_execute` | 前递选择、ALU、比较器、算分支目标和`flush`、组合发出dmem请求，写`mem_reg` | ALU 8种运算；CMP 6种比较，分支和slt共用（stage3_execute.sv:98-158；stage2_decode.sv:133-141） |
| `stage4_memory` | 收dmem数据，选字节并扩展，产生`dmem_accept`，写`wb_reg` | `dmem_rdata_hold`存住停顿期间到手的数据（stage4_memory.sv:19-70） |
| `stage5_writeback` | 写回regfile，输出16个RVFI信号 | 纯组合，无寄存器（stage5_writeback.sv） |
| `cpu` | 顶层连线，算`pipe_en`、`front_en` | （cpu.sv:52, 57） |

### 图1 总览

```
legend:  ===> data    ---> address / control

             +-------------------+                           +-------+
             |       imem        |                           | dmem  |
             +-------------------+                           +-------+
               ^             |                                 ^   |    dmem_rdata, dmem_resp
               |             | inst (imem_rdata)               |   |
     +---------+             |                       +---------+   +=========+
     | imem_addr             |                       | addr/mask/wdata       |
     |                       v                       |                       v
 +-------+   +-------+   +-------+   +-------+   +-------+   +-------+   +-------+   +-------+   +-------+
 |  IF   |==>|id_reg |==>|  ID   |==>|ex_reg |==>|  EX   |==>|mem_reg|==>|  MM   |==>|wb_reg |==>|  WB   |==> RVFI x16 --> Spike
 +-------+   +-------+   +-------+   +-------+   +-------+   +-------+   +-------+   +-------+   +-------+
                             |                       ^                                               |
                             | rs1_s, rs2_s          |                                               |
                             v                       | rs1_v, rs2_v                                  |
                         +-------------------+       |                                               |
                         | regfile 32 x 32b  |=======+                                               |
                         +-------------------+                                                       |
                                   ^                                                                 |
                                   +=================================================================+
                                                          regf_we, rd_s, rd_v
```

- imem、dmem、Spike在cpu外面；寄存器之间的`==>`是流水推进方向

## 3. 主要数据流

- 取指：`pc_if` → `imem_addr` → `imem_rdata`（或`inst_hold`）→ `inst` → decode（stage1_fetch.sv:54-56）
- 读操作数：`inst[19:15]`、`inst[24:20]`直接作regfile读地址，不经过译码（stage2_decode.sv:52-53）
  → `rs1_v`/`rs2_v`下一拍到EX
- EX选操作数：`rs1_v`/`rs2_v` → 前递mux → `rs1_fwd`/`rs2_fwd` → `a`/`b` mux → ALU、CMP（stage3_execute.sv:48-84）
  - `a`：rs1 / pc（auipc）/ 0（lui）；`b`：rs2 / imm
- 写回值：`rd_src`选`aluout` / `{31'd0, br_en}` / `ex_reg.pc + 32'd4`，load先占位（stage3_execute.sv:170-178）
  → `mem_reg.rd_v` → MM里load换成`load_val` → `wb_reg.rd_v` → regfile（stage4_memory.sv:89）
- 访存（stage3_execute.sv:121-143；stage4_memory.sv:39-66）：
  - EX组合发出：`dmem_addr = {aluout[31:2], 2'b00}`；mask宽度由`funct3[1:0]`定，位置由`aluout[1:0]`定
  - store数据：`dmem_wdata = rs2_fwd << {aluout[1:0], 3'b000}`
  - MM收`dmem_rdata`：按`mem_addr[1:0]`选字节或半字，按`funct3`补符号位或补0

### 图2 EX级内部

```
legend:  ===> data    ~~~> / : forwarding    ---> control    (all sel signals come from ex_reg)
                                                                                                 +------------------------+
                                                                                                 |    flush = valid &     |---> flush (IF, ID)
            mem_reg.rd_v  wb_reg.rd_v                                                         +->|(branch&br_en|jal|jalr) |
                  :            :                                                              |  +------------------------+
                  :            :                                                              |
                  v            v                                                              |
            +------------------------+              +-------------+       +---------+ br_en   |  +--------------+
rs1_v =====>|       fwd mux x2       |== rs1_fwd ==>| a: rs1|pc|0 |== a =>|   CMP   |=========+=>|   rd_v mux   |
rs2_v =====>|   MM > WB > regfile    |== rs2_fwd ==>| b: rs2|imm  |== b =>|   ALU   |========+==>| cmp|alu|pc+4 |==> mem_reg.rd_v
            +------------------------+              +-------------+       +---------+ aluout |   +--------------+
                                                                                             |            ^
                                                                                             |            |
                                                                                             |    +---------------+
                                                                                             |    | ex_reg.pc + 4 |
                                                                        {aluout[31:1], 1'b0} |    +---------------+
                                                                                             |
                                                                                             |   +---------------+
                                                                                             +==>| br_target mux |
                                                  +------------------------+                     |  sel = jalr   |==> br_target (IF)
                                                  | ex_reg.pc + ex_reg.imm |====================>|               |
                                                  +------------------------+                     +---------------+
```

### 图3 访存通路

```
legend:  ===> data    ---> address / control
EX: stage3_execute (combinational request)                                  MM: stage4_memory
                                                        +--------+
+-----------------------------------------+             |        |          +----------------------------------------+
|    dmem_addr = {aluout[31:2], 2'b00}    |------------>|        |dmem_rdata|                hold mux                |
+-----------------------------------------+             |        |=========>|  saved ? dmem_rdata_hold : dmem_rdata  |
                                                        |        |          +----------------------------------------+
+-----------------------------------------+             |        |                              |
|  mask = 0001|0011|1111 << aluout[1:0]   |------------>|        |                              v
|     rmask / wmask only when pipe_en     |             |  dmem  |          +----------------------------------------+
+-----------------------------------------+             |        |          |         select: mem_addr[1:0]          |==> load_val
                                                        |        |          |   extend: funct3 (lb lbu lh lhu lw)    |==> wb_reg.rd_v
+-----------------------------------------+             |        |          +----------------------------------------+
|wdata = rs2_fwd << {aluout[1:0], 3'b000} |============>|        |
+-----------------------------------------+             |        |dmem_resp +----------------------------------------+
                                                        |        |--------->| dmem_accept = req ? (resp | saved) : 1 |---> pipe_en
                                                        +--------+          +----------------------------------------+
```

- `mem_reg.mem_addr`存完整`aluout`，MM靠低两位选字节（stage3_execute.sv:206）
- 图3的`req`即`|mem_reg.mem_rmask || |mem_reg.mem_wmask`；报RVFI用对齐地址，非访存指令报0（stage4_memory.sv:69-70, 92-97）

## 4. 控制流与关键时序

- 全局推进：`pipe_en = imem_accept & dmem_accept`，门控全部流水寄存器和regfile读出（cpu.sv:52, 132）
  - `imem_accept = imem_resp | ~imem_busy`（stage1_fetch.sv:35）
  - `dmem_accept`：本条有访存时等`dmem_resp`或已存住的数据，否则为1（stage4_memory.sv:69-70）
- 前端推进：`front_en = pipe_en & ~load_use`，只门控IF和`id_reg`（cpu.sv:57；stage1_fetch.sv:78）
- dmem请求只在`pipe_en`那拍发出，停顿期间发空请求（stage3_execute.sv:139-140）
- memory模型（tb/common/memory_model.sv:77-97）：
  - MAGIC=1：不加延迟
  - MAGIC=0：请求地址跟模型内部tag不匹配时，随机延迟2/5/6/7拍，权重1/94/4/1
- 响应只有效一拍：另一侧卡住流水线时，`inst_hold`、`dmem_rdata_hold`先存下；
  `inst_saved`在`front_en`那拍清，`dmem_rdata_saved`在`pipe_en`那拍清（stage1_fetch.sv:45-52；stage4_memory.sv:23-31）
- dmem请求组合发出：memory模型内部的请求寄存器和`mem_reg`在同一个时钟沿打拍，合起来算EX/MM边界
  （stage3_execute.sv:13；cpu.sv:156）

### 图4 推进控制

```
legend:  ---> control
                                                        +---------------+
+---------------------------------------+               |               |
| imem_accept = imem_resp | ~imem_busy  |-------------->|   pipe_en =   |           +--------------------------------+
+---------------------------------------+               |  imem_accept  |           | front_en = pipe_en & ~load_use |
                                                        |       &       |------+--->|    pc_if, order_if, id_reg     |<--- load_use (ID)
                                                        |  dmem_accept  |      |    |        inst_saved clear        |
+-----------------------------------------------+       |               |      |    +--------------------------------+
|dmem_accept = mem req ? (dmem_resp | saved) : 1|------>|               |      |
+-----------------------------------------------+       +---------------+      |    +--------------------------------+
                                                                               |    |    ex_reg, mem_reg, wb_reg     |
                                                                               +--->|  regfile read (rs1_v, rs2_v)   |
                                                                               |    +--------------------------------+
                                                                               |
                                                                               |    +--------------------------------+
                                                                               |    |    dmem rmask / wmask (EX)     |
                                                                               +--->|    regf_we, rvfi_valid (WB)    |
                                                                               |    +--------------------------------+
                                                                               |
                                                                               |    +--------------------------------+
                                                                               +--->|     dmem_rdata_saved clear     |
                                                                                    +--------------------------------+
```

## 5. 异常、冲突与恢复处理

- 普通RAW相关，零气泡：
  - MM→EX：取`mem_reg.rd_v`，load除外，因为数据MM才到（stage3_execute.sv:39-42）
  - WB→EX：取`wb_reg.rd_v`，含load结果（stage3_execute.sv:44-46）
  - 两条都命中时MM优先（stage3_execute.sv:48-64）
  - WB写和ID读同一寄存器：regfile透明读（regfile.sv:41, 45）
- load-use（stage2_decode.sv:236-240, 250）：
  - 条件：EX是有效load、`rd_s`≠0、且等于ID的`rs1_s_id`或`rs2_s_id`
  - 处理：`front_en`=0，IF/ID停1拍，`ex_reg`塞bubble
  - 停完之后，相关指令到EX时load已到WB，经WB→EX前递
- 控制相关，静态不跳转预测：fetch一直取`pc_if + 4`，EX判出要跳就`flush`（stage3_execute.sv:164-166）：
  - `flush = ex_reg.valid && ((ex_reg.branch && br_en) || ex_reg.jal || ex_reg.jalr)`
  - `br_target = ex_reg.jalr ? {aluout[31:1], 1'b0} : ex_reg.pc + ex_reg.imm`
  - `id_reg.valid`←0（作废IF那条）；`ex_reg.valid`←0（作废ID那条）；`pc_if`←`br_target`
    （stage1_fetch.sv:81-82；stage2_decode.sv:250）
  - `order_if`←`id_reg.order`，RVFI的order保持连续（stage1_fetch.sv:84）
  - 每次跳转损失2拍
- 作废只清`valid`：写regfile、发dmem请求、报RVFI都先看`valid`
  （stage5_writeback.sv:32, 37；stage3_execute.sv:135-136）
- 异常、中断、CSR：代码里没有
- 访存只支持自然对齐（stage3_execute.sv:121注释）

### 图5 冒险时序

```
(a) RAW forwarding: no stall
                c1   c2   c3   c4   c5   c6   c7
add x1, ...     IF   ID   EX   MM   WB
add x2, x1           IF   ID   EX   MM   WB         c4: x1 <~~ mem_reg.rd_v (MM -> EX)
add x3, x1                IF   ID   EX   MM   WB    c5: x1 <~~ wb_reg.rd_v  (WB -> EX)
add x4, x1                     IF   ID   EX   MM    c5: ID reads x1 while WB writes it (regfile transparent read)

(b) load-use: 1 bubble
                c1   c2   c3   c4   c5   c6   c7
lw  x1, 0(x2)   IF   ID   EX   MM   WB
add x3, x1           IF   ID   ID   EX   MM   WB    c3: load_use = 1 -> front_en = 0, ex_reg <- bubble
(bubble)                       EX   MM   WB         c5: x1 <~~ wb_reg.rd_v (WB -> EX)
next                      IF   IF   ID   EX   MM

(c) taken branch / jal / jalr: flush 2
                c1   c2   c3   c4   c5   c6
beq (taken)     IF   ID   EX   MM   WB         c3: flush = 1, pc_next = br_target
pc+4                 IF   ID   xx              killed: ex_reg.valid <- 0
pc+8                      IF   xx              killed: id_reg.valid <- 0
target                         IF   ID   EX    order_if <- id_reg.order
```

## 6. 外部接口（cpu.sv:3-19）

- `clk`、`rst`
- imem：`imem_addr[31:0]`、`imem_rmask[3:0]`（恒为`4'b1111`，stage1_fetch.sv:61）、`imem_rdata[31:0]`、`imem_resp`
- dmem：`dmem_addr[31:0]`、`dmem_rmask[3:0]`、`dmem_wmask[3:0]`、`dmem_wdata[31:0]`、`dmem_rdata[31:0]`、`dmem_resp`
- RVFI：16个信号，cpu内部声明，Spike通过`configs/rvfi_reference.yaml`层次引用读取（cpu.sv:97-115）
  - `rvfi_valid`、`rvfi_order`、`rvfi_inst`
  - `rvfi_rs1_addr`、`rvfi_rs2_addr`、`rvfi_rs1_rdata`、`rvfi_rs2_rdata`、`rvfi_rd_addr`、`rvfi_rd_wdata`
  - `rvfi_pc_rdata`、`rvfi_pc_wdata`：后者EX算出，经`mem_reg`/`wb_reg`带到WB（stage3_execute.sv:212；stage5_writeback.sv:50）
  - `rvfi_mem_addr`、`rvfi_mem_rmask`、`rvfi_mem_wmask`、`rvfi_mem_rdata`、`rvfi_mem_wdata`

## 7. 关键设计决策

1. **三条前递路径，普通相关零气泡**：MM→EX、WB→EX、regfile透明读。
   取舍：MM→EX不转发load，换来load-use停1拍（stage3_execute.sv:39-64；regfile.sv:41-45）
2. **load-use只停前端**：`front_en`单独门控IF/ID，EX往后照常走，EX收bubble（cpu.sv:54-57）
3. **静态不跳转 + EX级flush**：结构简单；代价是每次跳转2拍（stage1_fetch.sv:58；stage3_execute.sv:165）
4. **比较器复用ALU的a/b输入**：分支目标另用一个`pc + imm`加法器；jalr目标复用ALU算`rs1 + imm`
   （stage3_execute.sv:162-164）
5. **regfile读地址直接取指令字段**：关键路径短；代价是用不到rs1/rs2的指令也会读，
   报RVFI前要按译码后的地址把读值清0（stage2_decode.sv:50-53；stage3_execute.sv:193-196）
6. **dmem请求从EX组合发出**：memory模型的请求寄存器就是EX/MM边界，load数据在MM当拍可用（stage3_execute.sv:13）
7. **停顿保持寄存器**：imem、dmem响应只有效一拍，另一侧卡住时先存下，不丢指令和数据
   （stage1_fetch.sv:37-41；stage4_memory.sv:16-17）
8. **作废只清`valid`**：所有副作用都由`valid`门控，bubble不用清其他字段（stage5_writeback.sv:32；stage3_execute.sv:135-136）

## 8. 图例约定

颜色按功能分，一经确定，所有页面含义不变。

| 元素 | 颜色 | 用在 |
|---|---|---|
| 存储 | 紫 | `id_reg`、`ex_reg`、`mem_reg`、`wb_reg`、regfile、`pc_if`、`inst_hold`、`dmem_rdata_hold` |
| 数据通路 | 蓝 | ALU、CMP、加法器、立即数生成、选字节/扩展、各个mux |
| 控制逻辑 | 琥珀 | 译码、`load_use`、`pipe_en`、`front_en`、`imem_accept`/`dmem_accept` |
| 恢复/冲刷 | 红 | `flush`、bubble、作废 |
| 提交/写回 | 绿 | WB写regfile、RVFI |
| 外部接口 | 灰 | imem、dmem、Spike |

| 连线 | 样式 |
|---|---|
| 数据（指令、操作数、结果、访存数据） | 紫，粗实线 |
| 地址 / PC | 蓝，细实线 |
| 控制 / 握手 | 琥珀，细实线 |
| 前递（MM→EX、WB→EX） | 青，实线 |
| 冲刷 / bubble | 红，虚线 |
| 写回 / 提交 | 绿，实线 |

## 9. 图里的简化

1. 图1把`imem_rdata`直接画进ID。实际线路是`imem_rdata` → stage1_fetch的`inst`选择（`inst_saved ? inst_hold : imem_rdata`）→ stage2_decode，组合直连，中间不经过`id_reg`（stage1_fetch.sv:54）
2. 图2的`fwd mux x2`代表rs1、rs2两个独立的mux，选择条件相同（stage3_execute.sv:48-64）
3. 图2里各mux和ALU/CMP的sel（`aluop`、`cmpop`、`rd_src`、`alu_a_src`、`alu_b_src`）都来自`ex_reg`，没画线
4. 图4没画`rst`：复位时流水寄存器清0，`pc_if`置`0xaaaaa000`（stage1_fetch.sv:72-77）
