# STASYS Bluetooth SPP parsing guide

**This guide is for Python client authors who need to read the STASYS telemetry stream efficiently and without desyncing.** It documents parsing *behaviour* — framing, resynchronisation, timing, loss and session lifecycle.

**The byte-by-byte field layout and the CLI usage live in [`tools/README.md`](tools/README.md) — this guide links there rather than repeating the offset table, so there is only ever one copy of it.** Read that first for the field table; come back here for everything that table does not tell you.

A working reference implementation already exists: [`tools/stasys_packet.py`](tools/stasys_packet.py) provides `parse_packet`, `PacketParser`, `encode_packet`, `auth_transcript`, `auth_proof` and `SppReceiver`. Prefer importing it over writing a parser from scratch. This guide explains how those pieces behave so you can use them correctly.

## Stream overview

The connection passes through three phases. There is **no marker in the byte stream** that announces the switch from phase 1 to phase 2 — the parser must be a state machine that flips when it has read `OK`.

```text
Bluetooth Classic SSP pairing (Just Works; legacy PIN rejected)
        |
        v
SPP open  -->  dev:  READY v=2\n                  10 B   \
        |      dev:  AUTH <64 lowercase hex>\n   70 B   /  one write, 80 B total
        |      host: PROOF <64 hex>\n            71 B   <-- line must be exactly 70 chars
        |      dev:  OK\n                         3 B   <-- PHASE SWITCH
        |          or FAIL\n                      5 B   (up to 3 attempts, then disconnect)
        v
PHASE 2: bare concatenation of 36-byte binary frames @ ~100 Hz
        -- no ASCII, no heartbeat, no terminator, ever again --
```

Two properties of phase 2 follow from that diagram and drive everything else in this guide:

- **It is a byte stream, not a message stream.** SPP is RFCOMM over L2CAP. A single 36-byte write can arrive split across several reads, and several writes can arrive coalesced into one read. You never get "one read = one packet".
- **It is best-effort and lossy.** Frames are dropped silently when the link is congested. There is no sequence number, so you cannot detect loss directly — you can only infer it from timing.

## Phase 1: the handshake

### Exact bytes

| Direction | Bytes | Length | Notes |
|---|---|---:|---|
| device → host | `READY v=2\n` | 10 | `\n` only — the device never emits `\r` |
| device → host | `AUTH ` + 64 lowercase hex + `\n` | 70 | 32-byte nonce, hex-encoded |
| *(those two are one write — 80 bytes total)* | | | |
| host → device | `PROOF ` + 64 hex + `\n` | 71 | line body must be **exactly** 70 chars |
| device → host | `OK\n` | 3 | authenticated |
| device → host | `FAIL\n` | 5 | proof rejected, attempts remaining |

Constants: `STASYS_AUTH_VERSION` is `2u`, `STASYS_AUTH_NONCE_SIZE` is `32u`, `STASYS_AUTH_MAX_ATTEMPTS` is `3u`, `STASYS_AUTH_MAX_LINE` is `160u`, `STASYS_AUTH_TIMEOUT_MS` is `10000u` (all in `components/app_protocol/include/app_protocol.h`).

Rules the firmware enforces — each one is a way to get disconnected:

- **The `PROOF` line must be exactly 70 characters** (`PROOF ` = 6, hex = 64). Not 69, not 71, no trailing whitespace. The device compares length *first* and rejects on mismatch.
- **Hex case does not matter** for the proof you send — `A-F` and `a-f` both decode. The nonce *you receive* is always lowercase.
- **`\r` is discarded** before the line length is checked, so sending `PROOF ...\r\n` works. The `\r` must be immediately before the `\n`.
- **A line over 160 bytes burns an attempt** by itself — overflow is a failure distinct from a bad proof. Three failures total (bad proof *or* overflow) and the link is dropped **with no `FAIL`** — the disconnect is your only signal.
- **The 10-second deadline is armed at connection open, but only evaluated when the host sends data.** There is no idle timer. A client that connects and sends nothing stays connected indefinitely; a client that sends its proof 11 seconds later gets disconnected.
- **Three failures → silent disconnect.** After the third, the device sends nothing at all — no `FAIL`, no reason code. Handle EOF during phase 1 as "auth failed".

### The transcript and the proof

```text
transcript (57 bytes) =
      b"STASYS-AUTH/v2\0"        15 B   <-- includes an explicit trailing NUL, not just the 14-char string
   || bt_mac                      6 B   first octet = first displayed octet of the MAC
   || generation                  4 B   uint32, little-endian
   || nonce                      32 B   raw bytes, NOT the hex string you received

proof = HMAC-SHA256(provisioned_device_key, transcript)   -> 32 bytes -> 64 hex chars
```

Three things trip up every first implementation:

1. **The domain separator is 15 bytes, not 14.** `AUTH_DOMAIN = b"STASYS-AUTH/v2\0"` in `tools/stasys_packet.py:42` carries the NUL as part of the string. Hash the NUL or your proof is wrong.
2. **The nonce in the transcript is raw**, not the 64 hex characters from the `AUTH` line. Decode hex first.
3. **`generation` never appears on the wire.** See [Reconnect and session lifecycle](#reconnect-and-session-lifecycle) — this is the single most common cause of an inexplicable `FAIL`.

Use the reference functions rather than re-deriving them:

```python
from tools.stasys_packet import auth_transcript, auth_proof

transcript = auth_transcript(identity, generation, nonce)   # identity: 6 bytes, nonce: 32 raw bytes
proof_hex  = auth_proof(key, transcript).hex().encode()     # 64 hex chars
conn.write(b"PROOF " + proof_hex + b"\n")
```

## ⚠️ A stock build can never authenticate

**Read this before debugging your client.** `staysys_provisioned_key` is declared `weak` at `src/main.cpp:44` and **defined nowhere in the repository**. The key provider checks for it and fails closed:

```c
if (staysys_provisioned_key == nullptr) return -1;
```

`staysys_auth_get_key` therefore returns `-1`, the `&&` chain in the proof-verification short-circuits before the HMAC is ever computed, and **every `PROOF` is answered `FAIL\n`** — followed by a disconnect after 3 attempts. This is deliberate: `app_protocol.h` documents that no fallback key exists and an unset provider must fail closed.

**Consequence: against a firmware built from this source tree you will never receive a single telemetry frame, and no amount of client-side fixing will change that.** If you are seeing three `FAIL`s and a disconnect, confirm this is the cause before touching your parser.

Develop and test the parser without a key:

- **Build fixtures.** Construct frames with `encode_packet()` and feed them to `PacketParser.feed()` — no Bluetooth, no device, no key needed.
- **Simulate the stream.** `FakeSerial` in `test/test_stasys_packet.py:89` models a serial connection whose `read()` returns caller-chosen chunk boundaries. Use it to reproduce split headers, coalesced frames and mid-frame fragmentation deterministically.
- **Record live captures once a key exists**, then replay them offline for regression tests.

## Phase 2: binary framing and resynchronisation

The frame layout is in [`tools/README.md`](tools/README.md) (`STASYS_PACKET_SIZE` = 36, header `0xAA 0xBB`, payload little-endian, XOR checksum at offset 35). What follows is the *algorithm* for reading it out of a byte stream.

### The accumulating-buffer algorithm

1. **Append every incoming chunk to a persistent buffer.** Never treat a read as a complete frame.
2. **Find `b"\xAA\xBB"`.** Discard everything before it — *except* a trailing lone `0xAA`, because the header itself can be split across two reads.
3. **Fewer than 36 bytes buffered?** Wait for more data. Do not parse, do not discard.
4. **Validate** the header and the XOR checksum over bytes **2..34 inclusive** (33 bytes; the header and the checksum byte itself are excluded).
5. **On failure, advance by exactly 1 byte — never by 36.** This is the load-bearing detail. A corrupted frame's payload can itself contain the bytes `AA BB`; if you skip a full frame's length you jump to a position with no valid frame and lose synchronisation for good. Stepping one byte guarantees you re-scan every candidate position.
6. **On success, consume exactly 36 bytes** and repeat from step 2 with what remains.

Bound the buffer. `PacketParser` caps it at `MAX_BUFFER_SIZE = FRAME_SIZE * 4` (144 bytes) and drops from the head. An unbounded buffer is the primary way a naive parser turns a brief stall into a memory problem.

`PacketParser.feed(chunk)` in `tools/stasys_packet.py:132` implements all six steps and returns a list of decoded packets, while exposing `discarded_bytes`, `checksum_errors` and `invalid_frames` counters so you can tell healthy resync from a genuinely corrupt link.

### The `OK\n` coalescing hazard

`OK\n` and the first 36-byte frame are **separate writes issued from different contexts**. RFCOMM may deliver them as a single read: `b"OK\n" + frame_bytes`. Anything after the `\n` of `OK` is not handshake leftover to discard — it is the beginning of phase 2.

Drain the tail of the handshake read into the binary parser rather than dropping it. `SppReceiver.authenticate()` at `tools/stasys_packet.py:231` does exactly this, and `test_authentication_handles_fragments_and_coalesced_first_frame` in `test/test_stasys_packet.py:106` locks the behaviour in.

The reverse case also occurs: the handshake lines themselves can arrive split (`b"READY v=2\nAU"`, then `b"TH <hex>\n"`). Parse the handshake by accumulating lines on `\n`, not by assuming one read per line.

## Timing and loss model

### Cadence

Nominal period is `STASYS_PACKET_PERIOD_US` = `10000` µs → **100 Hz**. Treat that as an **upper bound**, not a guarantee.

- **Gaps are one-sided: only ever ≥ 10 ms.** The firmware re-anchors its deadline to "now" at the top of each loop iteration and sleeps the remainder — it never compensates for a late iteration. A slow iteration stretches that one gap and is not carried forward, so you will never see frames arrive faster than 10 ms apart.
- **A ~6–15 ms spike every 500 ms.** The diagnostic block runs 200 back-to-back ADC reads *and* two log lines inside the packet loop (`diagnostic_interval_us = 500000`). Expect a widened gap twice per second, every second.
- **Up to ~204 ms on a wedged I²C bus.** Each register read has a 20 ms timeout and the oversample loop runs 10 times, so a bus fault costs up to 204 ms plus the magnetometer read.
- **A failing sensor skips the sleep entirely.** When no MPU sample succeeds the loop `continue`s without honouring the deadline, so that iteration emits no frame at all and retries immediately.
- **NVS is not a jitter source.** It is initialised only at boot; there are no runtime writes. Do not go looking for it.

### Loss: silent, and undetectable by content

There is exactly one `esp_spp_write` call site in the firmware, and `ESP_SPP_WRITE_DONE_EVT` is never handled — writes are fire-and-forget. Flow control is a single congestion flag:

| Condition | Firmware action | What you see |
|---|---|---|
| Link congested | frame **silently dropped** — no signal, no retransmit | a gap |
| Write error | connection torn down | EOF mid-stream |
| Write accepted, not yet delivered | no tracking at all | arrives later, possibly bursty |
| Write mutex not acquired in 100 ms | for packets → disconnect | EOF mid-stream |

**There is no ack, no queue, no retransmit and no flow control.** A slow reader loses data; it never back-pressures the device. Assume frames vanish and design for it.

Because the 36-byte frame carries **no sequence number, no timestamp and no counter**, you cannot detect loss from frame content. The only tool is timing: a gap wider than roughly two periods *plus* the expected jitter (500 ms diagnostic spike, I²C stall) means frames were dropped. Note that at 100 Hz a 36-byte frame is only ~3.6 KB/s, so sustained congestion means your reader is falling behind, not that the link is saturated.

Also note the **`battery` field steps at most once every 2 seconds** — `battery_task` samples on a 2 s period and writes a shared byte. Within a single frame the battery value can be up to 2 s staler than the accelerometer fields beside it. Do not treat it as a same-instant measurement.

## Efficiency guidance

**At 100 Hz, Python's CPU is not your bottleneck.** 100 `unpack` calls per second is nothing. The real risks are **unbounded buffer growth** and **backlog-driven latency** — a consumer that falls behind, buffers everything, and then replays a stale backlog. Optimise for those, not for cycles.

- **Precompile the `struct` format once.** `struct.Struct("<6f3hHB")` created at module scope, then call `.unpack()` per frame — `tools/stasys_packet.py:32-36` already does this. Passing the format string to `struct.unpack` each call re-parses it every time; it is a real cost only in hot loops, but there is no reason to pay it.
- **Reuse your read buffer.** Read into a fixed `bytearray` and slice, rather than concatenating into a growing `bytes` across the session.
- **Put a bounded, drop-oldest queue between the reader and your consumer.** This is the single most important structural choice. The reader thread must never block on the consumer — when the consumer stalls, drop the oldest frames and keep the newest. Degrades to *staleness*; the alternative (unbounded queue) degrades to *latency collapse*.

  ```python
  from collections import deque
  from threading import Lock

  class DropOldestQueue:
      def __init__(self, max_frames=256):
          self._items = deque(maxlen=max_frames)   # maxlen gives drop-oldest for free
          self._lock = Lock()

      def put(self, frame):
          with self._lock:
              self._items.append(frame)

      def drain(self):
          with self._lock:
              items, self._items = list(self._items), deque(maxlen=self._items.maxlen)
          return items
  ```

- **Do not format, log or serialise per frame.** Printing or JSON-encoding at 100 Hz will dominate your CPU and your I/O long before `unpack` does. Batch, sample down, or write binary.
- **Filter non-finite floats at the consumer, not in the parser.** The firmware does **not** sanitize NaN/Inf — `test_parser_accepts_nan_float_payload` explicitly asserts such a frame must parse successfully. Rejecting it in the parser would break legitimate captures (a sensor fault is real data your app may want to see). Use `math.isfinite` where it matters to you.

### Transport on Windows

The working path in this repo is a **pyserial outgoing COM port**, not a `pybluez` RFCOMM socket — there is no RFCOMM/`pybluez` code anywhere in the project. After pairing, Windows exposes the SPP service as a virtual COM port; read it exactly as you would a serial port. `tools/stasys_packet.py --port COM7 --key-file ... --identity ... --generation ...` implements this path end to end.

(One subtlety if you match a discovered device name against a MAC: the advertised `STASYS-XXXX` is derived by reading the 6-byte MAC into a `uint64_t` on a little-endian core and taking `mac >> 32`, so `XXXX` is the **byte-reversed** tail. For MAC `AA:BB:CC:DD:EE:FF` the name is `STASYS-FFEE`, not `STASYS-EEFF`. The 6-byte `identity` used in the transcript is raw display order and is *not* reversed.)

## Reconnect and session lifecycle

**Every connection requires a full re-authentication.** There is no session resume, no token and no cached state: each open produces a fresh 32-byte nonce, resets `auth_attempts`, and requires a new `PROOF`. Plan for this on every reconnect.

### `spp_generation` — the reconnect trap

`spp_generation` is an internal `uint32_t` incremented **once per accepted connection open** (`++spp_generation`, skipping 0 on wraparound). It is mixed into the auth transcript and **is never transmitted** — your client cannot learn it from the stream. It is deliberately **not** reset on disconnect; it survives until the device reboots.

So the value you must supply is:

```text
generation = (number of connections the device has accepted since it last booted)
           = Nth accepted connection open, starting at 1
```

Reconnect recipe:

```python
generation = 1            # after the device boots
while True:
    with open_connection() as conn:
        authenticate(conn, identity, key, generation=generation)
        run_stream(conn)
    generation += 1       # the device just incremented its own counter on that open
# reset generation to 1 ONLY after the device reboots
```

**Supplying a stale generation produces a perfectly well-formed HMAC that the device rejects with `FAIL`.** The proof will "look right" and still fail — there is no error message distinguishing this from a wrong key. If you see immediate `FAIL`s after a successful first connect, check the generation before anything else. The reference CLI exposes it as `--generation` (default `1`), which is correct only for a freshly booted device accepting its first connection.

### Other lifecycle facts

- **Second host is refused silently.** The firmware allows one client; a second opener is disconnected on open with **no banner and no error line**. Handle the case of being kicked by another host with an immediate, unexplained EOF.
- **No ASCII after `OK\n`.** No heartbeat, no periodic text, no terminator — only 36-byte frames until the link drops. Do not write a parser that waits for a periodic line to detect liveness; infer liveness from frame arrival timing instead.
- **No command channel after auth.** Bytes you send post-auth are discarded. There is no way to pause, query or reconfigure the stream over the socket.
- **Pairing is a separate, prior layer.** Bluetooth SSP (Just Works; legacy PIN requests are rejected) must succeed before the application handshake even begins. Pairing failures surface as connection/refusal problems, not as `FAIL` lines.
- **Disconnect sends nothing** — no `BYE`, no reason code. EOF is the only signal, and it means the same thing whether the device rebooted, another host connected, or your auth attempts ran out.

## Known documentation traps

- **`SENS` and `PIEZO` lines are UART-only.** They are emitted with `ESP_LOGI` to the serial console at 115200 baud and **never reach the Bluetooth socket** — the only mechanism putting bytes on SPP is `spp_write`, which they do not call. If you are reading over Bluetooth, expect *only* the handshake lines and binary frames.
  > Note: `docs/superpowers/specs/2026-09-27-sensor-serial-logging-design.md` states that `SENS` appears approximately every 500 ms *after authentication*, implying it is reachable from the client. The implementation does not do that — the `SENS` log has no Bluetooth-state guard and is written only to the console. **The code is authoritative here.**
- **The 36-byte frame has no version field, no sequence counter, no timestamp, no flags and no per-frame MAC.** The protocol version (`STASYS_AUTH_VERSION` = 2) appears only in the handshake's `READY v=2` line. Per-frame authentication of telemetry is planned but not implemented.
- **The checksum is integrity, not security.** It is a plain XOR over 33 bytes — anyone can recompute it. Do not treat a passing checksum as evidence the frame came from your device.

## Failure-mode checklist

| Symptom | Most likely cause | Check first |
|---|---|---|
| Three `FAIL\n` then disconnect, on every attempt | **Stock build with no provisioned key** (fail closed) | Confirm `staysys_provisioned_key` is defined in *your* firmware build before touching the client |
| Immediate `FAIL` right after a previously working connect | **Stale `spp_generation`**, or wrong key | Increment generation per connection; verify identity byte order |
| `FAIL` only after a delay | 10 s auth deadline expired (it is evaluated when you send) | Send the proof promptly after `OK`-equivalent; check your read loop isn't stalled |
| Disconnect with **no** `FAIL` after several attempts | Line-length violation (≠ 70 chars) or 3rd failed attempt | Verify exactly `PROOF ` + 64 hex + `\n`, no trailing whitespace |
| Handshake OK, then buffer never yields frames | Still in phase 1 — `OK` not consumed | Confirm you flipped state on reading `OK` and drained any tail bytes |
| Buffer grows without bound | Missing buffer cap / not discarding before `AA BB` | Apply the 144-byte cap; discard up to the next header |
| `checksum_errors` climbing slowly | Healthy resync after a dropped/fragmented frame | Normal if it settles; a steadily climbing counter means a genuinely corrupt link |
| `checksum_errors` climbing rapidly | Desynced framing — almost certainly advancing by 36 instead of 1 | Re-read step 5 of the resync algorithm |
| Intermittent gaps, otherwise clean | **Normal** — congestion drops, no signal | Confirm your reader isn't the bottleneck (bounded queue draining fast) |
| Sudden EOF mid-stream | Write error, second host connected, or device reboot | All three present identically: reconnect with `generation + 1` |
