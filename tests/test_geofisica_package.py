"""MICRO-GEO02 · row G1 of the geophysics plan: the skeleton of the mixed package ``geofisica``.

What is defended: the archive validates with the one validator (no error, no
warning); the partition holds (data under ``data/``, code under ``code/``,
nothing else but the envelope and the licence); two builds of the folder are
the same bytes; the archive built installs from disk on a clean machine
(``S3DGRAPHY_*_DIR`` in a temporary folder), its data are found, and its code
loads in EMStudio and in Blender (``setup`` wires nothing yet).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

X = pytest.importorskip("s3dgraphy.extensions")

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "profiles" / "geofisica"
NS = "https://w3id.org/extendedmatrix/profile/geofisica/vocab/"


@pytest.fixture
def machine(tmp_path, monkeypatch):
    for var, sub in (("S3DGRAPHY_EXTENSIONS_DIR", "extensions"), ("S3DGRAPHY_PROFILES_DIR", "profiles"),
                     ("S3DGRAPHY_PLUGINS_DIR", "plugins"), ("S3DGRAPHY_PLUGINS_DATA_DIR", "plugins-data"),
                     ("S3DGRAPHY_PLUGINS_DEV_DIR", "plugins-dev"), ("S3DGRAPHY_AUTHORITIES_DIR", "authorities")):
        monkeypatch.setenv(var, str(tmp_path / "machine" / sub))
    return tmp_path


def test_the_package_validates_without_a_word():
    rep = X.validate_archive(PKG)
    assert rep.ok, [p.text("en") for p in rep.errors]
    assert rep.warnings == [], [p.text("en") for p in rep.warnings]


def test_the_partition_and_the_head():
    files = sorted(str(p.relative_to(PKG)) for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    assert all(f.startswith(("data/", "code/")) or f in ("em-extension.toml", "LICENSE") for f in files), files
    assert not any(f.endswith(".py") for f in files if f.startswith("data/"))
    profile = json.loads((PKG / "data" / "profile.json").read_text(encoding="utf-8"))
    assert profile["name"] == "geofisica" and profile["prefix"] == "geof" and profile["version"] == "0.1.0"
    assert {t["id"] for t in profile["extractor_types"]} == {"geof:anomalia_punto", "geof:anomalia_linea",
                                                            "geof:anomalia_area"}
    assert {t["id"] for t in profile["document_types"]} == {"geof:fetta", "geof:sezione"}
    assert all(t["reader"] == "plugin:geofisica" for t in profile["file_types"])
    assert {q["scheme"] for q in profile["qualia_vocabularies"]} == {NS + "anomalie/", NS + "metodi/",
                                                                      NS + "grandezze/"}
    for lang in ("en", "it"):                                            # EN + IT, the help too
        assert (PKG / "data" / "help" / lang / "index.md").is_file()
        assert (PKG / "data" / "i18n" / f"{lang}.json").is_file()


def test_two_builds_are_the_same_bytes(tmp_path):
    a = X.build(PKG, output_dir=tmp_path / "a")
    b = X.build(PKG, output_dir=tmp_path / "b")
    assert a["ok"] and b["ok"], a["errors"] + b["errors"]
    assert a["file"] == "geofisica-0.1.0.zip" and a["type"] == "mixed"
    da = hashlib.sha256(Path(a["path"]).read_bytes()).hexdigest()
    db = hashlib.sha256(Path(b["path"]).read_bytes()).hexdigest()
    assert da == db and a["archive_hash"] == b["archive_hash"] and a["digests"] == b["digests"]
    assert set(a["digests"]) == {"data", "code"}


def test_the_archive_installs_from_disk_and_loads(machine):
    from s3dgraphy import em
    from s3dgraphy.em import plugins as PL
    built = X.build(PKG, output_dir=machine / "dist")
    zip_path = Path(built["path"])
    pre = X.preview(zip_path)
    assert pre["id"] == "geofisica"
    res = X.install(zip_path, trust=True)
    assert res["data"]["status"] == "installed" and res["code"]["status"] == "installed", res
    from s3dgraphy import profiles as P
    prof = P.find("geofisica", "0.1.0")
    assert prof is not None and prof.version == "0.1.0"
    PL.reset()
    try:
        for host in ("emstudio", "blender"):
            got = [p for p in PL.sync(host) if p.id == "geofisica"]
            assert got and got[0].state == "loaded", got and got[0].problems
            assert got[0].ctx.package and got[0].ctx.package.version == "0.1.0"
            assert set(got[0].ctx.package.extractor_types()) >= {"geof:anomalia_linea"}
        assert em.API_VERSION >= "1.2"                                   # ctx.stamp is there (G-5)
        assert PL.sync("server") == [] or all(p.id != "geofisica" for p in PL.sync("server"))
    finally:
        PL.reset()
