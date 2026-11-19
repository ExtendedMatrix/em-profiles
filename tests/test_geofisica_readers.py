"""MICRO-GEO04 · row G3 of the geophysics plan: readers A (``geofisica_core.readers``).

What is defended: a float GeoTIFF read without GDAL (the tags by a verified
copy of ``s3dgraphy.gis.geotiff``, the pixels by numpy), its nodata masked,
the int16 ceiling reported, the world file checked against the tags, the
absolute corner kept as a double; a headerless ASCII matrix with a declared
extent, ``0`` as nodata, its own grid, the declared orientation, non-square
pixels; a vertical section (rows along the profile, columns down from the
surface); an ESRI ASCII grid; the depth in centimetres in a name; the scan of
a folder of matrices and of GeoTIFFs (depth, section, product: never an
invented depth); two files with the same values reported. On the real data
when it is on this machine (skipped otherwise): the 12 ``.ASC`` of the
Basilica Iulia and the 22 ``.tif`` of UA Ilici with the shapes, nodata and
georeferences measured in §1 of the plan, and the two wrong copies of Ilici.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "profiles" / "geofisica" / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
core = importlib.import_module("geofisica_core")
_gt = importlib.import_module("geofisica_core.readers._geotiff")

ONEDRIVE = Path.home() / "Library" / "CloudStorage" / "OneDrive-CNR" / "0_RACCOLTA_CNR"
BASILICA = (ONEDRIVE / "Basilica Iuilia General" / "03_Documentation" / "05_Geophysical_survey"
            / "file-ascci-ert-fori-imperiali" / "sezioni-2D")
ILICI = (ONEDRIVE / "StratiGraph-grp - Documenti" / "WP 03 - Data Model and Knowledge Graph"
         / "WP 03 - Material" / "UA_Ilici_Augusta" / "GEORRADAR")

GDAL_NODATA = -3.4028234663852886e38
E0, N0 = 701756.963, 4234861.282                    # the corner of Ilici Sector 1


def _tif(path, rows, *, step=0.1, x0=E0, y0=N0, epsg=25830, nodata=GDAL_NODATA, tfw="centre"):
    _gt.write_geotiff(str(path), rows, affine=(x0, step, 0.0, y0, 0.0, -step), epsg=epsg,
                      nodata=nodata)
    if tfw:
        shift = step / 2 if tfw == "centre" else 0.0
        Path(str(path)[:-4] + ".tfw").write_text(
            "%r\n0.0\n0.0\n%r\n%r\n%r\n" % (step, -step, x0 + shift, y0 - shift))


def _field(ny, nx, k=0):
    return [[GDAL_NODATA if (i + j) % 7 == 0 else float(100 * i + j + k) for j in range(nx)]
            for i in range(ny)]


# ── the copy of s3dgraphy's reader ────────────────────────────────────────────

def test_the_geotiff_copy_is_s3dgraphys():
    spec = importlib.util.find_spec("s3dgraphy")
    if spec is None:
        pytest.skip("s3dgraphy not importable here")
    src = Path(spec.origin).parent / "gis" / "geotiff.py"
    mine = CODE / "geofisica_core" / "readers" / "_geotiff.py"
    assert hashlib.sha256(mine.read_bytes()).hexdigest() == \
        hashlib.sha256(src.read_bytes()).hexdigest(), "refresh the copy: cp s3dgraphy/gis/geotiff.py"


# ── depth in centimetres ──────────────────────────────────────────────────────

def test_depth_in_centimetres_and_mm_ranges():
    assert core.depth_from_name("100-150cm.ASC") == (1.0, 1.5)
    assert core.depth_from_name("550-600cm.ASC") == (5.5, 6.0)
    assert core.depth_from_name("0-500mm.png") == (0.0, 0.5)          # not 0–500 m
    assert core.depth_from_name("35cm.png") == (0.35, 0.35)
    assert core.depth_from_name("VERT-1-OK.ASC") is None
    assert core.depth_from_name("mean_v2.tif") is None


# ── GeoTIFF ───────────────────────────────────────────────────────────────────

def test_a_float_geotiff(tmp_path):
    rows = _field(6, 9)
    rows[2][3] = 32767.0
    p = tmp_path / "mean_v2.tif"
    _tif(p, rows)
    d = core.read_geotiff_slice(str(p))
    assert d.amp.shape == (6, 9) and d.amp.dtype == np.float32
    assert d.grid.x_step == pytest.approx(0.1) and d.grid.y_step == pytest.approx(0.1)
    assert d.grid.x_min == pytest.approx(0.05)                          # local, corner origin
    top = np.array(rows, dtype=np.float32)
    assert np.array_equal(d.mask, (top != np.float32(GDAL_NODATA))[::-1])  # row 0 = y_min (south)
    assert d.amp[3, 3] == 32767.0 and d.amp[5, 1] == top[0, 1]
    assert d.info["valid_cells"] == int(d.mask.sum())
    g = d.georef
    assert g["epsg"] == 25830 and g["rotation"] == 0.0
    assert g["origin_e"] == pytest.approx(E0, abs=1e-6)                 # a double, to the mm and beyond
    assert g["origin_n"] == pytest.approx(N0 - 6 * 0.1, abs=1e-6)
    assert isinstance(g["origin_e"], float)
    assert g["checks"]["tfw_agrees"] is True and g["checks"]["tfw"] == "mean_v2.tfw"
    sat = [w for w in d.warnings if w["code"] == "saturated"]
    assert len(sat) == 1 and sat[0]["cells"] == 1 and "32767" in sat[0]["en"] and sat[0]["it"]
    assert d.spec.product == "mean_v2" and not d.spec.depth_known


def test_the_fast_path_is_read_band(tmp_path):
    p = tmp_path / "x.tif"
    _tif(p, _field(5, 4, 3), tfw=None)
    d = core.read_geotiff_slice(str(p))
    band = np.asarray(_gt.read_band(str(p))["rows"], dtype=np.float32)[::-1]
    assert np.array_equal(d.amp[d.mask], band[d.mask])
    assert d.georef["checks"] == {"tfw": None}


def test_a_world_file_at_the_corner_is_said(tmp_path):
    p = tmp_path / "s.tif"
    _tif(p, _field(4, 4), tfw="corner")
    d = core.read_geotiff_slice(str(p))
    w = [w for w in d.warnings if w["code"] == "tfw_disagrees"]
    assert len(w) == 1 and "half a pixel" in w[0]["en"] and "mezzo pixel" in w[0]["it"]
    assert d.georef["origin_e"] == pytest.approx(E0)                     # the tags win


def test_a_geotiff_folder(tmp_path):
    f = tmp_path / "Sector 1"
    f.mkdir()
    _tif(f / "mean_v2.tif", _field(5, 6))
    _tif(f / "sqmean_v2.tif", _field(5, 6, 1))
    assert core.guess_kind(str(f)) == "geotiff"
    assert core.scan_stack(str(f))[0] == "image_stack"                  # auto unchanged (3DSC until G6)
    kind, specs = core.scan_stack(str(f), "geotiff")
    assert kind == "geotiff" and [s.product for s in specs] == ["mean_v2", "sqmean_v2"]
    assert all(not s.depth_known for s in specs)                        # never an invented depth
    assert core.geo_id("gpr", "Ilici-S1", specs[0]) == "gpr:Ilici-S1#mean_v2"
    geo = core.detect_georeference(str(f), "geotiff")
    assert geo["epsg"] == 25830 and geo["origin_e"] == pytest.approx(E0 + 0.05)
    assert geo["origin_n"] == pytest.approx(N0 - 5 * 0.1 + 0.05)        # the old convention: a centre


def test_the_same_values_are_said(tmp_path):
    for sec, k in (("Sector 12", 0), ("Sector 9", 0)):
        (tmp_path / sec).mkdir()
        _tif(tmp_path / sec / "sqmean_v2.tif", _field(4, 5, k), x0=E0 + len(sec))
    _tif(tmp_path / "Sector 9" / "mean_v2.tif", _field(4, 5, 9))
    data = [core.read_slice(s) for sec in ("Sector 12", "Sector 9")
            for s in core.scan_stack(str(tmp_path / sec), "geotiff")[1]]
    w = core.same_values(data)
    assert len(w) == 1 and w[0]["code"] == "same_values"
    assert w[0]["path"].endswith(os.path.join("Sector 9", "sqmean_v2.tif"))
    assert w[0]["same_as"].endswith(os.path.join("Sector 12", "sqmean_v2.tif"))
    assert "Sector 12/sqmean_v2.tif" in w[0]["en"] and "stessi valori" in w[0]["it"]


# ── ASCII matrices ────────────────────────────────────────────────────────────

M57 = "\n".join(" ".join("%6d" % (0 if (i in (0, 4) or j == 0) else 10 * i + j) for j in range(7))
                for i in range(5)) + "\n"


def test_a_headerless_matrix(tmp_path):
    p = tmp_path / "100-150cm.ASC"
    p.write_text(M57)
    kind, specs = core.scan_stack(str(tmp_path), "ascii_matrix")
    assert kind == "ascii_matrix" and specs[0].depth_top == 1.0 and specs[0].depth_bottom == 1.5
    d = core.read_slice(specs[0], extent=(92, 50))
    assert d.amp.shape == (5, 7) and (d.grid.nx, d.grid.ny) == (7, 5)
    assert d.grid.x_step == pytest.approx(92 / 7) and d.grid.y_step == pytest.approx(10.0)
    assert d.grid.width == pytest.approx(92) and d.grid.height == pytest.approx(50)
    assert not d.info["square_pixels"] and d.info["extent_declared"]
    assert d.amp[0, 3] == -9999.0 and not d.mask[0, 3]                  # 0 = nodata
    assert d.amp[1, 3] == 33.0                                          # row 0 = the picture's bottom
    assert d.amp[3, 2] == 12.0
    assert int((~d.mask).sum()) == 7 + 7 + 3
    assert d.georef is None and not d.warnings
    assert core.geo_id("ert", "BasilicaIulia", specs[0]) == "ert:BasilicaIulia#d1.000-1.500m"


def test_a_matrix_declared_otherwise(tmp_path):
    p = tmp_path / "m.asc"
    p.write_text(M57)
    d = core.read_ascii_matrix(str(p))
    assert d.grid.x_step == 1.0 and d.warnings[0]["code"] == "extent_not_declared"
    assert d.warnings[0]["en"] and d.warnings[0]["it"]
    t = core.read_ascii_matrix(str(p), step=0.5, row0="bottom", transpose=True, nodata=None)
    assert t.amp.shape == (7, 5) and t.amp[3, 2] == 23.0 and t.mask.all()


def test_a_ragged_matrix_is_refused_with_a_sentence(tmp_path):
    p = tmp_path / "bad.asc"
    p.write_text("1 2 3\n4 5\n")
    with pytest.raises(ValueError, match="bad.asc"):
        core.read_ascii_matrix(str(p))


def test_an_esri_ascii_grid(tmp_path):
    p = tmp_path / "mag.asc"
    p.write_text("ncols 3\nnrows 2\nxllcorner 701000.5\nyllcorner 4234000.25\ncellsize 0.5\n"
                 "NODATA_value -9999\n1 2 3\n4 -9999 6\n")
    (tmp_path / "mag.prj").write_text('PROJCS["x",AUTHORITY["EPSG","25830"]]')
    d = core.read_ascii_matrix(str(p), extent=(1, 1))                   # the header wins
    assert d.amp.shape == (2, 3) and d.grid.x_step == 0.5
    assert d.amp[1, 0] == 1.0 and not d.mask[0, 1]
    assert d.georef["origin_e"] == 701000.5 and d.georef["origin_n"] == 4234000.25
    assert d.georef["epsg"] == 25830


def test_a_vertical_section(tmp_path):
    # 6 positions along the line (rows), 4 cells down from the surface (columns)
    body = "\n".join(" ".join(str(100 * i + 10 * (j + 1)) for j in range(4)) for i in range(6))
    (tmp_path / "VERT-1-OK.ASC").write_text(body + "\n")
    (tmp_path / "250-300cm.ASC").write_text(M57)
    (tmp_path / "100-150cm.ASC").write_text(M57)
    assert core.guess_kind(str(tmp_path)) == "ascii_matrix"
    _, specs = core.scan_stack(str(tmp_path), "ascii_matrix")
    assert [os.path.basename(s.path) for s in specs] == ["100-150cm.ASC", "250-300cm.ASC",
                                                         "VERT-1-OK.ASC"]
    v = specs[2]
    assert v.orientation == "vertical" and v.line == "VERT1" and not v.depth_known
    d = core.read_slice(v, length=50, depth=8, extent=(92, 50))
    assert d.amp.shape == (4, 6)                                        # rows = depth, cols = along
    assert d.amp[3, 0] == 10.0 and d.amp[0, 0] == 40.0                  # top row = the surface
    assert d.amp[3, 5] == 510.0
    assert d.grid.x_step == pytest.approx(50 / 6) and d.grid.y_step == pytest.approx(2.0)
    assert d.grid.y_min == pytest.approx(-7.0) and d.grid.y_max == pytest.approx(-1.0)
    assert (v.depth_top, v.depth_bottom) == (0.0, 8.0)
    assert core.geo_id("ert", "BasilicaIulia", v) == "ert:BasilicaIulia#sVERT1"
    r = core.read_ascii_section(str(tmp_path / "VERT-1-OK.ASC"), reverse=True)
    assert r.amp[3, 0] == 510.0 and r.warnings[0]["code"] == "section_not_declared"
    assert not r.spec.depth_known


def test_line_from_name():
    assert [core.line_from_name(n) for n in ("VERT-1-OK.ASC", "VERT3-OK.ASC", "sez_2.asc",
                                             "Profile 04.asc", "100-150cm.ASC", "convert9.asc")] == \
        ["VERT1", "VERT3", "SEZ2", "PROFILE4", None, None]


# ── the real data (only where it is) ─────────────────────────────────────────

BASILICA_SHAPES = {  # §1 of the plan: rows × columns, cells at 0
    "100-150cm.ASC": (342, 721, 3207), "250-300cm.ASC": (343, 720, 2146),
    "300-350cm.ASC": (340, 721, 2571), "350-400cm.ASC": (350, 722, 2665),
    "450-500cm.ASC": (349, 721, 1571), "550-600cm.ASC": (349, 720, 2134),
    "VERT-1-OK.ASC": (1129, 171, 3029), "VERT-2-OK.ASC": (1114, 111, 3667),
    "VERT3-OK.ASC": (989, 99, 3439), "VERT4-OK.ASC": (1000, 99, 3292),
    "VERT5-OK.ASC": (722, 110, 2614), "VERT6-OK.ASC": (722, 109, 1781)}
SECTIONS = {"VERT1": (50, 8), "VERT2": (92, 9), "VERT3": (92, 9), "VERT4": (92, 9),
            "VERT5": (50, 8), "VERT6": (50, 8)}


@pytest.mark.skipif(not BASILICA.is_dir(), reason="the Basilica Iulia ERT is not on this machine")
def test_the_basilica_iulia_ert():
    assert core.guess_kind(str(BASILICA)) == "ascii_matrix"
    _, specs = core.scan_stack(str(BASILICA), "ascii_matrix")
    assert len(specs) == 12
    assert [s.orientation for s in specs] == ["horizontal"] * 6 + ["vertical"] * 6
    assert [s.depth_top for s in specs[:6]] == [1.0, 2.5, 3.0, 3.5, 4.5, 5.5]
    for s in specs:
        rows, cols, zeros = BASILICA_SHAPES[os.path.basename(s.path)]
        if s.orientation == "vertical":
            d = core.read_slice(s, length=SECTIONS[s.line][0], depth=SECTIONS[s.line][1])
            assert d.amp.shape == (cols, rows)                          # depth × along
            assert d.grid.width == pytest.approx(SECTIONS[s.line][0])
            assert s.depth_bottom == pytest.approx(SECTIONS[s.line][1])
            assert core.geo_id("ert", "BasilicaIulia", s) == "ert:BasilicaIulia#s" + s.line
        else:
            d = core.read_slice(s, extent=(92, 50))
            assert d.amp.shape == (rows, cols)
            assert d.grid.width == pytest.approx(92) and d.grid.height == pytest.approx(50)
            assert not d.info["square_pixels"]                          # 0.128 × 0.146 m
        assert (d.info["rows"], d.info["cols"]) == (rows, cols)
        assert int((~d.mask).sum()) == zeros
        valid = d.amp[d.mask]
        assert valid.min() >= 1 and valid.max() <= 255                 # colour indices, not Ω·m
        assert not d.warnings and d.read_seconds < 1.0


ILICI_SECTORS = {  # §1 / gpr_inspection.txt: (rows, cols), valid cells
    "Sector 1": ((588, 747), 179381), "Sector 2": ((1459, 527), 329861),
    "Sector 3": ((1739, 722), 793441), "Sector 4-1": ((450, 197), 56118),
    "Sector 4-2": ((587, 352), 157247), "Sector 5-1": ((203, 851), 158787),
    "Sector 5-2": ((350, 992), 242984), "Sector 7": ((960, 592), 430970),
    "Sector 9": ((878, 253), 117075), "Sector 11": ((257, 458), 63705),
    "Sector 12": ((537, 391), 152446)}


@pytest.mark.skipif(not ILICI.is_dir(), reason="the UA Ilici GPR is not on this machine")
def test_ua_ilici_geotiffs():
    data = []
    for sec, (shape, valid) in sorted(ILICI_SECTORS.items()):
        folder = ILICI / sec
        assert core.guess_kind(str(folder)) == "geotiff"
        _, specs = core.scan_stack(str(folder), "geotiff")
        assert [s.product for s in specs] == ["mean_v2", "sqmean_v2"]
        for s in specs:
            d = core.read_slice(s)
            data.append(d)
            if (sec, s.product) == ("Sector 9", "sqmean_v2"):            # Sector 12's, see below
                assert d.amp.shape == ILICI_SECTORS["Sector 12"][0]
                continue
            assert d.amp.shape == shape and d.info["valid_cells"] == valid
            g = d.georef
            assert g["epsg"] == 25830 and g["rotation"] == 0.0
            assert d.grid.x_step == pytest.approx(0.1) and d.grid.y_step == pytest.approx(0.1)
            assert 701500 < g["origin_e"] < 701900 and 4234600 < g["origin_n"] < 4235000
            if (sec, s.product) == ("Sector 4-2", "sqmean_v2"):
                assert g["checks"]["tfw"] is None                       # the GeoKeys are enough
            else:
                assert g["checks"]["tfw_agrees"] is True
            sat = [w for w in d.warnings if w["code"] == "saturated"]
            assert bool(sat) == (sec in ("Sector 5-1", "Sector 7") and s.product == "mean_v2")
    assert len(data) == 22
    s1 = next(d for d in data if "Sector 1" + os.sep in d.spec.path)
    assert s1.georef["origin_e"] == pytest.approx(701756.963, abs=1e-3)  # the tiepoint corner
    assert s1.georef["origin_n"] == pytest.approx(4234861.282 - 58.8, abs=1e-3)
    pairs = {(os.path.relpath(w["path"], ILICI), os.path.relpath(w["same_as"], ILICI))
             for w in core.same_values(data)}
    assert pairs == {(os.path.join("Sector 5-2", "sqmean_v2.tif"), os.path.join("Sector 5-2", "mean_v2.tif")),
                     (os.path.join("Sector 9", "sqmean_v2.tif"), os.path.join("Sector 12", "sqmean_v2.tif"))}
