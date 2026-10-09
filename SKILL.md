---
name: peak-shift
description: Query China's residential time-of-use (peak/valley) electricity tariffs and optimize household appliance scheduling to cut bills. Use when the user asks about 峰谷电价, 分时电价, 电费太贵怎么省, 哪些省没有峰谷电价, 我家空调用电怎么省钱, EV charging schedule, or how much they could save by shifting loads to off-peak hours. Covers all 31 provincial-level regions of mainland China, marks regions without residential TOU explicitly, and never invents tariff data.
license: MIT
metadata:
  author: peak-shift contributors
  version: "0.1.0"
  upstream:
    - cn-tou-tariff
    - peak-shift-engine
    - peak-shift-studio
---

# Peak Shift — 中国居民峰谷电价查询与家庭用电优化

把「夜间用电更划算」这种模糊认知，变成「洗衣机 22:15 启动，年省 X 元」这种可执行方案；
把「我们这儿有峰谷电价吗」这种不确定，变成有官方出处、有生效日期的明确答复。

## 何时使用

在以下场景激活：

- 用户询问某地峰谷 / 分时电价是多少、几点到几点
- 用户问「我们这儿有没有峰谷电价」「为什么我没有谷电」
- 用户觉得电费贵，想把洗衣机、热水器、充电桩等挪到谷段
- 用户想测算「这样改一年能省多少钱」
- 用户需要一份可执行的错峰方案（含定时建议）
- 用户需要图表或报告来说明用电优化效果

**不适用**：工商业电价与需求响应、国外电价、电力市场交易策略、储能与光伏投资测算。

## 三条硬性规则

1. **绝不编造电价数据。** 所有电价必须来自 `data/tariffs/`。数据缺失时明确说明「暂无该地区数据」，并引导用户按 `data/tariffs/index.json` 的结构反馈，**不要凭印象或按比例推算后当作官方值**。
2. **所有金额标注为「估算」。** 结果依赖用户提供的设备功率与实际作息，不得表述为承诺或保证。
3. **居民不执行峰谷电价的地区，必须如实告知。** 全国 31 个省级行政区中有 **9 个**居民生活用电不执行峰谷分时（天津、辽宁、吉林、黑龙江、云南、贵州、西藏、青海、新疆）。遇到这些地区，**要说明原因与例外情形，而不是套用邻近省份的数据**。

## 子能力与调用方式

本 Skill 是一个**集合型技能**，包含四类子能力。按用户意图选择：

| 子能力 | 触发 | 命令 |
|---|---|---|
| **① 查询** | 问某地电价、问哪些省没有峰谷 | `python scripts/entries/query_tariff.py --province 广东` |
| **② 测算** | 问「能省多少」 | `python scripts/entries/optimize_home.py --province 广东 --loads water_heater` |
| **③ 方案** | 要一套完整错峰方案 | `python scripts/entries/optimize_home.py --province 广东 --preset ev_owner` |
| **④ 可视化** | 要图表 / 报告 | `python scripts/entries/make_report.py --province 广东 --preset ev_owner --out output --html` |

全部使用 Python 标准库，**无外部依赖**，可离线运行。

## 标准工作流

### 第 1 步 · 确认地区

必须明确到**省级行政区**。用户未说明时先问一句。

> ⚠️ 不要用 IP、手机号归属地或「用户提到过」来推断。电价政策精确到省，猜错的代价是给出完全错误的建议。

### 第 2 步 · 先查是否存在居民峰谷

```
python scripts/entries/query_tariff.py --province 新疆
```

若输出中「居民是否执行峰谷分时」为 **否**，则：
- 说明官方给出的原因（`no_tou_reason`）
- 说明是否存在例外情形（如电采暖、居民充电桩另有峰谷价格）
- **终止优化流程**，不要继续套用其他省份数据

### 第 3 步 · 收集设备信息

需要：设备类型、功率(W)、单次时长、使用频次、当前习惯启动时间。

用户不清楚功率时使用 `references/appliance-library.md` 中的常见值，并**标注为默认估计**。

### 第 4 步 · 测算与出方案

```
python scripts/entries/optimize_home.py --province 广东 --preset ev_owner
```

预置画像：`single` / `family` / `ev_owner` / `all_electric`。

季节性电价地区（山东、四川、海南、宁夏）需加 `--month`。

### 第 5 步 · 输出

按用户需要选择格式：

- 简述 → 文本输出
- 文档 → `--format md`
- 结构化数据 → `--format json`
- 图表报告 → 走子能力 ④

**必须包含**：电价来源与生效日期、可信度等级、金额为估算的声明。

## 输出规范

| 要素 | 要求 |
|---|---|
| 时段表述 | 用「峰段 08:00–22:00」而非「白天」 |
| 金额 | 保留两位小数，标注「估算」 |
| 数据来源 | 附机构名与生效日期 |
| 未核实数据 | 明确标注「该地区电价尚未核实，仅供参考」 |
| 安全提醒 | 不建议将医疗、安防设备挪至谷段 |

## 参考文件

| 文件 | 用途 |
|---|---|
| `references/tariff-mechanism.md` | 峰谷分时电价机制、阶梯叠加、季节性差异 |
| `references/appliance-library.md` | 常见家电功率、可编程性、调度建议 |
| `references/data-confidence.md` | 数据可信度分级与使用限制 |

## 数据说明

- `data/tariffs/` 由 `scripts/build.py` 从三个源仓库构建生成，**请勿手工修改**
- 覆盖中国大陆 **31 个省级行政区**，其中 22 个执行居民峰谷分时
- 每条数据含 `source`（机构 / URL / 文号）、`effective_date`、`confidence`

## 边界

- 不做硬件控制，只输出方案与定时建议
- 不承诺具体节省金额
- 不覆盖工商业电价与电力市场
- 数据随政策变动，建议提醒用户核对当地供电部门最新公告
