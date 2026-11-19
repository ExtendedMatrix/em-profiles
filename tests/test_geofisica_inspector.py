"""The Inspector's section and the refusals in two languages — row G9 of the geophysics plan (MICRO-GEO10).

What is defended:

* ``geofisica.section`` is an ``inspector.section@1`` of documents and USD,
  read only; its rows carry EN and IT and ``em.plugins.compute`` writes them
  in the page's language;
* a slice says its method, depth band, quantity, the DECLARED scale (never a
  measure), who says where it lies (observable / reality_based, EPSG), the
  extent, its stack, file, identity and the stamp of its cached PNG; a GeoTIFF
  product without a depth says so;
* a USD read on slices — through an extractor (directly or through a region
  on the slice's resource) or a combiner of extractors — says the slices and
  the bands; a USD, a document or a US that are not geophysics have no rows
  (the host draws no section for them);
* a file the readers cannot read refuses the import with a sentence in EN and
  in IT, both reaching the host whole (T-6 of PL20, fixed in
  ``em.plugins.invoke``), nothing written;
* on the real data where present: a Basilica slice and UA Ilici Sector 1.
"""
from __future__ import annotations

import pytest

from test_geofisica_ingest import (BASILICA, BASILICA_DECLARED, ERT_SCALE, ILICI_S1, _geotiff_stack,  # noqa: F401
                                   _matrix_stack, _nodes, _value, session)

AUTHOR = "https://orcid.org/0000-0002-0000-0001"


def _rows(nid, lang="en"):
    from s3dgraphy.em import plugins as PL
    (v,) = PL.compute([{"key": "k", "plugin": "geofisica", "command": "geofisica.section",
                        "slot": "inspector.section@1", "slots": {"id": nid}}], lang=lang)
    assert v["ok"], v
    return {r["label"]: r["value"] for r in v["value"]}


def _doc(graph, geo_id_end):
    (d,) = [n for n in _nodes(graph, "document") if (n.data or {}).get("geo_id", "").endswith(geo_id_end)]
    return d


def test_the_section_is_declared_read_only_for_documents_and_usd(session):
    from s3dgraphy.em import plugins as PL
    c = PL.get("geofisica").commands["geofisica.section"]
    assert c.where == ["inspector.section@1"] and c.writes is False
    assert c.when == "selection:document|USD"
    assert c.label_in("it") == "Lettura geofisica" and c.label_in("en") == "Geophysical reading"


def test_a_slice_and_a_section_of_a_declared_ert_stack(tmp_path, session):
    folder = _matrix_stack(tmp_path / "basilica-like")
    _value(session(folder=str(folder), method="ert", value_scale=ERT_SCALE, declared=BASILICA_DECLARED))
    g = session.host.graph()
    sl = _doc(g, "#d1.000-1.500m")
    it, en = _rows(sl.node_id, "it"), _rows(sl.node_id, "en")
    assert it["Metodo"] == "ERT" and it["Che cosa"] == "fetta orizzontale"
    assert it["Profondità"] == "1.00–1.50 m dal piano di campagna"
    assert en["Depth"] == "1.00–1.50 m below ground"
    assert it["Grandezza"].startswith("resistività elettrica")
    assert it["Scala dei valori"].startswith("1–255 → 0–3500 ohm.m (dichiarata, confidenza bassa, figure")
    assert en["Scale of the values"].startswith("1–255 → 0–3500 ohm.m (declared, low confidence")
    assert it["Dove sta"].startswith("da un'altra documentazione (observable)")
    assert en["Extent"].startswith("92.00 × 50.00 m")
    assert it["Pila"] == "Pila ERT basilica-like" or "basilica-like" in it["Pila"]
    assert it["File"] == "100-150cm.ASC" and it["Identità"] == sl.data["geo_id"]
    assert it["Timbro"].startswith("il PNG della cache è timbrato")
    assert "%" in en["Values in the file"]
    sec = _doc(g, "#sVERT1")
    rows = _rows(sec.node_id, "en")
    assert rows["What"] == "vertical section" and rows["Depth"].endswith("along VERT1")


def test_a_geotiff_product_without_depth_is_reality_based(tmp_path, session):
    _value(session(folder=str(_geotiff_stack(tmp_path / "Sector 1")), method="gpr"))
    g = session.host.graph()
    rows = _rows(_doc(g, "#mean_v2").node_id, "it")
    assert rows["Metodo"] == "GPR" and rows["Profondità"] == "non detta (prodotto mean_v2)"
    assert rows["Dove sta"].startswith("dallo strumento (reality based)") and "EPSG:25830" in rows["Dove sta"]
    assert "Scala dei valori" not in rows                 # nothing declared: nothing said


def _usd_on(tx, name, *, extractor_on=None, region_on=None, combine=None):
    """A USD with one property whose provenance is an extractor (on a slice, or
    through a region on a resource) or a combiner of extractors on slices."""
    u = tx.add_node("USD", name)
    p = tx.add_node("property", f"{name}-depth")
    tx.add_edge(u, "has_property", p)
    if combine:
        c = tx.add_node("combiner", f"C.{name}")
        tx.add_edge(p, "has_data_provenance", c)
        for i, on in enumerate(combine):
            e = tx.add_node("extractor", f"D.{name}.{i}")
            tx.add_edge(e, "extracted_from", on)
            tx.add_edge(c, "combines", e)
        return u
    e = tx.add_node("extractor", f"D.{name}")
    tx.add_edge(p, "has_data_provenance", e)
    if extractor_on:
        tx.add_edge(e, "extracted_from", extractor_on)
    if region_on:
        r = tx.add_node("annotation_region", f"R.{name}", data={"shape_kind": "rect", "rect": [0.1, 0.2, 0.3, 0.1]})
        tx.add_edge(r, "is_on_resource", region_on)
        tx.add_edge(e, "extracted_from", r)
    return u


def test_a_usd_read_on_slices(tmp_path, session):
    from s3dgraphy import em
    _value(session(folder=str(_matrix_stack(tmp_path / "pila")), method="ert", declared=BASILICA_DECLARED))
    g = session.host.graph()
    a, b = _doc(g, "#d1.000-1.500m"), _doc(g, "#d2.500-3.000m")
    res_b = next(e.edge_target for e in g.edges if e.edge_source == b.node_id and e.edge_type == "has_linked_resource")
    with em.write("anomalies") as tx:
        one = _usd_on(tx, "USD1", extractor_on=a.node_id)
        reg = _usd_on(tx, "USD2", region_on=res_b)
        comb = _usd_on(tx, "USD3", combine=[a.node_id, b.node_id])
        plain = tx.add_node("USD", "USD4")
        us = tx.add_node("US", "US5")
    rows = _rows(one, "it")
    assert rows["Letta su"] == "1 fetta geofisica" and rows["Attraverso"] == "1 estrattore"
    assert rows["Bande"] == "1.00–1.50 m dal piano di campagna"
    assert rows["Fetta"].startswith(a.name)
    assert _rows(reg, "en")["Read on"] == "1 geophysical slice"            # through the region on the resource
    rows = _rows(comb, "en")
    assert rows["Read on"] == "2 geophysical slices" and rows["Through"] == "1 combiner"
    assert rows["Bands"] == "1.00–3.00 m below ground"
    assert _rows(plain) == {} and _rows(us) == {}
    # a document that is not a slice: no rows either
    with em.write("a document") as tx:
        other = tx.add_node("document", "D.99")
    assert _rows(other) == {}


@pytest.mark.parametrize("lang", ["it", "en"])
def test_an_unreadable_file_is_refused_in_both_languages(tmp_path, session, monkeypatch, lang):
    """T-6 of PL20: whatever the host's language, the host gets EN and IT whole."""
    from s3dgraphy.em import plugins as PL
    monkeypatch.setattr(session.host, "language", lambda: lang)
    bad = tmp_path / "rotta"
    bad.mkdir()
    (bad / "100-150cm.ASC").write_text("abc def\n1 2 3\n")
    res = session(folder=str(bad), method="ert", declared=BASILICA_DECLARED)
    assert not res.ok and res.data["reason"] == "handler-failed"
    msgs = res.data["messages"]
    assert "the stack rotta cannot be read" in msgs["en"] and "did not succeed" in msgs["en"]
    assert "la pila rotta non si legge" in msgs["it"] and "non è riuscito" in msgs["it"]
    assert not _nodes(session.host.graph(), "document")
    tif = tmp_path / "tif"
    tif.mkdir()
    (tif / "mean_v2.tif").write_bytes(b"II*\x00garbage")
    res = PL.invoke("geofisica", "geofisica.ingest", {"folder": str(tif), "kind": "geotiff", "at": "2026-11-19T12:00:00Z"},
                    author=AUTHOR)
    assert not res.ok and "la pila tif non si legge" in res.data["messages"]["it"]
    assert "the stack tif cannot be read" in res.data["messages"]["en"]


@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia's data is not on this machine")
def test_real_basilica_slice_section(tmp_path, session):
    _value(session(folder=str(BASILICA), method="ert", value_scale=ERT_SCALE, declared=BASILICA_DECLARED))
    rows = _rows(_doc(session.host.graph(), "#d1.000-1.500m").node_id, "it")
    assert rows["Metodo"] == "ERT" and rows["Estensione"].startswith("92.00 × 50.00 m")
    assert rows["File"] == "100-150cm.ASC" and rows["Dove sta"].startswith("da un'altra documentazione")


@pytest.mark.skipif(not ILICI_S1.is_dir(), reason="UA Ilici's data is not on this machine")
def test_real_ilici_sector_1_section(tmp_path, session):
    _value(session(folder=str(ILICI_S1), method="gpr", name="Ilici-S1"))
    rows = _rows(_doc(session.host.graph(), "#mean_v2").node_id, "en")
    assert rows["Method"] == "GPR" and "EPSG:25830" in rows["Where it lies"]
    assert rows["Depth"] == "not said (product mean_v2)" and rows["File"] == "mean_v2.tif"
