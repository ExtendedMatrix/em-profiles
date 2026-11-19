"""ESEMPIO INVENTATO (D-5) — non citare. / INVENTED EXAMPLE — not to be cited.

facemesh_fit — proposes the canonical points of the face (the set
``stat:volto`` of the package esempio-statuaria) on a 3D model, from its
geometry only (``fit.py`` says how). The proposals are VOLATILE (capability
``ingest-batch``): in the graph, drawn, not saved, until the person confirms
each point with the pose tool of the package — which writes the point as hers,
with ``proposed_by`` naming this plugin — or places it elsewhere.

The same Python in the two envelopes (SPEC-plugin §17.4): the pure plugin
``examples/facemesh_fit`` and the ``[code]`` of ``examples/esempio-statuaria-misto``."""
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

from s3dgraphy.em import EmError

from . import fit, mesh

NAME = "facemesh_fit"
SET = "stat:volto"
#: the extensions read (the permission the manifest declares says why)
MESH_EXT = (".glb", ".obj")

_ctx: Any = None


class Said(EmError):
    """A refusal with its words in EN and IT (``em.EmError``: ``str()`` is the
    host's language — the command fails with that sentence)."""

    def __init__(self, en: str, it: str):
        super().__init__({"en": en, "it": it})


def _url_of(node: Any) -> Optional[str]:
    d = node.data or {}
    for k in ("url", "path", "file"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def model_file(model_id: str) -> str:
    """The mesh file of the selected node: its own ``data.url``, or that of a
    representation model or linked resource it reaches (document →
    representation model → resource). A relative path is read against the
    folder of the document the host opened."""
    from s3dgraphy import em
    node = em.graph.node(model_id)
    seen = [node]
    for et in ("has_representation_model", "has_linked_resource"):
        for n in list(seen):
            seen += n.neighbours(type=et)
    urls = [u for u in (_url_of(n) for n in seen) if u]
    urls = [u for u in urls if u.lower().endswith(MESH_EXT)] or urls
    if not urls:
        raise Said(f"{node.name or model_id}: no 3D file is linked to this node",
                   f"{node.name or model_id}: a questo nodo non è legato nessun file 3D")
    url = urls[0]
    if url.startswith("file://"):
        url = url[7:]
    if not os.path.isabs(url):
        base = getattr(em.host.current(), "path", None)
        if not base:
            raise Said(f"{url}: a relative path, and the host does not say where the document is",
                       f"{url}: percorso relativo, e l'ospite non dice dove sta il documento")
        url = os.path.join(os.path.dirname(os.path.abspath(base)), url)
    if not os.path.isfile(url):
        raise Said(f"{url}: the file is not there", f"{url}: il file non c'è")
    if not url.lower().endswith(MESH_EXT):
        raise Said(f"{url}: only .glb and .obj are read", f"{url}: si leggono solo .glb e .obj")
    return url


def pose_target(model_id: str) -> str:
    """The node the points are placed ON: the 3D document that carries the
    selected representation model (as the pose tool of the Viewer places on
    the document shown), else the selected node itself."""
    from s3dgraphy import em
    node = em.graph.node(model_id)
    if node.type != "document":
        docs = [n for n in node.neighbours(type="has_representation_model", direction="in") if n.type == "document"]
        if len(docs) == 1:
            return docs[0].id
    return node.id


def _landmark_set() -> Dict[str, Any]:
    from s3dgraphy import em
    ls = None
    try:
        ls = em.host.current().overlay().landmark_set(SET)
    except Exception:                                # noqa: BLE001 — no document: the package's own
        ls = None
    if not ls and _ctx is not None and _ctx.package:
        ls = _ctx.package.landmark_set(SET)
    if not ls:
        raise Said(f"the landmark set {SET} is missing (the data of esempio-statuaria)",
                   f"manca l'insieme di punti {SET} (i dati di esempio-statuaria)")
    return ls


def _label(point: Dict[str, Any], lang: str) -> str:
    from s3dgraphy import em
    side = {"right": {"it": "destro", "en": "right"}, "left": {"it": "sinistro", "en": "left"}}.get(point.get("side") or "")
    c = em.vocab.find(str(point.get("concept") or "")) if point.get("concept") else None
    text = (c.label(lang) if c is not None else None) or str(point["id"])
    return f"{text} ({side[lang if lang in side else 'en']})" if side else text


def propose(slots: Dict[str, Any]) -> Dict[str, Any]:
    """The command ``facemesh.propose``: read, find, write the proposals."""
    from s3dgraphy import em
    model = str(slots["model"])
    path = model_file(model)
    ls = _landmark_set()
    points = list((ls.get("set") or {}).get("points") or [])
    kind = str(ls.get("extractor_type") or "stat:punto_canonico")
    pos, tris = mesh.read_mesh(path)
    try:
        found = fit.propose(pos, tris, points)
    except fit.FitError as exc:
        raise Said(f"no face found on this model: {exc}", f"nessun volto trovato su questo modello: {exc}")
    lang = (em.host.current().language() or "en")[:2]
    lang = lang if lang in ("it", "en") else "en"
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    version = getattr(_ctx, "version", "?")
    by = f"{NAME} {version}"
    on = pose_target(model)
    head = f"facemesh:{on}:{digest[:12]}:{version}"
    title = {"it": "Proposta dei punti del volto", "en": "Proposed face points"}[lang]
    rows: List[Dict[str, Any]] = []
    with em.write(f"{title} ({by})", volatile=True) as tx:
        cid = tx.add_node("combiner", f"{title} · {by}", id=head,
                          data={"facemesh_proposal": {"set": SET, "on": on, "by": by, "model_sha256": digest,
                                                      "frame": found["frame"], "unit_m": found["unit_m"],
                                                      "note": "glTF node transforms not applied"}})
        for p in points:
            got = found["points"].get(str(p["id"]))
            if got is None:
                continue
            label = _label(p, lang)
            # an extractor of the set's own type, with its point on the model (the
            # core writes it: a region the Viewer draws) — not a canonical point
            # yet: no data.landmark until the person confirms it
            xid = tx.add_extractor(kind, on=on, point=got["position"], name=f"? {label}")
            tx.update(xid, "data.proposal", {"set": SET, "point": str(p["id"]), "concept": p.get("concept"),
                                             "label": label, "lang": lang, "position": got["position"],
                                             "method": got["method"], "on": on, "by": by})
            tx.add_edge(cid, "combines", xid)
            region = next((e.edge_target for e in tx.graph.edges
                           if e.edge_source == xid and e.edge_type == "extracted_from"), None)
            rows.append({"point": str(p["id"]), "label": label, "position": got["position"],
                         "method": got["method"], "proposal": xid, "region": region})
    return {"model": on, "file": os.path.basename(path), "by": by, "proposals": rows,
            "unit_m": found["unit_m"], "written": bool(tx.result and tx.result.applied)}


def region_of(extractor_id: str) -> Optional[str]:
    """The region (the point on the model) of a proposal: what goes with it."""
    from s3dgraphy import em
    for e in em.graph.node(extractor_id).edges(type="extracted_from"):
        return e.target.id
    return None


def proposals(model: Optional[str] = None) -> List[Dict[str, Any]]:
    """The proposals in the graph (for the console: ``em.ext.facemesh_fit.proposals()``)."""
    from s3dgraphy import em
    out = []
    for n in em.graph.nodes(type="extractor"):
        pr = (n.data or {}).get("proposal")
        if pr and pr.get("set") == SET and (model is None or pr.get("on") == model):
            out.append(dict(pr, id=n.id, region=region_of(n.id)))
    return out


def setup(ctx: Any) -> None:
    global _ctx
    _ctx = ctx
    ctx.command("facemesh.propose", propose)
    ctx.expose("proposals", proposals)


def teardown(ctx: Any) -> None:
    global _ctx
    _ctx = None


plugin = type("Plugin", (), {"setup": staticmethod(setup), "teardown": staticmethod(teardown)})
