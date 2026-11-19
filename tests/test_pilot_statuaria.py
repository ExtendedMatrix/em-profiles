"""MICRO-PL20 · the synthetic statuary pilot (D-5): the head, the plugin's
finding of the points, and the whole road in the two forms."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / "pilots" / "statuaria-sintetica"
PLUGIN = REPO / "examples" / "facemesh_fit"
MIXED_CODE = REPO / "examples" / "esempio-statuaria-misto" / "code" / "facemesh_fit"
SET = json.loads((REPO / "examples/esempio-statuaria/landmarks/volto.json").read_text(encoding="utf-8"))


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


make_head = _module("pl20_make_head", PILOT / "make_head.py")
mesh = _module("pl20_fm_mesh", PLUGIN / "facemesh_fit" / "mesh.py")
fit = _module("pl20_fm_fit", PLUGIN / "facemesh_fit" / "fit.py")


def test_the_plugin_is_the_same_python_in_the_two_envelopes():
    for f in ("__init__.py", "fit.py", "mesh.py"):
        assert (PLUGIN / "facemesh_fit" / f).read_bytes() == (MIXED_CODE / f).read_bytes(), f


def test_the_head_is_generated_the_same_every_time(tmp_path):
    """No binary in the repository: the digest of the generated head is in the
    pilot's results, and the generator gives it back byte for byte."""
    summary = json.loads((PILOT / "risultati" / "summary.json").read_text(encoding="utf-8"))
    doc = make_head.main([str(tmp_path), "--name", "testa-canonica"])
    assert doc["model_digest"] == summary["heads"]["canonica"]["digest"]
    assert doc["license"] == "CC0-1.0" and "SYNTHETIC" in doc["_note"]
    em = json.loads((tmp_path / "testa-canonica.em.json").read_text(encoding="utf-8"))
    assert em["header"]["profiles"] == [{"iri": "https://w3id.org/extendedmatrix/profile/esempio-statuaria",
                                         "version": "0.1.0"}]


@pytest.mark.parametrize("variant,yaw,shift,predicted_mm", [
    ("canonica", 0, "0,0,0", 2.5), ("canonica", 35, "0.4,0.1,-0.2", 2.5), ("fuori-misura", -20, "0,0,0", 7.0)])
def test_the_points_are_found_where_the_truth_is(tmp_path, variant, yaw, shift, predicted_mm):
    doc = make_head.main([str(tmp_path), "--name", "t", "--variant", variant, "--yaw", str(yaw), "--shift", shift])
    pos, tris = mesh.read_mesh(str(tmp_path / "t.glb"))
    got = fit.propose(pos, tris, SET["points"])
    assert set(got["points"]) == {p["id"] for p in SET["points"]}
    for pid, p in got["points"].items():
        err = 1000 * math.dist(p["position"], doc["points"][pid])
        limit = 2.0 if p["method"] == "detected" else predicted_mm
        assert err < limit, (variant, yaw, pid, p["method"], err)
    assert {p for p, v in got["points"].items() if v["method"] == "predicted"} == {"exocanthion_r", "exocanthion_l"}


def test_a_mesh_without_a_face_is_said(tmp_path):
    # a flat square: no height to read a face in
    obj = tmp_path / "flat.obj"
    obj.write_text("v 0 0 0\nv 1 0 0\nv 1 0 1\nv 0 0 1\nf 1 2 3\nf 1 3 4\n", encoding="utf-8")
    pos, tris = mesh.read_mesh(str(obj))
    with pytest.raises(fit.FitError):
        fit.propose(pos, tris, SET["points"])
    with pytest.raises(mesh.MeshError):
        mesh.read_mesh(str(tmp_path / "x.ply"))


def test_the_whole_road_in_the_two_forms(tmp_path):
    pytest.importorskip("s3dgraphy.em.plugins")
    tpl = REPO.parent / "stratigraph-templates" / "src"
    if not (tpl / "stratigraph_templates").is_dir():
        pytest.skip("stratigraph-templates is not next to this repository (the sheet)")
    import subprocess
    out = tmp_path / "run"
    p = subprocess.run([sys.executable, str(PILOT / "run_pilot.py"), str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert all(a["same_proposals"] and a["same_values"] for a in s["forms_agree"])
    sep, mix = s["forms"]["separata"], s["forms"]["mista"]
    # the plugin alone: incomplete, and its command says what is missing
    assert sep["install"]["install_code_first"]["state"]["incomplete"] is True
    assert "manca l'insieme di punti stat:volto" in sep["install"]["command_without_data"]["propose_refused"]["it"]
    # the mixed package: the stub of before, then only the code updated
    assert "non ancora collegato" in mix["install"]["old_command"]["it"]
    assert mix["install"]["update"]["state"]["data"]["version"] == "0.1.0"
    assert mix["install"]["update"]["state"]["code"]["version"] == "0.2.0"
    assert mix["install"]["after_update_same_process"][0]["state"] == "restart"
    for form in (sep, mix):
        for h in form["heads"]["heads"]:
            assert h["proposals"]["count"] == 6
            assert h["pose_complete"] and h["reread"]["pose_complete"] and h["reread"]["same_values"]
            assert h["saved"]["volatile_nodes"] == 0 and h["saved"]["proposal_nodes"] == 0
            assert h["saved"]["landmarks_proposed_by_plugin"] == 6
            assert len(h["computed"]["computed"]) == 3
            for k in ("larghezza", "altezza", "indice"):
                assert abs(h["deviation_final"][k]["rel_pct"]) < 0.01, (h["head"], k)
            assert h["sheet"]["files"]["it"]["has_width"] and h["sheet"]["files"]["en"]["has_width"]
