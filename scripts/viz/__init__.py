# 此文件为构建产物，请勿手工修改。源仓库：peak-shift-engine
# -*- coding: utf-8 -*-
"""
peak-shift-studio
=================

把 ``peak-shift-engine`` 的 JSON 结果渲染为可视化图表与 HTML 报告。

设计原则：**只消费 JSON，不依赖 engine 代码**。两个仓库通过结果格式解耦，
studio 可独立安装使用，也可接入任何输出同构 JSON 的优化器。

模块：

- ``charts``  : 零依赖 SVG 图表生成（电价曲线 / 负荷分布 / 成本对比）
- ``report``  : 读取引擎 JSON，产出 SVG 与 HTML 报告
"""

from . import charts, report

__version__ = "0.1.0"
__all__ = ["charts", "report"]
