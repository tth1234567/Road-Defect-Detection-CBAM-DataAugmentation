"""
业务评估逻辑：根据检测框计算危险等级和预估修补成本
与模型推理逻辑完全解耦，方便独立修改成本规则
"""
from typing import List

from app.core.config import (
    CLASS_NAMES_CN,
    COST_CLAMP,
    COST_PER_SQM,
    DANGER_LEVEL,
    REFERENCE_ROAD_AREA_SQM,
)
from app.schemas.responses import DetectionBox


def evaluate_detection(
    class_name: str,
    confidence: float,
    bbox: List[float],
    image_width: int,
    image_height: int,
) -> DetectionBox:
    """
    根据检测类别和边界框大小估算修补成本

    原理：
      1. 计算检测框占整张图片的比例
      2. 用该比例 × 参考路面面积（20 m²）得到缺陷实际面积
      3. 乘以单价，再做上下限截断
    """
    x1, y1, x2, y2 = bbox
    box_pixel_area = max(0.0, (x2 - x1) * (y2 - y1))
    total_pixel_area = max(1.0, float(image_width * image_height))

    area_ratio = box_pixel_area / total_pixel_area
    actual_area_sqm = area_ratio * REFERENCE_ROAD_AREA_SQM
    unit_price = COST_PER_SQM.get(class_name, 400)

    raw_cost = actual_area_sqm * unit_price
    lo, hi = COST_CLAMP.get(class_name, (100, 20000))
    cost = int(max(lo, min(hi, raw_cost)))

    return DetectionBox(
        class_name=class_name,
        class_cn=CLASS_NAMES_CN.get(class_name, class_name),
        confidence=round(float(confidence), 4),
        bbox=[round(v, 1) for v in bbox],
        danger_level=DANGER_LEVEL.get(class_name, "中"),
        estimated_cost=cost,
    )
