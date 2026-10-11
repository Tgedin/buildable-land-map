"""A small U-Net: grayscale plan in, two logit maps out (walls, interior)."""

from __future__ import annotations

import torch
from torch import nn


def _block(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
    )


class UNet(nn.Module):
    def __init__(self, base: int = 16, depth: int = 4, in_ch: int = 1, out_ch: int = 2):
        super().__init__()
        widths = [base * 2**i for i in range(depth + 1)]
        self.down = nn.ModuleList(
            [_block(in_ch, widths[0])] + [_block(widths[i], widths[i + 1]) for i in range(depth)]
        )
        self.up = nn.ModuleList(
            [
                nn.ConvTranspose2d(widths[i + 1], widths[i], 2, stride=2)
                for i in reversed(range(depth))
            ]
        )
        self.merge = nn.ModuleList(
            [_block(2 * widths[i], widths[i]) for i in reversed(range(depth))]
        )
        self.head = nn.Conv2d(widths[0], out_ch, 1)
        self.pool = nn.MaxPool2d(2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for i, block in enumerate(self.down):
            x = block(x if i == 0 else self.pool(x))
            skips.append(x)
        x = skips.pop()
        for up, merge in zip(self.up, self.merge, strict=True):
            x = merge(torch.cat([up(x), skips.pop()], dim=1))
        return self.head(x)


def n_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
