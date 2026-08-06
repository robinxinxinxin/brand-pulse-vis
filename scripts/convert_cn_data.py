#!/usr/bin/env python3
"""
convert_cn_data.py — 中国众筹/新品平台数据抓取与预筛选脚本

支持平台：
1. 小米有品（https://www.xiaomiyoupin.com/）
2. （后续可扩展：京东众筹、淘宝造物节）

功能：
1. 抓取平台新品/众筹项目列表
2. 复用 convert_ks_data.py 中的过滤逻辑
3. 输出统一格式的候选集

用法：
  py -3 scripts/convert_cn_data.py --output products/cn-candidates.json [--max 500]
  py -3 scripts/convert_cn_data.py --browser  # 使用浏览器自动化

输出格式（与 ks/ig-candidates.json 一致）：
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
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 复用 KS 过滤逻辑
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from convert_ks_data import (
    is_fashion_product,
    is_non_visual_product,
    is_low_visual_premium_product,
)

# ---------------------------------------------------------------------------
# 小米有品爬取
# ---------------------------------------------------------------------------

XIAOMI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.xiaomiyoupin.com/",
}


def scrape_miyoupin_api(max_pages: int = 10) -> list:
    """
    尝试通过小米有品的内部 API 获取新品列表。
    小米有品的部分列表页使用 JSON API（含签名），此处尝试公开接口。
    """
    products = []
    print("[小米有品] 尝试通过 API 获取新品...")

    # 小米有品「最新上架」接口（可能需要签名）
    # 公开可访问的列表接口（不含签名的）
    api_urls = [
        "https://www.xiaomiyoupin.com/mtop/rxian/core/CategoryProductList/",
        "https://api.xiaomiyoupin.com/product/list",
    ]

    for api_url in api_urls:
        try:
            req = urllib.request.Request(
                api_url,
                headers={**XIAOMI_HEADERS, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                print(f"[小米有品] API 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
                break
        except Exception as e:
            print(f"[小米有品] API 调用失败 ({api_url}): {e}")
            continue

    return products


def scrape_miyoupin_html(max_pages: int = 10) -> list:
    """
    爬取小米有品新品/众筹 HTML 页面，解析产品列表。
    """
    products = []
    base_urls = [
        "https://www.xiaomiyoupin.com/classify?firstId=10000227",  # 智能硬件
        "https://www.xiaomiyoupin.com/classify?firstId=10000228",  # 生活家电
    ]

    for base_url in base_urls:
        for page in range(1, max_pages + 1):
            url = f"{base_url}&page={page}" if "?" in base_url else f"{base_url}?page={page}"
            print(f"[爬取] {url}")

            try:
                req = urllib.request.Request(url, headers=XIAOMI_HEADERS)
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

            page_products = parse_miyoupin_html(html)
            if not page_products:
                print(f"[爬取] 第 {page} 页无数据，停止")
                break

            products.extend(page_products)
            print(f"[爬取] 第 {page} 页获取 {len(page_products)} 个产品，累计 {len(products)}")
            time.sleep(1)

    return products


def parse_miyoupin_html(html: str) -> list:
    """解析小米有品页面 HTML，提取产品数据"""
    products = []

    # 策略1: JSON-LD
    json_ld_pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
    for match in json_ld_pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and data.get("@type") in ("Product", "itemListElement"):
                products.append(data)
        except json.JSONDecodeError:
            pass

    # 策略2: 内联 JSON 数据（小米有品页面常嵌入 __INITIAL_STATE__ 或类似变量）
    state_pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*(?:;|\n)', re.DOTALL)
    match = state_pattern.search(html)
    if match and not products:
        try:
            data = json.loads(match.group(1))
            # 提取产品列表（具体字段需根据实际页面调整）
            items = data.get("productList", data.get("items", []))
            if isinstance(items, list):
                products.extend(items)
        except (json.JSONDecodeError, Exception):
            pass

    if not products:
        print("[解析] ⚠️ HTML 解析未找到产品数据")
        print("[解析] 提示: 小米有品页面可能需要 JavaScript 渲染")
        print("[解析] 建议使用浏览器自动化: `agent-browser open https://www.xiaomiyoupin.com/`")

    return products


# ---------------------------------------------------------------------------
# 数据标准化
# ---------------------------------------------------------------------------

def normalize_cn_product(raw: dict, platform: str) -> dict | None:
    """将中国平台产品数据标准化"""
    if platform == "miyoupin":
        return _normalize_miyoupin(raw)
    return None


def _normalize_miyoupin(raw: dict) -> dict | None:
    """标准化小米有品产品数据"""
    proj_id = raw.get("productId") or raw.get("id") or raw.get("skuId")
    if not proj_id:
        return None

    title = (raw.get("productName") or raw.get("name") or raw.get("title") or "").strip()
    desc = (raw.get("brief") or raw.get("description") or raw.get("subtitle") or "").strip()

    if not title:
        return None

    # 复用 KS 过滤逻辑
    if is_fashion_product(title, desc):
        return None
    if is_non_visual_product(title, desc):
        return None
    if is_low_visual_premium_product(title, desc):
        return None

    # 价格（人民币，需换算为 USD 用于统一过滤）
    price_cny = float(raw.get("price") or raw.get("currentPrice") or 0)
    # 简单换算：1 USD ≈ 7.2 CNY（用于金额过滤，众筹平台不同）
    # 此处不过滤金额，因为中国平台是销售而非众筹

    return {
        "id": f"miyo-{proj_id}",
        "brand": (raw.get("brand") or raw.get("supplierName") or "Unknown").strip(),
        "category": _guess_category(title, desc),
        "title": title,
        "desc": desc,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "url": raw.get("productUrl") or f"https://www.xiaomiyoupin.com/detail?productId={proj_id}",
        "tags": ["小米有品", _guess_category(title, desc)],
        "image": raw.get("imageUrl") or raw.get("coverImg") or "",
        "source": "miyoupin",
        "sourceName": "小米有品",
        "cnData": {
            "priceCNY": price_cny,
            "platform": "小米有品",
        },
    }


def _guess_category(title: str, desc: str) -> str:
    """根据标题和描述猜测品类"""
    text = f"{title} {desc}".lower()
    if any(kw in text for kw in ["耳机", "earphone", "earbud", "headphone"]):
        return "audio"
    if any(kw in text for kw in ["手表", "手环", "watch", "wearable"]):
        return "wearables"
    if any(kw in text for kw in ["音箱", "speaker", "音响"]):
        return "audio"
    if any(kw in text for kw in ["充电", "充电器", "电源", "电池", "power"]):
        return "充电配件"
    if any(kw in text for kw in ["摄像头", "相机", "camera", "监控"]):
        return "cameras"
    if any(kw in text for kw in ["机器人", "robot", "扫地"]):
        return "robots"
    if any(kw in text for kw in ["灯", "照明", "light"]):
        return "智能家居"
    return "technology"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="中国众筹/新品平台数据抓取与预筛选"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 JSON 文件路径（默认: products/cn-candidates.json）",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=500,
        help="最大候选数（默认: 500）",
    )
    parser.add_argument(
        "--platform",
        default="miyoupin",
        choices=["miyoupin"],
        help="目标平台（默认: miyoupin）",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="使用浏览器自动化模式（需要 agent-browser）",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=10,
        help="爬虫模式：最多爬取 N 页（默认: 10）",
    )

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else (
        Path(__file__).parent.parent / "products" / "cn-candidates.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 获取数据
    if args.browser:
        print("[模式] 浏览器自动化模式")
        print("[提示] 请手动运行以下命令后，将快照保存为 HTML，然后由本脚本解析：")
        print("  agent-browser open https://www.xiaomiyoupin.com/classify?firstId=10000227")
        print("  agent-browser snapshot > /tmp/miyoupin-page1.html")
        raw_products = []
    else:
        print(f"[模式] HTTP 爬取模式（平台: {args.platform}）")
        if args.platform == "miyoupin":
            raw_products = scrape_miyoupin_html(max_pages=args.pages)
        else:
            raw_products = []

        if not raw_products:
            print("\n[提示] HTTP 模式未获取到数据")
            print("[提示] 中国平台普遍有强反爬措施，建议方案：")
            print("  1. 使用 --browser 模式（需要 agent-browser + Playwright）")
            print("  2. 申请平台开放 API（如有商家资质）")
            print("  3. 使用付费数据服务（如八爪鱼、亮数据）")
            sys.exit(1)

    # 标准化
    candidates = []
    seen_ids = set()
    for raw in raw_products:
        candidate = normalize_cn_product(raw, args.platform)
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
        "totalProcessed": len(raw_products),
        "totalFiltered": len(candidates),
        "candidates": candidates,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 输出 {len(candidates)} 个候选到 {output_path}")
    if candidates:
        print("  预览前3条:")
        for c in candidates[:3]:
            print(f"    - [{c['sourceName']}] {c['title'][:60]}")


if __name__ == "__main__":
    main()
