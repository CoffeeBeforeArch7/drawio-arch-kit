# 给代码助手的说明

- **画 / 改drawio图**：先读`docs/DrawIO绘图规范.md`，全程照做；四步提示词原文在`docs/DrawIO画图提示词.md`
- **画新图**：按规范第一节一口气跑到出图：每步对照源码自检，有错当场改，不按步暂停，只问必要的问题；风格按第二节
- **起步**：`python3 tools/new_diagram.py <输出文件夹>`；改`gen_drawio.py`（页多了拆成`pages_*.py`）；
  `python3 gen_drawio.py --export --check`。两个自查脚本都要报0，再导出2倍PNG放大看，至少两轮
- **样板**：`examples/mp_pipeline/`
- **代码**：每个文件不超过400行，嵌套不超过4层；不留placeholder、TODO
- **文字**：回复和文档用中文；中文和英文、数字之间不加空格；图中文字中英结合（名字用英文，短注释用中文）
