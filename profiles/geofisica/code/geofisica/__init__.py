"""geofisica — the plugin of the geophysics package (GPL-3.0-or-later).

0.1.0, row G1 of the geophysics plan: the skeleton. ``setup`` wires nothing
yet; the reading core (``geofisica_core``, row G2), the import into the graph
(G7), «Bring in…» (G8), the Inspector (G9), the Space layer (G10–G11) and the
tracing tool (G12) arrive row by row. Every derived artifact it will write is
stamped (``ctx.stamp``, decision G-5).
"""

__version__ = "0.1.0"


def setup(ctx):
    """Nothing to wire yet (row G1)."""
    return None


def teardown(ctx):
    return None


plugin = type("Plugin", (), {"setup": staticmethod(setup), "teardown": staticmethod(teardown)})
