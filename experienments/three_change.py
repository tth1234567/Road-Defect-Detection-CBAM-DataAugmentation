# -*- coding: utf-8 -*-
"""
YOLOv8：结构+损失综合改进（可直接运行）
- 结构：仅对“高通道”的 C2f 注入 CBAM（默认阈值 192，r=96，k=7），不改变输入/输出接口与 Detect 头
- 损失：将边界框损失替换为 SIoU（猴子补丁，顶层定义，可被 pickle）
- 数据：支持从原始图像+YOLO标签自动划分/写 data.yaml，可选 Albumentations 增强
- 训练：默认关闭训练绘图（省内存），Windows 建议 workers=2

示例：
python train_cbam_siou.py --src data --dest rd_yolo_dataset --epochs 100 --imgsz 1280 --batch 4 --model yolov8n.pt
"""

import os
import shutil
import random
import argparse
import sys
import re
import textwrap
from pathlib import Path
from typing import Tuple

import albumentations as A
import cv2

# =============== 你的类别名（按需改） ===============
NAMES = ["pothole", "lateral_crack", "longitudinal_crack", "alligator_crack"]


# ================== 通用工具函数 ==================
def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

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

def write_yaml(save_dir: Path, train_dir: Path, val_dir: Path, test_dir: Path, names):
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

def build_yolo_dirs(out_root):
    out_root = Path(out_root)
    images = out_root / "images"
    labels = out_root / "labels"
    for split in ["train", "val", "test"]:
        safe_mkdir(images / split)
        safe_mkdir(labels / split)
    return images, labels

def copy_pair(img, txt, img_dst, txt_dst, move=False):
    if move:
        shutil.move(str(img), str(img_dst))
        shutil.move(str(txt), str(txt_dst))
    else:
        shutil.copy2(str(img), str(img_dst))
        shutil.copy2(str(txt), str(txt_dst))

def stage_copy(split_pairs, images_dir: Path, labels_dir: Path, split: str, move=False):
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

def augment_and_save(pairs, save_dir):
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
        if image is None:
            continue
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


# ================== CBAM 模块与 C2f 包装 ==================
import torch
import torch.nn as nn

# 注意：C2f 类稍后从 ultralytics.nn.modules 导入（加载 YOLO 后）

class SE(nn.Module):
    def __init__(self, c: int, r: int = 16):
        super().__init__()
        c_mid = max(1, c // r)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(c, c_mid, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(c_mid, c, 1, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        w = self.fc(self.pool(x))
        return x * w

class CBAM(nn.Module):
    def __init__(self, c: int, r: int = 16, k: int = 7):
        super().__init__()
        self.channel = SE(c, r=r)
        self.spatial = nn.Sequential(
            nn.Conv2d(2, 1, k, padding=k // 2, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x = self.channel(x)
        m = torch.cat([x.mean(1, keepdim=True), x.max(1, keepdim=True)[0]], dim=1)
        a = self.spatial(m)
        return x * a

def _get_c2f_out_channels(c2f_mod) -> int:
    """从 Ultralytics 的 C2f 解析 out_channels"""
    try:
        return int(c2f_mod.cv2.conv.out_channels)
    except Exception:
        raise AttributeError("无法从 C2f 解析 out_channels")

class C2fWithCBAM(nn.Module):
    def __init__(self, c2f_mod, r: int = 16, k: int = 7):
        super().__init__()
        self.c2f = c2f_mod
        out_c = _get_c2f_out_channels(c2f_mod)
        self.cbam = CBAM(out_c, r=r, k=k)

    def forward(self, x):
        y = self.c2f(x)
        return self.cbam(y)

def replace_c2f_with_cbam(module: nn.Module,
                          only_high_channels: bool = True,
                          high_ch_threshold: int = 192,
                          r: int = 96,
                          k: int = 7) -> Tuple[int, int]:
    """
    递归替换：C2f -> C2fWithCBAM
    only_high_channels=True 时仅替换 out_channels >= high_ch_threshold 的 C2f
    """
    from ultralytics.nn.modules import C2f  # 运行时导入，确保已安装
    replaced = 0
    total = 0
    for name, child in module.named_children():
        rr, tt = replace_c2f_with_cbam(child, only_high_channels, high_ch_threshold, r, k)
        replaced += rr
        total += tt
        if isinstance(child, C2f):
            total += 1
            do_replace = True
            if only_high_channels:
                try:
                    out_c = _get_c2f_out_channels(child)
                    do_replace = out_c >= high_ch_threshold
                except Exception:
                    do_replace = True
            if do_replace:
                cbam_wrap = C2fWithCBAM(child, r=r, k=k)
                module._modules[name] = cbam_wrap
                replaced += 1
    return replaced, total


# ========== 顶层定义（可 pickle）：SIoU 边界框损失 ==========
try:
    from ultralytics.utils import loss as yloss
    _OriginalBboxLoss = yloss.BboxLoss
except Exception:
    yloss = None
    _OriginalBboxLoss = None

class BboxLossSIoU(_OriginalBboxLoss if _OriginalBboxLoss is not None else object):
    """继承官方 BboxLoss，把 iou_type 设为 'siou'"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iou_type = "siou"

def patch_yolov8_bbox_loss_to_siou():
    if yloss is None or _OriginalBboxLoss is None:
        raise RuntimeError("未检测到 ultralytics 或 utils.loss.BboxLoss，请先安装： pip install -U ultralytics")
    yloss.BboxLoss = BboxLossSIoU
    print("[Loss Patch] 已将 YOLOv8 的边界框损失切换为 SIoU。")


# ============================== Main ==============================
def main():
    ap = argparse.ArgumentParser("Road Damage | YOLOv8 + CBAM(高通道) + SIoU")
    # 数据相关
    ap.add_argument("--src", default="data", help="原始文件所在目录（混放 .jpg/.png/.txt）")
    ap.add_argument("--dest", default="rd_yolo_dataset", help="输出数据集目录（含 images/labels/train|val|test）")
    ap.add_argument("--train_ratio", type=float, default=0.8)
    ap.add_argument("--val_ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--move", action="store_true", help="移动文件而不是复制（省空间）")
    ap.add_argument("--augment", action="store_true", default=True, help="是否进行数据增强")
    # 训练相关
    ap.add_argument("--model", type=str, default="yolov8n.pt", help="可选 yolov8n/s/m/l/x.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--device", type=str, default="", help="设备：'0'、'0,1'、'cpu'（留空自动）")
    ap.add_argument("--plots", action="store_true", default=False, help="训练中是否绘图（默认关闭以省内存）")
    ap.add_argument("--workers", type=int, default=2, help="Windows 建议 0~2")
    # 结构注入参数（按你的要求的默认值）
    ap.add_argument("--only_high_channels", action="store_true", default=True, help="仅替换高通道 C2f（默认开启）")
    ap.add_argument("--high_ch_threshold", type=int, default=224, help="高通道阈值（默认 224）")
    ap.add_argument("--cbam_r", type=int, default=16, help="SE 的 reduction ratio r（默认 16）")
    ap.add_argument("--cbam_k", type=int, default=7, help="空间注意力卷积核（默认 7）")
    args = ap.parse_args()

    # 1) 收集与快速检查
    pairs = collect_pairs(args.src)
    if len(pairs) == 0:
        print("未发现图片-标注对，请检查目录！")
        sys.exit(1)

    bad = []
    for _, t in pairs[:100]:
        if not quick_check_label(t):
            bad.append(t)
    if bad:
        print("警告：检测到可能不符合 YOLO 行格式的标注（示例最多列 5 个）：")
        for p in bad[:5]:
            print(" -", p)
        print("请确认后再继续。\n")

    print(f"共发现 {len(pairs)} 对 (image, txt)。开始划分...")
    train, val, test = split_dataset(pairs, args.train_ratio, args.val_ratio, args.seed)
    print(f"train: {len(train)} | val: {len(val)} | test: {len(test)}")

    # 2) 目录搭建与拷贝
    out_root = Path(args.dest)
    images_dir, labels_dir = build_yolo_dirs(out_root)
    stage_copy(train, images_dir, labels_dir, "train", move=args.move)
    stage_copy(val, images_dir, labels_dir, "val", move=args.move)
    stage_copy(test, images_dir, labels_dir, "test", move=args.move)
    yaml_path = write_yaml(out_root, images_dir/"train", images_dir/"val", images_dir/"test", NAMES)
    print(f"已生成 data.yaml -> {yaml_path}")

    # 3) 可选增强（仅对 train）
    if args.augment:
        augment_and_save(train, args.dest)

    # 4) 先打补丁（SIoU），再导入 YOLO（关键顺序！）
    patch_yolov8_bbox_loss_to_siou()

    try:
        from ultralytics import YOLO
        import torch
    except Exception:
        print("\n未检测到 ultralytics 或 torch，请先安装：")
        print("  pip install -U ultralytics torch torchvision torchaudio\n")
        raise

    # 5) 加载模型、进行结构注入（仅高通道 C2f）
    model = YOLO(args.model)
    det_model = model.model  # ultralytics.nn.tasks.DetectionModel
    replaced, total = replace_c2f_with_cbam(
        det_model,
        only_high_channels=args.only_high_channels,
        high_ch_threshold=args.high_ch_threshold,
        r=args.cbam_r,
        k=args.cbam_k
    )
    print(f"[架构注入] 已将 {replaced}/{total} 个 C2f 替换为 C2f+CBAM（阈值={args.high_ch_threshold}, r={args.cbam_r}, k={args.cbam_k}）")

    # 6) 训练
    device_auto = (0 if (args.device == "" and torch.cuda.is_available()) else (args.device or "cpu"))
    train_kwargs = dict(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project="runs_road_damage",
        name=f"yolov8_cbam_r{args.cbam_r}_th{args.high_ch_threshold}_SIoU",
        exist_ok=False,
        device=device_auto,
        plots=args.plots,
        workers=args.workers,
    )
    print("\n========== Train Args ==========")
    for k, v in train_kwargs.items():
        print(f"{k}: {v}")
    print("================================\n")
    model.train(**train_kwargs)

    # 7) 测试（用 test split）
    metrics = model.val(data=str(yaml_path), split="test", imgsz=args.imgsz, batch=args.batch, workers=args.workers)
    print("\n==== Test Metrics ====")
    print(metrics)


if __name__ == "__main__":
    # 减少 CUDA 显存碎片（官方建议）
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    main()
