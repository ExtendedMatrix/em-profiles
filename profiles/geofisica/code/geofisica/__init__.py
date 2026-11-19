"""geofisica — the plugin of the geophysics package (GPL-3.0-or-later).

0.1.0. The reading core sits beside it, ``geofisica_core`` (row G2: the old
3DSC ``gpr_core`` moved here, the one source). Row G7 wires the import into
the graph: the command ``geofisica.ingest`` (:mod:`.ingest`) reads a stack,
caches it (every PNG and the manifest stamped, decision G-5) and writes the
acquisition, its files, one document per slice and the rasterization's
process as one act. «Bring in…» (G8), the Inspector (G9), the Space layer
(G10–G11) and the tracing tool (G12) arrive row by row.
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


def _stacks():
    from . import ingest
    return ingest.stacks()


def setup(ctx):
    global _ctx
    _ctx = ctx
    ctx.command("geofisica.ingest", _ingest)
    ctx.expose("stacks", _stacks)


def teardown(ctx):
    global _ctx
    _ctx = None


plugin = type("Plugin", (), {"setup": staticmethod(setup), "teardown": staticmethod(teardown)})
