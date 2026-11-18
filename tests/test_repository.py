"""The checks every pull request must pass (the CI runs them, and tools/validate.py)."""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import core_types  # noqa: E402
import validate  # noqa: E402

pytest.importorskip("s3dgraphy.extensions")


def test_every_archive_of_the_repository_is_valid():
    res = validate.run([])
    paths = [a["path"] for a in res["archives"]]
    assert paths == ["examples/esempio-statuaria", "examples/esempio-statuaria-misto",
                     "examples/example-toolmarks", "examples/facemesh_fit"]
    for a in res["archives"]:
        assert a["ok"], (a["path"], [e["en"] for e in a["errors"]])
    assert res["ok"], res["repository"]


def test_the_examples_say_they_are_examples():
    """D-5: the synthetic package is declared as such everywhere a person reads it."""
    for name in ("esempio-statuaria", "esempio-statuaria-misto", "facemesh_fit"):
        root = REPO / "examples" / name
        assert "ESEMPIO" in (root / "em-extension.toml").read_text(encoding="utf-8")
        assert "non citare" in (root / "LICENSE").read_text(encoding="utf-8").lower()
    for prof in (REPO / "examples/esempio-statuaria/profile.json", REPO / "examples/esempio-statuaria-misto/data/profile.json"):
        m = json.loads(prof.read_text(encoding="utf-8"))
        assert m["example"] is True and "EXAMPLE" in m["title"]["en"] and "ESEMPIO" in m["title"]["it"]
    assert "not to be cited" in (REPO / "examples/example-toolmarks/profile.json").read_text(encoding="utf-8").lower() \
        or "example" in json.loads((REPO / "examples/example-toolmarks/profile.json").read_text(encoding="utf-8"))["title"]["en"].lower()


def test_the_schemas_are_the_library_s_byte_for_byte():
    from s3dgraphy.profiles.package import SCHEMA_DIR
    lib = sorted(p.name for p in SCHEMA_DIR.glob("profile.v*.schema.json"))
    assert lib == sorted(p.name for p in (REPO / "schemas").glob("*.schema.json")) == \
        ["profile.v0.1.schema.json", "profile.v0.2.schema.json"]
    for n in lib:
        assert (REPO / "schemas" / n).read_bytes() == (SCHEMA_DIR / n).read_bytes(), n
        assert json.loads((REPO / "schemas" / n).read_text(encoding="utf-8"))["$id"] == \
            f"https://w3id.org/extendedmatrix/schemas/{n}"


def test_core_types_names_no_type_the_core_lacks():
    d = core_types.drift(json.loads((REPO / "core-types.json").read_text(encoding="utf-8")), core_types.current())
    assert not [t for k in d for t in d[k]["gone"]], d


def test_every_message_in_english_and_italian():
    for code, (en, it) in validate.MESSAGES.items():
        assert en and it and en != it, code
        assert set(re.findall(r"{(\w+)}", en)) == set(re.findall(r"{(\w+)}", it)), code


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """A copy of this repository's frame (schemas, core types, no CODEOWNERS
    line) where community packages are put by the test."""
    for n in ("schemas", "tools"):
        shutil.copytree(REPO / n, tmp_path / n)
    shutil.copy(REPO / "core-types.json", tmp_path / "core-types.json")
    (tmp_path / "profiles").mkdir()
    (tmp_path / "examples").mkdir()
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CODEOWNERS").write_text("/tools/ @zalmoxes-laran\n", encoding="utf-8")
    monkeypatch.setattr(validate, "REPO", tmp_path)
    return tmp_path


def _codes(res):
    return sorted(x["code"] for x in res["repository"] if x["level"] == "error")


def test_a_community_package_has_its_folder_its_curators_its_prefix(fake_repo):
    shutil.copytree(REPO / "examples/esempio-statuaria", fake_repo / "profiles/statuaria")
    res = validate.run([])
    assert res["archives"][0]["ok"]  # the archive itself is fine …
    assert _codes(res) == ["repo_folder_id", "repo_no_codeowners"]  # … its place in the repository is not
    assert not res["ok"]
    bad = next(x for x in res["repository"] if x["code"] == "repo_no_codeowners")
    assert "CODEOWNERS" in bad["en"] and "CODEOWNERS" in bad["it"] and "curatori" in bad["it"]
    # named as its id, with its curators: accepted
    (fake_repo / "profiles/statuaria").rename(fake_repo / "profiles/esempio-statuaria")
    (fake_repo / ".github/CODEOWNERS").write_text("/profiles/esempio-statuaria/ @zalmoxes-laran\n", encoding="utf-8")
    assert validate.run([])["ok"]


def test_two_packages_never_share_a_prefix_and_a_plugin_is_not_a_package(fake_repo):
    shutil.copytree(REPO / "examples/esempio-statuaria", fake_repo / "profiles/esempio-statuaria")
    shutil.copytree(REPO / "examples/facemesh_fit", fake_repo / "profiles/facemesh_fit")
    # a second package with the same prefix «stat»
    twin = fake_repo / "profiles/esempio-gemello"
    shutil.copytree(REPO / "examples/example-toolmarks", twin)
    m = json.loads((twin / "profile.json").read_text(encoding="utf-8"))
    m["name"], m["prefix"] = "esempio-gemello", "stat"
    txt = json.dumps(m, indent=2, ensure_ascii=False).replace('"tm:', '"stat:')
    (twin / "profile.json").write_text(txt, encoding="utf-8")
    ex = (twin / "example.em.json").read_text(encoding="utf-8").replace('"tm:', '"stat:').replace("tm_face", "stat_face")
    (twin / "example.em.json").write_text(ex.replace("example-toolmarks", "esempio-gemello"), encoding="utf-8")
    (fake_repo / ".github/CODEOWNERS").write_text(
        "".join(f"/profiles/{n}/ @zalmoxes-laran\n" for n in ("esempio-statuaria", "facemesh_fit", "esempio-gemello")),
        encoding="utf-8")
    res = validate.run([])
    assert _codes(res) == ["repo_plugin_only", "repo_prefix_twice"], res["repository"]


def test_a_schema_edited_by_hand_is_caught(fake_repo):
    s = fake_repo / "schemas/profile.v0.2.schema.json"
    s.write_text(s.read_text(encoding="utf-8").replace("additive", "ADDITIVE"), encoding="utf-8")
    assert _codes(validate.run([])) == ["repo_schema_differs"]


def test_the_command_line_says_it_in_both_languages(capsys):
    assert validate.main([]) == 0
    out = capsys.readouterr().out
    assert "OK   examples/esempio-statuaria" in out
    assert validate.main(["--lang", "it", str(REPO / "examples/example-toolmarks")]) == 0
    assert "sospesi" in capsys.readouterr().out


def test_the_spec_names_files_that_exist():
    spec = (REPO / "SPEC.md").read_text(encoding="utf-8")
    for rel in re.findall(r"\]\((?!https?:|#)([^)#]+)\)", spec):
        assert (REPO / rel).exists(), rel
    assert "**Version 0.2" in spec
