"""Shared STASYS presentation palette for the SCATT-inspired layout shells.

Every color used by this package comes from the application's existing
``COLORS`` mapping -- nothing in this package hardcodes a hex value.

The mapping is resolved lazily and defensively:

* ``stasys_app.core.COLORS`` is the historical owner of the palette and is
  preferred, because that is the surface the existing UI already renders with.
* ``stasys_app.constants.COLORS`` is the split-out copy of the same mapping. It
  carries no Qt/logging import side effects, so it is used as the fallback when
  ``core`` cannot be imported (another workstream may transiently leave
  ``core.py`` unparsable, or a consumer may want the palette without pulling in
  the serial/pyqtgraph stack).

Both sources are value-identical; a mismatch is reported rather than silently
ignored, so palette drift cannot hide behind the fallback.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional

__all__ = ["COLORS", "color", "colors", "reload_colors", "source"]

_cache: Optional[Dict[str, str]] = None
_source: str = ""


def _resolve() -> tuple:
    """Load the palette, preferring core and falling back to constants.

    Returns ``(mapping, source_name)``.
    """
    from_origin: Optional[tuple] = None

    try:
        from ..core import COLORS as core_colors  # noqa: PLC0415 - lazy on purpose
        from_origin = ("core", dict(core_colors))
    except Exception:  # pragma: no cover - depends on core import health
        pass

    fallback: Dict[str, str] = {}
    try:
        from ..constants import COLORS as const_colors  # noqa: PLC0415
        fallback = dict(const_colors)
    except Exception:  # pragma: no cover - constants is stdlib-only + numpy
        pass

    if from_origin is not None:
        name, mapping = from_origin
        if fallback and mapping != fallback:
            # A drift between the two copies is a real defect: surface it
            # instead of letting one screen render a different brand color.
            differing = sorted(
                key for key in set(mapping) | set(fallback)
                if mapping.get(key) != fallback.get(key)
            )
            raise RuntimeError(
                "COLORS mismatch between stasys_app.core and "
                f"stasys_app.constants for keys: {differing}"
            )
        return mapping, name

    return fallback, "constants"


def colors() -> Dict[str, str]:
    """Return a copy of the resolved STASYS palette."""
    global _cache, _source
    if _cache is None:
        _cache, _source = _resolve()
    return dict(_cache)


def color(name: str) -> str:
    """Return a single named palette entry (raises ``KeyError`` if unknown)."""
    return colors()[name]


def source() -> str:
    """Return which module the palette was resolved from ('core'/'constants')."""
    colors()
    return _source


def reload_colors() -> Dict[str, str]:
    """Drop the cache and re-resolve -- used after core becomes importable."""
    global _cache, _source
    _cache = None
    _source = ""
    return colors()


def __getattr__(name: str):  # PEP 562 -- keeps `from .palette import COLORS` lazy
    if name == "COLORS":
        return colors()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _exported_colors() -> Mapping[str, str]:  # pragma: no cover - typing aid
    return colors()
