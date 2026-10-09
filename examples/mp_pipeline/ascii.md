# mp_pipeline：ASCII图

> 依据`text.md`和提交版源码（`~/Desktop/ece411/mp_pipeline/rtl/`，`fe5a258`）。括号里的文件默认相对`rtl/`。
> 线型：`===>`数据，`--->`地址/控制，`~~>`和`:`前递，`xx`作废。

## 图1 总览：5级流水和外部存储

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

- 寄存器之间的`==>`就是流水推进方向；imem、dmem、Spike在cpu外面
- 指令位不进`id_reg`的触发器：imem的响应寄存器（停顿时加上`inst_hold`）充当IF/ID的指令部分，`id_reg`只存`pc`/`order`/`valid`（pkg/types.sv:160）
- regfile读出端是寄存器，即`ex_reg`的`rs1_v`/`rs2_v`；dmem请求在EX组合发出，数据在MM回来（regfile.sv:10；stage3_execute.sv:13）

## 图2 EX级内部：前递、ALU/CMP、分支目标

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

- 前递优先级MM > WB > regfile；MM路排除load（stage3_execute.sv:39-64）
- CMP和ALU吃同一对`a`/`b`：分支时decode把a/b设成rs1/rs2，所以分支目标另用一个`pc + imm`加法器（stage2_decode.sv:204-205；stage3_execute.sv:162）
- jalr目标复用ALU算`rs1 + imm`再清最低位；`mem_reg.pc_wdata = flush ? br_target : pc + 4`留给RVFI（stage3_execute.sv:164, 212）

## 图3 访存通路：load / store

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

- 请求在EX组合发出，只在`pipe_en`那拍有效；`mem_reg.mem_addr`存完整`aluout`，MM靠低两位选字节（stage3_execute.sv:139-140, 206）
- 数据在MM当拍可用；流水线被另一侧卡住时先存进`dmem_rdata_hold`（stage4_memory.sv:23-33）
- `req`即`|mem_reg.mem_rmask || |mem_reg.mem_wmask`；报RVFI用对齐地址，非访存指令报0（stage4_memory.sv:69-70, 92-97）

## 图4 推进控制：pipe_en / front_en

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

- imem、dmem任何一侧没放行，整条流水线原地不动（cpu.sv:52）
- load-use只关前端：IF、`id_reg`停一拍，EX往后照常走，`ex_reg`收bubble（cpu.sv:57；stage2_decode.sv:250）
- `inst_saved`在`front_en`那拍清，`dmem_rdata_saved`在`pipe_en`那拍清（stage1_fetch.sv:46；stage4_memory.sv:24）

## 图5 冒险与恢复：时序表

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

- (a) 普通相关零气泡：MM→EX、WB→EX、regfile透明读各管一种距离（stage3_execute.sv:48-64；regfile.sv:41, 45）
- (b) load的数据MM才到，不从MM前递；停1拍后经WB→EX拿到（stage2_decode.sv:236-240）
- (c) jal、jalr必跳，同样作废2条；作废只清`valid`，`order_if`接回被作废那条的号（stage1_fetch.sv:81-84）

## 对照源码的检查

逐条核对了5张图里的连接，没有对不上的。下面是图里做的简化：

1. 图1把`imem_rdata`直接画进ID。实际线路是`imem_rdata` → stage1_fetch的`inst`选择（`inst_saved ? inst_hold : imem_rdata`）→ stage2_decode，组合直连，中间不经过`id_reg`（stage1_fetch.sv:54）
2. 图2的`fwd mux x2`代表rs1、rs2两个独立的mux，选择条件相同（stage3_execute.sv:48-64）
3. 图2里送ALU/CMP的sel（`aluop`、`cmpop`）和`rd_src`、`alu_a_src`、`alu_b_src`都来自`ex_reg`，图上没画线
4. 图4没画`rst`：复位时流水寄存器清0，`pc_if`置`0xaaaaa000`（stage1_fetch.sv:72-77）
