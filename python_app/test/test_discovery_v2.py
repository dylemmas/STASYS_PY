"""Tests for banner-only, write-zero-probe SPP v2 discovery (Task 6).

Contract pinned here (task-6-brief.md):

  discover_stasys_devices() -> list[tuple[serial.Serial, str, bytes]]

    banner-only: open each candidate port, accumulate read(256) up to
    BANNER_TIMEOUT_S (module-level, read at call time), split lines on \\n;
    accept iff line 1 == 'READY v=2' and line 2 is 'AUTH ' + exactly 64
    lowercase hex chars.  Never write, never sleep, never
    reset_input_buffer — the write-zero-probe invariant is the regression pin
    for the legacy garbage-challenge bug (CHANGELOG_FIXES Fix #1).
    Winner stays OPEN with its raw banner bytes; non-match/timeout closes and
    continues.  First match wins over sorted ports; OSError -> continue.

  Candidate selection is metadata-driven: only Bluetooth (BTHENUM) ports
    are opened, MAC-bearing endpoints are tried before the generic pairing
    endpoint, and the winning port carries its 6-byte MAC as spp_identity.

  attempt_stasys_connection(parser)  one full attempt, no widget access:
    none          -> no banner; the screen retries every RETRY_INTERVAL_MS
                     (there is no one-shot fallback anymore)
    config        -> banner seen, credentials missing: port closed, no
                     handshake, config-missing detail
    auth_failed   -> port closed, detail returned
    error         -> unexpected failure AFTER a port was discovered: that
                     port is closed and the screen must NOT retry
    connected     -> port stays OPEN, advance_generation already ran
  ConnectionScreen routes outcomes on the GUI thread; Continue/reject set a
  cancel event so in-flight workers stop and close their ports instead of
  handing a live handle to the simulation path.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

APP_PATH = str(REPO_ROOT / 'python_app' / 'stasys_app')
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)
# Needed so `stasys_app.connection` (relative imports inside) resolves as a package.
PY_ROOT = str(REPO_ROOT / 'python_app')
if PY_ROOT not in sys.path:
    sys.path.insert(0, PY_ROOT)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import core  # noqa: E402  (sys.path set up above)


V2_BANNER = b"READY v=2\nAUTH " + b"a" * 64 + b"\n"


class FakePort:
    """Scripted serial port: reads come from a caller-chosen chunk list."""

    def __init__(self, port, baud, timeout=0.5, chunks=()):
        self.port = port
        self.baudrate = baud
        self.timeout = timeout
        self.chunks = list(chunks)
        self.writes = []
        self.closed = False
        self.is_open = True
        self.description = "fake %s" % port
        # Blocks like a serial read at its timeout without calling
        # time.sleep - discovery must never call time.sleep explicitly.
        self._idle = threading.Event()

    def read(self, _size):
        if not self.chunks:
            self._idle.wait(min(self.timeout, 0.005))
            return b""
        return self.chunks.pop(0)

    def write(self, data):
        self.writes.append(bytes(data))

    def close(self):
        self.closed = True
        self.is_open = False

    def reset_input_buffer(self):
        raise AssertionError("discovery must not flush the input buffer")


@pytest.fixture(scope="module")
def core_mod():
    import core
    return core


@pytest.fixture
def discover(core_mod, monkeypatch):
    """Patch comports + serial.Serial in core's namespace; return the harness."""
    opened = []
    scripts = {}

    def serial_factory(port, baud, timeout=0.5):
        fake = FakePort(port, baud, timeout, scripts.get(port, ()))
        opened.append(fake)
        return fake

    monkeypatch.setattr(core_mod.serial, "Serial", serial_factory)
    # hwid metadata per port ("" -> attribute-less fake, kept by the
    # no-metadata rule of _is_bluetooth_port).
    meta = {}

    def fake_comports():
        return [
            SimpleNamespace(device=p, hwid=meta.get(p, ""),
                            description=meta.get(p + "#desc", ""))
            for p in scripts
        ]

    monkeypatch.setattr(
        core_mod.serial.tools.list_ports, "comports", fake_comports,
    )
    # BANNER_TIMEOUT_S must be read at call time so tests can shrink it.
    monkeypatch.setattr(core_mod, "BANNER_TIMEOUT_S", 0.02, raising=False)

    def run(**scripts_in):
        scripts.update(scripts_in)
        return core_mod.discover_stasys_devices()

    run.opened = opened
    run.meta = meta
    return run


def test_v2_banner_found_write_zero_probe_and_banner_returned(discover):
    """v2 banner -> found, no writes, port left open, raw banner returned."""
    found = discover(**{"COM3": [V2_BANNER]})

    assert len(found) == 1, found
    ser, desc, banner = found[0]
    assert ser.port == "COM3"
    assert ser.writes == []          # write-zero-probe invariant
    assert not ser.closed            # winner stays open for perform_auth_v2
    assert banner == V2_BANNER       # raw bytes, byte-for-byte
    assert desc  # description present (str, may come from fake)


def test_no_banner_within_timeout_returns_empty_and_closes_port(discover):
    """Silent port times out -> [], port closed, nothing written."""
    found = discover(**{"COM1": []})

    assert found == []
    assert len(discover.opened) == 1
    assert discover.opened[0].closed
    assert discover.opened[0].writes == []


def test_legacy_ready_broadcast_rejected_without_write(discover):
    """Regression pin: legacy 'READY\\n' must NOT trigger a garbage write."""
    found = discover(**{"COM1": [b"READY\n"]})

    assert found == []
    assert discover.opened[0].writes == []
    assert discover.opened[0].closed


def test_first_match_wins_over_sorted_ports(discover):
    """Two valid v2 ports: lowest sorted port wins, the other is closed."""
    banner_hi = b"READY v=2\nAUTH " + b"b" * 64 + b"\n"
    found = discover(**{"COM10": [banner_hi], "COM2": [V2_BANNER]})

    assert len(found) == 1, found
    ser, _desc, banner = found[0]
    # sorted() puts COM10 before COM2 lexicographically; COM10 must win
    # and scanning must stop there — COM2 is never opened.
    assert ser.port == "COM10"
    assert banner == banner_hi
    assert [p.port for p in discover.opened] == ["COM10"]


def test_uppercase_hex_rejected(discover):
    """AUTH line must be exactly 64 lowercase hex chars."""
    bad = b"READY v=2\nAUTH " + b"A" * 64 + b"\n"
    found = discover(**{"COM1": [bad]})
    assert found == []
    assert discover.opened[0].closed


def test_osp_exception_continues_to_next_port(discover, monkeypatch, core_mod):
    """OSError on one port -> continue scanning, never raised to UI."""
    calls = []

    def serial_factory(port, baud, timeout=0.5):
        if port == "COM1":
            raise OSError("cannot open")
        fake = FakePort(port, baud, timeout, chunks=[V2_BANNER])
        opened.append(fake)
        return fake

    opened = []
    scripts = {"COM1": [], "COM2": [V2_BANNER]}
    monkeypatch.setattr(core_mod.serial, "Serial", serial_factory)
    monkeypatch.setattr(
        core_mod.serial.tools.list_ports, "comports",
        lambda: [SimpleNamespace(device=p) for p in scripts],
    )
    monkeypatch.setattr(core_mod, "BANNER_TIMEOUT_S", 0.02, raising=False)

    found = core_mod.discover_stasys_devices()
    assert len(found) == 1
    assert found[0][0].port == "COM2"


def _stub_screen(core_mod):
    """GUI-thread routing stub for ConnectionScreen._on_attempt_done."""
    class StubScreen:
        def __init__(self):
            self._cancel_event = threading.Event()
            self._attempts = 0
            self.serial_port = None
            self.detail_texts = []
            self.detail_label = SimpleNamespace(
                setText=self.detail_texts.append)
            self.shown = []
            self.retries = 0

        def _show_success(self, port, desc):
            self.shown.append(("success", port, desc))

        def _show_auth_failure(self, detail):
            self.shown.append(("failed", detail))

        def _schedule_retry(self):
            self.retries += 1

    return StubScreen()


def test_attempt_auth_failure_closes_port_and_returns_detail_verbatim(
        monkeypatch, core_mod):
    """Banner found, handshake fails -> auth_failed + detail verbatim."""
    detail = "firmware rejected the key — a stock build"
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close
    advanced = []

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config",
                        lambda **kw: (b"k", b"\x01\x02\x03\x04\x05\x06", 3))
    monkeypatch.setattr(core_mod, "perform_auth_v2",
                        lambda *a, **kw: (False, detail))
    monkeypatch.setattr(core_mod, "advance_generation",
                        lambda g: advanced.append(g))

    status, payload = core_mod.attempt_stasys_connection(None)

    assert status == "auth_failed"
    assert payload == detail, "detail must pass through verbatim"
    assert port.closed, "failed auth must close the port"
    assert advanced == [], "generation must never advance on auth failure"


def test_attempt_success_advances_generation_and_returns_open_port(
        monkeypatch, core_mod):
    """connected -> advance_generation ran, port stays OPEN."""
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close
    advanced = []

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config",
                        lambda **kw: (b"k", b"\x01\x02\x03\x04\x05\x06", 3))
    monkeypatch.setattr(core_mod, "perform_auth_v2",
                        lambda *a, **kw: (True, "authenticated"))
    monkeypatch.setattr(core_mod, "advance_generation",
                        lambda g: advanced.append(g))

    status, payload = core_mod.attempt_stasys_connection(None)

    assert status == "connected"
    ser, desc = payload
    assert ser is port and desc == "STASYS v2"
    assert not port.closed, "authenticated port must stay open"
    assert advanced == [3]


def test_attempt_missing_config_closes_port_without_handshake(
        monkeypatch, core_mod):
    """cfg is None -> config + port closed, handshake never starts."""
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close
    auth_called = []

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config", lambda **kw: None)
    monkeypatch.setattr(core_mod, "perform_auth_v2",
                        lambda *a, **kw: auth_called.append(True) or (True, "x"))

    status, payload = core_mod.attempt_stasys_connection(None)

    assert status == "config"
    assert port.closed
    assert not auth_called, "handshake must not start without config"
    assert "STASYS_DEVICE_KEY" in payload and "STASYS_DEVICE_IDENTITY" in payload
    assert "simulation" in payload.lower()


def test_attempt_no_banner_returns_none_for_retry(monkeypatch, core_mod):
    """No device -> ('none', None); a broken enumerator is terminal."""
    monkeypatch.setattr(core_mod, "discover_stasys_devices", lambda: [])
    assert core_mod.attempt_stasys_connection(None) == ("none", None)

    def boom():
        raise RuntimeError("enumeration exploded")
    monkeypatch.setattr(core_mod, "discover_stasys_devices", boom)
    status, detail = core_mod.attempt_stasys_connection(None)
    assert status == "error"
    assert "enumeration failed" in detail


def test_on_attempt_done_connected_shows_success(monkeypatch, core_mod):
    """connected routes to _show_success and stores the open port."""
    stub = _stub_screen(core_mod)
    port = SimpleNamespace(port="COM6")

    core_mod.ConnectionScreen._on_attempt_done(
        stub, ("connected", (port, "STASYS v2 (COM6)")))

    assert stub.serial_port is port
    assert stub.shown == [("success", "COM6", "STASYS v2 (COM6)")]
    assert stub.retries == 0, "success must not schedule another attempt"


def test_on_attempt_done_terminal_states_never_retry(monkeypatch, core_mod):
    """config / auth_failed -> _show_auth_failure, NO further attempts."""
    stub = _stub_screen(core_mod)
    detail = "detail-x"

    core_mod.ConnectionScreen._on_attempt_done(stub, ("auth_failed", detail))
    assert stub.shown == [("failed", detail)]
    assert stub.retries == 0, "a seen banner must not trigger a rescan"
    assert stub.serial_port is None

    stub2 = _stub_screen(core_mod)
    core_mod.ConnectionScreen._on_attempt_done(stub2, ("config", detail))
    assert stub2.shown == [("failed", detail)]
    assert stub2.retries == 0


def test_on_attempt_done_none_counts_attempt_and_schedules_retry(core_mod):
    """No device yet -> attempt counter on the detail line + auto-retry."""
    stub = _stub_screen(core_mod)

    core_mod.ConnectionScreen._on_attempt_done(stub, ("none", None))

    assert stub.shown == []
    assert stub.retries == 1, "no-banner must schedule the next attempt"
    assert "attempt 1" in stub.detail_texts[0]

    core_mod.ConnectionScreen._on_attempt_done(stub, ("none", None))
    assert stub.retries == 2
    assert "attempt 2" in stub.detail_texts[-1]


def test_on_attempt_done_ignored_after_cancel(core_mod):
    """Cancel wins over a result that slipped through."""
    stub = _stub_screen(core_mod)
    stub._cancel_event.set()

    core_mod.ConnectionScreen._on_attempt_done(
        stub, ("connected", (SimpleNamespace(port="COM6"), "x")))

    assert stub.shown == []
    assert stub.retries == 0
    assert stub.serial_port is None


def test_on_continue_cancels_timers_and_enters_simulation(core_mod):
    """Continue in Simulation: cancel flag set, timers stopped, MockSerial."""
    stub = _stub_screen(core_mod)
    stopped = []
    stub._retry_timer = SimpleNamespace(stop=lambda: stopped.append("retry"))
    stub._anim_timer = SimpleNamespace(stop=lambda: stopped.append("anim"))
    accepted = []
    stub.accept = lambda: accepted.append(True)

    core_mod.ConnectionScreen._on_continue(stub)

    assert stub._cancel_event.is_set()
    assert stopped == ["retry", "anim"]
    assert stub.is_simulation is True
    assert isinstance(stub.serial_port, core_mod.MockSerial)
    assert accepted == [True]


def test_launch_attempt_is_a_noop_once_cancelled(core_mod):
    """After cancel/continue no new worker may start."""
    cancel = threading.Event()
    cancel.set()
    stub = SimpleNamespace(_cancel_event=cancel, serial_port=None,
                           _workers=[])

    core_mod.ConnectionScreen._launch_attempt(stub)

    assert stub._workers == []


def test_connection_worker_emits_result(monkeypatch, core_mod):
    """Worker forwards attempt_stasys_connection's result to the GUI."""
    monkeypatch.setattr(core_mod, "attempt_stasys_connection",
                        lambda p: ("none", None))
    worker = core_mod._ConnectionWorker(None, threading.Event())
    got = []
    worker.attempt_done.connect(got.append)

    worker.run()  # synchronous: same-thread emit -> direct delivery

    assert got == [("none", None)]


def test_connection_worker_cancel_silently_closes_would_be_connection(
        monkeypatch, core_mod):
    """Cancelled worker emits nothing and closes its authenticated port."""
    closed = []
    port = SimpleNamespace(
        port="COM6", close=lambda: closed.append(True))

    def fake_attempt(p):
        return "connected", (port, "STASYS v2")
    monkeypatch.setattr(core_mod, "attempt_stasys_connection", fake_attempt)

    cancel = threading.Event()
    cancel.set()
    worker = core_mod._ConnectionWorker(None, cancel)
    got = []
    worker.attempt_done.connect(got.append)

    worker.run()

    assert got == [], "cancelled attempt must not reach the GUI"
    assert closed == [True], "the live port must be closed, not leaked"


# ---- metadata-driven candidate selection -----------------------------------

BTH_MAC_HWID = (
    "BTHENUM\\{00001101-0000-1000-8000-00805F9B34FB}_LOCALMFG&005D"
    "\\7&1AB7E702&0&781C3CF5161A_C00000000"
)
BTH_GENERIC_HWID = (
    "BTHENUM\\{00001101-0000-1000-8000-00805F9B34FB}_LOCALMFG&0000"
    "\\7&1AB7E702&0&000000000000_00000000"
)
USB_HWID = "USB\\VID_1A86&PID_7523&REV_0264"


def test_extract_port_mac_real_generic_and_malformed(core_mod):
    mac = core_mod._extract_port_mac(BTH_MAC_HWID)
    assert mac == bytes.fromhex("781C3CF5161A")
    # all-zero placeholder endpoint identifies no device
    assert core_mod._extract_port_mac(BTH_GENERIC_HWID) is None
    assert core_mod._extract_port_mac(USB_HWID) is None
    assert core_mod._extract_port_mac("") is None
    assert core_mod._extract_port_mac(None) is None
    assert core_mod._extract_port_mac(
        "BTHENUM\\{x}_LOCALMFG&005D\\7&1AB7E702&0&NOPE1234567_0") is None


def test_is_bluetooth_port_filters_usb_serials(core_mod):
    assert core_mod._is_bluetooth_port(
        SimpleNamespace(hwid=BTH_MAC_HWID, description="")) is True
    assert core_mod._is_bluetooth_port(
        SimpleNamespace(hwid="", description="Standard Serial over "
                                             "Bluetooth link (COM5)")) is True
    assert core_mod._is_bluetooth_port(
        SimpleNamespace(hwid=USB_HWID,
                        description="USB-SERIAL CH340 (COM4)")) is False
    # no metadata at all (test fakes / exotic backends) is kept
    assert core_mod._is_bluetooth_port(
        SimpleNamespace(hwid="", description="")) is True


def test_usb_serial_port_is_never_opened(discover):
    """CH340-style ports must not be probed; Bluetooth ports still are."""
    discover.meta["COM4"] = USB_HWID
    found = discover(**{"COM4": [], "COM2": [V2_BANNER]})

    assert len(found) == 1
    assert found[0][0].port == "COM2"
    opened = [p.port for p in discover.opened]
    assert "COM4" not in opened, "non-Bluetooth port must never be opened"


def test_mac_bearing_endpoint_tried_before_generic(discover):
    """Priority 0 (device MAC) beats lexicographic order (COM2 < COM10)."""
    banner_hi = b"READY v=2\nAUTH " + b"b" * 64 + b"\n"
    discover.meta["COM2"] = BTH_GENERIC_HWID
    discover.meta["COM10"] = BTH_MAC_HWID

    found = discover(**{"COM2": [V2_BANNER], "COM10": [banner_hi]})

    assert len(found) == 1
    assert found[0][0].port == "COM10"
    assert [p.port for p in discover.opened] == ["COM10"], \
        "generic endpoint must not even open when the MAC endpoint wins"


def test_winner_carries_extracted_mac_identity(discover):
    discover.meta["COM3"] = BTH_MAC_HWID
    found = discover(**{"COM3": [V2_BANNER]})
    assert found[0][0].spp_identity == bytes.fromhex("781C3CF5161A")


def test_winner_without_mac_carries_none_identity(discover):
    found = discover(**{"COM3": [V2_BANNER]})
    assert found[0][0].spp_identity is None


# ---- identity fallback in _load_spp_config ---------------------------------

def _config_env(monkeypatch, core_mod):
    monkeypatch.setenv("STASYS_DEVICE_KEY", "unit-test-key")
    monkeypatch.delenv("STASYS_DEVICE_IDENTITY", raising=False)
    monkeypatch.delenv("STASYS_GENERATION", raising=False)
    monkeypatch.setattr(core_mod, "load_settings", lambda: {})


def test_config_derives_identity_from_port_mac(monkeypatch, core_mod):
    """No configured identity -> the port MAC becomes the identity."""
    _config_env(monkeypatch, core_mod)

    cfg = core_mod._load_spp_config(
        fallback_identity=bytes.fromhex("781C3CF5161A"))

    assert cfg is not None
    assert cfg[0] == b"unit-test-key"
    assert cfg[1] == bytes.fromhex("781C3CF5161A")
    assert cfg[2] == 1


def test_configured_identity_wins_over_port_mac(monkeypatch, core_mod):
    """An explicit identity always beats the derived one."""
    _config_env(monkeypatch, core_mod)
    monkeypatch.setenv("STASYS_DEVICE_IDENTITY", "01:02:03:04:05:06")

    cfg = core_mod._load_spp_config(
        fallback_identity=bytes.fromhex("781C3CF5161A"))

    assert cfg[1] == bytes.fromhex("010203040506")


def test_bad_fallback_identity_is_ignored(monkeypatch, core_mod):
    """A malformed derived MAC fails closed instead of authenticating."""
    _config_env(monkeypatch, core_mod)

    assert core_mod._load_spp_config(fallback_identity=b"\x01\x02") is None
    assert core_mod._load_spp_config(fallback_identity=None) is None


# ---- review-fix coverage (Fix #3 review round) ------------------------------

def test_discovery_never_calls_time_sleep(core_mod, monkeypatch, discover):
    """No-sleep contract: discovery must not call time.sleep explicitly."""
    def trap(*a, **kw):
        raise AssertionError("discovery must not call time.sleep")
    monkeypatch.setattr(core_mod.time, "sleep", trap)
    found = discover(**{"COM3": [V2_BANNER]})
    assert len(found) == 1


def test_extract_port_mac_suffixed_and_overlong(core_mod):
    """Suffix text after the 12 digits is tolerated (review Important #3)."""
    base = "BTHENUM\\{x}_LOCALMFG&005D\\7&1AB7E702&0&"
    assert core_mod._extract_port_mac(
        base + "781C3CF5161AXYZ_0") == bytes.fromhex("781C3CF5161A")
    assert core_mod._extract_port_mac(
        base + "781C3CF5161A-suffix") == bytes.fromhex("781C3CF5161A")
    # A 13-hex run is ambiguous; fail closed instead of truncating a digit.
    assert core_mod._extract_port_mac(base + "781C3CF5161A7_0") is None


def test_duplicate_port_entries_are_opened_once(monkeypatch, core_mod):
    """Duplicate comports entries collapse to one open attempt."""
    opened = []

    def serial_factory(port, baud, timeout=0.5):
        fake = FakePort(port, baud, timeout, [V2_BANNER])
        opened.append(fake)
        return fake

    info = SimpleNamespace(device="COM3", hwid="", description="")
    monkeypatch.setattr(core_mod.serial, "Serial", serial_factory)
    monkeypatch.setattr(
        core_mod.serial.tools.list_ports, "comports", lambda: [info, info])
    monkeypatch.setattr(core_mod, "BANNER_TIMEOUT_S", 0.02, raising=False)

    found = core_mod.discover_stasys_devices()
    assert len(found) == 1
    assert len(opened) == 1, "duplicate entries must be deduplicated"


def test_attempt_internal_error_after_discovery_closes_port(
        monkeypatch, core_mod):
    """Exception after a port is open -> ('error', ...), port CLOSED."""
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close

    def bad_config(**kw):
        raise RuntimeError("settings blew up")

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config", bad_config)

    status, payload = core_mod.attempt_stasys_connection(None)

    assert status == "error", "internal faults must not read as 'no device'"
    assert port.closed, "discovered port must not leak on internal error"
    assert "application bug" in payload


def test_attempt_auth_exception_closes_port_and_reports_error(
        monkeypatch, core_mod):
    """perform_auth_v2 raising (not returning) still closes the port."""
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close

    def boom(*a, **kw):
        raise RuntimeError("handshake exploded")

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config",
                        lambda **kw: (b"k", b"\x01\x02\x03\x04\x05\x06", 3))
    monkeypatch.setattr(core_mod, "perform_auth_v2", boom)

    status, _payload = core_mod.attempt_stasys_connection(None)

    assert status == "error"
    assert port.closed


def test_on_attempt_done_error_is_terminal_no_retry(core_mod):
    """error status -> _show_auth_failure, never schedules another attempt."""
    stub = _stub_screen(core_mod)

    core_mod.ConnectionScreen._on_attempt_done(
        stub, ("error", "Internal connection error (boom)."))

    assert stub.shown == [("failed",
                           "Internal connection error (boom).")]
    assert stub.retries == 0
    assert stub.serial_port is None


def test_on_attempt_done_cancel_after_connected_closes_leaked_port(core_mod):
    """Race guard: connected result arriving after cancel is CLOSED."""
    stub = _stub_screen(core_mod)
    stub._cancel_event.set()
    port = SimpleNamespace(port="COM6", closed=False)

    def close():
        port.closed = True
    port.close = close

    core_mod.ConnectionScreen._on_attempt_done(
        stub, ("connected", (port, "STASYS v2")))

    assert port.closed, "a connected port must not leak after cancel"
    assert stub.serial_port is None
    assert stub.shown == []


def test_worker_crash_reports_error_not_none(monkeypatch, core_mod):
    """A worker-level crash must be terminal, not an absent-hardware retry."""
    def boom(p):
        raise RuntimeError("worker blew up")
    monkeypatch.setattr(core_mod, "attempt_stasys_connection", boom)
    worker = core_mod._ConnectionWorker(None, threading.Event())
    got = []
    worker.attempt_done.connect(got.append)

    worker.run()

    assert len(got) == 1
    assert got[0][0] == "error"
    assert "application bug" in got[0][1]


def test_malformed_configured_identity_never_falls_back_to_port_mac(
        monkeypatch, core_mod):
    """Explicit-but-invalid identity must fail closed (review Important #2)."""
    monkeypatch.setenv("STASYS_DEVICE_KEY", "unit-test-key")
    monkeypatch.setenv("STASYS_DEVICE_IDENTITY", "not-hex-at-all")
    monkeypatch.delenv("STASYS_GENERATION", raising=False)
    monkeypatch.setattr(core_mod, "load_settings", lambda: {})

    assert core_mod._load_spp_config(
        fallback_identity=bytes.fromhex("781C3CF5161A")) is None


def test_malformed_settings_identity_never_falls_back_to_port_mac(
        monkeypatch, core_mod):
    """Same fail-closed rule for a malformed settings.json identity."""
    monkeypatch.setenv("STASYS_DEVICE_KEY", "unit-test-key")
    monkeypatch.delenv("STASYS_DEVICE_IDENTITY", raising=False)
    monkeypatch.delenv("STASYS_GENERATION", raising=False)
    monkeypatch.setattr(
        core_mod, "load_settings",
        lambda: {"spp_identity_hex": "xyz"})

    assert core_mod._load_spp_config(
        fallback_identity=bytes.fromhex("781C3CF5161A")) is None
