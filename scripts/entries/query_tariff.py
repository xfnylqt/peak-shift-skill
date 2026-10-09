#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子能力 ①：查询某省居民分时（峰谷）电价。

用法::

    python scripts/entries/query_tariff.py --list
    python scripts/entries/query_tariff.py --province 广东
    python scripts/entries/query_tariff.py --province 新疆
    python scripts/entries/query_tariff.py --sort-by spread
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

DATA = SKILL_ROOT / "data" / "tariffs"


def load_index():
    return json.loads((DATA / "index.json").read_text(encoding="utf-8"))


def find(key):
    key = key.strip()
    for p in load_index()["provinces"]:
        if key in (p.get("region", ""), p.get("code", ""), p.get("file", ""),
                   (p.get("file") or "").replace(".json", "")):
            return json.loads((DATA / p["file"]).read_text(encoding="utf-8")), p
        if key and key in (p.get("region") or ""):
            return json.loads((DATA / p["file"]).read_text(encoding="utf-8")), p
    return None, None


def main():
    ap = argparse.ArgumentParser(description="查询中国居民分时电价")
    ap.add_argument("--province", help="省份名称或代码")
    ap.add_argument("--list", action="store_true", help="列出全部省份")
    ap.add_argument("--sort-by", choices=["spread", "peak_price", "region"], default="spread")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    idx = load_index()

    if args.province:
        data, meta = find(args.province)
        if not data:
            print("未找到省份：%s" % args.province, file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0

        has = data.get("residential_tou_available", True)
        print("=" * 64)
        print("%s  ·  %s" % (data["region"], data.get("customer_type", "")))
        print("=" * 64)
        print("居民是否执行峰谷分时 : %s" % ("是（自愿申请）" if has else "否"))
        print("数据可信度           : %s" % data.get("confidence"))
        print("生效日期             : %s" % data.get("effective_date"))
        src = data.get("source") or {}
        print("数据来源             : %s" % src.get("name"))
        print("来源链接             : %s" % src.get("url"))

        if not has:
            print()
            print("【不执行原因】")
            print("  %s" % data.get("no_tou_reason", ""))
            if data.get("exception"):
                print()
                print("【例外情形】")
                print("  %s" % data["exception"])
            if data.get("flat_price") is not None:
                print()
                print("【居民统一电价】%.4f 元/千瓦时" % data["flat_price"])
        else:
            print()
            print("【时段与电价】")
            for p in data.get("periods", []):
                price = "待核实" if p.get("price") is None else "%.4f 元/kWh" % p["price"]
                print("  %-12s %s - %s   %s" % (p.get("label", p["name"]), p["start"], p["end"], price))

        if data.get("tiers"):
            print()
            print("【阶梯电价】")
            for t in data["tiers"]:
                parts = ["第%d档 %s" % (t["tier"], t.get("range", ""))]
                for k, label in (("flat", "平"), ("peak", "峰"), ("valley", "谷")):
                    if t.get(k) is not None:
                        parts.append("%s %.4f" % (label, t[k]))
                print("  " + "  ".join(parts))

        for key, title in (("notes", "说明"), ("notes_tiers", "阶梯说明"),
                           ("price_derivation", "价格推算说明"),
                           ("pending", "待核实项")):
            v = data.get(key)
            if v:
                print()
                print("【%s】%s" % (title, v if isinstance(v, str) else "、".join(v)))
        return 0

    # 列表模式
    rows = list(idx["provinces"])
    if args.sort_by == "spread":
        rows.sort(key=lambda p: (not p["has_residential_tou"], -(p["spread"] or -1)))
    elif args.sort_by == "peak_price":
        rows.sort(key=lambda p: -(p["peak_price"] or -1))

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print("已收录 %d 个省级行政区（更新：%s）" % (idx["count"], idx["updated"]))
    print("其中居民执行峰谷分时 %d 个，不执行 %d 个\n"
          % (idx["with_residential_tou"], idx["without_residential_tou"]))

    print("— 居民执行峰谷分时 —")
    for p in rows:
        if not p["has_residential_tou"]:
            continue
        print("  %-16s 峰 %-22s 谷 %-22s 价差 %s" % (
            p["region"], p["peak"] or "-", p["valley"] or "-",
            ("%.4f" % p["spread"]) if p["spread"] else "待核实"))

    print("\n— 居民不执行峰谷分时 —")
    for p in rows:
        if p["has_residential_tou"]:
            continue
        print("  %-16s %s" % (p["region"], (p.get("reason") or "")[:44]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
