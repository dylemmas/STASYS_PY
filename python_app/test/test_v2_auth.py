"""Tests for perform_auth_v2 — the SPP v2 handshake wrapper — and legacy removal.

FakeSerial is ported from STASYS_FW/test/test_stasys_packet.py:89 so chunk
boundaries (split banner, coalesced ``OK\n`` + frame) are caller-chosen and
deterministic. The tests pin the Task 4 contract:

  perform_auth_v2(ser, *, banner=None, key, identity, generation,
                  pending_parser=None) -> tuple[bool, str]
"""

import hashlib
import hmac
import os
import sys
from pathlib import Path

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

from tools import stasys_packet as spp


KEY = b"test-secret-provisioned"
IDENTITY = bytes.fromhex("010203040506")
GENERATION = 7
NONCE = bytes(range(32))
BANNER = b"READY v=2\nAUTH " + NONCE.hex().encode("ascii") + b"\n"
FRAME = spp.encode_packet(
    spp.Packet(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, -1, 2, -3, 400, 88)
)
PROOF_WRITE_SIZE = 71  # b"PROOF " (6) + 64 hex chars + b"\n" (1)


class FakeSerial:
    """Serial stand-in with caller-chosen read chunk boundaries."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.writes = []
        self.closed = False

    def read(self, _size):
        return self.chunks.pop(0) if self.chunks else b""

    def write(self, data):
        self.writes.append(bytes(data))

    def close(self):
        self.closed = True


class NoFlushSerial(FakeSerial):
    """Pins 'no reset_input_buffer': calling it is a contract violation."""

    def reset_input_buffer(self):
        raise AssertionError("perform_auth_v2 must not flush the input buffer")


@pytest.fixture(scope="module")
def core():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import core
    return core


def _split_banner(at=24):
    return [BANNER[:at], BANNER[at:]]


def _expected_proof():
    """Re-derive the proof from first principles, independent of spp helpers."""
    transcript = (
        b"STASYS-AUTH/v2\x00"
        + IDENTITY
        + GENERATION.to_bytes(4, "little")
        + NONCE
    )
    return hmac.new(KEY, transcript, hashlib.sha256).hexdigest().encode("ascii")


def test_happy_path_split_banner_and_coalesced_ok_frame(core):
    ser = FakeSerial(_split_banner() + [b"OK\n" + FRAME])
    parser = spp.PacketParser()

    ok, detail = core.perform_auth_v2(
        ser, key=KEY, identity=IDENTITY, generation=GENERATION,
        pending_parser=parser,
    )

    assert ok is True, detail
    assert len(ser.writes) == 1, ser.writes
    assert len(ser.writes[0]) == PROOF_WRITE_SIZE, ser.writes[0]
    # The coalesced tail must already be buffered in the caller's parser.
    assert parser.feed(b"") == [spp.parse_packet(FRAME)]
    assert not ser.closed


def test_written_proof_is_exactly_71_bytes_and_matches_independent_hmac(core):
    ser = FakeSerial([BANNER, b"OK\n"])

    ok, detail = core.perform_auth_v2(
        ser, key=KEY, identity=IDENTITY, generation=GENERATION,
    )

    assert ok is True, detail
    write = ser.writes[0]
    assert write == b"PROOF " + _expected_proof() + b"\n"
    assert len(write) == PROOF_WRITE_SIZE
    assert write.startswith(b"PROOF ") and write.endswith(b"\n")


def test_banner_prefill_skips_stream_read_of_banner(core):
    # The stream never carries the banner: only the post-proof reply is queued.
    ser = FakeSerial([b"OK\n" + FRAME])
    parser = spp.PacketParser()

    ok, detail = core.perform_auth_v2(
        ser, banner=BANNER, key=KEY, identity=IDENTITY, generation=GENERATION,
        pending_parser=parser,
    )

    assert ok is True, detail
    assert len(ser.writes) == 1
    assert len(ser.writes[0]) == PROOF_WRITE_SIZE
    assert parser.feed(b"") == [spp.parse_packet(FRAME)]
    assert ser.chunks == []


def test_fail_response_returns_stock_key_and_stale_generation_guidance(core):
    ser = FakeSerial([BANNER, b"FAIL\n"])

    ok, detail = core.perform_auth_v2(
        ser, key=KEY, identity=IDENTITY, generation=GENERATION,
    )

    assert ok is False
    assert isinstance(detail, str) and detail
    low = detail.lower()
    assert "stock" in low and "provision" in low, detail
    assert "generation" in low, detail
    assert "1" in detail, detail


def test_eof_mid_handshake_returns_handshake_close_detail(core):
    # Banner arrives, then the device goes silent: every later read is EOF.
    ser = FakeSerial([BANNER])

    ok, detail = core.perform_auth_v2(
        ser, key=KEY, identity=IDENTITY, generation=GENERATION,
    )

    assert ok is False
    assert isinstance(detail, str) and detail
    low = detail.lower()
    assert "handshake" in low and "clos" in low, detail
    assert "another host" in low, detail
    assert "attempt" in low, detail


def test_mock_serial_short_circuits_as_simulation(core):
    class WriteSpy(core.MockSerial):
        """MockSerial plus a write recorder, so a handshake write would show."""

        def __init__(self):
            super().__init__()
            self.writes = []

        def write(self, data):
            self.writes.append(bytes(data))

    ser = WriteSpy()

    ok, detail = core.perform_auth_v2(
        ser, key=KEY, identity=IDENTITY, generation=GENERATION,
    )

    assert ok is True
    assert detail == "simulation"
    assert ser.writes == []


def test_handshake_never_flushes_buffer_or_sleeps(core, monkeypatch):
    slept = []
    monkeypatch.setattr(core.time, "sleep", lambda *_args: slept.append(_args))
    ser = NoFlushSerial(_split_banner() + [b"OK\n"])

    ok, detail = core.perform_auth_v2(
        ser, key=KEY, identity=IDENTITY, generation=GENERATION,
    )

    assert ok is True, detail
    assert slept == []


def test_missing_key_is_reported_as_failure_not_raised(core):
    ser = FakeSerial([BANNER, b"OK\n"])

    ok, detail = core.perform_auth_v2(
        ser, key=b"", identity=IDENTITY, generation=GENERATION,
    )

    assert ok is False
    assert isinstance(detail, str) and detail
    assert ser.writes == []


def test_core_replaces_legacy_perform_auth_with_v2(core):
    assert not hasattr(core, "perform_auth")
    assert hasattr(core, "perform_auth_v2")
    # Legacy hashlib/hmac/string, SECRET_KEY and AUTH_* stay until Task 6:
    # discover_stasys_devices still consumes them inline.
    # Kept for MockSerial and the packet-mag tests.
    assert hasattr(core, "random") and hasattr(core, "struct")
    assert hasattr(core, "PACKET_SIZE") and hasattr(core, "MAX_PACKETS_PER_TICK")


def test_constants_module_drops_legacy_auth_symbols():
    import constants as legacy_constants

    for name in ("SECRET_KEY", "AUTH_TIMEOUT", "AUTH_RESPONSE_TIMEOUT",
                 "AUTH_CHALLENGE_LENGTH"):
        assert not hasattr(legacy_constants, name), name
    # Protocol truth lives in the vendored reference implementation.
    assert "stasys_packet" in legacy_constants.__doc__
    assert hasattr(legacy_constants, "PACKET_SIZE")
    assert hasattr(legacy_constants, "MAX_PACKETS_PER_TICK")


def test_connection_facade_exports_perform_auth_v2_only():
    import stasys_app.connection as connection

    assert hasattr(connection, "perform_auth_v2")
    assert not hasattr(connection, "perform_auth")
    assert "perform_auth_v2" in connection.__all__
    assert "perform_auth" not in connection.__all__
