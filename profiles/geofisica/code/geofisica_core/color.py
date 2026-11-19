# -*- coding: utf-8 -*-
"""Values to colours: robust ranges and the colour maps of the cache.

Row G2 carries the old maps unchanged (``GRAY``, ``GRAY_INV``, ``VIRIDIS``:
the PNGs are byte for byte the old core's); the package's ``.emc`` ramps and
the declared ``value_scale`` arrive with row G5.
"""

from __future__ import annotations

try:
    import numpy as np
except ImportError:  # pragma: no cover - Blender always ships numpy
    np = None


def _viridis_lut():
    """10 anchor colours of viridis, linearly interpolated to 256 entries."""
    anchors = [(68, 1, 84), (72, 40, 120), (62, 74, 137), (49, 104, 142),
               (38, 130, 142), (31, 158, 137), (53, 183, 121), (109, 205, 89),
               (180, 222, 44), (253, 231, 37)]
    lut = np.zeros((256, 3), dtype=np.uint8)
    n = len(anchors) - 1
    for i in range(256):
        t = i / 255.0 * n
        k = min(int(t), n - 1)
        f = t - k
        for c in range(3):
            lut[i, c] = int(round(anchors[k][c] * (1 - f) + anchors[k + 1][c] * f))
    return lut


COLORMAPS = ("GRAY", "GRAY_INV", "VIRIDIS")


def to_rgba8(amp, mask, vmin, vmax, colormap="GRAY"):
    """Map values to an ``(ny, nx, 4)`` uint8 RGBA array.

    No-data cells get alpha 0, so the irregular footprint of the survey comes
    out of the texture for free — which is the main reason a textured plane
    beats a point cloud or a voxel volume for this data.
    """
    span = float(vmax - vmin) or 1.0
    norm = np.clip((amp - vmin) / span, 0.0, 1.0)
    idx = (norm * 255.0).astype(np.uint8)
    rgba = np.zeros(amp.shape + (4,), dtype=np.uint8)
    if colormap == "VIRIDIS":
        rgba[..., :3] = _viridis_lut()[idx]
    elif colormap == "GRAY_INV":
        rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = 255 - idx
    else:
        rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = idx
    rgba[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    return rgba


def percentile_range(values, lo=2.0, hi=98.0):
    return (float(np.percentile(values, lo)), float(np.percentile(values, hi)))
