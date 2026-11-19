"""ESEMPIO (D-5) — finding the canonical points of a face on a mesh, pure Python.

The method, in the order it runs (no learning, no texture — geometry only):

1. **Up is +y** (the model's frame; a statue lying down is not read).
2. **The tip of the nose** is the point farthest from the vertical axis of
   the bounding box, in the middle band of the height: it gives the facing
   direction, horizontal, from the axis to it.
3. **The midline profile** is the section of the mesh by the vertical plane
   through the tip and the facing direction (every triangle the plane cuts).
4. On that profile, binned every 0.5 mm of height and smoothed: the
   **pronasale** is its most anterior point; the **nasion** the first
   valley above it; the **glabella** the next crest above the nasion; the
   **gnathion** the most anterior-inferior point (45° forward and down) below
   the mouth, taken as lower than the tip by 0.6 × (nasion − tip).
5. **The other points** (the exocanthia) are not found: they are the set's
   reference positions (``ref``) brought onto the model by the similarity
   (rotation, uniform scale, translation; Horn's quaternions) that fits the
   found points to their references, then put on the surface along the facing
   direction. They are proposals of the second kind (``predicted``).

Everything returned is a proposal: the person confirms each point with the
pose tool, or places it elsewhere."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

V3 = Tuple[float, float, float]
BIN = 0.0005


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


class FitError(ValueError):
    pass


class Frame:
    """The face's frame: origin on the vertical axis at y = 0, ``s`` lateral
    (toward the head's left), ``up`` +y, ``f`` forward (the facing)."""

    def __init__(self, axis_x: float, axis_z: float, f: V3):
        self.o = (axis_x, 0.0, axis_z)
        self.up = (0.0, 1.0, 0.0)
        self.f = _norm((f[0], 0.0, f[2]))
        self.s = _cross(self.up, self.f)

    def local(self, p: Sequence[float]) -> V3:
        d = _sub(p, self.o)
        return (_dot(d, self.s), d[1], _dot(d, self.f))

    def world(self, q: Sequence[float]) -> V3:
        return _add(self.o, _add(_add(_mul(self.s, q[0]), _mul(self.up, q[1])), _mul(self.f, q[2])))


def facing(pos: Sequence[V3], tris: Sequence[Tuple[int, int, int]]) -> Tuple[Frame, V3, float]:
    ys = [p[1] for p in pos]
    y0, y1 = min(ys), max(ys)
    h = y1 - y0
    if h <= 0:
        raise FitError("the mesh has no height")
    lo, hi = y0 + 0.15 * h, y1 - 0.15 * h
    # the vertical axis: the area-weighted centre of the surface in the middle
    # band (the bounding box would be pulled forward by the nose itself)
    sw = sx = sz = 0.0
    for t in tris:
        p0, p1, p2 = pos[t[0]], pos[t[1]], pos[t[2]]
        cy = (p0[1] + p1[1] + p2[1]) / 3
        if not lo <= cy <= hi:
            continue
        c = _cross(_sub(p1, p0), _sub(p2, p0))
        w = math.sqrt(_dot(c, c))
        sw += w
        sx += w * (p0[0] + p1[0] + p2[0]) / 3
        sz += w * (p0[2] + p1[2] + p2[2]) / 3
    if sw <= 0:
        raise FitError("no surface in the middle band of the height")
    ax, az = sx / sw, sz / sw
    best, tip = -1.0, None
    for p in pos:
        if lo <= p[1] <= hi:
            r = (p[0] - ax) ** 2 + (p[2] - az) ** 2
            if r > best:
                best, tip = r, p
    if tip is None:
        raise FitError("no point in the middle band of the height")
    return Frame(ax, az, (tip[0] - ax, 0.0, tip[2] - az)), tip, h


def section(pos: Sequence[V3], tris: Sequence[Tuple[int, int, int]], frame: Frame, a0: float) -> List[V3]:
    """The points (local a, v, w) where the plane a = a0 cuts the mesh, front only."""
    loc = [frame.local(p) for p in pos]
    out: List[V3] = []
    for t in tris:
        pts = [loc[t[0]], loc[t[1]], loc[t[2]]]
        for i in range(3):
            p, q = pts[i], pts[(i + 1) % 3]
            da, db = p[0] - a0, q[0] - a0
            if (da < 0) != (db < 0) and da != db:
                k = da / (da - db)
                x = (a0, p[1] + k * (q[1] - p[1]), p[2] + k * (q[2] - p[2]))
                if x[2] > 0:
                    out.append(x)
    return out


def profile(points: Sequence[V3]) -> List[Tuple[float, float]]:
    """(v, w) every BIN of height: the outermost w, smoothed over three bins."""
    bins: Dict[int, float] = {}
    for _a, v, w in points:
        k = int(math.floor(v / BIN))
        if w > bins.get(k, -1e9):
            bins[k] = w
    keys = sorted(bins)
    raw = [(k * BIN + BIN / 2, bins[k]) for k in keys]
    out = []
    for i in range(len(raw)):
        win = [raw[j][1] for j in range(max(0, i - 1), min(len(raw), i + 2))
               if abs(raw[j][0] - raw[i][0]) < 2.5 * BIN]
        out.append((raw[i][0], sum(win) / len(win)))
    return out


def find_midline(pos, tris) -> Tuple[Frame, Dict[str, V3], float]:
    """The four midline points, local (a, v, w), and the model's height."""
    frame, tip_v, h = facing(pos, tris)
    a0 = frame.local(tip_v)[0]
    prof = profile(section(pos, tris, frame, a0))
    if len(prof) < 20:
        raise FitError("the midline section is too short to read a face")
    it = max(range(len(prof)), key=lambda i: prof[i][1])
    tip = prof[it]
    # walk up from the tip: the first valley, then the next crest
    i = it
    while i + 1 < len(prof) and prof[i + 1][1] <= prof[i][1]:
        i += 1
    inas = i
    while i + 1 < len(prof) and prof[i + 1][1] >= prof[i][1]:
        i += 1
    igla = i
    if inas == it or igla == inas:
        raise FitError("no nasion and glabella above the tip of the nose")
    nas, gla = prof[inas], prof[igla]
    below = tip[0] - 0.6 * (nas[0] - tip[0])
    cand = [p for p in prof if p[0] < below]
    if not cand:
        raise FitError("nothing of the chin below the mouth")
    gna = max(cand, key=lambda p: p[1] - p[0])
    pts = {"pronasale": (a0, tip[0], tip[1]), "nasion": (a0, nas[0], nas[1]),
           "glabella": (a0, gla[0], gla[1]), "gnathion": (a0, gna[0], gna[1])}
    return frame, pts, h


# ── the similarity (Horn 1987, quaternions; uniform scale) ──────────────────

def _jacobi4(m: List[List[float]]) -> Tuple[List[float], List[List[float]]]:
    a = [row[:] for row in m]
    v = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for _ in range(100):
        off = sum(a[i][j] ** 2 for i in range(4) for j in range(4) if i != j)
        if off < 1e-30:
            break
        for p in range(4):
            for q in range(p + 1, 4):
                if abs(a[p][q]) < 1e-300:
                    continue
                th = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = (1.0 if th >= 0 else -1.0) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(4):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(4):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(4):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    return [a[i][i] for i in range(4)], v


def similarity(src: Sequence[V3], dst: Sequence[V3]):
    """``f(p)`` mapping ``src`` onto ``dst`` at least squares (3+ points, not collinear)."""
    n = len(src)
    if n < 3:
        raise FitError("a similarity needs three points")
    cs = _mul(tuple(map(sum, zip(*src))), 1 / n)
    cd = _mul(tuple(map(sum, zip(*dst))), 1 / n)
    a = [_sub(p, cs) for p in src]
    b = [_sub(p, cd) for p in dst]
    S = [[sum(a[k][i] * b[k][j] for k in range(n)) for j in range(3)] for i in range(3)]
    sxx, sxy, sxz = S[0]
    syx, syy, syz = S[1]
    szx, szy, szz = S[2]
    N = [[sxx + syy + szz, syz - szy, szx - sxz, sxy - syx],
         [syz - szy, sxx - syy - szz, sxy + syx, szx + sxz],
         [szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy],
         [sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz]]
    vals, vecs = _jacobi4(N)
    k = max(range(4), key=lambda i: vals[i])
    q0, qx, qy, qz = (vecs[i][k] for i in range(4))
    R = [[q0 * q0 + qx * qx - qy * qy - qz * qz, 2 * (qx * qy - q0 * qz), 2 * (qx * qz + q0 * qy)],
         [2 * (qy * qx + q0 * qz), q0 * q0 - qx * qx + qy * qy - qz * qz, 2 * (qy * qz - q0 * qx)],
         [2 * (qz * qx - q0 * qy), 2 * (qz * qy + q0 * qx), q0 * q0 - qx * qx - qy * qy + qz * qz]]

    def rot(p):
        return (sum(R[0][j] * p[j] for j in range(3)), sum(R[1][j] * p[j] for j in range(3)),
                sum(R[2][j] * p[j] for j in range(3)))
    ra = [rot(p) for p in a]
    den = sum(_dot(p, p) for p in a)
    if den <= 0:
        raise FitError("the reference points coincide")
    scale = sum(_dot(ra[k], b[k]) for k in range(n)) / den

    def f(p):
        return _add(cd, _mul(rot(_sub(p, cs)), scale))
    f.scale = scale  # type: ignore[attr-defined]
    return f


def onto_surface(pos, tris, frame: Frame, q: V3, reach: float) -> Optional[V3]:
    """The first hit of the ray from in front of local ``q`` going back along
    the facing (−w): the surface point a person would click there."""
    o = frame.world((q[0], q[1], q[2] + reach))
    d = _mul(frame.f, -1.0)
    best = None
    for t in tris:
        p0, p1, p2 = pos[t[0]], pos[t[1]], pos[t[2]]
        e1, e2 = _sub(p1, p0), _sub(p2, p0)
        h = _cross(d, e2)
        a = _dot(e1, h)
        if abs(a) < 1e-14:
            continue
        f = 1.0 / a
        s = _sub(o, p0)
        u = f * _dot(s, h)
        if u < 0 or u > 1:
            continue
        qq = _cross(s, e1)
        v = f * _dot(d, qq)
        if v < 0 or u + v > 1:
            continue
        t_ = f * _dot(e2, qq)
        if t_ > 0 and (best is None or t_ < best):
            best = t_
    return None if best is None else _add(o, _mul(d, best))


def propose(pos, tris, points: Sequence[Dict]) -> Dict:
    """The proposals for the points of a landmark set (``points``: the set's
    entries with ``id`` and ``ref``). Returns ``{points: {id: {position,
    method}}, frame, scale, unit}``; world coordinates of the model."""
    frame, found, h = find_midline(pos, tris)
    refs = {str(p["id"]): tuple(p["ref"]) for p in points if p.get("ref") is not None}
    pairs = [(refs[k], found[k]) for k in found if k in refs]
    sim = similarity([a for a, _ in pairs], [b for _, b in pairs]) if len(pairs) >= 3 else None
    out: Dict[str, Dict] = {}
    for p in points:
        pid = str(p["id"])
        if pid in found:
            out[pid] = {"position": [round(c, 6) for c in frame.world(found[pid])], "method": "detected"}
        elif sim is not None and pid in refs:
            q = sim(refs[pid])
            hit = onto_surface(pos, tris, frame, q, reach=0.5 * h)
            if hit is not None:
                out[pid] = {"position": [round(c, 6) for c in hit], "method": "predicted"}
    unit = None
    if "nasion" in found and "gnathion" in found:
        unit = math.dist(found["nasion"], found["gnathion"])
    return {"points": out, "scale": getattr(sim, "scale", None), "unit_m": unit,
            "frame": {"facing": [round(c, 6) for c in frame.f], "up": [0.0, 1.0, 0.0]}}
