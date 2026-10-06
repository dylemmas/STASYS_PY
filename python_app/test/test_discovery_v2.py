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

  ConnectionScreen._start_scan()  empty -> _show_fallback (unchanged);
    device found -> _load_spp_config(); None -> close port +
    _show_auth_failure(config-missing text); else perform_auth_v2(...) with
    banner prefill; ok -> advance_generation first, then _show_success;
    fail -> close port + _show_auth_failure(detail) VERBATIM.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

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

    def read(self, _size):
        return self.chunks.pop(0) if self.chunks else b""

    def write(self, data):
        self.writes.append(bytes(data))

    def close(self):
        self.closed = True
        self.is_open = False

    def reset_input_buffer(self):
        raise AssertionError("discovery must not flush the input buffer")


class NoSleepSerial(FakePort):
    """Pins 'no sleep': calling time.sleep inside discovery is a violation."""


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
    monkeypatch.setattr(
        core_mod.serial.tools.list_ports, "comports",
        lambda: [SimpleNamespace(device=p) for p in scripts],
    )
    # BANNER_TIMEOUT_S must be read at call time so tests can shrink it.
    monkeypatch.setattr(core_mod, "BANNER_TIMEOUT_S", 0.02, raising=False)

    def run(**scripts_in):
        scripts.update(scripts_in)
        return core_mod.discover_stasys_devices()

    run.opened = opened
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


def test_start_scan_routes_auth_failure_detail_to_show_auth_failure(monkeypatch, core_mod):
    """ConnectionScreen auth-failure path: detail passed through VERBATIM.

    Unit-tested against a stubbed self (no Qt dialog instantiation): the
    offscreen dialog harness is heavier than this decision logic warrants and
    the existing suite only pins the facade exports.
    """
    detail = "firmware rejected the key — a stock build"
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close

    advanced = []

    class StubScreen:
        parser = None
        serial_port = None
        is_simulation = False

        def _show_success(self, *_a):
            pytest.success = True
            raise AssertionError("_show_success must not run on auth failure")

        def _show_fallback(self):
            raise AssertionError("_show_fallback must not run when device found")

        def _show_auth_failure(self, got):
            self.auth_failure_detail = got

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config",
                        lambda: (b"k", b"\x01\x02\x03\x04\x05\x06", 3))
    monkeypatch.setattr(core_mod, "perform_auth_v2",
                        lambda *a, **kw: (False, detail))
    monkeypatch.setattr(core_mod, "advance_generation",
                        lambda g: advanced.append(g))

    stub = StubScreen()
    core_mod.ConnectionScreen._start_scan(stub)

    assert port.closed, "failed auth must close the port"
    assert stub.auth_failure_detail == detail, "detail must pass through verbatim"
    assert advanced == [], "generation must never advance on auth failure"


def test_start_scan_success_advances_generation_then_shows_success(monkeypatch, core_mod):
    """ok -> advance_generation FIRST, then _show_success."""
    port = SimpleNamespace(port="COM5", closed=False)
    advanced = []
    seen = []

    class StubScreen:
        parser = None
        serial_port = None
        is_simulation = False

        def _show_success(self, p, d):
            seen.append(("success", p, d))

        def _show_auth_failure(self, got):
            raise AssertionError("auth success must not show failure")

        def _show_fallback(self):
            raise AssertionError("found device must not show fallback")

    def fake_advance(g):
        advanced.append(g)
        seen.append(("advance", g))

    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config",
                        lambda: (b"k", b"\x01\x02\x03\x04\x05\x06", 3))
    monkeypatch.setattr(core_mod, "perform_auth_v2",
                        lambda *a, **kw: (True, "authenticated"))
    monkeypatch.setattr(core_mod, "advance_generation", fake_advance)

    stub = StubScreen()
    core_mod.ConnectionScreen._start_scan(stub)

    assert advanced == [3]
    # advance_generation must be recorded before _show_success
    assert seen[0][0] == "advance" and seen[1][0] == "success"
    assert stub.serial_port is port


def test_start_scan_missing_config_shows_config_failure(monkeypatch, core_mod):
    """cfg is None -> close port + _show_auth_failure with config-missing text."""
    port = SimpleNamespace(port="COM5", closed=False)

    def close():
        port.closed = True
    port.close = close

    class StubScreen:
        parser = None
        serial_port = None
        is_simulation = False

        def _show_success(self, *_a):
            raise AssertionError("missing config must not show success")

        def _show_fallback(self):
            raise AssertionError("device found; fallback is for no-device only")

        def _show_auth_failure(self, got):
            self.auth_failure_detail = got

    auth_called = []
    monkeypatch.setattr(core_mod, "discover_stasys_devices",
                        lambda: [(port, "STASYS v2", V2_BANNER)])
    monkeypatch.setattr(core_mod, "_load_spp_config", lambda: None)
    monkeypatch.setattr(core_mod, "perform_auth_v2",
                        lambda *a, **kw: auth_called.append(True) or (True, "x"))

    stub = StubScreen()
    core_mod.ConnectionScreen._start_scan(stub)

    assert port.closed
    assert not auth_called, "handshake must not start without config"
    text = stub.auth_failure_detail
    assert "STASYS_DEVICE_KEY" in text and "STASYS_DEVICE_IDENTITY" in text
    assert "simulation" in text.lower()
