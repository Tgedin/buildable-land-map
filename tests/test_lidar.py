import numpy as np

from blm import lidar, synthetic
from blm.config import LidarConfig


def test_heights_match_ground_truth():
    parts = synthetic.make_parts(blocks=(2, 2))
    pc = synthetic.make_point_cloud(parts, density=2.0)
    out = lidar.building_heights(parts, pc, LidarConfig())

    expected = parts["floors_above"] * synthetic.FLOOR_H + 0.5
    err = (out["lidar_height_m"] - expected).abs()
    assert out["lidar_height_m"].notna().all()
    assert err.max() < 0.5, f"max error {err.max():.2f} m"


def test_low_point_density_is_flagged():
    parts = synthetic.make_parts(blocks=(1, 1))
    pc = synthetic.make_point_cloud(parts, density=0.05)
    out = lidar.building_heights(parts, pc, LidarConfig(min_roof_points=20))
    assert (out["lidar_confidence"] == "low").all()


def test_laz_roundtrip(tmp_path):
    parts = synthetic.make_parts(blocks=(1, 1))
    pc = synthetic.make_point_cloud(parts)
    path = tmp_path / "tile.laz"
    synthetic.write_laz(pc, path)

    read = lidar.read_laz([path], tuple(parts.total_bounds), keep={2, 6})
    inside = (
        (pc.x >= parts.total_bounds[0])
        & (pc.x <= parts.total_bounds[2])
        & (pc.y >= parts.total_bounds[1])
        & (pc.y <= parts.total_bounds[3])
    )
    assert len(read) == int(inside.sum())
    assert set(np.unique(read.cls)) <= {2, 6}


def test_grid_index_returns_superset():
    rng = np.random.default_rng(0)
    x, y = rng.uniform(0, 1000, 10_000), rng.uniform(0, 1000, 10_000)
    pc = lidar.PointCloud(x, y, np.zeros_like(x), np.full(len(x), 2, dtype=np.uint8))
    idx = lidar.GridIndex(pc, cell=25).query((100, 100, 160, 130))
    truth = np.flatnonzero((x >= 100) & (x <= 160) & (y >= 100) & (y <= 130))
    assert set(truth) <= set(idx)
