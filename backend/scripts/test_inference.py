"""
本地推理测试脚本（无需启动 Web 服务）
用途：验证 best.pt 和 yolov8n.pt 能否正常加载并完成推理

使用方法（在 backend/ 目录下运行）：
    python scripts/test_inference.py --image ../datasets/aug_examples/AB_1000.jpeg
    python scripts/test_inference.py --image demo_images/demo1.jpg --ab-test
"""
import argparse
import sys
import time
from pathlib import Path

# 将 backend/ 加入模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 必须先注册 CBAM 类，再加载模型
from app.models.cbam_modules import CBAM, SE, C2fWithCBAM  # noqa: F401
from ultralytics import YOLO

from app.core.config import BASELINE_MODEL_PATH, BEST_MODEL_PATH, DEFAULT_CONFIDENCE


def run_test(image_path: Path, confidence: float, ab_test: bool):
    print(f"\n{'='*55}")
    print(f"  智巡模型推理测试")
    print(f"{'='*55}")
    print(f"图片路径 : {image_path}")
    print(f"置信度   : {confidence}")
    print(f"A/B 测试 : {ab_test}\n")

    if not image_path.exists():
        print(f"[错误] 找不到图片：{image_path}")
        sys.exit(1)

    print("加载 best.pt …")
    t0 = time.perf_counter()
    best_model = YOLO(str(BEST_MODEL_PATH))
    print(f"  ✓ 加载完成（{(time.perf_counter()-t0)*1000:.0f} ms）")

    print("推理 best.pt …")
    t0 = time.perf_counter()
    results = best_model.predict(source=str(image_path), conf=confidence, verbose=False)
    elapsed = (time.perf_counter() - t0) * 1000
    r = results[0]
    print(f"  ✓ 推理完成（{elapsed:.0f} ms），检出 {len(r.boxes)} 个缺陷")
    for box in (r.boxes or []):
        cls = best_model.names[int(box.cls[0])]
        conf = float(box.conf[0])
        print(f"    - {cls:<25} conf={conf:.3f}  bbox={box.xyxy[0].tolist()}")

    out_path = image_path.parent / ("best_result_" + image_path.name)
    r.save(filename=str(out_path))
    print(f"  结果图片保存至：{out_path}")

    if ab_test:
        print("\n加载 yolov8n.pt（基线）…")
        t0 = time.perf_counter()
        base_model = YOLO(str(BASELINE_MODEL_PATH))
        print(f"  ✓ 加载完成（{(time.perf_counter()-t0)*1000:.0f} ms）")

        print("推理 yolov8n.pt …")
        t0 = time.perf_counter()
        base_results = base_model.predict(source=str(image_path), conf=confidence, verbose=False)
        elapsed = (time.perf_counter() - t0) * 1000
        br = base_results[0]
        print(f"  ✓ 推理完成（{elapsed:.0f} ms），检出 {len(br.boxes)} 个缺陷")
        out_base = image_path.parent / ("baseline_result_" + image_path.name)
        br.save(filename=str(out_base))
        print(f"  结果图片保存至：{out_base}")

    print(f"\n{'='*55}\n  测试通过 ✓\n{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智巡本地推理测试")
    parser.add_argument("--image", type=str, default="demo_images/demo1.jpg")
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--ab-test", action="store_true")
    args = parser.parse_args()

    run_test(
        image_path=Path(args.image),
        confidence=args.confidence,
        ab_test=args.ab_test,
    )
