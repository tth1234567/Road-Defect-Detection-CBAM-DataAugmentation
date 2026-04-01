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

#找对应的txt文件和png
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

#数据集划分的目录
def build_yolo_dirs(out_root):
    out_root = Path(out_root)
    images = out_root / "images"
    labels = out_root / "labels"
    for split in ["train", "val", "test"]:
        safe_mkdir(images / split)
        safe_mkdir(labels / split)
    return images, labels

#复制到对应目录
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
            ok = False; break
    return ok
#传递了train列表和rd_yolo_dataset路径
def augment_and_save(pairs, save_dir):
    '''
    A.Compose 返回的是一个 可调用对象（类似函数），其类型为 albumentations.core.composition.Compose。
    当调用这个对象时（如 transform(image=img, bboxes=boxes)），它会：
    按顺序应用所有定义的数据增强操作。
    返回一个字典，包含增强后的数据（如图像、边界框等）
    transforms	List[augmentations]	数据增强操作的列表（如翻转、旋转等）。
    bbox_params	BboxParams	边界框的处理参数（格式、过滤条件等），非必需。
    '''
    transform = A.Compose([
    #HorizontalFlip：水平翻转图像（概率50 %）。
    # Rotate：随机旋转图像（限制在 ±10度内，概率50 %）。
    # RandomBrightnessContrast：随机调整亮度和对比度（亮度限制 ±0.2，对比度限制 ±0.2，概率50 %）。
    # RandomScale：随机缩放图像（缩放比例限制 ±10 %，概率50 %）。
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=10, p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
        A.RandomScale(scale_limit=0.1, p=0.5)
    ],
    #     format='yolo'：边界框使用YOLO格式（中心坐标和宽高，归一化到[0, 1]）。
    # label_fields = ['class_labels']：类别标签与边界框关联。
    # min_area和min_visibility设为0，表示不过滤小或部分可见的边界框
        bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_area=0.0, min_visibility=0.0)
    )

    aug_images_dir = Path(save_dir) / "images" / "train"
    aug_labels_dir = Path(save_dir) / "labels" / "train"
    safe_mkdir(aug_images_dir)
    safe_mkdir(aug_labels_dir)

    for img_path, txt_path in pairs:
        image = cv2.imread(str(img_path))
        labels = []
        class_labels = []
        # 读取标注文件（.txt文件），每行包含一个边界框的类别和坐标（YOLO格式）。
        # 将类别和边界框坐标分别存储到class_labels和labels列表中。
        for line in Path(txt_path).read_text().splitlines():
            parts = line.strip().split()
            if len(parts) == 5:
                cls, x, y, w, h = map(float, parts)
                labels.append([x, y, w, h])
                class_labels.append(int(cls))

        if labels:
            #transform 返回一个字典，包含增强后的图像、边界框和类别标签
            augmented = transform(image=image, bboxes=labels, class_labels=class_labels)
            aug_img, aug_bboxes, aug_cls = augmented['image'], augmented['bboxes'], augmented['class_labels']

            aug_img_name = f"aug_{img_path.stem}{img_path.suffix}"
            aug_img_path = aug_images_dir / aug_img_name
            cv2.imwrite(str(aug_img_path), aug_img)

            aug_txt_path = aug_labels_dir / f"aug_{txt_path.stem}.txt"
            with open(aug_txt_path, 'w') as f:
                for cls, (x, y, w, h) in zip(aug_cls, aug_bboxes):
                    f.write(f"{cls} {x} {y} {w} {h}\n")

            print(f"增强完成：{aug_img_path}")

def main():
    ap = argparse.ArgumentParser("Road Damage | YOLOv8 split + train + test")
    ap.add_argument("--src", default="data", help="原始文件所在目录（混放 .jpeg/.txt）")
    ap.add_argument("--dest", default="rd_yolo_dataset", help="输出数据集目录（含 images/labels/train|val|test）")
    ap.add_argument("--train_ratio", type=float, default=0.8)
    ap.add_argument("--val_ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--move", action="store_true", help="移动文件而不是复制（省空间）")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--model", type=str, default="yolov8n.pt", help="模型大小：可选 yolov8n.pt / yolov8s.pt / yolov8m.pt 等")
    ap.add_argument("--augment", action="store_true", help="是否进行数据增强",default=True)
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
        for p in bad[:5]: print(" -", p)
        print("请确认后再继续。")

    print(f"共发现 {len(pairs)} 对 (image, txt)。开始划分...")
    #三个列表，分别存储训练集、验证集和测试集的图片-标注对。
    train, val, test = split_dataset(pairs, args.train_ratio, args.val_ratio, args.seed)
    print(f"train: {len(train)} | val: {len(val)} | test: {len(test)}")

    out_root = Path(args.dest)
    images_dir, labels_dir = build_yolo_dirs(out_root)

    stage_copy(train, images_dir, labels_dir, "train", move=args.move)
    stage_copy(val, images_dir, labels_dir, "val", move=args.move)
    stage_copy(test, images_dir, labels_dir, "test", move=args.move)

    yaml_path = write_yaml(out_root, images_dir/"train", images_dir/"val", images_dir/"test", NAMES)
    print(f"已生成 data.yaml -> {yaml_path}")

    if args.augment:
        augment_and_save(train, args.dest)

    try:
        from ultralytics import YOLO
    except Exception as e:
        print("\n未检测到 ultralytics，先安装：")
        print("  pip install ultralytics\n")
        raise

    model = YOLO(args.model)

    model.train(
        #数据集配置YAML文件路径	"data.yaml"
        data=str(yaml_path),
        #训练总轮次（所有数据迭代次数）
        epochs=args.epochs,
        #输入图像的尺寸（像素）
        imgsz=args.imgsz,
       # 每批次的样本数（根据显存调整）
        batch=4,
        #实验结果的根目录名称
        project="runs_road_damage",
        #当前实验的子目录名称
        name="yolov8_data_aug_epochsis100",
        #是否允许覆盖同名实验目录
        exist_ok=False,

        device=0 if torch.cuda.is_available() else "cpu"
    )

    metrics = model.val(data=str(yaml_path), split="test", imgsz=args.imgsz, batch=4)
    print("\n==== Test Metrics ====")
    print(metrics)

if __name__ == "__main__":
    import torch
    main()