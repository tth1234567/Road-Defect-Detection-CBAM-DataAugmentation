"""
Pydantic 数据模型：定义后端返回给前端的 JSON 格式
Pydantic 会自动校验数据类型，防止返回格式错误
"""
from typing import List, Optional
from pydantic import BaseModel


class DetectionBox(BaseModel):
    """单个检测框的信息"""
    class_name: str          # 英文类别名，如 "pothole"
    class_cn: str            # 中文类别名，如 "坑洼"
    confidence: float        # 置信度，0~1
    bbox: List[float]        # 边界框坐标 [x1, y1, x2, y2]（像素值）
    danger_level: str        # 危险等级："高" / "中" / "低"
    estimated_cost: int      # 预估修补费用（元）


class ModelResult(BaseModel):
    """单个模型的推理结果"""
    has_defect: bool                      # 是否检出缺陷
    detections: List[DetectionBox]        # 所有检测框列表
    annotated_image_b64: str              # 画框后的图片（Base64 编码）


class DetectResponse(BaseModel):
    """POST /api/detect 的完整响应"""
    has_defect: bool
    model_name: str                       # 模型描述字符串
    inference_time_ms: int                # 推理耗时（毫秒）
    detections: List[DetectionBox]        # 改进模型的检测结果
    annotated_image_b64: str              # 改进模型画框图（Base64）
    baseline_result: Optional[ModelResult] = None  # 仅 ab_test=true 时有值


class DemoImageInfo(BaseModel):
    """Demo 图片信息"""
    filename: str
    image_b64: str                        # 图片原图的 Base64


class TaskRecord(BaseModel):
    """历史任务列表条目（不含 detections_json，减小响应体积）"""
    id: int
    created_at: str
    filename: str
    confidence: float
    ab_test: bool
    has_defect: bool
    defect_count: int
    high_danger_count: int
    total_cost: int
    inference_time_ms: int
    user_id: int
    task_type: str = "image"


class TaskDetail(TaskRecord):
    """历史任务详情（含 detections_json 字符串）"""
    detections_json: str


class DashboardStats(BaseModel):
    """GET /api/stats/dashboard 的响应：混合模式（沙盘基数 + 真实增量）"""
    distance_km: float      # 最终分析路段里程（含基数，单位 km）
    total_defects: int      # 最终累计发现缺陷（含基数）
    fixed_count: int        # 最终高危缺陷已处置（含基数）
    running_days: int       # 从 2025-09-01 到今天的天数


# ── 视频巡检相关模型 ──────────────────────────────────────

class VideoTaskStatus(BaseModel):
    """GET /api/video/progress/{task_id} 的响应"""
    task_id: str
    status: str       # pending / processing / done / error
    progress: int     # 0-100
    message: str      # 当前阶段说明


class VideoFrameResult(BaseModel):
    """单帧的推理结果"""
    frame_idx: int
    has_defect: bool
    defect_count: int
    detections: List[DetectionBox]


class VideoResult(BaseModel):
    """GET /api/video/result/{task_id} 的完整响应"""
    task_id: str
    total_frames_processed: int
    defect_frame_count: int
    total_defects: int
    frame_results: List[VideoFrameResult]
    download_url: str          # /api/video/download/{task_id}


class VideoDemoInfo(BaseModel):
    """Demo 视频文件信息"""
    filename: str
    size_mb: float


class UserPublic(BaseModel):
    """当前登录用户信息"""
    id: int
    username: str
    role: str


class DefectPieItem(BaseModel):
    name: str
    value: int


class DefectPieResponse(BaseModel):
    total_detections: int
    series: List[DefectPieItem]


class RegisterRequest(BaseModel):
    username: str
    password: str
    password_confirm: str
    role: str
    admin_code: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ── 训练曲线 / A/B 对比实验室 ─────────────────────────────

class TrainingCurvePoint(BaseModel):
    epoch: int
    mAP50: float


class TrainingCurveSeries(BaseModel):
    name: str
    data: List[TrainingCurvePoint]


class TrainingCurvesResponse(BaseModel):
    series: List[TrainingCurveSeries]


class ABImageInfo(BaseModel):
    filename: str
    image_b64: str


class ABDetectResponse(BaseModel):
    """A/B 单模型推理响应（无历史记录保存）"""
    model_label: str
    has_defect: bool
    defect_count: int
    inference_time_ms: int
    annotated_image_b64: str
    detections: List[DetectionBox]
