"""MICRO-GEO08 · row G7 of the geophysics plan: the stack in the graph (``geofisica.ingest``).

What is defended: the plugin's command, run through ``em.plugins.invoke`` on a
graph held by a ``ScriptHost`` (the command line host), writes ONE act — the
acquisition (``local_import``, method, quantity, the stack's georef as doubles),
a resource per source file (its id the stamps' ``res:<uuid5 of the digest>``),
a document per slice or section (D.nn, ``geof:fetta``/``geof:sezione``, role
analytical, content_nature 2d_object, geometry from the source of the
position, ``geo_id``, ``geo``), the rasterization's process naming the plugin;
importing again adds nothing; a file renamed is the same document and the same
resource; a file whose bytes changed is a new resource and the old one leaves;
the graph's georeference is proposed, never written; the em.json saved reads
back and validates; a PNG's stamp absorbed joins acquisition → resource →
derivative. On the real data when it is here (skipped otherwise): the
Basilica Iulia's 12 ``.ASC`` (observable, no EPSG) and UA Ilici's Sector 1
(reality_based, EPSG:25830).
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("s3dgraphy.em.plugins")

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "profiles" / "geofisica"
CODE = PKG / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
core = importlib.import_module("geofisica_core")
_gt = importlib.import_module("geofisica_core.readers._geotiff")

ONEDRIVE = Path.home() / "Library" / "CloudStorage" / "OneDrive-CNR" / "0_RACCOLTA_CNR"
BASILICA = (ONEDRIVE / "Basilica Iuilia General" / "03_Documentation" / "05_Geophysical_survey"
            / "file-ascci-ert-fori-imperiali" / "sezioni-2D")
ILICI_S1 = (ONEDRIVE / "StratiGraph-grp - Documenti" / "WP 03 - Data Model and Knowledge Graph"
            / "WP 03 - Material" / "UA_Ilici_Augusta" / "GEORRADAR" / "Sector 1")

AUTHOR = "https://orcid.org/0000-0002-0000-0001"
AT = "2026-11-19T12:00:00Z"
NS = "https://w3id.org/extendedmatrix/profile/geofisica/vocab/"
ERT_SCALE = {"from": [1, 255], "to": [0, 3500], "unit": "ohm.m",
             "source": "figure colour bar, risultati-fori.pdf p. 5", "confidence": "low"}
#: the Basilica's sections, length × depth in m (risultati-fori.pdf, as row G5 measured)
SECTIONS = {"VERT1": [92.0, 8.0], "VERT2": [92.0, 8.0], "VERT3": [92.0, 8.0],
            "VERT4": [50.0, 8.0], "VERT5": [50.0, 8.0], "VERT6": [50.0, 8.0]}
BASILICA_DECLARED = {"extent": [92.0, 50.0], "sections": SECTIONS}


@pytest.fixture
def session(tmp_path, monkeypatch):
    """A clean machine, the package as the development folder, a graph on a
    ScriptHost; yields a function that runs the command."""
    for var, sub in (("S3DGRAPHY_EXTENSIONS_DIR", "extensions"), ("S3DGRAPHY_PROFILES_DIR", "profiles"),
                     ("S3DGRAPHY_PLUGINS_DIR", "plugins"), ("S3DGRAPHY_PLUGINS_DATA_DIR", "plugins-data"),
                     ("S3DGRAPHY_AUTHORITIES_DIR", "authorities")):
        monkeypatch.setenv(var, str(tmp_path / "machine" / sub))
    monkeypatch.setenv("S3DGRAPHY_PLUGINS_DEV_DIR", str(PKG))
    from s3dgraphy.em import host as H
    from s3dgraphy.em import plugins as PL
    from s3dgraphy.graph import Graph
    PL.reset()
    got = [p for p in PL.sync("emstudio", dev=True) if p.id == "geofisica"]
    assert got and got[0].state == "loaded", got and got[0].problems
    host = H.ScriptHost(Graph(graph_id="geo"), author=AUTHOR)
    previous = H.install(host)

    def run(**slots):
        slots.setdefault("at", AT)
        for k in ("declared", "georef", "value_scale", "value_range"):
            if isinstance(slots.get(k), (dict, list)):
                slots[k] = json.dumps(slots[k])
        res = PL.invoke("geofisica", "geofisica.ingest", slots, author=AUTHOR)
        return res
    run.host = host
    try:
        yield run
    finally:
        PL.reset()
        H.uninstall()
        if previous is not None and not isinstance(previous, H.ScriptHost):
            H.install(previous)


def _matrix_stack(folder):
    """Like the Basilica's: two slices (cm in the name, 0 = nodata) and a section."""
    folder.mkdir(parents=True)
    rows_a = [[0 if (i == 0 and j < 2) else 1 + (i * 7 + j) * 6 for j in range(7)] for i in range(5)]
    rows_b = [[0 if j == 5 else 255 - (i * 6 + j) * 5 for j in range(6)] for i in range(4)]
    sec = [[0 if j == 0 else 10 * (j + i) for j in range(4)] for i in range(9)]
    for name, rows in (("100-150cm.ASC", rows_a), ("250-300cm.ASC", rows_b), ("VERT-1-OK.ASC", sec)):
        (folder / name).write_text("\n".join(" ".join(str(v) for v in r) for r in rows) + "\n")
    return folder


def _geotiff_stack(folder, e0=701756.963, n0=4234861.282, step=0.1):
    folder.mkdir(parents=True)
    for name, k in (("mean_v2.tif", 1.0), ("sqmean_v2.tif", 1000.0)):
        rows = [[-3.4028234663852886e38 if (i + j) % 5 == 0 else k * (i + j) for j in range(8)]
                for i in range(6)]
        _gt.write_geotiff(str(folder / name), rows, affine=(e0, step, 0.0, n0, 0.0, -step),
                          epsg=25830, nodata=-3.4028234663852886e38)
    return folder


def _nodes(graph, node_type, em_kind=None):
    return [n for n in graph.nodes if n.node_type == node_type
            and (em_kind is None or (n.data or {}).get("em_kind") == em_kind)]


def _edges(graph, edge_type):
    return {(e.edge_source, e.edge_target) for e in graph.edges if e.edge_type == edge_type}


def _value(res):
    assert res.ok, res.message + json.dumps(res.data.get("messages"), ensure_ascii=False)
    return res.data["value"]


def test_a_matrix_stack_enters_as_one_act(tmp_path, session):
    folder = _matrix_stack(tmp_path / "basilica-like")
    out = _value(session(folder=str(folder), method="ert", value_scale=ERT_SCALE,
                         declared={"extent": [92, 50], "section": {"length": 9.0, "depth": 2.0}}))
    g = session.host.graph()
    assert out["written"] and len(session.host.steps) == 1               # one act, one step
    step = session.host.steps[0]
    assert step["author"] == AUTHOR and "ERT" in step["label"]
    acq = _nodes(g, "dtc_acquisition", "geof:pila")
    assert len(acq) == 1 and acq[0].node_id == out["acquisition"]
    a = acq[0].data
    assert a["dtc_kind"] == "local_import" and a["method"] == NS + "metodi/ert"
    assert a["quantity"] == NS + "grandezze/resistivita" and a["unit"] == "ohm.m"
    assert a["value_scale"]["confidence"] == "low" and "epsg" not in a
    assert a["geo_stack_id"] == "basilica-like" and a["georef_source"] == "declared sizes"
    docs = sorted(_nodes(g, "document"), key=lambda n: n.name)
    assert [d.name for d in docs] == ["D.01", "D.02", "D.03"]
    kinds = sorted(d.data["em_kind"] for d in docs)
    assert kinds == ["geof:fetta", "geof:fetta", "geof:sezione"]
    for d in docs:
        assert (d.data["role"], d.data["content_nature"], d.data["geometry"]) == \
            ("analytical", "2d_object", "observable")
        geo = d.data["geo"]
        assert geo["cache_key"] == out["cache_key"] and geo["raster"].endswith(".png")
        assert (Path(out["cache_dir"]) / geo["raster"]).is_file()
    ids = {d.data["geo_id"] for d in docs}
    assert ids == {"ert:basilica-like#d1.000-1.500m", "ert:basilica-like#d2.500-3.000m",
                   "ert:basilica-like#sVERT1"}
    sec = next(d for d in docs if d.data["em_kind"] == "geof:sezione")
    assert sec.data["geo"]["orientation"] == "vertical" and sec.data["geo"]["line"] == "VERT1"
    assert "VERT1" in sec.description
    res = _nodes(g, "resource")
    assert len(res) == 3
    for r in res:
        assert r.node_id == core.resource_id_for(r.data["checksum"])     # the stamps' id
    assert _edges(g, "dtc_had_output") == {(out["acquisition"], r.node_id) for r in res}
    assert len(_edges(g, "has_linked_resource")) == 3
    proc = _nodes(g, "dtc_process")
    assert len(proc) == 1 and proc[0].data["dtc_kind"] == "format_conversion"
    assert proc[0].data["software"][0]["id"] == "geofisica"
    assert proc[0].data["software"][1]["name"] == "geofisica_core"
    assert _edges(g, "dtc_had_input") == {(proc[0].node_id, out["acquisition"])}
    # the data of the act name the plugin (the seam's injector), and the author is the host's
    assert all(n.data.get("created_by") for n in docs)
    assert "georef_proposal" not in out["advice"] and out["advice"]["stack_epsg"] is None
    # every PNG stamped, citing the graph's resource and acquisition by identity
    for d in out["documents"]:
        st = json.loads(Path(d["stamp"]).read_text())
        cited = {f["resource_id"] for f in st["from"]}
        assert {d["resource"], out["acquisition"]} <= cited
        assert st["how"]["software"][0]["id"] == "geofisica"


def test_importing_again_adds_nothing_and_a_rename_is_the_same_document(tmp_path, session):
    folder = _matrix_stack(tmp_path / "pila")
    first = _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED))
    g = session.host.graph()
    before = ({n.node_id for n in g.nodes}, {e.edge_id for e in g.edges})
    again = _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED))
    assert not again["written"] and again["added"] == [] and again["reused"]
    assert ({n.node_id for n in g.nodes}, {e.edge_id for e in g.edges}) == before
    # renamed: the same depth band, the same bytes
    (folder / "100-150cm.ASC").rename(folder / "fetta_100-150cm.ASC")
    renamed = _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED))
    assert renamed["added"] == [] and {d["id"] for d in renamed["documents"]} == \
        {d["id"] for d in first["documents"]}
    rid = next(d["resource"] for d in renamed["documents"] if d["geo_id"].endswith("#d1.000-1.500m"))
    r = g.find_node_by_id(rid)
    assert r.name == "fetta_100-150cm.ASC" and r.data["url"].endswith("fetta_100-150cm.ASC")
    assert {n.node_id for n in g.nodes} == before[0]
    # the bytes changed: a new resource, the same document, the old resource gone
    (folder / "250-300cm.ASC").write_text("1 2 3\n4 5 6\n")
    changed = _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED))
    doc = next(d for d in changed["documents"] if d["geo_id"].endswith("#d2.500-3.000m"))
    old = next(d for d in first["documents"] if d["geo_id"].endswith("#d2.500-3.000m"))
    assert doc["id"] == old["id"] and doc["resource"] != old["resource"]
    assert changed["removed"] == [old["resource"]] and g.find_node_by_id(old["resource"]) is None
    assert len(_nodes(g, "document")) == 3 and len(_nodes(g, "resource")) == 3
    assert len(_nodes(g, "dtc_acquisition")) == 1
    assert len(_nodes(g, "dtc_process")) == 2          # a second cache, a second rasterization
    assert sorted(d.name for d in _nodes(g, "document")) == ["D.01", "D.02", "D.03"]


def test_a_geotiff_stack_is_reality_based_and_the_georef_only_proposed(tmp_path, session):
    folder = _geotiff_stack(tmp_path / "Sector 1")
    out = _value(session(folder=str(folder), method="gpr"))
    g = session.host.graph()
    docs = _nodes(g, "document")
    assert {d.data["geo_id"] for d in docs} == {"gpr:Sector 1#mean_v2", "gpr:Sector 1#sqmean_v2"}
    assert all(d.data["geometry"] == "reality_based" for d in docs)
    a = _nodes(g, "dtc_acquisition")[0].data
    assert a["epsg"] == 25830 and isinstance(a["georef"]["origin_e"], float)
    assert abs(a["georef"]["origin_e"] - 701756.963) < 1e-3
    assert a["quantity"] == NS + "grandezze/ampiezza"
    adv = out["advice"]
    assert adv["graph"] == "undeclared"
    assert adv["georef_proposal"] == {"epsg": 25830, "shift_x": 701750.0, "shift_y": 4234860.0,
                                      "shift_z": 0.0}
    from s3dgraphy.api import georeference_state
    assert georeference_state(g) == "undeclared"                       # proposed, not written


def test_a_graph_in_another_crs_is_told(tmp_path, session):
    from s3dgraphy.api import declare_georeference
    declare_georeference(session.host.graph(), 32633, 291000.0, 4640000.0)
    out = _value(session(folder=str(_geotiff_stack(tmp_path / "S")), method="gpr"))
    other = out["advice"]["georef_other"]
    assert other["graph_epsg"] == 32633 and other["stack_epsg"] == 25830
    assert "EPSG:32633" in other["it"] and "EPSG:32633" in other["en"]
    assert "georef_proposal" not in out["advice"]


def test_a_declared_placement_names_its_source(tmp_path, session):
    folder = _matrix_stack(tmp_path / "m")
    place = {"origin_e": 291234.5678, "origin_n": 4640123.4321, "epsg": 32633, "rotation": 12.5,
             "source": "figure, risultati-fori.pdf p. 5"}
    out = _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED, georef=place))
    assert out["geometry"] == "observable" and out["georef_source"].startswith("figure")
    a = _nodes(session.host.graph(), "dtc_acquisition")[0].data
    assert a["georef"]["origin_e"] == 291234.5678 and a["epsg"] == 32633
    eye = _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED, name="a-occhio",
                         georef=dict(place, source="declared")))
    assert eye["geometry"] == "asserted"


def test_the_saved_document_reads_back_validates_and_absorbs_a_stamp(tmp_path, session):
    from s3dgraphy import api, em
    from s3dgraphy.container import load_container_file
    from s3dgraphy.stamp.absorb import absorb_stamp_file
    out = _value(session(folder=str(_matrix_stack(tmp_path / "pila")), method="ert",
                         declared=BASILICA_DECLARED))
    path = em.host.current().save(str(tmp_path / "geo.em.json"))
    container, warnings = load_container_file(path)
    g = container.active()
    v = api.validate(g)
    assert v["ok"] and not v["issues"], v
    assert len(_nodes(g, "document")) == 3 and len(_nodes(g, "dtc_acquisition")) == 1
    doc = next(n for n in _nodes(g, "document") if n.data["geo_id"].endswith("#d1.000-1.500m"))
    assert doc.data["geometry"] == "observable" and doc.data["geo"]["depth_top"] == 1.0
    # the stamp of the slice's PNG joins the graph's chain: acquisition → resource → derivative
    d = next(x for x in out["documents"] if x["id"] == doc.node_id)
    before = len(_nodes(g, "resource"))
    got = absorb_stamp_file(g, d["stamp"])
    assert got.applied and not got.disagreements
    png = got.resource_id
    assert (png, d["resource"]) in _edges(g, "dtc_derived_from")
    assert (out["acquisition"], d["resource"]) in _edges(g, "dtc_had_output")
    assert len(_nodes(g, "resource")) == before + 1                     # the PNG, no copy of the source
    acq = _nodes(g, "dtc_acquisition")
    assert len(acq) == 1 and acq[0].name == "ERT stack pila"           # merged, not doubled nor renamed
    src = g.find_node_by_id(d["resource"])
    assert src.name == "100-150cm.ASC" and src.data["url"].endswith("100-150cm.ASC")
    assert api.validate(g)["ok"]


def test_the_refusals_are_said_in_two_languages(tmp_path, session):
    """The command fails with the host's language (the whole pair reaching the
    page is row G9's, T-6 of PL20); the refusal itself carries EN and IT."""
    from geofisica import ingest as I
    res = session(folder=str(tmp_path / "nowhere"))
    assert not res.ok and "not a folder" in res.message
    with pytest.raises(I.Said) as e:
        I.ingest(str(tmp_path / "nowhere"))
    assert e.value.messages["it"].endswith("non è una cartella")
    (tmp_path / "empty").mkdir()
    with pytest.raises(I.Said) as e:
        I.ingest(str(tmp_path / "empty"))
    assert "nessuna fetta geofisica" in e.value.messages["it"]
    with pytest.raises(I.Said) as e:
        I.ingest(str(_matrix_stack(tmp_path / "x")), method="sonar")
    assert "metodo 'sonar'" in e.value.messages["it"]
    res = session(folder=str(tmp_path / "x"), method="sonar")
    assert not res.ok and not _nodes(session.host.graph(), "document")     # nothing written


def test_the_console_lists_the_stacks(tmp_path, session):
    from s3dgraphy import em
    _value(session(folder=str(_matrix_stack(tmp_path / "pila")), method="ert", declared=BASILICA_DECLARED))
    rows = em.ext.geofisica.stacks()
    assert len(rows) == 1 and rows[0]["method"] == "ert" and len(rows[0]["documents"]) == 3


@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia data is not here")
def test_real_basilica_twelve_documents(tmp_path, session):
    before = {p.name: p.stat().st_mtime for p in BASILICA.iterdir()}
    t0 = time.time()
    out = _value(session(folder=str(BASILICA), method="ert", value_scale=ERT_SCALE,
                         declared=BASILICA_DECLARED, name="basilica-iulia-ert"))
    t1 = time.time()
    g = session.host.graph()
    docs = _nodes(g, "document")
    assert len(docs) == 12 and all(d.data["geometry"] == "observable" for d in docs)
    assert sum(d.data["em_kind"] == "geof:sezione" for d in docs) == 6
    assert "epsg" not in _nodes(g, "dtc_acquisition")[0].data
    again = _value(session(folder=str(BASILICA), method="ert", value_scale=ERT_SCALE,
                           declared=BASILICA_DECLARED, name="basilica-iulia-ert"))
    t2 = time.time()
    assert again["added"] == [] and not again["written"]
    assert {p.name: p.stat().st_mtime for p in BASILICA.iterdir()} == before     # read only
    print("\nBASILICA ingest: %.2f s (cache %s), again %.2f s; %d nodes"
          % (t1 - t0, "reused" if out["reused"] else "built", t2 - t1, len(g.nodes)))


@pytest.mark.skipif(not ILICI_S1.is_dir(), reason="the UA Ilici data is not here")
def test_real_ilici_sector_1(tmp_path, session):
    t0 = time.time()
    out = _value(session(folder=str(ILICI_S1), method="gpr", name="ilici-sector-1"))
    t1 = time.time()
    g = session.host.graph()
    docs = _nodes(g, "document")
    assert len(docs) == 2 and all(d.data["geometry"] == "reality_based" for d in docs)
    assert out["advice"]["georef_proposal"]["epsg"] == 25830
    print("\nILICI Sector 1 ingest: %.2f s; proposal %s" % (t1 - t0, out["advice"]["georef_proposal"]))
