# -*- coding: utf-8 -*-
"""geofisica_core — the reading core of the geophysics package: THE one source (G-1).

Geophysical stacks (GPR, ERT, magnetometry: the method is a word in the
stack, not a different program) read into slices, rasterised into a cache of
PNGs, described by a manifest. Pure Python + numpy: **no bpy, no s3dgraphy
required**, so it runs in Blender (3D Survey Collection embeds this folder at
build time, row G6), in EMStudio's bridge and in a test.

It is the old 3D-survey-collection ``importer/gpr_core.py`` (886 lines, moved
here in row G2 of the geophysics plan, MICRO-GEO03) divided into modules:

* :mod:`.grid` — ``GridSpec``, ``SliceSpec``/``Slice`` (with ``orientation``,
  ``line``, ``product``), ``SliceData``, ``Stack`` (``method``, ``quantity``,
  ``unit``, ``value_scale``);
* :mod:`.depth` — depth from a name, the CSV header;
* :mod:`.identity` — ``gpr:<stack>#d<top>-<bottom>m`` unchanged, ``ert:``,
  ``mag:``, ``#s<line>``, ``#<product>``;
* :mod:`.readers` — ``csv_grid``, ``image_stack``, ``scan_stack``;
* :mod:`.georef` — world files, ``.prj``, shift;
* :mod:`.color`, :mod:`.png` — colour maps and the zlib PNG writer;
* :mod:`.manifest` — the cache and ``gpr_stack.json`` v2 (reads v1);
* :mod:`.stamp` — ``<file>.stamp.json`` on everything written (G-5).

The names below are a STABLE API: they are what 3DSC's ``import_gpr.py``
uses (``build_cache_steps``, ``build_image_manifest``, ``load_manifest``,
``detect_georeference``, ``is_absolute``, ``propose_shift``, ``scan_stack``,
``MANIFEST_NAME``) and what the old module exported.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .color import COLORMAPS, _viridis_lut, percentile_range, to_rgba8
from .depth import depth_from_name, parse_csv_header, read_csv_header
from .georef import (ABSOLUTE_COORD_THRESHOLD, detect_georeference, epsg_from_prj,
                     extent_from_world_file, is_absolute, prj_file_for, propose_shift,
                     read_world_file, world_file_for)
from .grid import (DEFAULT_QUANTITY, METHODS, ORIENTATIONS, GridSpec, Slice, SliceData,
                   SliceSpec, Stack)
from .identity import document_id, geo_id, stack_name
from .manifest import (MANIFEST_NAME, MANIFEST_VERSION, as_v1, build_cache, build_cache_steps,
                       build_image_manifest, load_manifest, open_stack, upgrade_manifest)
from .png import write_png
from .readers import (CSV_EXT, IMG_EXT, NODATA, RepairedReader, image_size, read_csv_slice,
                      repair_chunk, scan_stack)
from .stamp import STAMP_SUFFIX, file_digest, resource_id_for, stamp_artifact, stamp_path

__all__ = [
    "ABSOLUTE_COORD_THRESHOLD", "COLORMAPS", "CSV_EXT", "DEFAULT_QUANTITY", "GridSpec", "IMG_EXT",
    "MANIFEST_NAME", "MANIFEST_VERSION", "METHODS", "NODATA", "ORIENTATIONS", "RepairedReader",
    "STAMP_SUFFIX", "Slice", "SliceData", "SliceSpec", "Stack", "as_v1", "build_cache",
    "build_cache_steps", "build_image_manifest", "depth_from_name", "detect_georeference",
    "document_id", "epsg_from_prj", "extent_from_world_file", "file_digest", "geo_id",
    "image_size", "is_absolute", "load_manifest", "open_stack", "parse_csv_header",
    "percentile_range", "prj_file_for", "propose_shift", "read_csv_header", "read_csv_slice",
    "read_world_file", "repair_chunk", "resource_id_for", "scan_stack", "stack_name",
    "stamp_artifact", "stamp_path", "to_rgba8", "upgrade_manifest", "world_file_for",
    "write_png",
]
