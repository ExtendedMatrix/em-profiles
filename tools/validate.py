#!/usr/bin/env python3
"""Validate everything in this repository, as the CI does on every pull request.

    python tools/validate.py [--lang en|it] [--json] [PATH …]

Without paths: every archive in ``examples/`` and ``profiles/``. Each archive
(a folder with ``em-extension.toml`` or ``profile.json``) goes through the ONE
validator of the EM tools, ``s3dgraphy.extensions.validate_archive`` — the
same the Extensions window shows before installing and ``python -m
s3dgraphy.extensions validate`` prints (SPEC.md §10). Nothing here re-states
its checks.

What this repository adds, because only a repository can see it:

* a community package lives in ``profiles/<id>/``: folder = id, one id and
  one prefix per package across ``profiles/``, a ``.github/CODEOWNERS`` line
  for its folder (its curators review it), and data — a pure plugin is not a
  community package and is listed elsewhere (``em-extensions``, phase 2);
* the schemas in ``schemas/`` are the library's own, byte for byte;
* ``core-types.json`` names no type the core no longer has;
* the packages of ``profiles/`` together, as the index of em-extensions will
  list them (``s3dgraphy.extensions.server_generate`` on their archives,
  built here and written nowhere): a version of a section never reused, a
  vocabulary version with one content, a vocabulary carried by a package
  that does not own it (an error when its owner is here), ``[requires]``
  without cycles, an entry with every field of the index.

Exit 1 when anything is an error. Warnings never fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

#: the repository's own problems, in the two languages of the tools (SPEC.md §10)
MESSAGES = {
    "repo_folder_id": ("profiles/{folder}: the folder must be named as the package id ({id})",
                       "profiles/{folder}: la cartella deve chiamarsi come l'id del pacchetto ({id})"),
    "repo_id_twice": ("profiles/{folder}: the id {id} is already used by profiles/{other}",
                      "profiles/{folder}: l'id {id} è già usato da profiles/{other}"),
    "repo_prefix_twice": ("profiles/{folder}: the prefix {prefix} is already used by profiles/{other}",
                          "profiles/{folder}: il prefisso {prefix} è già usato da profiles/{other}"),
    "repo_no_codeowners": ("profiles/{folder}: no line for /profiles/{folder}/ in .github/CODEOWNERS (its curators review it)",
                           "profiles/{folder}: manca la riga /profiles/{folder}/ in .github/CODEOWNERS (la rivedono i suoi curatori)"),
    "repo_plugin_only": ("profiles/{folder}: a plugin without data is not a community package; it is listed in em-extensions",
                         "profiles/{folder}: un plugin senza dati non è un pacchetto di comunità; si elenca in em-extensions"),
    "repo_schema_differs": ("schemas/{name} differs from the schema of s3dgraphy {version}: copy it again",
                            "schemas/{name} è diverso dallo schema di s3dgraphy {version}: ricopialo"),
    "repo_schema_missing": ("schemas/{name} is missing (s3dgraphy {version} has it)",
                            "manca schemas/{name} (s3dgraphy {version} lo ha)"),
    "repo_core_gone": ("core-types.json names types the core no longer has: {types} (rerun tools/core_types.py)",
                       "core-types.json nomina tipi che il nucleo non ha più: {types} (rilancia tools/core_types.py)"),
    "repo_core_new": ("core-types.json is behind the core: {types} (rerun tools/core_types.py)",
                      "core-types.json è indietro rispetto al nucleo: {types} (rilancia tools/core_types.py)"),
}


def say(code: str, lang: str, **params) -> str:
    en, it = MESSAGES[code]
    return (it if lang.startswith("it") else en).format(**params)


def archives(root: Path) -> List[Path]:
    """The archives of a folder: its sub-folders with an envelope or a profile."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")
                  and ((p / "em-extension.toml").is_file() or (p / "profile.json").is_file()))


def codeowners() -> str:
    f = REPO / ".github" / "CODEOWNERS"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


def repo_checks(packages: Dict[Path, object]) -> List[Dict]:
    """Errors (and warnings) that only the repository sees."""
    from s3dgraphy.profiles.package import SCHEMA_DIR
    import s3dgraphy
    import core_types

    out: List[Dict] = []
    owners = codeowners().split()
    seen_id: Dict[str, str] = {}
    seen_prefix: Dict[str, str] = {}
    for path, pkg in packages.items():
        if path.parent.name != "profiles":
            continue
        folder = path.name
        if pkg is None:
            continue
        if pkg.id and pkg.id != folder:
            out.append({"level": "error", "code": "repo_folder_id", "params": {"folder": folder, "id": pkg.id}})
        if pkg.id in seen_id:
            out.append({"level": "error", "code": "repo_id_twice", "params": {"folder": folder, "id": pkg.id, "other": seen_id[pkg.id]}})
        seen_id.setdefault(pkg.id, folder)
        prefix = (pkg.profile or {}).get("prefix")
        if prefix and prefix in seen_prefix:
            out.append({"level": "error", "code": "repo_prefix_twice", "params": {"folder": folder, "prefix": prefix, "other": seen_prefix[prefix]}})
        if prefix:
            seen_prefix.setdefault(prefix, folder)
        if not pkg.has_data:
            out.append({"level": "error", "code": "repo_plugin_only", "params": {"folder": folder}})
        if f"/profiles/{folder}/" not in owners:
            out.append({"level": "error", "code": "repo_no_codeowners", "params": {"folder": folder}})
    version = getattr(s3dgraphy, "__version__", "?")
    for lib in sorted(SCHEMA_DIR.glob("profile.v*.schema.json")):
        mine = REPO / "schemas" / lib.name
        if not mine.is_file():
            out.append({"level": "error", "code": "repo_schema_missing", "params": {"name": lib.name, "version": version}})
        elif mine.read_bytes() != lib.read_bytes():
            out.append({"level": "error", "code": "repo_schema_differs", "params": {"name": lib.name, "version": version}})
    d = core_types.drift(json.loads((REPO / "core-types.json").read_text(encoding="utf-8")), core_types.current())
    gone = [t for k in d for t in d[k]["gone"]]
    new = [t for k in d for t in d[k]["new"]]
    if gone:
        out.append({"level": "error", "code": "repo_core_gone", "params": {"types": ", ".join(gone)}})
    if new:
        out.append({"level": "warning", "code": "repo_core_new", "params": {"types": ", ".join(new)}})
    out += as_index([p for p, pkg in packages.items() if p.parent.name == "profiles" and pkg is not None])
    return out


def as_index(folders: List[Path]) -> List[Dict]:
    """The packages as the index would list them (X1): built in a temporary
    folder, then ``server_generate`` without writing. Its problems come with
    their own words (EN, IT) from the library, the file named by folder."""
    import tempfile
    from s3dgraphy.extensions import build, server_generate

    if not folders:
        return []
    out: List[Dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        names: Dict[str, str] = {}
        for f in sorted(folders):
            res = build(f, output_dir=tmp)
            if res["ok"]:
                names[res["file"]] = f"profiles/{f.name}"
        res = server_generate(tmp, dry_run=True)
    def where(p: Dict) -> Dict:
        name = names.get(p.get("where", ""), "")
        return {"level": p["level"], "code": p["code"], "params": {},
                "en": f"{name}: {p['en']}" if name else p["en"], "it": f"{name}: {p['it']}" if name else p["it"]}
    said = {(p["code"], p["en"]) for p in res["problems"]}
    out += [where(p) for p in res["problems"]]
    out += [where(dict(p, where=x["file"])) for x in res["refused"] for p in x["errors"]
            if (p["code"], p["en"]) not in said]       # a cross-check is in both lists
    return out


def run(paths: List[Path], lang: str = "en") -> Dict:
    from s3dgraphy.extensions import validate_archive
    from s3dgraphy.profiles.package import open_package

    targets = paths or archives(REPO / "examples") + archives(REPO / "profiles")
    result = {"archives": [], "repository": []}
    opened: Dict[Path, object] = {}
    for p in targets:
        r = validate_archive(p)
        try:
            opened[p.resolve()] = open_package(p)
        except Exception:
            opened[p.resolve()] = None
        rel = str(p.resolve().relative_to(REPO)) if p.resolve().is_relative_to(REPO) else str(p)
        result["archives"].append({"path": rel, **r.as_dict()})
    if not paths:
        for pr in repo_checks(opened):
            if "en" not in pr:
                pr = {**pr, "en": say(pr["code"], "en", **pr["params"]), "it": say(pr["code"], "it", **pr["params"])}
            result["repository"].append(pr)
    result["ok"] = all(a["ok"] for a in result["archives"]) and not any(
        x["level"] == "error" for x in result["repository"])
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate the archives of em-profiles, as the CI does")
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--lang", default="en", choices=("en", "it"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = run(a.paths, a.lang)
    if a.json:
        print(json.dumps(res, indent=1, ensure_ascii=False))
        return 0 if res["ok"] else 1
    for arc in res["archives"]:
        print(f"{'OK  ' if arc['ok'] else 'FAIL'} {arc['path']}")
        for p in arc["errors"]:
            print(f"  error   {p[a.lang]}")
        for p in arc["warnings"]:
            print(f"  warning {p[a.lang]}")
    for x in res["repository"]:
        print(f"{'FAIL' if x['level'] == 'error' else 'note'} {x[a.lang]}")
    print("all valid" if res["ok"] else "errors found", file=sys.stderr)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
