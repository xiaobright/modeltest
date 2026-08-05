# Pull Request: Project2 — Gateway authz hardening + ESP32-S3 v4 network backhaul restore

## Summary

Two coordinated fixes bring Project2 to a testable, contract-compliant state:

1. **Gateway (Python):** Close authentication/authorization gaps in the v3 admin & context APIs,
   add a real `care_events` module with legacy SQLite migration, fix the sleep CSV multi-bed
   strategy, and keep the local voice assistant working after auth tightening.
2. **Firmware (ESP32-S3 testpro4):** Restore the Wi-Fi STA + Bemfa MQTT network backhaul that the
   v4 firmware had stubbed out (`TODO(v4)`), wiring it in parallel with the existing USB CDC path
   and implementing the documented USB packet / CRC16-CCITT / topic conventions.

No features were removed, no test data was hardcoded, security was not lowered, and `tests/` and
`tools/` were not modified.

## Initial diagnosis (before changes)

- `python tests/run_public_tests.py project2_task` → **all public tests passed** (compile + smoke).
- `python tools/run_debug_probe.py project2_task` → **FAILs**:
  - Management APIs (`/api/v3/...` admin/config) returned **200 even with a missing or forged
    cookie** (no authorization enforced on localhost).
  - Unknown-identity and expired sessions were **allowed** instead of denied.
  - `care_events` returns **404**, and room/bed were **not normalized** on create/query.
  - Voice module had a **warning** (relied on ambient session after auth tightening).
- ESP32-S3 firmware (`esp32/testpro4`): the v4 refactor left network backhaul as
  `TODO(v4): 网络回传链路 — 需要补全`; only USB CDC was active.

## Changes

### Gateway — `gateway/auth.py`
- `_password_hash` now **always salts** (PBKDF2-SHA256, 200k iters); empty salt no longer accepted
  for new accounts.
- `admin_account_exists()` checks the DB instead of trusting a flag.
- `get_admin_http_session` validates `token_hash`, expiry (`expires_ts`), and active flag.
- Added `_issue_login` helper; `login_admin_account` accepts a **legacy plaintext + empty-salt**
  seed once, then **upgrades** it to a salted hash.
- Restored `delete_admin_http_session` to delete by `token_hash`.

### Gateway — `gateway/db.py`
- Full `care_events` schema with `severity`/`source`/`created_by`/`ts`.
- Added `_migrate_care_events`: guards a missing table, `ALTER TABLE` adds missing columns,
  backfills `ts` from `created_ts`, and normalizes legacy `room`/`bed` via `UPPER(TRIM())`.
  **Old rows are preserved.**

### Gateway — `gateway/care_events.py`
- Salted-safe `create_care_event` with room/bed normalization; `list_care_events` normalizes the
  query and orders by `ts DESC`; `build_care_events_context` returns items + brief.

### Gateway — `gateway/gateway.py`
- `_authorized_for_api` now **requires the admin cookie for management APIs even from localhost**;
  the local bypass is limited to a whitelist (`_path_allows_local_service`): `/api/v2/*`,
  `/api/esp/*`, `context/chat`, `identity/gallery`, `identity/match`, `vision/observation`.
- `session_is_authenticated` enforces all contract rules: unknown `identity_state`, `none`
  assurance, expired `expires_ts`, or missing `actor_subject_id` → `false`. `GET /api/v3/context/chat`
  returns `allowed:false` + empty modalities for unauthenticated/unknown/expired/no-actor sessions.
- Integrated `build_care_events_context` into `build_chat_context_v3` (`care_events` modality +
  `allowed_sections`); added `GET`/`POST /api/v3/care/events` routes (admin or authorized context).

### Gateway — `gateway/sleep_importer.py`
- `first` policy now returns `beds[0]` (was incorrectly `beds[-1]`), fixing multi-bed selection.

### Voice — `voice/voice_assistant_integrated.py`
- Added `fetch_current_session_id()` + `GATEWAY_SESSION_CURRENT_URL`; `build_gateway_context_params`
  now falls back to the current session id so tightening doesn't break the local assistant.

### ESP32-S3 firmware — `esp32/testpro4`
New modules (self-contained, no external component download needed — the offline build env cannot
reach the Espressif component registry, see Risks):
- `protocol_packet.{h,cpp}` — CRC16-CCITT (init `0xFFFF`, poly `0x1021`) over **payload only**,
  little-endian, plus the documented packet builder
  `[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`.
- `maixsense_parser.{h,cpp}` — robust ToF frame parser feeding the packet builder.
- `device_config.{h,cpp}` — config completeness check + **lowercase** topic builder
  (`{room}{bed}tof1/tof2/mlx1/mlx2`).
- `mqtt_min.{h,cpp}` — minimal MQTT 3.1.1 client over **lwIP BSD sockets** (Bemfa TCP `bemfa.com:9501`),
  CONNECT/CONNACK + QoS0 PUBLISH + 60s heartbeat, with auto-reconnect.
- `mqtt_payload.{h,cpp}` — base64 (mbedTLS) of the **raw payload** and publish as
  `{"payload_b64":"..."}` via `mqtt_min`.

`main.cpp` wiring:
- Includes added; the local duplicate `device_config_t` replaced by the shared header; `g_mqtt_client`
  / `s_mqtt_connected` replaced by `mqtt_min` internal state.
- Implemented `network_config_ready()` / `wifi_init_sta()` / `mqtt_heartbeat_task` /
  `start_network_backhaul()` (called in `app_main`, guarded by `s_device_config_ready`).
- ToF (`usb_send_tof_payload`) and MLX (`mlx_sender_task`) tasks now **also** publish the raw payload
  to the correct topic in addition to USB CDC; stale `TODO(v4)` backhaul comment replaced.

Build files:
- `main/CMakeLists.txt` — added the 5 new `.cpp` sources; `REQUIRES` now includes `esp_wifi`,
  `esp_netif`, `esp_event`, `lwip`, `mbedtls` (no `esp_mqtt`, which is unavailable offline).
- `main/idf_component.yml` — `espressif/esp_tinyusb` only (no `esp_mqtt`).

## Final verification

- `python tests/run_public_tests.py project2_task` → **all public tests passed** (compile, admin
  setup/page, refactored-feature module callables, sleep import, gateway smoke).
- `python tools/run_debug_probe.py project2_task` → **all visible diagnostic checks passed**:
  - admin setup 200; management API rejects missing **and** forged cookies; accepts valid cookie;
  - unknown-identity and expired sessions denied;
  - care_event write rejects missing admin cookie; room/bed normalized on create + query;
  - voice module references current-session fetch (info);
  - ESP note points to the build tool.
- `python tools/run_espidf_build.py project2_task` (env `E:\esp` IDF v6.0.1, target **esp32s3**) →
  **Build finished successfully. Successfully created ESP32-S3 image.**

## Risks / unverified

- **ESP MQTT against live Bemfa not runtime-tested.** The firmware compiles and links, and the
  protocol matches `docs/protocol.md` (§LAN回传) and `reference/espidf_protocol_contract.md`, but no
  live `bemfa.com` uplink was exercised (no hardware/network in this environment). The minimal MQTT
  client implements only what the backhaul needs (CONNECT, QoS0 PUBLISH, heartbeat); subscribe flows
  are out of scope for sensor uplink.
- **`esp_mqtt` component was intentionally not used** because the build host returns `403 Forbidden`
  from `components-file.espressif.com` (offline). The self-contained `mqtt_min` avoids that
  dependency. If the component registry becomes reachable, swapping to `esp_mqtt` is optional.
- `sdkconfig.defaults` emits two harmless unknown-kconfig warnings
  (`TINYUSB_ENABLED`, `USB_OTG_SUPPORTED`); pre-existing, not introduced here.
- Legacy admin plaintext seeds are accepted **once and upgraded**; this is a deliberate, bounded
  migration path, not a permanent weakening.
