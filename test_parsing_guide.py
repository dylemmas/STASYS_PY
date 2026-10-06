"""Source-contract tests for docs/spp-parsing-guide.md.

The guide states numeric and behavioural claims about the firmware. These
tests pin each claim to the actual firmware source so the guide cannot rot
silently when a constant changes: if the firmware moves, the test fails and
the guide must be edited in the same change.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE = REPO_ROOT / "docs" / "spp-parsing-guide.md"
MAIN_CPP = REPO_ROOT / "src" / "main.cpp"
APP_PROTOCOL_H = REPO_ROOT / "components" / "app_protocol" / "include" / "app_protocol.h"
APP_PROTOCOL_CPP = REPO_ROOT / "components" / "app_protocol" / "app_protocol.cpp"
SYSTEM_CONFIG_H = REPO_ROOT / "components" / "system_config" / "system_config.h"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def define_macro(source: str, name: str) -> str:
    """Return the value text of `#define NAME ...`, or '' if absent."""
    match = re.search(rf"^#define\s+{re.escape(name)}\s+(\S+)", source, re.MULTILINE)
    return match.group(1) if match else ""


class FirmwareConstantTests(unittest.TestCase):
    """The firmware still has the constants the guide documents."""

    @classmethod
    def setUpClass(cls):
        cls.header = read(APP_PROTOCOL_H)
        cls.impl = read(APP_PROTOCOL_CPP)
        cls.config = read(SYSTEM_CONFIG_H)
        cls.main = read(MAIN_CPP)

    def test_packet_size_is_36(self):
        self.assertEqual(define_macro(self.header, "STASYS_PACKET_SIZE"), "36u")

    def test_header_bytes_are_aa_bb(self):
        self.assertEqual(define_macro(self.header, "STASYS_PACKET_HEADER_0"), "0xAAu")
        self.assertEqual(define_macro(self.header, "STASYS_PACKET_HEADER_1"), "0xBBu")

    def test_packet_period_is_10000_us(self):
        self.assertEqual(define_macro(self.config, "STASYS_PACKET_PERIOD_US"), "10000")

    def test_auth_constants(self):
        self.assertEqual(define_macro(self.header, "STASYS_AUTH_VERSION"), "2u")
        self.assertEqual(define_macro(self.header, "STASYS_AUTH_NONCE_SIZE"), "32u")
        self.assertEqual(define_macro(self.header, "STASYS_AUTH_MAX_ATTEMPTS"), "3u")
        self.assertEqual(define_macro(self.header, "STASYS_AUTH_MAX_LINE"), "160u")
        self.assertEqual(define_macro(self.header, "STASYS_AUTH_TIMEOUT_MS"), "10000u")

    def test_checksum_covers_bytes_2_through_34(self):
        # `for (i = 2; i < 35; ++i) output[35] ^= output[i]` covers 2..34 inclusive.
        self.assertRegex(
            self.impl,
            r"for\s*\(\s*size_t\s+i\s*=\s*2\s*;\s*i\s*<\s*35\s*;",
            "checksum loop no longer covers offsets 2..34 inclusive",
        )

    def test_greeting_is_single_ready_auth_line(self):
        self.assertIn('"READY v=%u\\nAUTH %s\\n"', self.main)


class FlowControlClaimsTests(unittest.TestCase):
    """Claims the guide makes about loss and flow control."""

    @classmethod
    def setUpClass(cls):
        cls.main = read(MAIN_CPP)

    def test_single_esp_spp_write_call_site(self):
        # The guide states frames are fire-and-forget with one write per packet.
        occurrences = [
            line
            for path in sorted((REPO_ROOT / "src").rglob("*.[ch]pp")) + sorted(
                (REPO_ROOT / "components").rglob("*.[ch]pp")
            )
            for line in read(path).splitlines()
            if "esp_spp_write(" in line
        ]
        self.assertEqual(
            len(occurrences),
            1,
            f"expected exactly one esp_spp_write call site, found {len(occurrences)}",
        )

    def test_write_done_event_is_not_handled(self):
        # No completion/ack: the guide's "no flow control" claim depends on this.
        self.assertNotIn("ESP_SPP_WRITE_DONE_EVT", self.main)

    def test_sens_is_uart_log_not_bluetooth(self):
        # SENS must be an ESP_LOGI, never passed to spp_write.
        self.assertIn('ESP_LOGI(TAG, "SENS', self.main)
        self.assertNotRegex(
            self.main,
            r'spp_write\s*\([^;]*"SENS',
            "SENS must not be written to the Bluetooth socket",
        )


class FailClosedClaimTests(unittest.TestCase):
    """The guide's up-front warning that a stock build can never authenticate."""

    @classmethod
    def setUpClass(cls):
        cls.main = read(MAIN_CPP)

    def test_provisioned_key_is_weak_and_defined_nowhere(self):
        self.assertIn("__attribute__((weak))", self.main)
        sources = [
            path
            for pattern in ("*.c", "*.cpp", "*.h", "*.hpp")
            for path in REPO_ROOT.rglob(pattern)
            if ".pio" not in path.parts and "__pycache__" not in path.parts
        ]
        for path in sources:
            for line in read(path).splitlines():
                if "staysys_provisioned_key" not in line:
                    continue
                # Only a *definition* would invalidate the fail-closed claim.
                # A definition names the symbol followed by "(...". Legitimate
                # uses are distinguishable: `return <sym>(...)` is a call and
                # `extern ... <sym>(...)` is the declaration; the nullptr check
                # never puts "(" straight after the name.
                stripped = line.strip()
                if not re.search(r"staysys_provisioned_key\s*\(", stripped):
                    continue
                self.assertTrue(
                    "return " in stripped or "extern" in stripped,
                    f"{path} appears to define staysys_provisioned_key: {stripped}",
                )

    def test_key_provider_fails_closed(self):
        self.assertIn("if (staysys_provisioned_key == nullptr) return -1;", self.main)


class GuideContentTests(unittest.TestCase):
    """The guide exists and still states the pinned constants."""

    REQUIRED_CLAIMS = (
        "STASYS_PACKET_SIZE",
        "STASYS_PACKET_PERIOD_US",
        "STASYS_AUTH_VERSION",
        "STASYS_AUTH_MAX_ATTEMPTS",
        "STASYS_AUTH_MAX_LINE",
        "STASYS_AUTH_TIMEOUT_MS",
        "staysys_provisioned_key",
        "spp_generation",
        "PacketParser",
        "tools/README.md",
        "0xAA",
        "0xBB",
        "10000",
        "160",
    )

    @classmethod
    def setUpClass(cls):
        cls.guide = read(GUIDE) if GUIDE.exists() else ""

    def test_guide_exists(self):
        self.assertTrue(GUIDE.exists(), f"{GUIDE} is missing")

    def test_guide_states_pinned_constants(self):
        self.assertTrue(self.guide, "guide is empty or missing")
        for claim in self.REQUIRED_CLAIMS:
            self.assertIn(claim, self.guide, f"guide no longer states {claim!r}")

    def test_guide_links_the_byte_table_rather_than_duplicating_it(self):
        self.assertTrue(self.guide)
        self.assertIn("tools/README.md", self.guide)
        self.assertNotIn("| 2 | 4 |", self.guide, "byte offset table must live only in tools/README.md")


if __name__ == "__main__":
    unittest.main()
