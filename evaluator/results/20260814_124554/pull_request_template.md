# Pull Request 提测说明 (Pull Request Template)

> 本文件记录 Project2（本地护理/睡眠联调工程）本次 Sprint 的最终实现、测试与风险，供合并流水线与 Reviewer 做一致性交叉校验。

## 初始自检诊断（修改前）

修改前运行：

```text
python tests\run_public_tests.py project2_task   -> all public tests passed（浅层冒烟，未覆盖安全/权限/迁移）
python tools\run_debug_probe.py project2_task     -> 6 项失败
```

`run_debug_probe.py` 初始失败清单：

1. `management API rejects missing cookie` — `GET /api/v3/subjects` 无 Cookie 仍返回 200（本机请求被 `_authorized_for_api` 全量放行）。
2. `management API rejects forged cookie` — 伪造 Cookie 仍返回 200（`get_admin_http_session` 忽略 token、直接取任意活跃会话）。
3. `unknown identity session is denied` — `session_is_authenticated` 对 `identity_state=unknown` 直接放行。
4. `expired session is denied` — 过期 session 未校验 `expires_ts`。
5. `care_event write rejects missing admin cookie` — `/api/v3/care/events` 路由未实现（404）。
6. `care_event normalizes room/bed for create and query` — 大小写不规范化、查询不到。
7. 另有 voice 路径 Warning：本地助手仍依赖静默 ambient session 取上下文。

## 修改的文件列表

Gateway（Python）：

- `gateway/auth.py` — 密码改为强制 PBKDF2-HMAC-SHA256 加盐哈希（不再明文）；`admin_account_exists` 改为查库；`get_admin_http_session` 改为按 `token_hash` 精确校验并检查过期与账号状态。
- `gateway/gateway.py` — 收紧鉴权：`_authorized_for_api` 仅允许「管理员会话」或「本机 + 明确列出的服务接口」；`session_is_authenticated` 要求 `recognized + assurance 非 none + 未过期 + 有 actor_subject_id`；`actor_can_access_target` 对空 actor 一律拒绝；`build_chat_context_v3` 未授权时清空 `memory/care_events`，授权后注入 `modalities.care_events`；新增 `POST/GET /api/v3/care/events` 路由。
- `gateway/db.py` — `care_events` 补齐 `severity/source/created_by/ts` 列；新增 `_migrate_care_events` 对旧表 `ALTER TABLE ADD COLUMN` 补列并回填默认值、`ts=created_ts`、`UPPER(room/bed)`，保留旧数据。
- `gateway/care_events.py` — 完整实现 create/list/get 与 `build_care_events_context`，room/bed 统一大写规范化，按 `ts/created_ts` 倒序、支持 `limit`。
- `gateway/sleep_importer.py` — 修复 `first` 策略误写为末床（`beds[-1]`→`beds[0]`）；`row_targets` 统一规范化 room/bed；显式归属行与无归属行按行处理，互不影响；修正 skip 场景重复读取的 mtime 更新。

Voice：

- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session_id()`，从 `/api/v3/session/current` 显式获取当前会话，并随 `/api/v3/context/chat` 携带 `session_id`，不再静默依赖 ambient session。

ESP32-S3（esp32/testpro4）：

- `main/main.cpp` — 重写为模块 glue：Wi-Fi+MQTT 初始化、ToF/MLX 发送路径并行 MQTT 发布、任务与硬件初始化。
- `main/protocol_packet.{h,cpp}` — 新增：包头常量、`crc16_ccitt`、包头/CRC 构造。
- `main/maixsense_parser.{h,cpp}` — 新增：MaixSense 帧解析器（噪声/分块/坏尾/异常长度/半帧）。
- `main/device_config.{h,cpp}` — 新增：NVS 读写、`device_config_network_ready` 完整性校验、`device_config_build_topic` 小写拼接。
- `main/mqtt_payload.{h,cpp}` — 新增：Wi-Fi STA + 巴法云 MQTT 客户端、`payload_b64` JSON 构造、topic 选择。
- `main/CMakeLists.txt` — 新增源文件并补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖。
- `main/idf_component.yml` — 新增 `espressif/mqtt: ^1.0.0` 依赖。

文档：

- `project2_task/README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md` — 同步 care_event 与 ESP32 Wi-Fi+MQTT 已恢复的说明。
- `project2_task/PULL_REQUEST_TEMPLATE.md`（本文件）— 最终提测说明。

## 架构调整与模块设计

- 保持既有模块边界：认证在 `auth.py`，schema/迁移在 `db.py`，人员/绑定/会话在 `subjects.py`，护理事件 CRUD 独立到 `care_events.py`，睡眠导入在 `sleep_importer.py`，`gateway.py` 只做路由 glue。
- 新增 `care_event` 贯穿 DB（`care_events` 表 + 迁移）、API（`POST/GET /api/v3/care/events`）、授权上下文（`modalities.care_events`）与文档。
- ESP32 固件按推荐工程整理拆分为 `protocol_packet / maixsense_parser / device_config / mqtt_payload` 四个模块，`main.cpp` 仅保留 ESP-IDF 初始化、任务创建与硬件调用 glue。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256，16 字节随机盐，20 万次迭代，绝不存明文。
- Cookie 会话：只保存随机 token（`secrets.token_urlsafe`），数据库只存 `sha256(token)`；校验按 `token_hash` 精确匹配 + 过期 + 账号 active，伪造 Cookie 无效。
- 管理 API（`/api/v3/subjects|assignments|sessions|memories|credentials|care/events` 等）远程未登录一律 401。
- 本机 worker 例外仅限明确列出的服务接口：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`。
- `face/credential` 模板导出仍仅限本机（远程即便管理员也不导出）。
- v3 上下文：session 必须 `recognized` + 非 none 的 `assurance_level` + 未过期 + 有 `actor_subject_id`；actor 为空或角色不允许时，`target.patient/assignment` 与 `memory/care_events` 等患者明细一律置空，`modalities.care_events` 仅在授权通过时返回。
- 患者数据零泄漏：未授权时 `modalities.sleep/vitals/posture/memory/care_events` 为空，`target.patient={}`。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行带 `room/bed`：只写入对应床位（大小写匹配到配置床位则用规范化后的配置床位）。
- 行不带 `room/bed`（按行判断，不是整文件一刀切）：
  - 设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED`：写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`：写入第一个配置床位（修复了此前误写末床的问题）。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip`：跳过。
  - `all`：仅显式调试模式，不作为默认。
- 同一 CSV 内显式归属行与无归属行可混合，策略只作用于无归属行，不影响显式行。

## care_event 实现细节

- 表结构：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`。
- 迁移：对旧表（缺 `severity/source/created_by/ts`）用 `PRAGMA table_info` 检测缺失列并 `ALTER TABLE ADD COLUMN`，旧行回填 `severity=info`、`source=manual`、`ts=created_ts`、`room/bed` 大写规范化，旧数据不丢。
- 路由：`POST /api/v3/care/events`（需管理员）；`GET /api/v3/care/events?subject_id=...` 或 `?room=...&bed=...`（需管理员），支持 `limit`，按 `ts/created_ts` 倒序。
- room/bed 统一大写规范化，小写 `r1203/b1` 可被大写 `R1203/B1` 查询命中。
- 授权上下文：授权通过时在 `modalities.care_events` 返回最近事件摘要；未授权不返回。

## ESP32-S3 固件接口对齐说明

- **Wi-Fi + MQTT**：从 NVS 读 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed`，`device_config_network_ready` 要求 `ssid + uid + room + bed` 齐全才联网；Wi-Fi STA + MQTT 客户端连接巴法云 `bemfa.com:9501`，client_id 为巴法云 UID。
- **topic**：`device_config_build_topic` 将 room/bed 转小写拼接，得到 `{room}{bed}tof1/tof2/mlx1/mlx2`（如 `r1203b1tof1`）。
- **MQTT JSON**：`{"payload_b64":"<base64 原始 payload>"}`；base64 内容是传感器原始 payload（ToF 完整 MaixSense 帧、MLX 3072B float32），不是完整 USB packet；用堆分配足够缓冲，避免小固定缓冲越界。
- **并行回传**：`usb_send_tof_payload()` 与 MLX 发送路径在保留 USB CDC 的同时调用 `network_backhaul_publish` 发布对应 topic。
- **USB packet 契约保持不变**：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 只覆盖 payload，LEN/CRC 小端序。
- **ToF payload 保持不变**：完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`。
- **依赖**：`main/CMakeLists.txt` 补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`；`idf_component.yml` 新增 `espressif/mqtt: ^1.0.0`。

## 本地测试与编译验证结果

修复后运行：

```text
python tests\run_public_tests.py project2_task   -> all public tests passed
python tools\run_debug_probe.py project2_task     -> all visible diagnostic checks passed（8/8 ok）
```

关键诊断结果：管理 API 拒绝缺失/伪造 Cookie、接受有效 Cookie；unknown 身份与过期 session 均被拒绝；care_event 未授权写入返回 401、room/bed 大小写规范化查询通过；voice 路径已改为显式携带会话。

额外手工验证：

- 旧版 `care_events` 表迁移：旧行保留、新列补齐、`room/bed` 大写规范化、`ts` 回填。
- 睡眠 CSV 混合显式/无归属行：显式行写入其床位，无归属行按 `first` 写入首床。

ESP-IDF 编译：

```text
python tools\run_espidf_build.py project2_task
  -> [espidf] Build finished successfully.
  -> output_bin = ...\esp32\testpro4\build\stdpro.bin
```

编译过程说明：首次因 `espressif/mqtt` 版本约束写错（`>=1.2.0,<2.0.0` 无匹配版本）失败，改为官方示例同款 `^1.0.0` 后解析成功；随后修复 `esp_mqtt_client_register_event` 的事件 ID 参数（`MQTT_EVENT_ANY`）与 FreeRTOS 头文件缺失，最终编译通过。仅保留 `missing-field-initializers` 等无害告警。

## ESP 编译/失败情况

- 结果：**编译成功**（`stdpro.bin` 已生成），目标 `esp32s3`，使用 Windows EIM 安装的 ESP-IDF v6.0.1。
- 失败点与修复：`espressif/mqtt` 版本约束 → `^1.0.0`；`ESP_EVENT_ANY_ID` → `MQTT_EVENT_ANY`；`device_config.cpp` 缺 FreeRTOS 头文件。均已修复并复编译通过。

## 未验证的残留技术债与风险

- ESP32 固件为 Windows ESP-IDF 编译验证，未做 `idf.py flash`、`idf.py monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序或 MLX90640 实机读数。
- 巴法云 UID/真实 topic 未在实机联调，MQTT 大 payload（ToF ~13KB base64）在真实网络的吞吐与断线恢复未实测。
- `get_current_session()` 仍按「最近未过期 session」选取当前会话；操作者更替（护士离开、他人上前）时的会话切换/失效依赖视觉 worker 持续上报，属于产品级残留风险，本次未引入强制会话确认。
- 人脸向量比对阈值、OpenCV/ONNXRuntime 在 RK3588 ARM64 上的可用性未在本环境复验。
- `care_event` 未加 subject 存在性外键约束，与既有 `subjects` 表保持宽松引用（历史表结构兼容优先）。
