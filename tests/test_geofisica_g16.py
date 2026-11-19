"""The finishing touches of the field test — row G16 of the geophysics plan (MICRO-GEO16).

What is defended:

* (h) ``scan_stack(folder)`` with its default ``"auto"`` reads a GeoTIFF or
  ASCII folder by its own reader (before: as pictures, or nothing);
* (d) many ``same_values`` warnings are said as a few and ONE sentence
  (``summarize_warnings``; Alcudia: 217 repeated captures), the manifest
  keeps them all;
* (a) the import panel declares the frame of a stack of screen captures —
  the metres of the first and last ticks, the pixels typed or measured on
  the first capture — and the origin, EPSG and «according to»: a stack of
  captures enters from the panel alone, no script;
* (b) the anomalies traced on a slice come back on its plane as the
  ``marks`` of ``space.layer@1`` (one per extractor, in the plane's metres,
  labelled by the USD and the kind in the reader's language);
* (i) an origin «according to the instrument» (its own coordinates,
  transcribed) is ``reality_based``; a documentation ``observable``; by eye
  ``asserted``.
"""
from __future__ import annotations

import importlib

import pytest

from test_geofisica_ingest import BASILICA_DECLARED, _geotiff_stack, _matrix_stack, _nodes, _value, session  # noqa: F401

np = pytest.importorskip("numpy")
core = importlib.import_module("geofisica_core")


# ── (h) the default reads every kind it can guess ───────────────────────────

def test_scan_stack_auto_asks_guess_kind(tmp_path):
    tif = _geotiff_stack(tmp_path / "Sector 1")
    kind, specs = core.scan_stack(str(tif))
    assert kind == "geotiff" and [s.product for s in specs] == ["mean_v2", "sqmean_v2"]
    kind, specs = core.scan_stack(str(_matrix_stack(tmp_path / "ert")))
    assert kind == "ascii_matrix" and [s.orientation for s in specs] == ["horizontal", "horizontal", "vertical"]
    geo = core.detect_georeference(str(tif))                 # its default is "auto" too
    assert geo["epsg"] == 25830


# ── (d) the warnings, summed up ─────────────────────────────────────────────

def _same(i):
    return {"code": "same_values", "path": "/s/%03d.jpg" % i, "same_as": "/s/000.jpg",
            "en": "%d same" % i, "it": "%d uguale" % i}


def test_many_same_values_are_one_sentence():
    other = {"code": "saturation", "en": "x", "it": "x"}
    few = [_same(1), other, _same(2)]
    assert core.summarize_warnings(few) == few
    many = [_same(i) for i in range(1, 218)] + [other]
    out = core.summarize_warnings(many)
    assert [w["code"] for w in out] == ["same_values"] * 3 + ["same_values_many", "saturation"]
    s = out[3]
    assert s["count"] == 217 and len(s["paths"]) == 214 and s["paths"][0] == "/s/004.jpg"
    assert s["en"].startswith("217 slices hold the same values") and "214 more" in s["en"]
    assert s["it"].startswith("217 fette ripetono i valori") and "altre 214" in s["it"]
    assert core.summarize_warnings([]) == [] and len(many) == 218       # the input untouched


# ── (a) the panel's frame and placement ─────────────────────────────────────

def test_the_panel_fields_of_a_capture_stack(session):          # the plugin loaded: its modules
    from geofisica.door import panel_slots
    from geofisica.ingest import Said
    out = panel_slots({"frame": "610, 170, 1303, 715", "frame_x": "-50 25", "frame_y": "-22;37",
                       "origin": "701806.741, 4234824.081", "epsg": 25830, "origin_from": "instrument"})
    assert out["declared"]["frame"] == {"px": [610, 170, 1303, 715], "x_range": [-50.0, 25.0],
                                        "y_range": [-22.0, 37.0]}
    g = out["georef"]
    assert (g["origin_e"], g["origin_n"], g["epsg"]) == (701806.741, 4234824.081, 25830)
    assert g["source"].startswith("instrument")
    assert panel_slots({"frame_x": "-50 25", "frame_y": "-22 37"})["declared"]["frame"]["px"] is None
    assert panel_slots({"origin": "1 2"})["georef"]["source"] == "declared"
    for bad, word in (({"frame_x": "-50 25"}, "tacche"), ({"frame": "1 2 3", "frame_x": "0 1", "frame_y": "0 1"}, "quattro"),
                      ({"frame": "9 9 3 20", "frame_x": "0 1", "frame_y": "0 1"}, "destra"),
                      ({"epsg": 25830}, "origine"), ({"origin": "1 2", "epsg": "1.5"}, "codice"),
                      ({"origin": "1 2", "origin_from": "radar"}, "origin_from")):
        with pytest.raises(Said) as e:
            panel_slots(bad)
        assert word in e.value.messages["it"] and e.value.messages["en"]


def _capture(w=200, h=120, px=(40, 20, 160, 100), seed=0):
    """A capture as test_geofisica_readers_b draws it: black, two light axes
    with ticks, a coloured survey inside."""
    a = np.zeros((h, w, 3), dtype=np.uint8)
    left, top, right, bottom = px
    a[bottom, left - 30:right + 10] = 230
    a[top - 5:bottom + 10, left] = 230
    for c in np.linspace(left, right, 4).astype(int):
        a[bottom + 1:bottom + 6, c] = 230
    for r in np.linspace(top, bottom, 3).astype(int):
        a[r, left - 5:left] = 230
    rng = np.random.default_rng(seed)
    a[40:80, 60:140, 0] = rng.integers(100, 255, (40, 80))
    a[40:80, 60:140, 1] = rng.integers(0, 80, (40, 80))
    return a


def _captures(folder, seeds):
    folder.mkdir(parents=True)
    for i, seed in enumerate(seeds):
        rgba = np.zeros((120, 200, 4), dtype=np.uint8)
        rgba[..., :3] = _capture(seed=seed)
        rgba[..., 3] = 255
        core.write_png(str(folder / ("Slice_-%04dmm.png" % (5 * i))), rgba[::-1])
    return folder


def test_a_capture_stack_enters_from_the_panel_alone(tmp_path, session):
    pytest.importorskip("PIL")                                # the host's decoder
    folder = _captures(tmp_path / "Sector1_Alcudia", [0, 1, 1, 1, 1, 1, 2])
    out = _value(session(folder=str(folder), method="gpr", name="Alcudia",
                         frame_x="-50 25", frame_y="-22 37",          # pixels measured, kind from the frame
                         origin="701806.741, 4234824.081", epsg=25830, origin_from="instrument"))
    assert len(out["documents"]) == 7 and out["geometry"] == "reality_based"
    acq = _nodes(session.host.graph(), "dtc_acquisition")[0].data
    assert acq["geo_kind"] == "screenshot" and acq["epsg"] == 25830
    assert acq["georef"]["origin_e"] == 701806.741
    assert acq["grid"]["nx"] == 121 and acq["grid"]["x_min"] == -50
    # five captures repeat the second: three said, then one sentence
    codes = [w["code"] for w in out["warnings"]]
    assert codes == ["same_values"] * 3 + ["same_values_many"]
    assert out["warnings"][-1]["count"] == 4
    # the same frame typed in pixels: the same documents, nothing added
    again = _value(session(folder=str(folder), method="gpr", name="Alcudia", kind="screenshot",
                           frame="40 20 160 100", frame_x="-50 25", frame_y="-22 37",
                           origin="701806.741, 4234824.081", epsg=25830, origin_from="instrument"))
    assert not [i for i in again["added"] if i.startswith("doc")] and len(again["documents"]) == 7


def test_a_capture_stack_without_its_frame_is_said(tmp_path, session):
    pytest.importorskip("PIL")
    folder = _captures(tmp_path / "caps", [0, 1])
    res = session(folder=str(folder), kind="screenshot")
    assert not res.ok and "riquadro" in res.data["messages"]["it"]
    blank = tmp_path / "blank"
    blank.mkdir()
    rgba = np.zeros((50, 50, 4), dtype=np.uint8)
    rgba[..., 3] = 255
    core.write_png(str(blank / "Slice_-0005mm.png"), rgba)
    res = session(folder=str(blank), frame_x="0 1", frame_y="0 1")
    assert not res.ok and "scrivine i pixel" in res.data["messages"]["it"]
    assert "write its pixels" in res.data["messages"]["en"]


def test_describe_a_capture_stack(session, tmp_path):
    from s3dgraphy.em import plugins as PL
    folder = _captures(tmp_path / "caps", [0, 1])

    def rows(lang, **slots):
        (item,) = PL.compute([{"key": "k", "plugin": "geofisica", "command": "geofisica.describe",
                               "slot": "panel@1", "slots": slots}], lang=lang)
        assert item["ok"], item
        return {r["label"]: r["value"] for r in item["value"]}

    r = rows("it", folder=str(folder), kind="screenshot")
    assert r["Formato"] == "schermate" and r["Fette"] == "2" and "riquadro" in r["Manca"]
    r = rows("it", folder=str(folder), frame_x="-50 25", frame_y="-22 37")
    assert r["Formato"] == "schermate" and r["Riquadro"] == "misurato sulla prima schermata: x -50…25 m, y -22…37 m"
    r = rows("en", folder=str(folder), frame="610 170 1303 715", frame_x="-50 25", frame_y="-22 37")
    assert r["Frame"] == "pixels 610, 170, 1303, 715: x -50…25 m, y -22…37 m"


# ── (i) who says where the slices are ───────────────────────────────────────

def test_the_origin_according_to_whom(session):
    from geofisica.ingest import placement
    m = {"georef": {}}
    for source, want in (("instrument (its own coordinates, transcribed)", "reality_based"),
                         ("strumento", "reality_based"),
                         ("documentation (figure, plan, report)", "observable"),
                         ("by eye", "asserted"), ("declared", "asserted")):
        assert placement("screenshot", m, {"origin_e": 1.0, "origin_n": 2.0, "source": source}, None)[0] == want


# ── (b) the anomaly drawn on its planes ─────────────────────────────────────

def test_the_anomalies_are_marks_on_their_planes(tmp_path, session):
    from s3dgraphy.em import plugins as PL
    from test_geofisica_trace import _doc, _layer_g, _trace
    folder = _matrix_stack(tmp_path / "pila")
    (folder / "300-350cm.ASC").write_text((folder / "250-300cm.ASC").read_text().replace("255", "254"))
    _value(session(folder=str(folder), method="ert", declared=dict(BASILICA_DECLARED)))
    g = session.host.graph()
    a, b, c = (_doc(g, e) for e in ("#d1.000-1.500m", "#d2.500-3.000m", "#d3.000-3.500m"))
    assert _trace("line", _layer_g("polyline", (a.node_id, 0.25, 0.5), (a.node_id, 0.75, 0.5))).ok
    assert _trace("area", _layer_g("surface", (b.node_id, 0.1, 0.1), (b.node_id, 0.5, 0.1), (b.node_id, 0.5, 0.5),
                                   through=[c.node_id]), type="alta_resistivita").ok

    def layer(lang):
        (v,) = PL.compute([{"key": "L", "plugin": "geofisica", "command": "geofisica.layer",
                            "slot": "space.layer@1", "slots": {}}], lang=lang)
        assert v["ok"], v
        (lay,) = v["value"]
        return {i["id"]: i["marks"] for i in lay["items"]}

    m = layer("en")
    (line,) = m[a.node_id]
    assert line["primitive"] == "polyline" and line["points"] == [[23.0, 25.0], [69.0, 25.0]]
    assert line["label"] == "USD1 · linear anomaly"
    (area_b,), (area_c,) = m[b.node_id], m[c.node_id]                  # one extractor per slice
    assert area_b["primitive"] == area_c["primitive"] == "surface" and area_b["points"] == area_c["points"]
    assert area_b["label"] == "USD2 · high-resistivity zone"
    assert layer("it")[b.node_id][0]["label"] == "USD2 · zona ad alta resistività"
    assert all(not v for k, v in m.items() if k not in (a.node_id, b.node_id, c.node_id))
