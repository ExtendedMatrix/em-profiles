"""MICRO-PL20 · the synthetic head of the statuary pilot (D-5).

ESEMPIO SINTETICO — non è una statua, non citare. / SYNTHETIC EXAMPLE — not a
statue, not to be cited.

A head generated here, from nothing but this file: an ellipsoid with a brow
ridge, a nasion, a nose, two eye sockets, a mouth and a chin, a little
asymmetry, and a fine seeded roughness. Since we built it, we know where its
canonical points are — the **truth by construction** the pilot measures the
proposals and the combiners against (``*.truth.json``).

The truth follows operational definitions, written once here and nowhere
else (the plugin finds the points by its own means, from the mesh only):

* ``pronasale`` — the most anterior point of the midline profile;
* ``nasion`` — the deepest point of the midline profile between the brow and
  the nose;
* ``glabella`` — the most anterior point of the midline profile above the
  nasion (the brow ridge);
* ``gnathion`` — the most anterior-inferior point of the chin on the midline
  (the maximum of the 45° direction forward and down);
* ``exocanthion_r`` / ``_l`` — the lateral corner of each eye socket (its
  ellipse's lateral end), right = −x, left = +x (the head's own sides).

Model frame: metres, y up, the face looking at +z. ``--yaw`` turns the head
about y and ``--shift`` moves it, so the same face can be read in another
pose (the truth is turned with it).

Pure Python, no numpy. Writes ``<name>.glb``, ``<name>.truth.json`` and
``<name>.em.json`` (one unit, one 3D model document with its representation
model, the package declared).

    python make_head.py OUT_DIR [--name testa-sintetica] [--yaw 0] [--shift 0,0,0]
                                [--variant canonica|fuori-misura]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import struct
from typing import Dict, List, Sequence, Tuple

V3 = Tuple[float, float, float]

#: the ellipsoid of the skull, metres
C: V3 = (0.0, 0.30, 0.0)
RX, RY, RZ = 0.072, 0.112, 0.092
#: tessellation (columns around, rows top → bottom)
NU, NV = 160, 120
SEED = 2026
ROUGHNESS = 0.00015          # σ of the seeded roughness along the normal, m

# the features, relative to C (x right of the viewer = the head's left)
Y_NASION = 0.010
Y_BROW = 0.024
Y_TIP = -0.035
Y_EYE = 0.0035
X_EYE = 0.031
EYE_RX, EYE_RY = 0.019, 0.0085
Y_MOUTH = -0.070
Y_CHIN = -0.094
#: asymmetry: the head's left socket (+x) sits 1.2 mm higher, 0.8 mm wider
LEFT_DY, LEFT_DX = 0.0012, 0.0008


def _g(t: float) -> float:
    return math.exp(-t * t)


def displacement(x: float, y: float, z: float) -> float:
    """Outward displacement (m) of the base ellipsoid point (x, y, z) relative to C."""
    front = max(0.0, z / RZ)
    if front <= 0.0:
        return 0.0
    d = 0.0
    # brow ridge, strongest on the midline, fading sideways
    d += 0.0055 * _g((y - Y_BROW) / 0.0075) * _g(x / 0.034) * front
    # the nasion: a saddle between brow and nose
    d -= 0.0035 * _g((y - Y_NASION) / 0.0055) * _g(x / 0.010) * front
    # the nose: a ridge growing from the nasion to the tip, then falling fast
    if y <= Y_NASION:
        t = (Y_NASION - y) / (Y_NASION - Y_TIP)
        amp = 0.024 * min(1.0, max(0.0, t)) ** 1.4 if t <= 1.0 else 0.024 * _g((y - Y_TIP) / 0.0065)
        width = 0.006 + 0.007 * min(1.0, max(0.0, t))
        d += amp * _g(x / width) * front
    # the eye sockets (the head's right at −x, its left at +x, a little higher and wider)
    for side in (-1.0, 1.0):
        cx = side * (X_EYE + (LEFT_DX / 2 if side > 0 else 0.0))
        cy = Y_EYE + (LEFT_DY if side > 0 else 0.0)
        rx = EYE_RX + (LEFT_DX / 2 if side > 0 else 0.0)
        r2 = ((x - cx) / rx) ** 2 + ((y - cy) / EYE_RY) ** 2
        d -= 0.0075 * math.exp(-1.6 * r2 ** 1.5) * front
    # the mouth: a shallow groove
    d -= 0.0025 * _g((y - Y_MOUTH) / 0.0025) * _g(x / 0.022) * front
    # the chin
    d += 0.0170 * _g((y - Y_CHIN) / 0.012) * _g(x / 0.021) * front
    return d


def surface(nx: float, ny: float, nz: float) -> V3:
    """The point of the head in the unit direction (nx, ny, nz) of the sphere
    (displaced along that direction, as the tessellation is)."""
    bx, by, bz = RX * nx, RY * ny, RZ * nz
    d = displacement(bx, by, bz)
    return (C[0] + bx + d * nx, C[1] + by + d * ny, C[2] + bz + d * nz)


def at_xy(x: float, y: float) -> V3:
    """The front point whose base ellipsoid point has these x, y (relative to C)."""
    nx, ny = x / RX, y / RY
    nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
    return surface(nx, ny, nz)


def midline(step: float = 1e-4) -> List[V3]:
    """The midline profile of the front (x = 0), from top to bottom, fine."""
    out = []
    n = int(math.pi / step)
    for k in range(1, n):
        v = k * step                 # polar angle from the top
        ny, nz = math.cos(v), math.sin(v)
        out.append(surface(0.0, ny, nz))
    return out


def truth() -> Dict[str, V3]:
    prof = [p for p in midline() if p[2] - C[2] > 0.3 * RZ]
    tip = max(prof, key=lambda p: p[2])
    above = [p for p in prof if p[1] > tip[1]]
    # nasion: the deepest between the tip and the brow — search the band where
    # the profile turns (below the brow's crest)
    band = [p for p in above if p[1] - C[1] < Y_BROW]
    nasion = min(band, key=lambda p: p[2])
    glabella = max([p for p in above if p[1] > nasion[1] and p[1] - nasion[1] < 0.035], key=lambda p: p[2])
    below = [p for p in prof if p[1] - C[1] < Y_MOUTH]
    gnathion = max(below, key=lambda p: (p[2] - C[2]) - (p[1] - C[1]))
    exo_r = at_xy(-(X_EYE + EYE_RX), Y_EYE)
    exo_l = at_xy(X_EYE + LEFT_DX + EYE_RX, Y_EYE + LEFT_DY)
    return {"glabella": glabella, "nasion": nasion, "exocanthion_r": exo_r,
            "exocanthion_l": exo_l, "pronasale": tip, "gnathion": gnathion}


def infill_polygon() -> List[V3]:
    """A restoration infill (synthetic) on the tip of the nose: six points on
    the surface around the tip, in order."""
    out = []
    for k in range(6):
        a = 2 * math.pi * k / 6
        out.append(at_xy(0.0075 * math.cos(a), Y_TIP - 0.002 + 0.006 * math.sin(a)))
    return out


def tessellate() -> Tuple[List[V3], List[V3], List[int]]:
    rnd = random.Random(SEED)
    pos: List[V3] = []
    nrm: List[V3] = []
    for j in range(NV + 1):
        v = math.pi * j / NV
        for i in range(NU + 1):
            u = 2 * math.pi * i / NU
            nx, ny, nz = math.sin(v) * math.sin(u), math.cos(v), math.sin(v) * math.cos(u)
            x, y, z = surface(nx, ny, nz)
            if 0 < j < NV and i < NU:
                r = rnd.gauss(0.0, ROUGHNESS)
                x, y, z = x + r * nx, y + r * ny, z + r * nz
            pos.append((x, y, z))
            ln = math.sqrt((nx / RX) ** 2 + (ny / RY) ** 2 + (nz / RZ) ** 2) or 1.0
            nrm.append((nx / RX / ln, ny / RY / ln, nz / RZ / ln))
    # the seam (i = NU) is the same point as i = 0
    for j in range(NV + 1):
        pos[j * (NU + 1) + NU] = pos[j * (NU + 1)]
    idx: List[int] = []
    for j in range(NV):
        for i in range(NU):
            a = j * (NU + 1) + i
            b = a + NU + 1
            idx += [a, b, a + 1, a + 1, b, b + 1]
    return pos, nrm, idx


def pose_fn(yaw_deg: float, shift: Sequence[float]):
    a = math.radians(yaw_deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(p: Sequence[float]) -> V3:
        x, y, z = p[0] - C[0], p[1] - C[1], p[2] - C[2]
        x, z = ca * x + sa * z, -sa * x + ca * z
        return (x + C[0] + shift[0], y + C[1] + shift[1], z + C[2] + shift[2])

    def fn(n: Sequence[float]) -> V3:
        return (ca * n[0] + sa * n[2], n[1], -sa * n[0] + ca * n[2])
    return f, fn


def write_glb(path: str, pos: List[V3], nrm: List[V3], idx: List[int], name: str) -> None:
    pb = b"".join(struct.pack("<3f", *p) for p in pos)
    nb = b"".join(struct.pack("<3f", *n) for n in nrm)
    ib = b"".join(struct.pack("<I", k) for k in idx)
    binbuf = pb + nb + ib
    mins = [min(p[k] for p in pos) for k in range(3)]
    maxs = [max(p[k] for p in pos) for k in range(3)]
    gltf = {
        "asset": {"version": "2.0", "generator": "em-profiles pilots/statuaria-sintetica/make_head.py (SYNTHETIC, D-5)",
                  "copyright": "CC0-1.0 — synthetic head generated by a script, not a statue"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "material": 0}]}],
        "materials": [{"name": "marmo_sintetico", "pbrMetallicRoughness": {
            "baseColorFactor": [0.88, 0.85, 0.79, 1], "metallicFactor": 0, "roughnessFactor": 0.75}}],
        "buffers": [{"byteLength": len(binbuf)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pb), "target": 34962},
                        {"buffer": 0, "byteOffset": len(pb), "byteLength": len(nb), "target": 34962},
                        {"buffer": 0, "byteOffset": len(pb) + len(nb), "byteLength": len(ib), "target": 34963}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3", "min": mins, "max": maxs},
                      {"bufferView": 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
                      {"bufferView": 2, "componentType": 5125, "count": len(idx), "type": "SCALAR"}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    binbuf += b"\0" * ((4 - len(binbuf) % 4) % 4)
    glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binbuf))
    glb += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binbuf), 0x004E4942) + binbuf
    with open(path, "wb") as fh:
        fh.write(glb)


IRI = "https://w3id.org/extendedmatrix/profile/esempio-statuaria"


def em_json(name: str, title: str) -> Dict:
    """One unit (the surface of the face), one 3D model document with its
    representation model and the file; the package declared."""
    return {
        "header": {"format": "em.json", "version": "1.1", "schema_version": 2,
                   "generator": {"tool": "em-profiles pilots/statuaria-sintetica/make_head.py", "version": "0.1"},
                   "profiles": [{"iri": IRI, "version": "0.1.0"}]},
        "graphs": {"testa": {
            "graph_id": "testa", "name": title,
            "nodes": [
                {"id": "us1", "node_type": "US", "name": "US1",
                 "description": "Superficie del volto della testa sintetica (ESEMPIO, D-5)"},
                {"id": "d1", "node_type": "document", "name": "D.01",
                 "description": "Modello 3D della testa sintetica (generato, CC0)",
                 "data": {"url": f"{name}.glb"}},
                {"id": "rm1", "node_type": "representation_model", "name": f"{name}_RM",
                 "description": "Rappresentazione 3D della testa sintetica",
                 "data": {"url": f"{name}.glb"}},
            ],
            "edges": [
                {"id": "e1", "source": "us1", "target": "d1", "edge_type": "has_documentation"},
                {"id": "e2", "source": "d1", "target": "rm1", "edge_type": "has_representation_model"},
            ]}},
        "active_graph_id": "testa"}


#: «canonica»: eyes and chin close to the set's reference proportions;
#: «fuori-misura»: eyes 4 mm farther apart and 2 mm lower, the nose 3 mm
#: longer, the chin 5 mm lower — a face the reference does not describe well,
#: so the predicted points (the exocanthia) are tried where they are hard
VARIANTS = {
    "canonica": {},
    "fuori-misura": {"X_EYE": X_EYE + 0.002, "EYE_RX": EYE_RX + 0.002, "Y_EYE": Y_EYE - 0.002,
                     "Y_TIP": Y_TIP - 0.003, "Y_MOUTH": Y_MOUTH - 0.004, "Y_CHIN": Y_CHIN - 0.005},
}


def main(argv=None) -> Dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--name", default="testa-sintetica")
    ap.add_argument("--yaw", type=float, default=0.0, help="degrees about y")
    ap.add_argument("--shift", default="0,0,0", help="x,y,z metres")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="canonica")
    a = ap.parse_args(argv)
    globals().update(VARIANTS[a.variant])
    os.makedirs(a.out, exist_ok=True)
    shift = [float(v) for v in a.shift.split(",")]
    f, fn = pose_fn(a.yaw, shift)
    pos, nrm, idx = tessellate()
    pos = [f(p) for p in pos]
    nrm = [fn(n) for n in nrm]
    glb = os.path.join(a.out, a.name + ".glb")
    write_glb(glb, pos, nrm, idx, a.name)
    tr = {k: [round(c, 6) for c in f(v)] for k, v in truth().items()}
    poly = [[round(c, 6) for c in f(p)] for p in infill_polygon()]
    digest = "sha256:" + hashlib.sha256(open(glb, "rb").read()).hexdigest()
    doc = {
        "_note": "ESEMPIO SINTETICO (D-5) — la verità per costruzione della testa generata; non citare. / "
                 "SYNTHETIC EXAMPLE — the truth by construction of the generated head; not to be cited.",
        "model": os.path.basename(glb), "model_digest": digest, "license": "CC0-1.0",
        "variant": a.variant,
        "frame": {"units": "m", "up": "+y", "facing": f"+z turned {a.yaw:g}° about y", "yaw_deg": a.yaw,
                  "shift_m": shift},
        "generator": {"seed": SEED, "roughness_m": ROUGHNESS, "tessellation": [NU, NV],
                      "vertices": len(pos), "triangles": len(idx) // 3},
        "set": "stat:volto", "points": tr, "infill_polygon": poly,
    }
    with open(os.path.join(a.out, a.name + ".truth.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    title = "Testa sintetica (ESEMPIO, D-5)" + (f" · girata di {a.yaw:g}°" if a.yaw else "") + \
        (f" · {a.variant}" if a.variant != "canonica" else "")
    with open(os.path.join(a.out, a.name + ".em.json"), "w", encoding="utf-8") as fh:
        json.dump(em_json(a.name, title), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return doc


if __name__ == "__main__":
    d = main()
    print(json.dumps({"vertices": d["generator"]["vertices"], "points": d["points"]}, indent=1))
