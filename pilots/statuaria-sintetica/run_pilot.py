"""MICRO-PL20 · the statuary pilot, synthetic (D-5), in the two forms (D-20).

ESEMPIO SINTETICO — non citare. / SYNTHETIC EXAMPLE — not to be cited.

The whole road of a community package with its plugin, on generated heads
whose canonical points are known by construction (``make_head.py``), with
nothing but the libraries every tool uses (s3Dgraphy for the packages, the
plugins, the pose and the combiners; stratigraph-templates for the sheet):

* **separata** — ``esempio-statuaria`` (data) and ``facemesh_fit`` (code) as two
  archives; the plugin installed first, so its refusal without the data is
  measured, then the data;
* **mista** — ``esempio-statuaria`` 0.1.0 as ONE archive with its code (the
  stub of before), then updated to 0.1.1: the data stay 0.1.0, the code
  0.1.0 → 0.2.0, the trust question asked again (its permission changed).

On every head, in each form: the plugin proposes the six points (volatile);
the person confirms them (the pose tool's road: ``place_landmark`` with her
ORCID, ``proposed_by`` naming the plugin); the combiners compute; the points
farther than the tolerance from the truth are placed again where they are
(the combiners compute again); the infill surface is drawn, its area written
with its provenance, the phase and the working chosen from the package's
vocabularies; the document is saved and read back; the sheet of the package
is filled from the graph and drawn (IT and EN).

    python run_pilot.py OUT_DIR          # both forms, every head; writes OUT_DIR/summary.json

Each form runs in its own process with its own machine folders (the
``S3DGRAPHY_*`` and ``EM_VOCABULARIES_DIR`` variables, under OUT_DIR/machine-*):
``~/.s3dgraphy`` is never written. A plugin module imported in one process
is not the other's (the loader would say «restart»)."""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tarfile
import io
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EX = REPO / "examples"
#: the ORCID of ORCID's own documentation (Josiah Carberry, a fictitious person)
ORCID = "0000-0002-1825-0097"
SET = "stat:volto"
IRI = "https://w3id.org/extendedmatrix/profile/esempio-statuaria"
V_FASE = IRI + "/vocab/fase-superficie/integrazione"
V_LAV = IRI + "/vocab/lavorazione/gradina"
#: a confirmed point farther than this from the truth is placed again (m)
TOLERANCE = 0.0005
HEADS = [
    {"id": "canonica", "variant": "canonica", "yaw": 0, "shift": "0,0,0"},
    {"id": "girata", "variant": "canonica", "yaw": 35, "shift": "0.4,0.1,-0.2"},
    {"id": "fuori-misura", "variant": "fuori-misura", "yaw": -20, "shift": "0,0,0"},
]
QUALIA = {"larghezza": "stat:larghezza_biorbitale", "altezza": "stat:altezza_facciale",
          "indice": "stat:indice_facciale"}


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def machine_env(folder: Path) -> Dict[str, str]:
    env = dict(os.environ)
    for var, sub in (("EM_VOCABULARIES_DIR", "vocabularies"), ("S3DGRAPHY_PROFILES_DIR", "profiles"),
                     ("S3DGRAPHY_EXTENSIONS_DIR", "extensions"), ("S3DGRAPHY_PLUGINS_DIR", "plugins"),
                     ("S3DGRAPHY_PLUGINS_DATA_DIR", "plugins-data")):
        env[var] = str(folder / sub)
    env.pop("S3DGRAPHY_PLUGINS_DEV_DIR", None)
    return env


# ── the truth's own arithmetic (the conventions of SPEC §5.4) ───────────────

def truth_values(t: Dict[str, Any]) -> Dict[str, float]:
    p = t["points"]
    w = math.dist(p["exocanthion_r"], p["exocanthion_l"])
    h = math.dist(p["nasion"], p["gnathion"])
    return {"larghezza": w, "altezza": h, "indice": h / w, "area": polygon_area(t["infill_polygon"])}


def polygon_area(poly: List[List[float]]) -> float:
    sx = sy = sz = 0.0
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        sx += a[1] * b[2] - a[2] * b[1]
        sy += a[2] * b[0] - a[0] * b[2]
        sz += a[0] * b[1] - a[1] * b[0]
    return 0.5 * math.sqrt(sx * sx + sy * sy + sz * sz)


def _num(v: Any) -> Optional[float]:
    try:
        return float(str(v).split()[0].replace(",", "."))
    except (TypeError, ValueError, IndexError):
        return None


# ── the installation, form by form (in the child process) ───────────────────

# the commit before the pilot (MICRO-PL20, a53b9ee): there the mixed package still
# carries the stub of its code, the «before» of the update. HEAD was right only
# while the pilot's own change was uncommitted.
OLD_REF = "3cf61af"


def _git_archive_folder(rel: str, dest: Path) -> Path:
    """The folder ``rel`` as it is at OLD_REF (the stub of before), unpacked in ``dest``."""
    raw = subprocess.run(["git", "-C", str(REPO), "archive", OLD_REF, rel], check=True,
                         capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        tar.extractall(dest)
    return dest / rel


def install_separata(work: Path, heads_dir: Path) -> Dict[str, Any]:
    from s3dgraphy import extensions as X
    from s3dgraphy.em import plugins as PL
    out: Dict[str, Any] = {"form": "separata"}
    zips = work / "zips"
    t0 = time.perf_counter()
    bd = X.build(EX / "esempio-statuaria", output_dir=zips)
    bc = X.build(EX / "facemesh_fit", output_dir=zips)
    out["build"] = {"ms": _ms(t0), "data": {"file": bd["file"], "size": bd["size"], "ok": bd["ok"]},
                    "code": {"file": bc["file"], "size": bc["size"], "ok": bc["ok"]}}
    pv = X.preview(bc["path"])
    out["preview_code"] = {"trust_needed": (pv.get("code") or {}).get("trust_needed"),
                           "permissions": (pv.get("code") or {}).get("permissions"),
                           "capabilities": (pv.get("code") or {}).get("capabilities"),
                           "requires": [m.get("it") for m in (pv.get("requires") or {}).get("missing") or []]}
    t0 = time.perf_counter()
    r = X.install(bc["path"], trust=True)
    out["install_code_first"] = {"ms": _ms(t0), "state": _state(r)}
    plugs = PL.sync("emstudio")
    out["sync_without_data"] = [p.as_dict()["state"] for p in plugs]
    # the plugin's command on a head, the data still missing: the contract does not invent
    out["command_without_data"] = run_head(HEADS[0], heads_dir, work)
    t0 = time.perf_counter()
    r = X.install(bd["path"])
    out["install_data"] = {"ms": _ms(t0), "state": _state(r)}
    out["installed"] = [{"id": e.get("id"), "version": e.get("version"), "kind": e.get("kind")} for e in X.installed()]
    return out


def install_mista(work: Path, heads_dir: Path) -> Dict[str, Any]:
    from s3dgraphy import extensions as X
    from s3dgraphy.em import plugins as PL
    out: Dict[str, Any] = {"form": "mista"}
    zips = work / "zips"
    old = _git_archive_folder("examples/esempio-statuaria-misto", work / "head")
    t0 = time.perf_counter()
    b_old = X.build(old, output_dir=zips / "old")
    b_new = X.build(EX / "esempio-statuaria-misto", output_dir=zips)
    out["build"] = {"ms": _ms(t0), "old": {"file": b_old["file"], "size": b_old["size"]},
                    "new": {"file": b_new["file"], "size": b_new["size"]}}
    t0 = time.perf_counter()
    r = X.install(b_old["path"], trust=True)
    out["install_old"] = {"ms": _ms(t0), "state": _state(r)}
    plugs = PL.sync("emstudio")
    p = plugs[0] if plugs else None
    out["old_loaded"] = p.as_dict()["state"] if p else None
    # the old stub on an open head: since the em API (MICRO-PL14) a command needs
    # a graph open before anything else, so the stub's own answer comes only then
    from s3dgraphy import em
    from s3dgraphy.em.host import ScriptHost
    h = ScriptHost(author=ORCID, language="it")
    em.host.install(h)
    h.open(str(heads_dir / f"testa-{HEADS[0]['id']}.em.json"))
    res = PL.invoke(p.id, "facemesh.propose", {"model": "rm1"}, author=ORCID) if p else None
    em.host.uninstall()
    out["old_command"] = (res.data.get("messages") or {"en": res.message}) if res is not None else None
    pv = X.preview(b_new["path"])
    code = pv.get("code") or {}
    out["preview_update"] = {"trust_needed": code.get("trust_needed"), "trust_changes": code.get("trust_changes"),
                             "code_updated": code.get("updated"), "data": _short(pv.get("data"))}
    t0 = time.perf_counter()
    r = X.update(b_new["path"], trust=True)
    out["update"] = {"ms": _ms(t0), "state": _state(r)}
    plugs = PL.sync("emstudio")
    out["after_update_same_process"] = [{"state": q.state, "problems": [x.get("it") for x in q.problems]} for q in plugs]
    out["installed"] = [{"id": e.get("id"), "version": e.get("version"), "kind": e.get("kind")} for e in X.installed()]
    return out


def _short(d: Any) -> Any:
    if not isinstance(d, dict):
        return d
    return {k: d[k] for k in ("version", "state", "updated", "unchanged", "versions") if k in d}


def _state(row: Dict[str, Any]) -> Dict[str, Any]:
    keep = {}
    for part in ("data", "code"):
        sec = row.get(part) or {}
        keep[part] = {k: sec.get(k) for k in ("state", "version", "why", "reason") if sec.get(k) is not None}
    keep["version"] = row.get("version")
    for k in ("incomplete", "warnings", "changes"):
        if row.get(k):
            keep[k] = row[k] if k != "warnings" else [w.get("it") if isinstance(w, dict) else w for w in row[k]]
    return keep


# ── one head, in the child process ──────────────────────────────────────────

def run_head(head: Dict[str, Any], hdir: Path, out_dir: Path) -> Dict[str, Any]:
    from s3dgraphy import em
    from s3dgraphy.annotation.extractors import landmark_pose_status, place_landmark
    from s3dgraphy.contract.connector import VOLATILE_KEY
    from s3dgraphy.em import plugins as PL
    from s3dgraphy.em.host import ScriptHost

    name = f"testa-{head['id']}"
    truth = json.loads((hdir / f"{name}.truth.json").read_text(encoding="utf-8"))
    tv = truth_values(truth)
    rec: Dict[str, Any] = {"head": head["id"], "truth": {k: round(v, 6) for k, v in tv.items()}, "ms": {}}

    h = ScriptHost(author=ORCID, language="it")
    em.host.install(h)
    t0 = time.perf_counter()
    h.open(str(hdir / f"{name}.em.json"))
    rec["ms"]["open"] = _ms(t0)
    g = h.graph()
    on = "d1"
    rec["overlay_has_set"] = bool(h.overlay().landmark_set(SET))

    PL.sync("emstudio")
    t0 = time.perf_counter()
    res = PL.invoke("facemesh_fit" if PL.get("facemesh_fit") else "esempio-statuaria", "facemesh.propose",
                    {"model": "rm1"}, author=ORCID)
    rec["ms"]["propose"] = _ms(t0)
    if not res.ok:
        rec["propose_refused"] = res.data.get("messages") or {"en": res.message}
        rec["propose_reason"] = res.data.get("reason")
        em.host.uninstall()
        return rec
    val = res.data.get("value") or {}
    vol = [n for n in g.nodes if VOLATILE_KEY in (getattr(n, "data", None) or {})]
    rec["proposals"] = {"count": len(val.get("proposals") or []), "volatile_nodes": len(vol),
                        "by": val.get("by"), "unit_m": round(val.get("unit_m") or 0, 6),
                        "graph_steps": len(h.steps)}
    errs = {}
    for row in val.get("proposals") or []:
        errs[row["point"]] = {"method": row["method"], "label": row["label"],
                              "err_mm": round(1000 * math.dist(row["position"], truth["points"][row["point"]]), 2)}
    rec["proposal_errors"] = errs
    # em.save with the proposals still open: what reaches the file (an editor
    # drops volatile nodes on save — DocumentStore.toJSON, contract.document_view)
    open_copy = out_dir / f"{name}.proposte-aperte.em.json"
    h.save(str(open_copy))
    raw_open = json.loads(open_copy.read_text(encoding="utf-8"))
    gr = raw_open["graphs"][raw_open.get("active_graph_id") or next(iter(raw_open["graphs"]))]
    rec["save_with_proposals_open"] = {"volatile_nodes_in_file": sum(1 for n in gr["nodes"]
                                                                     if "aux_volatile" in (n.get("data") or {}))}

    # the person confirms every proposal. Two acts: em cannot BAKE a proposal
    # (the volatile mark is the seam's, a diff never carries it), and a point
    # placed where a proposal's point is finds that region (the core keys a
    # region by its place) and would keep its mark — and an editor drops volatile
    # nodes on save. So: the proposals go (rejected as proposals), then the
    # person's points are placed, new, hers, with ``proposed_by`` naming the plugin
    t0 = time.perf_counter()
    with em.write("Proposte dei punti del volto: tolte per la posa") as tx:
        for row in val["proposals"]:
            tx.remove(row["proposal"])
            if row.get("region"):
                tx.remove(row["region"])
        for nid in [n.node_id for n in tx.graph.nodes if "facemesh_proposal" in (getattr(n, "data", None) or {})]:
            tx.remove(nid)
    with em.write("Posa dei punti del volto: proposte confermate") as tx:
        pose = tx.start_pose(SET, on, subject="us1", combiner_type=None)
        for row in val["proposals"]:
            placed = place_landmark(tx.graph, tx.overlay, SET, row["point"], on, row["position"], pose_id=pose,
                                    subject="us1", label=row["label"], lang="it", author=ORCID)
            tx.update(placed.extractor_id, "data.proposed_by",
                      {"plugin": "facemesh_fit", "by": val["by"], "method": row["method"],
                       "proposal": row["proposal"], "accepted": "as proposed"})
        computed = tx.compute_available(on, subject="us1")
    rec["ms"]["confirm_and_compute"] = _ms(t0)
    rec["computed"] = _computed(computed)
    st = landmark_pose_status(g, h.overlay(), SET, on, subject="us1")
    rec["pose_complete"] = st["complete"]
    rec["volatile_left"] = len([n for n in g.nodes if VOLATILE_KEY in (getattr(n, "data", None) or {})])
    rec["values_as_proposed"] = _values(g)

    # the points farther than the tolerance: placed again where they are
    by = val["by"]
    head_id = (val["proposals"][0]["proposal"].rsplit(":", 1)[0]) if val.get("proposals") else ""
    far = [k for k, e in errs.items() if e["err_mm"] > TOLERANCE * 1000]
    t0 = time.perf_counter()
    recomputed: List[Any] = []
    with em.write("Posa dei punti del volto: punti corretti") as tx:
        for pid in far:
            placed = place_landmark(tx.graph, tx.overlay, SET, pid, on, truth["points"][pid], pose_id=st["pose_id"],
                                    subject="us1", label=errs[pid]["label"], lang="it", author=ORCID)
            # data.<key> is ONE key (set_field): the whole record, with how it ended
            tx.update(placed.extractor_id, "data.proposed_by",
                      {"plugin": "facemesh_fit", "by": by, "method": errs[pid]["method"],
                       "proposal": f"{head_id}:{pid}", "accepted": "moved by the person",
                       "moved_mm": errs[pid]["err_mm"]})
            for r in placed.recomputed or []:
                node = tx.graph.find_node_by_id(r.get("combiner_id"))
                recomputed.append(((getattr(node, "data", None) or {}).get("combiner") or {}).get("produces")
                                  or getattr(node, "name", None) or r.get("combiner_id"))
    rec["ms"]["correct"] = _ms(t0)
    rec["corrected"] = far
    rec["recomputed_on_move"] = sorted({str(x) for x in recomputed})
    rec["values_after_correction"] = _values(g)

    # the infill: a surface of the package, its area as a value with its chain; the terms
    t0 = time.perf_counter()
    with em.write("Integrazione di restauro sulla punta del naso") as tx:
        ext = tx.add_extractor("stat:superficie_integrata", on=on, vertices=truth["infill_polygon"],
                               name="D.01.07")
        meas = tx.graph.find_node_by_id(ext)
        from s3dgraphy.annotation.reading import measure
        region = next(e.edge_target for e in tx.graph.edges if e.edge_source == ext and e.edge_type == "extracted_from")
        m = measure(tx.graph, region)
        pid = tx.set_property("us1", "stat:area_integrazione", value=f"{m['area']:.4g}")
        tx.update(pid, "data.unit", "m2")
        tx.add_edge(pid, "has_data_provenance", ext)
        tx.set_property("us1", "stat:fase_di_superficie", concept=V_FASE, lang="it")
        tx.set_property("us1", "stat:lavorazione", concept=V_LAV, lang="it")
    rec["ms"]["infill_and_terms"] = _ms(t0)
    rec["infill"] = {"area_m2": round(m["area"], 8), "truth_m2": round(tv["area"], 8),
                     "perimeter_m": round(m.get("perimeter") or 0, 6), "value_text": m.get("value"),
                     "extractor_name": getattr(meas, "name", None)}

    # every value against the truth
    final = _values(g)
    rec["values_final"] = final
    rec["deviation_as_proposed"] = {k: _dev(rec["values_as_proposed"].get(k), tv[k]) for k in QUALIA}
    rec["deviation_final"] = {k: _dev(final.get(k), tv[k]) for k in list(QUALIA) + ["area"]}

    # saved, read back
    saved = out_dir / f"{name}.posata.em.json"
    t0 = time.perf_counter()
    h.save(str(saved))
    rec["ms"]["save"] = _ms(t0)
    raw = json.loads(saved.read_text(encoding="utf-8"))
    rec["saved"] = _saved_checks(raw)
    h2 = ScriptHost(author=ORCID, language="it")
    em.host.install(h2)
    h2.open(str(saved))
    st2 = landmark_pose_status(h2.graph(), h2.overlay(), SET, on, subject="us1")
    rec["reread"] = {"pose_complete": st2["complete"], "values": _values(h2.graph()),
                     "same_values": _values(h2.graph()) == final}

    # the sheet of the package, filled from the graph, IT and EN
    t0 = time.perf_counter()
    rec["sheet"] = sheet(h2.graph(), out_dir, name)
    rec["ms"]["sheet"] = _ms(t0)
    em.host.uninstall()
    return rec


def _dev(v: Optional[float], t: float) -> Optional[Dict[str, float]]:
    if v is None:
        return None
    return {"value": round(v, 6), "truth": round(t, 6), "abs": round(v - t, 6),
            "rel_pct": round(100 * (v - t) / t, 3) if t else None}


def _computed(out: Dict[str, Any]) -> Dict[str, Any]:
    return {"computed": [{k: r.get(k) for k in ("combiner_type", "operation", "value", "unit", "text", "created")}
                         for r in out.get("computed") or []],
            "missing": out.get("missing") or {}, "errors": out.get("errors") or {}}


def _values(g: Any) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    want = dict(QUALIA, area="stat:area_integrazione")
    for p in g.get_property_nodes_for_node("us1"):
        nm = getattr(p, "name", None)
        for k, q in want.items():
            if nm == q:
                out[k] = _num(getattr(p, "value", None) if getattr(p, "value", None) not in (None, "") else p.description)
    return out


def _saved_checks(raw: Dict[str, Any]) -> Dict[str, Any]:
    gr = raw["graphs"][raw.get("active_graph_id") or next(iter(raw["graphs"]))]
    nodes = gr["nodes"]
    lms = [n for n in nodes if (n.get("data") or {}).get("landmark")]
    return {"profiles": raw["header"].get("profiles"),
            "nodes": len(nodes), "edges": len(gr["edges"]),
            "volatile_nodes": sum(1 for n in nodes if "aux_volatile" in (n.get("data") or {})),
            "proposal_nodes": sum(1 for n in nodes if "proposal" in (n.get("data") or {})
                                  or "facemesh_proposal" in (n.get("data") or {})),
            "landmarks": len(lms),
            "landmarks_with_author": sum(1 for n in lms if (n.get("data") or {}).get("created_by") == ORCID
                                         or (n.get("data") or {}).get("author") == ORCID),
            "landmarks_proposed_by_plugin": sum(1 for n in lms if ((n.get("data") or {}).get("proposed_by") or {}).get("plugin") == "facemesh_fit"),
            "landmarks_moved_by_person": sum(1 for n in lms if ((n.get("data") or {}).get("proposed_by") or {}).get("accepted") == "moved by the person")}


# ── the sheet ────────────────────────────────────────────────────────────────

def _templates():
    try:
        import stratigraph_templates  # noqa: F401
    except ImportError:
        src = os.environ.get("STRATIGRAPH_TEMPLATES_SRC") or str(REPO.parent / "stratigraph-templates" / "src")
        sys.path.insert(0, src)
    from stratigraph_templates import loader, model, render
    return loader, model, render


def sheet(g: Any, out_dir: Path, name: str) -> Dict[str, Any]:
    """The record of US1 for the package's sheet, read from the graph by the
    bindings of the compiled definition (identity, description, qualia; a
    term as its concept and label), then drawn."""
    from s3dgraphy.profiles import find
    loader, model, render = _templates()
    prof = find("esempio-statuaria", "0.1.0")
    form = next(f for f in prof.manifest["forms"] if f["id"] == "stat-scheda-superficie")
    compiled = json.loads((Path(prof.root) / form["compiled"]).read_text(encoding="utf-8"))
    t = loader.template_from_compiled(compiled)
    unit = g.find_node_by_id("us1")
    props = {getattr(p, "name", None): p for p in g.get_property_nodes_for_node("us1")}
    values: Dict[str, Any] = {}
    # the bindings are in the compiled recipe (the loader does not read them back)
    for fid, b in (compiled.get("recipe") or {}).get("fields", {}).items():
        q = ((b.get("property") or {}).get("property_type"))
        if b.get("verdict") == "identity":
            values[fid] = unit.name.replace("US", "").strip() or unit.name
        elif any((st.get("emit") or {}).get("field") == "description" for st in b.get("steps") or []):
            values[fid] = unit.description
        elif q and q in props:
            p = props[q]
            term = (getattr(p, "data", None) or {}).get("concept")
            values[fid] = ({"concept": term.get("concept"), "label": term.get("label")}
                           if isinstance(term, dict) else (getattr(p, "value", None) or p.description))
    record = model.Record(template=t.id, template_version=t.version, values=values)
    out: Dict[str, Any] = {"template": f"{t.id} {t.version}", "values": values, "files": {}}
    for lang in ("it", "en"):
        html = render.sheet_html(t, record, lang=lang, mode="print")
        path = out_dir / f"{name}.scheda.{lang}.html"
        path.write_text(html, encoding="utf-8")
        out["files"][lang] = {"file": path.name, "bytes": len(html.encode("utf-8")),
                              "has_width": f"{_num(values.get('larghezza')):.4f}"[:5] in html if values.get("larghezza") else False}
    return out


# ── the two processes and the summary ───────────────────────────────────────

def child(form: str, out_dir: Path, heads_dir: Path, *, step: str) -> Dict[str, Any]:
    work = out_dir / f"work-{form}"
    work.mkdir(parents=True, exist_ok=True)
    if step == "install":
        return install_separata(work, heads_dir) if form == "separata" else install_mista(work, heads_dir)
    res: Dict[str, Any] = {"form": form, "heads": []}
    hout = out_dir / form
    hout.mkdir(parents=True, exist_ok=True)
    for head in HEADS:
        res["heads"].append(run_head(head, heads_dir, hout))
    return res


def _run_child(form: str, step: str, out_dir: Path, heads_dir: Path) -> Dict[str, Any]:
    env = machine_env(out_dir / f"machine-{form}")
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, __file__, "--child", form, "--step", step, "--heads", str(heads_dir),
                        str(out_dir)], env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"{form}/{step} failed:\n{p.stdout}\n{p.stderr}")
    doc = json.loads(p.stdout.strip().splitlines()[-1])
    doc["process_ms"] = _ms(t0)
    return doc


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="the statuary pilot (synthetic, D-5)")
    ap.add_argument("out")
    ap.add_argument("--child")
    ap.add_argument("--step", default="heads")
    ap.add_argument("--heads")
    a = ap.parse_args(argv)
    out_dir = Path(a.out).resolve()
    if not a.child and out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir}: not empty — the machine folders of a pilot are made new each time")
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.child:
        res = child(a.child, out_dir, Path(a.heads), step=a.step)
        print(json.dumps(res, ensure_ascii=False, default=str))
        return 0

    heads_dir = out_dir / "heads"
    heads_dir.mkdir(exist_ok=True)
    made = {}
    sys.path.insert(0, str(HERE))
    import make_head
    for head in HEADS:
        t0 = time.perf_counter()
        doc = make_head.main([str(heads_dir), "--name", f"testa-{head['id']}", "--variant", head["variant"],
                              "--yaw", str(head["yaw"]), "--shift", head["shift"]])
        made[head["id"]] = {"ms": _ms(t0), "vertices": doc["generator"]["vertices"],
                            "triangles": doc["generator"]["triangles"], "digest": doc["model_digest"],
                            "bytes": (heads_dir / f"testa-{head['id']}.glb").stat().st_size}
    summary: Dict[str, Any] = {"pilot": "MICRO-PL20 · statuaria sintetica (D-5)", "orcid": ORCID,
                               "tolerance_mm": TOLERANCE * 1000, "heads": made, "forms": {}}
    sep = {"install": _run_child("separata", "install", out_dir, heads_dir)}
    summary["forms"]["separata"] = sep
    mix = {"install": _run_child("mista", "install", out_dir, heads_dir)}
    mix["heads"] = _run_child("mista", "heads", out_dir, heads_dir)
    summary["forms"]["mista"] = mix
    sep["heads"] = _run_child("separata", "heads", out_dir, heads_dir)
    # the two forms give the same numbers
    same = []
    for hs, hm in zip(sep["heads"]["heads"], mix["heads"]["heads"]):
        same.append({"head": hs["head"], "same_proposals": hs.get("proposal_errors") == hm.get("proposal_errors"),
                     "same_values": hs.get("values_final") == hm.get("values_final")})
    summary["forms_agree"] = same
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n",
                                          encoding="utf-8")
    print(json.dumps(same))
    return 0


if __name__ == "__main__":
    sys.exit(main())
