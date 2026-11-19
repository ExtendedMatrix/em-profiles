"""How ``golden_gpr_core.json`` was made (row G2 of the geophysics plan, MICRO-GEO03).

Run ONCE against the OLD reader, 3D-survey-collection ``importer/gpr_core.py``
at commit 506e768 (19 Nov 2026), before it moved into ``geofisica_core``:

    python make_golden.py <path of the old importer/> <work folder>

It writes what the old core said about the synthetic stacks of
``tests/geofisica_synth.py``: the pixels of every PNG (sha256 of the
decompressed IDAT, so a different zlib cannot fail the test), the PNG bytes
(the same machine compares bytes too), the v1 manifests with the clock and
the folder taken out, the georeference detected, the depths read from names.
Kept beside the golden so the numbers can be remade; the test never runs it.
"""
import hashlib
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))     # tests/
from geofisica_synth import ilici_like, tivoli_like  # noqa: E402

CLOCK = ("build_seconds", "parse_seconds", "png_seconds")
CONFIGS = (("GRAY", "STACK"), ("VIRIDIS", "STACK"), ("GRAY_INV", "SLICE"))
NAMES = ("slice_0.000 - 0.100m.CSV", "slice_1,25-1,50m.csv", "Slice_-2889mm.jpg", "Slice_00000mm.jpg",
         "depth 0.75m.png", "no depth here.csv")


def pixels(path):
    b = open(path, "rb").read()
    i, idat = 8, b""
    while i < len(b):
        n, = struct.unpack(">I", b[i:i + 4])
        if b[i + 4:i + 8] == b"IDAT":
            idat += b[i + 8:i + 8 + n]
        i += 12 + n
    return hashlib.sha256(zlib.decompress(idat)).hexdigest()


def neutral(manifest, work):
    """The clock out, the machine's folders as ``<work>``."""
    m = {k: v for k, v in manifest.items() if k not in CLOCK}
    m["source_folder"] = "<stack>"
    real = os.path.realpath(work)
    for e in m["slices"]:
        for k in ("source", "raster"):
            e[k] = e[k].replace(real, "<work>")
    return m


def main(old_dir, work):
    sys.path.insert(0, old_dir)
    import gpr_core as old
    csv_dir, img_dir = os.path.join(work, "stack"), os.path.join(work, "ilici")
    tivoli_like(csv_dir)
    ilici_like(img_dir)
    out = {"source": "3D-survey-collection importer/gpr_core.py @ 506e768", "png": {}, "manifest_csv": {},
           "zlib": zlib.ZLIB_RUNTIME_VERSION}
    for cm, nm in CONFIGS:
        d = os.path.join(work, "cache_%s_%s" % (cm, nm))
        m = old.build_cache(csv_dir, d, colormap=cm, normalize=nm)
        key = "%s/%s" % (cm, nm)
        out["png"][key] = [{"raster": e["raster"], "pixels": pixels(os.path.join(d, e["raster"])),
                            "bytes": hashlib.sha256(open(os.path.join(d, e["raster"]), "rb").read()).hexdigest()}
                           for e in m["slices"]]
        out["manifest_csv"][key] = neutral(m, work)
    m = old.build_image_manifest(img_dir, os.path.join(work, "cache_img"))
    out["manifest_image"] = neutral(m, work)
    out["georef_csv"] = old.detect_georeference(csv_dir)
    out["georef_image"] = old.detect_georeference(img_dir)
    out["depth_from_name"] = {n: old.depth_from_name(n) for n in NAMES}
    out["shift"] = {"absolute": old.is_absolute(701806.741, 4234824.081),
                    "local": old.is_absolute(12.0, 30.0),
                    "proposed": old.propose_shift(701806.741, 4234824.081, 10.0)}
    with open(os.path.join(HERE, "golden_gpr_core.json"), "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
