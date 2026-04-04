from ultralytics import YOLO
import torch


def validate_model(model_path, yaml_path, imgsz=640, batch_size=4):
    # 加载训练好的模型
    model = YOLO(model_path)

    # 在验证集上进行验证
    metrics = model.val(data=yaml_path, imgsz=imgsz, batch=batch_size)

    # 输出评估结果
    print("\n==== Validation Metrics ====")
    print(metrics)  # 包含 mAP50, mAP50-95, precision, recall 等


if __name__ == "__main__":
    # 模型路径和yaml路径
    model_path = "runs_road_damage/yolov8_cbam_c2f_ris_32_high_ch_is224_without_augment/weights/best.pt"  # 你的训练模型路径
    yaml_path = "rd_yolo_dataset/data.yaml"  # 你的数据集 yaml 文件路径

    # 调用验证函数
    validate_model(model_path, yaml_path, imgsz=640, batch_size=4)  # 可以调整 imgsz 和 batch_size
