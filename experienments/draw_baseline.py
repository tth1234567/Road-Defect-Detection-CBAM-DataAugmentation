import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
file_path = "data_aug_epoches_is100.csv"
df = pd.read_csv(file_path)

# 去掉列名空格
df.columns = df.columns.str.strip()

# 按 epoch 分组取均值
df_grouped = df.groupby("epoch").mean().reset_index()

# 图1：精度类指标 (0-1)
metrics_acc = [
    "metrics/precision(B)", "metrics/recall(B)",
    "metrics/mAP50(B)", "metrics/mAP50-95(B)"
]
metrics_acc = [m for m in metrics_acc if m in df_grouped.columns]

plt.figure(figsize=(10, 6))
for metric in metrics_acc:
    plt.plot(df_grouped["epoch"], df_grouped[metric], label=metric)
plt.xlabel("Epoch")
plt.ylabel("Value (0-1)")
plt.title("Accuracy Metrics vs Epoch")
plt.ylim(0, 1)   # 限制在0-1区间
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# 图2：loss类指标 (1-5)
metrics_loss = [
    "train/box_loss", "train/cls_loss", "train/dfl_loss",
    "val/box_loss", "val/cls_loss", "val/dfl_loss"
]
metrics_loss = [m for m in metrics_loss if m in df_grouped.columns]

plt.figure(figsize=(10, 6))
for metric in metrics_loss:
    plt.plot(df_grouped["epoch"], df_grouped[metric], label=metric)
plt.xlabel("Epoch")
plt.ylabel("Loss Value (1-5)")
plt.title("Loss Metrics vs Epoch")
plt.ylim(1, 5)   # 限制在1-5区间
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()