"""
FastAPI 应用入口
- 使用 lifespan 在启动时加载模型，确保首个请求前模型已就绪
- CORS 允许前端开发服务器（localhost:5173）跨域访问
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.services.inference import model_manager
from app.services import history as history_svc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时加载模型，关闭时可添加清理逻辑"""
    logger.info("智巡后端启动中，正在预加载模型…")
    model_manager.load()
    history_svc.init_db()
    logger.info("模型预加载完成，历史数据库已就绪 ✓")
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="智巡 SmartInspect API",
    description="道路缺陷智能检测系统后端，基于 YOLOv8+CBAM 改进模型",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["detection"])

# ── 静态文件：aug_examples（增强图片，算法驾驶舱使用） ────
_AUG_EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "aug_examples"
_AUG_EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/aug_examples", StaticFiles(directory=str(_AUG_EXAMPLES_DIR)), name="aug_examples")

# ── 静态文件：ab_compare_images（A/B 实验室预置图） ────────
_AB_IMAGES_DIR = Path(__file__).resolve().parent.parent / "ab_compare_images"
_AB_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/ab_compare_static", StaticFiles(directory=str(_AB_IMAGES_DIR)), name="ab_compare_static")
