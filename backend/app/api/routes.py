"""
FastAPI 路由定义
所有业务逻辑均委托给 services 层，本文件只做参数接收与异常映射
"""
import base64
import csv
import logging
import time
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import require_user
from app.core.config import DEMO_IMAGES_DIR
from app.schemas.responses import (
    ABDetectResponse,
    ABImageInfo,
    DashboardStats,
    DefectPieItem,
    DefectPieResponse,
    DemoImageInfo,
    DetectResponse,
    LoginRequest,
    RegisterRequest,
    TaskDetail,
    TaskRecord,
    TrainingCurvePoint,
    TrainingCurveSeries,
    TrainingCurvesResponse,
    UserPublic,
    VideoDemoInfo,
    VideoFrameResult,
    VideoResult,
    VideoTaskStatus,
)
from app.services import auth as auth_svc
from app.services import history as history_svc
from app.services import video_service as video_svc
from app.services.auth import SESSION_COOKIE_NAME, SESSION_DAYS
from app.services.inference import detect, model_manager, _bytes_to_bgr, _run_single, _bgr_to_base64

# ── 仪表盘统计基数（运营沙盘初始值） ─────────────────────
_BASE_DISTANCE = 1247
_BASE_DEFECTS = 3892
_BASE_FIXED = 672
_LAUNCH_DATE = date(2025, 9, 1)

# ── 训练曲线 CSV 路径配置 ───────────────────────────────
_RESULTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "results"
_CURVE_FILES = {
    "Baseline": _RESULTS_DIR / "yolov8_baseline_batch_is4_epochis100" / "yolov8_baseline_batch_is4_epochis100.csv",
    "+Aug": _RESULTS_DIR / "yolov8_data_aug_epochsis100" / "yolov8_data_aug_epochsis100.csv",
    "+CBAM": _RESULTS_DIR / "yolov8_cbam_c2f_ris_32_high_ch_is224_without_augment" / "results.csv",
    "+Aug+CBAM（论文最终）": _RESULTS_DIR / "yolov8_cbam_c2f_ris_32_high_ch_is224_new" / "yolov8_cbam_c2f_ris_32_high_ch_is224_new.csv",
}

# ── A/B 对比图片目录 ────────────────────────────────────
_AB_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "ab_compare_images"

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def _is_admin(user: dict) -> bool:
    return user.get("role") == auth_svc.ROLE_ADMIN


def _assert_task_owner_or_admin(row: dict, user: dict) -> None:
    if _is_admin(user):
        return
    uid = row.get("user_id")
    if uid is not None and uid != user["id"]:
        raise HTTPException(status_code=403, detail="无权访问该任务")


def _assert_video_task_access(task_id: str, user: dict) -> None:
    state = video_svc.get_task_status(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"未找到任务 {task_id}")
    if _is_admin(user):
        return
    if getattr(state, "user_id", 0) != user["id"]:
        raise HTTPException(status_code=403, detail="无权访问该视频任务")


def _cookie_kwargs() -> dict:
    return {
        "key": SESSION_COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "max_age": int(SESSION_DAYS * 86400),
        "path": "/",
    }


# ── 认证（无需登录）────────────────────────────────────────

@router.post("/auth/register", response_model=UserPublic)
async def auth_register(body: RegisterRequest, response: Response):
    if body.password != body.password_confirm:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    _, err = auth_svc.register_user(
        body.username,
        body.password,
        body.role,
        body.admin_code,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    token, err2, user = auth_svc.login_user(body.username, body.password)
    if err2 or not token or not user:
        raise HTTPException(status_code=500, detail=err2 or "注册成功但自动登录失败")
    response.set_cookie(value=token, **_cookie_kwargs())
    return UserPublic(id=user["id"], username=user["username"], role=user["role"])


@router.post("/auth/login", response_model=UserPublic)
async def auth_login(body: LoginRequest, response: Response):
    token, err, user = auth_svc.login_user(body.username, body.password)
    if err or not token or not user:
        raise HTTPException(status_code=400, detail=err or "登录失败")
    response.set_cookie(value=token, **_cookie_kwargs())
    return UserPublic(id=user["id"], username=user["username"], role=user["role"])


@router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    auth_svc.logout_user(token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/auth/me", response_model=UserPublic)
async def auth_me(user: dict = Depends(require_user)):
    return UserPublic(id=user["id"], username=user["username"], role=user["role"])


@router.get("/health")
async def health():
    return {"status": "ok", "message": "智巡后端服务运行正常"}


# ── 需登录的业务接口 ───────────────────────────────────────


@router.post("/detect", response_model=DetectResponse)
async def detect_endpoint(
    user: dict = Depends(require_user),
    file: UploadFile = File(...),
    confidence: float = Form(default=0.25),
    ab_test: bool = Form(default=False),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400, detail=f"不支持的图片格式：{file.content_type}"
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="图片超过 20 MB 限制")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片内容为空")

    confidence = max(0.05, min(0.95, confidence))

    try:
        result = detect(image_bytes, confidence=confidence, ab_test=ab_test)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("推理过程中出现未知错误")
        raise HTTPException(status_code=500, detail=f"模型推理失败：{exc}") from exc

    try:
        history_svc.save_task(
            user_id=user["id"],
            filename=file.filename or "unknown.jpg",
            confidence=confidence,
            ab_test=ab_test,
            has_defect=result.has_defect,
            detections=result.detections,
            inference_time_ms=result.inference_time_ms,
            task_type="image",
        )
    except Exception:
        logger.warning("历史记录保存失败（不影响检测结果）", exc_info=True)

    return result


@router.get("/demo-images")
async def get_demo_images(user: dict = Depends(require_user)):
    items = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        for img_path in sorted(DEMO_IMAGES_DIR.glob(ext)):
            raw = img_path.read_bytes()
            items.append(
                DemoImageInfo(
                    filename=img_path.name,
                    image_b64=base64.b64encode(raw).decode("utf-8"),
                )
            )
    if not items:
        raise HTTPException(status_code=404, detail="未找到任何 Demo 图片")
    return items


def _row_to_task_record(r: dict) -> TaskRecord:
    return TaskRecord(
        id=r["id"],
        created_at=r["created_at"],
        filename=r["filename"],
        confidence=r["confidence"],
        ab_test=bool(r["ab_test"]),
        has_defect=bool(r["has_defect"]),
        defect_count=r["defect_count"],
        high_danger_count=r["high_danger_count"],
        total_cost=r["total_cost"],
        inference_time_ms=r["inference_time_ms"],
        user_id=r.get("user_id") or 0,
        task_type=r.get("task_type") or "image",
    )


@router.get("/history", response_model=List[TaskRecord])
async def get_history(
    user: dict = Depends(require_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    is_admin = _is_admin(user)
    rows = history_svc.get_tasks(
        limit=limit, offset=offset, user_id=user["id"], is_admin=is_admin
    )
    return [_row_to_task_record(r) for r in rows]


# 必须先于 /history/{task_id} 注册，否则 "defect-pie" 会被当成 task_id 导致 422
@router.get("/history/defect-pie", response_model=DefectPieResponse)
async def history_defect_pie(
    user: dict = Depends(require_user),
    start_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
):
    is_admin = _is_admin(user)
    data = history_svc.get_defect_type_counts_for_pie(
        user_id=user["id"],
        is_admin=is_admin,
        start_date=start_date,
        end_date=end_date,
    )
    series = [DefectPieItem(**item) for item in data["series"]]
    return DefectPieResponse(
        total_detections=data["total_detections"],
        series=series,
    )


@router.get("/history/{task_id}", response_model=TaskDetail)
async def get_history_task(task_id: int, user: dict = Depends(require_user)):
    row = history_svc.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"未找到 id={task_id} 的任务记录")
    _assert_task_owner_or_admin(row, user)
    base = _row_to_task_record(row)
    return TaskDetail(
        **base.model_dump(),
        detections_json=row["detections_json"],
    )


@router.delete("/history/{task_id}")
async def delete_history_task(task_id: int, user: dict = Depends(require_user)):
    row = history_svc.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"未找到 id={task_id} 的任务记录")
    _assert_task_owner_or_admin(row, user)
    deleted = history_svc.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"未找到 id={task_id} 的任务记录")
    return {"status": "ok", "message": f"任务 {task_id} 已删除"}


@router.get("/history-count")
async def get_history_count(user: dict = Depends(require_user)):
    is_admin = _is_admin(user)
    return {
        "total": history_svc.get_total_count(
            user_id=user["id"], is_admin=is_admin
        )
    }


@router.get("/stats/dashboard", response_model=DashboardStats)
async def dashboard_stats(user: dict = Depends(require_user)):
    s = history_svc.get_summary_stats()
    task_count = s["task_count"]
    real_defects = s["total_defects"]
    running_days = (date.today() - _LAUNCH_DATE).days
    return DashboardStats(
        distance_km=round(_BASE_DISTANCE + task_count * 0.05, 1),
        total_defects=_BASE_DEFECTS + real_defects,
        fixed_count=_BASE_FIXED + int(real_defects * 0.15),
        running_days=running_days,
    )


_VIDEO_ALLOWED_TYPES = {
    "video/mp4",
    "video/mpeg",
    "video/quicktime",
    "video/x-msvideo",
}
_MAX_VIDEO_BYTES = 200 * 1024 * 1024


@router.post("/video/submit")
async def video_submit(
    user: dict = Depends(require_user),
    file: UploadFile = File(...),
    confidence: float = Form(default=0.25),
):
    video_bytes = await file.read()
    if len(video_bytes) == 0:
        raise HTTPException(status_code=400, detail="视频文件内容为空")
    if len(video_bytes) > _MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="视频超过 200 MB 限制")

    confidence = max(0.05, min(0.95, confidence))
    task_id = video_svc.submit_video(
        video_bytes=video_bytes,
        filename=file.filename or "upload.mp4",
        confidence=confidence,
        user_id=user["id"],
    )
    return {"task_id": task_id}


@router.post("/video/submit-demo")
async def video_submit_demo(
    user: dict = Depends(require_user),
    filename: str = Form(...),
    confidence: float = Form(default=0.25),
):
    demo_path = video_svc.get_demo_video_path(filename)
    if demo_path is None:
        raise HTTPException(status_code=404, detail=f"Demo 视频不存在：{filename}")

    confidence = max(0.05, min(0.95, confidence))
    video_bytes = demo_path.read_bytes()
    task_id = video_svc.submit_video(
        video_bytes=video_bytes,
        filename=filename,
        confidence=confidence,
        user_id=user["id"],
    )
    return {"task_id": task_id}


@router.get("/video/progress/{task_id}", response_model=VideoTaskStatus)
async def video_progress(task_id: str, user: dict = Depends(require_user)):
    _assert_video_task_access(task_id, user)
    state = video_svc.get_task_status(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"未找到任务 {task_id}")
    return VideoTaskStatus(
        task_id=task_id,
        status=state.status,
        progress=state.progress,
        message=state.message,
    )


@router.get("/video/result/{task_id}", response_model=VideoResult)
async def video_result(task_id: str, user: dict = Depends(require_user)):
    _assert_video_task_access(task_id, user)
    state = video_svc.get_task_status(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"未找到任务 {task_id}")
    if state.status != "done":
        raise HTTPException(
            status_code=400, detail=f"任务尚未完成，当前状态：{state.status}"
        )

    defect_frames = [f for f in state.frame_results if f.has_defect]
    total_defects = sum(f.defect_count for f in state.frame_results)

    from app.schemas.responses import DetectionBox

    frame_results_out = []
    for fr in state.frame_results:
        frame_results_out.append(
            VideoFrameResult(
                frame_idx=fr.frame_idx,
                has_defect=fr.has_defect,
                defect_count=fr.defect_count,
                detections=[DetectionBox(**d) for d in fr.detections],
            )
        )

    return VideoResult(
        task_id=task_id,
        total_frames_processed=state.processed_frames,
        defect_frame_count=len(defect_frames),
        total_defects=total_defects,
        frame_results=frame_results_out,
        download_url=f"/api/video/download/{task_id}",
    )


@router.get("/video/download/{task_id}")
async def video_download(task_id: str, user: dict = Depends(require_user)):
    _assert_video_task_access(task_id, user)
    state = video_svc.get_task_status(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"未找到任务 {task_id}")
    if state.status != "done" or state.output_path is None:
        raise HTTPException(status_code=400, detail="视频尚未处理完成")
    if not state.output_path.exists():
        raise HTTPException(status_code=404, detail="输出文件不存在，可能已被清理")
    return FileResponse(
        path=str(state.output_path),
        media_type="video/mp4",
        filename=f"smartinspect_{task_id}_annotated.mp4",
    )


@router.get("/video/demos", response_model=List[VideoDemoInfo])
async def video_demos(user: dict = Depends(require_user)):
    demos = video_svc.get_demo_videos()
    return [VideoDemoInfo(**d) for d in demos]


# ── 算法成果驾驶舱接口 ────────────────────────────────────

@router.get("/training-curves", response_model=TrainingCurvesResponse)
async def get_training_curves():
    """读取四组训练 CSV，返回 mAP@0.5 随 epoch 变化的曲线数据（无需登录）"""
    series_list: List[TrainingCurveSeries] = []
    for name, csv_path in _CURVE_FILES.items():
        points: List[TrainingCurvePoint] = []
        if csv_path.exists():
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # 去掉列名的首尾空格，以防 CSV 列名包含大量空白
                stripped_fieldnames = [k.strip() for k in (reader.fieldnames or [])]
                for row in reader:
                    stripped_row = {k.strip(): v.strip() for k, v in row.items() if k and v}
                    try:
                        epoch = int(float(stripped_row["epoch"]))
                        map50 = float(stripped_row["metrics/mAP50(B)"])
                        points.append(TrainingCurvePoint(epoch=epoch, mAP50=round(map50, 4)))
                    except (KeyError, ValueError):
                        continue
        series_list.append(TrainingCurveSeries(name=name, data=points))
    return TrainingCurvesResponse(series=series_list)


@router.get("/ab-images")
async def get_ab_images():
    """列出 ab_compare_images/ 目录中所有图片（无需登录）"""
    _AB_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        for p in sorted(_AB_IMAGES_DIR.glob(ext)):
            items.append({"filename": p.name})
    return {"images": items}


@router.post("/detect/baseline", response_model=ABDetectResponse)
async def detect_baseline(
    file: UploadFile = File(...),
    confidence: float = Form(default=0.25),
):
    """调用 yolov8n.pt（基线模型）对单张图片推理，不保存历史（A/B 实验室专用）"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式：{file.content_type}")
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="图片超过 20 MB 限制")
    confidence = max(0.05, min(0.95, confidence))
    try:
        img_bgr = _bytes_to_bgr(image_bytes)
        t0 = time.perf_counter()
        result = _run_single(model_manager.baseline, img_bgr, confidence)
        ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        logger.exception("基线模型推理失败")
        raise HTTPException(status_code=500, detail=f"推理失败：{exc}") from exc
    return ABDetectResponse(
        model_label="YOLOv8n Baseline",
        has_defect=result.has_defect,
        defect_count=len(result.detections),
        inference_time_ms=ms,
        annotated_image_b64=result.annotated_image_b64,
        detections=result.detections,
    )


@router.post("/detect/improved", response_model=ABDetectResponse)
async def detect_improved(
    file: UploadFile = File(...),
    confidence: float = Form(default=0.25),
):
    """调用 best.pt（改进模型）对单张图片推理，不保存历史（A/B 实验室专用）"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式：{file.content_type}")
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="图片超过 20 MB 限制")
    confidence = max(0.05, min(0.95, confidence))
    try:
        img_bgr = _bytes_to_bgr(image_bytes)
        t0 = time.perf_counter()
        result = _run_single(model_manager.best, img_bgr, confidence)
        ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        logger.exception("改进模型推理失败")
        raise HTTPException(status_code=500, detail=f"推理失败：{exc}") from exc
    return ABDetectResponse(
        model_label="YOLOv8n+Aug+CBAM（论文改进）",
        has_defect=result.has_defect,
        defect_count=len(result.detections),
        inference_time_ms=ms,
        annotated_image_b64=result.annotated_image_b64,
        detections=result.detections,
    )
