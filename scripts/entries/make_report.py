#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子能力 ④：可视化 —— 把优化结果渲染为 SVG 图表与 HTML 报告。

用法::

    # 一步到位：直接由省份生成报告
    python scripts/entries/make_report.py --province 广东 --preset ev_owner --out output

    # 或消费已有的 JSON 结果
    python scripts/entries/make_report.py --input result.json --out output --html
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from peak_shift import build_price_curve, load_tariff, optimize  # noqa: E402
from peak_shift.loads import load_from_dict, make_load, presets  # noqa: E402
from peak_shift.report import render_json  # noqa: E402
from viz import report as viz_report  # noqa: E402

DATA = SKILL_ROOT / "data" / "tariffs"


def resolve_tariff(value):
    p = Path(value)
    if p.exists():
        return p
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    for item in idx["provinces"]:
        if value in (item.get("region", ""), item.get("code", "")) or value in (item.get("region") or ""):
            return DATA / item["file"]
    raise FileNotFoundError(value)


def main():
    ap = argparse.ArgumentParser(description="生成用电优化图表与报告")
    ap.add_argument("--province", help="省份名称（与 --input 二选一）")
    ap.add_argument("--input", help="已有的优化结果 JSON")
    ap.add_argument("--preset", choices=list(presets()), default="family")
    ap.add_argument("--loads", help="逗号分隔的设备类型")
    ap.add_argument("--out", default="output", help="输出目录")
    ap.add_argument("--html", action="store_true", help="额外生成 HTML 报告")
    ap.add_argument("--title", default="用电时段优化报告")
    args = ap.parse_args()

    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    elif args.province:
        tariff = load_tariff(resolve_tariff(args.province))
        if tariff.raw.get("residential_tou_available") is False:
            print("该地区居民不执行峰谷分时电价，无法生成报告：%s"
                  % tariff.raw.get("no_tou_reason", ""), file=sys.stderr)
            return 3
        keys = ([k.strip() for k in args.loads.split(",")] if args.loads
                else presets()[args.preset])
        loads = [make_load(k) for k in keys]
        result = optimize(loads, build_price_curve(tariff), region=tariff.region,
                          customer_type=tariff.customer_type, confidence=tariff.confidence)
        payload = json.loads(render_json(result))
    else:
        print("请提供 --province 或 --input", file=sys.stderr)
        return 2

    paths = viz_report.write_svgs(payload, args.out)
    for name, p in paths.items():
        print("  已生成  %s" % p)

    if args.html:
        svgs = {k: p.read_text(encoding="utf-8") for k, p in paths.items()}
        html = viz_report.html_report(payload, svgs, title=args.title)
        out = Path(args.out) / "report.html"
        out.write_text(html, encoding="utf-8")
        print("  已生成  %s" % out)

    print("\n%s：单次节省 ¥%.2f（%.1f%%），预计年省 ¥%.0f"
          % (payload.get("region") or "结果", payload.get("saving", 0),
             payload.get("saving_pct", 0), payload.get("yearly_saving", 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
