"""MICRO-PL20 · the pilot in EMStudio's own host (its Python bridge), not in
the page. ESEMPIO SINTETICO (D-5) — non citare.

Starts a bridge of EMStudio of ITS OWN (``tools/em_bridge.py`` on a free
port, a secret of its own, machine folders under OUT_DIR — never the
development stack, never ``~/.s3dgraphy``), then does what the page does:

1. ``/extensions/install`` the mixed archive (trust answered) — the folder;
2. ``/py/plugins`` — the plugin loaded for EMStudio, its command and slots;
3. ``/py/session`` with the head's em.json AS THE PAGE HAS IT (the model's
   ``url`` relative to the document), then ``/py/invoke facemesh.propose``;
4. the same with the ``url`` made absolute (what a page could send);
5. every proposal confirmed with ``/pose/landmark`` (the pose tool's route),
   the combiners at the last one, the deltas applied here as the page would.

    python bridge_pilot.py OUT_DIR HEADS_DIR [--emstudio ~/Documents/GitHub/EMStudio]
                           [--s3dgraphy ~/Documents/GitHub/s3Dgraphy/src]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORCID = "0000-0002-1825-0097"
TOKEN = "pl20-pilot-secret-0123456789abcdef"
SET = "stat:volto"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def post(base: str, route: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    req = urllib.request.Request(base + route, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


def apply_delta(doc: Dict[str, Any], delta: Dict[str, Any]) -> None:
    """What the page does with a pose route's delta (one undo step)."""
    g = doc["graphs"][doc["active_graph_id"]]
    byid = {n["id"]: n for n in g["nodes"]}
    gone = set(delta.get("remove_nodes") or [])
    g["nodes"] = [n for n in g["nodes"] if n["id"] not in gone]
    for n in delta.get("add_nodes") or []:
        g["nodes"].append(n)
    byid = {n["id"]: n for n in g["nodes"]}
    for c in delta.get("set_fields") or []:
        n = byid.get(c["node"])
        if n is None:
            continue
        f = c["field"]
        if f.startswith("data."):
            n.setdefault("data", {})
            if c["value"] is None:
                n["data"].pop(f[5:], None)
            else:
                n["data"][f[5:]] = c["value"]
        else:
            n[f] = c["value"]
    gone_e = {e.get("id") for e in delta.get("remove_edges") or []}
    g["edges"] = [e for e in g["edges"] if e.get("id") not in gone_e]
    have = {e.get("id") for e in g["edges"]}
    for e in delta.get("add_edges") or []:
        if e.get("id") not in have:
            g["edges"].append(e)


def _dtc(step: Dict[str, Any]) -> Dict[str, Any]:
    """What a step says of who acted: its process, and the DTC node the delta adds."""
    proc = step.get("process") if isinstance(step.get("process"), dict) else {}
    out = {"dtc": step.get("dtc") if isinstance(step.get("dtc"), str) else None,
           "process": {k: proc.get(k) for k in ("plugin", "plugin_version", "command", "source", "verified", "package")
                       if k in proc}}
    for n in (step.get("delta") or {}).get("add_nodes") or []:
        if n.get("id") == out["dtc"]:
            d = n.get("data") or {}
            out["dtc_node"] = {"name": n.get("name"), "node_type": n.get("node_type"), "data": d}
    return out


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("heads")
    ap.add_argument("--emstudio", default=str(REPO.parent / "EMStudio"))
    ap.add_argument("--s3dgraphy", default=str(REPO.parent / "s3Dgraphy" / "src"))
    ap.add_argument("--archive", help="the mixed archive (zip); built from examples/ when not given")
    ap.add_argument("--head", default="testa-canonica")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    machine = out / "machine-bridge"
    env = dict(os.environ)
    for var, sub in (("EM_VOCABULARIES_DIR", "vocab"), ("S3DGRAPHY_PROFILES_DIR", "profiles"),
                     ("S3DGRAPHY_EXTENSIONS_DIR", "extensions"), ("S3DGRAPHY_PLUGINS_DIR", "plugins"),
                     ("S3DGRAPHY_PLUGINS_DATA_DIR", "plugins-data"), ("S3DGRAPHY_CONSOLE_DIR", "console"),
                     ("EM_BRIDGE_STATE_DIR", "state")):
        env[var] = str(machine / sub)
    env.pop("S3DGRAPHY_PLUGINS_DEV_DIR", None)
    env["EM_BRIDGE_TOKEN"] = TOKEN
    env["EM_PY_ANSWER_S"] = "30"
    env["PYTHONPATH"] = a.s3dgraphy

    rep: Dict[str, Any] = {"bridge": {}}
    archive = a.archive
    if not archive:
        sys.path.insert(0, a.s3dgraphy)
        os.environ.update({k: v for k, v in env.items() if k.startswith(("S3DGRAPHY_", "EM_VOCAB"))})
        from s3dgraphy import extensions as X
        archive = X.build(REPO / "examples" / "esempio-statuaria-misto", output_dir=out / "zips")["path"]

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    log = open(out / "bridge.log", "w")
    t0 = time.perf_counter()
    child = subprocess.Popen([sys.executable, str(Path(a.emstudio) / "tools" / "em_bridge.py"), "--port", str(port),
                              "--s3dgraphy", a.s3dgraphy], env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(200):
            try:
                with urllib.request.urlopen(base + "/health", timeout=1) as r:
                    h = json.loads(r.read().decode("utf-8") or "{}")
                    rep["bridge"]["health"] = {k: h.get(k) for k in ("ok", "level", "bridge_level", "version") if k in h}
                    break
            except Exception:                        # noqa: BLE001 — not up yet
                time.sleep(0.1)
        rep["bridge"]["up_ms"] = round((time.perf_counter() - t0) * 1000)

        st, j = post(base, "/extensions/install", {"path": str(archive), "trust": True, "lang": "it"})
        rep["install"] = {"status": st, "ok": j.get("ok", st == 200),
                          "code": (j.get("code") or {}).get("state") if isinstance(j.get("code"), dict) else None}
        t1 = time.perf_counter()
        st, j = post(base, "/py/plugins", {"lang": "it"})
        rep["plugins"] = {"status": st, "ms": round((time.perf_counter() - t1) * 1000),
                          "plugins": [{"id": p["id"], "version": p["version"], "state": p["state"],
                                       "source": p["source"], "verified": p["verified"],
                                       "commands": [{"id": c["id"], "in": c.get("in"), "when": c.get("when")}
                                                    for c in p.get("commands") or []]}
                                      for p in j.get("plugins") or []]}
        pid = (j.get("plugins") or [{}])[0].get("id")

        heads = Path(a.heads)
        doc0 = json.loads((heads / f"{a.head}.em.json").read_text(encoding="utf-8"))
        truth = json.loads((heads / f"{a.head}.truth.json").read_text(encoding="utf-8"))
        declared = doc0["header"]["profiles"]

        def invoke(doc: Dict[str, Any]) -> Dict[str, Any]:
            st, s = post(base, "/py/session", {"doc": doc, "revision": 1, "author": ORCID, "lang": "it",
                                               "declared": declared, "selection": ["rm1"]})
            t = time.perf_counter()
            st2, r = post(base, "/py/invoke", {"session": s.get("session"), "revision": 1, "plugin": pid,
                                                "command": "facemesh.propose", "slots": {"model": "rm1"}, "lang": "it"})
            post(base, "/py/close", {"session": s.get("session")})
            return {"session_status": st, "status": st2, "ms": round((time.perf_counter() - t) * 1000), "answer": r}

        # 3 · as the page has it: the url relative to the document
        rel = invoke(doc0)
        ans = rel["answer"]
        rep["relative_url"] = {"status": rel["status"], "run": ans.get("status"),
                               "messages": ans.get("messages") or ans.get("error"), "steps": len(ans.get("steps") or [])}

        # 4 · the url absolute
        doc = copy.deepcopy(doc0)
        for n in doc["graphs"]["testa"]["nodes"]:
            if (n.get("data") or {}).get("url"):
                n["data"]["url"] = str((heads / n["data"]["url"]).resolve())
        absr = invoke(doc)
        ans = absr["answer"]
        steps = ans.get("steps") or []
        value = (ans.get("result") or {}).get("value") or {}
        rep["absolute_url"] = {"status": absr["status"], "run": ans.get("status"), "ms": absr["ms"],
                               "messages": ans.get("messages"), "steps": len(steps),
                               "volatile_steps": sum(1 for s in steps if s.get("volatile")),
                               "dtc": [_dtc(s) for s in steps],
                               "proposals": len(value.get("proposals") or []), "by": value.get("by")}
        errs = {r["point"]: round(1000 * math.dist(r["position"], truth["points"][r["point"]]), 2)
                for r in value.get("proposals") or []}
        rep["absolute_url"]["err_mm"] = errs

        # 5 · confirmed with the pose tool's route, one point after the other
        t = time.perf_counter()
        last: Dict[str, Any] = {}
        for k, r in enumerate(value.get("proposals") or []):
            st, j = post(base, "/pose/landmark", {"doc": doc, "declared": declared, "set": SET, "point": r["point"],
                                                  "on": "d1", "subject": "us1", "position": r["position"],
                                                  "label": r["label"], "lang": "it", "author": ORCID,
                                                  "name": f"D.01.{k + 1:02d}", "compute": True,
                                                  "pose_name": "Punti canonici del volto"})
            if st != 200:
                last = {"status": st, "error": j.get("error")}
                break
            apply_delta(doc, j["delta"])
            last = j["result"]
        rep["pose"] = {"ms": round((time.perf_counter() - t) * 1000),
                       "complete": (last.get("status") or {}).get("complete"),
                       "computed": [{"type": c.get("combiner_type"), "value": c.get("value"), "text": c.get("text")}
                                    for c in (last.get("computed") or {}).get("computed") or []],
                       "combiner_names": sorted(n.get("name") for n in doc["graphs"]["testa"]["nodes"]
                                                if n.get("node_type") == "combiner")}
    finally:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
        log.close()
    rep["bridge"]["stopped"] = child.returncode is not None
    (out / "bridge.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
