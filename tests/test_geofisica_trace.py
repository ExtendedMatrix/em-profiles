"""Tracing an anomaly on a slice — row G12 of the geophysics plan (MICRO-GEO13).

What is defended:

* three tools of the Space (``space.tool@1``: point, polyline, surface) that
  write, with a ``geometry`` slot;
* a trace on ONE slice writes, in one act, a USD (``geof:anomalia``, the kind
  from the package's vocabulary), its properties (kind as a concept, method,
  depths) whose provenance is ONE extractor (``geof:anomalia_*``) extracted
  from a region on the slice's file, the coords in the stack's metres with
  z = −depth and the same place on the picture (uv);
* a trace on THREE slices (clicks on two planes, a third shown «up to») writes
  one extractor per slice and a combiner of them;
* the same trace again adds nothing; a refusal speaks EN and IT and writes
  nothing; the kinds of the code are the vocabulary's;
* the em.json saved reads back, validates, and the Inspector (row G9) says
  the slices the USD was read on;
* on the real data where present: one anomaly on the Basilica Iulia (ERT,
  observable) and one on UA Ilici Sector 1 (GPR, EPSG:25830).
"""
from __future__ import annotations

import re

import pytest

from test_geofisica_ingest import (BASILICA, BASILICA_DECLARED, ERT_SCALE, ILICI_S1, NS, PKG,  # noqa: F401
                                   _edges, _geotiff_stack, _matrix_stack, _nodes, _value, session)

AUTHOR = "https://orcid.org/0000-0002-0000-0001"


def _trace(cmd, g, **slots):
    from s3dgraphy.em import plugins as PL
    return PL.invoke("geofisica", f"geofisica.trace.{cmd}", dict(slots, g=g), author=AUTHOR)


def _doc(graph, geo_id_end):
    (d,) = [n for n in _nodes(graph, "document") if (n.data or {}).get("geo_id", "").endswith(geo_id_end)]
    return d


def _layer_g(prim, *pts, through=()):
    """What EMStudio fills when the person clicks on the planes: (doc, u, v) per click."""
    return {"primitive": prim, "vertices": [[0, 0, 0]] * len(pts), "frame": "layer", "on": pts[0][0],
            "at": [{"on": d, "uv": [u, v]} for d, u, v in pts], "through": list(through)}


def _props(graph, usd):
    out = {}
    for e in graph.edges:
        if e.edge_source == usd and e.edge_type == "has_property":
            p = graph.find_node_by_id(e.edge_target)
            out[p.name] = p
    return out


def _prov(graph, pid):
    return [e.edge_target for e in graph.edges if e.edge_source == pid and e.edge_type == "has_data_provenance"]


def test_three_tools_of_the_space_that_write(session):
    from s3dgraphy.em import plugins as PL
    p = PL.get("geofisica")
    got = {c: (p.commands[c].primitive, p.commands[c].writes, p.commands[c].where)
           for c in ("geofisica.trace.point", "geofisica.trace.line", "geofisica.trace.area")}
    assert got == {"geofisica.trace.point": ("point", True, ["space.tool@1"]),
                   "geofisica.trace.line": ("polyline", True, ["space.tool@1"]),
                   "geofisica.trace.area": ("surface", True, ["space.tool@1"])}
    assert {c.id for c in PL.tools()} >= set(got)
    assert p.commands["geofisica.trace.line"].label_in("it") == "Anomalia lineare su fetta"


def test_the_kinds_of_the_code_are_the_vocabulary(session):
    from geofisica import trace as T
    ttl = (PKG / "data" / "vocab" / "anomalie.ttl").read_text(encoding="utf-8")
    concepts = re.findall(r'^v:(\w+) a skos:Concept.*?skos:prefLabel "([^"]+)"@it , "([^"]+)"@en', ttl, re.S | re.M)
    assert {k: (en, it) for k, it, en in concepts} == T.TYPES


def test_a_line_on_one_slice_is_a_usd_with_its_extractor(tmp_path, session):
    _value(session(folder=str(_matrix_stack(tmp_path / "pila")), method="ert", value_scale=ERT_SCALE,
                   declared=BASILICA_DECLARED))
    g = session.host.graph()
    sl = _doc(g, "#d1.000-1.500m")
    steps = len(session.host.steps)
    r = _trace("line", _layer_g("polyline", (sl.node_id, 0.25, 0.5), (sl.node_id, 0.75, 0.5)))
    assert r.ok, r.message
    out = r.data["value"] if "value" in r.data else r.data
    assert len(session.host.steps) == steps + 1                       # one act, one undo step
    usd = g.find_node_by_id(out["usd"])
    assert usd.node_type == "USD" and usd.name == "USD1"
    assert usd.data["em_kind"] == "geof:anomalia" and usd.data["anomaly_type"] == NS + "anomalie/lineare"
    assert usd.description.startswith("Linear anomaly traced on " + sl.name) and "1.00–1.50 m" in usd.description
    (xid,) = out["extractors"]
    x = g.find_node_by_id(xid)
    assert x.node_type == "extractor" and x.data["em_kind"] == "geof:anomalia_linea"
    assert x.name == sl.name + ".01" and x.data["depth_top"] == 1.0 and x.data["depth_bottom"] == 1.5
    assert x.data["geo"]["local"] == [[23.0, 25.0], [69.0, 25.0]]       # 92 × 50 m declared
    assert x.data["geo"]["measure"] == {"length_m": 46.0} == out["measure"]
    (reg,) = [t for s, t in _edges(g, "extracted_from") if s == xid]
    region = g.find_node_by_id(reg)
    assert region.node_type == "annotation_region" and region.data["geometry_kind"] == "polyline"
    assert region.data["coords"] == [[23.0, 25.0, -1.25], [69.0, 25.0, -1.25]]
    assert region.data["frame"] == "geof:stack" and region.data["uv"] == [[0.25, 0.5], [0.75, 0.5]]
    (res,) = [t for s, t in _edges(g, "is_on_resource") if s == reg]
    assert (sl.node_id, res) in _edges(g, "has_linked_resource")      # the slice's file
    props = _props(g, usd.node_id)
    assert set(props) == {"geof:anomaly_type", "geof:method", "geof:depth_top", "geof:depth_bottom"}
    assert all(_prov(g, p.node_id) == [xid] for p in props.values())
    assert props["geof:depth_top"].value == 1.0 and props["geof:depth_bottom"].value == 1.5
    # the same trace again: nothing added
    again = _trace("line", _layer_g("polyline", (sl.node_id, 0.25, 0.5), (sl.node_id, 0.75, 0.5)))
    assert again.ok and (again.data.get("value") or again.data)["added"] == []
    assert len(_nodes(g, "USD")) == 1


def test_an_area_on_three_slices_is_a_combiner(tmp_path, session):
    folder = _matrix_stack(tmp_path / "pila")
    (folder / "300-350cm.ASC").write_text((folder / "250-300cm.ASC").read_text().replace("255", "254"))
    _value(session(folder=str(folder), method="ert", declared=BASILICA_DECLARED))
    g = session.host.graph()
    a, b, c = (_doc(g, e) for e in ("#d1.000-1.500m", "#d2.500-3.000m", "#d3.000-3.500m"))
    gg = _layer_g("surface", (a.node_id, 0.1, 0.1), (b.node_id, 0.5, 0.1), (a.node_id, 0.5, 0.5),
                  through=[c.node_id, "nobody"])
    r = _trace("area", gg, type="alta_resistivita", confidence=0.6, ids=["US-not-a-slice"])
    assert r.ok, r.message
    out = r.data.get("value") or r.data
    assert out["slices"] == [a.node_id, b.node_id, c.node_id] and len(out["extractors"]) == 3
    comb = g.find_node_by_id(out["combiner"])
    assert comb.node_type == "combiner" and comb.name == "C.01"
    assert sorted(t for s, t in _edges(g, "combines") if s == comb.node_id) == sorted(out["extractors"])
    usd = g.find_node_by_id(out["usd"])
    assert usd.data["anomaly_type"] == NS + "anomalie/alta_resistivita"
    props = _props(g, usd.node_id)
    assert all(_prov(g, p.node_id) == [comb.node_id] for p in props.values())
    assert props["geof:depth_top"].value == 1.0 and props["geof:depth_bottom"].value == 3.5
    assert props["geof:confidence"].value == 0.6
    zs = sorted({tuple(c[2] for c in g.find_node_by_id(rg).data["coords"])[0] for rg in out["regions"]})
    assert zs == [-3.25, -2.75, -1.25]
    assert out["measure"]["area_m2"] == pytest.approx(0.5 * 36.8 * 20.0)
    # the Inspector of row G9 reads it
    from s3dgraphy.em import plugins as PL
    (v,) = PL.compute([{"key": "k", "plugin": "geofisica", "command": "geofisica.section",
                        "slot": "inspector.section@1", "slots": {"id": usd.node_id}}], lang="it")
    rows = {x["label"]: x["value"] for x in v["value"]}
    assert rows["Letta su"] == "3 fette geofisiche" and rows["Attraverso"] == "1 combinatore"
    assert rows["Anomalia"] == "zona ad alta resistività" and rows["Bande"].startswith("1.00–3.50 m")
    (v,) = PL.compute([{"key": "k", "plugin": "geofisica", "command": "geofisica.section",
                        "slot": "inspector.section@1", "slots": {"id": usd.node_id}}], lang="en")
    assert {x["label"]: x["value"] for x in v["value"]}["Anomaly"] == "high-resistivity zone"   # G15: not the slug


def test_a_point_on_a_section_and_the_refusals(tmp_path, session):
    _value(session(folder=str(_matrix_stack(tmp_path / "pila")), method="ert", declared=BASILICA_DECLARED))
    g = session.host.graph()
    sec = _doc(g, "#sVERT1")
    r = _trace("point", _layer_g("point", (sec.node_id, 0.5, 0.75)), type="iperbole")
    assert r.ok, r.message
    out = r.data.get("value") or r.data
    reg = g.find_node_by_id(out["regions"][0])
    assert reg.data["geometry_kind"] == "point" and reg.data["frame"] == "geof:section"
    assert reg.data["coords"] == [[46.0, 0.0, -2.0]]                  # 92 × 8 m, a quarter down
    n = len(g.nodes)
    steps = len(session.host.steps)
    sl = _doc(g, "#d1.000-1.500m")
    for cmd, gg, en, it in (
            ("line", {"primitive": "polyline", "vertices": [[0, 0, 0], [1, 1, 1]], "on": "RM1", "frame": "model"},
             "not on a model", "non su un modello"),
            ("area", _layer_g("surface", (sl.node_id, 0, 0), (sl.node_id, 1, 1)), "at least 3 points", "almeno 3 punti"),
            ("point", _layer_g("point", ("US1", 0.5, 0.5)), "not on a geophysical slice", "non è su una fetta geofisica"),
    ):
        r = _trace(cmd, gg)
        assert not r.ok
        msgs = r.data["messages"]
        assert en in msgs["en"] and it in msgs["it"], msgs
    r = _trace("point", _layer_g("point", (sl.node_id, 0.5, 0.5)), type="muro")
    assert not r.ok and "lineare" in r.data["messages"]["it"]
    assert len(g.nodes) == n and len(session.host.steps) == steps     # nothing written


def test_the_saved_document_reads_back_and_validates(tmp_path, session):
    from s3dgraphy import api, em
    from s3dgraphy.container import load_container_file
    _value(session(folder=str(_matrix_stack(tmp_path / "pila")), method="ert", declared=BASILICA_DECLARED))
    g = session.host.graph()
    sl = _doc(g, "#d2.500-3.000m")
    out = _trace("point", {"frame": "stack", "on": sl.node_id, "vertices": [[10.0, 20.0]]})
    assert out.ok, out.message
    usd_id = (out.data.get("value") or out.data)["usd"]
    path = em.host.current().save(str(tmp_path / "geo.em.json"))
    container, _w = load_container_file(path)
    g2 = container.active()
    v = api.validate(g2)
    assert v["ok"] and not v["issues"], v
    usd = g2.find_node_by_id(usd_id)
    assert usd is not None and usd.data["anomaly_type"].endswith("/puntuale")
    (p,) = [t for s, t in _edges(g2, "has_property") if s == usd_id and g2.find_node_by_id(t).name == "geof:anomaly_type"]
    (x,) = _prov(g2, p)
    (reg,) = [t for s, t in _edges(g2, "extracted_from") if s == x]
    assert g2.find_node_by_id(reg).data["coords"] == [[10.0, 20.0, -2.75]]


@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia data is not here")
def test_real_basilica_an_anomaly(tmp_path, session):
    from s3dgraphy import api, em
    from s3dgraphy.container import load_container_file
    _value(session(folder=str(BASILICA), method="ert", value_scale=ERT_SCALE,
                   declared=BASILICA_DECLARED, name="basilica-iulia-ert"))
    g = session.host.graph()
    top = _doc(g, "#d1.000-1.500m")
    deep = _doc(g, "#d2.500-3.000m")
    gg = _layer_g("polyline", (top.node_id, 0.2, 0.6), (top.node_id, 0.8, 0.6), through=[deep.node_id])
    r = _trace("line", gg)
    assert r.ok, r.message
    out = r.data.get("value") or r.data
    assert len(out["extractors"]) == 2 and out["combiner"]
    assert out["measure"]["length_m"] == pytest.approx(0.6 * 92.0)
    path = em.host.current().save(str(tmp_path / "basilica.em.json"))
    g2 = load_container_file(path)[0].active()
    assert api.validate(g2)["ok"] and g2.find_node_by_id(out["combiner"]).node_type == "combiner"


@pytest.mark.skipif(not ILICI_S1.is_dir(), reason="the UA Ilici data is not here")
def test_real_ilici_an_anomaly(tmp_path, session):
    from s3dgraphy import api, em
    from s3dgraphy.container import load_container_file
    _value(session(folder=str(ILICI_S1), method="gpr", name="ilici-sector-1"))
    g = session.host.graph()
    mean = _doc(g, "#mean_v2")
    r = _trace("area", _layer_g("surface", (mean.node_id, 0.3, 0.3), (mean.node_id, 0.6, 0.3),
                                (mean.node_id, 0.6, 0.5)))
    assert r.ok, r.message
    out = r.data.get("value") or r.data
    assert len(out["extractors"]) == 1 and out["combiner"] is None
    reg = g.find_node_by_id(out["regions"][0])
    assert all(c[2] == 0.0 for c in reg.data["coords"])                # a product without depth: at ground
    path = em.host.current().save(str(tmp_path / "ilici.em.json"))
    g2 = load_container_file(path)[0].active()
    assert api.validate(g2)["ok"] and g2.find_node_by_id(out["usd"]).data["anomaly_type"].endswith("/areale")
