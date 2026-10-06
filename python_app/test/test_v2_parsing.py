"""Characterization tests for the SPP v2 stream parser and wrapper contract.

Vendored-module tests should pass now. Wrapper tests intentionally describe the
Task 3 API and are expected to fail against the current legacy one-argument
implementation in stasys_app.core.
"""

import math
import os
import struct
import sys
from dataclasses import astuple
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import stasys_packet as spp


PACKET_FORMAT = '<' + 'f' * 6 + 'h' * 3 + 'HB'


def _packet(seed):
    return spp.Packet(
        float(seed), float(seed + 1), float(seed + 2),
        float(seed + 3), float(seed + 4), float(seed + 5),
        seed, seed + 1, seed + 2, seed + 3, seed + 4,
    )


def _values(packet):
    return [
        packet.ax, packet.ay, packet.az, packet.gx, packet.gy, packet.gz,
        packet.mag_x, packet.mag_y, packet.mag_z, packet.piezo, packet.battery,
    ]


def test_two_frame_stream_recovers_at_every_split_offset():
    packets = [_packet(1), _packet(11)]
    stream = spp.encode_packet(packets[0]) + spp.encode_packet(packets[1])

    for split in range(len(stream) + 1):
        parser = spp.PacketParser()
        actual = parser.feed(stream[:split]) + parser.feed(stream[split:])
        assert actual == packets, f"failed at split offset {split}"


def test_header_split_across_two_feeds_is_preserved():
    frame = spp.encode_packet(_packet(2))
    parser = spp.PacketParser()

    assert parser.feed(b'noise' + frame[:1]) == []
    assert parser.feed(frame[1:]) == [_packet(2)]
    assert parser.discarded_bytes == len(b'noise')


def test_noise_prefix_is_discarded_before_frame():
    parser = spp.PacketParser()
    assert parser.feed(b'\x01\x02junk' + spp.encode_packet(_packet(3))) == [_packet(3)]
    assert parser.discarded_bytes > 0


def test_corrupt_candidate_with_embedded_header_resynchronizes_by_one_byte():
    embedded = spp.encode_packet(_packet(4))
    # Outer candidate has a valid header but bad checksum; the embedded frame's
    # AA BB starts at byte 6 and its payload extends beyond the outer candidate.
    corrupt = spp.HEADER + b'\x10\x20\x30\x40' + embedded[:30]
    assert len(corrupt) == spp.FRAME_SIZE
    following = spp.encode_packet(_packet(14))
    parser = spp.PacketParser()

    recovered = parser.feed(corrupt + embedded[30:] + following)
    assert recovered == [_packet(4), _packet(14)]
    assert parser.invalid_frames >= 1
    assert parser.checksum_errors >= 1


def test_buffer_cap_discards_garbage_and_advances_counters():
    parser = spp.PacketParser()
    assert parser.feed(b'\x01' * 200) == []
    assert len(parser._buffer) <= spp.MAX_BUFFER_SIZE
    assert parser.discarded_bytes >= 200 - spp.MAX_BUFFER_SIZE
    assert parser.discarded_bytes > 0

    follow_up = spp.encode_packet(_packet(7))
    assert parser.feed(follow_up) == [_packet(7)]


def test_parser_accepts_nan_and_infinity_payloads():
    packet = spp.Packet(float('nan'), float('inf'), float('-inf'), 0, 0, 0, 1, 2, 3, 4, 5)
    frame = spp.encode_packet(packet)

    parsed_directly = spp.parse_packet(frame)
    parsed_incrementally = spp.PacketParser().feed(frame)
    assert len(parsed_incrementally) == 1

    for parsed in (parsed_directly, parsed_incrementally[0]):
        assert math.isnan(parsed.ax)
        assert math.isinf(parsed.ay) and parsed.ay > 0
        assert math.isinf(parsed.az) and parsed.az < 0
        assert parsed.gx == 0 and parsed.gz == 0
        assert (parsed.mag_x, parsed.mag_y, parsed.mag_z) == (1, 2, 3)
        assert (parsed.piezo, parsed.battery) == (4, 5)


def test_parse_packet_matches_legacy_struct_payload_unpack():
    packet = _packet(5)
    frame = spp.encode_packet(packet)
    payload = frame[2:-1]

    assert list(astuple(spp.parse_packet(frame))) == list(
        struct.unpack(PACKET_FORMAT, payload)
    )


class FakeSerial:
    """Minimal serial double; read returns up to n available bytes."""

    def __init__(self, data=b''):
        self.buffer = bytearray(data)

    @property
    def in_waiting(self):
        return len(self.buffer)

    def read(self, count):
        count = min(count, len(self.buffer))
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result


# These tests intentionally fail until Task 3 replaces the legacy wrapper.
def test_wrapper_returns_list_of_11_value_lists_for_completed_frames():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app_path = str(REPO_ROOT / 'python_app' / 'stasys_app')
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    from base import parse_binary_packet

    expected = _packet(6)
    parser = spp.PacketParser()
    actual = parse_binary_packet(FakeSerial(spp.encode_packet(expected)), parser)
    assert actual == [_values(expected)]
    assert all(isinstance(row, list) and len(row) == 11 for row in actual)


def test_wrapper_returns_none_when_no_frame_completed():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app_path = str(REPO_ROOT / 'python_app' / 'stasys_app')
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    from base import parse_binary_packet

    parser = spp.PacketParser()
    assert parse_binary_packet(FakeSerial(b'\xAA'), parser) is None
