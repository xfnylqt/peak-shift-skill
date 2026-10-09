#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建脚本：从三个源仓库同步代码与数据到本 Skill 目录。

设计依据见《SKILL 封装设计说明》§5.1：「源仓库 + 构建产物」模式。

- 源仓库是唯一事实来源，手工修改本目录下的产物会被下次构建覆盖
- 构建后本目录完全自包含，可离线分发

用法：
    python scripts/build.py            # 同步
    python scripts/build.py --check    # 仅检查差异，不写入
"""

import argparse
import filecmp
import json
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = SKILL_ROOT.parent

SOURCES = {
    "tariff": WORKSPACE / "cn-tou-tariff",
    "engine": WORKSPACE / "peak-shift-engine",
    "studio": WORKSPACE / "peak-shift-studio",
}

BANNER = "此文件为构建产物，请勿手工修改。源仓库：%s\n"


def git_head(repo: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def copy_tree(src: Path, dst: Path, pattern, header: str, check_only: bool):
    """复制匹配的文件，可选加头部注释标记为构建产物。"""
    copied, changed = 0, []
    if not src.exists():
        print("  [跳过] 源不存在：%s" % src)
        return copied, changed
    for f in sorted(src.rglob(pattern)):
        if "__pycache__" in f.parts:
            continue
        rel = f.relative_to(src)
        target = dst / rel
        if check_only:
            if not target.exists() or not filecmp.cmp(f, target, shallow=False):
                changed.append(str(rel))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = f.read_text(encoding="utf-8")
        if header and not text.lstrip().startswith("#!"):
            text = "# " + header + text
        elif header:
            first_nl = text.find("\n")
            shebang, rest = text[:first_nl], text[first_nl:]
            text = shebang + "\n# " + header + rest
        target.write_text(text, encoding="utf-8")
        copied += 1
    return copied, changed


def main():
    ap = argparse.ArgumentParser(description="构建 peak-shift-skill 产物")
    ap.add_argument("--check", action="store_true", help="仅检查差异")
    args = ap.parse_args()

    if args.check:
        print("=== 差异检查 ===")
    else:
        print("=== 开始构建 ===")

    info = {"built_from": {}, "counts": {}}

    # 1) 电价数据
    print("[1/3] 同步电价数据 …")
    n, changed = copy_tree(
        SOURCES["tariff"] / "data", SKILL_ROOT / "data" / "tariffs",
        "*.json", "", args.check)
    info["counts"]["tariff_files"] = n
    if changed:
        print("  变更：%d 个" % len(changed))
    else:
        print("  已同步 %d 个电价文件" % n)

    # 2) 引擎
    print("[2/3] 同步优化引擎 …")
    header = BANNER % "peak-shift-engine"
    n, _ = copy_tree(SOURCES["engine"] / "peak_shift",
                     SKILL_ROOT / "scripts" / "peak_shift", "*.py", header, args.check)
    info["counts"]["engine_files"] = n
    print("  已同步 %d 个模块" % n)

    # 3) 可视化
    print("[3/3] 同步可视化模块 …")
    n, _ = copy_tree(SOURCES["studio"] / "studio",
                     SKILL_ROOT / "scripts" / "viz", "*.py", header, args.check)
    info["counts"]["viz_files"] = n
    print("  已同步 %d 个模块" % n)

    for name, repo in SOURCES.items():
        info["built_from"][name] = {"repo": repo.name, "commit": git_head(repo)}

    if not args.check:
        (SKILL_ROOT / "BUILD_INFO.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n构建完成。产物信息见 BUILD_INFO.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
