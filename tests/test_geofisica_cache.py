"""MICRO-GEO06 · row G5 of the geophysics plan: colour and cache (``geofisica_core.cache``).

What is defended: the package's ramps in the core are the ``.emc`` files'
colour mappings (the core travels without ``data/``: 3DSC); a ramp, an old
colour map and an ``.emc`` read from disk all colour; the declared
``value_scale`` (the Basilica's 1–255 → 0–3500 Ω·m) maps the values linearly
and leaves nodata alone; the cache of any stack lands in
``plugins-data/geofisica/cache/<key>/``, never under the stack's folder; its
PNGs and manifest are the same bytes twice; nodata → alpha 0; every PNG and
the manifest are stamped (the source by digest, the acquisition by identity,
the ramp, the range, the percentiles and the scale as parameters); a UTM
origin survives to the millimetre. On the real data when it is on this
machine (skipped otherwise): the Basilica's 12 ``.ASC`` (6 slices at 92 × 50 m,
6 sections) and UA Ilici's Sector 1 (two GeoTIFFs, EPSG:25830), each built
twice with the same bytes; the times are printed (``-s``) for the report.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "profiles" / "geofisica" / "code"
COLORS = REPO / "profiles" / "geofisica" / "data" / "colors"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
core = importlib.import_module("geofisica_core")
_gt = importlib.import_module("geofisica_core.readers._geotiff")

try:
    import dtcstamp
except ImportError:  # pragma: no cover
    dtcstamp = None

ONEDRIVE = Path.home() / "Library" / "CloudStorage" / "OneDrive-CNR" / "0_RACCOLTA_CNR"
BASILICA = (ONEDRIVE / "Basilica Iuilia General" / "03_Documentation" / "05_Geophysical_survey"
            / "file-ascci-ert-fori-imperiali" / "sezioni-2D")
ILICI_S1 = (ONEDRIVE / "StratiGraph-grp - Documenti" / "WP 03 - Data Model and Knowledge Graph"
            / "WP 03 - Material" / "UA_Ilici_Augusta" / "GEORRADAR" / "Sector 1")

ERT_SCALE = {"from": [1, 255], "to": [0, 3500], "unit": "ohm.m",
             "source": "figure colour bar, risultati-fori.pdf p. 5", "confidence": "low"}
AT = "2026-11-19T12:00:00Z"
ACQ = {"resource_id": "acq:basilica-ert-2018", "kind": "acquisition"}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _png_rgba(path):
    """Decode one of the core's PNGs (8-bit RGBA, one IDAT, filter 0)."""
    import struct
    import zlib
    data = Path(path).read_bytes()
    pos, idat, w, h = 8, b"", None, None
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, w * 4 + 1)
    return raw[:, 1:].reshape(h, w, 4)


def _matrix_stack(folder):
    """Three headerless matrices like the Basilica's: two slices (cm in the
    name, 0 = nodata, grids of their own) and a section."""
    folder.mkdir(parents=True)
    rows_a = [[0 if (i == 0 and j < 2) else 1 + (i * 7 + j) * 6 for j in range(7)]
              for i in range(5)]
    rows_b = [[0 if j == 5 else 255 - (i * 6 + j) * 5 for j in range(6)] for i in range(4)]
    sec = [[0 if j == 0 else 10 * (j + i) for j in range(4)] for i in range(9)]
    for name, rows in (("100-150cm.ASC", rows_a), ("250-300cm.ASC", rows_b),
                       ("VERT-1-OK.ASC", sec)):
        (folder / name).write_text("\n".join(" ".join(str(v) for v in r) for r in rows) + "\n")
    return folder


def _declared(spec):
    if spec.orientation == "vertical":
        return {"length": 9.0, "depth": 2.0}
    return {"extent": (92.0, 50.0)}


@pytest.fixture
def plugins_data(tmp_path, monkeypatch):
    d = tmp_path / "plugins-data"
    monkeypatch.setenv("S3DGRAPHY_PLUGINS_DATA_DIR", str(d))
    return d


# ── ramps ─────────────────────────────────────────────────────────────────────

def test_the_ramps_in_the_core_are_the_packages_emc():
    names = sorted(p.stem for p in COLORS.glob("*.emc"))
    assert names == sorted(core.RAMPS) == ["grigio", "hot", "jet", "viridis"]
    for name in names:
        emc = core.load_emc(str(COLORS / (name + ".emc")))
        assert emc["color_mapping"] == core.RAMPS[name], "refresh RAMPS[%r] from %s.emc" % (
            name, name)
        assert emc["name"] and emc["name_it"]
        assert (core.ramp_lut(emc) == core.ramp_lut(name)).all()
    jet = core.ramp_lut("jet")
    assert jet.shape == (256, 3) and jet.dtype == np.uint8
    assert jet[0].tolist() == [0, 0, 127] and jet[255].tolist() == [127, 0, 0]
    assert core.ramp_lut("grigio")[128].tolist() == [128, 128, 128]
    assert core.DEFAULT_RAMP == {"gpr": "hot", "ert": "jet", "mag": "grigio"}


def test_a_ramp_colours_and_the_old_maps_do_not_move():
    amp = np.array([[0.0, 5.0], [10.0, -9999.0]], dtype=np.float32)
    mask = np.array([[True, True], [True, False]])
    hot = core.to_rgba8(amp, mask, 0.0, 10.0, "hot")
    assert hot[0, 0].tolist() == [0, 0, 0, 255] and hot[1, 0].tolist() == [255, 255, 255, 255]
    assert hot[1, 1, 3] == 0                                  # nodata → alpha 0
    gray = core.to_rgba8(amp, mask, 0.0, 10.0, "GRAY")
    assert gray[0, 1, :3].tolist() == [127, 127, 127]        # the old map, as before
    assert (core.to_rgba8(amp, mask, 0.0, 10.0, {"0": "#000000", "1": "#ff0000"})[1, 0, :3]
            == [255, 0, 0]).all()
    with pytest.raises(core.ColorError) as e:
        core.to_rgba8(amp, mask, 0.0, 10.0, "rainbow")
    assert "rainbow" in e.value.en and "sconosciuta" in e.value.it
    assert core.robust_range(np.array([])) == (0.0, 1.0)
    assert core.robust_range(np.array([3.0, 3.0])) == (3.0, 4.0)


def test_the_declared_value_scale():
    vs = core.check_value_scale(ERT_SCALE)
    assert vs["from"] == [1.0, 255.0] and vs["to"] == [0.0, 3500.0] and vs["confidence"] == "low"
    amp = np.array([[1.0, 128.0, 255.0, 0.0]], dtype=np.float32)
    mask = np.array([[True, True, True, False]])
    out = core.apply_value_scale(amp, mask, ERT_SCALE)
    assert out[0, 0] == 0.0 and out[0, 2] == 3500.0
    assert out[0, 1] == pytest.approx(127 * 3500 / 254)
    assert out[0, 3] == 0.0                                   # nodata untouched
    assert core.apply_value_scale(amp, mask, None) is amp
    with pytest.raises(core.ColorError) as e:
        core.check_value_scale({"from": [5, 5], "to": [0, 1]})
    assert e.value.it
    with pytest.raises(core.ColorError):
        core.check_value_scale({"to": [0, 1]})


# ── the cache ─────────────────────────────────────────────────────────────────

def test_the_cache_of_a_matrix_stack(tmp_path, plugins_data):
    folder = _matrix_stack(tmp_path / "ert-basilica")
    before = sorted(os.listdir(folder))
    m = core.build_stack_cache(str(folder), declared=_declared, method="ert",
                               value_scale=ERT_SCALE, acquisition=ACQ, at=AT,
                               software=[{"name": "test", "version": "1"}])
    out = Path(core.cache_root()) / m["cache_key"]
    assert str(out).startswith(str(plugins_data / "geofisica" / "cache"))
    assert (out / core.MANIFEST_NAME).is_file() and not m["reused"]
    assert sorted(os.listdir(folder)) == before                # nothing beside the source
    assert m["kind"] == "ascii_matrix" and m["colormap"] == "jet"
    assert m["ramp"] == core.RAMPS["jet"] and m["normalize"] == "STACK"
    assert m["stack"]["method"] == "ert" and m["stack"]["unit"] == "ohm.m"
    assert m["stack"]["value_scale"]["confidence"] == "low"
    ids = [e["geo_id"] for e in m["slices"]]
    assert ids == ["ert:ert-basilica#d1.000-1.500m", "ert:ert-basilica#d2.500-3.000m",
                   "ert:ert-basilica#sVERT1"]
    a, b, s = m["slices"]
    assert a["grid"]["nx"] == 7 and b["grid"]["nx"] == 6          # a grid per file
    assert a["grid"]["x_step"] == pytest.approx(92 / 7) and a["grid"]["y_step"] == 10.0
    assert s["orientation"] == "vertical" and s["line"] == "VERT1"
    assert a["vmin"] == b["vmin"] and 0.0 <= a["vmin"] < a["vmax"] <= 3500.0   # one range
    assert a["valid_cells"] == 33 and b["valid_cells"] == 20
    # nodata → alpha 0: matrix row 0 (top of the picture) is PNG row 0
    rgba = _png_rgba(out / a["raster"])
    assert rgba.shape == (5, 7, 4)
    assert rgba[0, 0, 3] == 0 and rgba[0, 1, 3] == 0 and rgba[0, 2, 3] == 255
    assert (rgba[..., 3] == 0).sum() == 2
    assert _png_rgba(out / b["raster"])[:, 5, 3].tolist() == [0, 0, 0, 0]
    # stamps: every PNG and the manifest
    for e in m["slices"]:
        png = out / e["raster"]
        assert e["png_digest"] == "sha256:" + _sha(png)
        st = json.loads((out / e["stamp"]).read_text())
        assert st["self"]["digest"] == e["png_digest"] and st["by"]["at"] == AT
        assert st["self"]["media_type"] == "image/png"
        assert st["how"]["dtc_kind"] == "format_conversion"
        src, acq = st["from"]
        assert src["digest"] == e["source_digest"] and src["label"] == Path(e["source"]).name
        assert acq == ACQ
        assert not any("/" in str(i.get("label", "")) for i in st["from"])
        p = st["how"]["parameters"]
        assert p["colormap"] == "jet" and p["ramp"] == core.RAMPS["jet"]
        assert p["clip_percentiles"] == [2.0, 98.0] and p["value_scale"]["to"] == [0.0, 3500.0]
        assert p["vmin"] == e["vmin"] and p["vmax"] == e["vmax"]
        assert st["how"]["software"][0] == {"name": "test", "version": "1"}
        assert st["how"]["software"][-1]["name"] == "geofisica_core"
        if dtcstamp is not None:
            assert dtcstamp.read_stamp(str(out / e["stamp"]))
    mst = json.loads((out / (core.MANIFEST_NAME + core.STAMP_SUFFIX)).read_text())
    assert mst["how"]["dtc_kind"] == "transformation" and len(mst["from"]) == 4
    assert mst["how"]["parameters"]["cache_key"] == m["cache_key"]
    assert "timing" not in json.loads((out / core.MANIFEST_NAME).read_text())
    assert core.load_manifest(str(out))["slices"][2]["geo_id"] == ids[2]


def test_the_cache_is_the_same_bytes_twice(tmp_path, plugins_data):
    folder = _matrix_stack(tmp_path / "s")
    kw = dict(declared=_declared, method="ert", value_scale=ERT_SCALE, at=AT)
    m1 = core.build_stack_cache(str(folder), out_dir=str(tmp_path / "c1"), **kw)
    m2 = core.build_stack_cache(str(folder), out_dir=str(tmp_path / "c2"), **kw)
    for name in os.listdir(tmp_path / "c1"):
        assert _sha(tmp_path / "c1" / name) == _sha(tmp_path / "c2" / name), name
    assert m1["cache_key"] == m2["cache_key"]
    # the same key in the same folder: reused, not rebuilt
    m3 = core.build_stack_cache(str(folder), out_dir=str(tmp_path / "c1"), **kw)
    assert m3["reused"] and m3["slices"] == m1["slices"]
    # another ramp, another key; a damaged PNG is rebuilt
    m4 = core.build_stack_cache(str(folder), out_dir=str(tmp_path / "c4"),
                                **dict(kw, colormap="grigio"))
    assert m4["cache_key"] != m1["cache_key"]
    (tmp_path / "c1" / m1["slices"][0]["raster"]).write_bytes(b"x")
    m5 = core.build_stack_cache(str(folder), out_dir=str(tmp_path / "c1"), **kw)
    assert not m5["reused"] and m5["slices"][0]["png_digest"] == m1["slices"][0]["png_digest"]


def test_the_cache_refuses_the_source_folder(tmp_path, plugins_data):
    folder = _matrix_stack(tmp_path / "s")
    for bad in (folder, folder / "cache", folder / "a" / "b"):
        with pytest.raises(core.CacheError) as e:
            core.build_stack_cache(str(folder), out_dir=str(bad), declared=_declared)
        assert "refused" in e.value.en and "rifiutata" in e.value.it
    assert sorted(os.listdir(folder)) == ["100-150cm.ASC", "250-300cm.ASC", "VERT-1-OK.ASC"]
    with pytest.raises(core.CacheError) as e:
        core.build_stack_cache(str(folder), normalize="FIXED", declared=_declared)
    assert "value_range" in e.value.en and e.value.it
    with pytest.raises(core.ColorError):
        core.build_stack_cache(str(folder), colormap="rainbow", declared=_declared)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(core.CacheError) as e:
        core.build_stack_cache(str(empty))
    assert e.value.it


def test_a_fixed_range_and_a_range_per_slice(tmp_path, plugins_data):
    folder = _matrix_stack(tmp_path / "s")
    m = core.build_stack_cache(str(folder), declared=_declared, method="ert",
                               value_scale=ERT_SCALE, normalize="FIXED",
                               value_range=(0, 3500), stamp=False)
    assert all((e["vmin"], e["vmax"]) == (0.0, 3500.0) for e in m["slices"])
    assert all(e["stamp"] is None for e in m["slices"]) and not m["stamped"]
    out = Path(core.cache_root()) / m["cache_key"]
    assert not list(out.glob("*.stamp.json"))
    m = core.build_stack_cache(str(folder), declared=_declared, normalize="SLICE", stamp=False)
    assert m["slices"][0]["vmin"] != m["slices"][1]["vmin"]


def test_a_geotiff_keeps_its_utm_origin_to_the_millimetre(tmp_path, plugins_data):
    e0, n0, step = 701756.963, 4234861.282, 0.1
    folder = tmp_path / "Sector 1"
    folder.mkdir()
    for name, k in (("mean_v2.tif", 1.0), ("sqmean_v2.tif", 1000.0)):
        rows = [[-3.4028234663852886e38 if (i + j) % 5 == 0 else k * (i + j) for j in range(8)]
                for i in range(6)]
        _gt.write_geotiff(str(folder / name), rows, affine=(e0, step, 0.0, n0, 0.0, -step),
                          epsg=25830, nodata=-3.4028234663852886e38)
    m = core.build_stack_cache(str(folder), normalize="SLICE", method="gpr", at=AT)
    assert m["kind"] == "geotiff" and m["colormap"] == "hot"
    g = m["georef"]
    assert g["epsg"] == 25830 and isinstance(g["origin_e"], float)
    assert abs(g["origin_e"] - e0) < 1e-3 and abs(g["origin_n"] - (n0 - 6 * step)) < 1e-3
    assert m["grid"]["x_min"] == pytest.approx(0.05)            # the grid stays local
    assert [e["geo_id"] for e in m["slices"]] == ["gpr:Sector 1#mean_v2",
                                                 "gpr:Sector 1#sqmean_v2"]
    assert m["slices"][1]["vmax"] > 100 * m["slices"][0]["vmax"]
    out = Path(core.cache_root()) / m["cache_key"]
    on_disk = json.loads((out / core.MANIFEST_NAME).read_text())
    assert on_disk["georef"]["origin_e"] == g["origin_e"]        # a double, not a float32
    assert _png_rgba(out / m["slices"][0]["raster"])[..., 3].min() == 0


def test_the_same_values_warning_and_a_declared_placement(tmp_path, plugins_data):
    folder = tmp_path / "s"
    folder.mkdir()
    rows = "\n".join(" ".join(str(1 + i + j) for j in range(4)) for i in range(3)) + "\n"
    (folder / "100-150cm.ASC").write_text(rows)
    (folder / "200-250cm.ASC").write_text(rows)
    place = {"origin_e": 291234.5678, "origin_n": 4640123.4321, "epsg": 32633,
             "rotation": 12.5, "source": "declared"}
    m = core.build_stack_cache(str(folder), declared={"extent": (4, 3)}, georef=place,
                               stamp=False)
    assert [w["code"] for w in m["warnings"]] == ["same_values"]
    assert m["warnings"][0]["it"]
    assert m["georef"] == place and m["slices"][1]["georef"] == place


def test_screen_captures_are_cached_through_the_hosts_decoder(tmp_path, plugins_data):
    folder = tmp_path / "Sector1_Alcudia"
    folder.mkdir()
    caps = {}
    for mm in (0, 5):
        rgb = np.zeros((40, 60, 3), dtype=np.uint8)
        rgb[10:30, 10:50] = (200 + mm, 60, 0)
        rgb[12, 12] = 0                                           # a black hole: nodata
        name = "Slice_-%04dmm.jpg" % mm if mm else "Slice_00000mm.jpg"
        (folder / name).write_bytes(b"not decoded by the core")
        caps[name] = rgb
    frame = core.declare_frame([10, 10, 49, 29], (-5, 5), (-2, 2))
    m = core.build_stack_cache(str(folder), kind="screenshot", declared={"frame": frame},
                               decode=lambda p: caps[os.path.basename(p)], at=AT)
    assert m["normalize"] == "AS_IS" and len(m["slices"]) == 2
    out = Path(core.cache_root()) / m["cache_key"]
    rgba = _png_rgba(out / m["slices"][0]["raster"])
    assert rgba.shape == (20, 40, 4)
    assert rgba[2, 2, 3] == 0 and rgba[5, 5].tolist() == [200, 60, 0, 255]
    assert rgba[-1, :, 3].max() == 0 and rgba[:, 0, 3].max() == 0   # the axis lines
    with pytest.raises(core.CacheError) as e:
        core.build_stack_cache(str(folder), kind="screenshot", declared={"frame": frame})
    assert "decode" in e.value.en and e.value.it


# ── the real data, where present ──────────────────────────────────────────────

_SECTIONS = {"VERT1": (50.0, 8.0), "VERT2": (92.0, 9.0), "VERT3": (92.0, 9.0),
             "VERT4": (92.0, 9.0), "VERT5": (50.0, 8.0), "VERT6": (50.0, 8.0)}


def _basilica(spec):
    if spec.orientation == "vertical":
        length, depth = _SECTIONS[spec.line]
        return {"length": length, "depth": depth}
    return {"extent": (92.0, 50.0)}


@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia data is not here")
def test_real_basilica_twelve_files_cached_twice(tmp_path, plugins_data):
    before = {p.name: p.stat().st_mtime for p in BASILICA.iterdir()}
    kw = dict(declared=_basilica, method="ert", value_scale=ERT_SCALE, acquisition=ACQ, at=AT)
    t0 = time.time()
    m1 = core.build_stack_cache(str(BASILICA), out_dir=str(tmp_path / "c1"), **kw)
    t1 = time.time()
    m2 = core.build_stack_cache(str(BASILICA), out_dir=str(tmp_path / "c2"), **kw)
    t2 = time.time()
    assert len(m1["slices"]) == 12
    assert [e["orientation"] for e in m1["slices"]] == ["horizontal"] * 6 + ["vertical"] * 6
    assert [e["line"] for e in m1["slices"][6:]] == ["VERT1", "VERT2", "VERT3", "VERT4",
                                                      "VERT5", "VERT6"]
    for e in m1["slices"]:
        assert e["valid_cells"] > 0 and Path(e["source"]).parent == BASILICA.resolve()
        st = json.loads((tmp_path / "c1" / e["stamp"]).read_text())
        assert st["self"]["digest"] == e["png_digest"] and st["from"][1] == ACQ
        if dtcstamp is not None:
            assert dtcstamp.read_stamp(str(tmp_path / "c1" / e["stamp"]))
    for name in os.listdir(tmp_path / "c1"):
        assert _sha(tmp_path / "c1" / name) == _sha(tmp_path / "c2" / name), name
    assert {p.name: p.stat().st_mtime for p in BASILICA.iterdir()} == before
    size = sum(p.stat().st_size for p in (tmp_path / "c1").iterdir())
    print("\nBASILICA 12 files: build %.2f s, again %.2f s, timing %s, cache %d files %d bytes, "
          "range %.0f-%.0f ohm.m" % (t1 - t0, t2 - t1, m1["timing"],
                                     len(os.listdir(tmp_path / "c1")), size,
                                     m1["slices"][0]["vmin"], m1["slices"][0]["vmax"]))


@pytest.mark.skipif(not ILICI_S1.is_dir(), reason="the UA Ilici data is not here")
def test_real_ilici_sector_1_cached_twice(tmp_path, plugins_data):
    kw = dict(method="gpr", normalize="SLICE", at=AT,
              acquisition={"resource_id": "acq:ilici-gpr-s1", "kind": "acquisition"})
    t0 = time.time()
    m1 = core.build_stack_cache(str(ILICI_S1), out_dir=str(tmp_path / "c1"), **kw)
    t1 = time.time()
    m2 = core.build_stack_cache(str(ILICI_S1), out_dir=str(tmp_path / "c2"), **kw)
    t2 = time.time()
    assert m1["kind"] == "geotiff" and len(m1["slices"]) == 2
    assert [e["geo_id"] for e in m1["slices"]] == ["gpr:Sector 1#mean_v2",
                                                  "gpr:Sector 1#sqmean_v2"]
    g = m1["georef"]
    assert g["epsg"] == 25830 and 701700 < g["origin_e"] < 701800
    assert 4234700 < g["origin_n"] < 4234900 and isinstance(g["origin_e"], float)
    assert m1["grid"]["x_step"] == pytest.approx(0.1)
    for name in os.listdir(tmp_path / "c1"):
        assert _sha(tmp_path / "c1" / name) == _sha(tmp_path / "c2" / name), name
    size = sum(p.stat().st_size for p in (tmp_path / "c1").iterdir())
    print("\nILICI Sector 1: build %.2f s, again %.2f s, timing %s, cache %d files %d bytes, "
          "origin %.3f %.3f" % (t1 - t0, t2 - t1, m1["timing"], len(os.listdir(tmp_path / "c1")),
                                size, g["origin_e"], g["origin_n"]))
