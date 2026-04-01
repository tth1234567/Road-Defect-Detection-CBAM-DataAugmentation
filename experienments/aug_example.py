# -*- coding: utf-8 -*-
"""
- Read:  paper/aug_examples/A_3190.jpeg
- Write: paper/aug_examples/00~04 .jpg
- 旋转: ±10°
- 缩放: ±10%，保持缩放后的真实尺寸（不再恢复原分辨率）
- 不添加底部标题条
"""

from pathlib import Path
import random
import cv2
import numpy as np
import albumentations as A

def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def load_image(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {path}")
    return img

def save_image(path: Path, img):
    ok = cv2.imwrite(str(path), img)
    if not ok:
        raise IOError(f"保存失败: {path}")

def main():
    random.seed(42)
    np.random.seed(42)

    # 脚本在 paper/，图片在 paper/aug_examples/
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir / "aug_examples"
    safe_mkdir(base_dir)

    image_path = base_dir / "A_3190.jpeg"
    img = load_image(image_path)

    # 0) 原图
    save_image(base_dir / "00_original.jpg", img)

    # 1) 水平翻转
    flip_img = A.Compose([A.HorizontalFlip(p=1.0)])(image=img)["image"]
    save_image(base_dir / "01_flip.jpg", flip_img)

    # 2) 旋转（±10°）
    rot_img = A.Compose([
        A.Rotate(limit=10, p=1.0, border_mode=cv2.BORDER_REFLECT_101)
    ])(image=img)["image"]
    save_image(base_dir / "02_rotate.jpg", rot_img)

    # 3) 亮度/对比度（±0.2）
    bc_img = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=1.0)
    ])(image=img)["image"]
    save_image(base_dir / "03_brightness_contrast.jpg", bc_img)

    # 4) 随机缩放（±10%），保持缩放后的真实分辨率
    scale_img = A.Compose([
        A.Affine(scale=(0.9, 1.1), keep_size=False, p=1.0)
    ])(image=img)["image"]
    save_image(base_dir / "04_scale.jpg", scale_img)

    # 打印路径
    print("\n====== 路径总览 ======")
    print(f"原图: {image_path.resolve()}")
    print("生成图片:")
    print(f"  {(base_dir / '00_original.jpg').resolve()}")
    print(f"  {(base_dir / '01_flip.jpg').resolve()}")
    print(f"  {(base_dir / '02_rotate.jpg').resolve()}")
    print(f"  {(base_dir / '03_brightness_contrast.jpg').resolve()}")
    print(f"  {(base_dir / '04_scale.jpg').resolve()} (保持缩放后分辨率)")
    print("======================\n")

if __name__ == "__main__":
    main()
