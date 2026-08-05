#!/usr/bin/env python3
import os
import re
import unittest
from pathlib import Path


def strip_cmake_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def strip_c_like_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def require_contains(testcase: unittest.TestCase, text: str, token: str, message: str) -> None:
    if token not in text:
        testcase.fail(message)


def require_regex(testcase: unittest.TestCase, text: str, pattern: str, message: str) -> None:
    if re.search(pattern, text) is None:
        testcase.fail(message)


class EspIdfStaticContractTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()
        self.esp = self.project / "esp32" / "testpro4"

    def test_required_files_exist(self):
        self.assertTrue((self.esp / "CMakeLists.txt").is_file())
        self.assertTrue((self.esp / "main" / "CMakeLists.txt").is_file())
        self.assertTrue((self.esp / "main" / "usb_descriptors.c").is_file())
        self.assertTrue((self.esp / "main" / "tusb_config.h").is_file())

    def test_cmake_has_core_dependencies(self):
        """Check that core dependencies (USB, NVS, MLX) are present.
        
        MQTT/mbedtls dependencies are checked separately in
        test_mqtt_dependencies_added — they are intentionally
        missing in the broken seed and must be added by the candidate.
        """
        cmake = strip_cmake_comments(
            (self.esp / "main" / "CMakeLists.txt").read_text(encoding="utf-8", errors="replace")
        )
        for token in ["main.cpp", "usb_descriptors.c", "esp_tinyusb", "nvs_flash"]:
            require_contains(self, cmake, token, f"{token} missing from active CMakeLists.txt")

    def test_mqtt_dependencies_added(self):
        """Check that Wi-Fi + MQTT + mbedtls dependencies have been added to CMakeLists.txt.
        
        This test FAILS in the broken seed — the candidate must add:
          esp_wifi, esp_netif, esp_event, lwip, mqtt, mbedtls
        """
        cmake = strip_cmake_comments(
            (self.esp / "main" / "CMakeLists.txt").read_text(encoding="utf-8", errors="replace")
        )
        for token in ["mqtt", "mbedtls", "esp_wifi", "esp_netif", "esp_event", "lwip"]:
            require_regex(
                self,
                cmake,
                rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])",
                f"{token} missing from active CMake REQUIRES",
            )

        manifest = strip_cmake_comments(
            (self.esp / "main" / "idf_component.yml").read_text(encoding="utf-8", errors="replace")
        )
        require_contains(self, manifest, "espressif/mqtt", "espressif/mqtt missing from active idf_component.yml")

    def test_protocol_contract_markers_exist(self):
        """Check that core protocol markers (packet format, CRC) are present.
        
        MQTT-related markers (payload_b64, mbedtls_base64) are checked
        separately in test_mqtt_protocol_markers_exist.
        """
        text = strip_c_like_comments("\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.esp / "main").glob("*")
            if p.suffix.lower() in {".c", ".cpp", ".h", ".hpp"}
        ))
        for token in ["0xAA", "0x55", "crc16"]:
            require_contains(self, text, token, f"{token} missing from active ESP32 source")

    def test_mqtt_protocol_markers_exist(self):
        """Check that MQTT protocol implementation markers exist in source code.
        
        This test FAILS in the broken seed — the candidate must implement:
          - payload_b64: JSON key for Base64-encoded MQTT messages
          - mbedtls_base64: Base64 encoding function for MQTT payloads
        """
        text = strip_c_like_comments("\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.esp / "main").glob("*")
            if p.suffix.lower() in {".c", ".cpp", ".h", ".hpp"}
        ))
        for token in ["payload_b64", "mbedtls_base64", "esp_mqtt_client_publish"]:
            require_contains(self, text, token, f"{token} missing from active ESP32 MQTT source")

    def test_wifi_mqtt_runtime_started(self):
        """Check that active firmware code starts Wi-Fi and MQTT runtime.

        This intentionally avoids requiring a particular helper function
        name.  The contract is that the restored firmware actually starts
        ESP-IDF Wi-Fi and MQTT, not that it mirrors the seed TODO text.
        """
        text = strip_c_like_comments("\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.esp / "main").glob("*")
            if p.suffix.lower() in {".c", ".cpp", ".h", ".hpp"}
        ))
        for token in ["esp_wifi_start", "esp_mqtt_client_start"]:
            require_contains(self, text, token, f"{token} missing from active ESP32 source")

    def test_topic_and_nvs_contract_markers_exist(self):
        """Check the parts that distinguish a real Bemfa backhaul from
        placeholder MQTT calls: required NVS keys, normalized topic names,
        and all four sensor stream suffixes.
        """
        text = strip_c_like_comments("\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.esp / "main").glob("*")
            if p.suffix.lower() in {".c", ".cpp", ".h", ".hpp"}
        ))
        for token in ["wifi_ssid", "wifi_pass", "bemfa_uid", "room", "bed"]:
            require_contains(self, text, token, f"NVS key/field {token} missing from ESP32 source")
        for stream in ["tof1", "tof2", "mlx1", "mlx2"]:
            require_contains(self, text.lower(), stream, f"topic stream suffix {stream} missing from ESP32 source")
        require_regex(
            self,
            text,
            r"(lower_copy|tolower|std::transform)",
            "topic builder must normalize room/bed to lowercase",
        )

    def test_network_config_requires_wifi_and_uid(self):
        """config readiness must include network credentials, not just room/bed."""
        text = strip_c_like_comments("\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.esp / "main").glob("*")
            if p.suffix.lower() in {".c", ".cpp", ".h", ".hpp"}
        ))
        require_regex(
            self,
            text,
            r"(config_is_complete|device_config_is_ready|network_config_ready)[\s\S]*wifi_ssid",
            "config readiness does not check wifi_ssid",
        )
        require_regex(
            self,
            text,
            r"(config_is_complete|device_config_is_ready|network_config_ready)[\s\S]*bemfa_uid",
            "config readiness does not check bemfa_uid",
        )

    def test_payload_buffer_not_fixed_undersized(self):
        """ToF/MQTT payload_b64 must not use a tiny fixed stack buffer (e.g. 256).

        Allowed: dynamic allocation (malloc/new/vector/string) or large buffers.
        Status is also exported for score_model as f8_07 via summary when uncertain.
        """
        raw = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.esp / "main").glob("*")
            if p.suffix.lower() in {".c", ".cpp", ".h", ".hpp"}
        )
        text = strip_c_like_comments(raw)
        # Fail hard on classic bait: char b64_buf[256] used with payload encoding.
        tiny = re.search(r"\b(?:char|uint8_t)\s+\w*b64\w*\s*\[\s*256\s*\]", text)
        dynamic = re.search(r"\b(malloc|calloc|realloc|new\s+char|std::vector|std::string)\b", text)
        large = re.search(r"\b(?:char|uint8_t)\s+\w+\s*\[\s*(?:[4-9]\d{3,}|\d{5,})\s*\]", text)
        if tiny and not (dynamic or large):
            self.fail(
                "fixed 256-byte base64/payload buffer is too small for ToF JSON; "
                "use dynamic allocation or a sufficiently large buffer"
            )
        # If neither tiny bait nor dynamic path is obvious, do not fail — human may review.
        # (pass when dynamic/large present, or no tiny buffer)


if __name__ == "__main__":
    unittest.main(verbosity=2)

