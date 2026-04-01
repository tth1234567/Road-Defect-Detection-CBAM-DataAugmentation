"""
视频巡检服务
- 接收视频字节流，在后台线程中逐帧推理（best.pt）
- CUDA 自适应：有 GPU 则用 CUDA，否则 CPU
- SKIP_FRAMES=2：每隔 1 帧取 1 帧，GPU 下速度极快
- 进度实时写入内存字典，前端通过轮询 /api/video/progress/{task_id} 获取
- 输出：标注后的 MP4（cv2.VideoWriter）+ 帧级缺陷 JSON
"""
import logging
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch

from app.services.inference import model_manager
from app.services.evaluator import evaluate_detection

logger = logging.getLogger(__name__)

# ── 配置常量 ─────────────────────────────────────────────
SKIP_FRAMES = 2            # 每隔 N-1 帧推理一次（N=2 即每隔 1 帧取 1 帧）
MAX_VIDEO_SIZE_MB = 200    # 上传上限（MB）
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "video_outputs"

# 设备自适应（启动时确定，避免每帧重复检测）
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("视频推理设备：%s", DEVICE)


# ── 任务状态数据类 ────────────────────────────────────────
@dataclass
class _FrameResult:
    frame_idx: int
    has_defect: bool
    defect_count: int
    detections: List[dict]  # 序列化后的 DetectionBox dict 列表


@dataclass
class _TaskState:
    status: str = "pending"    # pending / processing / done / error
    progress: int = 0          # 0-100
    message: str = "等待开始"
    frame_results: List[_FrameResult] = field(default_factory=list)
    output_path: Optional[Path] = None
    error_msg: str = ""
    total_frames: int = 0
    processed_frames: int = 0
    user_id: int = 0


# 全局任务状态字典（内存级，重启清空）
_TASKS: Dict[str, _TaskState] = {}
_TASKS_LOCK = threading.Lock()


# ── 公开 API ─────────────────────────────────────────────

def submit_video(
    video_bytes: bytes,
    filename: str,
    confidence: float = 0.25,
    user_id: int = 0,
) -> str:
    """
    提交视频处理任务，立即返回 task_id，后台线程异步处理。
    """
    task_id = uuid.uuid4().hex[:8]
    with _TASKS_LOCK:
        _TASKS[task_id] = _TaskState(
            status="pending",
            message="任务已提交，等待处理…",
            user_id=user_id,
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    t = threading.Thread(
        target=_process_video,
        args=(task_id, video_bytes, filename, confidence, user_id),
        daemon=True,
    )
    t.start()
    logger.info("视频任务已提交，task_id=%s，文件=%s", task_id, filename)
    return task_id


def get_task_status(task_id: str) -> Optional[_TaskState]:
    """返回任务状态，task_id 不存在时返回 None。"""
    return _TASKS.get(task_id)


def get_demo_videos() -> List[dict]:
    """返回 demo_videos 目录下所有 MP4 文件信息。"""
    demo_dir = Path(__file__).resolve().parent.parent.parent / "demo_videos"
    result = []
    if demo_dir.exists():
        for p in sorted(demo_dir.glob("*.mp4")):
            size_mb = round(p.stat().st_size / 1024 / 1024, 1)
            result.append({"filename": p.name, "size_mb": size_mb})
    return result


def get_demo_video_path(filename: str) -> Optional[Path]:
    """返回 Demo 视频的绝对路径，文件不存在时返回 None。"""
    demo_dir = Path(__file__).resolve().parent.parent.parent / "demo_videos"
    p = demo_dir / filename
    return p if p.exists() and p.suffix.lower() == ".mp4" else None


# ── 核心处理函数（后台线程执行）────────────────────────────

def _update(task_id: str, **kwargs):
    """线程安全地更新任务状态。"""
    with _TASKS_LOCK:
        state = _TASKS.get(task_id)
        if state:
            for k, v in kwargs.items():
                setattr(state, k, v)


def _process_video(
    task_id: str,
    video_bytes: bytes,
    filename: str,
    confidence: float,
    user_id: int,
):
    """在后台线程中执行视频逐帧推理，写出标注 MP4，记录帧结果。"""
    _update(task_id, status="processing", message="正在读取视频…", progress=1)
    t0 = time.monotonic()

    # 1. 将字节流写入临时文件（cv2.VideoCapture 只能读文件路径）
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            _update(task_id, status="error", message="无法解码视频文件，请检查格式",
                    error_msg="VideoCapture open failed")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        _update(task_id, total_frames=total_frames,
                message=f"共 {total_frames} 帧，开始推理（设备：{DEVICE}）…")

        # 2. 准备输出视频写入器
        out_path = OUTPUT_DIR / f"{task_id}_annotated.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # 输出帧率 = 原始 fps / SKIP_FRAMES（保持大致播放时长）
        out_fps = max(fps / SKIP_FRAMES, 1.0)
        writer = cv2.VideoWriter(str(out_path), fourcc, out_fps, (width, height))

        model = model_manager.best
        frame_idx = 0
        processed = 0
        frame_results: List[_FrameResult] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 跳帧逻辑
            if frame_idx % SKIP_FRAMES != 0:
                frame_idx += 1
                continue

            # 3. 推理
            results = model.predict(
                source=frame,
                conf=confidence,
                device=DEVICE,
                verbose=False,
            )
            res = results[0]
            annotated = res.plot()  # 画框后的 BGR 图像

            # 4. 解析检测框
            detections = []
            if res.boxes is not None and len(res.boxes) > 0:
                h, w = frame.shape[:2]
                for box in res.boxes:
                    cls_id = int(box.cls[0])
                    conf_val = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    det_box = evaluate_detection(
                        class_name=model.names[cls_id],
                        confidence=conf_val,
                        bbox=[x1, y1, x2, y2],
                        image_width=w,
                        image_height=h,
                    )
                    detections.append(det_box.dict())

            frame_results.append(_FrameResult(
                frame_idx=frame_idx,
                has_defect=len(detections) > 0,
                defect_count=len(detections),
                detections=detections,
            ))

            # 5. 写出标注帧
            writer.write(annotated)
            processed += 1

            # 6. 更新进度（1~95，留 5% 给收尾）
            if total_frames > 0:
                pct = max(1, min(95, int(processed / max(total_frames // SKIP_FRAMES, 1) * 95)))
            else:
                pct = 50
            _update(task_id,
                    processed_frames=processed,
                    progress=pct,
                    message=f"正在推理第 {frame_idx} 帧（{pct}%）…")

            frame_idx += 1

        cap.release()
        writer.release()

        _update(task_id,
                status="done",
                progress=100,
                message="处理完成",
                frame_results=frame_results,
                output_path=out_path,
                processed_frames=processed)
        logger.info("视频任务完成，task_id=%s，处理帧数=%d", task_id, processed)

        all_detections: List[dict] = []
        for fr in frame_results:
            all_detections.extend(fr.detections)
        elapsed_ms = max(0, int((time.monotonic() - t0) * 1000))
        try:
            from app.services import history as history_svc

            history_svc.save_task(
                user_id=user_id,
                filename=filename,
                confidence=confidence,
                ab_test=False,
                has_defect=len(all_detections) > 0,
                detections=all_detections,
                inference_time_ms=elapsed_ms,
                task_type="video",
            )
        except Exception:
            logger.warning("视频任务历史记录保存失败（不影响输出文件）", exc_info=True)

    except Exception as exc:
        logger.exception("视频处理失败，task_id=%s", task_id)
        _update(task_id, status="error", message=f"处理出错：{exc}", error_msg=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
