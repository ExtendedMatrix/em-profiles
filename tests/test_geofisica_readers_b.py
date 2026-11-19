"""MICRO-GEO05 · row G4 of the geophysics plan: readers B (``geofisica_core.readers``).

What is defended: a volume of points ``X Y Z V`` read as one plane per
distinct value of its plane column (a shared grid, the missing points
nodata, two points in a cell counted, ``row0="top"`` for index coordinates,
a product name and no invented depth); a file of blocks ``line N`` read as a
vertical section (three-decimal coordinates do not drift into an empty
column); a folder told apart (matrices, volumes, lines); a stack of screen
captures: the plot box measured by its axes and ticks, its grid, the crop
with black and the axes as nodata, the manifest that describes the stack
without rewriting a capture (the frame, the declared origin in doubles, the
captures by digest in its stamp, a cache folder under the captures refused),
the frame held against a GeoTIFF of the same sector. On the real data when it
is on this machine (skipped otherwise): the four volumes and ``VERT3-OK.XYZ``
of the Basilica Iulia, each under a second, and the 601 captures of UA Ilici
``Sector1_Alcudia`` — a 5 mm step, one frame on every capture, georeferenced
at 701806.741 / 4234824.081 (EPSG:25830), within half a metre of the
Sector 1 GeoTIFF.
"""
from __future__ import annotations

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
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
core = importlib.import_module("geofisica_core")
_gt = importlib.import_module("geofisica_core.readers._geotiff")

ONEDRIVE = Path.home() / "Library" / "CloudStorage" / "OneDrive-CNR" / "0_RACCOLTA_CNR"
BASILICA = ONEDRIVE / "Basilica Iuilia General" / "03_Documentation" / "05_Geophysical_survey"
VOLUMES = BASILICA / "file-ascci-ert-fori-imperiali" / "volumi-ert-specchiati"
ILICI = (ONEDRIVE / "StratiGraph-grp - Documenti" / "WP 03 - Data Model and Knowledge Graph"
         / "WP 03 - Material" / "UA_Ilici_Augusta" / "GEORRADAR")
ALCUDIA = ILICI / "Sector1_Alcudia"
ORIGIN = (701806.741, 4234824.081)                  # the overlay's local (0, 0)
FRAME_PX = [610, 170, 1303, 715]


# ── volumes ───────────────────────────────────────────────────────────────────

def _volume(path, planes=(45.0, 50.0), nx=6, ny=4, skip=((50.0, 2, 1),), dup=None):
    """An XYZV file the Basilica's way: X = row index, Z = column index, E notation, CRLF."""
    rows = []
    for p in planes:
        for r in range(ny):
            for c in range(nx):
                if (p, r, c) in skip:
                    continue
                v = 0.0 if (r, c) == (0, 0) else 10 * r + c + p
                rows.append("  %.15E  %.15E  %.15E  %.15E" % (r, p, c, v))
    if dup:
        rows.append("  %.15E  %.15E  %.15E  %.15E" % dup)
    Path(path).write_bytes(("\r\n".join(rows) + "\r\n").encode("ascii"))


def test_a_volume_is_read_plane_by_plane(tmp_path):
    f = tmp_path / "3D-1.ASC"
    _volume(f)
    assert core.is_points_file(str(f))
    planes = core.read_xyzv(str(f), plane="y", x="z", y="x", row0="top")
    assert [d.spec.product for d in planes] == ["3D-1_y45", "3D-1_y50"]
    assert [d.spec.plane for d in planes] == [45.0, 50.0]
    for d in planes:
        assert d.amp.shape == (4, 6)                              # rows = X, columns = Z
        assert not d.spec.depth_known                             # Y is not a depth: nobody said
        assert d.info["derived"] and d.spec.kind == "xyzv"
        top_row = d.amp[-1]                                       # row0="top": X = 0 on top
        assert not d.mask[-1, 0]                                  # 0 = nodata
        assert top_row[1] == pytest.approx(1 + d.spec.plane)
        assert d.amp[0, 5] == pytest.approx(10 * 3 + 5 + d.spec.plane)
    y50 = planes[1]
    assert y50.info["empty_cells"] == 1 and not y50.mask[4 - 1 - 2, 1]   # the missing point
    assert planes[0].grid.matches(planes[1].grid)                 # one grid for the file
    one = core.read_xyzv(str(f), plane="y", x="z", y="x", row0="top", only=50)
    assert len(one) == 1 and one[0].spec.plane == 50.0
    with pytest.raises(ValueError, match="no plane"):
        core.read_xyzv(str(f), only=7)


def test_two_points_in_one_cell_are_said(tmp_path):
    f = tmp_path / "v.asc"
    _volume(f, planes=(5.0,), skip=(), dup=(1, 5.0, 1, 99.0))
    d = core.read_xyzv(str(f), plane="y", x="z", y="x")[0]
    assert d.info["duplicates"] == 1
    w = d.warnings[0]
    assert w["code"] == "points_in_one_cell" and "punti" in w["it"] and "points" in w["en"]
    assert d.amp[1, 1] == pytest.approx(99.0)                     # the last one kept


def test_a_folder_of_volumes(tmp_path):
    vol = tmp_path / "volumi"
    vol.mkdir()
    _volume(vol / "3D-1.ASC")
    _volume(vol / "3D-2.ASC", planes=(35.0,))
    mat = tmp_path / "sezioni"
    mat.mkdir()
    (mat / "100-150cm.ASC").write_text("\n".join(" ".join("7" for _ in range(30))
                                                 for _ in range(4)) + "\n")
    assert core.guess_kind(str(vol)) == "xyzv"
    assert core.guess_kind(str(mat)) == "ascii_matrix"
    kind, specs = core.scan_stack(str(vol), "xyzv")
    assert kind == "xyzv"
    assert [s.product for s in specs] == ["3D-1_y45", "3D-1_y50", "3D-2_y35"]
    d = core.read_slice(specs[1], x="z", y="x", row0="top")
    assert d.spec is specs[1] and d.spec.plane == 50.0
    assert core.geo_id("ert", "volumi", specs[2]) == "ert:volumi#3D-2_y35"


# ── blocks «line N» ───────────────────────────────────────────────────────────

def _lines(path, n_along=5, n_depth=4, length=0.37248, depth_step=0.01):
    """``VERT3-OK.XYZ`` the way it is written: three decimals, a step that is not."""
    out = []
    for i in range(n_along):
        out.append("line %10d" % i)
        x = round(i * length / (n_along - 1), 3)
        for j in range(n_depth):
            v = 0.0 if i in (0, n_along - 1) else float(10 * i + j)
            out.append("%12.3f %12.3f %12.3f" % (x, j * depth_step, v))
    Path(path).write_bytes(("\r\n".join(out) + "\r\n").encode("ascii"))


def test_a_section_in_blocks(tmp_path):
    f = tmp_path / "VERT3-OK.XYZ"
    _lines(f, n_along=40, length=3.6)                             # 0.092307… written as 0.092
    assert core.is_points_file(str(f))
    d = core.read_xyz_lines(str(f))
    assert d.spec.orientation == "vertical" and d.spec.line == "VERT3"
    assert d.amp.shape == (4, 40)                                 # depth × along
    assert d.info["empty_cells"] == 0 and d.info["blocks"] == 40  # no drift into an empty column
    assert d.grid.x_step == pytest.approx(3.6 / 39, abs=1e-3)
    assert d.grid.y_min == pytest.approx(-0.03) and d.grid.y_step == pytest.approx(0.01)
    assert (d.spec.depth_top, d.spec.depth_bottom) == (0.0, pytest.approx(0.03))
    assert d.amp[0, 1] == pytest.approx(13.0)                     # row 0 = the deepest
    assert d.amp[-1, 1] == pytest.approx(10.0)                    # the top row = the surface
    assert not d.mask[:, 0].any() and not d.mask[:, -1].any()     # 0 = nodata
    folder = tmp_path
    assert core.guess_kind(str(folder)) == "xyz_lines"
    kind, specs = core.scan_stack(str(folder), "xyz_lines")
    assert kind == "xyz_lines" and [s.line for s in specs] == ["VERT3"]
    assert core.geo_id("ert", "Basilica", specs[0]) == "ert:Basilica#sVERT3"
    again = core.read_slice(specs[0])
    assert np.array_equal(again.amp, d.amp)


def test_blocks_read_as_a_plan(tmp_path):
    f = tmp_path / "plan.xyz"
    _lines(f)
    d = core.read_xyz_lines(str(f), orientation="horizontal")
    assert d.spec.orientation == "horizontal" and d.spec.product == "plan"
    assert d.grid.y_min == 0.0 and d.amp.shape == (4, 5)


# ── screen captures ───────────────────────────────────────────────────────────

def _capture(w=200, h=120, px=(40, 20, 160, 100), seed=0):
    """A capture: black, two light axes with ticks, a coloured survey inside."""
    a = np.zeros((h, w, 3), dtype=np.uint8)
    left, top, right, bottom = px
    a[bottom, left - 30:right + 10] = 230                         # x axis, longer than the box
    a[top - 5:bottom + 10, left] = 230                            # y axis
    for c in np.linspace(left, right, 4).astype(int):
        a[bottom + 1:bottom + 6, c] = 230                         # ticks below
    for r in np.linspace(top, bottom, 3).astype(int):
        a[r, left - 5:left] = 230                                 # ticks left
    a[bottom + 2:bottom + 8, left - 25:left - 15] = 230           # a label left of the axis
    rng = np.random.default_rng(seed)
    a[40:80, 60:140, 0] = rng.integers(100, 255, (40, 80))       # the survey, «hot»
    a[40:80, 60:140, 1] = rng.integers(0, 80, (40, 80))
    a[5:12, 5:30] = 255                                           # overlay text
    a[2:8, 45:90] = 255                                           # … and above the axis
    return a


def test_the_frame_is_measured_by_its_ticks():
    a = _capture()
    fr = core.measure_frame(a, (-50, 25), (-22, 37))
    assert fr["px"] == [40, 20, 160, 100]
    assert fr["x_ticks"] == [40, 80, 120, 160] and fr["y_ticks"] == [20, 60, 100]
    assert fr["image_size"] == [200, 120]
    g = core.frame_grid(fr)
    assert (g.nx, g.ny) == (121, 81)
    assert (g.x_min, g.y_min) == (-50, -22)
    assert g.x_step == pytest.approx(75 / 120) and g.y_step == pytest.approx(59 / 80)
    assert core.same_frame(fr, core.declare_frame([40, 20, 160, 100], (-50, 25), (-22, 37)))
    with pytest.raises(ValueError, match="axes"):
        core.measure_frame(np.zeros((50, 50, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        core.declare_frame([10, 10, 5, 20], (0, 1), (0, 1))


def test_the_crop_makes_black_and_axes_transparent():
    a = _capture()
    fr = core.declare_frame([40, 20, 160, 100], (-50, 25), (-22, 37))
    rgba = core.crop_rgba(a, fr)
    assert rgba.shape == (81, 121, 4)
    assert rgba[0, 0, 3] == 0 and rgba[-1, 60, 3] == 0            # black, the x axis
    assert not rgba[:, 0, 3].any()                                # the y axis
    assert (rgba[20:60, 20:100, 3] == 255).all()                  # the survey
    spec = core.SliceSpec(path="Slice_-1504mm.jpg", depth_top=1.5, depth_bottom=1.5,
                          kind="screenshot")
    d = core.read_slice(spec, frame=fr, rgb=a)
    assert d.amp.shape == (81, 121) and d.info["valid_cells"] == 40 * 80
    assert d.mask[80 - 20 - 1, 20] and not d.mask[0, 0]           # row 0 = the bottom of the plot
    with pytest.raises(ValueError, match="frame"):
        core.read_slice(spec)
    with pytest.raises(ValueError, match="decoded by the host"):
        core.read_slice(spec, frame=fr)                           # no decoder in the core


def _png_stack(folder, depths_mm, size=(200, 120)):
    folder.mkdir(parents=True, exist_ok=True)
    for i, mm in enumerate(depths_mm):
        rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
        rgba[..., :3] = _capture(*size, seed=i)
        rgba[..., 3] = 255
        core.write_png(str(folder / ("Slice_%05dmm.png" % -mm if mm else "Slice_00000mm.png")),
                       rgba[::-1])
    return folder


def _tif(path, x0, y0, nx, ny, step=0.1):
    rows = [[1.0] * nx for _ in range(ny)]
    _gt.write_geotiff(str(path), rows, affine=(x0, step, 0.0, y0 + ny * step, 0.0, -step),
                      epsg=25830)


def test_the_screenshot_manifest(tmp_path):
    folder = _png_stack(tmp_path / "Sector1_Alcudia", [0, 5, 10, 14, 20])
    fr = core.measure_frame(_capture(), (-50, 25), (-22, 37))
    tif = tmp_path / "mean_v2.tif"
    # the survey's box: 0.3 m inside the frame on every side
    _tif(tif, ORIGIN[0] - 50 - 75 / 240 + 0.3, ORIGIN[1] - 22 - 59 / 160 + 0.3, 750, 591)
    out = tmp_path / "cache"
    m = core.build_screenshot_manifest(str(folder), str(out), fr, origin=ORIGIN, epsg=25830,
                                       geotiff=str(tif), measured=[fr, fr])
    assert m["kind"] == "screenshot" and m["manifest_version"] == 2
    assert m["georef"]["origin_e"] == ORIGIN[0] and m["georef"]["origin_n"] == ORIGIN[1]
    assert isinstance(m["georef"]["origin_e"], float) and m["georef"]["epsg"] == 25830
    assert m["frame"]["px"] == [40, 20, 160, 100] and m["frame"]["image_size"] == [200, 120]
    assert m["grid"]["nx"] == 121 and m["grid"]["x_min"] == -50
    assert m["checks"]["frames"] == {"measured": 2, "same": 2, "off": []}
    assert m["checks"]["geotiff"]["agrees"] and not m["warnings"]
    assert m["checks"]["geotiff"]["edges"] == [pytest.approx(0.3, abs=0.06)] * 4
    assert len(m["slices"]) == 5 and m["slices"][0]["depth_top"] == 0.0
    assert all(Path(e["raster"]).is_file() for e in m["slices"])  # the captures, not copies
    assert sorted(os.listdir(folder)) == sorted("Slice_%s.png" % n for n in
                                                ("00000mm", "-0005mm", "-0010mm", "-0014mm",
                                                 "-0020mm"))      # nothing written beside them
    st = json.loads((out / (core.MANIFEST_NAME + core.STAMP_SUFFIX)).read_text())
    assert len(st["from"]) == 5 and all(i["digest"].startswith("sha256:") for i in st["from"])
    assert not any("/" in i.get("label", "") for i in st["from"])  # no path in a stamp
    p = st["how"]["parameters"]
    assert p["frame_px"] == [40, 20, 160, 100] and p["origin"] == list(ORIGIN)
    assert p["epsg"] == 25830 and p["black_at_most"] == core.readers.screenshot.BLACK
    try:
        import dtcstamp
    except ImportError:
        pass
    else:
        assert dtcstamp.read_stamp(str(out / (core.MANIFEST_NAME + core.STAMP_SUFFIX)))
    v1 = core.as_v1(m)
    assert not {"frame", "nodata", "checks", "warnings", "stack"} & set(v1)
    assert core.load_manifest(str(out))["frame"] == m["frame"]


def test_the_screenshot_manifest_says_what_is_off(tmp_path):
    folder = _png_stack(tmp_path / "s", [0, 5])
    fr = core.declare_frame([40, 20, 160, 100], (-50, 25), (-22, 37))
    tif = tmp_path / "far.tif"
    _tif(tif, ORIGIN[0] - 45, ORIGIN[1] - 22, 700, 590)          # 5 m off on the left
    moved = core.declare_frame([41, 20, 160, 100], (-50, 25), (-22, 37))
    m = core.build_screenshot_manifest(str(folder), str(tmp_path / "c"), fr, origin=ORIGIN,
                                       epsg=25830, geotiff=str(tif), measured=[fr, moved],
                                       stamp=False)
    codes = [w["code"] for w in m["warnings"]]
    assert codes == ["frame_differs", "frame_off_geotiff"]
    assert all(w["en"] and w["it"] for w in m["warnings"])
    assert m["checks"]["frames"]["off"] == [1] and not m["checks"]["geotiff"]["agrees"]
    with pytest.raises(ValueError, match="refused"):
        core.build_screenshot_manifest(str(folder), str(folder / "cache"), fr)
    with pytest.raises(ValueError, match="measured on a"):
        core.build_screenshot_manifest(str(folder), str(tmp_path / "c2"),
                                       dict(fr, image_size=[1918, 878]))
    with pytest.raises(ValueError, match="ticks"):
        core.build_screenshot_manifest(str(folder), str(tmp_path / "c3"),
                                       dict(fr, x_range=None))


# ── the real data ─────────────────────────────────────────────────────────────

VOLUME_SHAPES = {  # §1 / ert_inspection.txt: planes, (rows = X, columns = Z)
    "3D-00.ASC": ([5, 10, 15], (343, 720)), "3D-1.ASC": ([45, 50], (349, 721)),
    "3D-2.ASC": ([35, 40], (350, 722)), "3D-3.ASC": ([60, 65], (349, 720))}


@pytest.mark.skipif(not VOLUMES.is_dir(), reason="the Basilica Iulia ERT is not on this machine")
def test_the_basilica_iulia_volumes_and_lines():
    assert core.guess_kind(str(VOLUMES)) == "xyzv"
    for name, (planes, shape) in VOLUME_SHAPES.items():
        t = time.time()
        ds = core.read_xyzv(str(VOLUMES / name), plane="y", x="z", y="x", row0="top")
        assert time.time() - t < 1.0
        assert [d.spec.plane for d in ds] == planes
        for d in ds:
            assert d.amp.shape == shape and not d.spec.depth_known
            assert d.info["duplicates"] == 0
            v = d.amp[d.mask]
            assert v.min() >= 1 and v.max() <= 255
    t = time.time()
    d = core.read_xyz_lines(str(BASILICA / "VERT3-OK.XYZ"))
    assert time.time() - t < 1.0
    assert d.info["blocks"] == 989 and d.info["points"] == 979110
    assert d.amp.shape == (990, 989) and d.info["empty_cells"] == 0
    assert d.grid.width == pytest.approx(92.09, abs=0.01)         # 0…92 m, centres
    assert d.spec.line == "VERT3" and d.spec.depth_bottom == pytest.approx(9.89)
    assert 0 < d.amp[d.mask].min() and d.amp[d.mask].max() <= 240


@pytest.mark.skipif(not ALCUDIA.is_dir(), reason="UA Ilici Sector1_Alcudia is not on this machine")
def test_ua_ilici_alcudia(tmp_path):
    kind, specs = core.scan_stack(str(ALCUDIA), "screenshot")
    assert kind == "screenshot" and len(specs) == 601
    mids = [s.depth_mid for s in specs]
    steps = np.round(np.diff(mids) * 1000).astype(int)
    assert set(steps) <= {4, 5, 6} and mids[0] == pytest.approx(0.00125, abs=1e-3)
    assert mids[-1] == pytest.approx(2.999, abs=3e-3)
    assert len({core.document_id(str(ALCUDIA), s) for s in specs}) == 601
    assert {core.image_size(s.path) for s in specs} == {(1918, 878)}
    fr = core.declare_frame(FRAME_PX, (-50, 25), (-22, 37), (1918, 878))
    measured = None
    try:
        from PIL import Image
    except ImportError:
        pass
    else:
        measured = []
        for s in specs:
            with Image.open(s.path) as im:
                measured.append(core.measure_frame(np.asarray(im)))
        assert all(core.same_frame(m, fr) for m in measured)      # one frame on all 601
        assert measured[300]["x_ticks"] == [610, 784, 957, 1130, 1303]
        assert measured[300]["y_ticks"] == [170, 306, 442, 578, 715]
        with Image.open(specs[300].path) as im:
            d = core.read_slice(specs[300], frame=fr, rgb=np.asarray(im))
        assert 0.3 < d.mask.mean() < 0.6
    g = core.frame_grid(fr)
    assert g.x_step == pytest.approx(g.y_step, rel=1e-3)          # square pixels, ~0.108 m
    cmp = core.compare_extent(fr, ORIGIN, str(ILICI / "Sector 1" / "mean_v2.tif"))
    assert cmp["agrees"] and all(abs(v) <= 0.5 for v in cmp["edges"])
    m = core.build_screenshot_manifest(str(ALCUDIA), str(tmp_path / "alcudia"), fr,
                                       origin=ORIGIN, epsg=25830,
                                       geotiff=str(ILICI / "Sector 1" / "mean_v2.tif"),
                                       measured=measured)
    assert len(m["slices"]) == 601 and not m["warnings"]
    assert m["georef"]["origin_e"] == 701806.741 and m["georef"]["origin_n"] == 4234824.081
    assert m["georef"]["epsg"] == 25830
    st = json.loads((tmp_path / "alcudia" / (core.MANIFEST_NAME + core.STAMP_SUFFIX)).read_text())
    assert len(st["from"]) == 601
    assert st["how"]["parameters"]["frame_px"] == FRAME_PX
