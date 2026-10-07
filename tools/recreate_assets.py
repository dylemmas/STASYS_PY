#!/usr/bin/env python3
"""Build the STASYS UI asset set carved from SCATT Basic, with recolouring.

Policy (see docs/scatt_ui_spec.md §7):
  * SHIP only assets whose identity is provable — the 23 SVGs whose embedded
    Sketch <title>/id strings name them (all generic table/view glyphs).
  * RECREATE every RECREATE-slot (SCATT branding, person/calibrate/device
    glyphs, direction arrows) as ORIGINAL artwork; nothing scatt_* ships.
  * Everything else stays in scratch/scatt_extracted/assets/ as reading
    material only — attribution there was not provable.

Recolouring is by role against python_app/stasys_app/core.py COLORS.
Re-runnable: deletes and rebuilds image_assets/scatt_ui/ each run.

Usage:  python tools/recreate_assets.py
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scratch" / "scatt_extracted" / "assets"
OUT = ROOT / "python_app" / "stasys_app" / "image_assets" / "scatt_ui"

# ---- palette roles (must match core.py COLORS; asserted at runtime) --------
GLOW = "#A0A0A0"      # text_secondary — default glyph
MUTED = "#666666"     # text_muted
ACCENT = "#00D26A"    # accent_good
DANGER = "#FF5252"    # accent_bad
CANVAS_BG = "#0D0D0D"  # bg_primary

# Sketch-titled assets: filename -> (semantic name, role)
# All are generic ShotList-table / view-filter glyphs (spec §7.2).
TITLED = {
    "asset_019.svg": ("view", GLOW),
    "asset_115.svg": ("view_alt", GLOW),
    "asset_056.svg": ("filter", GLOW),
    "asset_061.svg": ("filter_selected", ACCENT),
    "asset_050.svg": ("favorites", GLOW),
    "asset_158.svg": ("favorites_selected", ACCENT),
    "asset_006.svg": ("dir_down_right", GLOW),
    "asset_022.svg": ("dir_up_right", GLOW),
    "asset_037.svg": ("dir_center", GLOW),
    "asset_083.svg": ("dir_left", GLOW),
    "asset_099.svg": ("dir_down", GLOW),
    "asset_116.svg": ("dir_right", GLOW),
    "asset_131.svg": ("dir_up", GLOW),
    "asset_177.svg": ("dir_down_left", GLOW),
    "asset_182.svg": ("dir_up_left", GLOW),
    "asset_046.svg": ("ring_10", GLOW),
    "asset_112.svg": ("mark_z2_plus", GLOW),
    "asset_153.svg": ("mark_z2", GLOW),
    "asset_205.svg": ("mark_z_plus", GLOW),
}

HEX_RE = re.compile(r"#[0-9A-Fa-f]{3,8}")


def recolor(text: str, role: str) -> str:
    """Recolour by role: explicit literal fills -> role colour; keep structure."""
    def sub(m: re.Match) -> str:
        val = m.group(0)
        low = val.lower()
        # keep non-colour semantics untouched
        if low in ("#fff", "#ffffff", "#fefefe"):
            return role  # light glyphs in dark theme
        if low in ("#000", "#000000"):
            return CANVAS_BG  # opaque backing plates become canvas bg
        if low in ("#00e678", "#00d26a"):
            return ACCENT  # SCATT green -> STASYS accent
        if low in ("#33383a", "#3a3a3a", "#4a4a4a"):
            return MUTED
        return role
    return HEX_RE.sub(sub, text)


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# ORIGINAL artwork for RECREATE slots (spec §7.1). Original geometry only —
# no SCATT paths, no wordmarks. 48x48 grid, single-path Material style.
# ---------------------------------------------------------------------------

def _svg(body: str, vb: str = "0 0 48 48") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
        f'viewBox="{vb}" fill="none">{body}</svg>'
    )


ORIGINALS = {
    # App icon slot: abstract STASYS reticle (ring + crosshair)
    "stasys_app_icon.svg": _svg(
        f'<circle cx="24" cy="24" r="17" stroke="{ACCENT}" stroke-width="3"/>'
        f'<circle cx="24" cy="24" r="6" fill="{ACCENT}"/>'
        f'<path d="M24 2v9M24 37v9M2 24h9M37 24h9" stroke="{ACCENT}" stroke-width="3"/>'
    ),
    # Wordmark slot (48px header): stylised S monogram
    "stasys_wordmark.svg": _svg(
        f'<path d="M32 14c0-4-4-7-10-7s-11 3-11 8c0 11 22 5 22 16 0 6-6 9-12 9s-11-3-12-8" '
        f'stroke="{ACCENT}" stroke-width="4" stroke-linecap="round" fill="none"/>'
    ),
    # Start-new-session glyph (96px card slot): play triangle in ring
    "stasys_new_session_96.svg": _svg(
        f'<circle cx="48" cy="48" r="38" stroke="{ACCENT}" stroke-width="5"/>'
        f'<path d="M38 30l24 18-24 18z" fill="{ACCENT}"/>', vb="0 0 96 96"
    ),
    # Open-sessions glyph (96px card slot): folder
    "stasys_open_sessions_96.svg": _svg(
        f'<path d="M10 26V18a6 6 0 016-6h16l6 8h26a6 6 0 016 6v26a6 6 0 01-6 6H16a6 6 0 01-6-6z" '
        f'stroke="{GLOW}" stroke-width="5" fill="none"/>'
        f'<path d="M10 34h76" stroke="{GLOW}" stroke-width="5"/>', vb="0 0 96 96"
    ),
    # Device connected / disconnected: generic USB plug
    "stasys_device_connected.svg": _svg(
        f'<path d="M24 6v26" stroke="{ACCENT}" stroke-width="3.5"/>'
        f'<path d="M18 12h12M18 18h12" stroke="{ACCENT}" stroke-width="3.5"/>'
        f'<circle cx="24" cy="36" r="5" fill="{ACCENT}"/>'
        f'<path d="M14 26l10 8 10-8" stroke="{ACCENT}" stroke-width="3.5" fill="none"/>'
    ),
    "stasys_device_disconnected.svg": _svg(
        f'<path d="M24 6v26" stroke="{DANGER}" stroke-width="3.5"/>'
        f'<path d="M18 12h12M18 18h12" stroke="{DANGER}" stroke-width="3.5"/>'
        f'<circle cx="24" cy="36" r="5" fill="{DANGER}"/>'
        f'<path d="M14 26l10 8 10-8" stroke="{DANGER}" stroke-width="3.5" fill="none"/>'
        f'<path d="M8 40L40 8" stroke="{DANGER}" stroke-width="3.5"/>'
    ),
    # Shooter avatar (SelectShooter slot): generic person
    "stasys_person.svg": _svg(
        f'<circle cx="24" cy="17" r="8" fill="{GLOW}"/>'
        f'<path d="M10 40c0-8 6-13 14-13s14 5 14 13z" fill="{GLOW}"/>'
    ),
    # Re-aim / correction glyph
    "stasys_correction.svg": _svg(
        f'<circle cx="24" cy="24" r="12" stroke="{ACCENT}" stroke-width="3.5" fill="none"/>'
        f'<circle cx="24" cy="24" r="3" fill="{ACCENT}"/>'
        f'<path d="M24 4v8M24 36v8M4 24h8M36 24h8" stroke="{ACCENT}" stroke-width="3.5"/>'
    ),
    # Calibration glyph: sliders
    "stasys_calibrate.svg": _svg(
        f'<path d="M10 14h28M10 24h28M10 34h28" stroke="{GLOW}" stroke-width="3.5"/>'
        f'<circle cx="20" cy="14" r="5" fill="{ACCENT}"/>'
        f'<circle cx="32" cy="24" r="5" fill="{ACCENT}"/>'
        f'<circle cx="16" cy="34" r="5" fill="{ACCENT}"/>'
    ),
}

DIRECTION_ORIGINALS = {
    "stasys_dir_up.svg": (f'<path d="M24 10l10 16H14z" fill="{GLOW}"/>'),
    "stasys_dir_down.svg": (f'<path d="M24 38L14 22h20z" fill="{GLOW}"/>'),
    "stasys_dir_left.svg": (f'<path d="M10 24l16-10v20z" fill="{GLOW}"/>'),
    "stasys_dir_right.svg": (f'<path d="M38 24L22 14v20z" fill="{GLOW}"/>'),
    "stasys_dir_up_right.svg": (f'<path d="M34 14L18 20l4 6 12-6z" fill="{GLOW}"/>'),
    "stasys_dir_down_left.svg": (f'<path d="M14 34l16-6-4-6-12 6z" fill="{GLOW}"/>'),
    "stasys_dir_down_right.svg": (f'<path d="M34 34l-16-6 4-6 12 6z" fill="{GLOW}"/>'),
    "stasys_dir_up_left.svg": (f'<path d="M14 14l16 6-4 6-12-6z" fill="{GLOW}"/>'),
}


def main() -> int:
    # palette sanity: read the real values from core.py COLORS
    core = (ROOT / "python_app" / "stasys_app" / "core.py").read_text(encoding="utf-8")
    m = re.search(r"COLORS\s*=\s*\{(.*?)\}", core, re.S)
    assert m, "COLORS dict not found in core.py"
    pairs = dict(re.findall(r"'(\w+)'\s*:\s*'(#[0-9A-Fa-f]{6})'", m.group(1)))
    checks = {
        "text_secondary": GLOW, "text_muted": MUTED, "accent_good": ACCENT,
        "accent_bad": DANGER, "bg_primary": CANVAS_BG,
    }
    for key, expected in checks.items():
        actual = pairs.get(key)
        assert actual and actual.lower() == expected.lower(), (
            f"palette drift: COLORS['{key}']={actual}, script expects {expected}"
        )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    shipped = 0
    for src_name, (semantic, role) in TITLED.items():
        src = SRC / src_name
        if not src.exists():
            print(f"MISSING {src_name}")
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        write(OUT / f"{semantic}.svg", recolor(text, role))
        shipped += 1

    for name, body in ORIGINALS.items():
        write(OUT / name, body)
        shipped += 1
    for name, body in DIRECTION_ORIGINALS.items():
        write(OUT / name, _svg(body))
        shipped += 1

    manifest = f"""# STASYS UI assets (SCATT-derived pipeline)

Built by `tools/recreate_assets.py`. {shipped} files.

## Provenance
* `view/filter/favorites/ring_10/mark_*/dir_*` — carved from SCATT Basic's
  embedded resources and identified by their embedded Sketch `<title>` strings
  (e.g. `Icons/General/View`), then recoloured to the STASYS palette. All
  generic table/view geometry; no SCATT branding.
* `stasys_*` — ORIGINAL artwork created for the RECREATE slots listed in
  `docs/scatt_ui_spec.md` §7.1 (app icon, wordmark, session cards, device
  state, person, correction, calibration, direction arrows). Nothing from
  SCATT is copied here.

## Policy
No `scatt_*` resource ships in this directory. Uncarved/unattributed SCATT
SVGs remain under `scratch/scatt_extracted/assets/` for reference only.
"""
    (OUT / "MANIFEST.md").write_text(manifest, encoding="utf-8")
    print(f"shipped {shipped} files -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
