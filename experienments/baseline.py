# split_and_train_yolo.py
import os, shutil, random, argparse, sys, re, textwrap
from pathlib import Path

# ---------- 可按需修改 ----------
NAMES = ["pothole", "lateral_crack", "longitudinal_crack", "alligator_crack"]
# 说明：上面顺序对应 YOLO 标注里的类别 id (0..3)。若你发现类别对不上，
# 可换成 ["lateral_crack","longitudinal_crack","alligator_crack","pothole"] 等，再跑一遍即可。
# --------------------------------

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


#找所有的图片和对应的txt文件
#存在pairs列表里
def collect_pairs(root, img_exts=(".jpg",".jpeg",".png",".JPG",".JPEG",".PNG")):
    root = Path(root)
    files = list(root.glob("*"))
    # 若在子目录，也一并考虑
    if len(files)==0 or any(p.is_dir() for p in files):
        files = list(root.rglob("*"))

    imgs = [p for p in files if p.suffix.lower() in img_exts]
    pairs = []
    for img in sorted(imgs):
        txt = img.with_suffix(".txt")
        if not txt.exists():
            # 兼容大小写或其他目录（比如 labels 同级）
            alt = list(img.parent.glob(img.stem + ".txt"))
            if alt:
                txt = alt[0]
        if txt.exists():
            pairs.append((img, txt))
    return pairs

#创建yaml文件
def write_yaml(save_dir, train_dir, val_dir, test_dir, names):
    yaml = textwrap.dedent(f"""
    path: {save_dir.absolute().as_posix()}
    train: {train_dir.absolute().as_posix()}
    val: {val_dir.absolute().as_posix()}
    test: {test_dir.absolute().as_posix()}
    names: {names}
    """).strip()+"\n"
    (save_dir / "data.yaml").write_text(yaml, encoding="utf-8")
    return save_dir / "data.yaml"

#划分数据集
def split_dataset(pairs, train_ratio=0.8, val_ratio=0.1, seed=42):
    assert 0 < train_ratio < 1 and 0 < val_ratio < 1 and train_ratio + val_ratio < 1
    random.Random(seed).shuffle(pairs)
    n = len(pairs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train = pairs[:n_train]
    val = pairs[n_train:n_train+n_val]
    test = pairs[n_train+n_val:]
    return train, val, test

#创建目录结构
def build_yolo_dirs(out_root):
    out_root = Path(out_root)
    images = out_root / "images"
    labels = out_root / "labels"
    for split in ["train","val","test"]:
        safe_mkdir(images / split)
        safe_mkdir(labels / split)
    return images, labels

#复制文件到相应目录
def stage_copy(split_pairs, images_dir, labels_dir, split, move=False):
    for img, txt in split_pairs:
        dst_img = images_dir / split / f"{img.stem}{img.suffix.lower()}"
        dst_txt = labels_dir / split / f"{txt.stem}.txt"
        copy_pair(img, txt, dst_img, dst_txt, move=move)

#检查标签是否符合YOLO格式
def quick_check_label(txt_path):
    # 粗检：行结构是否符合 "cls xc yc w h"
    ok = True
    for line in Path(txt_path).read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line:
            continue
        if not re.match(r"^\s*\d+\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s*$", line):
            ok = False; break
    return ok

def main():
    #用argparse的函数来创建命令行参数解析器


    #初始化一个 ArgumentParser 对象，用于解析命令行参数。
    # add_argument()函数来添加命令行参数
    ap = argparse.ArgumentParser("Road Damage | YOLOv8 split + train + test")
    ap.add_argument("--src", default="data", help="原始文件所在目录（混放 .jpeg/.txt）")
    ap.add_argument("--dest", default="initial_class", help="输出数据集目录（含 images/labels/train|val|test）")
    ap.add_argument("--train_ratio", type=float, default=0.8)
    ap.add_argument("--val_ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--move", action="store_true", help="移动文件而不是复制（省空间）")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--model", type=str, default="yolov8n.pt", help="yolov8n.pt / yolov8s.pt / yolov8m.pt 等")
    #解析用户输入的命令行参数，并存储到 args 对象中。
    args = ap.parse_args()


    pairs = collect_pairs(args.src)
    if len(pairs) == 0:
        print("未发现图片-标注对，请检查目录！")
        sys.exit(1)

    # 粗检几份标注合法性
    bad = []
    for _, t in pairs[:100]:
        if not quick_check_label(t):
            bad.append(t)
    if bad:
        print("警告：检测到可能不符合 YOLO 行格式的标注：")
        for p in bad[:5]: print(" -", p)
        print("请确认后再继续。")

    print(f"共发现 {len(pairs)} 对 (image, txt)。开始划分...")
    train, val, test = split_dataset(pairs, args.train_ratio, args.val_ratio, args.seed)
    print(f"train: {len(train)} | val: {len(val)} | test: {len(test)}")

    #输出路径
    out_root = Path(args.dest)
    # 创建输出目录结构
    images_dir, labels_dir = build_yolo_dirs(out_root)
    # 复制文件到相应目录
    stage_copy(train, images_dir, labels_dir, "train", move=args.move)
    stage_copy(val,   images_dir, labels_dir, "val",   move=args.move)
    stage_copy(test,  images_dir, labels_dir, "test",  move=args.move)
    #创建yaml文件
    yaml_path = write_yaml(out_root, images_dir/"train", images_dir/"val", images_dir/"test", NAMES)
    print(f"已生成 data.yaml -> {yaml_path}")

    # ---------- 训练与测试（Ultralytics） ----------
    try:
        from ultralytics import YOLO
    except Exception as e:
        print("\n未检测到 ultralytics，先安装：")
        print("  pip install ultralytics\n")
        raise
    #加载模型
    model = YOLO(args.model)
    # 训练
    model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=4,
        #训练后输出的路径
        project="runs_road_damage",
        name="yolov8_baseline_batch_is4_epochis100",
        exist_ok=True,
        device=0 if torch.cuda.is_available() else "cpu"
    )


    # 在 test split 上评估
    #test的信息都在metrics中
    metrics = model.val(data=str(yaml_path), split="test", imgsz=args.imgsz, batch=4)
    print("\n==== Test Metrics ====")
    print(metrics)  # 包含 mAP50, mAP50-95, precision, recall 等

if __name__ == "__main__":
    # 延迟导入 torch 以便上面 device 检测
    import torch
    main()