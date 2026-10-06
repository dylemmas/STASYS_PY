# STASYS Bluetooth packet guide

`stasys_packet.py` is a reference decoder for the firmware's Bluetooth Classic
Serial Port Profile (SPP) stream. It can decode offline captures or read live
from a Windows Bluetooth outgoing COM port. The live mode requires `pyserial`.

## Live Windows COM-port usage

Pair the ESP32 with Windows and note the **Outgoing** Bluetooth COM port. Do not
use the USB COM port used by PlatformIO for flashing and firmware logs. Install
the optional serial dependency:

```text
python -m pip install pyserial
```

Start a live receiver with a development key file or environment variable. No
key is embedded or supplied by default:

```text
python tools/stasys_packet.py --port COM7 --key-file device.key --identity 010203040506 --generation 1
```

Alternatively use `--key-env STASYS_DEVICE_KEY`; the value is read only from
the process environment. To stop after a fixed number:

```text
python tools/stasys_packet.py --port COM7 --key-file device.key --identity 010203040506 --generation 1 --count 10
```

The default 115200 baud value is nominal for a virtual Bluetooth COM port. The
receiver still treats the connection as an arbitrary byte stream. It handles
fragmented reads, multiple frames in one read, and authentication text followed
by binary data. The secret is intentionally not stored in this guide.

## Transport and authentication

The firmware sends `READY v=2\n` followed by `AUTH <64 hex nonce>\n` after
connection. The client returns `PROOF <64 hex HMAC>\n`, where the HMAC-SHA256
transcript is the domain `STASYS-AUTH/v2` plus the Bluetooth identity, little-
endian connection generation, and raw nonce. The firmware replies `OK\n` only
when a protected per-device key verifies the proof; missing provisioning fails
closed. Binary sensor frames begin after this step.

## Frame format

Every sensor frame is exactly 36 bytes:

| Offset | Size | Type | Field |
| ---: | ---: | --- | --- |
| 0 | 2 | bytes | Header `AA BB` |
| 2 | 4 | little-endian `float32` | `ax` |
| 6 | 4 | little-endian `float32` | `ay` |
| 10 | 4 | little-endian `float32` | `az` |
| 14 | 4 | little-endian `float32` | `gx` |
| 18 | 4 | little-endian `float32` | `gy` |
| 22 | 4 | little-endian `float32` | `gz` |
| 26 | 2 | little-endian signed `int16` | `mag_x` |
| 28 | 2 | little-endian signed `int16` | `mag_y` |
| 30 | 2 | little-endian signed `int16` | `mag_z` |
| 32 | 2 | little-endian unsigned `uint16` | `piezo` |
| 34 | 1 | unsigned `uint8` | `battery` |
| 35 | 1 | `uint8` | XOR checksum |

The checksum is:

```text
checksum = byte[2] XOR byte[3] XOR ... XOR byte[34]
```

The header and checksum byte are not included in the XOR. Reject a frame with
a wrong header, wrong length, or wrong checksum.

## Android implementation notes

Use a persistent `ByteArray` or ring buffer. Append every received SPP chunk,
search for `AA BB`, wait until 36 bytes are available, validate the checksum,
then remove exactly one frame and repeat. On a checksum failure, advance one
byte and search again so the next valid frame can be recovered.

The equivalent Java/Kotlin payload layout is:

```text
ByteBuffer.order(ByteOrder.LITTLE_ENDIAN)
getFloat() six times             // ax, ay, az, gx, gy, gz
getShort() three times            // signed mag_x, mag_y, mag_z
getShort().toInt() and 0xffff    // unsigned piezo
get().toInt() and 0xff           // unsigned battery
```

The firmware currently converts acceleration to metres per second squared and
gyroscope values to radians per second before serialization. Magnetometer and
piezo values are raw sensor counts. Battery is a percentage from 0 to 100.

## Python usage

Decode hex captured from SPP:

```text
python tools/stasys_packet.py --hex "aabb..."
```

Decode a binary capture:

```text
python tools/stasys_packet.py --file capture.bin
```

Run the fragmented-input demonstration:

```text
python tools/stasys_packet.py --demo
```
