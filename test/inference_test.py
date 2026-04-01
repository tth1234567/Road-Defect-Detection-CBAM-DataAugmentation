import cv2
import os
from ultralytics import YOLO


def detect_road_defect(image_path, model_path):
    """
    调用 YOLO 模型进行道路缺陷检测
    """
    print(f"正在加载模型: {model_path} ...")
    # 1. 加载你训练好的最优模型权重
    model = YOLO(model_path)

    print(f"正在分析图片: {image_path} ...")
    # 2. 对本地图片进行推理 (conf=0.25 是置信度阈值，可根据实际情况微调)
    results = model(image_path, conf=0.25)

    # 3. 解析结果
    has_defect = False
    defect_details = []

    # results 通常是一个列表，因为这里只传了一张图，所以取第一个结果
    for result in results:
        boxes = result.boxes
        if len(boxes) > 0:
            has_defect = True
            # 获取每个检测框的详细信息
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = model.names[cls_id]
                defect_details.append(f"{class_name} (置信度: {conf:.2f})")

        # 4. 自动在图片上画好框，并返回 numpy 图像矩阵
        annotated_frame = result.plot()

    return has_defect, defect_details, annotated_frame


if __name__ == "__main__":
    # ================= 配置路径 =================
    # 使用 r 前缀防止 Windows 路径中的 \t 被转义
    BASE_DIR = r"E:\paper_for_competition\test"

    # 你的测试图片文件名 (请确保该图片在 test 文件夹下)
    IMAGE_NAME = "test_image.jpg"

    IMAGE_PATH = os.path.join(BASE_DIR, IMAGE_NAME)
    MODEL_WEIGHTS = os.path.join(BASE_DIR, "best.pt")
    # ============================================

    # 检查文件是否存在，防止低级报错
    if not os.path.exists(MODEL_WEIGHTS):
        print(f"❌ 找不到模型文件，请检查路径: {MODEL_WEIGHTS}")
        exit()
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ 找不到测试图片，请检查路径: {IMAGE_PATH}")
        exit()

    # 执行检测
    defect_found, details, output_img = detect_road_defect(IMAGE_PATH, MODEL_WEIGHTS)

    # 打印检测结果
    print("\n" + "=" * 30)
    if defect_found:
        print(f"⚠️ 警告: 发现道路缺陷!")
        print(f"🔎 详情: {', '.join(details)}")
    else:
        print("✅ 道路状况良好，未检测到缺陷。")
    print("=" * 30 + "\n")

    # 显示画好框的图片
    # 注意：在某些环境下 cv2.imshow 可能会卡住，弹出的窗口按任意键即可关闭
    cv2.imshow("Road Defect Detection Result", output_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 将画好框的图片保存到当前文件夹
    save_path = os.path.join(BASE_DIR, "result_output.jpg")
    cv2.imwrite(save_path, output_img)
    print(f"💾 处理后的图片已保存至: {save_path}")