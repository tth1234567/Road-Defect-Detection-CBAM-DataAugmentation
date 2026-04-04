# -*- coding: utf-8 -*-
"""
YOLOv8 结构增强（不改输入/输出）：为所有 C2f 模块注入 CBAM 注意力
- 兼容原始 data.yaml、训练/推理 API，不改 Detect 头及输出格式
- 原 C2f 权重保留，新加 CBAM 参数参与训练
- 适用于 yolov8n/s/m/l/x 权重

运行示例：
python train_yolov8_cbam_wrap.py --data rd_yolo_dataset/data.yaml --weights yolov8n.pt --epochs 100 --imgsz 1280 --batch 4
"""
import argparse
import os
from typing import Tuple

import torch
#ultralytics.nn.modules中有CBAM模块，直接导入就行，什么C2F,Conv都在这里面
import torch.nn as nn

try:
    from ultralytics import YOLO
    from ultralytics.nn.modules import C2f  # 用于识别并替换
except Exception as e:
    raise RuntimeError(
        "未检测到 ultralytics，请先安装：\n  pip install -U ultralytics\n"
    ) from e


# -----------------------------
#   模块定义：CBAM 注意力
# -----------------------------

#SE模块
#通道注意力（SE）：决定“哪类特征更重要”（比如裂缝纹理 vs 背景纹理）。
'''
SE、CBAM都在别的论文中，这里是借鉴
SE/CBAM 属于“轻量级增强”：
增加的参数和计算量很小；
但能提升模型的判别力（尤其是小目标、复杂背景下）。
所以很多人会在 YOLOv8 的基础上加 SE/CBAM，作为改进尝试。
'''





'''
在 PyTorch 里，所有的网络模块（卷积层、全连接层、我们自己写的模块……）都必须继承 nn.Module，
这样 PyTorch 才能识别它，知道里面有哪些参数、怎么 forward。
'''
class SE(nn.Module):

    # 类的构造函数（就像 Java 的构造方法），当你 SE(通道数, r值) 时会被调用。
    # self：和 Java 里的 this 一样，代表“这个对象自己”。类里面的方法第一个参数永远是 self。
    # c: int：输入特征图的通道数，类型提示是 int。比如如果输入特征是 (batch, 64, H, W)，那么 c=64
    # r: int = 32：缩放比例 reduction ratio，默认 32。用来把通道数压缩成更小的中间维度。等号 = 32 表示有默认值，如果你不传，就用 32。
    def __init__(self, c: int, r: int = 32):

        #这是在调用父类（这里是 nn.Module）的构造函数。
        #PyTorch 里所有自定义模块都要继承 nn.Module，它内部有很多管理参数、保存子模块的机制。
        #所以你必须先把父类初始化一下，就像 Java 里 super() 一样。
        super().__init__()
        #// 是 Python 的整数除法
        #c // r 表示把输入通道数压缩 r 倍（例如 c=64，r=16 → 64//16=4）。
        #这个压缩是为了减少计算量，相当于一个“瓶颈层”。
        #max(1, c // r) 是为了避免结果为 0（比如 c 很小的时候），保证至少有 1 个通道。
        #结果：c_mid 就是中间层的通道数。
        c_mid = max(1, c // r)
        '''
        nn.AdaptiveAvgPool2d(1)
        作用：对输入的每个通道做全局平均池化。
        假设输入是 (batch, c, H, W)，输出就是 (batch, c, 1, 1)。
        也就是把每个通道压成一个数。
        '''
        self.pool = nn.AdaptiveAvgPool2d(1)
        '''
        nn.Sequential(...)
    这是 PyTorch 提供的“顺序容器”，里面放的模块会依次执行。
    它包含三层：
    nn.Conv2d(c, c_mid, 1)：1×1 卷积，把通道数从 c 压缩到 c_mid。
    nn.ReLU(inplace=True)：激活函数 ReLU。
    nn.Conv2d(c_mid, c, 1)：1×1 卷积，把通道数恢复到 c。
    nn.Sigmoid()：把输出压缩到 0~1，作为每个通道的权重。
        '''
        self.fc = nn.Sequential(
            ## 类似 Linear(c → c_mid)全连接层
            nn.Conv2d(c, c_mid, 1, bias=False),

            nn.ReLU(inplace=True),
            #类似 Linear(c_mid → c)
            nn.Conv2d(c_mid, c, 1, bias=False),
            nn.Sigmoid(),
        )

    #x是输入张量，是特征图，形状是 (batch, c, H, W)。
    '''
    self.fc(...)
这是一个“小型神经网络”，顺序执行：
1×1卷积（c → c_mid）：把通道数降维，减少参数。
ReLU：非线性激活。
1×1卷积（c_mid → c）：再升维回原通道数。
Sigmoid：把输出压缩到 0~1 之间。
结果：得到一个 (batch, c, 1, 1) 的张量。
    '''
    '''
    这就是每个通道的权重 w。
w[i] 大 ≈ 1 → 表示这个通道很重要，保留。
w[i] 小 ≈ 0 → 表示这个通道不重要，抑制。
    '''
    def forward(self, x):
        w = self.fc(self.pool(x))

        '''
        x * w
把原始特征 x 和权重 w 相乘。
因为 w 的形状是 (batch, c, 1, 1)，它会自动扩展（broadcasting）到 (batch, c, h, w)，所以每个通道整张图都会乘同一个权重。
这样就实现了通道加权：重要的通道“音量变大”，不重要的“音量变小”。
        '''
        return x * w



#空间注意力（CBAM 的第二步）：决定“图像上哪些位置更重要”。
#类比：合唱团指挥既能给“哪个声部”加音量（通道），也能指挥“哪一片区域的人”更响（空间）。
class CBAM(nn.Module):
    def __init__(self, c: int, r: int = 32, k: int = 7):
        super().__init__()
        '''
        self.channel：通道注意力模块，直接复用你上面定义的 SE。
功能回顾：先全局平均池化到 (B, C, 1, 1)，再用小 MLP 产生每个通道的权重 w ∈ [0,1]，最后 x * w 做通道重标定。
        '''
        self.channel = SE(c, r=r)
        '''
        self.spatial：空间注意力模块。输入是 2 个通道（稍后解释哪 2 个），输出是 1 个注意力通道。
nn.Conv2d(2, 1, k, padding=k // 2, bias=False)：
输入通道=2，输出通道=1，卷积核 k×k，padding=k//2 使输出空间尺寸与输入相同（“same”效果）。
bias=False 常见于后接 BN 或 Sigmoid 的场景，减少不必要参数；这里直接 Sigmoid 也问题不大。
nn.Sigmoid()：把卷积产出的特征压到 [0,1]，作为空间权重图。
        '''
        self.spatial = nn.Sequential(
            nn.Conv2d(2, 1, k, padding=k // 2, bias=False),
            nn.Sigmoid(),
        )




    '''
    self.channel 和 self.spatial 是 类实例（对象），不是函数。
    它们能像函数一样调用，是因为 nn.Module 内部实现了 __call__，会自动去执行它们的 forward。
    所以你写 x = self.channel(x) 其实就是 “调用 SE 的 forward，把输入 x 送进去”。
    '''


    def forward(self, x):
        '''
        第一步：通道注意力
先把输入 x（形状 (B, C, H, W)）送入 SE：
SE 会为每个通道学一个系数 w_c ∈ [0,1]，得到“加权后的特征”。
输出形状仍然是 (B, C, H, W)（只是在通道维度上做了缩放）。
        '''
        x = self.channel(x)
        '''
        x.mean(1, keepdim=True)：对通道取平均 → 得到形状 (B, 1, H, W) 的“平均响应图”。
x.max(1, keepdim=True)[0]：对通道取最大值 → 得到形状 (B, 1, H, W) 的“最强响应图”。
PyTorch 的 max 会返回 (values, indices)，所以这里要取 [0] 拿到值。
torch.cat([...], dim=1)：把这两张图在通道维拼在一起，形成 (B, 2, H, W)。
直觉：平均图看“整体趋势”，最大图看“最强信号”，两者互补。
        '''

        m = torch.cat(
            [x.mean(1, keepdim=True), x.max(1, keepdim=True)[0]],
            dim=1,
        )
        a = self.spatial(m)
        return x * a


# -----------------------------
#   包装器：C2f -> C2f + CBAM
#   不改变前后张量形状/接口
#把一个 C2f“包”成 C2f+CBAM（不改形状）
# -----------------------------
'''
c2f_mod: C2f
c2f_mod 是函数的 输入参数名字。
: C2f 是 类型注解，意思是：这个参数应该是 一个 C2f 模块（YOLOv8 里定义的网络层）。
👉 也就是说，这个函数接收的输入必须是一个 C2f 对象。

-> int
这是函数的 返回值类型注解。
int 表示：函数运行后，返回的结果应该是一个整数。
'''
def _get_c2f_out_channels(c2f_mod: C2f) -> int:
    """
    尝试从 Ultralytics 的 C2f 里解析最终输出通道数
    兼容常见实现：c2f.cv2.conv.out_channels
    """
    try:
        #C2f 模块（YOLOv8 backbone/neck 的核心堆叠模块之一）会把输入特征变换后，输出一个新的特征图。
        #我们需要知道这个输出特征图有多少个通道数（out_channels），因为 CBAM 的输入通道必须匹配它。
        return int(c2f_mod.cv2.conv.out_channels)
    except Exception:
        # 兜底：通过一次假前向推断通道（不建议，通常上面的方式足够）
        raise AttributeError("无法从 C2f 模块中解析 out_channels")


'''
这个类就是一个“外壳包装器”：
输入 → 原始 C2f 模块
输出 → 再过一层 CBAM 注意力
等于在 不改动输入输出形状 的前提下，增强了 C2f 的表达能力。
'''
class C2fWithCBAM(nn.Module):
    def __init__(self, c2f_mod: C2f, r: int = 32, k: int = 7):
        super().__init__()
        self.c2f = c2f_mod
        out_c = _get_c2f_out_channels(c2f_mod)
        self.cbam = CBAM(out_c, r=r, k=k)

    def forward(self, x):
        y = self.c2f(x)
        return self.cbam(y)


# -----------------------------
#   递归替换：把模型中的 C2f 换成 C2fWithCBAM
# -----------------------------
def replace_c2f_with_cbam(module: nn.Module,
                          only_high_channels: bool = False,
                          high_ch_threshold: int = 224) -> Tuple[int, int]:
    """
    递归地把 module 内所有 C2f 替换为 C2fWithCBAM。
    参数:
        only_high_channels: True 时只替换高通道的 C2f（加速）；False 全替换
        high_ch_threshold: 通道阈值（仅当 only_high_channels=True 时生效）
    返回:
        (replaced, total)  替换的数量 / C2f 总数
    """
    replaced = 0
    total = 0
    '''
    named_children() 是谁的函数？
    named_children() 是 nn.Module 自带的方法。
    它会遍历当前这个模块的直接子模块，返回 (name, child)：
    name：子模块在当前模块中的名字（字符串，比如 "0", "conv1", "c2f_3"）；
    child：子模块对象本身（一个 nn.Module，可能是 Conv、C2f 等）。
    注意：它只遍历 一层直系孩子，不会递归到孙子、重孙子层。
    '''

    for name, child in module.named_children():
        # 先处理孩子
        #递归的深度优先遍历
        r, t = replace_c2f_with_cbam(child, only_high_channels, high_ch_threshold)
        replaced += r
        total += t

        # 再看当前层

        #判断某个对象是不是某个类（或其子类）的实例。
        if isinstance(child, C2f):
            total += 1
            do_replace = True
            if only_high_channels:
                try:
                    out_c = _get_c2f_out_channels(child)
                    do_replace = out_c >= high_ch_threshold
                except Exception:
                    do_replace = True  # 若取不到就保守替换

            if do_replace:
                # C2fWithCBAM构造函数init里有传递参数，传个c2f类型的参数
                cbam_wrap = C2fWithCBAM(child)
                '''
                module._modules[name] = cbam_wrap
                PyTorch 里，nn.Module 把子模块存放在一个字典里，名字就是 key。
                比如：
                model._modules = {
                "0": Conv(...),
                "1": Conv(...),
                "2": C2f(...),   # 假设这是原来的
                "3": Detect(...)
                }
                现在我们想把 "2": C2f(...) 换成 "2": C2fWithCBAM(...)。
                所以这行代码就是 用新的模块替换掉旧的模块，但是保持名字不变：
                '''


                # 用 _modules 替换，保持层名不变
                module._modules[name] = cbam_wrap
                replaced += 1

    return replaced, total


# -----------------------------
#   训练/验证脚本
# -----------------------------
def main():
    parser = argparse.ArgumentParser("YOLOv8 with CBAM-wrapped C2f (no I/O change)")
    parser.add_argument("--data", type=str,
                        help="数据配置 data.yaml 路径（包含 train/val/test 与 names）",default=r"E:\paper\rd_yolo_dataset\data.yaml" )
    parser.add_argument("--weights", type=str, default="yolov8n.pt",
                        help="初始权重（yolov8n/s/m/l/x.pt 均可）")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--project", type=str, default="runs_road_damage")
    parser.add_argument("--name", type=str, default="yolov8_cbam_c2f_ris_32_high_ch_is224_new")
    parser.add_argument("--device", type=str, default="",
                        help="设备选择，如 '0'、'0,1' 或 'cpu'（留空则自动）")
    parser.add_argument("--only_high_channels", action="store_true",default=True,
                        help="仅对高通道 C2f 注入 CBAM（更快）")
    parser.add_argument("--high_ch_threshold", type=int, default=224,
                        help="高通道阈值（only_high_channels=True 时生效）")
    parser.add_argument("--val_split", type=str, default="test",
                        choices=["val", "test"], help="验证/测试使用的划分")
    args = parser.parse_args()

    # 1) 加载 YOLO 权重（保持 Detect 头与推理接口不变）
    model = YOLO(args.weights)

    # 2) 结构注入：把所有 C2f → C2f+CBAM（不改 I/O）


    #外层 YOLO 类：负责训练、推理、加载权重等“管理工作”

    #内层 .model：才是真正的 PyTorch 神经网络结构（包含 Conv、C2f、SPPF、Detect 等层）
    det_model = model.model  # ultralytics.nn.tasks.DetectionModel
    replaced, total = replace_c2f_with_cbam(
        det_model, only_high_channels=args.only_high_channels,
        high_ch_threshold=args.high_ch_threshold
    )
    print(f"[架构注入] 已替换 {replaced}/{total} 个 C2f 为 C2f+CBAM")

    # 3) 可选：打印参数量/结构摘要（便于对比）
    try:
        # 只有在用户愿意时再打印，防止日志过长
        params_m = sum(p.numel() for p in det_model.parameters()) / 1e6
        print(f"[模型规模] 参数量约：{params_m:.2f} M")
    except Exception:
        pass

    # 4) 训练（Ultralytics 会根据 data.yaml 的 nc 自动调整分类数）
    train_kwargs = dict(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        device=args.device if args.device else None,
        # 其他你可以按需追加：lr0、optimizer、cos_lr、patience、freeze 等
    )
    model.train(**train_kwargs)

    # 5) 评估（保持原输出/后处理不变）
    metrics = model.val(data=args.data, split=args.val_split, imgsz=args.imgsz, batch=args.batch)
    print("\n==== Metrics ====")
    print(metrics)


if __name__ == "__main__":
    # 为了可重复性，用户也可在此处设置随机种子
    # import random, numpy as np
    # torch.manual_seed(42); random.seed(42); np.random.seed(42)
    main()
