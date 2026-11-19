# -*- coding: utf-8 -*-
"""Depth from a file name, and the header of a CSV slice."""

from __future__ import annotations

import os
import re

_RE_RANGE_M = re.compile(
    r"([-+]?\d+(?:[.,]\d+)?)\s*(?:-|to|_)\s*([-+]?\d+(?:[.,]\d+)?)\s*m", re.I)
_RE_SINGLE_MM = re.compile(r"([-+]?\d+(?:[.,]\d+)?)\s*mm", re.I)
_RE_SINGLE_M = re.compile(r"([-+]?\d+(?:[.,]\d+)?)\s*m\b", re.I)
_RE_HEADER_FIELD = re.compile(
    r"([A-Za-z]+)\s*(?:\xb1|±|\+/-|\+-)?\s*([-+]?\d+(?:\.\d+)?)\s*m?", re.I)


def depth_from_name(name):
    """Return ``(top, bottom)`` in metres, positive downwards, or ``None``.

    Handles ``slice_0.100 - 0.200m.CSV`` (a range) and ``Slice_-2889mm.jpg``
    (a single signed depth in millimetres, as UA Ilici writes them).
    """
    stem = os.path.splitext(os.path.basename(name))[0]
    m = _RE_RANGE_M.search(stem)
    if m:
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", "."))
        return (min(abs(a), abs(b)), max(abs(a), abs(b)))
    m = _RE_SINGLE_MM.search(stem)
    if m:
        d = abs(float(m.group(1).replace(",", "."))) / 1000.0
        return (d, d)
    m = _RE_SINGLE_M.search(stem)
    if m:
        d = abs(float(m.group(1).replace(",", ".")))
        return (d, d)
    return None


def parse_csv_header(line):
    """Parse ``X ± 0.0500m, Y ± 0.0500m, Z ± 1.9000m, Depth ± 1.9000m, Amplitude``.

    Returns a dict with whichever of ``x_step``, ``y_step``, ``z``, ``depth``
    could be read. The ``±`` is latin-1 (0xB1) in the CS07 sample, so the
    caller decodes with ``latin-1``.
    """
    out = {}
    for part in line.split(","):
        m = _RE_HEADER_FIELD.search(part.strip())
        if not m:
            continue
        key, val = m.group(1).lower(), float(m.group(2))
        if key == "x":
            out["x_step"] = val
        elif key == "y":
            out["y_step"] = val
        elif key == "z":
            out["z"] = val
        elif key == "depth":
            out["depth"] = val
    return out


def read_csv_header(path):
    with open(path, "rb") as fh:
        first = fh.readline()
    return parse_csv_header(first.decode("latin-1", "replace"))
