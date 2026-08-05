# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行的命令和关键结果：

- `python tests\run_public_tests.py project2_task` — 全部通过（基础测试原本通过）
- `python tools\run_debug_probe.py project2_task` — **6 项失败**：
  - `[probe:FAIL] management API rejects missing cookie status=200` — 管理 API 缺 Cookie 时仍返回 200
  - `[probe:FAIL] management API rejects forged cookie status=200` — 伪造 Cookie 仍通过
  - `[probe:FAIL] unknown identity session is denied` — identity_state=unknown 时未被拒绝
  - `[probe:FAIL] expired session is denied` — 过期 session 未被拒绝
  - `[probe:FAIL] care_event write rejects missing admin cookie status=404` — `/api/v3/care/events` 路由不存在
  - `[probe:FAIL] care_event normalizes room/bed for create and query` — 查询不区分大小写

## 修改的文件列表

| 文件 | 说明 |
|------|------|
| `gateway/gateway.py` | 收紧管理 API 鉴权、修复 session 认证逻辑、新增 `/api/v3/care/events` 路由、wire care_events 到 v3 context |
| `gateway/auth.py` | `admin_account_exists` 改为查 DB；`_password_hash` 强制加盐；`get_admin_http_session` 按 token_hash 校验 |
| `gateway/care_events.py` | 完整重写：room/bed 规范化、补齐 severity/source/created_by/ts 字段、旧表迁移、查询按 ts 倒序 |
| `gateway/db.py` | care_events 建表补齐缺失列、初始化时调用 `_migrate_care_events_table` 迁移旧数据 |
| `gateway/sleep_importer.py` | 修复 `SLEEP_IMPORT_UNSCOPED_POLICY=first` 时使用 `beds[0]`（原为 `beds[-1]`） |
| `voice/voice_assistant_integrated.py` | 新增 `fetch_current_session()`，让本地助手显式获取当前 session |
| `esp32/testpro4/main/main.cpp` | 重构：恢复 Wi-Fi+MQTT 巴法云回传、模块 glue |
| `esp32/testpro4/main/protocol_packet.{h,cpp}` | USB 协议常量、CRC16-CCITT、sensor type→stream name |
| `esp32/testpro4/main/device_config.{h,cpp}` | NVS 配置读写、room/bed 规范化、topic 拼接 |
| `esp32/testpro4/main/mqtt_payload.{h,cpp}` | `{"payload_b64":"..."}` JSON 构造，动态缓冲区 |
| `esp32/testpro4/main/mqtt_backhaul.{h,cpp}` | Wi-Fi STA + ESP-IDF MQTT 客户端初始化和发布 |
| `esp32/testpro4/main/CMakeLists.txt` | 补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖 |
| `esp32/testpro4/main/idf_component.yml` | 新增 `espressif/mqtt` 组件依赖 |

## 架构调整与模块设计

遵循 ONBOARDING_TODO.md 与 `reference/architecture_notes.md` 的模块边界要求：

- `gateway.py` 只做路由 glue 与上下文聚合；
- 认证/会话逻辑保留在 `auth.py`（管理员密码、Cookie 会话）；
- 人员/床位/凭据/会话/记忆逻辑在 `subjects.py`；
- care_event CRUD 独立放 `care_events.py`，不扩大 `subjects.py`；
- ESP32 固件拆分为 `protocol_packet`/`device_config`/`mqtt_payload`/`mqtt_backhaul` 四个模块，`main.cpp` 仅保留硬件初始化和任务 glue。

## 安全边界及鉴权设计

1. **管理 API 鉴权收紧**：新增 `_is_management_api()` 区分本地服务路径与管理 API。管理 API（`/api/v3/subjects`、`/api/v3/care/events` 等）**不再接受 localhost 绕过**，必须携带有效的 admin Cookie。本机 worker 服务路径（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat` 等）维持 localhost 可访问。
2. **管理员密码**：创建和登录均使用 PBKDF2-HMAC-SHA256（200k 迭代）+ 16 字节随机盐，数据库只存 `salt` 和 password_hash，无明文。
3. **Cookie 仅存随机 token**：Cookie 值为 `secrets.token_urlsafe(32)`，数据库只存 `sha256(token)`。`get_admin_http_session()` 改为按 `token_hash` 精确匹配，伪造 token 查不到记录。
4. **session 认证收紧**：`session_is_authenticated()` 现在对以下情况返回 `False`：缺少 actor_subject_id、identity_state 未知、assurance_level 为空/none、expires_ts 已过期。
5. **care_event 写入**：`POST /api/v3/care/events` 需要管理员登录。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行带 `room/bed`：仅写入匹配的已配置床位；
- 行不带 `room/bed`：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 时写入指定床位；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` 时写入**第一个配置床位**（已修复为 `beds[0]`）；
  - `=skip` 时跳过；
  - `=all` 仅作为显式调试模式；
- 同一 CSV 内可同时出现显式行与无归属行：策略只作用于无归属行，显式行不会被误改或丢弃。

## care_event 实现细节

- DB schema（`care_events` 表）：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`；
- 旧 SQLite 库迁移：`init_management_db()` 调用 `_migrate_care_events_table()`，用 `PRAGMA table_info` 检查缺失列并 `ALTER TABLE ADD COLUMN`，旧行填充默认值（severity=info、source=manual、created_by=空、ts=created_ts）；
- `create_care_event()`：调用 `normalize_room()`/`normalize_bed()` 确保写入统一为大写；
- `list_care_events()`：查询参数也经过 `normalize_room()`/`normalize_bed()`，按 `created_ts DESC` 排序，支持 `limit`；
- `/api/v3/context/chat` 在 `allowed` 且存在 target_subject_id 时，会聚合最近 care_event 摘要到 `modalities.care_events` 并拼入 `brief`，未授权时不返回。

## ESP32-S3 固件接口对齐说明

按 `reference/espidf_protocol_contract.md` 修复：

- **USB Packet**：保持 `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`，CRC16-CCITT 仅覆盖 payload，LEN 与 CRC 均小端序；
- **ToF Payload**：通过 `usb_send_tof_payload()` 发送的是完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`，没有裁剪为 10000B 图像区。发送时统一 USB 包头 [AA 55 02 ID LEN_L LEN_H] + 完整原始帧 + CRC；
- **MQTT Topic**：`{room}{bed}tof1/tof2/mlx1/mlx2`，全部小写拼接，由 `device_config_get_topic()` 生成；
- **MQTT JSON**：`{"payload_b64":"..."}`，base64 内容是原始 payload（ToF 为完整 MaixSense 帧，MLX 为 3072 字节 float32 温度），不是完整 USB packet；
- **NVS 配置**：`load_device_config()` 读取 `ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`，`config_is_complete()` 校验 room+bed，`network_ready()` 额外校验 wifi_ssid+bemfa_uid；
- **CMake 依赖**：`main/CMakeLists.txt` 已补齐 `esp_wifi`、`esp_netif`、`esp_event`、`lwip`、`mqtt`、`mbedtls`；
- **USB CDC 并行**：`usb_send_tof_payload()` 向 CDC1 发送 USB packet 后，调用 `publish_to_backhaul()` 向 MQTT topic 发布 base64。`mlx_sender_task()` 同理，USB CDC 与 MQTT 互不阻塞。

## 本地测试与编译验证结果

修复后运行：

- `python tests\run_public_tests.py project2_task` — **全部通过**（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway）
- `python tools\run_debug_probe.py project2_task` — **全部通过**：
  - `[probe:ok] admin setup returns 200`
  - `[probe:ok] management API rejects missing cookie`
  - `[probe:ok] management API rejects forged cookie`
  - `[probe:ok] management API accepts valid cookie`
  - `[probe:ok] unknown identity session is denied`
  - `[probe:ok] expired session is denied`
  - `[probe:ok] care_event write rejects missing admin cookie`
  - `[probe:ok] care_event normalizes room/bed for create and query`
  - `[probe:info] voice module appears to reference current-session fetch`
- `python tools\run_espidf_build.py project2_task` — **编译成功**，生成 `stdpro.bin`（app partition 使用 0xf0000 / 0x100000 字节，剩余 6%）。

## 未验证的残留技术债与风险

1. **Wi-Fi/MQTT 实机连通性**：仅做了 Windows ESP-IDF 编译验证，未做 `idf.py flash`、`idf.py monitor`、真实 Wi-Fi 连接、真实巴法云 broker 收发测试；
2. **ToF 传感器实机读数**：未验证自动波特率探测、AT 命令时序、实际 UART 字节流与帧解析；
3. **MLX90640 实机 I2C 温度**：未验证真实 I2C 通信与温度读数准确性；
4. **USB 枚举与 CDC 通信**：未做真实 USB 枚举与 TinyUSB CDC 收发测试；
5. **身份识别 runtime 依赖**：`vision/identity_runtime.py` 依赖 YuNet ONNX 模型 + contrib OpenCV，实际板端推理未联调；
6. **MQTT base64 内存**：`mqtt_payload.cpp` 用 `malloc` 动态分配 base64 buffer，极端堆碎片场景下可能失败——生产环境建议改用栈或静态缓冲；
7. **Wi-Fi 重连策略**：当前 `WIFI_EVENT_STA_DISCONNECTED` 仅立即重连，未做指数退避，实际部署建议增加退避；
8. **TLS**：当前 MQTT broker 连接为明文 `mqtt://`，未启用 TLS——巴法云 UID 明文传输，生产环境应启用 `mqtts://` 并配置证书。
