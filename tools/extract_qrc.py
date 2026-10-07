#!/usr/bin/env python3
"""Statically extract UI evidence from the SCATT Basic executable.

The SCATT app ships its QML as *compiled* V4 bytecode (resource payloads are
tagged `qv4cdata`), so QML source text is not recoverable. What is recoverable
without launching the app:

  * every UTF-16BE string in the resource/translation name tables
    (screen names, object IDs, qrc paths, literal UI text)
  * ASCII string table entries (dialog titles, menu items, format strings)
  * embedded SVG/image assets (plain or qCompress/zlib wrapped)

Usage:
    python tools/extract_qrc.py [exe_path] [out_dir]

Defaults: F:/Scatt Basic/scattbasic.exe  ->  scratch/scatt_extracted/
"""
from __future__ import annotations

import re
import struct
import sys
import zlib
from pathlib import Path

DEFAULT_EXE = Path(r"F:\Scatt Basic\scattbasic.exe")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "scratch" / "scatt_extracted"

UTF16_RE = re.compile(rb"(?:\x00[\x20-\x7e]){3,}")
ASCII_RE = re.compile(rb"[\x20-\x7e]{5,}")
ZLIB_RE = re.compile(rb"\x78[\x01\x5e\x9c\xda]")

# UI-relevant terms used to keep the ASCII string dump focused.
UI_HINTS = re.compile(
    r"(menu|toolbar|dialog|popup|window|button|label|tab|panel|pane|footer|header|"
    r"title|status|settings|prefer|calibrat|session|practice|match|target|distance|"
    r"sensor|device|firmware|language|print|export|import|about|diagnos|score|shot|"
    r"replay|summary|start|stop|connect|new |open |save|exit|help|view|mode|step|"
    r"shooter|rifle|pistol|range|aim)",
    re.I,
)


def decode_utf16_strings(data: bytes) -> list[str]:
    out: list[str] = []
    for m in UTF16_RE.finditer(data):
        s = m.group().decode("utf-16-be", "ignore")
        if s.strip():
            out.append(s)
    return out


def decode_ascii_strings(data: bytes) -> list[str]:
    return [m.group().decode("ascii", "ignore") for m in ASCII_RE.finditer(data)]


def try_decompress(blob: bytes) -> bytes | None:
    """Qt qCompress = 4-byte BE raw size + zlib stream; also try plain zlib/deflate."""
    candidates: list[bytes] = []
    # qCompress: check the 4-byte declared raw size first
    if len(blob) > 8:
        declared = struct.unpack(">I", blob[:4])[0]
        if 0 < declared < 200_000_000:
            candidates.append(blob[4:])
    candidates.append(blob)
    for cand in candidates:
        for wbits in (47, 15, -15):  # zlib / gzip / raw deflate
            try:
                return zlib.decompress(cand, wbits)
            except Exception:
                continue
    return None


def carve_assets(data: bytes, out_dir: Path) -> dict[str, int]:
    """Find SVG/XML and other asset payloads by decompressing at zlib candidate offsets."""
    written: dict[str, int] = {}
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    n = 0
    seen: set[bytes] = set()
    for m in ZLIB_RE.finditer(data):
        off = m.start()
        # prefer qCompress framing: 4 bytes before the zlib header hold raw size
        for base in (off - 4, off):
            if base < 0:
                continue
            dec = try_decompress(data[base:base + 2_000_000])
            if not dec or len(dec) < 64 or dec in seen:
                continue
            head = dec.lstrip()[:64].lower()
            if head.startswith(b"<?xml") or head.startswith(b"<svg") or b"<svg" in dec[:400]:
                seen.add(dec)
                name = f"asset_{n:03d}.svg"
                (assets / name).write_bytes(dec)
                written[name] = len(dec)
                n += 1
            break
    # uncompressed SVGs too
    for m in re.finditer(rb"<svg[\s>]", data):
        start = data.rfind(b"<?xml", max(0, m.start() - 400), m.start())
        start = start if start != -1 else m.start()
        end = data.find(b"</svg>", m.start())
        if end == -1:
            continue
        blob = data[start:end + 6]
        if len(blob) < 64 or blob in seen:
            continue
        seen.add(blob)
        name = f"asset_{n:03d}.svg"
        (assets / name).write_bytes(blob)
        written[name] = len(blob)
        n += 1
    return written


def main() -> int:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXE
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not exe.exists():
        print(f"not found: {exe}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)

    data = exe.read_bytes()
    print(f"read {exe} ({len(data):,} bytes)")

    # --- UTF-16BE strings (resource/translation name tables) -----------------
    u16 = decode_utf16_strings(data)
    seen: set[str] = set()
    uniq16 = []
    for s in u16:
        if s not in seen:
            seen.add(s)
            uniq16.append(s)
    (out / "strings_utf16.txt").write_text("\n".join(uniq16), encoding="utf-8")
    print(f"utf-16 strings: {len(uniq16)} unique")

    # --- focused ASCII UI strings -------------------------------------------
    asc = []
    seen_a: set[str] = set()
    for s in decode_ascii_strings(data):
        if s in seen_a or not UI_HINTS.search(s):
            continue
        seen_a.add(s)
        asc.append(s)
    (out / "strings_ui.txt").write_text("\n".join(asc), encoding="utf-8")
    print(f"ascii UI strings: {len(asc)} unique")

    # --- asset carving --------------------------------------------------------
    assets = carve_assets(data, out)
    print(f"assets carved: {len(assets)}")

    # --- resource path inventory ---------------------------------------------
    paths = sorted({s for s in uniq16 if s.startswith(":/") or s.startswith("qrc:///")})
    (out / "resource_paths.txt").write_text("\n".join(paths), encoding="utf-8")
    print(f"resource paths: {len(paths)}")

    print(f"output -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
