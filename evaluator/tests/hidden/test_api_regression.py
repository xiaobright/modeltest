#!/usr/bin/env python3
import unittest

from eval_helpers import GatewayServer, TempProjectTestMixin, request_json


class ApiRegressionTest(TempProjectTestMixin, unittest.TestCase):
    def test_legacy_v2_and_esp_paths_still_work(self):
        server = GatewayServer(self.tmp_path)
        try:
            status, data, _ = request_json(server.base_url, "POST", "/api/v2/ingest?room=R1203&bed=B1", {
                "kind": "radar",
                "payload": {"heart_rate": 72, "breath_rate": 16},
            })
            self.assertEqual(status, 200, data)

            status, data, _ = request_json(server.base_url, "GET", "/api/v2/latest?room=R1203&bed=B1")
            self.assertEqual(status, 200, data)
            self.assertIn("radar", str(data).lower())

            status, data, _ = request_json(server.base_url, "POST", "/api/v2/ingest/posture?room=R1203&bed=B1", {
                "label": "supine",
                "confidence": 0.91,
            })
            self.assertIn(status, (200, 204), data)

            status, data, _ = request_json(server.base_url, "GET", "/api/v2/voice/chat_context?room=R1203&bed=B1")
            self.assertEqual(status, 200, data)

            status, data, _ = request_json(server.base_url, "GET", "/api/esp/status?room=R1203&bed=B1")
            self.assertEqual(status, 200, data)
            self.assertIn("online", data)
        finally:
            server.close()

    def test_esp_set_requires_all_streams_and_payload_is_opt_in(self):
        server = GatewayServer(self.tmp_path)
        try:
            gw = server.gw
            gw.append_esp_packet("R1203", "B1", 0x01, 0x01, b"mlx1", 0, "test", True)
            partial = gw.get_latest_esp_set("R1203", "B1", include_payload=False)
            self.assertEqual(partial, {}, "partial ESP set must not become latest complete set")

            gw.append_esp_packet("R1203", "B1", 0x01, 0x02, b"mlx2", 0, "test", True)
            gw.append_esp_packet("R1203", "B1", 0x02, 0x01, b"tof1", 0, "test", True)
            gw.append_esp_packet("R1203", "B1", 0x02, 0x02, b"tof2", 0, "test", True)

            latest = gw.get_latest_esp_set("R1203", "B1", include_payload=False)
            self.assertEqual(set(latest.get("streams", [])), {"mlx1", "mlx2", "tof1", "tof2"})
            self.assertNotIn("payload_b64", str(latest))

            latest_payload = gw.get_latest_esp_set("R1203", "B1", include_payload=True)
            self.assertIn("payload_b64", str(latest_payload))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
