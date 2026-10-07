"""Reusable SCATT-style chrome widgets for the STASYS layout shells.

This module contains the *chrome* -- the top title row, the right-hand
information/settings pane, the bottom timeline band and the footer/status
region -- plus a clean settings panel. It depends only on PyQt5 and the
resolved STASYS palette; it never imports ``stasys_app.core`` at module import
time, so it stays loadable while the core module is being edited.

Every color is looked up through :mod:`stasys_app.scatt_layout.palette`. There
are no hardcoded color literals anywhere in this package.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .palette import color

# --------------------------------------------------------------------------- #
# low-level helpers
# --------------------------------------------------------------------------- #

_ROLES = (
    "bg_primary", "bg_secondary", "bg_tertiary", "bg_card", "bg_elevated",
    "text_primary", "text_secondary", "text_muted", "accent_good", "accent_ok",
    "accent_bad", "accent_blue", "border", "border_active",
)


def palette_check() -> None:
    """Fail loudly if a role this package depends on is missing from COLORS."""
    from .palette import colors  # noqa: PLC0415 - lazy, avoids import cycle

    missing = [role for role in _ROLES if role not in colors()]
    if missing:  # pragma: no cover - guards a palette edit regression
        raise KeyError(f"palette missing required roles: {missing}")


def label(text: str, role: str = "text_primary", size: int = 11,
          bold: bool = False, word_wrap: bool = False) -> QLabel:
    """Build a palette-styled QLabel."""
    widget = QLabel(text)
    weight = "600" if bold else "400"
    widget.setStyleSheet(
        f"color: {color(role)}; font-size: {size}px; font-weight: {weight};"
        " background: transparent; border: none;"
    )
    widget.setWordWrap(word_wrap)
    return widget


def card(widget: QWidget, *, background: str = "bg_secondary",
         rounded: bool = True) -> QFrame:
    """Wrap ``widget`` in a palette-styled framed container."""
    frame = QFrame()
    frame.setObjectName("layoutCard")
    radius = "8px" if rounded else "0px"
    frame.setStyleSheet(
        "QFrame#layoutCard {"
        f"background: {color(background)}; border: 1px solid {color('border')};"
        f" border-radius: {radius};"
        "}"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.addWidget(widget)
    return frame


def styled_button(text: str, *, primary: bool = False) -> QPushButton:
    """Build a flat palette-styled button."""
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    bg = "accent_blue" if primary else "bg_tertiary"
    border = "accent_blue" if primary else "border"
    fg = "text_primary"
    btn.setStyleSheet(
        f"QPushButton {{ background: {color(bg)}; color: {color(fg)};"
        f" border: 1px solid {color(border)}; border-radius: 5px;"
        " padding: 6px 12px; font-size: 11px; font-weight: 600; }"
        f"QPushButton:hover {{ border-color: {color('border_active')}; }}"
        "QPushButton:disabled { color: %s; }" % color("text_muted")
    )
    return btn


def _field_label(text: str) -> QLabel:
    return label(text, "text_secondary", 11)


# --------------------------------------------------------------------------- #
# neutral blank / error state
# --------------------------------------------------------------------------- #

class EmptyState(QWidget):
    """Neutral placeholder shown when optional content is not available.

    Deliberately shows *no* fabricated data: no invented device output, no
    synthetic shots, no fake session metrics.
    """

    def __init__(self, message: str = "", detail: str = "",
                 *, role: str = "bg_tertiary",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        layout.addStretch(1)

        self._message_label = label(message or "No data", "text_secondary", 12, True,
                                    word_wrap=True)
        self._message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._message_label)

        if detail:
            self._detail_label = label(detail, "text_muted", 10, word_wrap=True)
            self._detail_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self._detail_label)
        else:
            self._detail_label = None

        layout.addStretch(1)
        self.setStyleSheet(
            f"QWidget#emptyState {{ background: {color(role)};"
            f" border: 1px dashed {color('border')}; border-radius: 8px; }}"
        )

    def set_message(self, message: str, detail: str = "") -> None:
        """Update the placeholder copy."""
        self._message_label.setText(message or "No data")
        if self._detail_label is not None:
            self._detail_label.setText(detail)


# --------------------------------------------------------------------------- #
# top title / session row
# --------------------------------------------------------------------------- #

class TitleBar(QWidget):
    """Top row: mode badge, session title, readout chips, status, settings."""

    settingsRequested = pyqtSignal()

    def __init__(self, mode: str = "", session_title: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setStyleSheet(
            f"QWidget#titleBar {{ background: {color('bg_secondary')};"
            f" border: 1px solid {color('border')}; border-radius: 8px; }}"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.mode_badge = QLabel(mode or "")
        self.mode_badge.setStyleSheet(
            f"QLabel {{ background: {color('accent_blue')}; color: {color('text_primary')};"
            " padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; }"
        )
        self.mode_badge.setVisible(bool(mode))
        row.addWidget(self.mode_badge)

        self.title_label = label(session_title or "Session", "text_primary", 15, True)
        row.addWidget(self.title_label)

        self.chip_host = QHBoxLayout()
        self.chip_host.setSpacing(6)
        row.addLayout(self.chip_host)
        row.addStretch(1)

        self.status_badge = QLabel("")
        self.status_badge.setStyleSheet(
            f"QLabel {{ background: {color('status_idle')}; color: {color('text_primary')};"
            " padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; }"
        )
        self.status_badge.setVisible(False)
        row.addWidget(self.status_badge)

        self.settings_button = styled_button("Settings")
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        row.addWidget(self.settings_button)

        outer.addLayout(row)

    # -- public API ------------------------------------------------------- #

    def set_mode(self, mode: str) -> None:
        self.mode_badge.setText(mode or "")
        self.mode_badge.setVisible(bool(mode))

    def set_session_title(self, title: str) -> None:
        self.title_label.setText(title or "Session")

    def set_status(self, text: str, *, role: str = "status_idle",
                   fg: str = "text_primary") -> None:
        """Show a status chip. ``role`` sets the background and ``fg`` the
        foreground -- both palette keys. ``fg`` exists so light backgrounds
        (e.g. ``accent_ok``) can pair with dark text for readable contrast."""
        self.status_badge.setText(text or "")
        self.status_badge.setVisible(bool(text))
        if text:
            self.status_badge.setStyleSheet(
                f"QLabel {{ background: {color(role)}; color: {color(fg)};"
                " padding: 4px 10px; border-radius: 4px;"
                " font-size: 10px; font-weight: 700; }"
            )

    def set_chips(self, chips: Optional[list]) -> None:
        """Replace the readout chips. Each chip is ``(caption, value)``."""
        while self.chip_host.count():
            item = self.chip_host.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for caption, value in (chips or []):
            self.chip_host.addWidget(self._chip(caption, value))

    @staticmethod
    def _chip(caption: str, value: str) -> QFrame:
        box = QFrame()
        box.setStyleSheet(
            f"QFrame {{ background: {color('bg_tertiary')};"
            f" border: 1px solid {color('border')}; border-radius: 5px;"
            " padding: 2px 8px; }"
        )
        lay = QHBoxLayout(box)
        lay.setContentsMargins(2, 2, 8, 2)
        lay.setSpacing(6)
        cap = label(caption, "text_muted", 9)
        val = label(value, "text_primary", 11, True)
        lay.addWidget(cap)
        lay.addWidget(val)
        return box


# --------------------------------------------------------------------------- #
# right-hand information / settings pane
# --------------------------------------------------------------------------- #

class _Slot(QFrame):
    """Holds exactly one widget and can swap it without losing layout order."""

    def __init__(self, initial: QWidget, decorate=None):
        super().__init__()
        self.setObjectName("slot")
        self.setStyleSheet("QFrame#slot { border: none; background: transparent; }")
        self._decorate = decorate
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._current: Optional[QWidget] = None
        self.show_widget(initial)

    def show_widget(self, widget: QWidget) -> None:
        if widget is self._current:
            return
        if self._current is not None:
            self._layout.removeWidget(self._current)
            self._current.setParent(None)
        shown = self._decorate(widget) if self._decorate is not None else widget
        self._layout.addWidget(shown)
        self._current = widget


class InfoPane(QWidget):
    """Right pane: session summary, shot detail, optional injected widgets.

    Missing optional content renders as a neutral blank state -- never as
    fabricated device output.

    The analysis row and the detail row each own a stable slot widget, so an
    injected widget and its blank state can be swapped without disturbing the
    surrounding layout order.
    """

    settingsRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, *,
                 stats_widget: Optional[QWidget] = None,
                 detail_widget: Optional[QWidget] = None,
                 width: int = 320):
        super().__init__(parent)
        self.setObjectName("infoPane")
        self.setMinimumWidth(width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Session row -- a neutral blank state driven entirely by the caller.
        layout.addWidget(label("SESSION", "text_muted", 9, True))
        self.session_state = EmptyState("No session selected",
                                        "Start a session to see summary data.")
        layout.addWidget(self.session_state)

        # Analysis row.
        layout.addWidget(label("ANALYSIS", "text_muted", 9, True))
        self._stats_empty = EmptyState("No analysis", "No shots recorded yet.")
        self._stats_slot = _Slot(self._stats_empty, decorate=card)
        layout.addWidget(self._stats_slot)
        self.stats_widget: Optional[QWidget] = None

        # Shot detail row.
        layout.addWidget(label("SHOT DETAIL", "text_muted", 9, True))
        self._detail_empty = EmptyState("No shot selected",
                                        "Select a shot to inspect its detail.")
        self._detail_slot = _Slot(self._detail_empty, decorate=card)
        layout.addWidget(self._detail_slot)
        self.detail_widget: Optional[QWidget] = None

        layout.addStretch(1)

        self.settings_button = styled_button("Open Settings")
        self.settings_button.clicked.connect(self.settingsRequested)
        layout.addWidget(self.settings_button)

        # Optional injections go through the public setters so the blank/slot
        # bookkeeping lives in exactly one place.
        if stats_widget is not None:
            self.set_stats_widget(stats_widget)
        if detail_widget is not None:
            self.set_detail_widget(detail_widget)

    # -- public API ------------------------------------------------------- #

    def set_session_state(self, message: str, detail: str = "") -> None:
        """Update the neutral session placeholder copy."""
        self.session_state.set_message(message or "No session selected", detail)

    def set_stats_widget(self, widget: Optional[QWidget]) -> None:
        """Inject (or clear) the session-stats widget."""
        self.stats_widget = widget
        self._stats_slot.show_widget(widget if widget is not None
                                     else self._stats_empty)

    def set_detail_widget(self, widget: Optional[QWidget]) -> None:
        """Inject (or clear) the shot-detail widget."""
        self.detail_widget = widget
        self._detail_slot.show_widget(widget if widget is not None
                                      else self._detail_empty)


#
# bottom timeline band + footer
# --------------------------------------------------------------------------- #

class TimelineBand(QWidget):
    """Bottom band holding the filmstrip and the replay transport."""

    def __init__(self, parent: Optional[QWidget] = None, *,
                 filmstrip: Optional[QWidget] = None,
                 replay_bar: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("timelineBand")
        self.setStyleSheet(
            f"QWidget#timelineBand {{ background: {color('bg_secondary')};"
            f" border: 1px solid {color('border')}; border-radius: 8px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(label("TIMELINE", "text_muted", 9, True))
        header.addStretch(1)
        self.shot_count_label = label("0 shots", "text_secondary", 10)
        header.addWidget(self.shot_count_label)
        layout.addLayout(header)

        self.filmstrip = filmstrip
        if filmstrip is not None:
            filmstrip.setMinimumHeight(56)
            layout.addWidget(filmstrip)
        else:
            self.filmstrip_empty = EmptyState("No shots yet",
                                              "Recorded shots appear here as chips.")
            self.filmstrip_empty.setMinimumHeight(56)
            layout.addWidget(self.filmstrip_empty)

        self.replay_bar = replay_bar
        if replay_bar is not None:
            layout.addWidget(replay_bar)
        else:
            self.replay_empty = EmptyState("No replay available")
            self.replay_empty.setMinimumHeight(40)
            layout.addWidget(self.replay_empty)

    def set_shot_count(self, count: int) -> None:
        self.shot_count_label.setText(f"{count} shot" if count == 1 else f"{count} shots")

    def set_filmstrip(self, widget: Optional[QWidget]) -> None:
        """Inject (or clear) the filmstrip widget."""
        self.filmstrip = widget
        if widget is not None and hasattr(self, "filmstrip_empty"):
            self.filmstrip_empty.setParent(None)
            self.filmstrip_empty.deleteLater()
            del self.filmstrip_empty
            widget.setMinimumHeight(56)
            self.layout().insertWidget(1, widget)
        elif widget is None and not hasattr(self, "filmstrip_empty"):
            self.filmstrip_empty = EmptyState("No shots yet",
                                              "Recorded shots appear here as chips.")
            self.filmstrip_empty.setMinimumHeight(56)
            self.layout().insertWidget(1, self.filmstrip_empty)

    def set_replay_bar(self, widget: Optional[QWidget]) -> None:
        """Inject (or clear) the replay transport widget."""
        self.replay_bar = widget
        if widget is not None and hasattr(self, "replay_empty"):
            self.replay_empty.setParent(None)
            self.replay_empty.deleteLater()
            del self.replay_empty
            self.layout().addWidget(widget)
        elif widget is None and not hasattr(self, "replay_empty"):
            self.replay_empty = EmptyState("No replay available")
            self.replay_empty.setMinimumHeight(40)
            self.layout().addWidget(self.replay_empty)


class StatusBar(QWidget):
    """Footer status region: left message, right-hand secondary readouts."""

    def __init__(self, message: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setStyleSheet(
            f"QWidget#statusBar {{ background: {color('bg_secondary')};"
            f" border: 1px solid {color('border')}; border-radius: 6px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        self.message_label = label(message or "Ready", "text_secondary", 10)
        layout.addWidget(self.message_label, 1)
        self.right_host = QHBoxLayout()
        self.right_host.setSpacing(12)
        layout.addLayout(self.right_host)

    def set_message(self, message: str) -> None:
        self.message_label.setText(message or "Ready")

    def set_right(self, pairs: Optional[list]) -> None:
        """Replace the right-hand readouts. Each item is ``(caption, value)``."""
        while self.right_host.count():
            item = self.right_host.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for caption, value in (pairs or []):
            self.right_host.addWidget(label(f"{caption}  {value}", "text_muted", 10))


# --------------------------------------------------------------------------- #
# settings
# --------------------------------------------------------------------------- #

# Defaults mirror stasys_app.constants; resolved lazily so this module does not
# import core (which may be mid-edit) at import time.
def _defaults() -> dict:
    from .. import constants as k  # noqa: PLC0415 - lazy on purpose
    return {
        "firearm_profile": "FWB_P800",
        "target_type": "10m_air_pistol",
        "target_view_mode": "issf",
        "target_distance": getattr(k, "DEFAULT_TARGET_DISTANCE", 10.0),
        "muzzle_velocity": getattr(k, "DEFAULT_MUZZLE_VELOCITY", 200.0),
        "trigger_pull_time_ms": getattr(k, "DEFAULT_TRIGGER_PULL_TIME", 0.050) * 1000,
        "piezo_threshold": getattr(k, "DEFAULT_PIEZO_MIN", 100),
        "shot_rotation_limit": getattr(k, "DEFAULT_SHOT_ROTATION_LIMIT", 4.0),
    }


class SettingsPanel(QWidget):
    """Clean STASYS settings panel built from available UI concepts.

    MainWindow's ``_build_settings_tab`` is *not* reused: it is an instance
    method that mutates ``MainWindow`` internals (``self.detector``,
    ``self.analysis_canvas``, ...) and writes settings to disk on every change,
    so it cannot be safely shared outside a fully constructed MainWindow. This
    panel therefore exposes the same control concepts as standalone, side-effect
    free widgets driven by caller-supplied values.

    Emits ``settingsChanged(dict)`` on every control change; nothing is
    persisted automatically.
    """

    settingsChanged = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None, *,
                 values: Optional[dict] = None):
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self.setStyleSheet(
            f"QWidget#settingsPanel {{ background: {color('bg_primary')}; }}"
        )
        current = _defaults()
        current.update({k: v for k, v in (values or {}).items() if v is not None})

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        root.addWidget(label("Settings", "text_primary", 16, True))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")
        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(0, 0, 8, 0)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # -- equipment profile ------------------------------------------- #
        self.profile_combo = QComboBox()
        for key, spec in sorted(_profiles().items()):
            self.profile_combo.addItem(spec.get("name", key), key)
        self.profile_combo.setCurrentIndex(
            max(0, self.profile_combo.findData(current["firearm_profile"])))
        form.addRow(_field_label("Feinwerkbau profile"), self.profile_combo)

        # -- target ------------------------------------------------------- #
        self.target_combo = QComboBox()
        for key, spec in _targets().items():
            self.target_combo.addItem(spec.get("name", key), key)
        self.target_combo.setCurrentIndex(
            max(0, self.target_combo.findData(current["target_type"])))
        form.addRow(_field_label("Target type"), self.target_combo)

        self.view_combo = QComboBox()
        self.view_combo.addItem("ISSF target", "issf")
        self.view_combo.addItem("Simple rings", "simple")
        self.view_combo.setCurrentIndex(
            max(0, self.view_combo.findData(current["target_view_mode"])))
        form.addRow(_field_label("Target view"), self.view_combo)

        # -- ballistics --------------------------------------------------- #
        self.distance_spin = self._spin(
            "targetDistance", 5.0, 25.0, 0.5, current["target_distance"], " m")
        form.addRow(_field_label("Target distance"), self.distance_spin)

        self.velocity_spin = self._spin(
            "muzzleVelocity", 100.0, 300.0, 5.0, current["muzzle_velocity"], " m/s")
        form.addRow(_field_label("Muzzle velocity"), self.velocity_spin)

        self.trigger_spin = self._spin(
            "triggerPullTime", 10.0, 200.0, 5.0, current["trigger_pull_time_ms"], " ms")
        form.addRow(_field_label("Trigger pull time"), self.trigger_spin)

        # -- detection ---------------------------------------------------- #
        self.piezo_spin = self._spin(
            "piezoThreshold", 0.0, 4095.0, 10.0, current["piezo_threshold"], "")
        form.addRow(_field_label("Piezo threshold"), self.piezo_spin)

        self.rotation_spin = self._spin(
            "rotationLimit", 1.0, 20.0, 0.5, current["shot_rotation_limit"], " rad/s")
        form.addRow(_field_label("Max trigger rotation"), self.rotation_spin)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        note = label("Controls are side-effect free; an integration layer decides "
                     "whether and when to persist them.", "text_muted", 9, word_wrap=True)
        root.addWidget(note)

        self.profile_combo.currentIndexChanged.connect(self._on_change)
        self.target_combo.currentIndexChanged.connect(self._on_change)
        self.view_combo.currentIndexChanged.connect(self._on_change)
        for spin in (self.distance_spin, self.velocity_spin, self.trigger_spin,
                     self.piezo_spin, self.rotation_spin):
            spin.valueChanged.connect(self._on_change)

    # -- helpers --------------------------------------------------------- #

    @staticmethod
    def _spin(name: str, lo: float, hi: float, step: float, value: float,
              suffix: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setObjectName(name)
        spin.setRange(lo, hi)
        spin.setSingleStep(step)
        spin.setDecimals(1 if step < 1 else 0)
        spin.setValue(float(value))
        if suffix:
            spin.setSuffix(suffix)
        spin.setStyleSheet(
            f"QDoubleSpinBox {{ background: {color('bg_tertiary')};"
            f" color: {color('text_primary')}; border: 1px solid {color('border')};"
            " border-radius: 5px; padding: 5px 8px; font-size: 11px; }"
        )
        return spin

    def _on_change(self, *_args) -> None:
        self.settingsChanged.emit(self.values())

    # -- public API ------------------------------------------------------ #

    def values(self) -> dict:
        """Return the current controls as a settings dict."""
        return {
            "firearm_profile": self.profile_combo.currentData(),
            "target_type": self.target_combo.currentData(),
            "target_view_mode": self.view_combo.currentData(),
            "target_distance": self.distance_spin.value(),
            "muzzle_velocity": self.velocity_spin.value(),
            "trigger_pull_time_ms": self.trigger_spin.value(),
            "piezo_threshold": self.piezo_spin.value(),
            "shot_rotation_limit": self.rotation_spin.value(),
        }

    def set_values(self, values: dict) -> None:
        """Programmatically update the controls without emitting a change."""
        merged = _defaults()
        merged.update({k: v for k, v in (values or {}).items() if v is not None})
        self.profile_combo.blockSignals(True)
        self.target_combo.blockSignals(True)
        self.view_combo.blockSignals(True)
        for spin in (self.distance_spin, self.velocity_spin, self.trigger_spin,
                     self.piezo_spin, self.rotation_spin):
            spin.blockSignals(True)
        self.profile_combo.setCurrentIndex(
            max(0, self.profile_combo.findData(merged["firearm_profile"])))
        self.target_combo.setCurrentIndex(
            max(0, self.target_combo.findData(merged["target_type"])))
        self.view_combo.setCurrentIndex(
            max(0, self.view_combo.findData(merged["target_view_mode"])))
        self.distance_spin.setValue(float(merged["target_distance"]))
        self.velocity_spin.setValue(float(merged["muzzle_velocity"]))
        self.trigger_spin.setValue(float(merged["trigger_pull_time_ms"]))
        self.piezo_spin.setValue(float(merged["piezo_threshold"]))
        self.rotation_spin.setValue(float(merged["shot_rotation_limit"]))
        for spin in (self.distance_spin, self.velocity_spin, self.trigger_spin,
                     self.piezo_spin, self.rotation_spin):
            spin.blockSignals(False)
        self.profile_combo.blockSignals(False)
        self.target_combo.blockSignals(False)
        self.view_combo.blockSignals(False)


def _profiles() -> dict:
    """Feinwerkbau profiles: prefer core, fall back to constants."""
    try:
        from ..core import FEINWERKBAU_PROFILES as p  # noqa: PLC0415
        return p
    except Exception:  # pragma: no cover - core mid-edit fallback
        from .. import constants as k  # noqa: PLC0415
        return getattr(k, "FEINWERKBAU_PROFILES", {})


def _targets() -> dict:
    """Target specs normalized to ``{key: {"name": str, ...}}``.

    The authoritative values are dataclass ``ISSFTargetSpec`` objects, while a
    partial fallback may expose plain dicts -- normalize both shapes so the
    settings panel never depends on which source answered.
    """
    try:
        from ..core import TARGET_SPECS as specs  # noqa: PLC0415
    except Exception:  # pragma: no cover - core mid-edit fallback
        from .. import constants as k  # noqa: PLC0415
        specs = getattr(k, "TARGET_SPECS", {})
    out = {}
    for key, spec in specs.items():
        if isinstance(spec, dict):
            out[key] = dict(spec)
        else:
            out[key] = {"name": getattr(spec, "name", key),
                        "distance_m": getattr(spec, "distance_m", None)}
    return out


class SettingsDialog(QDialog):
    """Modal dialog wrapping a :class:`SettingsPanel`."""

    def __init__(self, parent: Optional[QWidget] = None, *,
                 values: Optional[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(460, 520)
        self.setStyleSheet(f"QDialog {{ background: {color('bg_primary')}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        self.panel = SettingsPanel(self, values=values)
        layout.addWidget(self.panel, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.setStyleSheet(
            f"QDialogButtonBox {{ background: transparent; border: none; }}"
            f"QPushButton {{ color: {color('text_secondary')};"
            f" background: {color('bg_tertiary')}; border: 1px solid {color('border')};"
            " border-radius: 5px; padding: 6px 14px; font-size: 11px; }}"
        )
        layout.addWidget(buttons)

        self.panel.settingsChanged.connect(self._forward)

    def _forward(self, values: dict) -> None:
        self.settingsChanged.emit(values)

    settingsChanged = pyqtSignal(dict)

    def values(self) -> dict:
        return self.panel.values()


__all__ = [
    "EmptyState", "TitleBar", "InfoPane", "TimelineBand", "StatusBar",
    "SettingsPanel", "SettingsDialog",
    "label", "card", "styled_button", "palette_check",
]
