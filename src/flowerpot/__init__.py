"""Flowerpot collaboration services and platform runtime helpers.

Keep this package initializer import-light: Grasshopper GHPython loads it before
`flowerpot.runtime`, and the service modules are Python 3 only.
"""

__all__ = [
    "cleanup_flowerpots",
    "create_flowerpot",
    "get_flowerpot",
]


def __getattr__(name):
    if name in __all__:
        from flowerpot import registry

        return getattr(registry, name)
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
