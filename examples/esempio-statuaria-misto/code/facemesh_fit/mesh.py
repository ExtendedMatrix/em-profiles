"""ESEMPIO (D-5) — reading a mesh, pure Python: binary glTF (.glb) and
Wavefront (.obj). Only positions and triangles; the node transforms of a glTF
are NOT applied (the model's frame is the file's), and that is said where the
proposals are written."""
from __future__ import annotations

import json
import struct
from typing import List, Tuple

V3 = Tuple[float, float, float]
Tri = Tuple[int, int, int]

_COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}


class MeshError(ValueError):
    """The file cannot be read as a mesh (the words say why)."""


def read_glb(path: str) -> Tuple[List[V3], List[Tri]]:
    with open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) < 20 or raw[:4] != b"glTF":
        raise MeshError(f"{path}: not a binary glTF (.glb)")
    off, js, binbuf = 12, None, b""
    while off + 8 <= len(raw):
        ln, kind = struct.unpack_from("<II", raw, off)
        chunk = raw[off + 8: off + 8 + ln]
        if kind == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif kind == 0x004E4942:
            binbuf = chunk
        off += 8 + ln
    if js is None:
        raise MeshError(f"{path}: no JSON chunk")

    def accessor(i: int) -> List[Tuple[float, ...]]:
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        fmt, size = _COMP[a["componentType"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        stride = bv.get("byteStride") or size * n
        base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return [struct.unpack_from("<" + fmt * n, binbuf, base + k * stride) for k in range(a["count"])]

    pos: List[V3] = []
    tris: List[Tri] = []
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            base = len(pos)
            pts = accessor(prim["attributes"]["POSITION"])
            pos.extend((float(p[0]), float(p[1]), float(p[2])) for p in pts)
            if "indices" in prim:
                idx = [int(v[0]) for v in accessor(prim["indices"])]
            else:
                idx = list(range(len(pts)))
            tris.extend((base + idx[k], base + idx[k + 1], base + idx[k + 2]) for k in range(0, len(idx) - 2, 3))
    if not tris:
        raise MeshError(f"{path}: no triangles")
    return pos, tris


def read_obj(path: str) -> Tuple[List[V3], List[Tri]]:
    pos: List[V3] = []
    tris: List[Tri] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                x, y, z = line.split()[1:4]
                pos.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                ids = []
                for tok in line.split()[1:]:
                    k = int(tok.split("/")[0])
                    ids.append(k - 1 if k > 0 else len(pos) + k)
                for k in range(1, len(ids) - 1):
                    tris.append((ids[0], ids[k], ids[k + 1]))
    if not tris:
        raise MeshError(f"{path}: no faces")
    return pos, tris


def read_mesh(path: str) -> Tuple[List[V3], List[Tri]]:
    low = path.lower()
    if low.endswith(".glb"):
        return read_glb(path)
    if low.endswith(".obj"):
        return read_obj(path)
    raise MeshError(f"{path}: only .glb and .obj are read by this example")
