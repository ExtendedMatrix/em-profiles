"""«Porta dentro…» for a geophysical stack — row G8 of the geophysics plan (MICRO-GEO09).

What is defended:

* the package declares a reader of ``door.reader@2`` — a folder, ``.asc``
  and ``.xyz`` taken, the rasters, pictures and CSVs only CLAIMED (the host
  reads them too) — that opens the panel ``import``; the panel's value
  (``geofisica.describe``) only reads; its button is ``geofisica.ingest``;
* ``em.plugins.readers_for`` finds it for a folder and for a claimed file;
* the reader alone (a host without panels): the method the format suggests
  (matrices → ERT), a file reads its folder, the documents of row G7;
* the panel's plain fields (sizes, sections ``VERT1=92x8``, the scale
  ``1-255`` → ``0-3500``) become the declarations of row G7: importing from
  the panel after the door rewrites THE SAME documents (sizes now declared),
  and gives what the JSON slots give; wrong words refused in EN and IT;
* ``geofisica.describe`` says what a folder is from the names (format,
  slices, sections, depths, what is missing, what is already in the graph);
* on the real data where present: the Basilica Iulia (door, then panel with
  92 × 50 m and the sections) and UA Ilici Sector 1 (the door alone).
"""
from __future__ import annotations

import json

import pytest

from test_geofisica_ingest import (BASILICA, BASILICA_DECLARED, ERT_SCALE, ILICI_S1, _geotiff_stack,  # noqa: F401
                                   _matrix_stack, _nodes, _value, session)

AUTHOR = "https://orcid.org/0000-0002-0000-0001"


def _invoke(command, **slots):
    from s3dgraphy.em import plugins as PL
    slots.setdefault("at", "2026-11-19T12:00:00Z")
    return PL.invoke("geofisica", command, slots, author=AUTHOR)


def _docs(graph):
    return sorted((n.node_id, (n.data or {}).get("geo_id")) for n in _nodes(graph, "document"))


# ── the declaration ─────────────────────────────────────────────────────────

def test_the_reader_is_door_reader_2_with_its_panel(session, tmp_path):
    from s3dgraphy.em import plugins as PL
    c = PL.get("geofisica").commands
    r = c["geofisica.read"]
    assert r.where == ["door.reader@2"] and r.folders is True and r.writes is True
    assert r.accept == [".asc", ".xyz"]
    assert r.claims == [".csv", ".tif", ".tiff", ".jpg", ".jpeg", ".png"]
    assert r.panel == "geofisica/import" and r.path_slot == "folder"
    assert c["geofisica.describe"].writes is False and c["geofisica.describe"].where == []
    (panel,) = [p for p in PL.panels() if p.plugin == "geofisica"]
    kinds = {f.get("name") or f.get("command"): f["kind"] for f in panel.fields}
    assert kinds["folder"] == "text" and kinds["geofisica.describe"] == "value" and kinds["geofisica.ingest"] == "button"
    # every input of the panel is a slot of the command its button runs (the host fills by name)
    ingest_slots = {s["name"] for s in c["geofisica.ingest"].slots}
    assert {f["name"] for f in panel.fields if f.get("name")} <= ingest_slots
    assert all(f["label"].get("it") and f["label"].get("en") for f in panel.fields)
    # what «Porta dentro…» finds
    folder = _matrix_stack(tmp_path / "pila")
    assert [x.id for x in PL.readers_for(str(folder))] == ["geofisica.read"]
    assert [x.id for x in PL.readers_for(str(folder / "100-150cm.ASC"))] == ["geofisica.read"]
    assert PL.readers_for("/x/mean_v2.tif") == [] and PL.readers_for("/x/table.csv") == []
    assert [x.id for x in PL.readers_for("/x/mean_v2.tif", claimed=True)] == ["geofisica.read"]


# ── the reader alone ────────────────────────────────────────────────────────

def test_the_reader_alone_reads_the_folder_with_the_formats_method(session, tmp_path):
    folder = _matrix_stack(tmp_path / "basilica-like")
    out = _value(_invoke("geofisica.read", folder=str(folder / "250-300cm.ASC")))   # a file: its folder
    g = session.host.graph()
    (acq,) = _nodes(g, "dtc_acquisition", "geof:pila")
    assert acq.data["method"].endswith("/metodi/ert") and acq.data["geo_stack_id"] == "basilica-like"
    assert len(out["documents"]) == 3 and all(d["geo_id"].startswith("ert:") for d in out["documents"])
    assert any(w.get("code") == "extent_not_declared" for w in out["warnings"] if isinstance(w, dict)) \
        or any("extent" in json.dumps(w) for w in out["warnings"])
    assert len(session.host.steps) == 1
    # a method said wins
    gt = _geotiff_stack(tmp_path / "Sector 9")
    out = _value(_invoke("geofisica.read", folder=str(gt)))
    assert all(d["geo_id"].startswith("gpr:") for d in out["documents"])


def test_the_reader_refuses_in_two_languages(session, tmp_path):
    res = _invoke("geofisica.read", folder=str(tmp_path / "nowhere"))
    assert not res.ok and "not found" in res.message
    from geofisica.door import Said, panel_slots
    for bad in ({"extent_x": 92}, {"sections": "VERT1 92 8"}, {"scale_from": "1"}, {"scale_from": "1-255"},
                {"extent_x": "lots", "extent_y": 3}):
        with pytest.raises(Said) as e:
            panel_slots(bad)
        words = e.value.args[0] if e.value.args and isinstance(e.value.args[0], dict) else getattr(e.value, "messages", {})
        assert words.get("en") and words.get("it") and words["en"] != words["it"], bad


# ── the panel ───────────────────────────────────────────────────────────────

def test_panel_fields_become_the_declarations(session):
    from geofisica.door import panel_slots
    out = panel_slots({"folder": "/x", "extent_x": 92, "extent_y": "50", "sections": "VERT1=92x8, VERT4 = 50 × 8 m",
                       "section_depth": "8", "scale_from": "1-255", "scale_to": "0..3500", "scale_unit": "ohm.m",
                       "scale_source": "colour bar"})
    assert out["declared"] == {"extent": [92.0, 50.0], "sections": {"VERT1": [92.0, 8.0], "VERT4": [50.0, 8.0]},
                               "section": {"depth": 8.0}}
    assert out["value_scale"] == {"from": [1.0, 255.0], "to": [0.0, 3500.0], "unit": "ohm.m",
                                  "source": "colour bar", "confidence": "low"}
    assert not {"extent_x", "extent_y", "sections", "scale_from", "scale_to"} & set(out)
    # a field written wins over the JSON's same key; the rest of the JSON stays
    out = panel_slots({"declared": json.dumps({"extent": [1, 1], "transpose": True}), "extent_x": 3, "extent_y": 4})
    assert out["declared"] == {"extent": [3.0, 4.0], "transpose": True}
    assert panel_slots({"folder": "/x"}) == {"folder": "/x"}
    assert panel_slots({"scale_from": "-2;3", "scale_to": "0 1"})["value_scale"]["from"] == [-2.0, 3.0]


def test_the_door_then_the_panel_rewrites_the_same_documents(session, tmp_path):
    folder = _matrix_stack(tmp_path / "pila")
    door = _value(_invoke("geofisica.read", folder=str(folder)))
    g = session.host.graph()
    before = _docs(g)
    n_nodes = len(g.nodes)
    # the panel: the folder the door wrote, the sizes and the scale in plain words
    panel = _value(_invoke("geofisica.ingest", folder=str(folder), method="ert", extent_x=92, extent_y=50,
                           sections="VERT1=92x8", scale_from="1-255", scale_to="0-3500", scale_unit="ohm.m",
                           scale_source="figure colour bar"))
    assert _docs(g) == before and [d["id"] for d in panel["documents"]] == [d["id"] for d in door["documents"]]
    slice_ = next(n for n in _nodes(g, "document", "geof:fetta") if n.data["geo"]["depth_top"] == 1.0)
    assert slice_.data["geo"]["extent"] == pytest.approx([0.0, 0.0, 92.0, 50.0])     # 92 × 50 m declared
    (acq,) = _nodes(g, "dtc_acquisition", "geof:pila")
    assert acq.data["value_scale"]["to"] == [0.0, 3500.0] and acq.data["value_scale"]["confidence"] == "low"
    assert acq.data["georef_source"] == "declared sizes"
    # a file in the panel's field (a slice «read as» a stack) reads its folder
    again = _value(_invoke("geofisica.ingest", folder=str(folder / "100-150cm.ASC"), method="ert", extent_x=92,
                           extent_y=50, sections="VERT1=92x8", scale_from="1-255", scale_to="0-3500",
                           scale_unit="ohm.m", scale_source="figure colour bar"))
    assert again["cache_key"] == panel["cache_key"] and again["reused"] and len(session.host.steps) == 2  # nothing new: no step
    # a new rasterization (new parameters), the rest the same nodes
    assert len(g.nodes) == n_nodes + 1
    # the plain fields give what the JSON slots give (the cache key differs
    # only by 92 vs 92.0 in its parameters: the same documents, sizes, scale)
    other = _value(_invoke("geofisica.ingest", folder=str(folder), method="ert",
                           declared=json.dumps({"extent": [92, 50], "sections": {"VERT1": [92, 8]}}),
                           value_scale=json.dumps({"from": [1, 255], "to": [0, 3500], "unit": "ohm.m",
                                                   "source": "figure colour bar", "confidence": "low"})))
    assert [d["id"] for d in other["documents"]] == [d["id"] for d in panel["documents"]]
    assert slice_.data["geo"]["extent"] == pytest.approx([0.0, 0.0, 92.0, 50.0])
    (acq,) = _nodes(g, "dtc_acquisition", "geof:pila")
    assert acq.data["value_scale"]["from"] == [1, 255] and acq.data["value_scale"]["to"] == [0, 3500]


def test_describe_says_what_the_folder_is(session, tmp_path):
    from s3dgraphy.em import plugins as PL
    folder = _matrix_stack(tmp_path / "pila")

    def rows(**slots):
        (item,) = PL.compute([{"key": "k", "plugin": "geofisica", "command": "geofisica.describe",
                               "slot": "panel@1", "slots": slots}], lang="it")
        assert item["ok"], item
        return {r["label"]: r["value"] for r in item["value"]}

    r = rows(folder=str(folder))
    assert r["Formato"] == "matrici ASCII" and r["Fette"] == "2" and r["Sezioni"] == "VERT1"
    assert r["Profondità"] == "1.00–3.00 m" and r["Metodo"] == "ERT" and "estensione" in r["Manca"]
    assert "Nel grafo" not in r
    assert "Manca" not in rows(folder=str(folder), extent_x=92)
    _value(_invoke("geofisica.read", folder=str(folder)))
    assert rows(folder=str(folder))["Nel grafo"].startswith("3 documenti di pila")
    assert "ancora nessuna" in rows()["Cartella"]
    assert "non trovata" in rows(folder=str(tmp_path / "x"))["Cartella"]
    gt = rows(folder=str(_geotiff_stack(tmp_path / "Sector 9")))
    assert gt["Formato"] == "raster GeoTIFF" and gt["Metodo"] == "GPR" and "mean_v2" in gt["Prodotti (senza profondità)"]
    # it only reads: refused if it tried to write, and it wrote nothing
    assert PL.get("geofisica").commands["geofisica.describe"].writes is False


# ── the real data ───────────────────────────────────────────────────────────

@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia data is not here")
def test_real_basilica_through_the_door_and_the_panel(session):
    before = {p.name: p.stat().st_mtime for p in BASILICA.iterdir()}
    door = _value(_invoke("geofisica.read", folder=str(BASILICA), name="basilica-iulia-ert"))
    assert len(door["documents"]) == 12
    panel = _value(_invoke("geofisica.ingest", folder=str(BASILICA), name="basilica-iulia-ert", method="ert",
                           extent_x=92, extent_y=50,
                           sections="VERT1=92x8, VERT2=92x8, VERT3=92x8, VERT4=50x8, VERT5=50x8, VERT6=50x8",
                           scale_from="1-255", scale_to="0-3500", scale_unit="ohm.m",
                           scale_source="figure colour bar, risultati-fori.pdf p. 5"))
    assert [d["id"] for d in panel["documents"]] == [d["id"] for d in door["documents"]]
    g = session.host.graph()
    assert all(n.data["geometry"] == "observable" for n in _nodes(g, "document"))
    assert {p.name: p.stat().st_mtime for p in BASILICA.iterdir()} == before          # read only


@pytest.mark.skipif(not ILICI_S1.is_dir(), reason="the UA Ilici data is not here")
def test_real_ilici_through_the_door(session):
    out = _value(_invoke("geofisica.read", folder=str(ILICI_S1), name="ilici-sector-1"))
    assert len(out["documents"]) == 2 and out["geometry"] == "reality_based"
    assert all(d["geo_id"].startswith("gpr:") for d in out["documents"])
