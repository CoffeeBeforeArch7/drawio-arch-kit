#!/usr/bin/env python3
"""范例：mp_pipeline 5 级流水 RV32I CPU 的 4 页深色架构图。

用法：python3 gen_drawio.py --export --check   → 写 mp_pipeline.drawio、导出每页 PNG、每页跑两个自查脚本
代码：mp_style.py（这张图的标题 / 决策 / 图例文字）、pages_main.py（第 1、2 页）、pages_detail.py（第 3、4 页）；
     配色和版式部件来自仓库的 tools/drawio_kit.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from drawio_kit import run_all  # noqa: E402
from pages_main import page1, page2  # noqa: E402
from pages_detail import page3, page4  # noqa: E402

if __name__ == "__main__":
    run_all([page1, page2, page3, page4], Path(__file__).with_name("mp_pipeline.drawio"), sys.argv)
