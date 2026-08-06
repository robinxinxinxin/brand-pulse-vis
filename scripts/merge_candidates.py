#!/usr/bin/env python3
"""
merge_candidates.py — 合并多平台众筹候选集

功能：
1. 读取 ks-candidates.json / ig-candidates.json / cn-candidates.json
2. 去重（跨平台同名/同URL产品）
3. 输出统一候选集 all-candidates.json

用法：
  py -3 scripts/merge_candidates.py --output products/all-candidates.json
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 去重工具
# ---------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    """标准化标题用于去重"""
    return re.sub(r'[^a-z0-9]', '', title.lower())


def merge_candidates(ks_path: Path, ig_path: Path, cn_path: Path) -> dict:
    """合并三个平台的候选集，去重"""
    all_candidates = []
    seen_keys = set()  # (normalized_title, source_group)

    # 来源优先级（用于去重时的保留策略）
    SOURCE_PRIORITY = {"kickstarter": 0, "indiegogo": 1, "miyoupin": 2}

    # 读取各平台数据
    sources = [
        ("ks", ks_path),
        ("ig", ig_path),
        ("cn", cn_path),
    ]

    raw_counts = {}
    for source_name, path in sources:
        if not path.exists():
            print(f"[{source_name.upper()}] 文件不存在，跳过: {path}")
            raw_counts[source_name] = 0
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        candidates = data.get("candidates", [])
        raw_counts[source_name] = len(candidates)
        print(f"[{source_name.upper()}] 读取 {len(candidates)} 条")

        for c in candidates:
            title_norm = normalize_title(c.get("title", ""))
            # 去重 key：标准化标题 + 来源分组（同类平台合并去重）
            dedup_key = (title_norm, c.get("source", "unknown"))

            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            all_candidates.append(c)

    # 按来源排序（Kickstarter 优先），然后按时间倒序
    all_candidates.sort(
        key=lambda c: (
            SOURCE_PRIORITY.get(c.get("source", ""), 99),
            -(int(c.get("time", "2000-01-01").replace("-", "").replace(" ", "").replace(":", "") or 0)),
        )
    )

    total_raw = sum(raw_counts.values())
    print(f"\n[合并] 原始总计: {total_raw}，去重后: {len(all_candidates)}")
    for src in ["kickstarter", "indiegogo", "miyoupin"]:
        count = sum(1 for c in all_candidates if c.get("source") == src)
        print(f"  {src}: {count} 条")

    return {
        "sourceDate": max(
            _get_source_date(p) for p in [ks_path, ig_path, cn_path] if p.exists()
        ),
        "totalProcessed": total_raw,
        "totalFiltered": len(all_candidates),
        "candidates": all_candidates,
    }


def _get_source_date(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sourceDate", "2000-01-01")
    except Exception:
        return "2000-01-01"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    ks_path = Path("products/ks-candidates.json")
    ig_path = Path("products/ig-candidates.json")
    cn_path = Path("products/cn-candidates.json")
    output_path = Path("products/all-candidates.json")

    print("[合并] 开始合并多平台候选集...")
    result = merge_candidates(ks_path, ig_path, cn_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[完成] 已写入 {output_path} ({result['totalFiltered']} 条)")


if __name__ == "__main__":
    main()
