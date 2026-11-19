"""The stack in the graph — row G7 of the geophysics plan (MICRO-GEO08).

``geofisica.ingest`` reads a stack with the core (:func:`geofisica_core.
build_stack_cache`: the PNG cache, every file stamped) and writes it into the
open graph with ``em`` — ONE act, one undo step, the DTC of the act naming
this plugin::

    DTCAcquisitionNode «the stack»  (dtc_kind local_import; method, quantity,
        unit, value_scale, geo_stack_id, georef_source, epsg, georef, grid…)
      ──dtc_had_output──▶ ResourceNode per source file (id = res:<uuid5 of
                          its digest>, the id the stamps cite)
    DocumentNode per slice / section (D.nn; em_kind geof:fetta | geof:sezione;
        role analytical · content_nature 2d_object · geometry from the source
        of the position; geo_id; geo {orientation, depths, extent, line,
        cache_key, raster, vmin, vmax, valid_cells, grid, georef, stamp})
      ──has_linked_resource──▶ its source file's resource
    DTCProcessNode «rasterization» (format_conversion: the plugin as the
        software, the parameters, the cache key)
      ──dtc_had_input──▶ the acquisition

Identities: the acquisition and the documents are ``uuid5`` of what they are
ABOUT (method + stack, the slice's ``geo_id``), so importing the same stack
again changes what changed and adds nothing; a file renamed is the same
resource (its digest) and the same document (its depth band). A file whose
bytes changed is a new resource: the document is linked to it and the old
resource, linked by nobody any more, leaves.

The graph's georeference is never written here: when the graph has none and
the stack says an EPSG, it is PROPOSED (``georef_proposal``); a graph that
says another EPSG is told (``georef_other``). Interpretations — the USD of an
anomaly — are never written by an import (row G12 traces them).
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from s3dgraphy.em import EmError

PLUGIN_ID = "geofisica"
NS = "https://w3id.org/extendedmatrix/profile/geofisica/vocab/"
#: the kinds whose grid is the file's own coordinates (the instrument's)
MEASURED_KINDS = ("csv", "geotiff", "xyzv", "xyz_lines")
#: a declared georef whose ``source`` names a rigorous documentation
DOCUMENTED_SOURCES = ("figure", "plan", "report", "documentation", "survey", "pianta", "figura",
                      "relazione")
QUANTITY_OF = {"gpr": "ampiezza", "ert": "resistivita", "mag": "campo_magnetico"}
METHOD_LABEL = {"gpr": ("GPR", "GPR"), "ert": ("ERT", "ERT"), "mag": ("magnetometry", "magnetometria")}


class Said(EmError):
    """A refusal with its words in EN and IT."""

    def __init__(self, en: str, it: str):
        super().__init__({"en": en, "it": it})


def _core():
    import geofisica_core
    return geofisica_core


def _ids():
    from s3dgraphy.contract import stable_id
    return stable_id


def acquisition_id(method: str, stack: str) -> str:
    return _ids()("geofisica", "acquisition", method, stack)


def document_node_id(geo_id: str) -> str:
    return _ids()("geofisica", "document", geo_id)


def process_id(acquisition: str, cache_key: str) -> str:
    return _ids()("geofisica", "rasterization", acquisition, cache_key)


# ── the slots ───────────────────────────────────────────────────────────────

def _json_slot(value: Any, name: str) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            raise Said(f"{name}: not JSON ({value[:60]!r})", f"{name}: non è JSON ({value[:60]!r})")
    return value


def declared_from(value: Any) -> Any:
    """What the files do not say, as the core wants it: a callable stays; a
    dict ``{extent, section: {length, depth}, sections: {VERT1: {length,
    depth}}, transpose, row0, …}`` becomes ``f(spec) -> dict`` (a section
    takes its own line's, else ``section``; a slice the rest)."""
    if value is None or callable(value):
        return value
    if not isinstance(value, dict):
        raise Said("declared: a dict or a function", "declared: un dizionario o una funzione")
    sections = dict(value.get("sections") or {})
    common = dict(value.get("section") or {})
    plain = {k: v for k, v in value.items() if k not in ("sections", "section")}

    def per_spec(spec: Any) -> Dict[str, Any]:
        if getattr(spec, "orientation", "") == "vertical":
            own = sections.get(getattr(spec, "line", None) or "") or {}
            if isinstance(own, (list, tuple)):
                own = {"length": own[0], "depth": own[1]}
            out = dict(common, **own)
            out.update({k: v for k, v in plain.items() if k not in ("extent",)})
            return out
        return dict(plain)
    return per_spec


def _decoder() -> Optional[Callable[[str], Any]]:
    """A capture decoder when the host has Pillow (the core has none)."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None

    def decode(path: str):
        with Image.open(path) as im:
            return np.asarray(im.convert("RGB"))
    return decode


# ── the placement → the document's geometry axis ────────────────────────────

def placement(kind: str, manifest: Dict[str, Any], georef: Optional[Dict[str, Any]],
              declared: Any) -> Tuple[str, Optional[str]]:
    """``(geometry, georef_source)``: who says where the slices are (plan §2.6).

    * ``reality_based`` — the instrument or its processing (a GeoTIFF's keys,
      a world file, a grid in survey coordinates);
    * ``observable`` — another rigorous documentation (a declared placement
      whose source is a figure, a plan, a report; sizes declared from it);
    * ``asserted`` — placed by eye, no source."""
    if georef:
        src = str(georef.get("source") or "declared").lower()
        if any(w in src for w in DOCUMENTED_SOURCES):
            return "observable", src
        return "asserted", src
    g = manifest.get("georef") or {}
    src = str(g.get("source") or "none")
    if kind in MEASURED_KINDS or (src and src != "none"):
        return "reality_based", ("file" if src in ("", "none") else src)
    if declared:
        return "observable", "declared sizes"
    return "asserted", None


# ── the act ─────────────────────────────────────────────────────────────────

def _label_of(entry: Dict[str, Any], method: str, lang: str) -> str:
    m = METHOD_LABEL.get(method, (method.upper(), method.upper()))[lang == "it"]
    if entry.get("orientation") == "vertical":
        return (f"Sezione {m} {entry.get('line')}" if lang == "it"
                else f"{m} section {entry.get('line')}")
    if entry.get("depth_top") is not None and entry.get("depth_bottom") is not None:
        a, b = entry["depth_top"], entry["depth_bottom"]
        return (f"Fetta {m} {a:.2f}–{b:.2f} m" if lang == "it"
                else f"{m} slice {a:.2f}–{b:.2f} m")
    prod = entry.get("product") or os.path.basename(str(entry.get("source") or ""))
    return f"Fetta {m} {prod}" if lang == "it" else f"{m} slice {prod}"


def _extent(entry: Dict[str, Any]) -> Optional[List[float]]:
    """The slice's rectangle in the stack's local frame, from the CENTRES of
    its first and last cells (half a step out). A grid that says only
    ``nx``/``ny`` and the steps (the cache's per-slice grid) has its last
    centre computed (MICRO-GEO09: the documents of G7 had no extent)."""
    g = dict(entry.get("grid") or {})
    for ax in ("x", "y"):
        n, lo, step = g.get(f"n{ax}"), g.get(f"{ax}_min"), g.get(f"{ax}_step")
        if g.get(f"{ax}_max") is None and None not in (n, lo, step):
            g[f"{ax}_max"] = float(lo) + (int(n) - 1) * float(step)
    keys = ("x_min", "y_min", "x_max", "y_max")
    if all(g.get(k) is not None for k in keys):
        hx, hy = float(g.get("x_step") or 0) / 2.0, float(g.get("y_step") or 0) / 2.0
        # to the micrometre: 92.00000000000001 is the sum of 343 steps, not a size
        return [round(float(g["x_min"]) - hx, 6) + 0.0, round(float(g["y_min"]) - hy, 6) + 0.0,
                round(float(g["x_max"]) + hx, 6) + 0.0, round(float(g["y_max"]) + hy, 6) + 0.0]
    return None


def _upsert(tx: Any, node_type: str, nid: str, name: Optional[str], data: Dict[str, Any],
            description: Optional[str] = None, *, keep_name: bool = True) -> bool:
    """A node with these fields: added when not there, else the fields that
    differ written (a name a person gave is kept when ``keep_name``).
    True when it was added."""
    node = tx.graph.find_node_by_id(nid)
    if node is None:
        tx.add_node(node_type, name, id=nid, description=description, data=data)
        return True
    have = dict(getattr(node, "data", None) or {})
    for k, v in data.items():
        if json.dumps(have.get(k), sort_keys=True, default=str) != json.dumps(v, sort_keys=True, default=str):
            tx.update(nid, f"data.{k}", v)
    if not keep_name and name and getattr(node, "name", None) != name:
        tx.update(nid, "name", name)
    if description and not (getattr(node, "description", "") or "").strip():
        tx.update(nid, "description", description)
    return False


def _find_document(graph: Any, geo_id: str) -> Optional[str]:
    """The document already carrying this ``geo_id`` (any id: a scene of 3DSC's too)."""
    own = graph.find_node_by_id(document_node_id(geo_id))
    if own is not None:
        return own.node_id
    for n in graph.nodes:
        if getattr(n, "node_type", "") == "document" and (n.data or {}).get("geo_id") == geo_id:
            return n.node_id
    return None


def _linked(graph: Any, source: str, edge_type: str) -> List[str]:
    return [e.edge_target for e in graph.edges if e.edge_source == source and e.edge_type == edge_type]


def _incoming(graph: Any, target: str, edge_type: str) -> List[str]:
    return [e.edge_source for e in graph.edges if e.edge_target == target and e.edge_type == edge_type]


def georef_advice(graph: Any, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """What the graph's georeference and the stack's say together (never written)."""
    from s3dgraphy.api import _geo_anchor, georeference_state
    g = manifest.get("georef") or {}
    epsg = g.get("epsg")
    out: Dict[str, Any] = {"graph": georeference_state(graph), "stack_epsg": epsg}
    if not epsg:
        return out
    core = _core()
    if out["graph"] in ("undeclared", "legacy_default"):
        e, n = g.get("origin_e"), g.get("origin_n")
        sx, sy = core.propose_shift(e, n) if core.is_absolute(e, n) else (0.0, 0.0)
        out["georef_proposal"] = {"epsg": int(epsg), "shift_x": float(sx), "shift_y": float(sy),
                                  "shift_z": 0.0}
    else:
        have = _geo_anchor(graph).get("epsg")
        if have and int(have) != int(epsg):
            out["georef_other"] = {
                "graph_epsg": int(have), "stack_epsg": int(epsg),
                "en": f"the graph is in EPSG:{have}, the stack in EPSG:{epsg}: nothing converted",
                "it": f"il grafo è in EPSG:{have}, la pila in EPSG:{epsg}: niente convertito"}
    return out


def ingest(folder: str, *, kind: Optional[str] = None, method: str = "gpr",
           quantity: Optional[str] = None, unit: Optional[str] = None, name: Optional[str] = None,
           declared: Any = None, georef: Optional[Dict[str, Any]] = None,
           value_scale: Optional[Dict[str, Any]] = None, colormap: Any = None,
           normalize: Optional[str] = None, value_range: Any = None,
           geometry: Optional[str] = None, decode: Optional[Callable[[str], Any]] = None,
           agent: Optional[Dict[str, str]] = None, lang: str = "en",
           out_dir: Optional[str] = None, at: Optional[str] = None) -> Dict[str, Any]:
    """Read the stack in ``folder``, cache it, write it into the open graph.
    Returns what was written (ids, the manifest's key and folder, the advice
    on the georeference, the warnings)."""
    from s3dgraphy import em
    from s3dgraphy.document_names import next_document_name
    core = _core()
    folder = os.fspath(folder)
    if not os.path.isdir(folder):
        raise Said(f"{folder}: not a folder", f"{folder}: non è una cartella")
    method = (method or "gpr").lower()
    if method not in core.METHODS:
        raise Said(f"method {method!r}: one of {', '.join(core.METHODS)}",
                   f"metodo {method!r}: uno tra {', '.join(core.METHODS)}")
    kind = kind or core.guess_kind(folder)
    if kind is None:
        raise Said(f"nothing in {folder} is a geophysical slice",
                   f"in {folder} non c'è nessuna fetta geofisica")
    if kind == "screenshot" and decode is None:
        decode = _decoder()
        if decode is None:
            raise Said("screen captures need an image decoder (Pillow) in this host",
                       "le schermate vogliono un decodificatore d'immagini (Pillow) in questo host")
    stack = name or core.stack_name(folder)
    acq = acquisition_id(method, stack)
    quantity = quantity or QUANTITY_OF.get(method)
    software = [agent] if agent else []
    decl = declared_from(declared)
    try:
        manifest = core.build_stack_cache(
            folder, kind=kind, out_dir=out_dir, colormap=colormap,
            normalize=normalize or ("SLICE" if kind == "geotiff" else "STACK"),
            value_range=value_range, value_scale=value_scale, declared=decl, georef=georef,
            decode=decode, method=method, quantity=quantity, unit=unit, name=stack,
            acquisition={"resource_id": acq, "kind": "acquisition"}, software=software, at=at)
    except (core.CacheError, core.ColorError) as exc:
        raise Said(getattr(exc, "en", str(exc)), getattr(exc, "it", str(exc)))
    geom, georef_source = placement(kind, manifest, georef, decl)
    if geometry:
        geom = geometry
    cache_dir = out_dir or os.path.join(core.cache_root(), manifest["cache_key"])
    st = manifest.get("stack") or {}
    g = manifest.get("georef") or {}
    lang = "it" if str(lang or "").startswith("it") else "en"
    m_label = METHOD_LABEL.get(method, (method.upper(), method.upper()))[lang == "it"]
    title = (f"Importazione della pila {m_label} {stack}" if lang == "it"
             else f"Import of the {m_label} stack {stack}")
    result: Dict[str, Any] = {"acquisition": acq, "documents": [], "resources": [], "added": [],
                              "updated": [], "removed": [], "cache_key": manifest["cache_key"],
                              "cache_dir": cache_dir, "reused": bool(manifest.get("reused")),
                              "geometry": geom, "georef_source": georef_source,
                              "warnings": manifest.get("warnings") or []}
    with em.write(title) as tx:
        graph = tx.graph
        acq_data = {
            "em_kind": "geof:pila", "dtc_kind": "local_import",
            "method": NS + "metodi/" + method,
            "quantity": (NS + "grandezze/" + quantity) if quantity and ":" not in quantity else quantity,
            "unit": st.get("unit"), "value_scale": st.get("value_scale"), "geo_stack_id": stack,
            "geo_kind": kind, "georef_source": georef_source, "epsg": g.get("epsg"),
            "georef": g or None, "grid": manifest.get("grid"),
            "depth_reference": "below ground", "source_folder": manifest.get("source_folder")}
        acq_data = {k: v for k, v in acq_data.items() if v is not None}
        if _upsert(tx, "dtc_acquisition", acq,
                   (f"Pila {m_label} {stack}" if lang == "it" else f"{m_label} stack {stack}"),
                   acq_data):
            result["added"].append(acq)
        else:
            result["updated"].append(acq)
        proc = process_id(acq, manifest["cache_key"])
        line = dict(agent or {"name": "Geofisica", "id": PLUGIN_ID})
        if _upsert(tx, "dtc_process", proc,
                   (f"Rasterizzazione {stack}" if lang == "it" else f"Rasterization of {stack}"),
                   {"dtc_kind": "format_conversion", "technique": "slice rasterization",
                    "software": [line, core.stamp.core_line()],
                    "parameters": {"kind": kind, "colormap": manifest.get("colormap"),
                                   "normalize": manifest.get("normalize"),
                                   "clip_percentiles": manifest.get("clip_percentiles"),
                                   "value_range": manifest.get("value_range"),
                                   "value_scale": st.get("value_scale")},
                    "cache_key": manifest["cache_key"]}):
            result["added"].append(proc)
        tx.add_edge(proc, "dtc_had_input", acq)
        for entry in manifest["slices"]:
            rid = core.resource_id_for(entry["source_digest"])
            src = entry["source"]
            fname = os.path.basename(src)
            size = os.path.getsize(src) if os.path.isfile(src) else None
            res_data = {"url": src, "checksum": entry["source_digest"], "geo_id": entry["geo_id"]}
            if size is not None:
                res_data["size_bytes"] = size
            if _upsert(tx, "resource", rid, fname, res_data, keep_name=False):
                result["added"].append(rid)
            tx.add_edge(acq, "dtc_had_output", rid)
            vertical = entry.get("orientation") == "vertical"
            geo = {k: entry.get(k) for k in ("orientation", "depth_top", "depth_bottom", "line",
                                              "product", "plane", "vmin", "vmax", "valid_cells",
                                              "grid", "georef", "stamp", "png_digest")}
            geo.update({"extent": _extent(entry), "raster": entry["raster"],
                        "cache_key": manifest["cache_key"], "stack": stack, "method": method})
            geo = {k: v for k, v in geo.items() if v is not None}
            doc_data = {"em_kind": "geof:sezione" if vertical else "geof:fetta",
                        "role": "analytical", "content_nature": "2d_object", "geometry": geom,
                        "geo_id": entry["geo_id"], "geo": geo}
            did = _find_document(graph, entry["geo_id"]) or document_node_id(entry["geo_id"])
            if _upsert(tx, "document", did, next_document_name(graph), doc_data,
                       description=_label_of(entry, method, lang)):
                result["added"].append(did)
            for old in _linked(graph, did, "has_linked_resource"):
                if old != rid and acq in _incoming(graph, old, "dtc_had_output"):
                    tx.remove_edge(did, "has_linked_resource", old)
                    if not _incoming(graph, old, "has_linked_resource"):
                        tx.remove(old)
                        result["removed"].append(old)
            tx.add_edge(did, "has_linked_resource", rid)
            result["documents"].append({"id": did, "geo_id": entry["geo_id"],
                                        "name": graph.find_node_by_id(did).name,
                                        "resource": rid, "raster": os.path.join(cache_dir, entry["raster"]),
                                        "stamp": os.path.join(cache_dir, entry["stamp"]) if entry.get("stamp") else None})
            result["resources"].append(rid)
        result["advice"] = georef_advice(graph, manifest)
    wr = tx.result
    result["written"] = bool(wr and wr.applied)
    result["message"] = wr.message if wr is not None else ""
    result["updated"] = [i for i in result["updated"] if wr is not None and any(
        op.get("node_id") == i or op.get("id") == i for op in wr.delta.ops)]
    return result


def _bool(v: Any) -> bool:
    return v is True or str(v).lower() in ("1", "true", "yes", "on", "sì", "si")


def command(slots: Dict[str, Any], *, agent: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """The command ``geofisica.ingest``: the slots as the host fills them
    (strings and numbers; the dicts as JSON text or as dicts)."""
    from s3dgraphy import em
    from .door import panel_slots, stack_folder
    slots = panel_slots(slots)          # the panel's plain fields (row G8): sizes, sections, scale
    folder = slots.get("folder") or slots.get("path")
    if not folder:
        raise Said("which folder? (the slot folder)", "quale cartella? (lo slot folder)")
    if os.path.isfile(str(folder)):     # a slice «read as» a stack (row G8): its folder
        folder = stack_folder(str(folder))
    lang = (em.host.current().language() or "en")[:2]
    vr = _json_slot(slots.get("value_range"), "value_range")
    return ingest(
        str(folder), kind=slots.get("kind") or None, method=str(slots.get("method") or "gpr"),
        quantity=slots.get("quantity") or None, unit=slots.get("unit") or None,
        name=slots.get("name") or None, declared=_json_slot(slots.get("declared"), "declared"),
        georef=_json_slot(slots.get("georef"), "georef"),
        value_scale=_json_slot(slots.get("value_scale"), "value_scale"),
        colormap=slots.get("colormap") or None, normalize=slots.get("normalize") or None,
        value_range=vr, geometry=slots.get("geometry") or None, decode=slots.get("decode"),
        agent=agent, lang=lang, at=slots.get("at") or None)


def stacks() -> List[Dict[str, Any]]:
    """The stacks of the open graph (for the console: ``em.ext.geofisica.stacks()``)."""
    from s3dgraphy import em
    graph = em.host.current().graph()
    out = []
    for n in graph.nodes if graph is not None else []:
        d = n.data or {}
        if getattr(n, "node_type", "") == "dtc_acquisition" and d.get("em_kind") == "geof:pila":
            docs = [s for r in _linked(graph, n.node_id, "dtc_had_output")
                    for s in _incoming(graph, r, "has_linked_resource")]
            out.append({"id": n.node_id, "name": n.name, "stack": d.get("geo_stack_id"),
                        "method": str(d.get("method") or "").rsplit("/", 1)[-1],
                        "documents": sorted(set(docs)), "epsg": d.get("epsg")})
    return out


__all__ = ["Said", "ingest", "command", "stacks", "placement", "declared_from", "georef_advice",
           "acquisition_id", "document_node_id", "process_id"]
