"""
全局配置：路径、类别名称、成本估算规则
修改模型路径或调整成本参数时只需改这一个文件
"""
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
WEIGHTS_DIR = BASE_DIR / "weights"

BEST_MODEL_PATH = WEIGHTS_DIR / "best.pt"
BASELINE_MODEL_PATH = WEIGHTS_DIR / "yolov8n.pt"
DEMO_IMAGES_DIR = BASE_DIR / "demo_images"

# ── 模型推理参数 ───────────────────────────────────────
DEFAULT_CONFIDENCE = 0.25
IMAGE_SIZE = 1280

# ── 类别映射（训练时的顺序） ───────────────────────────
CLASS_NAMES_EN = ["pothole", "lateral_crack", "longitudinal_crack", "alligator_crack"]
CLASS_NAMES_CN = {
    "pothole": "坑洼",
    "lateral_crack": "横向裂缝",
    "longitudinal_crack": "纵向裂缝",
    "alligator_crack": "网状裂缝",
}

# ── 危险等级 ───────────────────────────────────────────
DANGER_LEVEL = {
    "pothole": "高",
    "lateral_crack": "中",
    "longitudinal_crack": "中",
    "alligator_crack": "高",
}

# ── 维修成本参数 ───────────────────────────────────────
# 单价：元/平方米（基于真实道路养护工程参考值）
COST_PER_SQM = {
    "pothole": 800,
    "lateral_crack": 300,
    "longitudinal_crack": 300,
    "alligator_crack": 600,
}
# 假设每张图拍摄的参考路面面积（平方米）
REFERENCE_ROAD_AREA_SQM = 20.0
# 单次缺陷费用限制（避免极端值）
COST_CLAMP = {
    "pothole":           (500,  8000),
    "lateral_crack":     (200,  3000),
    "longitudinal_crack":(200,  3000),
    "alligator_crack":   (500, 10000),
}
