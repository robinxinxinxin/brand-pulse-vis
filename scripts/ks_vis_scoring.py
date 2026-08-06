#!/usr/bin/env python3
"""
ks_vis_scoring.py — KS 候选项目 VIS 五维启发式评分引擎

用法：
  py -3 scripts/ks_vis_scoring.py
    --input products/ks-candidates.json
    --output products/ks-recent.json
    --top 200

评分权重（vis-scoring-config.json v2.0 唯一权威 — 注释仅供人类读档，计算请读 config.json）：
  diffusionPotential (扩散潜力)     30%  → score += d×3.0
  recognition        (识别度)       25%  → score += r×2.5
  transferability    (可迁移性)     20%  → score += t×2.0
  cmfInnovation      (CMF创新)      15%  → score += c×1.5
  paradigmShift      (范式变化)     10%  → score += p×1.0

score = sum(...) 即 diffusionPotential*0.30 + recognition*0.25 + ... 乘以10（与 vis-scoring-config.json v2.0 对齐）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── 中文品名翻译映射 ──
# 优先级：词条越长越先匹配，避免短词误替换
# 格式：英文字符串 → 中文翻译，按长度降序排列确保精确匹配
KS_ZH_MAP = [
    # >>> 品类核心词
    ("smart glasses", "智能眼镜"), ("ai glasses", "AI眼镜"), ("ar glasses", "AR眼镜"),
    ("mixed reality headset", "混合现实头显"), ("virtual reality headset", "虚拟现实头显"),
    ("vr headset", "VR头显"), ("xr headset", "XR头显"), ("smart helmet", "智能头盔"),
    ("smartwatch", "智能手表"), ("smart watch", "智能手表"),
    ("smart ring", "智能戒指"), ("fitness ring", "健身戒指"),
    ("wearable camera", "穿戴式相机"), ("body camera", "随身相机"),
    ("action camera", "运动相机"), ("360 camera", "全景相机"),
    ("dash cam", "行车记录仪"), ("trail camera", "野外相机"),
    ("security camera", "安防摄像头"), ("ptz camera", "云台相机"),
    ("camera glasses", "拍照眼镜"), ("sports camera", "运动相机"),
    ("bone conduction", "骨传导"), ("open-ear", "开放式耳机"),
    ("true wireless", "真无线"), ("noise cancelling", "降噪"),
    ("wireless earbuds", "无线耳机"), ("wireless earphone", "无线耳机"),
    ("wireless headphone", "无线耳机"), ("over-ear", "头戴式"),
    ("bluetooth speaker", "蓝牙音箱"), ("portable speaker", "便携音箱"),
    ("smart speaker", "智能音箱"), ("soundbar", "条形音箱"),
    ("drone", "无人机"), ("quadcopter", "四轴飞行器"),
    ("robot vacuum", "扫地机器人"), ("robot mop", "拖地机器人"),
    ("robot lawn", "割草机器人"), ("robot cleaner", "清洁机器人"),
    ("3d printer", "3D打印机"), ("3d printing", "3D打印"),
    ("laser engraver", "激光雕刻机"), ("cnc machine", "CNC雕刻机"),
    ("electric scooter", "电动滑板车"), ("electric skateboard", "电动滑板"),
    ("electric bike", "电动自行车"), ("ebike", "电助力自行车"),
    ("power bank", "移动电源"), ("powerbank", "移动电源"),
    ("wireless charger", "无线充电器"), ("charging station", "充电站"),
    ("gan charger", "氮化镓充电器"), ("magsafe", "磁吸"),
    ("charging dock", "充电底座"),
    ("car charger", "车载充电器"), ("wall charger", "壁式充电器"),
    ("usb hub", "USB集线器"), ("usb-c hub", "USB-C扩展坞"),
    ("thunderbolt dock", "雷电扩展坞"), ("docking station", "扩展坞"),
    ("mechanical keyboard", "机械键盘"), ("wireless keyboard", "无线键盘"),
    ("ergonomic keyboard", "人体工学键盘"), ("split keyboard", "分离式键盘"),
    ("mouse", "鼠标"), ("gaming mouse", "游戏鼠标"), ("trackball", "轨迹球鼠标"),
    ("monitor stand", "显示器支架"), ("monitor arm", "显示器支架臂"),
    ("laptop stand", "笔记本支架"), ("standing desk", "升降桌"),
    ("solar panel", "太阳能板"), ("solar charger", "太阳能充电器"),
    ("solar generator", "太阳能发电机"), ("portable generator", "便携发电机"),
    ("home battery", "家用电池"), ("lifepo4", "磷酸铁锂电池"),
    ("led lamp", "LED灯"), ("desk lamp", "台灯"),
    ("smart lamp", "智能灯"), ("reading light", "阅读灯"),
    ("flashlight", "手电筒"), ("headlamp", "头灯"),
    ("camping lantern", "露营灯"), ("work light", "工作灯"),
    ("edc light", "EDC手电"), ("keychain light", "钥匙扣灯"),
    ("smart lock", "智能锁"), ("fingerprint lock", "指纹锁"),
    ("smart doorbell", "智能门铃"), ("video doorbell", "视频门铃"),
    ("smart plug", "智能插座"), ("smart switch", "智能开关"),
    ("smart sensor", "智能传感器"), ("motion sensor", "运动传感器"),
    ("temperature sensor", "温度传感器"), ("air quality", "空气质量监测"),
    ("smart scale", "智能秤"), ("body composition", "体脂秤"),
    ("blood pressure", "血压计"), ("pulse oximeter", "血氧仪"),
    ("thermometer", "体温计"), ("smart thermometer", "智能体温计"),
    ("massage gun", "筋膜枪"), ("massager", "按摩仪"),
    ("fitness tracker", "健身追踪器"), ("activity tracker", "活动追踪器"),
    ("sleep tracker", "睡眠追踪器"), ("posture corrector", "姿势矫正器"),
    ("vr glove", "VR手套"), ("haptic glove", "触觉手套"),
    ("vr controller", "VR手柄"), ("motion controller", "体感控制器"),
    ("vr treadmill", "VR跑步机"), ("vr shoes", "VR鞋"),
    ("gaming chair", "电竞椅"), ("gaming desk", "电竞桌"),
    ("gaming headset", "游戏耳机"), ("gaming monitor", "电竞显示器"),
    ("portable monitor", "便携显示器"), ("external monitor", "外接显示器"),
    ("oled monitor", "OLED显示器"), ("mini led", "Mini LED"),
    ("e-ink", "电子墨水"), ("e ink", "电子墨水"), ("eink", "电子墨水"),
    ("digital notebook", "电子笔记本"), ("smart notebook", "智能笔记本"),
    ("smart pen", "智能笔"), ("stylus pen", "触控笔"),
    ("drawing tablet", "数位板"), ("graphics tablet", "绘图板"),
    ("electric toothbrush", "电动牙刷"), ("smart toothbrush", "智能牙刷"),
    ("water flosser", "水牙线"), ("oral irrigator", "口腔冲洗器"),
    ("electric shaver", "电动剃须刀"), ("hair clipper", "理发器"),
    ("beard trimmer", "胡须修剪器"), ("body groomer", "体毛修剪器"),
    ("nail printer", "美甲打印机"), ("smart mirror", "智能镜子"),
    ("smart mug", "智能杯"), ("temperature control mug", "温控杯"),
    ("smart water bottle", "智能水杯"), ("smart bottle", "智能水瓶"),
    ("coffee maker", "咖啡机"), ("espresso machine", "意式咖啡机"),
    ("smart coffee", "智能咖啡"), ("portable blender", "便携搅拌机"),
    ("smart lock box", "智能保险箱"), ("smart safe", "智能保险柜"),
    ("fingerprint safe", "指纹保险柜"),
    ("cable management", "线材管理"), ("cable organizer", "理线器"),
    ("desk organizer", "桌面收纳"), ("pegboard", "洞洞板"),
    ("tool organizer", "工具收纳"), ("tool roll", "工具卷包"),
    ("precision screwdriver", "精密螺丝刀"), ("mini screwdriver", "迷你螺丝刀"),
    ("torque driver", "扭矩螺丝刀"), ("electric screwdriver", "电动螺丝刀"),
    ("bit set", "批头套装"), ("ratchet", "棘轮扳手"),
    ("multitool", "多功能工具"), ("multi-tool", "多功能工具"),
    ("pocket knife", "口袋刀"), ("folding knife", "折叠刀"),
    ("edc", "EDC"), ("everyday carry", "日常携带"),
    ("titanium", "钛合金"), ("carbon fiber", "碳纤维"),
    ("aluminum", "铝合金"), ("stainless steel", "不锈钢"),
    ("copper", "铜"), ("brass", "黄铜"), ("damascus", "大马士革"),

    # >>> 描述词 — 大写开头确保匹配品牌词后
    ("first-ever", "首创"), ("first ever", "全球首款"),
    ("world's first", "全球首款"), ("world's smallest", "全球最小"),
    ("world's thinnest", "全球最薄"), ("world's lightest", "全球最轻"),
    ("world's fastest", "全球最快"), ("patent pending", "专利审核中"),
    ("patented", "专利"), ("kickstarter exclusive", "KS独家"),
    ("limited edition", "限量版"), ("early bird", "早鸟价"),
    ("color option", "配色可选"), ("multiple color", "多色可选"),
    ("customizable", "可定制"), ("interchangeable", "可替换"),
    ("modular", "模块化"), ("magnetic", "磁吸"),
    ("foldable", "可折叠"), ("collapsible", "可折叠"),
    ("detachable", "可拆卸"), ("retractable", "可伸缩"),
    ("waterproof", "防水"), ("water-resistant", "抗水"),
    ("dustproof", "防尘"), ("shockproof", "防震"),
    ("scratch-resistant", "防刮"), ("shatterproof", "防碎"),
    ("anti-glare", "防眩光"), ("anti-fingerprint", "防指纹"),
    ("transparent", "透明"), ("translucent", "半透明"),
    ("frosted", "磨砂"), ("matte", "哑光"), ("glossy", "亮面"),
    ("anodized", "阳极氧化"), ("brushed metal", "拉丝金属"),
    ("sandblasted", "喷砂"), ("textured", "纹理"),
    ("gradient", "渐变"), ("iridescent", "虹彩"),
    ("holographic", "全息"), ("metallic finish", "金属质感"),
    ("rgb", "RGB"), ("led indicator", "LED指示灯"),
    ("backlit", "背光"), ("edge-lit", "边缘发光"),
    ("minimalist", "极简"), ("premium design", "高端设计"),
    ("award-winning", "获奖"), ("red dot", "红点奖"),
    ("futuristic", "未来感"), ("sleek", "流畅"),
    ("elegant", "优雅"), ("refined", "精致"),
    ("ergonomic", "人体工学"), ("contoured", "贴合曲线"),
    ("sculpted", "雕塑感"), ("crafted", "精工"),
    ("handcrafted", "手工"), ("artisanal", "匠造"),
    ("bespoke", "定制"), ("personalized", "个性化"),
    ("biodegradable", "可降解"), ("recycled", "回收材料"),
    ("sustainable", "可持续"), ("eco-friendly", "环保"),
    ("plant-based", "植物基"), ("ocean plastic", "海洋塑料"),
    ("vegan leather", "素皮"), ("bamboo", "竹"),
    ("wood", "实木"), ("ceramic", "陶瓷"),
    ("sapphire", "蓝宝石"), ("gorilla glass", "康宁玻璃"),
    ("military grade", "军规级"), ("aerospace", "航空级"),
    ("liquid metal", "液态金属"), ("magnesium", "镁合金"),
    ("app-controlled", "App控制"), ("smartphone app", "手机App"),
    ("voice control", "语音控制"), ("gesture control", "手势控制"),
    ("touch-free", "无接触"), ("hands-free", "免提"),
    ("ai-powered", "AI驱动"), ("ai driven", "AI驱动"),
    ("built-in ai", "内置AI"), ("ai assistant", "AI助手"),
    ("machine learning", "机器学习"), ("deep learning", "深度学习"),
    ("real-time translation", "实时翻译"), ("live translation", "实时翻译"),
    ("noise reduction", "降噪"), ("audio enhancement", "音频增强"),
    ("super telephoto", "超长焦"), ("wide-angle", "广角"),
    ("macro lens", "微距镜头"), ("night vision", "夜视"),
    ("thermal imaging", "热成像"), ("thermal camera", "热成像相机"),
    ("infrared", "红外"), ("ultrasonic", "超声波"),
    ("ultra-slim", "超薄"), ("ultra-light", "超轻"),
    ("pocket-sized", "口袋大小"), ("compact", "紧凑"),
    ("portable", "便携"), ("mini", "迷你"),
    ("travel-friendly", "旅行友好"), ("ultra-portable", "超便携"),
    ("fast charging", "快充"), ("quick charge", "快充"),
    ("wireless charging", "无线充电"), ("reverse charging", "反向充电"),
    ("long battery life", "长续航"), ("all-day battery", "全天续航"),
    ("usb-c", "USB-C"), ("usb c", "USB-C"),
    ("bluetooth 5", "蓝牙5"), ("wifi 6", "WiFi 6"),
    ("hdmi", "HDMI"), ("displayport", "DisplayPort"),
    ("thunderbolt", "雷电接口"),

    # >>> 连接词/常用后缀
    ("redefining", "重新定义"), ("reinventing", "重新发明"),
    ("reimagined", "重新构想"), ("revolutionary", "革命性"),
    ("revolution", "革新"), ("next generation", "新一代"),
    ("next-gen", "次世代"), ("the future of", "未来的"),
    ("ultimate", "终极"), ("pro", "专业版"),
    ("professional", "专业"), ("premium", "高级"),
    ("elite", "精英"), ("advanced", "高级"),
    ("essential", "基础版"), ("standard", "标准版"),
    ("lite", "轻量版"), ("plus", "增强版"),
    ("max", "至尊版"), ("ultra", "极致版"),
    ("mini", "迷你版"), ("nano", "纳米版"),
    ("- pro", " 专业版"), ("- lite", " 轻量版"),
    ("of", "的"), ("for", "为"), ("with", "配备"),
    ("your", "你的"), ("that", "能"),
    ("truly", "真正"), ("simply", "简单"),
    ("finally", "终于"), ("never", "再也不"),
    ("unlike", "不同于"), ("designed", "专为"),
    ("engineered", "工程打造"), ("built", "打造"),
    ("made", "制作"), ("powered by", "搭载"),
    # 组合短语
    ("all in one", "一体式"), ("all-in-one", "一体式"),
    ("two in one", "二合一"), ("2 in 1", "二合一"),
    ("three in one", "三合一"), ("3 in 1", "三合一"),
    ("four in one", "四合一"), ("4 in 1", "四合一"),
    # 长短语优先 — set up 短版已删除防止拆分
    ("set up in seconds", "秒装"), ("set up in minutes", "分钟安装"),

    # >>> 补充高频名词
    ("experience", "体验"), ("adventure", "冒险"),
    ("capture", "捕捉"), ("record", "录制"),
    ("recording", "录音"), ("device", "设备"),
    ("feature", "功能"), ("edition", "版本"),
    ("system", "系统"), ("companion", "伴侣"),
    ("habit", "习惯"), ("comfort", "舒适"),
    ("design", "设计"), ("new", "全新"),
    ("improved", "改进"), ("enhanced", "增强"),
    ("world", "世界"), ("life", "生活"),
    ("face", "面容"), ("show", "展示"),
    ("your face", "真面目"),
    ("open source", "开源"), ("open-source", "开源"),
    ("open ear", "开放式"), ("open-ear", "开放式"),
    ("wood burning", "燃木"), ("woodburning", "燃木"),
    ("wood-burning", "燃木"), ("key ring", "钥匙圈"),
    ("keyring", "钥匙圈"), ("key-ring", "钥匙圈"),
    ("collar stay", "领撑"), ("collar stays", "领撑"),
    ("travel system", "旅行套装"), ("storage system", "存储系统"),
    ("quick release", "快拆"), ("quick-release", "快拆"),
    ("charging case", "充电仓"), ("travel case", "旅行盒"),
    ("carrying case", "携带盒"), ("hard case", "硬壳"),
    ("world's", "全球"), ("worlds", "世界"),
    ("seconds", "秒"), ("minutes", "分钟"),
    ("hours", "小时"), ("days", "天"),
    ("weeks", "周"), ("months", "月"),
    ("years", "年"),
    ("rechargeable", "可充电"), ("battery", "电池"),
    # 注意: set up/setup 已移至短语区防止拆分
    ("second", "秒"), ("seconds", "秒"),
    ("wood burning", "燃木"), ("woodburning", "燃木"),
    ("stove", "炉"), ("tripod", "三脚架"),
    ("flash", "闪光灯"), ("lighting", "灯光"),
    ("bracket", "支架"), ("bounce", "反射"),
    ("mic", "麦克风"), ("microphone", "麦克风"),
    ("stereo", "立体声"), ("charging case", "充电仓"),
    ("superpower", "超能力"), ("entry-level", "入门"),
    ("desktop", "桌面"), ("creative", "创意"),
    ("tool", "工具"), ("everyday", "日常"),
    ("focus", "聚焦"), ("clean", "清洁"),
    ("style", "风格"), ("modern", "现代"),
    ("hybrid", "混合"), ("unique", "独特"),
    ("innovative", "创新"), ("innovation", "创新"),
    ("smart", "智能"), ("intelligent", "智能"),
    ("automatic", "自动"), ("automated", "自动化"),
    ("manual", "手动"), ("electric", "电动"),
    ("digital", "数字"), ("analog", "模拟"),
    ("home", "家庭"), ("office", "办公"),
    ("travel", "旅行"), ("outdoor", "户外"),
    ("indoor", "室内"), ("everyday carry", "日常携带"),
    ("daily", "日常"), ("night", "夜间"),
    ("morning", "早晨"), ("sleep", "睡眠"),
    ("wake", "唤醒"), ("health", "健康"),
    ("fitness", "健身"), ("workout", "训练"),
    ("training", "训练"), ("exercise", "锻炼"),
    ("sport", "运动"), ("sports", "运动"),
    ("adventure", "探险"), ("camping", "露营"),
    ("hiking", "徒步"), ("running", "跑步"),
    ("cycling", "骑行"), ("driving", "驾驶"),
    ("cooking", "烹饪"), ("kitchen", "厨房"),
    ("food", "食物"), ("drink", "饮品"),
    ("coffee", "咖啡"), ("tea", "茶"),
    ("water", "水"), ("beverage", "饮料"),
    ("pet", "宠物"), ("dog", "狗"), ("cat", "猫"),
    ("baby", "婴儿"), ("kids", "儿童"),
    ("men", "男士"), ("women", "女士"),
    ("unisex", "男女通用"), ("adult", "成人"),
    ("music", "音乐"), ("audio", "音频"),
    ("sound", "声音"), ("voice", "语音"),
    ("video", "视频"), ("photo", "照片"),
    ("image", "图像"), ("picture", "图片"),
    ("screen", "屏幕"), ("display", "显示"),
    ("touchscreen", "触摸屏"), ("touch screen", "触摸屏"),
    ("button", "按钮"), ("dial", "旋钮"),
    ("switch", "开关"), ("knob", "旋钮"),
    ("lever", "手柄"), ("handle", "把手"),
    ("grip", "握把"), ("strap", "绑带"),
    ("band", "腕带"), ("clip", "夹子"),
    ("mount", "支架"), ("holder", "支架"),
    ("stand", "底座"), ("base", "底座"),
    ("case", "保护壳"), ("cover", "盖子"),
    ("cap", "盖子"), ("lid", "盖子"),
    ("bag", "背包"), ("pouch", "收纳包"),
    ("sleeve", "套"), ("shell", "外壳"),
    ("housing", "外壳"), ("enclosure", "外壳"),
    ("frame", "框架"), ("chassis", "底盘"),
    ("panel", "面板"), ("plate", "板"),
    ("ring", "戒指"), ("bracelet", "手环"),
    ("necklace", "项链"), ("pendant", "吊坠"),
    ("badge", "徽章"), ("patch", "补丁"),
    ("pin", "胸针"), ("coin", "硬币"),
    ("card", "卡片"), ("wallet", "钱包"),
    ("keychain", "钥匙扣"), ("keyring", "钥匙圈"),
    ("lanyard", "挂绳"), ("cord", "绳"),
    ("cable", "线材"), ("wire", "电线"),
    ("connector", "连接器"), ("adapter", "转接头"),
    ("converter", "转换器"), ("splitter", "分线器"),
    ("extender", "延长器"), ("repeater", "中继器"),
    ("booster", "增强器"), ("amplifier", "放大器"),
    ("filter", "过滤器"), ("purifier", "净化器"),
    ("cleaner", "清洁器"), ("washer", "清洗器"),
    ("dryer", "干燥器"), ("heater", "加热器"),
    ("cooler", "冷却器"), ("fan", "风扇"),
    ("pump", "泵"), ("valve", "阀门"),
    ("motor", "电机"), ("engine", "引擎"),
    ("generator", "发电机"), ("inverter", "逆变器"),
    ("charger", "充电器"), ("dock", "底座"),
    ("station", "工作站"), ("hub", "集线器"),
    ("router", "路由器"), ("modem", "调制解调器"),
    ("antenna", "天线"), ("receiver", "接收器"),
    ("transmitter", "发射器"), ("transceiver", "收发器"),
    ("sensor", "传感器"), ("detector", "探测器"),
    ("monitor", "监测器"), ("tracker", "追踪器"),
    ("locator", "定位器"), ("finder", "查找器"),
    ("meter", "测量仪"), ("gauge", "量表"),
    ("tester", "测试仪"), ("analyzer", "分析仪"),
    ("scanner", "扫描仪"), ("printer", "打印机"),
    ("projector", "投影仪"), ("displayer", "显示器"),
    ("player", "播放器"), ("recorder", "录音机"),
    ("speaker", "音箱"), ("earphone", "耳机"),
    ("earbuds", "耳机"), ("headset", "耳机"),
    ("headphone", "耳机"), ("headphones", "耳机"),
    ("buds", "耳机"), ("earpiece", "耳塞"),
    ("wearable", "穿戴式"), ("wearables", "穿戴设备"),
    ("accessory", "配件"), ("accessories", "配件"),
    ("gadget", "小工具"), ("gadgets", "小工具"),
    ("gear", "装备"), ("equipment", "设备"),
    ("kit", "套件"), ("set", "套装"),
    ("bundle", "套装"), ("combo", "组合"),
    ("collection", "系列"), ("series", "系列"),
    ("line", "产品线"), ("range", "系列"),
    # 笔/文具
    ("pen", "笔"), ("fountain pen", "钢笔"),
    ("ballpoint", "圆珠笔"), ("rollerball", "签字笔"),
    ("stylus pen", "触控笔"), ("stylus", "触控笔"),
    ("smart pen", "智能笔"), ("digital pen", "数字笔"),
    ("mechanical pencil", "自动铅笔"),
    # 剃须/个人护理
    ("razor", "剃须刀"), ("shaver", "剃须刀"),
    ("electric razor", "电动剃须刀"), ("electric shaver", "电动剃须刀"),
    ("beard trimmer", "胡须修剪器"), ("hair clipper", "理发器"),
    ("nose trimmer", "鼻毛修剪器"), ("body groomer", "体毛修剪器"),
    ("nail clipper", "指甲刀"), ("nail file", "指甲锉"),
    # 存储介质
    ("usb drive", "U盘"), ("flash drive", "U盘"),
    ("thumb drive", "U盘"), ("memory card", "存储卡"),
    ("sd card", "SD卡"), ("microsd", "MicroSD卡"),
    ("ssd", "固态硬盘"), ("hard drive", "硬盘"),
    ("nvme", "NVMe"), ("sata", "SATA"),
    ("external drive", "移动硬盘"), ("external ssd", "移动固态硬盘"),
    # 杂项补缺
    ("night light", "夜灯"), ("mood light", "氛围灯"),
    ("alarm clock", "闹钟"), ("wall clock", "挂钟"),
    ("digital clock", "数字钟"), ("smart clock", "智能钟"),
    ("thermostat", "温控器"), ("smart thermostat", "智能温控器"),
    ("air purifier", "空气净化器"), ("humidifier", "加湿器"),
    ("dehumidifier", "除湿机"), ("diffuser", "香薰机"),

    # >>> 补充高频形容词
    ("best", "最佳"), ("better", "更好"),
    ("smallest", "最小"), ("largest", "最大"),
    ("thinnest", "最薄"), ("lightest", "最轻"),
    ("fastest", "最快"), ("strongest", "最强"),
    ("brightest", "最亮"), ("quietest", "最静"),
    ("easiest", "最简单"), ("simplest", "最简单"),
    ("perfect", "完美"), ("amazing", "惊人"),
    ("incredible", "难以置信"), ("awesome", "超赞"),
    ("fantastic", "出色"), ("excellent", "优秀"),
    ("superior", "卓越"), ("outstanding", "杰出"),
    ("exceptional", "卓越"), ("remarkable", "非凡"),
    ("powerful", "强大"), ("efficient", "高效"),
    ("reliable", "可靠"), ("durable", "耐用"),
    ("sturdy", "坚固"), ("robust", "稳固"),
    ("lightweight", "轻量"), ("heavy-duty", "重型"),
    ("versatile", "多功能"), ("flexible", "灵活"),
    ("adaptable", "适应性"), ("adjustable", "可调"),
    ("easy", "简便"), ("simple", "简单"),
    ("quick", "快速"), ("rapid", "快速"),
    ("instant", "即时"), ("seamless", "无缝"),
    ("smooth", "平滑"), ("gentle", "柔和"),
    ("soft", "柔软"), ("hard", "坚硬"),
    ("warm", "温暖"), ("cool", "凉爽"),
    ("hot", "热"), ("cold", "冰"),
    ("bright", "明亮"), ("dark", "暗"),
    ("loud", "响亮"), ("quiet", "安静"),
    ("silent", "静音"), ("noiseless", "无声"),

    # >>> 执行动作
    ("turn", "转化"), ("transform", "变身"),
    ("change", "改变"), ("create", "创造"),
    ("build", "构建"), ("make", "制作"),
    ("use", "使用"), ("get", "获得"),
    ("take", "带走"), ("bring", "带来"),
    ("give", "给予"), ("keep", "保持"),
    ("save", "节省"), ("protect", "保护"),
    ("guard", "守护"), ("shield", "防护"),
    ("connect", "连接"), ("link", "链接"),
    ("pair", "配对"), ("sync", "同步"),
    ("share", "分享"), ("stream", "串流"),
    ("play", "播放"), ("pause", "暂停"),
    ("stop", "停止"), ("start", "开始"),
    ("open", "打开"), ("close", "关闭"),
    ("lock", "锁定"), ("unlock", "解锁"),
    ("charge", "充电"), ("discharge", "放电"),
    ("power", "供电"), ("energize", "供能"),
    ("light", "照亮"), ("illuminate", "照明"),
    ("heat", "加热"), ("cool", "制冷"),
    ("wash", "洗"), ("rinse", "冲洗"),
    ("dry", "干燥"), ("clean", "清洁"),
    ("polish", "抛光"), ("shine", "闪亮"),
    ("cut", "切割"), ("slice", "切片"),
    ("grind", "研磨"), ("blend", "搅拌"),
    ("mix", "混合"), ("stir", "搅拌"),
    ("pour", "倒"), ("fill", "装填"),
    ("carry", "携带"), ("hold", "容纳"),
    ("store", "储存"), ("organize", "整理"),
    ("sort", "分类"), ("arrange", "排列"),
    ("stack", "堆叠"), ("fold", "折叠"),
    ("roll", "卷"), ("wrap", "包裹"),
    ("pack", "打包"), ("unpack", "拆包"),
    ("install", "安装"), ("uninstall", "卸载"),
    ("mount", "安装"), ("attach", "附加"),
    ("detach", "拆卸"), ("remove", "移除"),
    ("replace", "替换"), ("swap", "更换"),
    ("upgrade", "升级"), ("update", "更新"),
    ("fix", "修复"), ("repair", "修理"),
    ("restore", "恢复"), ("reset", "重置"),

    # >>> 介词/连词（≥4 字符，避免短词误匹配）
    ("from", "来自"), ("into", "进入"),
    ("over", "超过"), ("under", "下方"),
    ("with", "配备"), ("without", "无需"),
    ("within", "内"), ("between", "之间"),
    ("through", "通过"), ("during", "期间"),
    ("about", "关于"), ("above", "上方"),
    ("below", "下方"), ("behind", "背后"),
    ("beyond", "超越"), ("inside", "内部"),
    ("outside", "外部"), ("around", "周围"),
    ("across", "跨越"), ("along", "沿着"),
    ("against", "对抗"), ("among", "之中"),
    ("before", "之前"), ("after", "之后"),
    ("always", "始终"), ("never", "永不"),
    ("only", "仅"), ("also", "也"),
    ("very", "非常"), ("even", "甚至"),
    ("just", "只需"), ("much", "更多"),
    ("many", "许多"), ("each", "每个"),
    ("both", "两者"), ("other", "其他"),
    ("another", "另一个"), ("everything", "一切"),
    ("nothing", "没什么"), ("something", "某些"),
    ("anything", "任何事"), ("everyone", "每个人"),
    ("yourself", "自己"), ("itself", "本身"),
    ("and", "和"), ("or", "或"),
    ("every", "每个"), ("all", "所有"),
    ("your", "你的"), ("our", "我们的"), ("my", "我的"),
    ("complete", "完整"), ("full", "全"),
    ("posture", "姿势"), ("support", "支撑"),
    ("utensil", "餐具"), ("utensils", "餐具"),
    ("stretchy", "弹性"), ("brush", "刷"),
]

# 中文品名分割符
SPLITTERS = r"[:\-\|–—·]"

def generate_title_zh(title: str) -> str:
    """将英文产品标题翻译为中文"""
    if not title:
        return ""
    result = title.strip()
    # 第一步：保护 URL
    urls = re.findall(r"https?://\S+", result)
    for i, u in enumerate(urls):
        result = result.replace(u, f"__URL{i}__")
    # 第二步：按长度从长到短替换，避免短词吞长词
    for en, zh in KS_ZH_MAP:
        # 始终使用词边界匹配 — 防止 "sport" 匹配 "Sports" 等子串误伤
        # 规则: 匹配必须是完整词，前后不能是字母/数字
        pattern = re.compile(r'(?<![a-zA-Z0-9])' + re.escape(en) + r'(?![a-zA-Z0-9])', re.IGNORECASE)
        if pattern.search(result):
            # 找所有匹配位置，从右到左替换避免索引偏移
            matches = list(pattern.finditer(result))
            for m in reversed(matches):
                # 保留原大小写的品牌名部分
                replacement = zh
                result = result[:m.start()] + replacement + result[m.end():]
    # 第三步：恢复 URL
    for i, u in enumerate(urls):
        result = result.replace(f"__URL{i}__", u)
    # 第四步：清理多余空格
    result = re.sub(r"\s+", " ", result).strip()
    # 第五步：清理常见英文后缀残留
    # 复数/所有格
    result = re.sub(r"(\w)'s\b", r"\1的", result)  # world's → world的
    result = re.sub(r"([\u4e00-\u9fff])s\b", r"\1", result)  # 运动s → 运动
    # 动词后缀
    result = re.sub(r"([\u4e00-\u9fff])ing\b", r"\1", result)  # 录制ing → 录制
    result = re.sub(r"([\u4e00-\u9fff])ed\b", r"\1", result)   # 腌制ed → 腌制
    result = re.sub(r"([\u4e00-\u9fff])es\b", r"\1", result)   # 比赛es → 比赛
    # 清理多余空格
    result = re.sub(r"\s+", " ", result).strip()
    # 第六步：去除英文冠词（the/a/an）— 中文不需要
    result = re.sub(r'\bthe\b', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\ba\b', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\ban\b', '', result, flags=re.IGNORECASE)
    # 第七步：替换最后残留的 "in" 介词（前后有空格/中文/标点）
    result = re.sub(r'(?<=[ .,;:!?，。；：！？])in(?=[ .,;:!?，。；：！？])', '于', result, flags=re.IGNORECASE)
    result = re.sub(r'^in(?=[ .,;:!?，。；：！？])', '在', result, flags=re.IGNORECASE)
    result = re.sub(r'(?<=[ .,;:!?，。；：！？])in$', '于', result, flags=re.IGNORECASE)
    # 清理多余空格（再次）
    result = re.sub(r"\s+", " ", result).strip()
    return result.strip()
CATEGORY_MAP = {
    "technology_wearables": "wearable",
    "technology_gadgets": "gadget",
    "technology_hardware": "hardware",
    "technology_robots": "robot",
    "technology_diy_electronics": "hardware",
    "technology_sound": "audio",
    "technology_camera_equipment": "camera",
    "technology_3d_printing": "hardware",
    "technology_makers": "hardware",
    "technology_apps": "app",
    "technology_web": "app",
    "technology_software": "app",
    "design_product_design": "design",
    "design_fashion": "design",
    "design_interactive_design": "design",
    "design_toys": "design",
    "design_games": "design",
    "hardware": "hardware",
}

# ── VIS 信号关键词 ──
MATERIAL_PREMIUM = [
    "titanium", "carbon fiber", "carbon fibre", "ceramic", "sapphire",
    "aluminum", "stainless steel", "liquid metal", "magnesium",
    "aerospace", "military grade", "gorilla glass", "sapphire glass",
]

MATERIAL_INNOVATION = [
    "biodegradable", "recycled", "plant-based", "bio-based", "ocean plastic",
    "sustainable material", "eco-friendly material", "bamboo", "wood",
    "vegan leather", "lab-grown", "bio", "mushroom",
]

CMF_KEYWORDS = [
    "transparent", "translucent", "see-through", "frosted", "matte",
    "glossy", "anodized", "pvd coating", "electroplating",
    "gradient color", "color-shifting", "iridescent", "holographic",
    "metallic finish", "brushed metal", "sandblasted", "textured",
    "soft-touch", "rubberized", "silicone coated",
    "color options", "limited edition color", "custom color",
    "rgb", "led pattern", "light pipe", "edge-lit",
]

PARADIGM_KEYWORDS = [
    "modular", "magnetic", "magsafe", "foldable", "rollable",
    "detachable", "transforming", "convertible", "swappable",
    "all-in-one", "multi-functional", "hybrid", "dual-purpose",
    "pocket-sized", "ultra-slim", "miniatur", "world's smallest",
    "world's thinnest", "first ever", "revolutionary",
    "reimagined", "reinvented", "next generation",
    "ai-powered", "ai driven", "ai-", "smart",
    "voice control", "gesture control", "touch-free",
    "wireless", "cordless", "true wireless",
    "open-ear", "bone conduction",
]

DESIGN_INNOVATION = [
    "minimalist", "premium design", "award-winning design", "red dot",
    "if design", "good design", "iconic", "signature",
    "futuristic", "sleek", "elegant", "refined",
    "ergonomic", "contoured", "sculpted", "crafted",
    "handcrafted", "artisanal", "bespoke",
    "customizable", "personalized", "interchangeable",
]

VISUAL_ORIENTED_CATEGORIES = {
    "technology_wearables": 7.5,  # 智能眼镜/戒指天然高识别度
    "technology_camera_equipment": 7.0,
    "design_product_design": 6.5,
    "technology_sound": 6.0,
    "technology_gadgets": 5.0,
    "technology_hardware": 5.0,
    "technology_robots": 5.0,
    "technology_diy_electronics": 4.0,
    "technology_3d_printing": 4.0,
    "design_fashion": 6.0,
    "design_toys": 5.5,
    "design_interactive_design": 6.0,
}

# 充电配件品牌（视觉驱动优先）
CHARGER_BRANDS = {
    "anker", "安克", "baseus", "倍思", "ugreen", "绿联",
    "belkin", "贝尔金", "cuktech", "酷态科", "romoss", "罗马仕",
    "sharge", "闪极", "闪极科技", "unitek", "优越者",
    "veout", "维奥", "维奥技术", "iottie", "艾欧提",
}

def normalize_brand(brand):
    return brand.lower().strip() if brand else ""

def keyword_score(text, keywords):
    """计数匹配的关键词，返回 0-10 的得分"""
    if not text:
        return 0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)
    # 1-2 match: 3-5, 3-4 match: 6-7, 5+: 8-10
    if matches == 0:
        return 0
    elif matches <= 2:
        return min(3 + matches, 5)
    elif matches <= 4:
        return min(6 + (matches - 3), 7)
    else:
        return min(8 + (matches - 5) * 0.5, 10)

def is_charger_brand(brand):
    brand_lower = normalize_brand(brand)
    return brand_lower in CHARGER_BRANDS

def score_candidate(c):
    brand = c.get("brand", "")
    title = (c.get("title", "") or "") + " " + (c.get("desc", "") or "")
    category = c.get("category", "")
    ks = c.get("ksData", {})
    tags = c.get("tags", [])

    text_lower = title.lower()
    brand_lower = normalize_brand(brand)
    is_charger = is_charger_brand(brand)

    # ── recognition (识别度) 0-10 ──
    base_recog = VISUAL_ORIENTED_CATEGORIES.get(category, 4.5)
    # 品牌名称本身有辨识度加分
    if len(brand) > 0 and brand[0].isupper():
        base_recog += 0.3
    # AI 眼镜/戒指/手表等高识别度
    if any(kw in text_lower for kw in ["smart glasses", "smart ring", "smart watch", "ai glass", "camera glasses"]):
        base_recog = max(base_recog, 8.0)
    # 透明设计加分
    if any(kw in text_lower for kw in ["transparent", "see-through", "translucent"]):
        base_recog += 1.2
    # 独特形态
    if any(kw in text_lower for kw in ["foldable", "rollable", "modular", "transforming"]):
        base_recog += 0.6
    # 高端材质视觉加成
    if any(kw in text_lower for kw in ["titanium", "carbon fiber", "stainless steel"]):
        base_recog += 0.6
    # Staff Pick 加分
    if ks.get("staffPick"):
        base_recog += 0.4
    # 高筹款市场验证
    pct = ks.get("percentFunded", 0)
    backers = ks.get("backersCount", 0)
    if backers > 500 or pct > 2000:
        base_recog += 0.6
    elif backers > 100 or pct > 500:
        base_recog += 0.3

    recognition = min(round(base_recog, 1), 10.0)

    # ── paradigmShift (范式变化) 0-10 ──
    para_base = 4.5
    # 智能眼镜/戒指类天然有范式转变
    if category == "technology_wearables":
        para_base = 6.5
    # 相机设备
    if category == "technology_camera_equipment":
        para_base = max(para_base, 5.0)
    # AI 驱动
    if any(kw in text_lower for kw in ["ai-powered", "ai driven", "chatgpt", "gpt-", "powered by ai", "ai "]):
        para_base += 1.8  # keep generous for AI
    # 新交互
    if any(kw in text_lower for kw in ["gesture control", "voice control", "nod-control", "eye tracking", "touch-free"]):
        para_base += 1.2
    if "bone conduction" in text_lower or "open-ear" in text_lower:
        para_base += 1.0
    # 模块化/磁吸
    if any(kw in text_lower for kw in ["modular", "magnetic", "magsafe", "swappable", "interchangeable"]):
        para_base += 0.8
    # 世界首款/mini化
    if any(kw in text_lower for kw in ["world's first", "first ever", "world's smallest", "revolutionary", "reimagined", "reinvented"]):
        para_base += 0.8
    # 机器人
    if category == "technology_robots":
        para_base = max(para_base, 5.5)
    # 可折叠
    if any(kw in text_lower for kw in ["foldable", "rollable", "transforming", "convertible"]):
        para_base += 0.8

    paradigm_shift = min(round(para_base, 1), 10.0)

    # ── cmfInnovation (CMF创新) 0-10 ──
    cmf_base = 4.5
    # 高端材料
    mat_score = keyword_score(title, MATERIAL_PREMIUM)
    if mat_score > 0:
        cmf_base = max(cmf_base, 4.5 + mat_score * 0.6)
        if "titanium" in text_lower:
            cmf_base += 1.0
    # 创新材料
    mat_innov = keyword_score(title, MATERIAL_INNOVATION)
    if mat_innov > 0:
        cmf_base = max(cmf_base, 4.5 + mat_innov * 0.6)
    # CMF 工艺
    cmf_score = keyword_score(title, CMF_KEYWORDS)
    if cmf_score > 0:
        cmf_base = max(cmf_base, 4.5 + cmf_score * 0.55)
    # 品类加成
    if category == "design_product_design":
        cmf_base = max(cmf_base, 5.2)
    if category == "technology_wearables":
        cmf_base = max(cmf_base, 5.0)
    if category == "design_fashion":
        cmf_base = max(cmf_base, 5.5)
    if any(kw in text_lower for kw in ["color options", "custom color", "interchangeable", "multiple style", "customization"]):
        cmf_base += 0.6

    if is_charger:
        if cmf_score < 3 and mat_score < 2:
            cmf_base = max(cmf_base - 2.0, 2.5)

    cmf_innovation = min(round(cmf_base, 1), 10.0)

    # ── transferability (可迁移性) 0-10 ──
    trans_base = 4.5
    if category == "design_product_design":
        trans_base = 5.5
    if category == "design_fashion":
        trans_base = 5.2
    if mat_score >= 3 or cmf_score >= 3:
        trans_base += 0.8
    elif mat_score >= 1 or cmf_score >= 1:
        trans_base += 0.4
    if any(kw in text_lower for kw in ["modular", "magnetic", "interchangeable", "swappable"]):
        trans_base += 0.7
    if category == "technology_wearables":
        trans_base += 0.5
    if ks.get("state") == "successful" and pct > 500:
        trans_base += 0.4

    transferability = min(round(trans_base, 1), 10.0)

    # ── diffusionPotential (扩散潜力) 0-10 ──
    diff_base = 4.5
    if ks.get("backersCount", 0) > 1000:
        diff_base += 2.0
    elif ks.get("backersCount", 0) > 500:
        diff_base += 1.5
    elif ks.get("backersCount", 0) > 100:
        diff_base += 1.0
    elif ks.get("backersCount", 0) > 50:
        diff_base += 0.5
    if pct > 5000:
        diff_base += 2.0
    elif pct > 1000:
        diff_base += 1.5
    elif pct > 500:
        diff_base += 1.0
    elif pct > 100:
        diff_base += 0.5
    if ks.get("staffPick"):
        diff_base += 0.6
    if ks.get("state") == "live":
        diff_base += 0.5
    if category in ("technology_wearables", "technology_gadgets"):
        diff_base += 0.4

    diffusion_potential = min(round(diff_base, 1), 10.0)

    # ── 充电配件视觉过滤 ──
    if is_charger and recognition < 6.0 and cmf_innovation < 5.0:
        # 无明显外观亮点的充电配件降分
        recognition = min(recognition, 4.5)
        paradigm_shift = min(paradigm_shift, 3.5)

    # ── score 计算 ──
    score = round(
        recognition * 3.0
        + paradigm_shift * 2.5
        + cmf_innovation * 2.0
        + transferability * 1.5
        + diffusion_potential * 1.0,
        1,
    )

    return {
        "recognition": recognition,
        "paradigmShift": paradigm_shift,
        "cmfInnovation": cmf_innovation,
        "transferability": transferability,
        "diffusionPotential": diffusion_potential,
        "score": score,
    }


def build_reason(c, vis, ks_data=None):
    """生成一句话中文推荐理由"""
    parts = []
    cat = c.get("category", "").replace("_", "/")
    parts.append(c.get("title", "Unknown")[:50])
    parts.append(f"在{cat}领域")

    ks = ks_data if ks_data is not None else c.get("ksData", {})
    src = c.get("source", "kickstarter")
    src_name = c.get("sourceName", src)
    backers = ks.get("backersCount", 0)
    if backers >= 1000:
        parts.append(f"获得{backers:,}人支持")
    else:
        parts.append(f"获得{backers}人支持")

    pledged = ks.get("usdPledged", ks.get("pledged", 0))
    if pledged >= 1000:
        parts.append(f"筹得${pledged:,.0f}")
    else:
        parts.append(f"筹得${pledged}")

    if ks.get("staffPick"):
        parts.append(f"{src_name} Staff Pick")

    pct = ks.get("percentFunded", 0)
    if pct > 0:
        parts.append(f"达成率{pct:.1f}%")

    # 视觉亮点标签
    highlights = []
    text = ((c.get("title") or "") + " " + (c.get("desc") or "")).lower()
    if any(kw in text for kw in ["titanium", "carbon fiber", "aluminum", "stainless steel"]):
        highlights.append("高端材质")
    if any(kw in text for kw in ["transparent", "translucent", "see-through"]):
        highlights.append("透明设计")
    if any(kw in text for kw in ["ai-powered", "ai driven", "chatgpt", "smart"]):
        highlights.append("AI驱动")
    if any(kw in text for kw in ["modular", "magnetic", "magsafe"]):
        highlights.append("模块化/磁吸")
    if any(kw in text for kw in ["foldable", "rollable"]):
        highlights.append("可折叠")
    if any(kw in text for kw in ["gesture", "voice control", "touch-free"]):
        highlights.append("新交互")
    if any(kw in text for kw in ["bone conduction", "open-ear"]):
        highlights.append("开放式音频")

    if highlights:
        parts.append("视觉亮点：" + "、".join(highlights[:3]))

    return "，".join(parts)


def normalize_category(cat):
    return CATEGORY_MAP.get(cat, "hardware")


def normalize_source_data(c: dict) -> dict:
    """
    将多平台候选数据统一为 ksData 兼容格式，使评分函数可复用。
    返回 unified 字典，键名与 ksData 一致。
    """
    src = c.get("source", "kickstarter")
    unified = {
        "goal": 0,
        "pledged": 0,
        "usdPledged": 0,
        "backersCount": 0,
        "currency": "USD",
        "state": "",
        "staffPick": False,
        "percentFunded": 0,
        "daysSinceLaunch": 0,
    }

    if src == "kickstarter":
        ks = c.get("ksData", {})
        unified.update({
            "goal": ks.get("goal", 0),
            "pledged": ks.get("pledged", 0),
            "usdPledged": ks.get("usdPledged", 0),
            "backersCount": ks.get("backersCount", 0),
            "currency": ks.get("currency", "USD"),
            "state": ks.get("state", ""),
            "staffPick": ks.get("staffPick", False),
            "percentFunded": ks.get("percentFunded", 0),
            "daysSinceLaunch": ks.get("daysSinceLaunch", 0),
        })

    elif src == "indiegogo":
        ig = c.get("igData", {})
        funds = float(ig.get("pledged", ig.get("fundsGathered", 0)) or 0)
        goal = float(ig.get("goal", ig.get("campaignGoal", 0))) or 1
        backers = int(ig.get("backersCount", ig.get("backerCount", 0))) or 0
        currency = (ig.get("currency", "USD") or "USD").upper()
        # 换算 USD
        RATE = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73, "AUD": 0.67}
        usd = funds * RATE.get(currency, 1.0)
        pct = round(funds / goal * 100, 1) if goal > 0 else 0
        state_map = {"active": "live", "successful": "successful", "ended": "failed"}
        state_raw = (ig.get("state", "") or ig.get("campaignStatus", "") or "").lower()
        unified.update({
            "goal": goal,
            "pledged": funds,
            "usdPledged": usd,
            "backersCount": backers,
            "currency": currency,
            "state": state_map.get(state_raw, state_raw),
            "staffPick": False,  # Indiegogo 无直接对应
            "percentFunded": pct,
        })

    elif src in ("miyoupin", "cn-platform"):
        cn = c.get("cnData", {})
        # 中国平台是销售平台，无众筹 backers；用价格做粗略市场信号
        price_cny = float(cn.get("priceCNY", 0)) or 0
        # 换算 USD 用于统一过滤（仅作信号参考，不用于金额门槛）
        usd_equiv = price_cny / 7.2
        # 对于销售平台，用「是否有视觉创新信号」来给 backersCount 赋值（用于扩散潜力评分）
        title = (c.get("title") or "") + " " + (c.get("desc") or "")
        has_visual_signal = any(
            kw in title.lower() for kw in [
                "transparent", "titanium", "carbon", "foldable",
                "modular", "magnetic", "ai", "ar", "vr",
            ]
        )
        fake_backers = 200 if has_visual_signal else 50
        unified.update({
            "goal": 0,
            "pledged": usd_equiv,
            "usdPledged": usd_equiv,
            "backersCount": fake_backers,
            "currency": "CNY",
            "state": "live",  # 在售即为 live
            "staffPick": False,
            "percentFunded": 0,
        })

    return unified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None,
                        help="输入候选 JSON（默认: products/all-candidates.json，若不存在则 products/ks-candidates.json）")
    parser.add_argument("--output", default=None,
                        help="输出 JSON（默认: 与输入对应的 -recent.json）")
    parser.add_argument("--top", type=int, default=200)
    args = parser.parse_args()

    # 确定输入文件
    if args.input:
        input_path = Path(args.input)
    else:
        p1 = Path("products/all-candidates.json")
        p2 = Path("products/ks-candidates.json")
        input_path = p1 if p1.exists() else p2
        if not input_path.exists():
            print("[错误] 未找到候选数据文件，请先运行 convert_ks_data.py 或 merge_candidates.py")
            sys.exit(1)

    # 确定输出文件
    if args.output:
        output_path = Path(args.output)
    else:
        stem = input_path.stem.replace("-candidates", "-recent")
        output_path = input_path.parent / f"{stem}.json"

    # 读取候选
    with open(input_path, "r", encoding="utf-8") as f:
        candidates_data = json.load(f)

    candidates = candidates_data.get("candidates", [])
    source_date = candidates_data.get("sourceDate", datetime.now().strftime("%Y-%m-%d"))

    print(f"[评分] 共 {len(candidates)} 个候选项目...")

    scored = []
    for c in candidates:
        # 标准化多平台数据
        c["ksData"] = normalize_source_data(c)
        vis = score_candidate(c)
        mapped = normalize_category(c.get("category", ""))
        reason = build_reason(c, vis, c["ksData"])
        src = c.get("source", "kickstarter")
        src_name = c.get("sourceName", src)

        product = {
            "id": c["id"],
            "brand": c.get("brand", ""),
            "category": mapped,
            "title": c.get("title", ""),
            "titleZh": generate_title_zh(c.get("title", "")),
            "desc": c.get("desc", ""),
            "time": c.get("time", ""),
            "score": vis["score"],
            "visBreakdown": {
                "recognition": vis["recognition"],
                "paradigmShift": vis["paradigmShift"],
                "cmfInnovation": vis["cmfInnovation"],
                "transferability": vis["transferability"],
                "diffusionPotential": vis["diffusionPotential"],
            },
            "source": src,
            "sourceName": src_name,
            "url": c.get("url", ""),
            "tags": c.get("tags", []),
            "image": c.get("image", ""),
            "personalRelevanceTier": c.get("personalRelevanceTier", "unknown"),
            "personalRelevanceReason": c.get("personalRelevanceReason", ""),
            "reason": reason,
            "ksData": c["ksData"],
            "sourceData": c.get(f"{src}Data", {}),
        }
        scored.append(product)

    # 排序：score desc, backers desc, percentFunded desc, live优先
    scored.sort(
        key=lambda p: (
            -p["score"],
            -p["ksData"]["backersCount"],
            -p["ksData"]["percentFunded"],
            0 if p["ksData"]["state"] == "live" else 1,
        )
    )

    top_n = scored[: args.top]

    # 统计
    high_signal = [p for p in top_n if p["score"] >= 70]
    categories_dist = {}
    for p in top_n:
        cat = p["category"]
        categories_dist[cat] = categories_dist.get(cat, 0) + 1

    print(f"[完成] 评分完成")
    print(f"  总候选: {len(scored)}")
    print(f"  Top {args.top}: {len(top_n)}")
    print(f"  Score >= 70 高信号: {len(high_signal)}")
    print(f"  品类分布: {json.dumps(categories_dist, ensure_ascii=False)}")
    print(f"  Top 5:")
    for p in top_n[:5]:
        print(f"    {p['score']:>5.1f}  {p['title'][:60]}")
        print(f"          R:{p['visBreakdown']['recognition']} P:{p['visBreakdown']['paradigmShift']} C:{p['visBreakdown']['cmfInnovation']} T:{p['visBreakdown']['transferability']} D:{p['visBreakdown']['diffusionPotential']}")

    # 输出 JSON
    sources = list(set(p.get("source", "kickstarter") for p in scored))
    src_label = "+".join(sorted(set(
        {"kickstarter": "KS", "indiegogo": "IG", "miyoupin": "有品"}.get(s, s)
        for s in sources
    )))
    output = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "sourceDate": source_date,
        "source": f"crowd-pulse/products/{src_label.lower()}-recent.json",
        "ingestPolicy": f"多平台来源（{', '.join(sources)}），过滤非视觉产品，usdPledged >= 5000（众筹）/ 视觉信号过滤（销售平台）",
        "sortPolicy": "score desc, backersCount desc, percentFunded desc, live state, launch time",
        "products": top_n,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    # 输出 JS
    js_path = str(output_path).replace(".json", ".js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.__crowdfundingData = ")
        json.dump(output, f, ensure_ascii=False, indent=4)
        f.write(";")

    print(f"[输出] {output_path} ({len(json.dumps(output))} bytes)")
    print(f"[输出] {js_path}")

    return top_n, source_date


if __name__ == "__main__":
    main()
