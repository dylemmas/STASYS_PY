"""Additive SCATT-style layout package for the STASYS application.

This package reproduces the SCATT Basic UI/UX *structure* for the core
shooting/analysis screen (plus settings) while keeping the STASYS dark
palette. It is wired into ``MainWindow.init_ui`` (``stasys_app.core``) behind a
function-level lazy import, and is the DEFAULT layout:

* ``core`` imports this package only inside ``init_ui`` at runtime -- never at
  module level -- so there is no circular import at load time (guarded by
  ``test_package_does_not_import_itself_into_core``);
* the chrome installs for any ``STASYS_LAYOUT`` value except the exact token
  ``legacy``, which keeps the original header/tab layout as an escape hatch;
* no device, serial, database or session logic is executed -- every optional
  region defaults to a neutral blank state, and real widgets are injected by
  the caller;
* every color comes from the existing STASYS ``COLORS`` mapping via
  :mod:`stasys_app.scatt_layout.palette` -- no hardcoded color literals.

Layout provenance is the statically extracted SCATT Basic QML tree under
``scratch/scatt_extracted`` (never executed).
"""

from .palette import COLORS, color, colors, reload_colors, source
from .chrome import (
    EmptyState,
    InfoPane,
    SettingsDialog,
    SettingsPanel,
    StatusBar,
    TimelineBand,
    TitleBar,
    card,
    label,
    palette_check,
    styled_button,
)
from .screens import (
    CATALOG_STEPS,
    PRACTICE_STEPS,
    SettingsScreen,
    ShootingScreen,
    StepStrip,
)

__all__ = [
    # palette
    "COLORS", "color", "colors", "reload_colors", "source", "palette_check",
    # chrome
    "EmptyState", "TitleBar", "InfoPane", "TimelineBand", "StatusBar",
    "SettingsPanel", "SettingsDialog", "label", "card", "styled_button",
    # screens
    "ShootingScreen", "SettingsScreen", "StepStrip",
    "PRACTICE_STEPS", "CATALOG_STEPS",
]
