# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前在 workspace 根目录运行的两条自检命令及关键结果：

- `python tests\run_public_tests.py project2_task` → **全部通过**（公开测试故意只做编译与冒烟，不校验安全属性）。
- `python tools\run_debug_probe.py project2_task` → **6 项失败**：
  1. `management API rejects missing cookie` — FAIL：`GET /api/v3/subjects` 缺 cookie 仍返回 200。
  2. `management API rejects forged cookie` — FAIL：伪造 cookie 仍返回 200。
  3. `unknown identity session is denied` — FAIL：`identity_state=unknown` 的 session 被判为已认证。
  4. `expired session is denied` — FAIL：`expires_ts` 已过期的 session 被判为已认证。
  5. `care_event write rejects missing admin cookie` — FAIL：`POST /api/v3/care/events` 返回 404（路由不存在）。
  6. `care_event normalizes room/bed for create and query` — FAIL：小写写入、大写查不到，且表缺 `severity/source/created_by/ts` 列。
- 另有 voice 路径 Warning：收紧鉴权后若助手仍依赖隐式 ambient session，护理上下文同步会断。

根因（代码审查确认）：
- `auth._password_hash` 在无 salt 时直接返回明文密码；`auth.get_admin_http_session` 的 SQL `WHERE` 子句忽略 `token_hash`，返回任意活跃 session；`auth.admin_account_exists` 恒返回 `False`。
- `gateway._authorized_for_api` 对任何本机请求放行所有 `/api/` 路径，未使用 `_path_allows_local_service` 白名单。
- `gateway.session_is_authenticated` 对 `identity_state=unknown` 返回 `True`；`actor_can_access_target` 对无 actor 返回 `True`。
- `care_events.py` 表 schema 不完整、无 room/bed 规范化、无路由；`db.py` 的 `care_events` CREATE TABLE 也缺列且无迁移。
- `sleep_importer.py` 的 `first` 策略误用 `beds[-1]`（末位床）而非 `beds[0]`（首位床）。
- ESP32 `testpro4` 的 Wi-Fi/MQTT 回传被注释为 TODO，仅剩 USB CDC。

## 修改的文件列表

Gateway（Python）：
- `gateway/auth.py` — 密码加盐 PBKDF2 哈希、token 严格校验、`admin_account_exists` 查 DB。
- `gateway/care_events.py` — 完整 schema、旧表迁移、room/bed 规范化与大小写不敏感查询、context 摘要。
- `gateway/db.py` — `init_management_db` 委托 `care_events.ensure_care_events_schema` 做 care_events 建表+迁移。
- `gateway/gateway.py` — 收紧 `_authorized_for_api`、修复 `session_is_authenticated`/`actor_can_access_target`、接入 `modalities.care_events`、新增 `GET/POST /api/v3/care/events` 路由。
- `gateway/sleep_importer.py` — `first` 策略改用 `beds[0]`。
- `gateway/README.md` — 模块清单、鉴权边界、care_event、睡眠策略说明。

Voice：
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session`，无显式 `VOICE_SESSION_ID` 时主动拉取 `/api/v3/session/current`，不再依赖 gateway 隐式 ambient 回退。

ESP32 `testpro4`：
- `main/main.cpp` — 重写：USB CDC 与 MQTT 并行回传，调用新模块；保留 USB packet 契约与 ToF/MLX/UART 初始化。
- `main/protocol_packet.{h,cpp}` — 新增：USB packet 常量、CRC16-CCITT、header 构造、stream 名映射。
- `main/maixsense_parser.{h,cpp}` — 新增：MaixSense 字节流解析器（噪声/分块/坏尾/半帧）。
- `main/device_config.{h,cpp}` — 新增：NVS 读写、CFG 控制台、配置完整性校验、topic 规范化。
- `main/mqtt_payload.{h,cpp}` — 新增：Wi-Fi STA + Bemfa MQTT client + `{"payload_b64":"..."}` JSON 构造。
- `main/CMakeLists.txt` — 补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖与新源文件。
- `main/idf_component.yml` — 添加 `espressif/mqtt: "^1.0.0"` managed 依赖（IDF v6 已将 mqtt 移出核心）。

文档：
- `README.md` — care_event 接口、ESP32 Wi-Fi+MQTT 恢复说明、模块拆分。
- `RK3588_TEST_GUIDE.md` — 改造状态、睡眠策略、权限上下文测试更新。
- `PULL_REQUEST_TEMPLATE.md` — 本文件。

## 架构调整与模块设计

Gateway 保持模块边界，未把逻辑塞回 `gateway.py`：

- 鉴权全部在 `auth.py`；路由 glue 在 `gateway.py`；care_event CRUD/迁移/摘要 在 `care_events.py`；session/subject 在 `subjects.py`。
- `db.init_management_db` 通过延迟 import 调用 `care_events.ensure_care_events_schema(conn)`，避免 `db ↔ care_events` 循环导入。
- ESP32 固件按 ONBOARDING 推荐拆为 4 个模块：`protocol_packet`（协议常量+CRC）、`maixsense_parser`（帧解析）、`device_config`（NVS+topic）、`mqtt_payload`（Wi-Fi+MQTT+payload_b64）。`main.cpp` 只保留 ESP-IDF 初始化、硬件 bring-up、任务创建和把 payload 同时发往 USB CDC 与 MQTT 的 glue。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256，200k 迭代，16 字节随机盐，DB 只存盐+摘要，绝不落明文。
- Cookie：只保存 `secrets.token_urlsafe(32)` 随机 token；DB 存 `sha256(token)`；`get_admin_http_session` 严格按 `token_hash = ?` 查询，伪造 cookie 无法顶替已存在会话；登出删除对应 token_hash。
- `_authorized_for_api`：管理员 cookie 放行；本机请求只对白名单服务路径（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`）放行；管理类接口（subjects/assignments/credentials/care_events 等）即使来自本机也必须带管理员 cookie，缺/伪造一律 401。
- `/api/v3/context/chat`：本机可调用，但响应由 `build_chat_context_v3` 按 session 裁剪。`session_is_authenticated` 按 contract 收紧：`identity_state=unknown`、`assurance_level=none/空`、`expires_ts` 过期、缺 `actor_subject_id` 任一成立即视为未认证。`actor_can_access_target` 对无 actor 返回 `False`（不再“内部 worker 直接放行”）。未授权时 `target.patient`/`target.assignment`/各 modality 均为空，`modalities.care_events` 也为空。
- voice：新增 `fetch_current_session`，无显式 session_id 时主动拉取 `/api/v3/session/current` 并带回 `session_id`，不再依赖 gateway 的隐式 `get_current_session()` ambient 回退。无 recognized session 时 voice 收到 `policy.allowed=false` 并回复权限提示，不泄漏患者数据。
- 历史 SQLite 迁移：care_events 旧表缺列时 `ALTER TABLE ADD COLUMN` 补齐 `severity/source/created_by/ts`，旧行保留并回填默认值（`severity='info'`、`source='manual'`、`created_by=''`、`ts=0`）。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行策略（不整表丢弃显式行）：

- 行带 `room/bed`：只写入对应床位（配置床位大小写不敏感匹配）。
- 行不带 `room/bed`：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 写入 `BEDS[0]`（第一个配置床位，修复了原先误用 `beds[-1]` 末位床的 bug）。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过该行。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 仅显式调试模式，广播到所有床位，不作默认。
- 同一 CSV 内显式行与无归属行可并存：策略只作用于无归属行，显式行不受影响。

## care_event 实现细节

- 表：`care_events(event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts)`，索引 `(subject_id, ts DESC, created_ts DESC)`、`(room, bed, ts DESC, created_ts DESC)` 等。
- 迁移：`ensure_care_events_schema` 先 `CREATE TABLE IF NOT EXISTS`（全新库得完整 schema），再对旧表 `ALTER TABLE ADD COLUMN` 补缺列，最后建索引（避免在缺 `ts` 列的旧表上 `CREATE INDEX` 失败）。
- CRUD：`create_care_event` 写入时 `room/bed` 规范化为大写；`list_care_events` 查询用 `COLLATE NOCASE`，故旧库小写 `r1203/b1` 行也能被大写 `R1203/B1` 查到；按 `ts DESC, created_ts DESC` 排序，`limit` 默认 50（上限 500）。
- 路由：`POST /api/v3/care/events`（需管理员）、`GET /api/v3/care/events?subject_id=...` 或 `?room=...&bed=...&limit=...`（需管理员）。
- Context：`build_chat_context_v3` 在 `allowed=true` 时调用 `build_care_events_context`，`modalities.care_events` 返回最近 5 条事件摘要 + brief；未授权时为空。

## ESP32-S3 固件接口对齐说明

按 `reference/espidf_protocol_contract.md` 实现：

- Wi-Fi STA：`esp_wifi` STA 模式，凭据从 NVS `wifi_ssid/wifi_pass` 读取；`device_config_is_network_ready()` 要求 `ssid/password/uid/room/bed` 五项齐全才启动网络回传，否则仅 USB（USB 始终可用）。
- MQTT：broker `mqtt://{bemfa_host}:{bemfa_mqtt_port}`（默认 `bemfa.com:9501`），username=`bemfa_uid`，password 空，client_id 取 `device_id` 或 `esp32-posture-{room}{bed}`。连接异步建立，未连接时 `mqtt_publish_payload` 为 no-op。
- Topic：`device_config_build_topic(stream)` 产出 `{room}{bed}{stream}` 小写，如 `r1203b1tof1`，与 gateway `bed_config.topics_for()` 一致。stream 名由 `(sensor_type, sensor_id)` 映射：`(TOF,1)->tof1`、`(TOF,2)->tof2`、`(MLX,1)->mlx1`、`(MLX,2)->mlx2`。
- Payload：`{"payload_b64":"<base64 原始 payload>"}`。base64 内容是传感器原始 payload：ToF 为完整 MaixSense 帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`，MLX 为 768×float=3072 字节；**不是**完整 USB packet（无 AA55 header/CRC）。base64 缓冲按需 malloc（ToF ~13.4KB），用完即释放，避免静态大缓冲。
- USB packet 契约不变：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT（init 0xFFFF, poly 0x1021）仅覆盖 payload，小端序。`usb_send_tof_payload` 与 MLX sender 在保留 USB CDC 输出的同时镜像原始 payload 到对应 MQTT topic。
- 模块化：`protocol_packet`（常量+CRC+header+stream名）、`maixsense_parser`（帧解析，处理噪声/分块/坏尾/半帧/异常长度）、`device_config`（NVS+CFG控制台+完整性+topic）、`mqtt_payload`（Wi-Fi+MQTT+payload_b64）。`main.cpp` 仅保留初始化、硬件 bring-up、任务创建与 fan-out glue。
- NVS 控制台命令不变：`CFG? / CFGSET ssid=... / password=... / uid=... / room=... / bed=... / CFGRESET / REBOOT`。

## 本地测试与编译验证结果

修复后运行：

- `python tests\run_public_tests.py project2_task` → **全部通过**（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway）。
- `python tools\run_debug_probe.py project2_task` → **all visible diagnostic checks passed**（6 项失败全部修复，voice 路径 Warning 消除）。
- 额外验证（临时库，不污染真实数据）：
  - 旧 SQLite care_events 表（缺 `severity/source/created_by/ts`）经 `init_management_db` 迁移后列齐全、旧行保留、大小写不敏感查询命中。
  - 管理员密码在 DB 中为 64 字符 hex 摘要（非明文），salt 为 32 字符 hex；正确密码登录成功，错误密码被拒，伪造 token 不解析，有效 token 解析成功，`admin_account_exists` 在建账号后返回 True。
- `python tools\run_espidf_build.py project2_task` 编译结果：见下方“ESP-IDF 编译记录”。

### ESP-IDF 编译记录

- 命令：`python tools/run_espidf_build.py project2_task`（Windows EIM ESP-IDF v6.0.1，无 Docker/WSL）。
- 首次配置阶段两次失败已修复：
  1. `Failed to resolve component 'mqtt'` — IDF v6 已将 mqtt 移出核心，已在 `main/idf_component.yml` 添加 `espressif/mqtt: "^1.0.0"` managed 依赖。
  2. `espressif/mqtt ^0.1.0` 版本不匹配 — 改为 `^1.0.0`（实际 v1.0.0）。
  3. `mqtt_payload.cpp` 编译错误 `invalid conversion from 'int' to 'esp_mqtt_event_id_t'` — `esp_mqtt_client_register_event` 第二参数由 `ESP_EVENT_ANY_ID` 改为 `MQTT_EVENT_ANY`，并移除未使用的 `event` 变量。
- 修复后**编译成功**：`[espidf] Build finished successfully.`，输出 `build/stdpro.bin`（0xedd50 ≈ 972KB，1MB app 分区剩余 7%）。
- 编译范围：Wi-Fi STA（esp_wifi/wpa_supplicant）、MQTT client（espressif/mqtt v1.0.0）、mbedtls base64、TinyUSB CDC、MLX90640 组件，以及新增的 `protocol_packet / maixsense_parser / device_config / mqtt_payload` 四个模块全部通过。
- 未做（按契约不在本地编译验证范围）：`idf.py flash` / `idf.py monitor` / 真实 USB 枚举 / 真实 Wi-Fi/MQTT 连通 / ToF 上电时序 / MLX90640 实机读数。

## 未验证的残留技术债与风险

- ESP-IDF 编译为 Windows EIM 本地编译，**未做** `idf.py flash` / `idf.py monitor` / 真实 USB 枚举 / 真实 Wi-Fi/MQTT 连通 / ToF 上电时序 / MLX90640 实机读数。巴法云 MQTT 用户名/密码模型按社区契约（username=UID, password 空）实现，未在真实巴法云账号上联调。
- 大 ToF payload（~10KB）的 base64 编码用 malloc 临时缓冲，单次发布 ~13.4KB JSON；ESP32-S3 PSRAM 充足，但若未来切到无 PSRAM 型号需复查堆压力。MQTT QoS=0，与 gateway 巴法云 TCP 订阅语义一致（不保证送达）。
- voice `fetch_current_session` 每次 context 查询多一次 HTTP 往返；若 gateway 未启动或无 recognized session，voice 会收到 denial 并提示，属预期行为。
- care_events 旧表迁移只补列，不把已存在的旧小写 `room/bed` 数据规范化为大写（查询已用 `COLLATE NOCASE` 兜底，不影响检索）；如需统一存储形态可后续加一次性 `UPDATE` 规范化。
- 测试均使用临时 SQLite（`PROJECT2_DB_FILE` 指向 temp 目录），未触碰 `data/project2.db`。
- `run_debug_probe.py` 明确声明不替代 CI/Review，隐藏测试可能覆盖更严格的安全/迁移场景。
