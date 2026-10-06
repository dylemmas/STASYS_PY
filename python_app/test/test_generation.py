"""Tests for the SPP v2 config loader and generation tracker (Task 5).

Contract pinned here (task-5-brief.md):

  _load_spp_config() -> tuple[key: bytes, identity: bytes, generation: int] | None

    key         STASYS_DEVICE_KEY (raw UTF-8, CLI --key-env parity) > spp_key_hex
    identity    STASYS_DEVICE_IDENTITY > spp_identity_hex, colons stripped -> 6 bytes
    generation  STASYS_GENERATION (one-shot override) > spp_next_generation > 1
    missing / malformed key or identity -> None (fail closed, never a fallback key)
    all-zero identity -> allowed, logged as a warning

  advance_generation(gen)  load -> merge -> save settings['spp_next_generation'] = gen + 1
                           (only after a successful auth; never on failure)

Env precedence is "primary wins when present": a present-but-malformed
STASYS_DEVICE_KEY / STASYS_DEVICE_IDENTITY fails closed instead of silently
falling through to settings.json. Generation is the exception -- it has a safe
default, so a malformed override falls back down the chain.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

APP_PATH = str(REPO_ROOT / 'python_app' / 'stasys_app')
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)
PY_ROOT = str(REPO_ROOT / 'python_app')
if PY_ROOT not in sys.path:
    sys.path.insert(0, PY_ROOT)

ENV_KEYS = ('STASYS_DEVICE_KEY', 'STASYS_DEVICE_IDENTITY', 'STASYS_GENERATION')
SETTINGS_KEYS = ('spp_key_hex', 'spp_identity_hex', 'spp_next_generation')

GOOD_KEY = b"test-secret-provisioned"
GOOD_KEY_HEX = GOOD_KEY.hex()
GOOD_IDENTITY = bytes.fromhex("010203040506")
GOOD_IDENTITY_HEX = GOOD_IDENTITY.hex()
BANNER = b"READY v=2\nAUTH " + bytes(range(32)).hex().encode("ascii") + b"\n"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """The host machine must not be able to leak SPP config into a test."""
    for name in ENV_KEYS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(scope="module")
def core():
    import os
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import core
    return core


@pytest.fixture
def tmp_settings(core, tmp_path, monkeypatch):
    """Point core's SETTINGS_FILE at a throwaway path and start empty."""
    path = tmp_path / 'settings.json'
    monkeypatch.setattr(core, 'SETTINGS_FILE', str(path))
    return path


def _write_settings(path, payload):
    import json
    path.write_text(json.dumps(payload), encoding='utf-8')


def _read_settings(path):
    import json
    import os
    if not os.path.exists(path):
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


# ---- key: env > settings > fail closed -------------------------------------

def test_key_env_beats_settings_hex(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': 'aa' * 8,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_KEY', 'env-secret')

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[0] == b'env-secret'


def test_key_env_is_raw_utf8_not_hex_decoded(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_identity_hex': GOOD_IDENTITY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_KEY', 'plain-secret')

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[0] == b'plain-secret'


def test_key_from_settings_hex_when_env_absent(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[0] == GOOD_KEY


def test_missing_key_fails_closed(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_identity_hex': GOOD_IDENTITY_HEX})

    assert core._load_spp_config() is None


def test_missing_everything_fails_closed(core, tmp_settings):
    assert core._load_spp_config() is None


def test_invalid_settings_key_fails_closed(core, tmp_settings):
    _write_settings(tmp_settings, {
        'spp_key_hex': 'not-hex-at-all',
        'spp_identity_hex': GOOD_IDENTITY_HEX,
    })

    assert core._load_spp_config() is None


def test_empty_env_key_fails_closed_even_with_valid_settings(core, tmp_settings,
                                                             monkeypatch):
    """An explicitly-set-but-empty override is a config error, not unset."""
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_KEY', '')

    assert core._load_spp_config() is None


# ---- identity: env > settings, colons stripped, exactly 6 bytes -----------

def test_identity_env_colon_form(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_IDENTITY', '01:02:03:04:05:06')

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[1] == GOOD_IDENTITY


def test_identity_env_bare_hex_form(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_IDENTITY', GOOD_IDENTITY_HEX)

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[1] == GOOD_IDENTITY


def test_identity_from_settings_colon_form(core, tmp_settings):
    _write_settings(tmp_settings, {
        'spp_key_hex': GOOD_KEY_HEX,
        'spp_identity_hex': '01:02:03:04:05:06',
    })

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[1] == GOOD_IDENTITY


def test_identity_wrong_length_fails_closed(core, tmp_settings, monkeypatch):
    """Reachability pin: with a valid key + identity in the SAME environment
    the config loads, so the key gate (core.py:1126) is open and the None
    below is caused by the malformed override alone."""
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})
    assert core._load_spp_config() is not None

    monkeypatch.setenv('STASYS_DEVICE_IDENTITY', '01020304050607')

    assert core._load_spp_config() is None


def test_identity_non_hex_fails_closed(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_IDENTITY', 'zz0203040506')

    assert core._load_spp_config() is None


def test_key_without_identity_is_config_missing(core, tmp_settings, monkeypatch):
    monkeypatch.setenv('STASYS_DEVICE_KEY', 'plain-secret')

    assert core._load_spp_config() is None


def test_all_zero_identity_allowed_but_warns(core, tmp_settings, caplog):
    _write_settings(tmp_settings, {
        'spp_key_hex': GOOD_KEY_HEX,
        'spp_identity_hex': '00:00:00:00:00:00',
    })

    with caplog.at_level('WARNING'):
        cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[1] == bytes(6)
    assert any('identity' in rec.message.lower() and 'zero' in rec.message.lower()
               for rec in caplog.records), [r.message for r in caplog.records]


# ---- generation: env > settings > 1 ----------------------------------------

def test_generation_env_overrides_settings(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX,
                                   'spp_next_generation': 41})
    monkeypatch.setenv('STASYS_GENERATION', '7')

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 7


def test_generation_from_settings_when_env_absent(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX,
                                   'spp_next_generation': 41})

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 41


def test_generation_defaults_to_one(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 1


def test_generation_reset_override_env_one(core, tmp_settings, monkeypatch):
    """STASYS_GENERATION=1 is the documented reboot/reset override."""
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX,
                                   'spp_next_generation': 99})
    monkeypatch.setenv('STASYS_GENERATION', '1')

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 1


def test_invalid_generation_env_falls_back_to_settings(core, tmp_settings,
                                                       monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX,
                                   'spp_next_generation': 41})
    monkeypatch.setenv('STASYS_GENERATION', 'not-a-number')

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 41


def test_generation_beyond_uint32_falls_back(core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})
    monkeypatch.setenv('STASYS_GENERATION', str(2 ** 32))

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 1


def test_zero_generation_from_settings_falls_back_to_one(core, tmp_settings):
    """The firmware skips 0 on wraparound; 0 is never a valid seed."""
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX,
                                   'spp_next_generation': 0})

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 1


# ---- persistence: load-merge-save around a tmp SETTINGS_FILE ---------------

def test_advance_generation_persists_next_seed(core, tmp_settings):
    core.advance_generation(5)

    assert _read_settings(tmp_settings)['spp_next_generation'] == 6


def test_advance_generation_is_load_merge_save(core, tmp_settings):
    _write_settings(tmp_settings, {'other_setting': 'keep-me',
                                   'spp_next_generation': 5})

    core.advance_generation(5)

    saved = _read_settings(tmp_settings)
    assert saved['spp_next_generation'] == 6
    assert saved['other_setting'] == 'keep-me'


def test_load_reads_back_persisted_generation(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})
    core.advance_generation(1)
    core.advance_generation(2)

    cfg = core._load_spp_config()

    assert cfg is not None
    assert cfg[2] == 3


def test_advance_generation_round_trips_key_and_identity(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})

    core.advance_generation(1)

    cfg = core._load_spp_config()
    assert cfg is not None
    assert cfg[0] == GOOD_KEY
    assert cfg[1] == GOOD_IDENTITY
    assert cfg[2] == 2


# ---- auth <-> generation coupling (Task 6 caller shape) --------------------

class _Serial:
    """Minimal read-chunk serial stand-in (see test_v2_auth.FakeSerial)."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.writes = []

    def read(self, _size):
        return self.chunks.pop(0) if self.chunks else b""

    def write(self, data):
        self.writes.append(bytes(data))


def test_successful_auth_then_advance_persists_gen_plus_one(core, tmp_settings):
    """The Task 6 caller shape: seed -> auth -> persist gen+1 only on success."""
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})
    seed = core._load_spp_config()[2]

    ok, detail = core.perform_auth_v2(
        _Serial([BANNER, b'OK\n']),
        key=GOOD_KEY, identity=GOOD_IDENTITY, generation=seed,
    )
    if ok:
        core.advance_generation(seed)

    assert ok is True, detail
    assert _read_settings(tmp_settings)['spp_next_generation'] == seed + 1


def test_failed_auth_never_advances_generation(core, tmp_settings):
    """A rejected proof must leave the persisted seed untouched."""
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX,
                                   'spp_next_generation': 3})
    seed = core._load_spp_config()[2]
    assert seed == 3

    ok, detail = core.perform_auth_v2(
        _Serial([BANNER, b'FAIL\n']),
        key=GOOD_KEY, identity=GOOD_IDENTITY, generation=seed,
    )
    if ok:
        core.advance_generation(seed)

    assert ok is False, detail
    assert _read_settings(tmp_settings)['spp_next_generation'] == 3


def test_perform_auth_v2_does_not_advance_generation_by_itself(
        core, tmp_settings, monkeypatch):
    """advance_generation is the caller's job -- advancing twice would drift."""
    def _boom(gen):
        raise AssertionError("perform_auth_v2 must not persist the generation")

    monkeypatch.setattr(core, 'advance_generation', _boom)

    ok, detail = core.perform_auth_v2(
        _Serial([BANNER, b'OK\n']),
        key=GOOD_KEY, identity=GOOD_IDENTITY, generation=1,
    )

    assert ok is True, detail


# ---- generation counter bounds --------------------------------------------

def test_advance_generation_wraps_like_the_firmware(core, tmp_settings):
    """The firmware skips 0 on wraparound, so gen+1 past uint32 becomes 1."""
    core.advance_generation(2 ** 32 - 1)

    assert _read_settings(tmp_settings)['spp_next_generation'] == 1


def test_advance_generation_rejects_non_integer_without_writing(core,
                                                                tmp_settings):
    core.advance_generation('not-a-generation')

    assert 'spp_next_generation' not in _read_settings(tmp_settings)


# ---- malformed settings values must fail closed, never raise ---------------

def test_non_string_settings_key_fails_closed(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': 12345,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})

    assert core._load_spp_config() is None


def test_non_string_settings_identity_fails_closed(core, tmp_settings):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': ['01', '02', '03',
                                                        '04', '05', '06']})

    assert core._load_spp_config() is None


def test_whitespace_only_env_key_fails_closed_without_settings_fallback(
        core, tmp_settings, monkeypatch):
    _write_settings(tmp_settings, {'spp_key_hex': GOOD_KEY_HEX,
                                   'spp_identity_hex': GOOD_IDENTITY_HEX})
    monkeypatch.setenv('STASYS_DEVICE_KEY', '   \n')

    assert core._load_spp_config() is None


def test_advance_generation_survives_non_dict_settings_file(core, tmp_settings):
    tmp_path = tmp_path_from(tmp_settings)
    tmp_path.write_text('["not", "a", "dict"]', encoding='utf-8')

    assert core.advance_generation(5) == 6
    assert _read_settings(tmp_settings)['spp_next_generation'] == 6


def tmp_path_from(settings_path):
    return Path(settings_path)
