#!/usr/bin/env python3
"""
convert_ks_data.py — Kickstarter 数据集下载、解析、预筛选脚本

功能：
1. 从 webrobots.io S3 镜像下载最新 KS 数据集（.json.gz）
2. 流式解压并解析 JSONL
3. 按品类白名单/黑名单 + 金额门槛筛选
4. 去重
5. 输出预筛选候选集（不含 VIS 评分，由 AI 后续完成）

用法：
  py -3 scripts/convert_ks_data.py --url <URL> --output <output.json> [--max 500]
  py -3 scripts/convert_ks_data.py --auto  # 自动从 webrobots.io 获取最新 URL

输出格式（candidates.json）：
{
  "sourceDate": "2026-05-12",
  "totalProcessed": 50000,
  "totalFiltered": 1200,
  "candidates": [ ... ]
}
"""

import argparse
import gzip
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

CATEGORY_WHITELIST = {
    "product design", "technology", "gadgets", "hardware",
    "wearables", "cameras", "diy electronics", "audio",
    "robots", "flight", "3d printing", "cnc", "fabrication tools",
    # 也匹配带连字符/下划线的变体
    "product_design", "diy_electronics", "3d_printing",
}

CATEGORY_BLACKLIST = {
    "fashion", "apparel", "food", "drinks", "art", "music",
    "publishing", "comics", "crafts", "dance", "theater",
    "journalism", "podcasts",
}

MIN_USD_PLEDGED = 5000

# Robin 个人相关性门：只让能训练「带电硬件外观判断」的项目进入 VIS 评分。
# core 是主输出；edge 是保留少量新奇特边缘机会，避免过度精简误杀早期信号。
PERSONAL_RELEVANCE_PASS_TIERS = {"core", "edge"}
EDGE_CANDIDATE_MAX_RATIO = 0.2

CORE_POWERED_HARDWARE_KEYWORDS = {
    # 充电 / 能源
    "power bank", "powerbank", "charger", "charging", "wireless charger",
    "gan charger", "wall charger", "car charger", "charging dock",
    "charging station", "battery pack", "portable battery",
    "portable power station", "solar generator", "solar charger",
    "home battery", "lifepo4", "usb-c hub", "usb c hub",
    "thunderbolt dock", "docking station",
    # AI / 穿戴 / 移动硬件
    "ai glasses", "smart glasses", "ar glasses", "camera glasses",
    "smartwatch", "smart watch", "smart ring", "fitness tracker",
    "ai recorder", "voice recorder", "ai pendant", "wearable camera",
    "body camera", "smart helmet",
    # 影像 / 音频 / 创作者设备
    "camera", "action camera", "360 camera", "webcam", "gimbal", "drone",
    "earbuds", "earphone", "headphone", "headset", "speaker", "soundbar",
    "microphone", "audio interface", "midi controller", "stream deck",
    # 桌搭 / 移动办公 / 电子交互
    "keyboard", "mouse", "trackball", "portable monitor", "external monitor",
    "e-ink", "e ink", "digital notebook", "smart notebook", "smart pen",
    "drawing tablet", "graphics tablet", "smart lamp", "led lamp",
    "vr headset", "xr headset", "mixed reality headset",
    # 小型机器人 / 家庭电子
    "robot", "robot vacuum", "robot mop", "desktop robot", "pet camera",
    "smart feeder", "smart lock", "video doorbell", "smart sensor",
}

ADJACENT_POWERED_HARDWARE_KEYWORDS = {
    "electric bike", "ebike", "e-bike", "electric scooter",
    "electric skateboard", "smart bike", "bike computer",
    "laser engraver", "cnc machine", "3d printer", "3d printing",
    "electric screwdriver", "smart screwdriver", "smart scale",
    "smart mirror", "smart mug", "temperature control mug",
    "smart water bottle", "electric toothbrush", "smart toothbrush",
    "electric shaver", "smart coffee", "smart blender", "smart juicer",
    "air purifier", "smart plug", "smart switch",
}

APPEARANCE_JUDGMENT_KEYWORDS = {
    "transparent", "translucent", "see-through", "clear shell",
    "modular", "magnetic", "magsafe", "swappable", "interchangeable",
    "foldable", "rollable", "transforming", "detachable", "retractable",
    "wearable", "ultra-slim", "ultra slim", "ultra-light", "ultra light",
    "pocket-sized", "pocket sized", "compact", "mini", "world's smallest",
    "world's thinnest", "titanium", "carbon fiber", "aluminum",
    "stainless steel", "ceramic", "sapphire", "brushed metal",
    "anodized", "matte", "frosted", "rgb", "led", "display", "screen",
    "e-ink", "e ink", "customizable", "color options", "premium design",
    "award-winning", "red dot", "futuristic", "sleek", "minimalist",
}

EDGE_VALUE_KEYWORDS = {
    "world's first", "first-ever", "first ever", "reimagined", "reinvented",
    "redefining", "revolutionary", "ai-powered", "ai driven", "built-in ai",
    "gesture control", "voice control", "eye tracking", "touch-free",
    "haptic", "invisible display", "spatial", "mixed reality",
    "transparent", "translucent", "modular", "foldable", "magnetic",
    "wearable", "pocket-sized", "ultra-slim", "ultra-light",
}

PERSONAL_RELEVANCE_EXCLUDE_KEYWORDS = {
    "chair", "stool", "sofa", "couch", "table", "desk", "shelf",
    "knife", "knives", "blade", "cookware", "frying pan", "saucepan",
    "pot set", "pan set", "bowl", "plate", "cutting board",
    "cup", "mug", "tumbler", "bottle", "glass", "wallet", "bag",
    "backpack", "purse", "tent", "sleeping bag", "camping chair",
    "camp table", "stove", "grill", "blanket", "pillow", "mattress",
    "organizer", "holder", "stand", "rack", "mat", "rug",
}

# 服饰/时尚类关键词黑名单 — 针对 "technology/wearables" 漏网之鱼
# 匹配标题或简介时，命中任一关键词即排除
FASHION_KEYWORDS = {
    "pants", "trouser", "jeans", "shirt", "blouse", "t-shirt", "tshirt",
    "jacket", "coat", "hoodie", "sweater", "cardigan", "blazer", "vest",
    "dress", "skirt", "suit", "uniform", "kimono", "robe",
    "sock", "socks", "stocking", "legging", "leggings", "tights", "pantyhose",
    "shoe", "shoes", "sneaker", "boot", "boots", "sandal", "slipper",
    "underwear", "bra", "brief", "boxer", "pajama", "nightwear",
    "hat", "cap", "beanie", "scarf", "glove", "gloves", "belt", "tie", "bowtie",
    "swimsuit", "bikini", "swimwear", "wetsuit",
    "bag", "backpack", "purse", "handbag", "wallet", "clutch", "tote",
    "jersey", "jerseys", "cycling jersey", "bike jersey",
    "cycling shorts", "cycling bibs", "basketball jersey", "baseball jersey",
    "fabric", "textile", "cotton", "wool", "linen", "silk", "denim",
    "fashion", "apparel", "clothing", "wardrobe", "outfit",
    "wearable blanket", "heated vest", "heated jacket", "heated glove",
    "heated sock", "heated scarf", "cooling vest",
}

# 明确允许（即使命中 FASHION_KEYWORDS 也不排除）的关键词
FASHION_ALLOWLIST = {
    "smartwatch", "smart watch", "smart glasses", "ar glasses",
    "camera glasses", "smart helmet", "wearable camera", "wearable display",
    "headset", "earbud", "earphone", "headphone",
    "backpack battery", "backpack solar", "tech backpack",
    "vr glove", "haptic glove", "motion glove",  # 交互手套不是服饰
    "vr shoe", "vr shoes", "gaming shoe",  # VR/游戏鞋是电子设备
}

# ── 非视觉产品关键词 —— 功能导向、视觉溢价低的产品 ──
# 这些品类本质上不靠视觉设计驱动，即使有好看的造型，核心竞争力也不在视觉
NON_VISUAL_KEYWORDS = {
    # ===== 运动/健身器材 =====
    "putting trainer", "putting aid", "putting training",
    "golf putter", "golf club", "golf driver", "golf wedge",
    "putter", "chipper", "golf chipper",
    "ball machine", "jump rope", "skipping rope",
    "leg press", "squat rack", "pull-up bar", "pull up bar",
    "dumbbell", "kettlebell", "barbell", "weight bench",
    "yoga mat", "yoga block", "yoga strap", "yoga wheel",
    "exercise bench", "dip bar", "dip station", "gym machine",
    "paddle board", "paddleboard", "paddleboards", "paddle lounge",
    # 健身训练系统/综合器械（非智能穿戴类）
    "training system", "workout system", "full-body training",
    "home gym", "home workout", "gym equipment", "fitness equipment",
    "power rack", "power cage", "smith machine",
    "cable machine", "resistance machine", "strength machine",
    "weight machine", "exercise equipment", "workout equipment",
    "functional trainer", "cable crossover", "lat pulldown",
    "rowing machine", "rower", "elliptical", "stationary bike",
    "treadmill", "spin bike", "exercise bike",
    "resistance band", "resistance tube", "pull-up assist",
    # ===== 按摩器/理疗设备（非智能穿戴）=====
    "leg massager", "neck massager", "foot massager",
    "back massager", "massage gun", "fascia gun",
    "massage device", "massager", "shiatsu massager",
    "acupressure", "tens unit", "tens device",
    # ===== 家居用品 =====
    "pillow", "bed pillow", "memory foam pillow", "sleep pillow",
    "mattress", "mattress topper", "mattress pad",
    "towel", "towels", "bath towel", "beach towel", "towel set", "hand towel",
    "kitchen sponge", "cleaning sponge", "dish sponge", "sponge", "scrub sponge",
    "toothbrush holder", "toothbrush stand",
    "dish rack", "drying rack", "dish drainer",
    "shower curtain", "bath mat", "bathroom mat",
    "bed sheet", "bedsheet", "bedding", "bed linen",
    "comforter", "duvet", "blanket", "weighted blanket",
    "curtain", "curtains", "blinds", "window blind", "window film",
    "rug", "carpet", "doormat",
    "wine glass", "whiskey glass", "whisky glass",
    "beer glass", "shot glass", "drinking glass",
    "martini glass", "cocktail glass", "wine decanter",
    "glass at", "cold activated glass", "temperature glass",
    # ===== 厨房用具（非电子）=====
    "nutcracker", "nut cracker", "garlic press", "garlic crusher",
    "coffee grinder", "burr grinder", "manual grinder",
    "coffee maker", "coffee machine", "espresso machine",
    "milk frother", "juicer", "blender", "food processor",
    "cutting board", "chopping board", "butcher block",
    "measuring cup", "measuring spoon",
    "food container", "food storage", "lunch box",
    "bento box", "meal prep container",
    "spice jar", "spice rack", "salt and pepper",
    "apron", "oven mitt", "pot holder", "trivet",
    "napkin", "placemat", "table mat",
    # ===== 五金工具/通用工具 =====
    "toolkit", "precision toolkit", "tool set", "screwdriver set",
    "screwdriver", "wrench", "pliers", "hammer", "crowbar",
    "hatchet", "axe", "machete", "maul",
    "socket set", "ratchet set", "tape measure", "level tool",
    "clamp", "vise", "chisel", "saw blade", "drill bit",
    "pocket safe", "safe box", "gun safe",
    "holster", "holster pouch", "edc holster",
    "compass", "navigation compass",
    # ===== 户外/露营（纯功能性装备）=====
    "camping tent", "backpacking tent", "tent stakes", "tent pole",
    "tent", "tents", "tonneau tent", "truck tent",
    "sleeping bag", "sleeping pad", "camping mattress",
    "camp chair", "camping chair", "camp table",
    "camp stove", "camping stove", "portable stove",
    "cooler box", "ice chest", "cooler bag",
    "hiking pole", "trekking pole", "walking stick",
    # ===== 宠物用品 =====
    "cat collar", "cat collars", "dog collar", "dog collars",
    "pet collar", "pet collars", "pet tag", "pet tags",
    "litter box", "cat litter", "litter system",
    "pet bed", "dog bed", "cat bed",
    "pet bowl", "pet feeder", "dog bowl", "cat bowl",
    "pet leash", "dog leash", "pet harness", "dog harness",
    "dog toy", "cat toy", "pet toy", "chew toy",
    "dog treat", "cat treat", "pet treat",
    # ===== 婴儿/育儿用品 =====
    "breastfeeding", "breast pump", "nursing pump",
    "baby bottle", "baby formula", "baby food maker",
    "diaper", "diaper bag", "diaper pail", "changing pad",
    "baby carrier", "baby wrap", "baby sling",
    "stroller", "baby stroller", "car seat", "high chair",
    # ===== 文具/办公用品 =====
    "journal", "notebook", "bullet journal", "travel journal",
    "pen holder", "pencil case", "desk mat", "mouse pad",
    "stapler", "staple", "hole punch", "paper clip",
    "binder", "folder", "file organizer",
    # ===== 纯软件/App（非硬件/非设计品）=====
    "widget app", "widget platform", "home screen widget",
    "widget list", "widget dashboard",
    "mobile app", "task manager app", "productivity app",
    "ai workflow", "ai course", "ai training course",
    "master claude", "chatgpt course",
    # ===== 音乐器材/配件（非电子乐器）=====
    "guitar tuner", "instrument tuner", "guitar pedal",
    "guitar capo", "guitar pick", "guitar strings",
    "guitar stand", "guitar hanger", "guitar strap",
    "drum stick", "drumstick",
    "violin bow", "cello bow", "rosin",
    "music stand", "sheet music",
    # ===== 非产品型项目（众筹社区项目等）=====
    "neighborhood park", "community park", "community garden",
    "school project", "city project",
    # ===== 卫浴/水管 =====
    "faucet", "sink faucet", "kitchen faucet", "bathroom faucet",
    "shower head", "showerhead", "rain shower",
    "bidet", "bidet seat", "toilet seat",
    "plumbing", "drain", "pipe", "p-trap",
    # ===== 个人护理（非智能）=====
    "razor", "shaver", "electric razor", "beard trimmer",
    "hair clipper", "body groomer",
    "comb", "hair brush", "hairbrush",
    # ===== 自行车/骑行装备（非电动）=====
    "bike light", "bicycle light", "cycling light",
    "bike lock", "bicycle lock", "u-lock",
    "bike pump", "bicycle pump", "tire pump",
    "bike rack", "bicycle rack", "bike stand",
}

# 明确放行：即使命中 NON_VISUAL_KEYWORDS 也保留
# （智能/电子/视觉创新版本）
NON_VISUAL_ALLOWLIST = {
    # 智能枕头有传感器/显示屏
    "smart pillow", "anti-snore pillow", "anti snore",
    # 智能床垫
    "smart mattress", "sleep tracking mattress",
    # 智能咖啡设备
    "smart coffee", "smart brewer", "precision brewer",
    "smart espresso", "iot coffee",
    # 智能工具箱（含显示/充电）
    "smart toolkit", "digital toolkit", "electric screwdriver set",
    # 智能宠物设备
    "smart pet", "gps pet", "pet gps", "pet tracker",
    "smart collar", "gps collar", "activity collar",
    "automatic feeder", "smart feeder", "automatic pet feeder",
    "pet camera", "dog camera", "cat camera",
    # 智能婴儿设备
    "baby monitor", "smart baby", "smart diaper",
    "smart breast pump", "wearable breast pump",
    # 智能卫浴
    "smart faucet", "touchless faucet", "digital faucet",
    "smart shower", "digital shower",
    # 智能体重秤/健身追踪
    "smart scale", "body composition", "fitness tracker",
    # 智能按摩器
    "smart massager", "heated massager", "shiatsu pillow",
    # 智能锁/密码锁
    "smart lock", "fingerprint lock", "biometric lock",
    # 智能厨房
    "smart food container", "smart container", "smart lunch box",
    "temperature control mug", "smart mug", "heated mug",
    "smart blender", "iot blender", "smart juicer",
    # 食品3D打印
    "food 3d printer", "chocolate 3d printer",
    "smart toothbrush", "connected toothbrush", "electric toothbrush with app",
    # 智能文具
    "smart pen", "digital pen", "smart notebook", "smart journal",
    "digital notebook", "e-ink notebook",
    # 骑行智能装备
    "smart bike", "smart bicycle", "electric bike", "ebike",
    "smart helmet", "bike computer", "cycling computer",
    # 智能乐器/电子乐器
    "smart guitar", "midi controller", "synthesizer",
    "electronic piano", "digital piano", "electronic drum",
    "smart instrument", "looper pedal", "audio interface",
}


def is_fashion_product(title: str, desc: str) -> bool:
    """检查产品标题/描述是否属于服饰/时尚类"""
    # 先清理文本：去除标点转为空格，便于词边界匹配
    import string as _string
    _trans = str.maketrans(_string.punctuation, ' ' * len(_string.punctuation))
    text = f" {title.lower().translate(_trans)} {desc.lower().translate(_trans)} "
    # 检查允许白名单
    for allowed in FASHION_ALLOWLIST:
        if allowed in text:
            return False
    # 检查黑名单关键词（完整词匹配）
    for kw in FASHION_KEYWORDS:
        if f" {kw} " in text or f" {kw}s " in text or text.startswith(f"{kw} ") or text.endswith(f" {kw}"):
            return True
    return False

# 视觉溢价低的产品关键词 — 功能导向，外观创新不是主要卖点
# 匹配标题或简介时，命中任一关键词即排除
LOW_VISUAL_PREMIUM_KEYWORDS = {
    # --- 智能戒指（功能导向健康监测，外观同质化严重）---
    "smart ring", "smartring", "health ring", "fitness ring",
    "sleep ring", "nfc ring", "payment ring", "mood ring",
    "smart jewelry", "smart jewellery",
    "health tracker ring", "activity ring", "wellness ring",
    # --- VR/XR 配件（纯功能附件，非头显本身）---
    "vr head strap", "vr strap", "head strap", "halo strap",
    "elite strap", "comfort strap",
    "vr facial interface", "facial interface", "vr face cover",
    "vr face pad", "vr gasket", "face gasket",
    "vr grip", "controller grip", "knuckle strap",
    "vr stand", "headset stand", "charging dock",
    "vr cable", "link cable", "vr link", "oculus link",
    "vr lens", "prescription lens", "vr prescription",
    "vr lens protector", "vr cover", "vr protector",
    "vr fan", "vr cooling fan", "vr ventilation",
    "vr battery pack", "vr battery strap", "vr power bank",
    "vr mat", "vr mat cover", "vr floor mat",
    "vr case", "headset case", "vr travel case",
    "gun stock", "vr stock", "vr gunstock", "rifle stock",
    "vr pulley", "cable pulley", "vr cable management",
    "vr holder", "controller holder", "vr wall mount",
    "vr cleaning", "vr wipe", "vr hygiene",
    # --- 工具腰带/腰包（纯实用工具承载）---
    "tool belt", "utility belt", "work belt", "tactical belt",
    "tool pouch", "tool holster", "tool organizer",
    # --- 刀具/EDC（功能至上，视觉溢价低）---
    "pocket knife", "folding knife", "edc knife",
    "survival knife", "camping knife", "hunting knife",
    "chef knife", "kitchen knife", "cooking knife",
    "paring knife", "bread knife", "utility knife",
    "scalpel knife", "scalpel blade",
    "keyknife", "key knife", "keychain knife",
    "claw knife", "card knife", "credit card knife",
    "karambit", "bowie knife", "hunting blade",
    "tactical knife", "rescue knife", "box cutter",
    "damascus knife", "damascus blade", "damascus steel",
    "tactical pen", "edc pry bar", "edc tool",
    "pocket tool", "keychain tool",
    # --- 厨房用具（功能导向）---
    "cutting board", "chopping board",
    "frying pan", "saucepan", "cookware set",
    "pot set", "pan set", "non-stick pan",
    "kitchen gadget", "kitchen tool", "cooking tool",
    "measuring cup", "measuring spoon",
    # --- 杯具/水具（外观差异小，视觉溢价低）---
    "coffee mug", "travel mug", "insulated mug",
    "thermos", "thermos flask", "vacuum flask",
    "tumbler", "drinking cup", "tea cup",
    "wine glass", "whiskey glass", "beer glass",
    "shot glass", "drinking glass",
    "water bottle cage", "bottle cage",
    # --- 纯户外工具/装备（功能导向不强调视觉设计）---
    "multitool", "multi-tool", "multi tool",
    "mini wrench", "titanium wrench", "adjustable wrench",
    "flashlight", "tactical flashlight", "rangefinder flashlight",
    "edc light", "keychain light",
    "lantern holder", "camping stove",
    # --- 桌面收纳/线材管理---
    "cable organizer", "cable management", "cable clip",
    "cable holder", "cord organizer",
    "desk organizer", "pen holder", "desk tray",
    # --- 其他低视觉溢价配件---
    "screen protector", "tempered glass",
    "cleaning cloth", "cleaning kit",
}

# 明确允许（即使命中 LOW_VISUAL_PREMIUM_KEYWORDS 也不排除）
LOW_VISUAL_PREMIUM_ALLOWLIST = {
    # VR 头显本身有显著的视觉/CMF 创新空间
    "vr headset", "vr head-mounted", "vr head mounted",
    "virtual reality headset", "mixed reality headset",
    "ar headset", "xr headset",
    # 智能水杯有显示屏/传感器等视觉创新
    "smart water bottle", "smart bottle", "smart mug",
    "temperature display bottle", "led bottle",
    # 智能戒指如果是作为控制器（手势/交互）而不是健康监测，可能视觉溢价足够
    # 但大部分 KS 智能戒指是健康监测，因此默认排除
}

# 交互/结构创新信号 — 如果产品描述命中这些信号，即使品类命中排除关键词也放行
# 核心理念：卡扣、锁止机构、变形机制等「结构上的交互」本身就是设计溢价
INTERACTION_INNOVATION_SIGNALS = {
    # --- 机构/机械创新 ---
    "patented mechanism", "proprietary mechanism", "novel mechanism",
    "locking mechanism", "locking system", "lock mechanism",
    "deployment mechanism", "deployment system",
    "opening mechanism", "closing mechanism",
    "quick release", "quick-release",
    "snap mechanism", "snap lock", "snap-lock",
    "click mechanism", "click system", "click-lock",
    "slide mechanism", "sliding mechanism", "rail mechanism",
    "cam mechanism", "cam lock", "cam-lock",
    "ratchet mechanism", "ratchet system",
    "tension mechanism", "torsion mechanism",
    "spring loaded", "spring-loaded",
    # --- 卡扣/连接/固定创新 ---
    "magnetic lock", "magnetic lock", "magnetic latch",
    "magnetic buckle", "magnetic mechanism",
    "buckle system", "buckle mechanism",
    "latch mechanism", "latch system",
    "clasp mechanism", "clasp system",
    "clip mechanism", "quick clip",
    "tool free", "tool-free", "toolless",
    "no tools required", "no screws",
    # --- 折叠/变形/展开 ---
    "folding mechanism", "fold mechanism",
    "transforming mechanism", "transformable",
    "retractable mechanism", "retractable system",
    "telescopic mechanism", "telescoping",
    "collapsible mechanism",
    "flip mechanism", "flip open",
    # --- 单手操作/人体工学交互 ---
    "one-hand deployment", "one-handed deployment",
    "one hand operation", "one-handed operation",
    "single hand operation", "single-handed",
    "ambidextrous design", "ambidextrous operation",
    # --- 模块化物理连接 ---
    "modular mechanism", "modular connection",
    "interchangeable mechanism",
    "hot swap mechanism", "hot-swap",
    "tool-less swap", "tool free swap",
}


def is_non_visual_product(title: str, desc: str) -> bool:
    """检查产品是否属于非视觉驱动的功能品类（枕头、厨具、运动器材等）"""
    import string as _string
    _trans = str.maketrans(_string.punctuation, ' ' * len(_string.punctuation))
    text = f" {title.lower().translate(_trans)} {desc.lower().translate(_trans)} "
    # 检查放行白名单
    for allowed in NON_VISUAL_ALLOWLIST:
        if f" {allowed} " in text or text.startswith(f"{allowed} ") or text.endswith(f" {allowed}"):
            return False
    # 检查黑名单关键词（完整词匹配）
    for kw in NON_VISUAL_KEYWORDS:
        if f" {kw} " in text or text.startswith(f"{kw} ") or text.endswith(f" {kw}"):
            # 命中排除关键词，但先检查是否有交互/结构创新信号
            if _has_interaction_innovation(text):
                return False  # 有创新信号，放行
            return True
    return False


def is_low_visual_premium_product(title: str, desc: str) -> bool:
    """检查产品标题/描述是否属于视觉溢价低的功能导向产品"""
    import string as _string
    _trans = str.maketrans(_string.punctuation, ' ' * len(_string.punctuation))
    text = f" {title.lower().translate(_trans)} {desc.lower().translate(_trans)} "
    # 检查允许白名单
    for allowed in LOW_VISUAL_PREMIUM_ALLOWLIST:
        if allowed in text:
            return False
    # 检查黑名单关键词（完整词匹配）
    for kw in LOW_VISUAL_PREMIUM_KEYWORDS:
        if f" {kw} " in text or text.startswith(f"{kw} ") or text.endswith(f" {kw}"):
            # 命中排除关键词，但先检查是否有交互/结构创新信号
            if _has_interaction_innovation(text):
                return False  # 有创新信号，放行
            return True
    # 复合词检测：产品名以 ring 结尾（如 jiyuairing）且描述含健康指标
    title_lower = title.lower().translate(_trans)
    desc_lower = desc.lower().translate(_trans)
    ring_health_indicators = {
        "health", "sleep", "heart rate", "blood oxygen", "spo2",
        "fitness", "wellness", "activity track", "calorie", "step",
        "finger", "wearable ring", "body temperature",
    }
    if re.search(r"\bring\b", title_lower) or re.search(r"\b\w+ring\b", title_lower):
        for indicator in ring_health_indicators:
            if indicator in desc_lower:
                return True
    return False


def _has_interaction_innovation(text: str) -> bool:
    """检查文本是否包含交互/结构创新信号（卡扣、锁止机构、变形机制等）"""
    for signal in INTERACTION_INNOVATION_SIGNALS:
        if f" {signal} " in text or text.startswith(f"{signal} ") or text.endswith(f" {signal}"):
            return True
    return False


def _normalize_match_text(*parts: str) -> str:
    """标准化文本，便于短语匹配。"""
    import string as _string
    _trans = str.maketrans(_string.punctuation, ' ' * len(_string.punctuation))
    return " " + " ".join(str(p or "").lower().translate(_trans) for p in parts) + " "


def _find_keyword(text: str, keywords: set[str]) -> str | None:
    """返回命中的第一个关键词。"""
    for kw in sorted(keywords, key=len, reverse=True):
        normalized_kw = kw.lower().replace("-", " ")
        if f" {normalized_kw} " in text:
            return kw
    return None


def classify_personal_relevance(title: str, desc: str, category_info) -> tuple[str, str]:
    """
    Robin 个人相关性分层。

    core: 6 个主战场内，且有明确外观/CMF/结构/形态判断信号。
    edge: 边缘带电品类里少量新奇特机会，有迁移价值。
    watch: 有结构/交互启发，但不进入本轮 VIS 评分。
    exclude: 与带电硬件外观判断无关，前置排除。
    """
    if isinstance(category_info, dict):
        cat_slug = str(category_info.get("slug", ""))
        cat_name = str(category_info.get("name", ""))
    else:
        cat_slug = str(category_info or "")
        cat_name = ""

    text = _normalize_match_text(title, desc, cat_slug, cat_name)

    appearance_hit = _find_keyword(text, APPEARANCE_JUDGMENT_KEYWORDS)
    edge_value_hit = _find_keyword(text, EDGE_VALUE_KEYWORDS)
    has_structure_signal = _has_interaction_innovation(text)

    core_hit = _find_keyword(text, CORE_POWERED_HARDWARE_KEYWORDS)
    if core_hit and (appearance_hit or has_structure_signal):
        signal = appearance_hit or "结构/交互创新"
        return "core", f"主战场: {core_hit}; 外观判断信号: {signal}"
    if core_hit:
        return "watch", f"主战场但缺少外观判断信号: {core_hit}"

    adjacent_hit = _find_keyword(text, ADJACENT_POWERED_HARDWARE_KEYWORDS)
    if adjacent_hit and (edge_value_hit or has_structure_signal):
        signal = edge_value_hit or "结构/交互创新"
        return "edge", f"边缘机会: {adjacent_hit}; 新奇特/迁移信号: {signal}"
    if adjacent_hit:
        return "watch", f"相邻带电品类但价值信号不足: {adjacent_hit}"

    exclude_hit = _find_keyword(text, PERSONAL_RELEVANCE_EXCLUDE_KEYWORDS)
    if exclude_hit:
        return "exclude", f"非个人主战场品类: {exclude_hit}"

    if has_structure_signal and edge_value_hit:
        return "edge", f"非主战场但有强结构/迁移信号: {edge_value_hit}"

    if has_structure_signal:
        return "watch", "有结构/交互创新，但未命中带电硬件核心范围"

    return "exclude", "未同时命中主战场和外观判断信号"


# KS 图片 URL 模板：替换为 1024x768 尺寸
PHOTO_SIZE_RE = re.compile(r'(/photos/[^/]+/)original\.')

# 支持的币种对 USD 近似汇率（用于换算 pledges）
CURRENCY_TO_USD = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73,
    "AUD": 0.67, "NZD": 0.61, "SGD": 0.75, "HKD": 0.128,
    "JPY": 0.0067, "CHF": 1.12, "SEK": 0.096, "NOK": 0.094,
    "DKK": 0.145, "MXN": 0.058, "KRW": 0.00075,
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def normalize_category(cat_slug: str) -> str:
    """将 KS 原始 slug 映射到统一品类名"""
    slug = cat_slug.lower().replace("-", "_").replace(" ", "_")
    slug = slug.replace("/", "_")
    # 直接返回原始 slug（后续 AI 可进一步映射）
    return slug


def is_category_allowed(category_info) -> bool:
    """检查品类是否在白名单中且不在黑名单中"""
    slugs = set()

    if isinstance(category_info, dict):
        # KS v1 API 格式
        for key in ("slug", "name", "parent_name"):
            val = category_info.get(key, "")
            if val:
                slugs.add(str(val).lower().replace("-", "_").replace(" ", "_"))
                slugs.add(str(val).lower())
    elif isinstance(category_info, str):
        slugs.add(category_info.lower())

    # 检查黑名单
    for s in slugs:
        for banned in CATEGORY_BLACKLIST:
            if banned in s:
                return False

    # 检查白名单
    for s in slugs:
        for allowed in CATEGORY_WHITELIST:
            if allowed in s:
                return True

    return False


def get_usd_pledged(project: dict) -> float:
    """获取或估算项目的 USD 筹款金额"""
    usd = project.get("usd_pledged")
    if usd is not None and float(usd) > 0:
        return float(usd)

    # 尝试从 pledged + currency 换算
    pledged = float(project.get("pledged", 0) or 0)
    currency = project.get("currency", "USD").upper()
    rate = CURRENCY_TO_USD.get(currency, 1.0)
    return pledged * rate


def normalize_photo_url(raw_url: str) -> str:
    """将 KS 图片 URL 转换为 1024x768 尺寸"""
    if not raw_url:
        return ""
    # 替换 /original. 为合适的尺寸
    url = re.sub(r'/(original|full)\.', '/full/1024x768.', raw_url)
    return url


def parse_ks_timestamp(val) -> str:
    """解析 KS 时间戳为 YYYY-MM-DD HH:MM 格式"""
    if isinstance(val, (int, float)):
        if val > 1e12:  # 毫秒
            val /= 1000
        dt = datetime.fromtimestamp(val, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(val or "")


def flatten_project(project: dict) -> dict | None:
    """将 KS 原始项目数据展平为候选条目"""
    proj_id = project.get("id")
    if not proj_id:
        return None

    usd_pledged = get_usd_pledged(project)
    if usd_pledged < MIN_USD_PLEDGED:
        return None

    category_info = project.get("category", {})
    if not is_category_allowed(category_info):
        return None

    # 提取标题和简介
    title = str(project.get("name", "")).strip()
    desc = str(project.get("blurb", "")).strip()

    personal_tier, personal_reason = classify_personal_relevance(title, desc, category_info)
    if personal_tier not in PERSONAL_RELEVANCE_PASS_TIERS:
        return None

    # 过滤服饰/时尚类产品
    if is_fashion_product(title, desc):
        return None
    # 过滤纯功能导向的非视觉产品（枕头、厨具、运动器材、宠物用品等）
    if is_non_visual_product(title, desc):
        return None
    # 过滤视觉溢价低的功能导向产品（智能戒指、VR配件、刀具、厨具等）
    if is_low_visual_premium_product(title, desc):
        return None
    creator = project.get("creator", {})
    brand = (creator.get("name") or "").strip()
    if not brand:
        brand = "Unknown"

    # 品类
    if isinstance(category_info, dict):
        cat_slug = category_info.get("slug", "")
    else:
        cat_slug = str(category_info)

    # 图片
    photo_url = ""
    photo = project.get("photo")
    if isinstance(photo, dict):
        photo_url = photo.get("full", photo.get("1024x768", photo.get("small", "")))
    elif isinstance(photo, str):
        photo_url = normalize_photo_url(photo)

    # 时间
    launched = parse_ks_timestamp(project.get("launched_at", 0))
    created = parse_ks_timestamp(project.get("created_at", 0))
    launch_time = launched or created

    # 项目链接
    urls = project.get("urls", {})
    web_url = ""
    if isinstance(urls, dict):
        web_url = urls.get("web", {}).get("project", "")
    if not web_url:
        web_url = f"https://www.kickstarter.com/projects/{project.get('slug','')}/{proj_id}"

    # 位置
    location = project.get("location", {})
    if isinstance(location, dict):
        country = location.get("country", "")
    else:
        country = ""

    # 计算达成率和上线天数
    goal = float(project.get("goal", 0) or 0)
    pledged = float(project.get("pledged", 0) or 0)
    percent_funded = round((pledged / goal * 100), 1) if goal > 0 else 0

    # 上线天数
    days_since_launch = 0
    launched_at = project.get("launched_at")
    if launched_at:
        if isinstance(launched_at, (int, float)):
            if launched_at > 1e12:
                launched_at /= 1000
            days_since_launch = max(0, int((time.time() - launched_at) / 86400))

    state = project.get("state", "")

    return {
        "id": f"ks-{proj_id}",
        "brand": brand,
        "category": normalize_category(cat_slug),
        "title": title,
        "desc": desc,
        "time": launch_time,
        "url": web_url,
        "tags": [cat_slug] if cat_slug else [],
        "image": photo_url,
        "source": "kickstarter",
        "sourceName": "Kickstarter",
        "personalRelevanceTier": personal_tier,
        "personalRelevanceReason": personal_reason,
        "ksData": {
            "goal": goal,
            "pledged": pledged,
            "usdPledged": usd_pledged,
            "backersCount": int(project.get("backers_count", 0) or 0),
            "currency": project.get("currency", "USD"),
            "state": state,
            "staffPick": bool(project.get("staff_pick", False)),
            "percentFunded": percent_funded,
            "daysSinceLaunch": days_since_launch,
        },
        "country": country,
    }


# ---------------------------------------------------------------------------
# 下载与处理
# ---------------------------------------------------------------------------

def download_file(url: str, dest: str, chunk_size: int = 8192 * 1024) -> str:
    """下载文件到指定路径，显示进度"""
    print(f"[下载] {url}")
    print(f"[目标] {dest}")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    print(f"\r  进度: {downloaded / 1024 / 1024:.1f} MB / {total / 1024 / 1024:.1f} MB ({pct:.0f}%)", end="")
        print()
    print(f"[完成] 下载完成 ({downloaded / 1024 / 1024:.1f} MB)")
    return dest


def process_jsonl_gz(gz_path: str, max_candidates: int = 500) -> dict:
    """流式处理 .json.gz 文件，返回候选集"""
    total = 0
    filtered = 0
    edge_count = 0
    edge_limit = max(1, int(max_candidates * EDGE_CANDIDATE_MAX_RATIO))
    candidates = []
    seen_ids = set()

    print(f"[处理] 开始解析 {gz_path} ...")
    t0 = time.time()

    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            total += 1
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 兼容新格式：数据包裹在 data 键中
            project = raw.get("data", raw)
            # 跳过 wrapper header 行（有 table_id 无 data）
            if "table_id" in raw and "data" not in raw:
                continue

            # 去重
            proj_id = project.get("id")
            if not proj_id or proj_id in seen_ids:
                continue
            seen_ids.add(proj_id)

            # 展平 + 筛选
            candidate = flatten_project(project)
            if candidate is None:
                continue
            if candidate.get("personalRelevanceTier") == "edge":
                if edge_count >= edge_limit:
                    continue
                edge_count += 1

            filtered += 1
            candidates.append(candidate)

            if total % 10000 == 0:
                elapsed = time.time() - t0
                speed = total / elapsed if elapsed > 0 else 0
                print(f"\r  已处理: {total} 行, 候选: {filtered} ({speed:.0f} 行/秒)", end="")

            if len(candidates) >= max_candidates:
                print(f"\n[限制] 达到最大候选数 {max_candidates}，停止处理")
                break

    elapsed = time.time() - t0
    print(f"\n[完成] 处理 {total} 行, 筛选出 {filtered} 个候选, 耗时 {elapsed:.1f}s")

    return {
        "totalProcessed": total,
        "totalFiltered": filtered,
        "candidates": candidates,
    }


def find_latest_dataset_url() -> str | None:
    """从 webrobots.io 页面找到最新数据集 URL"""
    print("[获取] 正在从 webrobots.io 查找最新数据集...")
    try:
        req = urllib.request.Request(
            "https://webrobots.io/kickstarter-datasets/",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[错误] 无法访问 webrobots.io: {e}")
        return None

    # 匹配 .json.gz 文件的完整 URL
    pattern = re.compile(
        r'https?://s3\.amazonaws\.com/weruns/forfun/Kickstarter/'
        r'Kickstarter_(\d{4}-\d{2}-\d{2})[^"\s]*\.json\.gz'
    )
    matches = pattern.findall(html)

    if not matches:
        print("[错误] 未在页面中找到数据集 URL")
        return None

    # 按日期排序取最新
    dates = sorted(set(matches), reverse=True)
    latest_date = dates[0]
    print(f"[信息] 最新数据集日期: {latest_date}")

    # 重新搜索完整 URL
    url_pattern = re.compile(
        r'(https?://s3\.amazonaws\.com/weruns/forfun/Kickstarter/'
        r'Kickstarter_' + re.escape(latest_date) + r'[^"\s]*\.json\.gz)'
    )
    url_matches = url_pattern.findall(html)
    if url_matches:
        return url_matches[0]
    return None


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def check_latest_dataset_date() -> str | None:
    """仅检查 webrobots.io 上的最新数据集日期，不下载文件"""
    print("[检查] 正在查询 webrobots.io 最新数据集日期...")
    try:
        req = urllib.request.Request(
            "https://webrobots.io/kickstarter-datasets/",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[错误] 无法访问 webrobots.io: {e}")
        return None

    pattern = re.compile(
        r'Kickstarter_(\d{4}-\d{2}-\d{2})[^"\s]*\.json\.gz'
    )
    matches = pattern.findall(html)
    if not matches:
        return None

    dates = sorted(set(matches), reverse=True)
    latest_date = dates[0]
    print(f"[信息] 最新数据集日期: {latest_date}")
    return latest_date


def process_incremental(gz_path: str, since_date: str, max_candidates: int = 500) -> dict:
    """增量模式：只处理在 since_date 之后上线的项目"""
    since_dt = datetime.strptime(since_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    since_ts = since_dt.timestamp()

    total = 0
    filtered = 0
    edge_count = 0
    edge_limit = max(1, int(max_candidates * EDGE_CANDIDATE_MAX_RATIO))
    candidates = []
    seen_ids = set()

    print(f"[增量] 只处理 {since_date} 之后上线的项目...")

    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            total += 1
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue

            project = raw.get("data", raw)
            if "table_id" in raw and "data" not in raw:
                continue

            proj_id = project.get("id")
            if not proj_id or proj_id in seen_ids:
                continue
            seen_ids.add(proj_id)

            # 时间过滤
            launched_at = project.get("launched_at", 0)
            if isinstance(launched_at, (int, float)):
                if launched_at > 1e12:
                    launched_at /= 1000
                if launched_at < since_ts:
                    continue

            candidate = flatten_project(project)
            if candidate is None:
                continue
            if candidate.get("personalRelevanceTier") == "edge":
                if edge_count >= edge_limit:
                    continue
                edge_count += 1

            filtered += 1
            candidates.append(candidate)

            if len(candidates) >= max_candidates:
                print(f"\n[限制] 达到最大候选数 {max_candidates}，停止处理")
                break

    print(f"[完成] 增量处理 {total} 行, 筛选出 {filtered} 个候选")
    return {
        "totalProcessed": total,
        "totalFiltered": filtered,
        "candidates": candidates,
    }


def scrape_discover_incremental(since_days: int = 3, max_pages: int = 10) -> dict:
    """
    通过 KS Discover 页面增量抓取近期新项目（无需下载全量数据）。
    使用 requests + 浏览器 UA，尝试获取 JSON 格式数据。
    如果失败，返回空结果并提示需要浏览器自动化。
    """
    # Kickstarter 品类映射（slug -> (category_id, name)）
    # 这些 ID 来自 KS Discover 页面的过滤参数
    DISCOVER_CATEGORIES = [
        ("product_design", 30),
        ("technology", 16),
        ("hardware", 27),
        ("wearables", 33),
        ("cameras", 10),
        ("audio", 12),
    ]

    all_candidates = []
    seen_ids = set()
    edge_count = 0
    edge_limit = max(1, int(500 * EDGE_CANDIDATE_MAX_RATIO))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.kickstarter.com/discover/",
    }

    print(f"[Discover] 正在抓取近 {since_days} 天的 KS 新项目...")

    for cat_name, cat_id in DISCOVER_CATEGORIES:
        for page in range(1, max_pages + 1):
            url = (
                f"https://www.kickstarter.com/discover/advanced"
                f"?category_id={cat_id}&sort=newest&format=json&page={page}"
            )
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    print(f"[Discover] ⚠️ 被 Cloudflare 拦截 ({cat_name} page {page})")
                    print(f"[Discover] 建议使用浏览器自动化模式，运行: agent-browser open {url}")
                    continue
                else:
                    print(f"[Discover] HTTP 错误 {e.code}: {e.reason}")
                    break
            except Exception as e:
                print(f"[Discover] 抓取失败 ({cat_name} page {page}): {e}")
                break

            # 解析响应 — KS JSON 格式
            projects = data if isinstance(data, list) else data.get("projects", [])
            if not projects:
                break

            for proj in projects:
                candidate = flatten_project(proj)
                if candidate is None:
                    continue
                if candidate["id"] in seen_ids:
                    continue
                if candidate.get("personalRelevanceTier") == "edge":
                    if edge_count >= edge_limit:
                        continue
                    edge_count += 1
                seen_ids.add(candidate["id"])
                all_candidates.append(candidate)

            if len(projects) < 12:  # 最后一页
                break

    print(f"[Discover] 共抓取 {len(all_candidates)} 个候选")
    return {
        "sourceDate": datetime.now().strftime("%Y-%m-%d"),
        "totalProcessed": len(all_candidates),
        "totalFiltered": len(all_candidates),
        "candidates": all_candidates,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Kickstarter 数据集下载与预筛选"
    )
    parser.add_argument(
        "--url",
        help="数据集 .json.gz 文件的直接下载 URL",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动从 webrobots.io 获取最新数据集 URL",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 JSON 文件路径（默认: products/ks-candidates.json）",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=500,
        help="最大候选数（默认: 500）",
    )
    parser.add_argument(
        "--source-date",
        help="手动指定数据来源日期（YYYY-MM-DD），覆写自动检测",
    )
    parser.add_argument(
        "--since",
        help="增量模式：只处理此日期之后上线的项目（YYYY-MM-DD）",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查最新数据集日期，不下载",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="使用 Discover 增量抓取模式（无需下载全量数据）",
    )
    parser.add_argument(
        "--discover-days",
        type=int,
        default=3,
        help="Discover 模式：抓取近 N 天的新项目（默认: 3）",
    )

    args = parser.parse_args()

    # --check-only：仅检查日期
    if args.check_only:
        latest = check_latest_dataset_date()
        if latest:
            print(f"LATEST_DATE={latest}")
        sys.exit(0 if latest else 1)

    # --discover：增量抓取模式
    if args.discover:
        result = scrape_discover_incremental(
            since_days=args.discover_days, max_pages=10
        )
        output_path = Path(args.output) if args.output else (
            Path(__file__).parent.parent / "products" / "ks-candidates.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[完成] Discover 模式输出 {result['totalFiltered']} 个候选到 {output_path}")
        return

    # 确定 URL
    url = args.url
    if not url and args.auto:
        url = find_latest_dataset_url()
        if not url:
            print("[错误] 无法自动获取数据集 URL")
            sys.exit(1)

    if not url:
        print("[错误] 请提供 --url 或使用 --auto，或改用 --discover")
        sys.exit(1)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent.parent / "products" / "ks-candidates.json"

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 提取来源日期
    source_date = args.source_date
    if not source_date:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', url)
        if date_match:
            source_date = date_match.group(1)

    # 下载
    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        download_file(url, tmp_path)

        # 处理：增量 or 全量
        if args.since:
            result = process_incremental(
                tmp_path, since_date=args.since, max_candidates=args.max
            )
        else:
            result = process_jsonl_gz(tmp_path, max_candidates=args.max)

        result["sourceDate"] = source_date or datetime.now().strftime("%Y-%m-%d")

        # 写入
        print(f"[输出] 写入 {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        file_size = output_path.stat().st_size
        print(f"[完成] 已输出 {result['totalFiltered']} 个候选 ({file_size / 1024:.0f} KB)")

    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print("[清理] 已删除临时文件")


if __name__ == "__main__":
    main()
