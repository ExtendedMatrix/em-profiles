"""Synthetic geophysical stacks for the tests of ``geofisica_core`` (no real data).

``tivoli_like(folder)`` writes a stack in the form CS07 CSIC-Tivoli ships
(row G2 of the geophysics plan): one CSV per depth band, the header with the
cell size in latin-1 ``±``, CRLF lines, a complete regular grid in raster
order (Y slowest), the cells outside the surveyed polygon with an EMPTY
amplitude field. Deterministic: no random numbers, the same bytes every time.
"""
from __future__ import annotations

import math
import os

NX, NY, STEP = 37, 23, 0.05
BANDS = ((0.0, 0.1), (0.1, 0.2), (0.2, 0.3))


def _amp(i, j, k):
    """A smooth field with a 'wall' and a 'pit' that change with depth."""
    wall = 40.0 * math.exp(-((i - 12 - 3 * k) ** 2) / 8.0)
    pit = 25.0 * math.exp(-(((i - 26) ** 2) + ((j - 11) ** 2)) / (10.0 + 4 * k))
    return 10.0 + 3.0 * k + wall + pit + 2.0 * math.sin(0.7 * i) * math.cos(0.5 * j)


def _inside(i, j, nx, ny):
    """The survey footprint: an ellipse, so about a third of the grid is empty."""
    return ((i - nx / 2.0) / (nx / 2.0)) ** 2 + ((j - ny / 2.0) / (ny / 2.0)) ** 2 <= 1.0


def tivoli_like(folder, bands=BANDS, nx=NX, ny=NY, step=STEP):
    """Write the stack into ``folder``; return the paths, shallowest first."""
    os.makedirs(folder, exist_ok=True)
    paths = []
    for k, (top, bottom) in enumerate(bands):
        name = "slice_%.3f - %.3fm.CSV" % (top, bottom)
        depth = 0.5 * (top + bottom)
        lines = ["X \xb1 %.4fm, Y \xb1 %.4fm, Z \xb1 %.4fm, Depth \xb1 %.4fm, Amplitude"
                 % (step, step, -depth, depth)]
        for j in range(ny):
            for i in range(nx):
                head = "%.4f, %.4f, %.4f, %.4f," % (i * step, j * step, -depth, depth)
                lines.append(head + (" %.3f" % _amp(i, j, k) if _inside(i, j, nx, ny) else ""))
        path = os.path.join(folder, name)
        with open(path, "wb") as fh:
            fh.write(("\r\n".join(lines) + "\r\n").encode("latin-1"))
        paths.append(path)
    return paths


#: a .prj in the ESRI form, ETRS89 / UTM 30N (UA Ilici's CRS), trimmed to what is read
PRJ_25830 = ('PROJCS["ETRS_1989_UTM_Zone_30N",GEOGCS["GCS_ETRS_1989",DATUM["D_ETRS_1989",'
             'SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],'
             'UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
             'UNIT["Meter",1.0],AUTHORITY["EPSG","25830"]]')
ILICI_ORIGIN = (701806.741, 4234824.081)


def _png(path, w, h, level):
    """A grey PNG of ``w`` x ``h`` (stdlib only), its value ``level`` with a ramp."""
    import struct
    import zlib
    rows = b"".join(b"\x00" + bytes((level + i) % 256 for i in range(w)) for _ in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def ilici_like(folder, depths_mm=(0, 5, 10, 15), w=20, h=12, cell=0.1, origin=ILICI_ORIGIN):
    """An image stack the way UA Ilici names it (``Slice_-0005mm.png``), each
    image with its world file (``.pgw``: the centre of the top-left pixel) and
    a ``.prj`` beside the first. Returns the paths, shallowest first."""
    os.makedirs(folder, exist_ok=True)
    paths = []
    for k, d in enumerate(depths_mm):
        stem = os.path.join(folder, "Slice_%05dmm" % -d if d else "Slice_00000mm")
        _png(stem + ".png", w, h, 10 * k)
        with open(stem + ".pgw", "w") as fh:
            fh.write("%.6f\n0.0\n0.0\n%.6f\n%.6f\n%.6f\n"
                     % (cell, -cell, origin[0] + cell / 2.0, origin[1] + h * cell - cell / 2.0))
        if k == 0:
            with open(stem + ".prj", "w") as fh:
                fh.write(PRJ_25830)
        paths.append(stem + ".png")
    return paths
