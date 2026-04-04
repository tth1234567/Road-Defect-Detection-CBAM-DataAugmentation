"""
模型推理服务
- ModelManager 采用单例模式，应用启动时只加载一次模型
- 必须先 import cbam_modules，再 import YOLO，否则 best.pt 反序列化会失败
"""
import base64
import functools as _functools
import logging
import time
from typing import Optional

import cv2
import numpy as np
import torch as _torch

# ── PyTorch 2.6 兼容补丁 ────────────────────────────────
# PyTorch 2.6 将 torch.load 的 weights_only 默认值改为 True，
# 导致含自定义类的 .pt 文件无法反序列化。此补丁在 Ultralytics
# 未传该参数时自动回退到 weights_only=False。
_original_torch_load = _torch.load

@_functools.wraps(_original_torch_load)
def _patched_torch_load(f, *args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_torch_load(f, *args, **kwargs)

_torch.load = _patched_torch_load
# ── 补丁结束 ─────────────────────────────────────────────

# ── 关键：先注册自定义类，再导入 YOLO ─────────────────
from app.models.cbam_modules import CBAM, SE, C2fWithCBAM  # noqa: F401
from ultralytics import YOLO

from app.core.config import (
    BASELINE_MODEL_PATH,
    BEST_MODEL_PATH,
    DEFAULT_CONFIDENCE,
    IMAGE_SIZE,
)
from app.schemas.responses import DetectResponse, ModelResult
from app.services.evaluator import evaluate_detection

logger = logging.getLogger(__name__)


class ModelManager:
    """负责模型生命周期管理（加载 / 持有引用）"""

    def __init__(self):
        self._best: Optional[YOLO] = None
        self._baseline: Optional[YOLO] = None

    def load(self):
        logger.info("正在加载改进模型 best.pt …")
        self._best = YOLO(str(BEST_MODEL_PATH))
        logger.info("正在加载基线模型 yolov8n.pt …")
        self._baseline = YOLO(str(BASELINE_MODEL_PATH))
        logger.info("模型加载完毕")

    @property
    def best(self) -> YOLO:
        if self._best is None:
            raise RuntimeError("best.pt 尚未加载，请先调用 model_manager.load()")
        return self._best

    @property
    def baseline(self) -> YOLO:
        if self._baseline is None:
            raise RuntimeError("yolov8n.pt 尚未加载，请先调用 model_manager.load()")
        return self._baseline


model_manager = ModelManager()


# ── 内部工具函数 ──────────────────────────────────────

def _bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解码图片，请确认文件格式正确")
    return img


def _bgr_to_base64(img_bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("图片编码失败")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _run_single(model: YOLO, img_bgr: np.ndarray, confidence: float) -> ModelResult:
    """对单张 BGR 图执行推理，返回结构化结果"""
    h, w = img_bgr.shape[:2]
    results = model.predict(
        source=img_bgr,
        conf=confidence,
        imgsz=IMAGE_SIZE,
        verbose=False,
    )
    result = results[0]

    detections = []
    if result.boxes is not None and len(result.boxes):
        for box in result.boxes:
            cls_idx = int(box.cls[0])
            cls_name = model.names[cls_idx]
            conf_val = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            det = evaluate_detection(cls_name, conf_val, [x1, y1, x2, y2], w, h)
            detections.append(det)

    annotated_bgr = result.plot()
    return ModelResult(
        has_defect=len(detections) > 0,
        detections=detections,
        annotated_image_b64=_bgr_to_base64(annotated_bgr),
    )


# ── 公开 API ──────────────────────────────────────────

def detect(image_bytes: bytes, confidence: float = DEFAULT_CONFIDENCE, ab_test: bool = False) -> DetectResponse:
    """
    主推理入口，由 routes.py 调用

    Parameters
    ----------
    image_bytes : 原始图片字节流
    confidence  : 置信度阈值
    ab_test     : 若为 True，同时运行基线模型并返回对比结果
    """
    img_bgr = _bytes_to_bgr(image_bytes)

    t0 = time.perf_counter()
    best_result = _run_single(model_manager.best, img_bgr, confidence)
    inference_ms = int((time.perf_counter() - t0) * 1000)

    baseline_result: Optional[ModelResult] = None
    if ab_test:
        baseline_result = _run_single(model_manager.baseline, img_bgr, confidence)

    return DetectResponse(
        has_defect=best_result.has_defect,
        model_name="YOLOv8n-CBAM (best.pt)",
        inference_time_ms=inference_ms,
        detections=best_result.detections,
        annotated_image_b64=best_result.annotated_image_b64,
        baseline_result=baseline_result,
    )
