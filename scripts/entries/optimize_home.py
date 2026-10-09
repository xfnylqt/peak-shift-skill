#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子能力 ② / ③：测算与方案 —— 家庭用电时段优化。

用法::

    python scripts/entries/optimize_home.py --province 广东 --preset ev_owner
    python scripts/entries/optimize_home.py --province 浙江 --loads ev_charger,water_heater
    python scripts/entries/optimize_home.py --province 山东 --preset family --month 1
    python scripts/entries/optimize_home.py --province 广东 --preset all_electric --format json
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from peak_shift import build_price_curve, load_tariff, optimize, report  # noqa: E402
from peak_shift.loads import DEFAULT_LOADS, load_from_dict, make_load, presets  # noqa: E402

DATA = SKILL_ROOT / "data" / "tariffs"


def resolve_tariff(value):
    """支持传省份名或直接传文件路径。"""
    p = Path(value)
    if p.exists():
        return p
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    for item in idx["provinces"]:
        if value in (item.get("region", ""), item.get("code", "")) or value in (item.get("region") or ""):
            return DATA / item["file"]
    raise FileNotFoundError(value)


def build_loads(args):
    if args.loads_file:
        spec = json.loads(Path(args.loads_file).read_text(encoding="utf-8"))
        return [load_from_dict(d) for d in spec["loads"]]
    if args.loads:
        return [make_load(k.strip()) for k in args.loads.split(",") if k.strip()]
    return [make_load(k) for k in presets()[args.preset or "family"]]


def main():
    ap = argparse.ArgumentParser(description="家庭用电时段优化")
    ap.add_argument("--province", required=True, help="省份名称，或电价 JSON 路径")
    ap.add_argument("--preset", choices=list(presets()), help="预置画像")
    ap.add_argument("--loads", help="逗号分隔的设备类型")
    ap.add_argument("--loads-file", help="自定义负荷 JSON")
    ap.add_argument("--month", type=int, choices=range(1, 13))
    ap.add_argument("--peak-limit", type=float)
    ap.add_argument("--format", choices=["text", "md", "json"], default="text")
    args = ap.parse_args()

    try:
        path = resolve_tariff(args.province)
    except FileNotFoundError:
        print("未找到省份或文件：%s" % args.province, file=sys.stderr)
        return 2

    tariff = load_tariff(path)

    if not tariff.has_prices():
        print("⚠️ 该地区电价数据中存在未核实项（null），相关设备将无法优化。", file=sys.stderr)
    if tariff.raw.get("residential_tou_available") is False:
        print("⚠️ 该地区居民生活用电**不执行峰谷分时电价**：", file=sys.stderr)
        print("   %s" % tariff.raw.get("no_tou_reason", ""), file=sys.stderr)
        if tariff.raw.get("exception"):
            print("   例外：%s" % tariff.raw["exception"], file=sys.stderr)
        print("   因此无法给出错峰建议。", file=sys.stderr)
        return 3

    loads = build_loads(args)
    curve = build_price_curve(tariff, month=args.month)

    result = optimize(loads, curve,
                      region=tariff.region, customer_type=tariff.customer_type,
                      confidence=tariff.confidence, peak_limit_kw=args.peak_limit)

    if args.format == "json":
        print(report.render_json(result))
    elif args.format == "md":
        print(report.render_markdown(result))
    else:
        print(report.render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
