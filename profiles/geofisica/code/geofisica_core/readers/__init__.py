# -*- coding: utf-8 -*-
"""The readers, one module per form of file (row G2: ``csv_grid``, ``image_stack``;
GeoTIFF, headerless ASCII matrices, XYZV and screenshot stacks arrive in G3–G4),
and the scan of a stack folder."""

from __future__ import annotations

import os

from ..depth import depth_from_name, read_csv_header
from ..grid import SliceSpec
from .csv_grid import CSV_EXT, NODATA, RepairedReader, read_csv_slice, repair_chunk
from .image_stack import IMG_EXT, image_size


def scan_stack(folder, kind="auto"):
    """Return ``(kind, [SliceSpec, ...])`` sorted by depth.

    Depth comes from the file name; for CSVs it falls back to the header's
    ``Depth`` field, and finally to the file's index in the sorted listing
    (thickness 0), so a badly named stack still imports in the right order.
    """
    names = sorted(os.listdir(folder))
    csvs = [n for n in names if n.lower().endswith(CSV_EXT)]
    imgs = [n for n in names if n.lower().endswith(IMG_EXT)]
    if kind == "auto":
        kind = "csv_grid" if len(csvs) >= len(imgs) and csvs else "image_stack"
    picked = csvs if kind == "csv_grid" else imgs
    if not picked:
        return kind, []

    specs = []
    for i, n in enumerate(picked):
        p = os.path.join(folder, n)
        rng = depth_from_name(n)
        if rng is None and kind == "csv_grid":
            hdr = read_csv_header(p)
            if "depth" in hdr:
                d = abs(hdr["depth"])
                rng = (d, d)
        if rng is None:
            rng = (float(i), float(i))
        specs.append(SliceSpec(path=p, depth_top=rng[0], depth_bottom=rng[1],
                               kind=kind))
    specs.sort(key=lambda s: (s.depth_mid, s.path))

    # single-depth stacks (Ilici style): derive thickness from the neighbour
    if len(specs) > 1 and all(s.thickness == 0 for s in specs):
        step = abs(specs[1].depth_mid - specs[0].depth_mid)
        for s in specs:
            mid = s.depth_mid           # read before mutating either bound
            s.depth_top = max(0.0, mid - step / 2.0)
            s.depth_bottom = mid + step / 2.0
    return kind, specs


__all__ = ["CSV_EXT", "IMG_EXT", "NODATA", "RepairedReader", "image_size", "read_csv_slice",
           "repair_chunk", "scan_stack"]
