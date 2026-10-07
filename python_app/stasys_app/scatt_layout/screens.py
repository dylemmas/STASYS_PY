"""Composite SCATT-style screens assembled from chrome + STASYS widgets.

Structure reproduced from the statically extracted SCATT Basic QML tree
(``scratch/scatt_extracted/resource_paths.txt``):

    RangeView_Title        -> :class:`TitleBar`
    RangeView_TargetView   -> main aim/target area
    RangeView_TargetView_SidePane -> :class:`InfoPane`
    RangeView_Timeline     -> :class:`TimelineBand` (filmstrip + replay)
    RangeView_Footer       -> :class:`StatusBar`

The practice-mode wizard steps (SelectShooter / SelectTarget /
ConfigureHardware / Calibration / Shooting) are represented by
:class:`StepStrip`, which renders the step sequence and keeps only the active
step visible.

No device, serial or session behaviour lives here: every optional region
defaults to a neutral blank state, and real widgets are supplied by the caller.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .palette import color
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
    styled_button,
)

# Practice-mode wizard steps, in SCATT order (RangeView_PracticeMode_*.qml).
PRACTICE_STEPS = (
    "Select shooter",
    "Select target",
    "Configure hardware",
    "Calibration",
    "Shooting",
)

# Catalog/session browsing steps (RangeView_CatalogMode_*.qml).
CATALOG_STEPS = (
    "Select session",
    "Session view",
)

__all__ = [
    "StepStrip",
    "ShootingScreen",
    "SettingsScreen",
    "PRACTICE_STEPS",
    "CATALOG_STEPS",
]


class StepStrip(QWidget):
    """Horizontal practice/catalog step indicator (SCATT *Step.qml family).

    Steps are plain titles; no fabricated progress or device state is shown.
    """

    stepActivated = pyqtSignal(int, str)

    def __init__(self, steps: Optional[list] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("stepStrip")
        self.setStyleSheet(
            f"QWidget#stepStrip {{ background: {color('bg_secondary')};"
            f" border: 1px solid {color('border')}; border-radius: 6px; }}"
        )
        self._steps = [str(s) for s in (steps or [])]
        self._labels: list[QLabel] = []
        self._active = -1

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(14)
        self._layout = layout
        self._rebuild()
        layout.addStretch(1)

    # -- construction ----------------------------------------------------- #

    def _rebuild(self) -> None:
        for lbl in self._labels:
            self._layout.removeWidget(lbl)
            lbl.deleteLater()
        self._labels = []
        for index, title in enumerate(self._steps):
            lbl = QLabel(f"{index + 1}. {title}")
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.setProperty("stepIndex", index)
            lbl.mouseReleaseEvent = self._make_handler(index, title)
            self._labels.append(lbl)
            self._layout.addWidget(lbl)
        self._apply_style()

    def _make_handler(self, index: int, title: str):
        def handler(_event, _index=index, _title=title):
            self.set_active_step(_index)
            self.stepActivated.emit(_index, _title)
        return handler

    def _apply_style(self) -> None:
        for index, lbl in enumerate(self._labels):
            if index == self._active:
                fg, weight, underline = color("accent_good"), "700", "underline"
            elif 0 <= self._active and index < self._active:
                fg, weight, underline = color("text_secondary"), "500", "none"
            else:
                fg, weight, underline = color("text_muted"), "400", "none"
            lbl.setStyleSheet(
                f"QLabel {{ color: {fg}; font-size: 11px; font-weight: {weight};"
                f" text-decoration: {underline}; background: transparent; }}"
            )

    # -- public API ------------------------------------------------------- #

    def set_steps(self, steps: list) -> None:
        self._steps = [str(s) for s in steps]
        self._active = -1
        self._rebuild()

    def set_active_step(self, index: int) -> None:
        if self._steps and 0 <= index < len(self._steps):
            self._active = index
        else:
            self._active = -1
        self._apply_style()

    @property
    def steps(self) -> list:
        return list(self._steps)

    @property
    def active_index(self) -> int:
        return self._active


class ShootingScreen(QWidget):
    """Main shooting/analysis screen: title, canvas, side pane, timeline, footer.

    All heavy widgets (aim canvas, filmstrip, replay transport, session stats)
    are *injected*. When they are not supplied the regions show a neutral blank
    state -- this class never synthesises shots, scores or device output.

    Supplied widgets are reparented into this screen by Qt; do not share one
    instance across two screens at once.
    """

    settingsRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, *,
                 aim_canvas: Optional[QWidget] = None,
                 filmstrip: Optional[QWidget] = None,
                 replay_bar: Optional[QWidget] = None,
                 stats_widget: Optional[QWidget] = None,
                 detail_widget: Optional[QWidget] = None,
                 mode: str = "Practice",
                 session_title: str = "Session",
                 status: str = "No session selected",
                 show_steps: bool = True,
                 steps: Optional[list] = None):
        super().__init__(parent)
        self.setObjectName("shootingScreen")
        self.setStyleSheet(
            f"QWidget#shootingScreen {{ background: {color('bg_primary')}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        # -- top: mode / session title row -------------------------------- #
        self.title_bar = TitleBar(mode=mode, session_title=session_title)
        self.title_bar.settingsRequested.connect(self.settingsRequested)
        root.addWidget(self.title_bar)

        # -- practice step strip ------------------------------------------ #
        self.step_strip = StepStrip(list(steps) if steps else list(PRACTICE_STEPS))
        self.step_strip.setVisible(show_steps)
        root.addWidget(self.step_strip)

        # -- main area: aim/target canvas + right information pane --------- #
        body = QHBoxLayout()
        body.setSpacing(10)

        self._aim_slot = _CanvasSlot(aim_canvas)
        body.addWidget(self._aim_slot, 1)

        self.info_pane = InfoPane(stats_widget=stats_widget,
                                  detail_widget=detail_widget)
        self.info_pane.settingsRequested.connect(self.settingsRequested)
        body.addWidget(self.info_pane)
        root.addLayout(body, 1)

        # -- bottom: shot filmstrip / timeline ---------------------------- #
        self.timeline = TimelineBand(filmstrip=filmstrip, replay_bar=replay_bar)
        root.addWidget(self.timeline)

        # -- footer / status ---------------------------------------------- #
        self.status_bar = StatusBar(status)
        root.addWidget(self.status_bar)

        # Optional widget injections.
        self.aim_canvas = aim_canvas
        self.filmstrip = filmstrip
        self.replay_bar = replay_bar

        self.title_bar.set_status(status and "READY" or "", role="status_idle")

    # -- public API ------------------------------------------------------- #

    def set_session(self, title: str, mode: str = "", status: str = "") -> None:
        """Update the title row and footer together."""
        self.title_bar.set_session_title(title)
        if mode:
            self.title_bar.set_mode(mode)
        if status:
            self.set_status(status)

    def set_status(self, message: str) -> None:
        """Update the footer message and session placeholder copy."""
        self.status_bar.set_message(message)
        self.info_pane.set_session_state(message)

    def set_aim_canvas(self, widget: Optional[QWidget]) -> None:
        """Inject (or clear) the aim/target canvas."""
        self.aim_canvas = widget
        self._aim_slot.show_widget(widget if widget is not None
                                   else EmptyState(
                                       "No target view",
                                       "Aim and target canvas appear here."))

    def set_filmstrip(self, widget: Optional[QWidget]) -> None:
        self.filmstrip = widget
        self.timeline.set_filmstrip(widget)

    def set_replay_bar(self, widget: Optional[QWidget]) -> None:
        self.replay_bar = widget
        self.timeline.set_replay_bar(widget)

    def set_stats_widget(self, widget: Optional[QWidget]) -> None:
        self.info_pane.set_stats_widget(widget)

    def set_detail_widget(self, widget: Optional[QWidget]) -> None:
        self.info_pane.set_detail_widget(widget)

    def set_steps(self, steps: list) -> None:
        self.step_strip.set_steps(steps)

    def set_active_step(self, index: int) -> None:
        self.step_strip.set_active_step(index)

    @property
    def steps(self) -> list:
        return self.step_strip.steps

    @property
    def active_step(self) -> int:
        return self.step_strip.active_index

    def set_shot_count(self, count: int) -> None:
        self.timeline.set_shot_count(count)


class _CanvasSlot(QWidget):
    """Stable host for the aim/target canvas so it can be swapped."""

    def __init__(self, widget: Optional[QWidget]):
        super().__init__()
        self.setObjectName("canvasSlot")
        self.setStyleSheet(
            f"QWidget#canvasSlot {{ background: {color('bg_secondary')};"
            f" border: 1px solid {color('border')}; border-radius: 8px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self._layout = layout
        self._current: Optional[QWidget] = None
        self.show_widget(widget if widget is not None else EmptyState(
            "No target view", "Aim and target canvas appear here."))

    def show_widget(self, widget: QWidget) -> None:
        if widget is self._current:
            return
        if self._current is not None:
            self._layout.removeWidget(self._current)
            self._current.setParent(None)
        self._layout.addWidget(widget)
        self._current = widget


class SettingsScreen(QWidget):
    """Standalone settings screen hosting a :class:`SettingsPanel`.

    Provided as a screen so the SCATT mode switch (Shooting <-> Settings) can be
    reproduced by stacking this beside :class:`ShootingScreen`.
    """

    settingsChanged = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None, *,
                 values: Optional[dict] = None,
                 show_back: bool = True):
        super().__init__(parent)
        self.setObjectName("settingsScreen")
        self.setStyleSheet(
            f"QWidget#settingsScreen {{ background: {color('bg_primary')}; }}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title_bar = TitleBar(mode="Settings", session_title="Preferences")
        self.title_bar.settings_button.setVisible(False)
        header.addWidget(self.title_bar, 1)
        if show_back:
            self.back_button = styled_button("Back to shooting")
            self.back_button.clicked.connect(self.backRequested)
            header.addWidget(self.back_button)
        root.addLayout(header)

        self.panel_slot = QStackedWidget()
        self.settings_panel = SettingsPanel(values=values)
        self.settings_panel.settingsChanged.connect(self.settingsChanged)
        self.panel_slot.addWidget(self.settings_panel)
        root.addWidget(self.panel_slot, 1)

        self.status_bar = StatusBar("Settings are local until applied.")
        root.addWidget(self.status_bar)

    backRequested = pyqtSignal()

    def values(self) -> dict:
        return self.settings_panel.values()

    def set_values(self, values: dict) -> None:
        self.settings_panel.set_values(values)

    @staticmethod
    def open_dialog(parent: Optional[QWidget] = None, *,
                    values: Optional[dict] = None) -> SettingsDialog:
        """Convenience factory for the modal settings dialog."""
        return SettingsDialog(parent, values=values)
