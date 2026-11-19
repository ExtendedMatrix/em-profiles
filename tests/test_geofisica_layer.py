"""The stacks as layers of the Space — row G10 of the geophysics plan (MICRO-GEO11).

What is defended:

* ``geofisica.layer`` is a ``space.layer@1`` of kind ``raster_stack``, read
  only;
* ONE ``em.plugins.compute`` gives the host the stacks of the open graph in
  the one shape (``em.plugins.shape``): a layer per stack, a plane per slice
  or section — slices from the shallowest down, products without a depth
  after, sections last; the picture and its stamp as paths inside the
  plugin's data folder (the only place the bridge serves from), present on
  this machine; the frame's origin the stack's georef in doubles (UA Ilici to
  the millimetre), none for a stack not placed in the world (the Basilica);
  a section's plane along its line and down, its trace on the ground not said;
* a cache that is not on this machine leaves the plane without a picture,
  never with a path that would not be served; the graph's landscape surface
  becomes the ground; over 60 slices a stack is shown one at a time; ``stack``
  asks for one stack by its name or its acquisition;
* on the real data where present: the Basilica's 6 slices + 6 sections and
  UA Ilici Sector 1.
"""
from __future__ import annotations

import os
import shutil
import time

import pytest

from test_geofisica_ingest import (BASILICA, BASILICA_DECLARED, ERT_SCALE, ILICI_S1, _geotiff_stack,  # noqa: F401
                                   _matrix_stack, _nodes, _value, session)


def _layers(lang="en", **slots):
    from s3dgraphy.em import plugins as PL
    t0 = time.time()
    (v,) = PL.compute([{"key": "L", "plugin": "geofisica", "command": "geofisica.layer",
                        "slot": "space.layer@1", "slots": slots}], lang=lang)
    assert v["ok"], v
    _layers.took = time.time() - t0
    return v["value"]


def _data_dir():
    from s3dgraphy.em import plugins as PL
    return os.path.join(str(PL.plugins_data_dir()), "geofisica")


def test_the_layer_is_declared_read_only(session):
    from s3dgraphy.em import plugins as PL
    c = PL.get("geofisica").commands["geofisica.layer"]
    assert c.where == ["space.layer@1"] and c.layer == "raster_stack" and c.writes is False
    assert c.label_in("it") == "Fette geofisiche" and c.label_in("en") == "Geophysical slices"
    assert [x.name for x in PL.layers()] == ["geofisica/geofisica.layer"]


def test_no_stack_no_layer(session):
    assert _layers() == []


def test_a_declared_ert_stack_is_one_layer_not_placed_in_the_world(tmp_path, session):
    _value(session(folder=str(_matrix_stack(tmp_path / "basilica-like")), method="ert",
                   value_scale=ERT_SCALE, declared=BASILICA_DECLARED))
    (layer,) = _layers("it")
    acq = _nodes(session.host.graph(), "dtc_acquisition")[0]
    assert layer["kind"] == "raster_stack" and layer["id"] == acq.node_id and layer["name"] == acq.name
    assert layer["frame"] == {"epsg": None, "origin": None, "rotation": 0.0, "local": True}
    assert layer["ground"] == {"mode": "flat", "z": 0.0, "surface": None}
    assert layer["display"] == {"mode": "all", "index": 0} and layer["opacity"] == 1.0
    a, b, s = layer["items"]
    assert [a["orientation"], b["orientation"], s["orientation"]] == ["horizontal", "horizontal", "vertical"]
    assert (a["depth_top"], a["depth_bottom"], b["depth_top"]) == (1.0, 1.5, 2.5)
    assert a["label"].endswith("1.00–1.50 m dal piano di campagna") and a["extent"] == [0.0, 0.0, 92.0, 50.0]
    assert s["extent"] == [0.0, -8.0, 92.0, 0.0] and s["line"] is None and "lungo VERT1" in s["label"]
    # the pictures and their stamps: inside the plugin's folder, on this machine
    for it in layer["items"]:
        assert it["image"].startswith("cache/") and it["image"].endswith(".png")
        assert it["stamp"] == it["image"] + ".stamp.json"
        assert os.path.isfile(os.path.join(_data_dir(), *it["image"].split("/")))
        assert os.path.isfile(os.path.join(_data_dir(), *it["stamp"].split("/")))
    doc = session.host.graph().find_node_by_id(a["id"])
    assert doc.node_type == "document" and doc.data["geo_id"].endswith("#d1.000-1.500m")
    en = _layers("en")[0]["items"][0]["label"]
    assert en.endswith("1.00–1.50 m below ground")


def test_a_georeferenced_stack_keeps_its_origin_and_one_stack_is_asked(tmp_path, session):
    _value(session(folder=str(_matrix_stack(tmp_path / "b")), method="ert", declared=BASILICA_DECLARED))
    _value(session(folder=str(_geotiff_stack(tmp_path / "Sector 1")), method="gpr"))
    layers = _layers()
    assert len(layers) == 2
    (gpr,) = _layers(stack="Sector 1")
    assert gpr["frame"] == {"epsg": 25830, "origin": [701756.963, 4234860.682], "rotation": 0.0, "local": True}
    assert [i["label"].split(" · ")[1] for i in gpr["items"]] == ["mean_v2", "sqmean_v2"]
    assert all(i["depth_top"] is None for i in gpr["items"])
    assert gpr["items"][0]["extent"] == [0.0, 0.0, 0.8, 0.6]
    assert _layers(stack=gpr["id"]) == [gpr]
    assert _layers(stack="nowhere") == []


def test_a_cache_not_on_this_machine_leaves_the_plane_without_a_picture(tmp_path, session):
    out = _value(session(folder=str(_matrix_stack(tmp_path / "b")), method="ert", declared=BASILICA_DECLARED))
    shutil.rmtree(out["cache_dir"])
    (layer,) = _layers()
    assert len(layer["items"]) == 3 and all(i["image"] is None and i["stamp"] is None for i in layer["items"])


def test_the_landscape_surface_is_the_ground(tmp_path, session):
    from s3dgraphy.nodes import LandscapeSurfaceNode
    _value(session(folder=str(_matrix_stack(tmp_path / "b")), method="ert", declared=BASILICA_DECLARED))
    session.host.graph().add_node(LandscapeSurfaceNode("LS1"))
    (layer,) = _layers()
    assert layer["ground"] == {"mode": "surface", "z": 0.0, "surface": "LS1"}


def test_over_sixty_slices_one_at_a_time(tmp_path, session):
    folder = tmp_path / "many"
    folder.mkdir()
    for i in range(61):
        (folder / f"{i * 10}-{i * 10 + 10}cm.ASC").write_text("1 2 3\n4 5 6\n")
    _value(session(folder=str(folder), method="ert", declared={"extent": [3.0, 2.0]}))
    (layer,) = _layers()
    assert len(layer["items"]) == 61 and layer["display"]["mode"] == "one"
    tops = [i["depth_top"] for i in layer["items"]]
    assert tops == sorted(tops) and tops[0] == 0.0


@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia data is not here")
def test_real_basilica_twelve_planes(tmp_path, session):
    _value(session(folder=str(BASILICA), method="ert", value_scale=ERT_SCALE,
                   declared=BASILICA_DECLARED, name="basilica-iulia-ert"))
    (layer,) = _layers("it")
    flat = [i for i in layer["items"] if i["orientation"] == "horizontal"]
    sections = [i for i in layer["items"] if i["orientation"] == "vertical"]
    assert len(flat) == 6 and len(sections) == 6 and layer["frame"]["origin"] is None
    assert all(i["image"] and i["stamp"] for i in layer["items"])
    assert all(i["extent"] == [0.0, 0.0, 92.0, 50.0] for i in flat)
    assert {tuple(i["extent"]) for i in sections} == {(0.0, -8.0, 92.0, 0.0), (0.0, -8.0, 50.0, 0.0)}
    print("\nBASILICA layer: %d planes in %.3f s" % (len(layer["items"]), _layers.took))


@pytest.mark.skipif(not ILICI_S1.is_dir(), reason="the UA Ilici data is not here")
def test_real_ilici_sector_1(tmp_path, session):
    _value(session(folder=str(ILICI_S1), method="gpr", name="ilici-sector-1"))
    (layer,) = _layers()
    assert layer["frame"]["epsg"] == 25830 and len(layer["items"]) == 2
    e, n = layer["frame"]["origin"]
    assert 700000 < e < 710000 and 4230000 < n < 4240000
    print("\nILICI Sector 1 layer: origin %r in %.3f s" % (layer["frame"]["origin"], _layers.took))
