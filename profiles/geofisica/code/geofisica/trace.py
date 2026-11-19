"""Tracing an anomaly on a slice — row G12 of the geophysics plan (MICRO-GEO13).

Three tools of the Space (``space.tool@1``), one per primitive —
``geofisica.trace.point`` (point), ``geofisica.trace.line`` (polyline),
``geofisica.trace.area`` (surface) — and one handler. The person draws on
the planes of a stack (row G11); the host fills the slot ``g`` with what was
placed::

    {primitive, vertices,               # the scene's points (not read here)
     frame: "layer",
     on: <the document of the first click>,
     at: [{on: <document>, uv: [u, v]}, …]   # one per vertex: the slice hit
                                             # and where on its picture
     through: [<document>, …]}               # optional: the slices shown
                                             # «up to» the cursor

A script may say the place in the stack's own metres instead:
``{frame: "stack", on: <document>, vertices: [[x, y], …]}`` (a section:
``[[along, -depth], …]``).

The decision G-4 (the paper *Sensors* 23/5 2769) and the domain rules: an
anomaly is a **USD** (no new node type); the slice is its source through an
**extractor** (one slice) or a **combiner** of one extractor per slice (more
slices), all in ONE act::

    USD «USDn» (data.em_kind geof:anomalia, anomaly_type)
      ──has_property──▶ geof:anomaly_type (the concept), geof:method,
                        geof:depth_top, geof:depth_bottom, geof:confidence
        ──has_data_provenance──▶ the extractor, or the combiner
    CombinerNode «C.nn» ──combines──▶ one extractor per slice
    ExtractorNode «D.nn.mm» (em_kind geof:anomalia_punto | _linea | _area;
        geo: the slice, its band, the place in metres and on the picture)
      ──extracted_from──▶ AnnotationRegion (point | polyline | surface; coords
        in the stack's local frame, metres: x east, y north, z = −depth; a
        section without a line on the ground: [along, 0, −depth] and
        frame geof:section; data.uv the same place on the slice's picture,
        [0, 1], v = 1 north or the surface)
        ──is_on_resource──▶ the slice's file (its ResourceNode)

The same trace twice adds nothing (the ids are of what the trace is about:
the slices and the place to the millimetre). The archaeological judgement —
what the USD is — stays the person's: the kind says the shape read on the
slice (the vocabulary's scope note), never an interpretation.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .ingest import METHOD_LABEL, NS, Said, _incoming, _linked
from .inspector import KINDS

#: the kinds of anomaly (vocab/anomalie.ttl: a test holds the two equal) → (en, it)
TYPES: Dict[str, Tuple[str, str]] = {
    "lineare": ("linear anomaly", "anomalia lineare"),
    "areale": ("areal anomaly", "anomalia areale"),
    "puntuale": ("point anomaly", "anomalia puntuale"),
    "iperbole": ("diffraction hyperbola", "iperbole di diffrazione"),
    "alta_resistivita": ("high-resistivity zone", "zona ad alta resistività"),
    "bassa_resistivita": ("low-resistivity zone", "zona a bassa resistività"),
}
#: what a primitive is when the person does not say the kind
DEFAULT_TYPE = {"point": "puntuale", "polyline": "lineare", "surface": "areale"}
#: the package's extractor type of each primitive (profile.json)
EXTRACTOR_TYPE = {"point": "geof:anomalia_punto", "polyline": "geof:anomalia_linea",
                  "surface": "geof:anomalia_area"}
#: the clicks a primitive takes (min, max)
CLICKS = {"point": (1, 1), "polyline": (2, None), "surface": (3, None)}
PRIM_WORDS = {"point": ("point", "punto"), "polyline": ("line", "linea"), "surface": ("area", "area")}
#: a trace is not a survey: one sign, a few hundred clicks at most
VERTICES_MAX = 500


def _graph():
    from s3dgraphy import em
    return em.host.current().graph()


def _ids():
    from s3dgraphy.contract import stable_id
    return stable_id


def _num(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _slice(graph: Any, nid: Any) -> Any:
    n = graph.find_node_by_id(str(nid)) if nid else None
    if n is None or n.node_type != "document" or (n.data or {}).get("em_kind") not in KINDS:
        return None
    return n


def _stack_of(graph: Any, doc_id: str) -> Tuple[Optional[str], Optional[str]]:
    """(the acquisition, the slice's resource) of a slice document."""
    for rid in _linked(graph, doc_id, "has_linked_resource"):
        for aid in _incoming(graph, rid, "dtc_had_output"):
            acq = graph.find_node_by_id(aid)
            if acq is not None and (acq.data or {}).get("em_kind") == "geof:pila":
                return aid, rid
    rs = _linked(graph, doc_id, "has_linked_resource")
    return None, (rs[0] if rs else None)


def _extent(doc: Any) -> List[float]:
    ext = ((doc.data or {}).get("geo") or {}).get("extent")
    if not (isinstance(ext, (list, tuple)) and len(ext) == 4 and all(_num(x) is not None for x in ext)):
        raise Said(f"{doc.name}: the slice has no extent (import the stack again)",
                   f"{doc.name}: la fetta non ha un'estensione (importa di nuovo la pila)")
    return [float(x) for x in ext]


def _vertical(doc: Any) -> bool:
    return ((doc.data or {}).get("geo") or {}).get("orientation") == "vertical"


def to_local(doc: Any, uv: Sequence[float]) -> List[float]:
    """A place on the slice's picture ([0, 1], v = 1 north or the surface)
    → the stack's metres on the slice's plane: [x, y] (a section: [along, −depth])."""
    x0, y0, x1, y1 = _extent(doc)
    u, v = float(uv[0]), float(uv[1])
    return [x0 + u * (x1 - x0), y0 + v * (y1 - y0)]


def to_uv(doc: Any, local: Sequence[float]) -> List[float]:
    x0, y0, x1, y1 = _extent(doc)
    return [(float(local[0]) - x0) / (x1 - x0) if x1 != x0 else 0.0,
            (float(local[1]) - y0) / (y1 - y0) if y1 != y0 else 0.0]


def _depth(doc: Any) -> Optional[float]:
    """The plane's depth below ground: the band's middle, None when not said."""
    geo = (doc.data or {}).get("geo") or {}
    top, bottom = _num(geo.get("depth_top")), _num(geo.get("depth_bottom"))
    if top is not None and bottom is not None:
        return (top + bottom) / 2.0
    return top if top is not None else bottom


def _coords(doc: Any, pts: List[List[float]]) -> Tuple[List[List[float]], str]:
    """The region's coords in the stack's frame (metres, z = −depth) and the
    frame's name; a section on a line said on the ground follows it."""
    if not _vertical(doc):
        d = _depth(doc)
        z = -d if d is not None else 0.0
        return [[round(p[0], 4) + 0.0, round(p[1], 4) + 0.0, round(z, 4) + 0.0] for p in pts], "geof:stack"
    trace = ((doc.data or {}).get("geo") or {}).get("trace")
    if isinstance(trace, (list, tuple)) and len(trace) == 2 and all(
            isinstance(q, (list, tuple)) and len(q) == 2 for q in trace):
        (ax, ay), (bx, by) = [(float(q[0]), float(q[1])) for q in trace]
        length = math.hypot(bx - ax, by - ay) or 1.0
        x0 = _extent(doc)[0]
        out = []
        for s, z in pts:
            f = (s - x0) / length
            out.append([round(ax + f * (bx - ax), 4) + 0.0, round(ay + f * (by - ay), 4) + 0.0, round(z, 4) + 0.0])
        return out, "geof:stack"
    return [[round(s, 4) + 0.0, 0.0, round(z, 4) + 0.0] for s, z in pts], "geof:section"


def _measure(primitive: str, pts: List[List[float]]) -> Dict[str, float]:
    if primitive == "polyline":
        return {"length_m": round(sum(math.dist(a, b) for a, b in zip(pts, pts[1:])), 4)}
    if primitive == "surface":
        a = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1])) / 2.0
        return {"area_m2": round(abs(a), 4)}
    return {}


def _type_of(value: Any, primitive: str) -> str:
    v = str(value or "").strip()
    if not v:
        return DEFAULT_TYPE[primitive]
    tail = v.rstrip("/").rsplit("/", 1)[-1] if "/" in v else v
    if tail in TYPES:
        return tail
    for k, (en, it) in TYPES.items():
        if v.lower() in (en, it):
            return k
    raise Said(f"the kind of anomaly {v!r}: one of {', '.join(TYPES)}",
               f"il tipo di anomalia {v!r}: uno tra {', '.join(TYPES)}")


def _next(graph: Any, node_type: str, prefix: str, *, sep: str = "", width: int = 0) -> str:
    n = 0
    for x in graph.nodes:
        name = str(getattr(x, "name", "") or "")
        if getattr(x, "node_type", "") == node_type and name.startswith(prefix + sep):
            tail = name[len(prefix + sep):]
            if tail.isdigit():
                n = max(n, int(tail))
    return f"{prefix}{sep}{n + 1:0{width}d}"


def _band_words(tops: List[float], bottoms: List[float]) -> Tuple[str, str]:
    if not tops and not bottoms:
        return "", ""
    a = min(tops) if tops else min(bottoms)
    b = max(bottoms) if bottoms else max(tops)
    band = f"{a:.2f}–{b:.2f} m" if b != a else f"{a:.2f} m"
    return f" ({band} below ground)", f" ({band} dal piano di campagna)"


def placed(graph: Any, g: Any, primitive: str) -> List[Tuple[Any, List[float]]]:
    """Each vertex: the slice it lies on and its place in the stack's metres."""
    if not isinstance(g, dict):
        raise Said("nothing placed: draw on a slice of a stack in the Space",
                   "niente di tracciato: disegna su una fetta di una pila nello Spazio")
    frame = str(g.get("frame") or "")
    out: List[Tuple[Any, List[float]]] = []
    if frame == "layer":
        at = g.get("at")
        if not isinstance(at, list) or not at:
            raise Said("the trace says no slice: draw on the planes of a stack",
                       "la traccia non dice nessuna fetta: disegna sui piani di una pila")
        for a in at:
            doc = _slice(graph, (a or {}).get("on")) if isinstance(a, dict) else None
            uv = (a or {}).get("uv") if isinstance(a, dict) else None
            if doc is None:
                raise Said("a point of the trace is not on a geophysical slice",
                           "un punto della traccia non è su una fetta geofisica")
            if not (isinstance(uv, (list, tuple)) and len(uv) == 2 and all(_num(q) is not None for q in uv)):
                raise Said(f"{doc.name}: a point without its place on the slice (uv)",
                           f"{doc.name}: un punto senza il suo posto sulla fetta (uv)")
            out.append((doc, to_local(doc, uv)))
    elif frame == "stack":
        doc = _slice(graph, g.get("on"))
        if doc is None:
            raise Said("the trace is not on a geophysical slice (on)",
                       "la traccia non è su una fetta geofisica (on)")
        for p in g.get("vertices") or []:
            if not (isinstance(p, (list, tuple)) and len(p) >= 2 and all(_num(q) is not None for q in p[:2])):
                raise Said("a vertex is not [x, y] in metres", "un vertice non è [x, y] in metri")
            out.append((doc, [float(p[0]), float(p[1])]))
    else:
        raise Said("a geophysical anomaly is traced on a slice of a stack in the Space, not on a model",
                   "un'anomalia geofisica si traccia su una fetta di una pila nello Spazio, non su un modello")
    lo, hi = CLICKS[primitive]
    if len(out) < lo or (hi is not None and len(out) > hi) or len(out) > VERTICES_MAX:
        en, it = PRIM_WORDS[primitive]
        want_en = f"{lo}" if hi == lo else f"at least {lo}"
        want_it = f"{lo}" if hi == lo else f"almeno {lo}"
        raise Said(f"an anomaly as a {en} takes {want_en} points, not {len(out)}",
                   f"un'anomalia come {it} vuole {want_it} punti, non {len(out)}")
    return out


def trace(g: Any, *, primitive: Optional[str] = None, kind: Any = None, confidence: Any = None,
          also: Sequence[str] = (), lang: str = "en") -> Dict[str, Any]:
    """Write the anomaly traced: the USD, its properties, the extractor(s)
    and (more slices) the combiner, as ONE act."""
    from s3dgraphy import em
    graph = _graph()
    if graph is None:
        raise Said("no graph is open", "nessun grafo è aperto")
    primitive = str(primitive or (g or {}).get("primitive") or "")
    if primitive == "line":
        primitive = "polyline"
    if primitive not in CLICKS:
        raise Said(f"a trace is a point, a line or an area (not {primitive!r})",
                   f"una traccia è un punto, una linea o un'area (non {primitive!r})")
    kind = _type_of(kind, primitive)
    conf = _num(confidence) if confidence not in (None, "") else None
    if confidence not in (None, "") and (conf is None or not 0.0 <= conf <= 1.0):
        raise Said(f"confidence {confidence!r}: a number from 0 to 1",
                   f"confidenza {confidence!r}: un numero da 0 a 1")
    pts = placed(graph, g, primitive)
    first = pts[0][0]
    acq, _res = _stack_of(graph, first.node_id)
    vertical = _vertical(first)
    # the slices: those the trace touches, then those shown «up to» or selected, of the same stack
    order: List[Any] = []
    warnings: List[Dict[str, str]] = []
    for doc, _p in pts:
        if doc not in order:
            order.append(doc)
    extra = list((g or {}).get("through") or []) + list(also or [])
    for nid in extra:
        doc = _slice(graph, nid)
        if doc is None or doc in order:
            continue
        if _stack_of(graph, doc.node_id)[0] != acq or _vertical(doc) != vertical:
            warnings.append({"en": f"{doc.name}: not a {'section' if vertical else 'slice'} of the same stack, left out",
                             "it": f"{doc.name}: non è una {'sezione' if vertical else 'fetta'} della stessa pila, lasciata fuori"})
            continue
        order.append(doc)
    for doc in order:
        if _stack_of(graph, doc.node_id)[0] != acq:
            raise Said("the trace runs over two stacks: draw it on one",
                       "la traccia passa su due pile: disegnala su una")
    if vertical and len(order) > 1:
        raise Said("a trace on a section stays on that section",
                   "una traccia su una sezione resta su quella sezione")
    local = [p for _d, p in pts]
    key = _ids()("geofisica", "trace", primitive, kind, *sorted(d.node_id for d in order),
                 *(f"{p[0]:.3f},{p[1]:.3f}" for p in local))
    stable = _ids()
    lang = "it" if str(lang or "").startswith("it") else "en"
    geos = [(d.data or {}).get("geo") or {} for d in order]
    tops = [x for x in (_num(q.get("depth_top")) for q in geos) if x is not None]
    bottoms = [x for x in (_num(q.get("depth_bottom")) for q in geos) if x is not None]
    band_en, band_it = _band_words(tops, bottoms)
    t_en, t_it = TYPES[kind]
    where_en = first.name if len(order) == 1 else f"{len(order)} slices from {first.name}"
    where_it = first.name if len(order) == 1 else f"{len(order)} fette da {first.name}"
    title = (f"Anomalia tracciata su {first.name}" if lang == "it" else f"Anomaly traced on {first.name}")
    method = str(geos[0].get("method") or "")
    usd_id = stable("geofisica", "usd", key)
    result: Dict[str, Any] = {"usd": usd_id, "extractors": [], "regions": [], "combiner": None,
                              "slices": [d.node_id for d in order], "kind": kind, "primitive": primitive,
                              "measure": _measure(primitive, local), "added": [], "warnings": warnings}
    with em.write(title) as tx:
        gr = tx.graph
        new = gr.find_node_by_id(usd_id) is None
        if new:
            tx.add_node("USD", _next(gr, "USD", "USD"), id=usd_id,
                        description=(f"{t_it.capitalize()} tracciata su {where_it}{band_it}" if lang == "it"
                                     else f"{t_en.capitalize()} traced on {where_en}{band_en}"),
                        data={"em_kind": "geof:anomalia", "anomaly_type": NS + "anomalie/" + kind,
                              "primitive": primitive, "stack": acq})
            result["added"].append(usd_id)
        extractors = []
        for i, doc in enumerate(order):
            xid = stable("geofisica", "extractor", key, doc.node_id)
            place = local       # the stack's metres: the same place on every slice of the stack
            coords, frame = _coords(doc, place)
            geo = (doc.data or {}).get("geo") or {}
            if gr.find_node_by_id(xid) is None:
                data = {"em_kind": EXTRACTOR_TYPE[primitive], "anomaly_type": NS + "anomalie/" + kind,
                        "geo": {"slice": doc.node_id, "stack": acq, "orientation": geo.get("orientation"),
                                "local": [[round(a, 4) + 0.0, round(b, 4) + 0.0] for a, b in place],
                                "uv": [[round(c, 6) + 0.0 for c in to_uv(doc, p)] for p in place],
                                "measure": _measure(primitive, place)}}
                for k in ("depth_top", "depth_bottom"):
                    if geo.get(k) is not None:
                        data[k] = geo[k]
                if conf is not None:
                    data["confidence"] = conf
                tx.add_node("extractor", _next(gr, "extractor", doc.name, sep=".", width=2), id=xid,
                            description=(f"{t_it} tracciata sulla fetta" if lang == "it"
                                         else f"{t_en} traced on the slice"), data=data)
                result["added"].append(xid)
            _acq, rid = _stack_of(gr, doc.node_id)
            region = tx.place_reading(xid, rid or doc.node_id,
                                      {"geometry_kind": primitive, "vertices": coords})
            for k, v in (("frame", frame), ("stack", acq), ("slice", doc.node_id),
                         ("uv", [[round(c, 6) + 0.0 for c in to_uv(doc, p)] for p in place])):
                if (gr.find_node_by_id(region).data or {}).get(k) != v:
                    tx.update(region, f"data.{k}", v)
            extractors.append(xid)
            result["regions"].append(region)
        result["extractors"] = extractors
        prov = extractors[0]
        if len(extractors) > 1:
            cid = stable("geofisica", "combiner", key)
            if gr.find_node_by_id(cid) is None:
                tx.add_node("combiner", _next(gr, "combiner", "C", sep=".", width=2), id=cid,
                            description=(f"{t_it} letta su {len(order)} fette" if lang == "it"
                                         else f"{t_en} read on {len(order)} slices"),
                            data={"em_kind": "geof:anomalia_su_fette", "slices": result["slices"],
                                  "stack": acq})
                result["added"].append(cid)
            for x in extractors:
                tx.add_edge(cid, "combines", x)
            prov = cid
            result["combiner"] = cid
        props = [("geof:anomaly_type", t_it if lang == "it" else t_en, NS + "anomalie/" + kind)]
        if method:
            m = METHOD_LABEL.get(method, (method.upper(), method.upper()))
            props.append(("geof:method", m[lang == "it"], NS + "metodi/" + method))
        if tops:
            props.append(("geof:depth_top", min(tops), None))
        if bottoms:
            props.append(("geof:depth_bottom", max(bottoms), None))
        if conf is not None:
            props.append(("geof:confidence", conf, None))
        for quale, value, concept in props:
            pid = tx.set_property(usd_id, quale, value, concept=concept, lang=lang)
            tx.add_edge(pid, "has_data_provenance", prov)
    wr = tx.result
    result["written"] = bool(wr and wr.applied)
    result["message"] = wr.message if wr is not None else ""
    result["name"] = graph.find_node_by_id(usd_id).name if graph.find_node_by_id(usd_id) is not None else None
    return result


def command(slots: Dict[str, Any], primitive: str) -> Dict[str, Any]:
    """The commands ``geofisica.trace.point|line|area``."""
    from s3dgraphy import em
    lang = (em.host.current().language() or "en")[:2]
    also = slots.get("ids") or []
    if isinstance(also, str):
        also = [also]
    return trace(slots.get("g"), primitive=primitive, kind=slots.get("type"),
                 confidence=slots.get("confidence"), also=also, lang=lang)


__all__ = ["trace", "command", "placed", "to_local", "to_uv", "TYPES", "EXTRACTOR_TYPE"]
