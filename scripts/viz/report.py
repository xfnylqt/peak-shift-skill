# 此文件为构建产物，请勿手工修改。源仓库：peak-shift-engine
# -*- coding: utf-8 -*-
"""把引擎的 JSON 结果渲染为 SVG 图表与 HTML 报告。"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from . import charts


def load_payload(path) -> Dict:
    """读取 peak-shift-engine 的 ``--format json`` 输出。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def curve_from(payload: Dict) -> List[Tuple[str, float]]:
    """从 payload 还原 96 槽电价曲线。"""
    prices = payload.get("hourly_price") or []
    periods = payload.get("hourly_periods") or ["unknown"] * len(prices)
    if len(periods) != len(prices):
        periods = ["unknown"] * len(prices)
    return list(zip(periods, prices))


def write_svgs(payload: Dict, outdir) -> Dict[str, Path]:
    """生成三张图表并写入 outdir，返回 {名称: 路径}。"""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    region = payload.get("region") or ""

    svgs = {
        "price_curve": charts.price_curve_svg(
            curve_from(payload),
            title=("%s · 分时电价曲线" % region) if region else "分时电价曲线"),
        "load_profile": charts.load_profile_svg(
            payload.get("hourly_load_baseline") or [0.0] * 24,
            payload.get("hourly_load_optimized") or [0.0] * 24,
            title="优化前后用电负荷分布"),
        "cost_compare": charts.cost_compare_svg(
            payload.get("items") or [],
            payload.get("baseline_total", 0.0),
            payload.get("optimized_total", 0.0),
            title="各设备成本对比"),
    }

    paths = {}
    for name, svg in svgs.items():
        p = outdir / ("%s.svg" % name)
        p.write_text(svg, encoding="utf-8")
        paths[name] = p
    return paths


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def html_report(payload: Dict, svgs: Dict[str, str], title: str = "用电时段优化报告") -> str:
    """把图表与摘要组装为一个可离线打开的 HTML 页面。"""
    region = payload.get("region") or ""
    items = payload.get("items") or []
    warnings = payload.get("warnings") or []

    rows = []
    for i in items:
        rows.append(
            "<tr><td>%s</td><td>%.2f kW</td><td>%.1f h</td><td>%s–%s</td>"
            "<td>¥%.2f</td><td>¥%.2f</td><td class=\"%s\">¥%.2f</td></tr>"
            % (_esc(i.get("name")), i.get("power_kw", 0), i.get("duration_h", 0),
               i.get("start", "-"), i.get("end", "-"),
               i.get("cost_before", 0), i.get("cost_after", 0),
               "pos" if i.get("saving", 0) > 0.005 else "zero", i.get("saving", 0)))

    warn_html = "".join("<li>%s</li>" % _esc(w) for w in warnings)

    return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#FBFAF7;--card:#FFFFFF;--line:#E8E6DF;--text:#2C2C2A;--muted:#7A7873;--pos:#2F7A38;--accent:#5B4FCF}}
*{{box-sizing:border-box}}
body{{margin:0;padding:40px 24px;background:var(--bg);color:var(--text);
font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;
line-height:1.6;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{font-size:24px;font-weight:500;margin:0 0 6px}}
.sub{{color:var(--muted);font-size:13px;margin-bottom:28px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:20px 22px;margin-bottom:20px}}
.card h2{{font-size:15px;font-weight:500;margin:0 0 16px;color:var(--text)}}
.kpis{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px}}
.kpi{{flex:1;min-width:150px;background:var(--card);border:1px solid var(--line);
border-radius:14px;padding:16px 18px}}
.kpi .l{{font-size:12px;color:var(--muted);margin-bottom:6px}}
.kpi .v{{font-size:22px;font-weight:500;letter-spacing:-.01em}}
.kpi .v.pos{{color:var(--pos)}}
.kpi .v.acc{{color:var(--accent)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line)}}
th{{color:var(--muted);font-weight:400;font-size:12px;text-align:right}}
th:first-child,td:first-child{{text-align:left}}
td.pos{{color:var(--pos)}}
td.zero{{color:var(--muted)}}
.warn{{background:#FFF8E8;border:1px solid #F0DCB0;border-radius:12px;
padding:14px 18px;font-size:13px;color:#6B5320}}
.warn ul{{margin:6px 0 0;padding-left:20px}}
svg{{display:block;width:100%;height:auto}}
footer{{color:var(--muted);font-size:12px;margin-top:28px;text-align:center}}
</style></head><body><div class="wrap">
<h1>{title}</h1>
<div class="sub">{region}{ctype} · 数据可信度 {conf} · 由 peak-shift-studio 生成</div>

<div class="kpis">
  <div class="kpi"><div class="l">优化前单次成本</div><div class="v">¥{before:.2f}</div></div>
  <div class="kpi"><div class="l">优化后单次成本</div><div class="v">¥{after:.2f}</div></div>
  <div class="kpi"><div class="l">单次节省</div><div class="v pos">¥{saving:.2f}</div></div>
  <div class="kpi"><div class="l">整体降幅</div><div class="v acc">{pct:.1f}%</div></div>
  <div class="kpi"><div class="l">预计年省（估算）</div><div class="v pos">¥{yearly:,.0f}</div></div>
</div>

<div class="card"><h2>分时电价曲线</h2>{svg_price}</div>
<div class="card"><h2>优化前后负荷分布</h2>{svg_load}</div>
<div class="card"><h2>各设备成本对比</h2>{svg_cost}</div>

<div class="card"><h2>设备排程明细</h2>
<table><thead><tr><th>设备</th><th>功率</th><th>时长</th><th>建议时段</th>
<th>优化前</th><th>优化后</th><th>节省</th></tr></thead>
<tbody>{rows}</tbody></table></div>

{warn_block}

<footer>金额为基于给定电价与设备参数的估算，实际节省取决于真实使用模式。<br>
电价数据由 cn-tou-tariff 社区维护，请以当地供电部门公布为准。</footer>
</div></body></html>""".format(
        title=_esc(title),
        region=_esc(region),
        ctype=(" · " + _esc(payload.get("customer_type"))) if payload.get("customer_type") else "",
        conf=_esc(payload.get("confidence") or "未知"),
        before=payload.get("baseline_total", 0.0),
        after=payload.get("optimized_total", 0.0),
        saving=payload.get("saving", 0.0),
        pct=payload.get("saving_pct", 0.0),
        yearly=payload.get("yearly_saving", 0.0),
        svg_price=svgs.get("price_curve", ""),
        svg_load=svgs.get("load_profile", ""),
        svg_cost=svgs.get("cost_compare", ""),
        rows="".join(rows),
        warn_block=('<div class="warn"><strong>注意事项</strong><ul>%s</ul></div>' % warn_html)
                   if warnings else "",
    )
