# -*- coding: utf-8 -*-
"""
在保持输入输出与训练 API 不变的前提下，把 YOLOv8 的边界框损失改为 SIoU。
做法：运行时“猴子补丁（monkey patch）” ultralytics 的 BboxLoss，让 iou_type='siou'。
你原有的数据收集/划分/写 data.yaml/增强/训练流程全部保留。

用法示例：
python train_with_siou.py --src data --dest rd_yolo_dataset --epochs 100 --imgsz 1280 --batch 4 --model yolov8n.pt
"""
import os
import shutil
import random
import argparse
import sys
import re
import textwrap
from pathlib import Path

import albumentations as A
import cv2

NAMES = ["pothole", "lateral_crack", "longitudinal_crack", "alligator_crack"]


def is_pair_ok(img, txt):
    return img.stem == txt.stem and txt.exists()


def safe_mkdir(p):
    p.mkdir(parents=True, exist_ok=True)


def copy_pair(img, txt, img_dst, txt_dst, move=False):
    if move:
        shutil.move(str(img), str(img_dst))
        shutil.move(str(txt), str(txt_dst))
    else:
        shutil.copy2(str(img), str(img_dst))
        shutil.copy2(str(txt), str(txt_dst))


# 找对应的txt文件和png
def collect_pairs(root, img_exts=(".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")):
    root = Path(root)
    files = list(root.glob("*"))
    if len(files) == 0 or any(p.is_dir() for p in files):
        files = list(root.rglob("*"))
    imgs = [p for p in files if p.suffix.lower() in img_exts]
    pairs = []
    for img in sorted(imgs):
        txt = img.with_suffix(".txt")
        if not txt.exists():
            alt = list(img.parent.glob(img.stem + ".txt"))
            if alt:
                txt = alt[0]
        if txt.exists():
            pairs.append((img, txt))
    return pairs


def write_yaml(save_dir, train_dir, val_dir, test_dir, names):
    yaml = textwrap.dedent(f"""
    path: {save_dir.absolute().as_posix()}
    train: {train_dir.absolute().as_posix()}
    val: {val_dir.absolute().as_posix()}
    test: {test_dir.absolute().as_posix()}
    names: {names}
    """).strip() + "\n"
    (save_dir / "data.yaml").write_text(yaml, encoding="utf-8")
    return save_dir / "data.yaml"


def split_dataset(pairs, train_ratio=0.8, val_ratio=0.1, seed=42):
    assert 0 < train_ratio < 1 and 0 < val_ratio < 1 and train_ratio + val_ratio < 1
    random.Random(seed).shuffle(pairs)
    n = len(pairs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train = pairs[:n_train]
    val = pairs[n_train:n_train + n_val]
    test = pairs[n_train + n_val:]
    return train, val, test


# 数据集划分的目录
def build_yolo_dirs(out_root):
    out_root = Path(out_root)
    images = out_root / "images"
    labels = out_root / "labels"
    for split in ["train", "val", "test"]:
        safe_mkdir(images / split)
        safe_mkdir(labels / split)
    return images, labels


# 复制到对应目录
def stage_copy(split_pairs, images_dir, labels_dir, split, move=False):
    for img, txt in split_pairs:
        dst_img = images_dir / split / f"{img.stem}{img.suffix.lower()}"
        dst_txt = labels_dir / split / f"{txt.stem}.txt"
        copy_pair(img, txt, dst_img, dst_txt, move=move)


def quick_check_label(txt_path):
    ok = True
    for line in Path(txt_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if not re.match(r"^\s*\d+\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s*$", line):
            ok = False
            break
    return ok


# 传递了train列表和rd_yolo_dataset路径
def augment_and_save(pairs, save_dir):
    """
    使用 Albumentations 做基本增强：翻转、旋转、亮度对比度、缩放。
    YOLO 格式框通过 bbox_params(format='yolo') 传入与回写。
    """
    transform = A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.Rotate(limit=10, p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.RandomScale(scale_limit=0.1, p=0.5),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"], min_area=0.0, min_visibility=0.0),
    )

    aug_images_dir = Path(save_dir) / "images" / "train"
    aug_labels_dir = Path(save_dir) / "labels" / "train"
    safe_mkdir(aug_images_dir)
    safe_mkdir(aug_labels_dir)

    for img_path, txt_path in pairs:
        image = cv2.imread(str(img_path))
        labels = []
        class_labels = []
        for line in Path(txt_path).read_text().splitlines():
            parts = line.strip().split()
            if len(parts) == 5:
                cls, x, y, w, h = map(float, parts)
                labels.append([x, y, w, h])
                class_labels.append(int(cls))

        if labels:
            augmented = transform(image=image, bboxes=labels, class_labels=class_labels)
            aug_img, aug_bboxes, aug_cls = augmented["image"], augmented["bboxes"], augmented["class_labels"]

            aug_img_name = f"aug_{img_path.stem}{img_path.suffix}"
            aug_img_path = aug_images_dir / aug_img_name
            cv2.imwrite(str(aug_img_path), aug_img)

            aug_txt_path = aug_labels_dir / f"aug_{txt_path.stem}.txt"
            with open(aug_txt_path, "w") as f:
                for cls, (x, y, w, h) in zip(aug_cls, aug_bboxes):
                    f.write(f"{cls} {x} {y} {w} {h}\n")

            print(f"增强完成：{aug_img_path}")


# ===========================
#   关键：把 BboxLoss 改为 SIoU
# ===========================
# 导入原始 BboxLoss
# 引入官方的损失模块：loss模块定义了里面定义了 YOLOv8 各种损失（边界框、分类、DFL）
from ultralytics.utils import loss as yloss
# 取出原来的边界框损失类
OriginalBboxLoss = yloss.BboxLoss

#继承一份
class BboxLossSIoU(OriginalBboxLoss):
    def __init__(self, *args, **kwargs):
        #保留原始初始化
        #仅把 IoU 类型改成 SIoU
        super().__init__(*args, **kwargs)
        # 强制改为 SIoU
        self.iou_type = "siou"
def patch_yolov8_bbox_loss_to_siou():
    """
    运行时替换 ultralytics 的 BboxLoss，让 iou_type='siou'。
    不改源码，不改 Detect 头/输出格式。
    """
    try:

        # 替换为我们自定义的版本+
        yloss.BboxLoss = BboxLossSIoU
        print("[Loss Patch] 已将 YOLOv8 的边界框损失切换为 SIoU。")
    except Exception as e:
        print("[Loss Patch] 失败：", e)
        print("请确认 ultralytics 版本 >= 8.x，并包含 utils.loss.BboxLoss。")
        raise


def main():
    ap = argparse.ArgumentParser("Road Damage | YOLOv8 split + train + test (SIoU box loss)")
    ap.add_argument("--src", default="data", help="原始文件所在目录（混放 .jpeg/.txt）")
    ap.add_argument("--dest", default="rd_yolo_dataset", help="输出数据集目录（含 images/labels/train|val|test）")
    ap.add_argument("--train_ratio", type=float, default=0.8)
    ap.add_argument("--val_ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--move", action="store_true", help="移动文件而不是复制（省空间）")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--model", type=str, default="yolov8n.pt", help="可选 yolov8n/s/m/l/x.pt")
    ap.add_argument("--augment", action="store_true", help="是否进行数据增强", default=True)
    args = ap.parse_args()

    pairs = collect_pairs(args.src)
    if len(pairs) == 0:
        print("未发现图片-标注对，请检查目录！")
        sys.exit(1)

    bad = []
    for _, t in pairs[:100]:
        if not quick_check_label(t):
            bad.append(t)
    if bad:
        print("警告：检测到可能不符合 YOLO 行格式的标注：")
        for p in bad[:5]:
            print(" -", p)
        print("请确认后再继续。")

    print(f"共发现 {len(pairs)} 对 (image, txt)。开始划分...")
    train, val, test = split_dataset(pairs, args.train_ratio, args.val_ratio, args.seed)
    print(f"train: {len(train)} | val: {len(val)} | test: {len(test)}")

    out_root = Path(args.dest)
    images_dir, labels_dir = build_yolo_dirs(out_root)

    stage_copy(train, images_dir, labels_dir, "train", move=args.move)
    stage_copy(val, images_dir, labels_dir, "val", move=args.move)
    stage_copy(test, images_dir, labels_dir, "test", move=args.move)

    yaml_path = write_yaml(out_root, images_dir / "train", images_dir / "val", images_dir / "test", NAMES)
    print(f"已生成 data.yaml -> {yaml_path}")

    if args.augment:
        augment_and_save(train, args.dest)

    # 先打补丁，再导入 YOLO（确保 Trainer 构建 Loss 时已是 SIoU）
    patch_yolov8_bbox_loss_to_siou()

    try:
        from ultralytics import YOLO
        import torch
    except Exception as e:
        print("\n未检测到 ultralytics，先安装：")
        print("  pip install -U ultralytics\n")
        raise

    model = YOLO(args.model)

    # 训练（此时内部 BboxLoss 已是 SIoU）
    model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project="runs_road_damage",
        name="yolov8_data_aug_SIoU",
        exist_ok=False,
        device=0 if torch.cuda.is_available() else "cpu",
    )

    # 测试（可选：用 test split）
    metrics = model.val(data=str(yaml_path), split="test", imgsz=args.imgsz, batch=args.batch)
    print("\n==== Test Metrics ====")
    print(metrics)


if __name__ == "__main__":
    main()
