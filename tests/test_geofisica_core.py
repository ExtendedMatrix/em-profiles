"""MICRO-GEO03 · row G2 of the geophysics plan: the core moved (``geofisica_core``).

What is defended: the old 3D-survey-collection ``importer/gpr_core.py`` moved
into ``profiles/geofisica/code/geofisica_core/`` divided into modules keeps
its public API (the names ``import_gpr.py`` uses) and its results — on a
synthetic Tivoli-like CSV stack the PNGs are the old core's pixel for pixel
and byte for byte, the manifest v2 reduced to the v1 fields is the old v1;
v1 manifests are read back as v2; the identities (``gpr:`` unchanged,
``ert:``, ``mag:``, ``#s``, ``#<product>``); and every PNG and manifest the
core writes leaves stamped (``<file>.stamp.json``, read by ``dtcstamp``, its
inputs the source files by digest). The golden was made once from the old
core (``fixtures/geofisica/make_golden.py``); when the old file is still
beside this repository the test also runs it live.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "profiles" / "geofisica" / "code"
FIX = Path(__file__).resolve().parent / "fixtures" / "geofisica"
GOLDEN = json.loads((FIX / "golden_gpr_core.json").read_text(encoding="utf-8"))
OLD = REPO.parent / "3D-survey-collection" / "importer" / "gpr_core.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geofisica_synth import ilici_like, tivoli_like  # noqa: E402

if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
core = importlib.import_module("geofisica_core")

CLOCK = ("build_seconds", "parse_seconds", "png_seconds")


def _pixels(path):
    b = Path(path).read_bytes()
    i, idat = 8, b""
    while i < len(b):
        n, = struct.unpack(">I", b[i:i + 4])
        if b[i + 4:i + 8] == b"IDAT":
            idat += b[i + 8:i + 8 + n]
        i += 12 + n
    return hashlib.sha256(zlib.decompress(idat)).hexdigest()


def _neutral(manifest, work):
    m = {k: v for k, v in core.as_v1(manifest).items() if k not in CLOCK}
    m["source_folder"] = "<stack>"
    real = os.path.realpath(str(work))
    for e in m["slices"]:
        for k in ("source", "raster"):
            e[k] = e[k].replace(real, "<work>")
    return m


@pytest.fixture
def work(tmp_path):
    tivoli_like(str(tmp_path / "stack"))
    ilici_like(str(tmp_path / "ilici"))
    return tmp_path


# ── the API ───────────────────────────────────────────────────────────────────

def test_the_api_import_gpr_uses_is_there():
    for name in ("build_cache_steps", "build_image_manifest", "load_manifest", "detect_georeference",
                 "is_absolute", "propose_shift", "scan_stack", "MANIFEST_NAME"):
        assert hasattr(core, name), name
    assert core.MANIFEST_NAME == "gpr_stack.json"
    # everything the old module defined at its top level is still a name of the core
    old_names = {"NODATA", "MANIFEST_VERSION", "CSV_EXT", "IMG_EXT", "GridSpec", "SliceSpec", "document_id",
                 "SliceData", "depth_from_name", "parse_csv_header", "read_csv_header", "repair_chunk",
                 "RepairedReader", "read_csv_slice", "_viridis_lut", "COLORMAPS", "to_rgba8", "write_png",
                 "percentile_range", "build_cache", "read_world_file", "world_file_for",
                 "extent_from_world_file", "image_size", "prj_file_for", "epsg_from_prj",
                 "ABSOLUTE_COORD_THRESHOLD"}
    assert not [n for n in old_names if not hasattr(core, n)]


def test_the_core_needs_neither_bpy_nor_s3dgraphy():
    imports = re.compile(r"^\s*(?:from|import)\s+(bpy|s3dgraphy)\b", re.M)
    for f in CODE.joinpath("geofisica_core").rglob("*.py"):
        assert not imports.search(f.read_text(encoding="utf-8")), f
        assert "dtcstamp" not in f.name                                   # 3DSC carries no copy of it


# ── depth, header, repair ─────────────────────────────────────────────────────

def test_depth_from_name_as_before():
    for name, want in GOLDEN["depth_from_name"].items():
        got = core.depth_from_name(name)
        assert (list(got) if got else None) == want, name


def test_the_header_in_latin1():
    assert core.parse_csv_header("X \xb1 0.0500m, Y \xb1 0.0400m, Z \xb1 -1.9000m, Depth \xb1 1.9000m, A") == {
        "x_step": 0.05, "y_step": 0.04, "z": -1.9, "depth": 1.9}


@pytest.mark.parametrize("chunk", [5, 7, 13, 64, 1 << 22])
def test_repaired_reader_any_chunk_boundary(work, chunk):
    path = sorted((work / "stack").iterdir())[0]
    raw = path.read_bytes()
    want = core.repair_chunk(raw.split(b"\n", 1)[1])
    with open(path, "rb") as fh:
        got = core.RepairedReader(fh, chunk=chunk).read()
    assert got == want and b"\r" not in got and b",\n" not in got


def test_read_csv_slice_and_the_fast_path(work):
    paths = sorted((work / "stack").iterdir())
    grid, amp, mask, _ = core.read_csv_slice(str(paths[0]))
    assert (grid.nx, grid.ny, grid.x_step, grid.y_step) == (37, 23, 0.05, 0.05)
    assert amp.dtype == np.float32 and amp.shape == (23, 37)
    assert int(mask.sum()) == GOLDEN["manifest_csv"]["GRAY/STACK"]["slices"][0]["valid_cells"]
    g2, amp2, mask2, _ = core.read_csv_slice(str(paths[1]), grid)
    assert g2 is grid and amp2.shape == amp.shape
    with pytest.raises(ValueError):
        core.read_csv_slice(str(paths[1]), core.GridSpec(10, 10, 0, 0, 0.05, 0.05))


# ── the golden: the old core's results ───────────────────────────────────────

@pytest.mark.parametrize("config", sorted(GOLDEN["png"]))
def test_pngs_are_the_old_cores(work, config):
    cm, nm = config.split("/")
    out = work / ("cache_%s_%s" % (cm, nm))
    m = core.build_cache(str(work / "stack"), str(out), colormap=cm, normalize=nm)
    for e, g in zip(m["slices"], GOLDEN["png"][config]):
        assert e["raster"] == g["raster"]
        assert _pixels(out / e["raster"]) == g["pixels"], e["raster"]
        if zlib.ZLIB_RUNTIME_VERSION == GOLDEN["zlib"]:                # bytes: the same zlib
            assert hashlib.sha256((out / e["raster"]).read_bytes()).hexdigest() == g["bytes"]
    assert _neutral(m, work) == GOLDEN["manifest_csv"][config]


def test_image_manifest_is_the_old_cores(work):
    m = core.build_image_manifest(str(work / "ilici"), str(work / "cache_img"))
    assert _neutral(m, work) == GOLDEN["manifest_image"]
    assert m["georef"]["epsg"] == 25830 and m["georef"]["origin_e"] == GOLDEN["georef_image"]["origin_e"]


def test_georeference_and_shift_as_before(work):
    assert core.detect_georeference(str(work / "stack")) == GOLDEN["georef_csv"]
    assert core.detect_georeference(str(work / "ilici")) == GOLDEN["georef_image"]
    assert core.is_absolute(701806.741, 4234824.081) is GOLDEN["shift"]["absolute"]
    assert core.is_absolute(12.0, 30.0) is GOLDEN["shift"]["local"]
    assert list(core.propose_shift(701806.741, 4234824.081, 10.0)) == GOLDEN["shift"]["proposed"]


@pytest.mark.skipif(not OLD.is_file(), reason="the old 3DSC gpr_core.py is not beside this repository")
def test_live_against_the_old_core(work):
    spec = importlib.util.spec_from_file_location("_old_gpr_core", str(OLD))
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old                                         # its dataclasses look it up
    try:
        spec.loader.exec_module(old)
    finally:
        sys.modules.pop(spec.name, None)
    a = old.build_cache(str(work / "stack"), str(work / "old"), colormap="VIRIDIS")
    b = core.build_cache(str(work / "stack"), str(work / "new"), colormap="VIRIDIS")
    for ea, eb in zip(a["slices"], b["slices"]):
        assert (work / "old" / ea["raster"]).read_bytes() == (work / "new" / eb["raster"]).read_bytes()
    strip = lambda m: {k: v for k, v in m.items() if k not in CLOCK + ("source_folder",)}  # noqa: E731
    assert strip(core.as_v1(b)) == strip(a)


# ── manifest v2, and v1 read back ────────────────────────────────────────────

def test_manifest_v2_says_more(work):
    m = core.build_cache(str(work / "stack"), str(work / "c"), method="gpr", unit="V")
    assert m["manifest_version"] == 2 and m["generator"] == "geofisica_core " + core.__version__
    assert m["stack"] == {"name": "stack", "method": "gpr", "quantity": "ampiezza", "unit": "V",
                          "value_scale": None}
    e = m["slices"][1]
    assert e["geo_id"] == e["document_id"] == "gpr:stack#d0.100-0.200m"
    assert e["orientation"] == "horizontal" and e["stamp"] == e["raster"] + ".stamp.json"
    assert core.load_manifest(str(work / "c")) == json.loads((work / "c" / "gpr_stack.json").read_text())


def test_a_v1_manifest_reads_as_v2(tmp_path):
    v1 = dict(GOLDEN["manifest_csv"]["GRAY/STACK"], source_folder="/data/CS07")
    (tmp_path / "gpr_stack.json").write_text(json.dumps(v1))
    m = core.load_manifest(str(tmp_path))
    assert m["manifest_version"] == 2 and m["upgraded_from"] == 1 and m["stamped"] is False
    assert m["stack"]["method"] == "gpr" and m["stack"]["name"] == "CS07"
    assert [e["geo_id"] for e in m["slices"]] == [e["document_id"] for e in v1["slices"]]
    assert core.as_v1(m) == v1                                            # nothing lost on the way
    assert core.load_manifest(str(tmp_path / "nowhere")) is None


# ── identity ─────────────────────────────────────────────────────────────────

def test_identities():
    h = core.SliceSpec("x/slice.csv", 1.0, 1.5)
    assert core.document_id("/d/CS07/", h) == "gpr:CS07#d1.000-1.500m"            # unchanged
    assert core.geo_id("ert", "BasilicaIulia", h) == "ert:BasilicaIulia#d1.000-1.500m"
    assert core.geo_id("MAG", "S", h).startswith("mag:S#d")
    v = core.SliceSpec("VERT3-OK.ASC", 0.0, 9.0, orientation="vertical", line="VERT 3")
    assert core.geo_id("ert", "BasilicaIulia", v) == "ert:BasilicaIulia#sVERT_3"
    p = core.SliceSpec("Sector 1/mean_v2.tif", None, None, product="mean_v2")
    assert core.geo_id("gpr", "Ilici-S1", p) == "gpr:Ilici-S1#mean_v2"
    assert p.label == "mean_v2" and p.depth_mid == 0.0 and not p.depth_known
    assert core.Stack(folder="f", kind="csv_grid", method="ert").quantity == "resistivita"
    assert core.Slice is core.SliceSpec


# ── the stamp (G-5) ──────────────────────────────────────────────────────────

def test_every_png_and_the_manifest_leave_stamped(work):
    dtcstamp = pytest.importorskip("dtcstamp")
    out = work / "c"
    m = core.build_cache(str(work / "stack"), str(out), software=[{"name": "3D Survey Collection",
                                                                    "version": "test"}])
    sources = sorted((work / "stack").iterdir())
    digest = {p.name: dtcstamp.file_digest(str(p)) for p in sources}
    for e in m["slices"]:
        st = dtcstamp.read_stamp(str(out / e["stamp"]))
        assert st["self"]["digest"] == dtcstamp.file_digest(str(out / e["raster"]))
        assert st["self"]["media_type"] == "image/png" and st["self"]["label"] == e["geo_id"]
        assert st["self"]["measures"]["size_bytes"] == e["png_bytes"]
        (src,) = st["from"]
        assert src["digest"] == digest[src["label"]] and src["label"] == os.path.basename(e["source"])
        assert st["how"]["dtc_kind"] == "format_conversion" and st["how"]["parameters"]["vmin"] == e["vmin"]
        assert [s["name"] for s in st["how"]["software"]] == ["3D Survey Collection", "geofisica_core"]
        assert "operator" not in st["by"]
        text = (out / e["stamp"]).read_text(encoding="utf-8")
        assert str(work) not in text and os.path.realpath(str(work)) not in text      # never a path
    st = dtcstamp.read_stamp(str(out / "gpr_stack.json.stamp.json"))
    assert st["self"]["digest"] == dtcstamp.file_digest(str(out / "gpr_stack.json"))
    assert sorted(f["digest"] for f in st["from"]) == sorted(digest.values())


def test_the_image_manifest_is_stamped_with_its_images(work):
    dtcstamp = pytest.importorskip("dtcstamp")
    out = work / "ci"
    core.build_image_manifest(str(work / "ilici"), str(out))
    st = dtcstamp.read_stamp(str(out / "gpr_stack.json.stamp.json"))
    assert len(st["from"]) == 4 and st["how"]["parameters"]["epsg"] == 25830
    assert sorted(os.listdir(out)) == ["gpr_stack.json", "gpr_stack.json.stamp.json"]  # images untouched


def test_stamp_false_writes_none(work):
    out = work / "n"
    m = core.build_cache(str(work / "stack"), str(out), stamp=False)
    assert m["stamped"] is False and all(e["stamp"] is None for e in m["slices"])
    assert not [f for f in os.listdir(out) if f.endswith(".stamp.json")]


def test_without_dtcstamp_the_same_record(work, monkeypatch):
    from geofisica_core import stamp as st
    png = work / "a.png"
    png.write_bytes(b"\x89PNG fake")
    with_lib = st.make_stamp(str(png), inputs=[str(sorted((work / "stack").iterdir())[0])], at="2026-11-19T00:00:00Z")
    monkeypatch.setattr(st, "_dtc", None)
    rec = st.stamp_artifact(str(png), inputs=[str(sorted((work / "stack").iterdir())[0])],
                            at="2026-11-19T00:00:00Z")
    assert rec == with_lib
    assert json.loads((work / "a.png.stamp.json").read_text(encoding="utf-8")) == rec
    try:
        from s3dgraphy.em.stamps import resource_id_for
    except Exception:                                                     # noqa: BLE001
        return
    assert rec["self"]["resource_id"] == resource_id_for(rec["self"]["digest"])   # one identity


def test_an_embedded_copy_names_its_commit(tmp_path, monkeypatch):
    """Row G6: 3DSC embeds the core with ``SOURCE.json`` beside it; the core's
    software line then carries the em-profiles commit (the stamp names the
    exact code). Without the file (the installed package) no commit."""
    assert core.stamp.core_line() == {"name": "geofisica_core", "version": core.__version__}
    import shutil
    copy = tmp_path / "geofisica_core"
    shutil.copytree(CODE / "geofisica_core", copy,
                    ignore=shutil.ignore_patterns("__pycache__", SOURCE_FILE))
    (copy / SOURCE_FILE).write_text(json.dumps({"repo": "em-profiles", "commit": "0123456789abcdef"}),
                                    encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "geofisica_core_embedded", copy / "__init__.py", submodule_search_locations=[str(copy)])
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    assert mod.stamp.vendored_source()["repo"] == "em-profiles"
    assert mod.stamp.core_line() == {"name": "geofisica_core", "version": mod.__version__,
                                     "commit": "0123456"}
    (copy / SOURCE_FILE).write_text("not json", encoding="utf-8")
    assert mod.stamp.vendored_source() == {} and "commit" not in mod.stamp.core_line()


SOURCE_FILE = "SOURCE.json"
