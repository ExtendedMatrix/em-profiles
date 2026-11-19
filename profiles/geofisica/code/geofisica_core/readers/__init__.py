# -*- coding: utf-8 -*-
"""The readers, one module per form of file — ``csv_grid``, ``image_stack``
(row G2), ``geotiff`` and ``ascii_matrix`` (row G3); XYZV and screenshot stacks
arrive in G4 — the scan of a stack folder, and :func:`read_slice`, which reads
any of them into a :class:`~geofisica_core.grid.SliceData`."""

from __future__ import annotations

import hashlib
import os
import re

from ..depth import depth_from_name, read_csv_header
from ..grid import SliceData, SliceSpec
from .ascii_matrix import ASCII_EXT, read_ascii_matrix, read_ascii_section
from .csv_grid import CSV_EXT, NODATA, RepairedReader, read_csv_slice, repair_chunk
from .geotiff import (GEOTIFF_EXT, SATURATION, geotiff_info, is_value_raster,
                      read_geotiff_slice)
from .image_stack import IMG_EXT, image_size

#: the kinds a folder can be read as; ``scan_stack(kind="auto")`` still only
#: chooses between the first two (as 3DSC's import_gpr.py expects until G6):
#: :func:`guess_kind` knows them all
KINDS = ("csv_grid", "image_stack", "geotiff", "ascii_matrix")

#: a vertical section named by its line: ``VERT-1-OK``, ``VERT3``, ``sez_2``,
#: ``profile 4`` → ``VERT1``, ``VERT3``, ``SEZ2``, ``PROFILE4``
_RE_LINE = re.compile(r"(?i)(?<![a-z])(vert|sez|sezione|sec|section|profile|profilo|line|linea)"
                      r"[\s_-]*(\d+)")


def line_from_name(name):
    """The line a vertical section runs along, from its file name, or ``None``."""
    m = _RE_LINE.search(os.path.splitext(os.path.basename(name))[0])
    return (m.group(1).upper() + str(int(m.group(2)))) if m else None


def guess_kind(folder):
    """The reader a folder asks for: ``csv_grid`` if it has CSVs, ``ascii_matrix``
    for ``.asc`` matrices, ``geotiff`` when its TIFFs are rasters of values
    (one band, float or 16 bits: UA Ilici), ``image_stack`` for pictures;
    ``None`` when nothing in it is read."""
    names = sorted(os.listdir(folder))
    low = [n.lower() for n in names]
    if any(n.endswith(CSV_EXT) for n in low):
        return "csv_grid"
    if any(n.endswith(ASCII_EXT) for n in low):
        return "ascii_matrix"
    tifs = [n for n, lo in zip(names, low) if lo.endswith(GEOTIFF_EXT)]
    if tifs and all(is_value_raster(os.path.join(folder, n)) for n in tifs):
        return "geotiff"
    if any(n.endswith(IMG_EXT) for n in low):
        return "image_stack"
    return None


def _scan_named(folder, kind):
    """A ``geotiff`` or ``ascii_matrix`` folder: the depth from the name, or a
    section (its line from the name), or a product (its name) — never the
    index in the listing, which would invent a depth."""
    ext = GEOTIFF_EXT if kind == "geotiff" else ASCII_EXT
    specs = []
    for n in sorted(os.listdir(folder)):
        if not n.lower().endswith(ext):
            continue
        p = os.path.join(folder, n)
        stem = os.path.splitext(n)[0]
        line = line_from_name(n) if kind == "ascii_matrix" else None
        rng = None if line else depth_from_name(n)
        if line:
            specs.append(SliceSpec(path=p, depth_top=None, depth_bottom=None, kind=kind,
                                   orientation="vertical", line=line))
        elif rng:
            specs.append(SliceSpec(path=p, depth_top=rng[0], depth_bottom=rng[1], kind=kind))
        else:
            specs.append(SliceSpec(path=p, depth_top=None, depth_bottom=None, kind=kind,
                                   product=stem))
    specs.sort(key=lambda s: (s.orientation == "vertical", not s.depth_known, s.depth_mid,
                              s.line or "", s.path))
    return kind, specs


def scan_stack(folder, kind="auto"):
    """Return ``(kind, [SliceSpec, ...])`` sorted by depth.

    Depth comes from the file name; for CSVs it falls back to the header's
    ``Depth`` field, and finally to the file's index in the sorted listing
    (thickness 0), so a badly named stack still imports in the right order.
    """
    if kind in ("geotiff", "ascii_matrix"):
        return _scan_named(folder, kind)
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


_HORIZONTAL = ("extent", "step", "nodata", "row0", "transpose")
_VERTICAL = ("length", "depth", "nodata", "along", "reverse", "surface")


def read_slice(spec, grid=None, **declared):
    """Read any slice into a :class:`SliceData`, by its ``kind``.

    ``declared`` — what the file does not say and the person declares at
    import: for a matrix ``extent``/``step``, ``nodata``, ``row0``,
    ``transpose``; for a section ``length``, ``depth``, ``along``,
    ``reverse``, ``surface``. ``grid`` — a CSV stack's grid (the fast path).
    """
    if spec.kind == "csv_grid":
        g, amp, mask, dt = read_csv_slice(spec.path, grid)
        return SliceData(spec=spec, grid=g, amp=amp, mask=mask, read_seconds=dt)
    if spec.kind == "geotiff":
        return read_geotiff_slice(spec.path, spec)
    if spec.kind == "ascii_matrix":
        if spec.orientation == "vertical":
            return read_ascii_section(spec.path, spec,
                                      **{k: v for k, v in declared.items() if k in _VERTICAL})
        return read_ascii_matrix(spec.path, spec,
                                 **{k: v for k, v in declared.items() if k in _HORIZONTAL})
    raise ValueError("no reader for slices of kind %r (%s)" % (spec.kind, spec.path))


def values_digest(data):
    """A digest of what a slice SAYS (grid shape, mask, valid values), not of its
    bytes: two files with the same values have the same digest whatever their
    names, headers or georeference."""
    import numpy as np
    h = hashlib.sha256()
    h.update(("%d,%d;" % (data.grid.ny, data.grid.nx)).encode("ascii"))
    h.update(np.packbits(data.mask).tobytes())
    h.update(np.ascontiguousarray(data.amp[data.mask], dtype=np.float32).tobytes())
    return h.hexdigest()


def same_values(slices):
    """Warn about slices that hold the same values as an earlier one.

    UA Ilici ships two such mistakes: ``Sector 5-2/mean_v2.tif`` is the
    sector's ``sqmean_v2``, ``Sector 9/sqmean_v2.tif`` is Sector 12's. The
    reader cannot know which file is wrong: it says which ones are the same,
    in both languages, and nobody corrects the data. Returns the warnings
    (``{code: "same_values", path, same_as, en, it}``)."""
    seen = {}
    out = []
    for d in slices:
        k = values_digest(d)
        if k in seen:
            first = seen[k]
            a = os.path.join(os.path.basename(os.path.dirname(first)), os.path.basename(first))
            b = os.path.join(os.path.basename(os.path.dirname(d.spec.path)),
                             os.path.basename(d.spec.path))
            out.append({"code": "same_values", "path": d.spec.path, "same_as": first,
                        "en": "%s holds the same values as %s: one of the two is probably the "
                              "wrong file." % (b, a),
                        "it": "%s contiene gli stessi valori di %s: probabilmente uno dei due è "
                              "il file sbagliato." % (b, a)})
        else:
            seen[k] = d.spec.path
    return out


__all__ = ["ASCII_EXT", "CSV_EXT", "GEOTIFF_EXT", "IMG_EXT", "KINDS", "NODATA", "RepairedReader",
           "SATURATION", "geotiff_info", "guess_kind", "image_size", "is_value_raster",
           "line_from_name", "read_ascii_matrix", "read_ascii_section", "read_csv_slice",
           "read_geotiff_slice", "read_slice", "repair_chunk", "same_values", "scan_stack",
           "values_digest"]
