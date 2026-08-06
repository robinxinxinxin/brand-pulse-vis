#!/usr/bin/env python3
"""
convert_ig_data.py — Indiegogo 众筹数据抓取与预筛选脚本

功能：
1. 通过 Indiegogo Public API 或网页爬取获取 Technology 类项目
2. 复用 convert_ks_data.py 中的过滤逻辑
3. 输出统一格式的候选集

用法：
  py -3 scripts/convert_ig_data.py --output products/ig-candidates.json [--max 500]
  py -3 scripts/convert_ig_data.py --browser  # 使用浏览器自动化（如果需要）

输出格式（与 ks-candidates.json 一致）：
{
  "sourceDate": "2026-06-13",
  "totalProcessed": ...,
  "totalFiltered": ...,
  "candidates": [ ... ]
}
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 复用 KS 过滤逻辑
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from convert_ks_data import (
    is_fashion_product,
    is_non_visual_product,
    is_low_visual_premium_product,
    CATEGORY_WHITELIST as KS_CATEGORY_WHITELIST,
)

# Indiegogo Technology 相关分类关键词
IG_TECH_KEYWORDS = {
    "tech", "technology", "gadget", "electronic", "hardware",
    "wearable", "smart", "iot", "camera", "audio", "speaker",
    "headphone", "earbud", "charger", "power", "battery",
    "solar", "lighting", "display", "screen", "monitor",
    "keyboard", "mouse", "game", "gaming", "vr", "ar",
    "drone", "robot", "smart home", "home automation",
    "security", "camera", "lock", "thermostat",
    "design", "product design", "innovation",
}

# ---------------------------------------------------------------------------
# Indiegogo API 抓取
# ---------------------------------------------------------------------------

def fetch_active_projects_api() -> list:
    """
    尝试通过 Indiegogo Public API 获取活跃项目。
    ⚠️ 注意：/getActiveCrowdfundingProjects 端点无分类筛选，
    会返回所有活跃项目（数量很大）。
    此处仅做演示，实际需要分页处理。
    """
    url = "https://api.indiegogo.com/api/public/projects/getActiveCrowdfundingProjects"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; BrandPulse/1.0)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # API 返回格式待确认
            projects = data if isinstance(data, list) else data.get("projects", [])
            print(f"[API] 获取到 {len(projects)} 个活跃项目")
            return projects
    except Exception as e:
        print(f"[API] 获取失败: {e}")
        return []


def scrape_tech_category_pages(max_pages: int = 20) -> list:
    """
    爬取 Indiegogo Technology 分类页面。
    URL: https://www.indiegogo.com/explore/technology
    返回项目列表（原始 HTML 解析）。
    """
    projects = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://www.indiegogo.com/",
    }

    for page in range(1, max_pages + 1):
        url = f"https://www.indiegogo.com/explore/technology?page={page}"
        print(f"[爬取] {url}")

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"[爬取] ⚠️ 被拦截 (403)，建议使用浏览器自动化")
                break
            else:
                print(f"[爬取] HTTP 错误 {e.code}")
                break
        except Exception as e:
            print(f"[爬取] 失败: {e}")
            break

        # 解析 HTML 中的项目数据（JSON-LD 或 __NEXT_DATA__）
        page_projects = parse_ig_html(html, page)
        if not page_projects:
            print(f"[爬取] 第 {page} 页无数据，停止")
            break

        projects.extend(page_projects)
        print(f"[爬取] 第 {page} 页获取 {len(page_projects)} 个项目，累计 {len(projects)}")
        time.sleep(1)  # 礼貌延迟

    return projects


def parse_ig_html(html: str, page: int) -> list:
    """
    解析 Indiegogo 分类页 HTML，提取项目数据。
    尝试多种解析策略：
    1. JSON-LD structured data
    2. __NEXT_DATA__ (Next.js)
    3. 正则匹配内联 JSON
    """
    projects = []

    # 策略1: JSON-LD
    json_ld_pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
    for match in json_ld_pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and data.get("@type") == "CrowdfundingCampaign":
                projects.append(data)
        except json.JSONDecodeError:
            pass

    # 策略2: 内联 JSON 数据（Indiegogo 页面中常嵌入 campaign 数据）
    # 查找 "campaigns":[...] 或 "project":{...}
    if not projects:
        inline_pattern = re.compile(r'"campaigns"\s*:\s*(\[.*?\])', re.DOTALL)
        for match in inline_pattern.finditer(html):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    projects.extend(data)
            except json.JSONDecodeError:
                pass

    # 策略3: 如果上述都失败，记录日志供后续用浏览器自动化
    if not projects and page == 1:
        print("[解析] ⚠️ HTML 解析未找到项目数据，建议使用浏览器自动化模式")
        print("[解析] 提示: 运行 `agent-browser open https://www.indiegogo.com/explore/technology`")

    return projects


# ---------------------------------------------------------------------------
# 数据标准化（转为与 KS 候选集一致的格式）
# ---------------------------------------------------------------------------

def normalize_ig_project(raw: dict) -> dict | None:
    """将 Indiegogo 项目数据标准化"""
    # Indiegogo API 字段映射（根据实际返回调整）
    proj_id = raw.get("id") or raw.get("projectId")
    if not proj_id:
        return None

    title = (raw.get("projectName") or raw.get("title") or "").strip()
    desc = (raw.get("shortDescription") or raw.get("description") or "").strip()

    # 复用 KS 过滤逻辑
    if is_fashion_product(title, desc):
        return None
    if is_non_visual_product(title, desc):
        return None
    if is_low_visual_premium_product(title, desc):
        return None

    # 筹款数据
    funds = float(raw.get("fundsGathered", 0) or 0)
    goal = float(raw.get("campaignGoal", 0) or 0)
    currency = (raw.get("currencyShortName") or "USD").upper()
    backers = int(raw.get("backerCount", 0) or 0)

    # 换算 USD
    CURRENCY_RATE = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73, "AUD": 0.67}
    rate = CURRENCY_RATE.get(currency, 1.0)
    usd_pledged = funds * rate

    if usd_pledged < 5000:
        return None

    # 时间
    created_str = ""
    campaign_start = raw.get("campaignStartDate", "")
    if campaign_start:
        try:
            dt = datetime.fromisoformat(campaign_start.replace("Z", "+00:00"))
            created_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            created_str = campaign_start[:16] if campaign_start else ""

    # URL
    url_name = raw.get("projectUrlName") or raw.get("urlName") or str(proj_id)
    project_url = f"https://www.indiegogo.com/projects/{url_name}"

    # 图片
    image_url = raw.get("projectImageUrl") or raw.get("imageUrl") or ""

    return {
        "id": f"ig-{proj_id}",
        "brand": (raw.get("creatorName") or "Unknown").strip(),
        "category": "technology",  # Indiegogo 侧统一标为 technology
        "title": title,
        "desc": desc,
        "time": created_str,
        "url": project_url,
        "tags": ["indiegogo", "technology"],
        "image": image_url,
        "source": "indiegogo",
        "sourceName": "Indiegogo",
        "igData": {
            "goal": goal,
            "pledged": funds,
            "usdPledged": usd_pledged,
            "backersCount": backers,
            "currency": currency,
            "state": raw.get("campaignStatus", ""),
        },
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Indiegogo 众筹数据抓取与预筛选"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 JSON 文件路径（默认: products/ig-candidates.json）",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=500,
        help="最大候选数（默认: 500）",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="使用浏览器自动化模式（需要 agent-browser）",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=20,
        help="爬虫模式：最多爬取 N 页（默认: 20）",
    )

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else (
        Path(__file__).parent.parent / "products" / "ig-candidates.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 获取数据
    if args.browser:
        print("[模式] 浏览器自动化模式")
        print("[提示] 请手动运行以下命令：")
        print("  agent-browser open https://www.indiegogo.com/explore/technology")
        print("  agent-browser snapshot > /tmp/ig-page1.html")
        print("然后在后续版本中自动解析快照")
        # TODO: 在此实现浏览器自动化解析
        raw_projects = []
    else:
        print("[模式] HTTP 爬取模式")
        raw_projects = scrape_tech_category_pages(max_pages=args.pages)

        if not raw_projects:
            print("\n[提示] HTTP 模式未获取到数据（可能被反爬拦截）")
            print("[提示] 两种解决方案：")
            print("  1. 使用 --browser 模式（需要安装 agent-browser）")
            print("  2. 配置代理或使用付费抓取服务（如 Bright Data、Apify）")
            sys.exit(1)

    # 标准化 + 过滤
    candidates = []
    seen_ids = set()
    for raw in raw_projects:
        candidate = normalize_ig_project(raw)
        if candidate is None:
            continue
        if candidate["id"] in seen_ids:
            continue
        seen_ids.add(candidate["id"])
        candidates.append(candidate)
        if len(candidates) >= args.max:
            break

    # 输出
    result = {
        "sourceDate": datetime.now().strftime("%Y-%m-%d"),
        "totalProcessed": len(raw_projects),
        "totalFiltered": len(candidates),
        "candidates": candidates,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 输出 {len(candidates)} 个候选到 {output_path}")
    print(f"  （原始数据: {len(raw_projects)} 条，通过过滤: {len(candidates)} 条）")


if __name__ == "__main__":
    main()
