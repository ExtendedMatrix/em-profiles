"""geofisica — the plugin of the geophysics package (GPL-3.0-or-later).

0.1.0. The reading core sits beside it, ``geofisica_core`` (row G2: the old
3DSC ``gpr_core`` moved here, the one source). Row G7 wires the import into
the graph: the command ``geofisica.ingest`` (:mod:`.ingest`) reads a stack,
caches it (every PNG and the manifest stamped, decision G-5) and writes the
acquisition, its files, one document per slice and the rasterization's
process as one act. Row G8 (:mod:`.door`) brings it in through «Porta
dentro…»: the reader ``geofisica.read`` (``door.reader@2``: a folder, the
claimed rasters and pictures) opens the panel ``import`` with the folder,
whose value ``geofisica.describe`` says what the folder is and whose button
runs ``geofisica.ingest``. Row G9 (:mod:`.inspector`): ``geofisica.section``,
the Inspector's section of a slice and of a USD read on slices. The Space
layer (G10–G11) and the tracing tool (G12) arrive row by row.
"""

__version__ = "0.1.0"

_ctx = None


def _agent():
    """This plugin as the first software line of its stamps and processes."""
    if _ctx is None:
        return {"name": "Geofisica", "id": "geofisica", "version": __version__}
    return {"name": "Geofisica", "id": _ctx.id, "version": str(_ctx.version)}


def _ingest(slots):
    from . import ingest
    return ingest.command(slots, agent=_agent())


def _read(slots):
    from . import door
    return door.read(slots, run=_ingest)


def _describe(slots):
    from . import door
    return door.describe(slots)


def _section(slots):
    from . import inspector
    return inspector.section(slots)


def _stacks():
    from . import ingest
    return ingest.stacks()


def setup(ctx):
    global _ctx
    _ctx = ctx
    ctx.command("geofisica.ingest", _ingest)
    ctx.command("geofisica.read", _read)
    ctx.command("geofisica.describe", _describe)
    ctx.command("geofisica.section", _section)
    ctx.expose("stacks", _stacks)


def teardown(ctx):
    global _ctx
    _ctx = None


plugin = type("Plugin", (), {"setup": staticmethod(setup), "teardown": staticmethod(teardown)})
