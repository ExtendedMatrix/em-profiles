"""The Inspector's section — row G9 of the geophysics plan (MICRO-GEO10).

``geofisica.section`` (``inspector.section@1``, read only) says what the
inspected node is to geophysics, in rows ``{label, value}`` whose words carry
EN and IT (the host writes them in the page's language):

* a slice or a section (a ``document`` of :mod:`.ingest`): method, what it is,
  the depth band (or the product when the depth is not said), the quantity
  and unit, the declared scale of the values with its source and confidence,
  the values and the cells read, who says where it lies (the ``geometry``
  axis, §2.6 of the plan) and the EPSG, the extent, the stack, the file, the
  identity, the stamp of its cached PNG;
* a USD — the interpretation of an anomaly (row G12 traces it) — that a
  property's extractor (or a combiner of extractors) links to slices: the
  slices it was read on, the bands, extractor or combiner;
* anything else: no rows (the host does not draw a section with nothing to
  say: ``when`` names the TYPE, only the plugin knows the node is its own).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .ingest import METHOD_LABEL, _incoming, _linked

KINDS = ("geof:fetta", "geof:sezione")
QUANTITY = {
    "ampiezza": ("signal amplitude", "ampiezza del segnale"),
    "ampiezza_media": ("mean amplitude", "ampiezza media"),
    "energia": ("energy (mean of squares)", "energia (media dei quadrati)"),
    "resistivita": ("electrical resistivity", "resistività elettrica"),
    "campo_magnetico": ("magnetic field anomaly", "anomalia del campo magnetico"),
}
GEOMETRY = {
    "reality_based": ("from the instrument (reality based)", "dallo strumento (reality based)"),
    "observable": ("from another documentation (observable)", "da un'altra documentazione (observable)"),
    "asserted": ("placed by eye (asserted)", "collocata a occhio (asserted)"),
}
GEOREF_SOURCE = {"file": ("the file", "il file"), "declared": ("declared", "dichiarata"),
                 "figure": ("a figure", "una figura"), "none": ("none", "nessuna")}
#: the slices a USD lists by name before saying «and n more»
SLICES_MAX = 6


def _w(en: str, it: str) -> Dict[str, str]:
    return {"en": en, "it": it}


def _row(label: Dict[str, str], value: Any) -> Dict[str, Any]:
    return {"label": label, "value": value}


def _m(x: Any) -> str:
    return f"{float(x):.2f}"


def _g(x: Any) -> str:
    """A number of a declaration as a person writes it (255, not 255.0)."""
    return f"{x:g}" if isinstance(x, (int, float)) else str(x)


def _graph():
    from s3dgraphy import em
    return em.host.current().graph()


def _method(code: str) -> Dict[str, str]:
    en, it = METHOD_LABEL.get(code, (code.upper(), code.upper()))
    return _w(en, it)


def _tail(uri: Any) -> str:
    return str(uri or "").rstrip("/").rsplit("/", 1)[-1]


def _band(geo: Dict[str, Any]) -> Optional[Dict[str, str]]:
    top, bottom = geo.get("depth_top"), geo.get("depth_bottom")
    if geo.get("orientation") == "vertical":
        if bottom is not None:
            return _w(f"0–{_m(bottom)} m below ground, along {geo.get('line')}",
                      f"0–{_m(bottom)} m dal piano di campagna, lungo {geo.get('line')}")
        return None
    if top is not None and bottom is not None:
        a, b = _m(top), _m(bottom)
        if 0 < abs(float(bottom) - float(top)) < 0.01:  # a band thinner than a centimetre (Alcudia: 5 mm)
            a, b = f"{float(top):.3f}", f"{float(bottom):.3f}"
        return _w(f"{a}–{b} m below ground", f"{a}–{b} m dal piano di campagna")
    if top is not None:
        return _w(f"{_m(top)} m below ground", f"{_m(top)} m dal piano di campagna")
    prod = geo.get("product") or "—"
    return _w(f"not said (product {prod})", f"non detta (prodotto {prod})")


def _scale(vs: Dict[str, Any]) -> Dict[str, str]:
    a, b = (vs.get("from") or [None, None])[:2]
    c, d = (vs.get("to") or [None, None])[:2]
    unit = vs.get("unit") or ""
    conf = str(vs.get("confidence") or "")
    src = vs.get("source") or ""
    conf_en = {"low": "low confidence", "medium": "medium confidence", "high": "high confidence"}.get(conf, conf)
    conf_it = {"low": "confidenza bassa", "medium": "confidenza media", "high": "confidenza alta"}.get(conf, conf)
    head = f"{_g(a)}–{_g(b)} → {_g(c)}–{_g(d)} {unit}".strip()
    tail_en = ", ".join(x for x in ("declared", conf_en, src) if x)
    tail_it = ", ".join(x for x in ("dichiarata", conf_it, src) if x)
    return _w(f"{head} ({tail_en})", f"{head} ({tail_it})")


def _stack_of(graph: Any, doc_id: str) -> Optional[Any]:
    for rid in _linked(graph, doc_id, "has_linked_resource"):
        for aid in _incoming(graph, rid, "dtc_had_output"):
            acq = graph.find_node_by_id(aid)
            if acq is not None and (acq.data or {}).get("em_kind") == "geof:pila":
                return acq
    return None


def _stamp_state(geo: Dict[str, Any]) -> Optional[Dict[str, str]]:
    stamp, key = geo.get("stamp"), geo.get("cache_key")
    if not stamp or not key:
        return None
    try:
        import geofisica_core as core
        here = os.path.isfile(os.path.join(core.cache_root(), key, stamp))
    except Exception:                                # noqa: BLE001 — a host without the cache: not said
        return None
    return _w("the cached PNG is stamped (" + os.path.basename(stamp) + ")",
              "il PNG della cache è timbrato (" + os.path.basename(stamp) + ")") if here else \
        _w("the cache is not on this machine (import the stack again)",
           "la cache non è su questa macchina (importa di nuovo la pila)")


def slice_rows(graph: Any, node: Any) -> List[Dict[str, Any]]:
    d = node.data or {}
    geo = dict(d.get("geo") or {})
    vertical = d.get("em_kind") == "geof:sezione"
    method = geo.get("method") or (d.get("geo_id") or "").split(":", 1)[0]
    acq = _stack_of(graph, node.node_id)
    ad = (acq.data or {}) if acq is not None else {}
    rows = [_row(_w("Method", "Metodo"), _method(method)),
            _row(_w("What", "Che cosa"), _w("vertical section", "sezione verticale") if vertical
                 else _w("horizontal slice", "fetta orizzontale"))]
    band = _band(geo)
    if band:
        rows.append(_row(_w("Depth", "Profondità"), band))
    q = _tail(ad.get("quantity"))
    if q:
        en, it = QUANTITY.get(q, (q, q))
        unit = ad.get("unit")
        rows.append(_row(_w("Quantity", "Grandezza"), _w(f"{en} ({unit})" if unit else en,
                                                         f"{it} ({unit})" if unit else it)))
    if isinstance(ad.get("value_scale"), dict):
        rows.append(_row(_w("Scale of the values", "Scala dei valori"), _scale(ad["value_scale"])))
    if geo.get("vmin") is not None and geo.get("vmax") is not None:
        cells = geo.get("valid_cells")
        g = geo.get("grid") or {}
        total = (g.get("nx") or 0) * (g.get("ny") or 0)
        share = f" · {100.0 * cells / total:.0f} %" if cells is not None and total else ""
        rows.append(_row(_w("Values in the file", "Valori nel file"),
                         f"{geo['vmin']:.6g} … {geo['vmax']:.6g}{share}"))
    where = GEOMETRY.get(str(d.get("geometry") or ""))
    if where:
        src = GEOREF_SOURCE.get(str(ad.get("georef_source") or ""), None)
        epsg = ad.get("epsg")
        extra_en = "; ".join(x for x in ((f"georeference: {src[0]}" if src else ""),
                                         (f"EPSG:{epsg}" if epsg else "")) if x)
        extra_it = "; ".join(x for x in ((f"georeferenza: {src[1]}" if src else ""),
                                         (f"EPSG:{epsg}" if epsg else "")) if x)
        rows.append(_row(_w("Where it lies", "Dove sta"),
                         _w(where[0] + (f" — {extra_en}" if extra_en else ""),
                            where[1] + (f" — {extra_it}" if extra_it else ""))))
    ext = geo.get("extent")
    if isinstance(ext, list) and len(ext) == 4:
        w, h = ext[2] - ext[0], ext[3] - ext[1]
        rows.append(_row(_w("Extent", "Estensione"),
                         _w(f"{w:.2f} × {h:.2f} m (local frame of the stack)",
                            f"{w:.2f} × {h:.2f} m (frame locale della pila)")))
    if acq is not None:
        rows.append(_row(_w("Stack", "Pila"), acq.name or ad.get("geo_stack_id") or acq.node_id))
    files = [graph.find_node_by_id(r) for r in _linked(graph, node.node_id, "has_linked_resource")]
    files = [f.name for f in files if f is not None and f.name]
    if files:
        rows.append(_row(_w("File", "File"), ", ".join(files)))
    rows.append(_row(_w("Identity", "Identità"), d.get("geo_id") or "—"))
    st = _stamp_state(geo)
    if st:
        rows.append(_row(_w("Stamp", "Timbro"), st))
    return rows


def _slices_of_extractor(graph: Any, ext_id: str) -> List[str]:
    """The geophysics documents an extractor was read on: directly, or through
    the region it was extracted from (on the slice's resource or on the slice)."""
    out: List[str] = []

    def is_slice(nid: str) -> bool:
        n = graph.find_node_by_id(nid)
        return n is not None and n.node_type == "document" and (n.data or {}).get("em_kind") in KINDS

    for t in _linked(graph, ext_id, "extracted_from"):
        n = graph.find_node_by_id(t)
        if n is None:
            continue
        if is_slice(t):
            out.append(t)
        elif n.node_type == "annotation_region":
            for on in _linked(graph, t, "is_on_resource"):
                if is_slice(on):
                    out.append(on)
                else:
                    out.extend(s for s in _incoming(graph, on, "has_linked_resource") if is_slice(s))
    return out


def usd_rows(graph: Any, node: Any) -> List[Dict[str, Any]]:
    slices: List[str] = []
    # the same extractor or combiner is the provenance of several properties (row G12): counted once
    sources = list(dict.fromkeys(pv for pid in _linked(graph, node.node_id, "has_property")
                                 for pv in _linked(graph, pid, "has_data_provenance")))
    extractors = combiners = 0
    for pv in sources:
        n = graph.find_node_by_id(pv)
        if n is None:
            continue
        if n.node_type == "combiner":
            found = [s for e in _linked(graph, pv, "combines") for s in _slices_of_extractor(graph, e)]
            if found:
                combiners += 1
                slices.extend(found)
        elif n.node_type == "extractor":
            found = _slices_of_extractor(graph, pv)
            if found:
                extractors += 1
                slices.extend(found)
    slices = list(dict.fromkeys(slices))
    if not slices:
        return []
    docs = [graph.find_node_by_id(s) for s in slices]
    rows = [_row(_w("Read on", "Letta su"),
                 _w(f"{len(docs)} geophysical slice" + ("s" if len(docs) != 1 else ""),
                    f"{len(docs)} " + ("fetta geofisica" if len(docs) == 1 else "fette geofisiche")))]
    how_en = ", ".join(x for x in ((f"{extractors} extractor" + ("s" if extractors != 1 else "")) if extractors else "",
                                   (f"{combiners} combiner" + ("s" if combiners != 1 else "")) if combiners else "") if x)
    how_it = ", ".join(x for x in ((f"{extractors} " + ("estrattore" if extractors == 1 else "estrattori")) if extractors else "",
                                   (f"{combiners} " + ("combinatore" if combiners == 1 else "combinatori")) if combiners else "") if x)
    rows.append(_row(_w("Through", "Attraverso"), _w(how_en, how_it)))
    tops = [(d.data or {}).get("geo", {}).get("depth_top") for d in docs]
    bottoms = [(d.data or {}).get("geo", {}).get("depth_bottom") for d in docs]
    tops = [t for t in tops if t is not None]
    bottoms = [b for b in bottoms if b is not None]
    if tops and bottoms:
        rows.append(_row(_w("Bands", "Bande"),
                         _w(f"{_m(min(tops))}–{_m(max(bottoms))} m below ground",
                            f"{_m(min(tops))}–{_m(max(bottoms))} m dal piano di campagna")))
    for d in docs[:SLICES_MAX]:
        rows.append(_row(_w("Slice", "Fetta"), f"{d.name} · {d.description or (d.data or {}).get('geo_id')}"))
    if len(docs) > SLICES_MAX:
        more = len(docs) - SLICES_MAX
        rows.append(_row(_w("Slice", "Fetta"), _w(f"and {more} more", f"e altre {more}")))
    kind = (node.data or {}).get("anomaly_type")
    if kind:
        from .trace import TYPES        # trace imports this module: asked here
        en_it = TYPES.get(_tail(kind))
        rows.insert(0, _row(_w("Anomaly", "Anomalia"), _w(*en_it) if en_it else _tail(kind)))
    return rows


def section(slots: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The command ``geofisica.section``: the rows of the inspected node."""
    graph = _graph()
    nid = slots.get("id")
    node = graph.find_node_by_id(str(nid)) if graph is not None and nid else None
    if node is None:
        return []
    if node.node_type == "document" and (node.data or {}).get("em_kind") in KINDS:
        return slice_rows(graph, node)
    if node.node_type == "USD":
        return usd_rows(graph, node)
    return []


__all__ = ["section", "slice_rows", "usd_rows"]
