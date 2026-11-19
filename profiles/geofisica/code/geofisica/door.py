"""«Porta dentro…» for a geophysical stack — row G8 of the geophysics plan (MICRO-GEO09).

Three commands around :func:`geofisica.ingest.ingest` (row G7):

* ``geofisica.read`` — the reader of «Porta dentro…» (``door.reader@2``): it
  takes a FOLDER (a stack is a folder), accepts the extensions the host does
  not read (``.asc .xyz .csv``) and CLAIMS those it does (``.tif .tiff .jpg
  .jpeg .png``: offered as «Leggi come: pila geofisica», never taken). It names
  the panel ``import``: a host that draws panels opens it with the folder, the
  person says what the files do not (the method, the sizes of a matrix, the
  scale of the values) and «Importa» reads. A host that draws no panel invokes
  it straight away: then the method is the one the format suggests
  (:data:`METHOD_OF_KIND`) and the sizes are 1 unit per cell, said as a
  warning — importing again from the panel rewrites the same documents (the
  identities are of the depth band, not of the act). A FILE given to it reads
  the folder it is in (a slice alone is not a stack).
* ``geofisica.describe`` — read only, the panel's value: what the folder is
  (the format, how many slices and sections, the depths, what is already in
  the graph, what is missing), without reading a raster.
* the panel's own fields (the sizes, the sections, the scale) fill slots of
  ``geofisica.ingest`` in words a person writes (``92``, ``VERT1=92x8``,
  ``1-255``): :func:`panel_slots` turns them into the declarations of row G7.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .ingest import Said, _json_slot

#: the method a format suggests when nobody says it (the panel's default, the
#: plain reader's choice): the matrices, volumes and lines of points we have
#: are ERT inversions (Basilica Iulia); rasters, captures and CSV grids GPR
#: (UA Ilici, Alcudia, Tivoli)
METHOD_OF_KIND = {"ascii_matrix": "ert", "xyzv": "ert", "xyz_lines": "ert",
                  "csv_grid": "gpr", "geotiff": "gpr", "image_stack": "gpr", "screenshot": "gpr"}

_NUM = r"[-+]?\d+(?:[.,]\d+)?"


def _num(text: str) -> float:
    return float(text.replace(",", "."))


def _pair(value: Any, name: str) -> Optional[List[float]]:
    """``"1-255"``, ``"1..255"``, ``"1 255"``, ``"-2;3"``, ``[1, 255]`` → ``[1.0, 255.0]``."""
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return [float(value[0]), float(value[1])]
    # a minus is a sign only where no digit stands before it: «1-255» is two numbers
    nums = re.findall(r"(?:(?<![\d.])-)?\d+(?:\.\d+)?", str(value).replace(",", "."))
    if len(nums) != 2:
        raise Said(f"{name}: two numbers, as 1-255 ({value!r})", f"{name}: due numeri, come 1-255 ({value!r})")
    return [float(nums[0]), float(nums[1])]


def _sections(value: Any) -> Optional[Dict[str, List[float]]]:
    """``"VERT1=92x8, VERT4=50x8"`` (or JSON ``{"VERT1": [92, 8]}``) → length × depth per line."""
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        return {str(k): [float(v[0]), float(v[1])] for k, v in value.items()}
    text = str(value).strip()
    if text.startswith("{"):
        return _sections(_json_slot(text, "sections"))
    out: Dict[str, List[float]] = {}
    for part in re.split(r"[;,\n]+", text):
        if not part.strip():
            continue
        m = re.fullmatch(rf"\s*([^=:\s]+)\s*[=:]\s*({_NUM})\s*[x×*]\s*({_NUM})\s*(?:m)?\s*", part)
        if not m:
            raise Said(f"sections: LINE=LENGTHxDEPTH, as VERT1=92x8 ({part.strip()!r})",
                       f"sezioni: LINEA=LUNGHEZZAxPROFONDITÀ, come VERT1=92x8 ({part.strip()!r})")
        out[m.group(1)] = [_num(m.group(2)), _num(m.group(3))]
    return out or None


def _number(value: Any, name: str) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        raise Said(f"{name}: a number ({value!r})", f"{name}: un numero ({value!r})")


def panel_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    """The panel's plain fields folded into the declarations of
    ``geofisica.ingest``: ``extent_x``/``extent_y`` (m), ``sections``
    (``VERT1=92x8, …``), ``section_length``/``section_depth`` (every section)
    → ``declared``; ``scale_from``/``scale_to`` (``1-255``, ``0-3500``),
    ``scale_unit``, ``scale_source`` → ``value_scale`` (confidence low: a
    declaration, never a measure). A field written wins over the same key of
    the JSON slot."""
    out = dict(slots)
    declared = _json_slot(out.get("declared"), "declared") or {}
    if not isinstance(declared, dict):
        raise Said("declared: a JSON object", "declared: un oggetto JSON")
    ex, ey = _number(out.pop("extent_x", None), "extent_x"), _number(out.pop("extent_y", None), "extent_y")
    if (ex is None) != (ey is None):
        raise Said("the extent wants both sizes (x and y, in m)", "l'estensione vuole le due misure (x e y, in m)")
    if ex is not None:
        declared["extent"] = [ex, ey]
    sec = _sections(out.pop("sections", None))
    if sec:
        declared["sections"] = dict(declared.get("sections") or {}, **sec)
    sl, sd = _number(out.pop("section_length", None), "section_length"), _number(out.pop("section_depth", None), "section_depth")
    if sl is not None or sd is not None:
        common = dict(declared.get("section") or {})
        if sl is not None:
            common["length"] = sl
        if sd is not None:
            common["depth"] = sd
        declared["section"] = common
    if declared:
        out["declared"] = declared
    scale = _json_slot(out.get("value_scale"), "value_scale") or {}
    sf, st = _pair(out.pop("scale_from", None), "scale_from"), _pair(out.pop("scale_to", None), "scale_to")
    unit, source = out.pop("scale_unit", None), out.pop("scale_source", None)
    if sf is not None:
        scale["from"] = sf
    if st is not None:
        scale["to"] = st
    if unit:
        scale["unit"] = str(unit)
    if source:
        scale["source"] = str(source)
    if scale:
        if not ("from" in scale and "to" in scale):
            raise Said("the scale of the values wants from and to (as 1-255 and 0-3500)",
                       "la scala dei valori vuole da e a (come 1-255 e 0-3500)")
        scale.setdefault("confidence", "low")
        out["value_scale"] = scale
    return out


def stack_folder(path: str) -> str:
    """The folder of a stack: the path itself, or the folder a file is in."""
    path = os.fspath(path)
    return path if os.path.isdir(path) else os.path.dirname(path)


def _core():
    import geofisica_core
    return geofisica_core


def read(slots: Dict[str, Any], *, run) -> Dict[str, Any]:
    """The reader ``geofisica.read``: the folder (or the folder of a file),
    the method the format suggests when none is said, then ``run`` (the
    ingest command) with the same slots."""
    path = slots.get("folder") or slots.get("path")
    if not path:
        raise Said("which folder? (the slot folder)", "quale cartella? (lo slot folder)")
    if not os.path.exists(str(path)):
        raise Said(f"{path}: not found", f"{path}: non trovato")
    folder = stack_folder(str(path))
    out = dict(slots, folder=folder)
    out.pop("path", None)
    if not out.get("method"):
        kind = out.get("kind") or _core().guess_kind(folder)
        out["method"] = METHOD_OF_KIND.get(kind or "", "gpr")
    return run(out)


def _documents_there(folder: str) -> Tuple[int, Optional[str]]:
    """How many documents of the open graph already come from this folder (by
    the acquisition's ``source_folder``), and the stack's name."""
    try:
        from s3dgraphy import em
        graph = em.host.current().graph()
    except Exception:  # noqa: BLE001 — no host: nothing there
        return 0, None
    if graph is None:
        return 0, None
    want = os.path.realpath(folder)
    from .ingest import _incoming, _linked
    for n in graph.nodes:
        d = n.data or {}
        if getattr(n, "node_type", "") == "dtc_acquisition" and d.get("em_kind") == "geof:pila" \
                and d.get("source_folder") and os.path.realpath(str(d["source_folder"])) == want:
            docs = {s for r in _linked(graph, n.node_id, "dtc_had_output")
                    for s in _incoming(graph, r, "has_linked_resource")}
            return len(docs), str(d.get("geo_stack_id") or n.name)
    return 0, None


KIND_WORDS = {
    "csv_grid": ("CSV grids", "griglie CSV"), "ascii_matrix": ("ASCII matrices", "matrici ASCII"),
    "xyzv": ("XYZV volumes", "volumi XYZV"), "xyz_lines": ("XYZ lines", "linee XYZ"),
    "geotiff": ("GeoTIFF rasters", "raster GeoTIFF"), "image_stack": ("pictures", "immagini"),
    "screenshot": ("screen captures", "schermate")}


def describe(slots: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The panel's value: what the folder is, read from the names (no raster
    read: the panel asks again at each change)."""
    path = slots.get("folder") or slots.get("path")
    W = lambda en, it: {"en": en, "it": it}  # noqa: E731
    if not path:
        return [{"label": W("Folder", "Cartella"),
                 "value": W("none yet: «Porta dentro una cartella…» or write it above",
                            "ancora nessuna: «Porta dentro una cartella…» o scrivila sopra")}]
    path = str(path)
    if not os.path.exists(path):
        return [{"label": W("Folder", "Cartella"), "value": W(f"{path}: not found", f"{path}: non trovata")}]
    folder = stack_folder(path)
    core = _core()
    kind = slots.get("kind") or core.guess_kind(folder)
    rows: List[Dict[str, Any]] = [{"label": W("Stack", "Pila"), "value": slots.get("name") or core.stack_name(folder)}]
    if kind is None:
        rows.append({"label": W("Format", "Formato"),
                     "value": W("nothing here is a geophysical slice", "qui non c'è nessuna fetta geofisica")})
        return rows
    words = KIND_WORDS.get(kind, (kind, kind))
    rows.append({"label": W("Format", "Formato"), "value": W(words[0], words[1])})
    if kind in ("xyzv",):
        n = sum(1 for x in os.listdir(folder) if x.lower().endswith(core.ASCII_EXT))
        rows.append({"label": W("Files", "File"), "value": n})
    else:
        try:
            _, specs = core.scan_stack(folder, kind if kind != "screenshot" else "image_stack")
        except Exception as exc:  # noqa: BLE001 — said, never raised into the panel
            rows.append({"label": W("Reading", "Lettura"), "value": str(exc)})
            specs = []
        hor = [s for s in specs if s.orientation != "vertical"]
        ver = [s for s in specs if s.orientation == "vertical"]
        rows.append({"label": W("Slices", "Fette"), "value": len(hor)})
        if ver:
            rows.append({"label": W("Sections", "Sezioni"), "value": ", ".join(str(s.line) for s in ver)})
        known = [s for s in hor if s.depth_known]
        if known:
            rows.append({"label": W("Depths", "Profondità"),
                         "value": f"{min(s.depth_top for s in known):.2f}–{max(s.depth_bottom for s in known):.2f} m"})
        products = [s.product for s in hor if s.product]
        if products:
            rows.append({"label": W("Products (no depth)", "Prodotti (senza profondità)"), "value": ", ".join(products)})
    method = slots.get("method") or METHOD_OF_KIND.get(kind, "gpr")
    rows.append({"label": W("Method", "Metodo"), "value": str(method).upper()})
    if kind == "ascii_matrix" and not (slots.get("extent_x") or slots.get("declared")):
        rows.append({"label": W("Missing", "Manca"),
                     "value": W("the extent in m (the matrices do not say it: 1 unit per cell until then)",
                                "l'estensione in m (le matrici non la dicono: 1 unità per cella finché manca)")})
    n, stack = _documents_there(folder)
    if n:
        rows.append({"label": W("In the graph", "Nel grafo"),
                     "value": W(f"{n} documents of {stack}: importing again updates them",
                                f"{n} documenti di {stack}: importare di nuovo li aggiorna")})
    return rows


__all__ = ["METHOD_OF_KIND", "panel_slots", "stack_folder", "read", "describe"]
