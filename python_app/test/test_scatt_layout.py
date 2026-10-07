"""Tests for the additive SCATT-style layout package.

Scope discipline: these tests exercise *only* ``stasys_app.scatt_layout``.
Nothing here asserts against core surfaces, and no device, serial, database or
session code is executed. Widgets are built offscreen.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# --------------------------------------------------------------------------- #
# palette
# --------------------------------------------------------------------------- #

def test_palette_resolves_and_exposes_only_existing_roles(qapp):
    from stasys_app.scatt_layout import COLORS, color, palette_check

    palette_check()          # raises if a role this package needs is missing
    assert color("accent_good") == COLORS["accent_good"]
    # Palette must be hex strings, i.e. real usable colors.
    assert all(v.startswith("#") for v in COLORS.values())


def test_palette_sources_are_value_identical(qapp):
    """core and constants both own a COLORS copy; they must not drift."""
    from stasys_app.scatt_layout import colors, reload_colors

    from stasys_app import constants
    assert colors() == dict(constants.COLORS)

    try:
        from stasys_app import core
    except Exception:
        pytest.skip("stasys_app.core not importable in this state")
    assert reload_colors() == dict(core.COLORS)
    assert colors() == dict(constants.COLORS)


def test_palette_falls_back_when_core_unimportable(qapp, monkeypatch):
    """If core cannot be imported, the palette still resolves via constants."""
    import builtins

    from stasys_app.scatt_layout import palette

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.endswith("core") or name == "stasys_app.core":
            raise ImportError("core deliberately unavailable for this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    monkeypatch.setattr(palette, "_cache", None)
    monkeypatch.setattr(palette, "_source", "")
    try:
        resolved = palette.colors()
        assert resolved == dict(__import__(
            "stasys_app.constants", fromlist=["COLORS"]).COLORS)
        assert palette.source() == "constants"
    finally:
        monkeypatch.setattr(builtins, "__import__", real_import)
        palette.reload_colors()


def test_package_contains_no_hardcoded_colors(qapp):
    """Every color in the new module must come from the STASYS palette."""
    import pathlib
    import re

    pkg = pathlib.Path(__file__).resolve().parents[1] / "stasys_app" / "scatt_layout"
    offenders = []
    for path in sorted(pkg.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            # allow hex values only inside palette.py doc/comment prose
            if re.search(r"#[0-9A-Fa-f]{3,8}\b", line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "hardcoded colors found:\n" + "\n".join(offenders)


def test_no_scatt_branding_or_brand_literals(qapp):
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parents[1] / "stasys_app" / "scatt_layout"
    for path in pkg.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for banned in ("scatt electronics", "scattbasic", "www.scatt.com",
                       "1993-", "scatt_basic"):
            assert banned not in text, f"{path.name} contains brand literal {banned!r}"


# --------------------------------------------------------------------------- #
# blank / error states
# --------------------------------------------------------------------------- #

def test_empty_state_is_neutral_and_updatable(qapp):
    from stasys_app.scatt_layout import EmptyState

    state = EmptyState("Nothing here", "And no fake data.")
    assert "Nothing here" in state.findChildren(QLabel)[0].text()
    # neutral: never renders a number, score, or device token
    joined = " ".join(w.text() for w in state.findChildren(QLabel))
    assert not any(ch.isdigit() for ch in joined)
    state.set_message("Offline", "Device unavailable.")
    joined = " ".join(w.text() for w in state.findChildren(QLabel))
    assert "Offline" in joined and "Device unavailable." in joined


def test_settings_panel_defaults_to_blank_not_fake_output(qapp):
    from stasys_app.scatt_layout import ShootingScreen

    screen = ShootingScreen()          # no injected widgets
    labels = " ".join(w.text() for w in screen.findChildren(QLabel))
    assert "No session selected" in labels
    assert "No shots yet" in labels
    assert "No target view" in labels


# --------------------------------------------------------------------------- #
# SCATT screen structure
# --------------------------------------------------------------------------- #

def test_shooting_screen_has_all_scatt_regions(qapp):
    from stasys_app.scatt_layout import ShootingScreen

    screen = ShootingScreen(session_title="Series A", mode="Practice",
                            status="Idle")
    # RangeView_Title / TargetView / SidePane / Timeline / Footer
    assert screen.title_bar is not None
    assert screen.info_pane is not None
    assert screen.timeline is not None
    assert screen.status_bar is not None
    assert screen.step_strip.isVisibleTo(screen)          # steps present
    assert screen.title_bar.title_label.text() == "Series A"
    assert screen.title_bar.mode_badge.text() == "Practice"
    assert screen.status_bar.message_label.text() == "Idle"
    # stacked top -> bottom
    kids = [screen.layout().itemAt(i).widget() for i in range(screen.layout().count())]
    order = [type(k).__name__ for k in kids if k is not None]
    assert order.index("TitleBar") < order.index("StepStrip") < order.index("TimelineBand")
    assert order.index("TimelineBand") < order.index("StatusBar")


def test_practice_step_strip_reflects_extracted_step_order(qapp):
    from stasys_app.scatt_layout import PRACTICE_STEPS, ShootingScreen, StepStrip

    assert PRACTICE_STEPS == ("Select shooter", "Select target",
                              "Configure hardware", "Calibration", "Shooting")
    screen = ShootingScreen()
    assert screen.step_strip.steps == list(PRACTICE_STEPS)
    strip = StepStrip(list(PRACTICE_STEPS))
    assert [s.text() for s in strip._labels][0].startswith("1. Select shooter")
    strip.set_active_step(2)
    assert strip.active_index == 2
    assert "font-weight: 700" in strip._labels[2].styleSheet()   # active = bold
    # out-of-range index is ignored rather than crashing
    strip.set_active_step(99)
    assert strip.active_index == -1


def test_shooting_screen_setters_swap_and_clear_widgets(qapp):
    from stasys_app.scatt_layout import ShootingScreen

    screen = ShootingScreen()
    holder = QWidget()
    screen.set_aim_canvas(holder)
    assert screen.aim_canvas is holder
    assert holder.parent() is not None                     # reparented in
    screen.set_aim_canvas(None)
    assert screen.aim_canvas is None                       # back to blank state


def test_injected_widgets_land_in_the_expected_slots(qapp):
    from stasys_app.scatt_layout import ShootingScreen

    stats, detail = QWidget(), QWidget()
    strip_holder, replay_holder = QWidget(), QWidget()
    screen = ShootingScreen(stats_widget=stats, detail_widget=detail,
                            filmstrip=strip_holder, replay_bar=replay_holder)
    assert stats in screen.info_pane.findChildren(QWidget) or \
        screen.info_pane.stats_widget is stats
    assert screen.info_pane.detail_widget is detail
    assert screen.timeline.filmstrip is strip_holder
    assert screen.timeline.replay_bar is replay_holder
    # each injected widget has a real parent (actually placed)
    for w in (stats, detail, strip_holder, replay_holder):
        assert w.parent() is not None


def test_title_chips_and_status_role_are_palette_driven(qapp):
    from stasys_app.scatt_layout import COLORS, TitleBar

    bar = TitleBar(mode="Catalog", session_title="Session")
    bar.set_chips([("AVG", "--"), ("SHOTS", "0")])
    texts = [w.text() for w in bar.findChildren(QLabel)]
    assert "AVG" in texts and "SHOTS" in texts
    bar.set_status("ARMED", role="status_armed")
    assert bar.status_badge.isVisibleTo(bar)
    assert COLORS["status_armed"] in bar.status_badge.styleSheet()


def test_title_settings_button_emits_signal(qapp):
    from stasys_app.scatt_layout import ShootingScreen

    screen = ShootingScreen()
    seen = []
    screen.settingsRequested.connect(lambda: seen.append(True))
    screen.title_bar.settings_button.click()
    screen.info_pane.settings_button.click()
    assert seen == [True, True]


def test_timeline_shot_count_wording(qapp):
    from stasys_app.scatt_layout import TimelineBand

    band = TimelineBand()
    band.set_shot_count(0)
    assert band.shot_count_label.text() == "0 shots"
    band.set_shot_count(1)
    assert band.shot_count_label.text() == "1 shot"
    band.set_shot_count(12)
    assert band.shot_count_label.text() == "12 shots"


def test_status_bar_right_readouts(qapp):
    from stasys_app.scatt_layout import StatusBar

    bar = StatusBar("Ready")
    bar.set_right([("MODE", "Dry Fire"), ("TARGET", "10 m")])
    texts = [w.text() for w in bar.findChildren(QLabel)]
    assert any("MODE" in t and "Dry Fire" in t for t in texts)
    bar.set_message("Connected")
    assert bar.message_label.text() == "Connected"


# --------------------------------------------------------------------------- #
# settings
# --------------------------------------------------------------------------- #

def test_settings_panel_round_trips_values_without_side_effects(qapp):
    from stasys_app.scatt_layout import SettingsPanel

    payload = {
        "firearm_profile": "FWB_700_RIFLE",
        "target_type": "10m_air_rifle",
        "target_view_mode": "simple",
        "target_distance": 10.0,
        "muzzle_velocity": 170.0,
        "trigger_pull_time_ms": 35.0,
        "piezo_threshold": 400.0,
        "shot_rotation_limit": 4.0,
    }
    panel = SettingsPanel(values=payload)
    out = panel.values()
    for key, expected in payload.items():
        assert out[key] == expected, key

    # round trip is stable and emits no spurious change signal on set_values
    seen = []
    panel.settingsChanged.connect(lambda v: seen.append(v))
    panel.set_values(dict(payload, target_distance=20.0))
    assert seen == []
    assert panel.values()["target_distance"] == 20.0


def test_settings_panel_emits_on_user_edit(qapp):
    from stasys_app.scatt_layout import SettingsPanel

    panel = SettingsPanel()
    seen = []
    panel.settingsChanged.connect(lambda v: seen.append(v))
    panel.distance_spin.setValue(15.0)
    assert len(seen) == 1
    assert seen[0]["target_distance"] == 15.0


def test_settings_panel_uses_real_profile_and_target_names(qapp):
    from stasys_app import constants
    from stasys_app.scatt_layout import SettingsPanel

    panel = SettingsPanel()
    profile_ids = {panel.profile_combo.itemData(i)
                   for i in range(panel.profile_combo.count())}
    assert profile_ids == set(constants.FEINWERKBAU_PROFILES)
    target_ids = {panel.target_combo.itemData(i)
                  for i in range(panel.target_combo.count())}
    assert target_ids == set(constants.TARGET_SPECS)


def test_settings_dialog_wraps_panel(qapp):
    from stasys_app.scatt_layout import SettingsDialog

    seen = []
    dialog = SettingsDialog(values={"target_distance": 12.5})
    dialog.settingsChanged.connect(lambda v: seen.append(v))
    assert dialog.values()["target_distance"] == 12.5
    dialog.panel.distance_spin.setValue(18.0)
    assert seen and seen[-1]["target_distance"] == 18.0
    dialog.reject()


def test_settings_screen_exposes_back_navigation(qapp):
    from stasys_app.scatt_layout import SettingsScreen

    screen = SettingsScreen(values={"muzzle_velocity": 180.0})
    fired = []
    screen.backRequested.connect(lambda: fired.append(True))
    screen.back_button.click()
    assert fired == [True]
    assert screen.values()["muzzle_velocity"] == 180.0


# --------------------------------------------------------------------------- #
# package hygiene
# --------------------------------------------------------------------------- #

def test_package_does_not_import_itself_into_core(qapp):
    """core must not import scatt_layout at module level (no import cycle).

    A *function-level* lazy import is allowed: scatt_layout only touches
    core while init_ui is running, long after core finished importing.
    Only top-level imports would create the cycle this test guards against.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "stasys_app"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:  # module level only, not inside functions/classes
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "scatt_layout" in mod:
                    raise AssertionError(
                        f"{path.name} imports scatt_layout at module level")
            elif isinstance(node, ast.Import):
                if any("scatt_layout" in (a.name or "") for a in node.names):
                    raise AssertionError(
                        f"{path.name} imports scatt_layout at module level")


def test_public_surface_is_importable_from_package_root(qapp):
    import stasys_app.scatt_layout as pkg

    for name in pkg.__all__:
        assert hasattr(pkg, name), name


def test_step_strip_click_emits_index(qapp):
    from stasys_app.scatt_layout import StepStrip

    strip = StepStrip(["Alpha", "Beta"])
    got = []
    strip.stepActivated.connect(lambda i, t: got.append((i, t)))
    from PyQt5.QtGui import QMouseEvent  # noqa: F401  (event class exists)
    strip._labels[1].mouseReleaseEvent(None)
    assert got == [(1, "Beta")]
    assert strip.active_index == 1


def _make_mainwindow(qapp, legacy: bool, monkeypatch):
    """Build a MainWindow using the SCATT default or legacy escape hatch."""
    if legacy:
        monkeypatch.setenv("STASYS_LAYOUT", "legacy")
    else:
        monkeypatch.delenv("STASYS_LAYOUT", raising=False)

    from stasys_app.connection import MockSerial
    from stasys_app.SL import MainWindow

    window = MainWindow(MockSerial())
    timer = getattr(window, "timer", None)
    if timer is not None:
        timer.stop()
    return window


def test_scatt_layout_is_default(qapp, monkeypatch):
    """With no env override, SCATT chrome wraps the unchanged five tabs."""
    window = _make_mainwindow(qapp, False, monkeypatch)
    try:
        assert hasattr(window, "scatt_title_bar")
        assert hasattr(window, "scatt_status_bar")
        assert window.tabs.count() == 5
        titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert "Settings" in titles
        central = window.centralWidget()
        assert window.scatt_title_bar.parent() is central
        assert window.scatt_status_bar.parent() is central
    finally:
        window.close()


def test_simulation_indicator_survives_default_chrome(qapp, monkeypatch):
    """The default chrome must keep a SIMULATION indicator (legacy header
    that used to carry it is hidden when SCATT chrome installs)."""
    monkeypatch.delenv("STASYS_LAYOUT", raising=False)
    window = _make_mainwindow(qapp, False, monkeypatch)
    try:
        # MockSerial exposes update_sim, so the legacy badge would show
        # "SIMULATION MODE"; the SCATT title bar must show it too.
        badge = window.scatt_title_bar.status_badge
        assert badge.text() == "SIMULATION"
        assert badge.isVisibleTo(window.scatt_title_bar)
        # legible pairing: amber accent_ok background, dark bg_primary text
        # (the review found status_arming + light text was unreadable 1.76:1)
        from stasys_app.core import COLORS
        css = badge.styleSheet()
        assert COLORS["accent_ok"] in css
        assert COLORS["bg_primary"] in css
    finally:
        window.close()


def test_legacy_layout_with_escape_hatch(qapp, monkeypatch):
    """STASYS_LAYOUT=legacy keeps the original header and tabs."""
    window = _make_mainwindow(qapp, True, monkeypatch)
    try:
        assert not hasattr(window, "scatt_title_bar")
        assert not hasattr(window, "scatt_status_bar")
        assert window.tabs.count() == 5
    finally:
        window.close()


def test_core_direct_launcher_reuses_connection_parser():
    """The canonical core.py launcher forwards the authenticated parser."""
    import ast
    import pathlib

    core_path = pathlib.Path(__file__).resolve().parents[1] / "stasys_app" / "core.py"
    tree = ast.parse(core_path.read_text(encoding="utf-8"))
    main_block = next(
        node for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
    )
    calls = [node for node in ast.walk(main_block) if isinstance(node, ast.Call)]
    window_call = next(
        node for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "MainWindow"
    )
    assert len(window_call.args) == 2
    assert isinstance(window_call.args[0], ast.Attribute)
    assert window_call.args[0].attr == "serial_port"
    assert isinstance(window_call.args[1], ast.Attribute)
    assert window_call.args[1].attr == "parser"
    assert isinstance(window_call.args[1].value, ast.Name)
    assert window_call.args[1].value.id == "conn"
