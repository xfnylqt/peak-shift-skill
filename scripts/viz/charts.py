# 此文件为构建产物，请勿手工修改。源仓库：peak-shift-engine
# -*- coding: utf-8 -*-
"""
零依赖 SVG 图表生成。

所有函数返回 SVG 字符串（不含 XML 声明），可直接嵌入 HTML 或写入 .svg 文件。
配色遵循「峰高谷低」的直觉映射：峰段偏暖、谷段偏冷绿。
"""

from typing import List, Optional, Sequence, Tuple

PALETTE = {
    "sharp": "#A32D2D",
    "peak": "#D64545",
    "flat": "#E8A33D",
    "valley": "#4E9A51",
    "deep_valley": "#2F7A38",
    "unknown": "#D8D6CF",
    "text": "#2C2C2A",
    "muted": "#7A7873",
    "grid": "#E8E6DF",
    "axis": "#B4B2A9",
    "before": "#B5D4F4",
    "after": "#2F6DB5",
    "accent": "#5B4FCF",
}

PERIOD_LABEL = {
    "sharp": "尖峰", "peak": "峰", "flat": "平",
    "valley": "谷", "deep_valley": "深谷", "unknown": "未知",
}

FONT = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _svg(width: int, height: int, body: str, title: str = "") -> str:
    t = "<title>%s</title>" % _esc(title) if title else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'width="100%%" role="img" font-family="%s">%s%s</svg>'
            % (width, height, FONT, t, body))


def _empty(width: int, height: int, msg: str) -> str:
    body = ('<rect width="%d" height="%d" fill="#FAF9F6"/>'
            '<text x="%d" y="%d" text-anchor="middle" font-size="14" fill="%s">%s</text>'
            % (width, height, width // 2, height // 2, PALETTE["muted"], _esc(msg)))
    return _svg(width, height, body, msg)


def _runs(curve: Sequence[Tuple[str, Optional[float]]]):
    """把槽序列压缩为 (name, price, start_slot, end_slot) 的连续段。"""
    runs = []
    for i, (name, price) in enumerate(curve):
        if runs and runs[-1][0] == name and runs[-1][1] == price:
            runs[-1] = (name, price, runs[-1][2], i + 1)
        else:
            runs.append((name, price, i, i + 1))
    return runs


# ---------------------------------------------------------------------------
# 图 1：分时电价曲线
# ---------------------------------------------------------------------------
def price_curve_svg(curve, width: int = 840, height: int = 330,
                    title: str = "分时电价曲线") -> str:
    valid = [(n, p) for n, p in curve if p is not None]
    if not valid:
        return _empty(width, height, "电价数据不可用（price 为 null）")

    prices = [p for _, p in valid]
    pmax, pmin = max(prices), min(prices)
    top = pmax * 1.18 if pmax > 0 else 1.0

    L, R, T, B = 62, 22, 48, 52
    pw, ph = width - L - R, height - T - B
    n = len(curve)

    def x(slot: float) -> float:
        return L + slot / n * pw

    def y(price: float) -> float:
        return T + ph - price / top * ph

    parts = []
    parts.append('<rect width="%d" height="%d" fill="#FAF9F6" rx="10"/>' % (width, height))
    parts.append('<text x="%d" y="28" font-size="15" font-weight="500" fill="%s">%s</text>'
                 % (L, PALETTE["text"], _esc(title)))

    # y 轴网格
    for i in range(5):
        gv = top * i / 4
        gy = y(gv)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="0.8"/>'
                     % (L, gy, L + pw, gy, PALETTE["grid"]))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" font-size="11" fill="%s">%.2f</text>'
                     % (L - 8, gy + 4, PALETTE["muted"], gv))

    # 时段色块
    for name, price, s, e in _runs(curve):
        if price is None:
            continue
        color = PALETTE.get(name, PALETTE["unknown"])
        rx = x(s)
        rw = x(e) - rx
        ry = y(price)
        rh = T + ph - ry
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.82"/>'
                     % (rx, ry, rw, rh, color))

    # 阶梯轮廓
    path = []
    for name, price, s, e in _runs(curve):
        if price is None:
            continue
        if not path:
            path.append("M %.1f %.1f" % (x(s), y(price)))
        else:
            path.append("L %.1f %.1f" % (x(s), y(price)))
        path.append("L %.1f %.1f" % (x(e), y(price)))
    if path:
        parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6" '
                     'stroke-linejoin="round"/>' % (" ".join(path), PALETTE["text"]))

    # x 轴
    parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                 % (L, T + ph, L + pw, T + ph, PALETTE["axis"]))
    for h in range(0, 25, 2):
        gx = x(h * n / 24)
        parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.8"/>'
                     % (gx, T + ph, gx, T + ph + 4, PALETTE["axis"]))
        parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="%s">%02d</text>'
                     % (gx, T + ph + 18, PALETTE["muted"], h))

    # 图例
    seen, lx = [], L
    for name, price in curve:
        if name in seen or price is None:
            continue
        seen.append(name)
        color = PALETTE.get(name, PALETTE["unknown"])
        parts.append('<rect x="%.1f" y="%.1f" width="11" height="11" rx="2" fill="%s"/>'
                     % (lx, height - 28, color))
        parts.append('<text x="%.1f" y="%.1f" font-size="11.5" fill="%s">%s %s</text>'
                     % (lx + 16, height - 19, PALETTE["muted"],
                        PERIOD_LABEL.get(name, name), "%.3f" % price))
        lx += 92

    return _svg(width, height, "".join(parts), title)


# ---------------------------------------------------------------------------
# 图 2：负荷分布对比
# ---------------------------------------------------------------------------
def load_profile_svg(baseline: Sequence[float], optimized: Sequence[float],
                     width: int = 840, height: int = 320,
                     title: str = "优化前后负荷分布") -> str:
    vmax = max(list(baseline) + list(optimized) + [0.1]) * 1.18
    L, R, T, B = 62, 22, 48, 52
    pw, ph = width - L - R, height - T - B
    steps = len(baseline)
    slot_w = pw / steps

    def y(v: float) -> float:
        return T + ph - v / vmax * ph

    parts = ['<rect width="%d" height="%d" fill="#FAF9F6" rx="10"/>' % (width, height)]
    parts.append('<text x="%d" y="28" font-size="15" font-weight="500" fill="%s">%s</text>'
                 % (L, PALETTE["text"], _esc(title)))

    for i in range(5):
        gv = vmax * i / 4
        gy = y(gv)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="0.8"/>'
                     % (L, gy, L + pw, gy, PALETTE["grid"]))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" font-size="11" fill="%s">%.1f</text>'
                     % (L - 8, gy + 4, PALETTE["muted"], gv))

    bar_w = slot_w * 0.38
    for h in range(steps):
        bx = L + h * slot_w
        for series, color, offset in (
            (baseline, PALETTE["before"], -bar_w * 0.52),
            (optimized, PALETTE["after"], bar_w * 0.52),
        ):
            v = series[h]
            if v <= 0:
                continue
            bh = T + ph - y(v)
            parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1.5" fill="%s"/>'
                         % (bx + offset + slot_w / 2, y(v), bar_w, bh, color))

    parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                 % (L, T + ph, L + pw, T + ph, PALETTE["axis"]))
    for h in range(0, 25, 2):
        gx = L + (h / 24) * pw
        parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="%s">%02d</text>'
                     % (gx, T + ph + 18, PALETTE["muted"], h))
    parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="%s">小时</text>'
                 % (L + pw / 2, height - 14, PALETTE["muted"]))
    parts.append('<text x="14" y="%.1f" text-anchor="middle" font-size="11" fill="%s" '
                 'transform="rotate(-90 14 %.1f)">等效功率 (kW)</text>'
                 % (T + ph / 2, PALETTE["muted"], T + ph / 2))

    lx = L
    for label, color in (("优化前", PALETTE["before"]), ("优化后", PALETTE["after"])):
        parts.append('<rect x="%.1f" y="%.1f" width="11" height="11" rx="2" fill="%s"/>'
                     % (lx, height - 30, color))
        parts.append('<text x="%.1f" y="%.1f" font-size="11.5" fill="%s">%s</text>'
                     % (lx + 16, height - 21, PALETTE["muted"], label))
        lx += 78

    return _svg(width, height, "".join(parts), title)


# ---------------------------------------------------------------------------
# 图 3：成本对比
# ---------------------------------------------------------------------------
def cost_compare_svg(items, baseline_total: float, optimized_total: float,
                     width: int = 840, height: int = 340,
                     title: str = "成本对比") -> str:
    L, R, T, B = 168, 118, 52, 56
    pw, ph = width - L - R, height - T - B
    if items and isinstance(items[0], dict):
        rows = [(i["name"], i["cost_before"], i["cost_after"]) for i in items]
    else:
        rows = [(i.load.name, i.baseline_cost, i.cost) for i in items]
    rows.append(("合计", baseline_total, optimized_total))
    n = len(rows)
    row_h = ph / n
    vmax = max([r[1] for r in rows] + [0.001]) * 1.06

    def w_of(v: float) -> float:
        return v / vmax * pw

    parts = ['<rect width="%d" height="%d" fill="#FAF9F6" rx="10"/>' % (width, height)]
    parts.append('<text x="28" y="30" font-size="15" font-weight="500" fill="%s">%s</text>'
                 % (PALETTE["text"], _esc(title)))

    for idx, (name, before, after) in enumerate(rows):
        cy = T + idx * row_h + row_h / 2
        is_total = (idx == n - 1)
        y0 = cy - row_h * 0.32
        y1 = cy + row_h * 0.32
        color_b = PALETTE["before"] if not is_total else "#93BDE8"
        color_a = PALETTE["after"] if not is_total else PALETTE["accent"]
        parts.append('<text x="%d" y="%.1f" text-anchor="end" font-size="12%s" fill="%s">%s</text>'
                     % (L - 14, cy + 4, " font-weight=\"500\"" if is_total else "",
                        PALETTE["text"], _esc(name)))
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s" opacity="0.85"/>'
                     % (L, y0, max(w_of(before), 1), y1 - y0, color_b))
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                     % (L, y1 + 1, max(w_of(after), 1), y1 - y0, color_a))
        saving = before - after
        label = "¥%.2f" % before if saving <= 0.005 else "¥%.2f → ¥%.2f（省 ¥%.2f）" % (before, after, saving)
        parts.append('<text x="%.1f" y="%.1f" font-size="11.5" fill="%s">%s</text>'
                     % (L + max(w_of(before), 1) + 8, cy + 4, PALETTE["muted"], _esc(label)))

    pct = (baseline_total - optimized_total) / baseline_total * 100 if baseline_total else 0
    parts.append('<rect x="28" y="%.1f" width="11" height="11" rx="2" fill="%s"/>'
                 % (height - 30, PALETTE["before"]))
    parts.append('<text x="45" y="%.1f" font-size="11.5" fill="%s">优化前</text>'
                 % (height - 21, PALETTE["muted"]))
    parts.append('<rect x="98" y="%.1f" width="11" height="11" rx="2" fill="%s"/>'
                 % (height - 30, PALETTE["after"]))
    parts.append('<text x="115" y="%.1f" font-size="11.5" fill="%s">优化后</text>'
                 % (height - 21, PALETTE["muted"]))
    parts.append('<text x="%.1f" y="%.1f" text-anchor="end" font-size="13" font-weight="500" fill="%s">'
                 '整体节省 %.1f%%</text>' % (width - 28, height - 20, PALETTE["accent"], pct))

    return _svg(width, height, "".join(parts), title)
