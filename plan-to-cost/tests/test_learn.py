import numpy as np
import pytest
import torch

from plan2cost.learn import data, infer, train
from plan2cost.learn.model import UNet, n_params


def test_unet_shapes_and_size():
    m = UNet(base=8, depth=3)
    out = m(torch.zeros(2, 1, 64, 64))
    assert out.shape == (2, 2, 64, 64)  # two channels: walls, interior
    assert 50_000 < n_params(m) < 1_000_000
    assert n_params(UNet(base=16)) == pytest.approx(1.94e6, rel=0.01)


def test_letterbox_pads_top_left():
    canvas = data.letterbox(np.ones((2, 3), np.uint8), 5, 9)
    assert canvas.shape == (5, 5)
    assert canvas[:2, :3].sum() == 6 and canvas[4, 4] == 9


def test_augment_keeps_shapes_and_aligned_labels():
    rng = np.random.default_rng(0)
    x = np.arange(16, dtype=np.uint8).reshape(4, 4) * 10
    y = np.stack([x > 50, x > 100]).astype(np.uint8)
    for _ in range(20):
        xa, ya = data.augment(x, y, rng)
        assert xa.shape == (4, 4) and ya.shape == (2, 4, 4)
        # a mask built from the image brightness must stay consistent after the same transform,
        # up to the contrast change: the brightest pixel is still inside the second mask
        assert ya[1][np.unravel_index(np.argmax(xa), xa.shape)] == 1


def test_to_input_inverts_so_ink_is_high():
    t = train.to_input(np.array([[[0, 255]]], dtype=np.uint8))
    assert t.shape == (1, 1, 1, 2)
    assert t[0, 0, 0, 0] == 1.0 and t[0, 0, 0, 1] == 0.0


def test_iou_helper_and_loss():
    target = torch.zeros(1, 2, 4, 4)
    target[:, :, :2] = 1
    perfect = (target * 20) - 10  # confident logits
    assert train.iou_per_channel(perfect, target).tolist() == [1.0, 1.0]
    assert train.dice_bce(perfect, target) < 0.05
    assert train.dice_bce(-perfect, target) > 5


def _tiny_cache(tmp_path, n=6, size=32):
    rng = np.random.default_rng(0)
    for split in ("train", "val"):
        x = rng.integers(0, 255, (n, size, size), dtype=np.uint8)
        y = np.zeros((n, 2, size, size), np.uint8)
        y[:, 0, :, 8:12] = 1
        y[:, 1, 4:20, 4:20] = 1
        np.savez(tmp_path / f"{split}.npz", x=x, y=y)


def test_train_saves_a_loadable_checkpoint_and_predicts(tmp_path):
    _tiny_cache(tmp_path)
    out = tmp_path / "m.pt"
    log = train.train(tmp_path, out, epochs=2, batch=2, base=4, lr=1e-2, threads=2, seed=0)
    assert len(log) == 2 and out.exists()
    model = infer.load_model(out)
    gray = np.random.default_rng(1).integers(0, 255, (20, 30), dtype=np.uint8)
    wall, interior = infer.predict_masks(model, gray, size=32)
    assert wall.shape == gray.shape == interior.shape
    assert wall.dtype == bool and interior.dtype == bool


def test_training_reduces_loss_on_a_learnable_toy_problem(tmp_path):
    _tiny_cache(tmp_path, n=8)
    log = train.train(
        tmp_path, tmp_path / "m.pt", epochs=12, batch=4, base=4, lr=1e-2, threads=2, seed=0
    )
    assert log[-1]["loss"] < log[0]["loss"]
