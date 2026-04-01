"""
CBAM 注意力模块定义
必须在加载 best.pt 之前 import 本文件，否则 torch.load 会因找不到类定义而报错。
这些类与训练时 experienments/ris32_chis224.py 中的定义完全一致。
"""
import torch
import torch.nn as nn


class SE(nn.Module):
    """通道注意力模块（Squeeze-and-Excitation）"""

    def __init__(self, c: int, r: int = 32):
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
        return x * self.fc(self.pool(x))


class CBAM(nn.Module):
    """CBAM = SE 通道注意力 + 空间注意力"""

    def __init__(self, c: int, r: int = 32, k: int = 7):
        super().__init__()
        self.channel = SE(c, r=r)
        self.spatial = nn.Sequential(
            nn.Conv2d(2, 1, k, padding=k // 2, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x = self.channel(x)
        m = torch.cat([x.mean(1, keepdim=True), x.max(1, keepdim=True)[0]], dim=1)
        return x * self.spatial(m)


class C2fWithCBAM(nn.Module):
    """将 C2f 模块包裹后加上 CBAM，形状不变"""

    def __init__(self, c2f_mod, r: int = 32, k: int = 7):
        super().__init__()
        self.c2f = c2f_mod
        try:
            out_c = int(c2f_mod.cv2.conv.out_channels)
        except Exception as e:
            raise AttributeError("无法从 C2f 模块解析 out_channels") from e
        self.cbam = CBAM(out_c, r=r, k=k)

    def forward(self, x):
        return self.cbam(self.c2f(x))
