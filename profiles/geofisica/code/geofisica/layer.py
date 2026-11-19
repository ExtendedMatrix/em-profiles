"""The stacks as layers of the Space — row G10 of the geophysics plan (MICRO-GEO11).

``geofisica.layer`` (``space.layer@1``, ``layer = "raster_stack"``, read only)
describes the stacks of the open graph for the host to draw (decision G-2:
planes with a picture, as in Blender, with a depth cursor). The plugin draws
nothing: one layer per stack (the acquisition ``geof:pila`` of
:mod:`.ingest`), one plane per slice or section document::

    {kind: "raster_stack", id: <acquisition>, name,
     frame: {epsg, origin: [E, N] — the stack's georef in doubles, or null when
             the stack is not placed in the world (Basilica), rotation},
     ground: {mode: "surface", surface: <the graph's landscape_surface>} or flat,
     items: [{id: <document>, label, image: "cache/<key>/<png>" — inside the
              plugin's data folder, the only place the host serves from —
              null when the cache is not on this machine, stamp, extent (local
              metres; a section runs along its line and down, y = −depth),
              orientation, depth_top, depth_bottom, line}],
     display: all, or one at a time over 60 slices}

The slices go from the shallowest down (the products without a depth last,
by name), then the sections. A section's ``line`` — where it lies on the
ground — is the document's ``geo.trace`` when someone said it; the reports
give the Basilica's sections as length × depth only, so it is null there and
the host decides how to show a section it cannot place.

``em.plugins.shape`` gives the host the one normalised description; the
slot ``stack`` asks for one stack (its acquisition id or its name).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .inspector import KINDS, _band, _w
from .ingest import _incoming, _linked

#: over this many slices a stack is shown one at a time (plan §2.4; the host enforces it too)
ALL_MAX = 60


def _graph():
    from s3dgraphy import em
    return em.host.current().graph()


def _cache_root() -> Optional[str]:
    try:
        import geofisica_core as core
        return core.cache_root()
    except Exception:                                # noqa: BLE001 — a host without the core: no pictures
        return None


def _inner(root: Optional[str], key: Any, name: Any) -> Optional[str]:
    """``cache/<key>/<name>`` when that file is on this machine, else None."""
    if not root or not key or not name or "/" in str(name) or "\\" in str(name):
        return None
    return f"cache/{key}/{name}" if os.path.isfile(os.path.join(root, str(key), str(name))) else None


def _point(v: Any) -> Optional[List[float]]:
    if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
        return [float(v[0]), float(v[1])]
    return None


def _surface(graph: Any) -> Optional[str]:
    for n in graph.nodes:
        if getattr(n, "node_type", "") == "landscape_surface":
            return n.node_id
    return None


def _documents(graph: Any, acq_id: str) -> List[Any]:
    seen, out = set(), []
    for rid in _linked(graph, acq_id, "dtc_had_output"):
        for did in _incoming(graph, rid, "has_linked_resource"):
            node = graph.find_node_by_id(did)
            if node is None or did in seen or (node.data or {}).get("em_kind") not in KINDS:
                continue
            seen.add(did)
            out.append(node)
    return out


def _order(node: Any):
    geo = (node.data or {}).get("geo") or {}
    vertical = geo.get("orientation") == "vertical"
    top = geo.get("depth_top")
    return (vertical, top is None, top if top is not None else 0.0, node.name or "")


def _item(node: Any, root: Optional[str]) -> Optional[Dict[str, Any]]:
    geo = (node.data or {}).get("geo") or {}
    ext = geo.get("extent")
    if not (isinstance(ext, (list, tuple)) and len(ext) == 4):
        return None
    image = _inner(root, geo.get("cache_key"), geo.get("raster"))
    # a product without a depth is named by its product (the Inspector says «not said»)
    band = _w(geo["product"], geo["product"]) if geo.get("depth_top") is None and geo.get("product") \
        and geo.get("orientation") != "vertical" else (_band(geo) or _w("", ""))
    name = node.name or node.node_id
    trace = geo.get("trace")
    line = [_point(trace[0]), _point(trace[1])] if isinstance(trace, (list, tuple)) and len(trace) == 2 else None
    return {"id": node.node_id,
            "label": {lang: (f"{name} · {band[lang]}" if band.get(lang) else name) for lang in ("en", "it")},
            "image": image, "stamp": _inner(root, geo.get("cache_key"), geo.get("stamp")) if image else None,
            "extent": [float(x) for x in ext], "orientation": geo.get("orientation") or "horizontal",
            "depth_top": geo.get("depth_top"), "depth_bottom": geo.get("depth_bottom"),
            "line": line if line and None not in line else None}


def layers(slots: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """The command ``geofisica.layer``: the stacks of the open graph as layers."""
    graph = _graph()
    if graph is None:
        return []
    want = str((slots or {}).get("stack") or "").strip()
    root = _cache_root()
    surface = _surface(graph)
    out: List[Dict[str, Any]] = []
    for acq in graph.nodes:
        d = acq.data or {}
        if getattr(acq, "node_type", "") != "dtc_acquisition" or d.get("em_kind") != "geof:pila":
            continue
        if want and want not in (acq.node_id, d.get("geo_stack_id")):
            continue
        items = [i for i in (_item(n, root) for n in sorted(_documents(graph, acq.node_id), key=_order)) if i]
        if not items:
            continue
        g = d.get("georef") or {}
        e, n = g.get("origin_e"), g.get("origin_n")
        flat = sum(1 for i in items if i["orientation"] == "horizontal")
        out.append({
            "kind": "raster_stack", "id": acq.node_id, "name": acq.name or d.get("geo_stack_id") or acq.node_id,
            "frame": {"epsg": d.get("epsg") or g.get("epsg"),
                      "origin": [float(e), float(n)] if isinstance(e, (int, float)) and isinstance(n, (int, float))
                      else None,
                      "rotation": float(g.get("rotation") or 0.0)},
            "ground": {"mode": "surface", "surface": surface} if surface else {"mode": "flat", "z": 0.0},
            "items": items,
            "display": {"mode": "one" if flat > ALL_MAX else "all", "index": 0},
            "opacity": 1.0})
    return out


__all__ = ["layers", "ALL_MAX"]
