"""Drift test for the vendored SPP parser (tools/stasys_packet.py).

The canonical source of truth is STASYS_FW/tools/. This repo vendors a
byte-identical copy under STASYS_PY/tools/ so the parsing guide's links
resolve and the core can import it. Three layers of protection:

  (a) byte-equality of the vendored files vs the STASYS_FW originals
      (skipped when STASYS_FW is not present);
  (b) always-run constant anchors on the vendored module, so an
      environment with no sibling STASYS_FW still catches drift;
  (c) independent first-principles re-derivation of the HMAC transcript
      and proof, compared against the vendored implementations.
"""

import hashlib
import hmac
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FW_ROOT = Path(
    os.environ.get("STASYS_FW_ROOT")
    or REPO_ROOT.parent / "STASYS_FW"
)
VENDORED_FILES = ("stasys_packet.py", "README.md", "__init__.py")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _vendored_path(name: str) -> Path:
    return REPO_ROOT / "tools" / name


# (a) byte-equality vs STASYS_FW original, skip when the source repo is absent
def test_vendored_files_byte_identical_to_stasys_fw():
    if not FW_ROOT.is_dir():
        pytest.skip(f"STASYS_FW not found at {FW_ROOT}; nothing to compare")
    for name in VENDORED_FILES:
        vendored = _vendored_path(name)
        original = FW_ROOT / "tools" / name
        assert vendored.is_file(), f"missing vendored file: {vendored}"
        assert original.is_file(), f"missing STASYS_FW source file: {original}"
        assert vendored.read_bytes() == original.read_bytes(), (
            f"drift: {vendored} differs from {original}; re-copy it byte-identically"
        )


# (b) always-run anchors on the vendored module
def _import_vendored():
    from tools import stasys_packet as spp  # noqa: PLC0415 - path set at module top

    return spp


def test_auth_domain_constant():
    spp = _import_vendored()
    assert spp.AUTH_DOMAIN == b"STASYS-AUTH/v2\0"
    assert len(spp.AUTH_DOMAIN) == 15


def test_frame_and_format_constants():
    spp = _import_vendored()
    assert spp.FRAME_SIZE == 36
    assert spp.PAYLOAD_FORMAT == "<6f3hHB"
    assert spp.MAX_BUFFER_SIZE == 144
    assert spp.HEADER == b"\xAA\xBB"


# (c) independent HMAC re-derivation from first principles
def test_auth_transcript_rederived_from_first_principles():
    spp = _import_vendored()
    identity = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
    generation = 0x01020304
    nonce = bytes(range(32))

    domain = b"STASYS-AUTH/v2" + b"\x00"
    assert len(domain) == 15
    expected = domain + identity + generation.to_bytes(4, "little") + nonce

    assert spp.AUTH_DOMAIN == domain
    assert spp.auth_transcript(identity, generation, nonce) == expected
    assert len(expected) == 15 + 6 + 4 + 32


def test_auth_proof_rederived_from_first_principles():
    spp = _import_vendored()
    key = bytes(range(1, 33))
    identity = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x01])
    generation = 42
    nonce = bytes((i * 7) % 256 for i in range(32))

    transcript = (
        b"STASYS-AUTH/v2\x00"
        + identity
        + generation.to_bytes(4, "little")
        + nonce
    )
    expected_proof = hmac.new(key, transcript, hashlib.sha256).digest()

    assert spp.auth_transcript(identity, generation, nonce) == transcript
    assert spp.auth_proof(key, transcript) == expected_proof
    assert len(expected_proof) == 32
