# Pull Request 提测说明 — Project2 护理/睡眠 Gateway Sprint

## 初始自检诊断

修改前运行结果：

`python tests\run_public_tests.py project2_task` → all public tests passed

`python tools\run_debug_probe.py project2_task` → failures=6:

- management API rejects missing cookie (status=200, 应 401)
- management API rejects forged cookie (status=200, 应 401)
- unknown identity session is denied (allowed=True, 应 False)
- expired session is denied (allowed=True, 应 False)
- care_event write rejects missing admin cookie (status=404, 路由不存在)
- care_event normalizes room/bed for create and query (rows=[], 大小写不匹配)

## 修改的文件列表

### Gateway (Python)

| 文件 | 修改内容 |
|------|----------|
| `gateway/auth.py` | 修复 `admin_account_exists()` 始终返回 False；修复 `_password_hash()` 无盐时返回明文；修复 `get_admin_http_session()` 不校验 token hash |
| `gateway/gateway.py` | 收紧 `_authorized_for_api()` 仅对本地服务接口放行；修复 `session_is_authenticated()` 对 unknown/expired/无 actor 的判定；新增 care_event GET/POST 路由；context 增加 `modalities.care_events` |
| `gateway/db.py` | care_events 表新增 severity/source/created_by/ts 列；增加 `_migrate_care_events()` 迁移旧表 |
| `gateway/care_events.py` | 完整重写：CRUD 含 room/bed 规范化、limit、ts 排序；实现 `build_care_events_context()` |
| `gateway/sleep_importer.py` | 修复 `first` 策略错误返回 `beds[-1]`（最后一个）改为 `beds[0]`（第一个） |

### ESP32-S3 固件 (C/C++)

| 文件 | 修改内容 |
|------|----------|
| `esp32/testpro4/main/protocol_packet.h/.cpp` | 新增：USB packet 常量、CRC16-CCITT 独立模块 |
| `esp32/testpro4/main/maixsense_parser.h/.cpp` | 新增：MaixSense 帧解析器模块（处理噪声、分块、坏尾、异常长度） |
| `esp32/testpro4/main/device_config.h/.cpp` | 新增：NVS 配置读写、room/bed 完整性校验、topic 规范化（小写拼接） |
| `esp32/testpro4/main/mqtt_payload.h/.cpp` | 新增：`{"payload_b64":"..."}` JSON 构造，mbedtls base64 编码 |
| `esp32/testpro4/main/wifi_mqtt.h/.cpp` | 新增：Wi-Fi STA 初始化 + MQTT client 连接巴法云，publish 接口 |
| `esp32/testpro4/main/main.cpp` | 重构：引用模块化头文件，移除内联重复代码；ToF/MLX 发送路径增加 MQTT mirror；app_main 增加 Wi-Fi/MQTT 启动 |
| `esp32/testpro4/main/CMakeLists.txt` | 新增源文件和 esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls 依赖 |
| `esp32/testpro4/main/idf_component.yml` | 新增 espressif/mqtt 组件依赖 |

## 架构调整与模块设计

保持已有模块边界：

- `auth.py` 只负责管理员账号、密码哈希、HTTP Cookie 会话。
- `db.py` 只负责 schema 和迁移。
- `care_events.py` 独立放护理事件 CRUD，不扩大 subjects.py。
- `gateway.py` 只放路由 glue，不含业务逻辑。
- `sleep_importer.py` 独立处理 CSV 导入策略。
- ESP32 固件按职责拆分为 protocol_packet / maixsense_parser / device_config / mqtt_payload / wifi_mqtt 五个模块，main.cpp 只做初始化和任务 glue。

## 安全边界及鉴权设计

- 管理员密码使用 PBKDF2-HMAC-SHA256 + 随机 16 字节盐，200000 轮迭代，绝不存明文。
- Cookie 只保存随机 token（`secrets.token_urlsafe(32)`），数据库存 SHA-256(token) 哈希。
- `get_admin_http_session()` 严格按 token_hash 匹配，不再"取任意活跃 session"。
- 管理 API（subjects/assignments/sessions/credentials/memories/care_events）即使本机也必须带有效 Cookie。
- 仅 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation` 允许本机无 Cookie 访问（worker 服务接口）。
- `session_is_authenticated()` 严格拒绝：identity_state=unknown、assurance_level=none/空、expires_ts 过期、缺少 actor_subject_id。
- 未授权时 context 返回空 modalities，不泄漏患者数据。
- 远程未登录用户不能访问 face template / credential template。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行策略处理（不是整文件一刀切）：

- 行带 room/bed：只写入对应床位（大小写不敏感匹配已配置床位）。
- 行不带 room/bed：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 时，写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` 时，写入第一个配置床位（修复了原来错误写入最后一个的 bug）。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` 时跳过。
  - `all` 只作为显式调试模式。
- 同一 CSV 内显式行与无归属行共存时，策略只作用于无归属行，不误改或整表丢弃显式行。

## care_event 实现细节

- DB：`care_events` 表含 event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts。
- 迁移：`_migrate_care_events()` 用 `PRAGMA table_info` 检测缺失列，`ALTER TABLE ADD COLUMN` 补齐，旧行 ts 从 created_ts 回填，旧数据不丢失。
- API：`POST /api/v3/care/events`（需管理员 Cookie）、`GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=...`。
- room/bed 写入和查询均经过 `normalize_room/normalize_bed`（uppercase），保证 `r1203/b1` 写入后 `R1203/B1` 可查到。
- 查询按 ts DESC（ts=0 时 fallback 到 created_ts DESC），支持 limit 参数，默认 20 条。
- Context：授权通过后 `modalities.care_events` 返回最近 5 条事件摘要；未授权时返回空对象。

## ESP32-S3 固件接口对齐说明

### Wi-Fi + MQTT

- `wifi_mqtt.cpp`：Wi-Fi STA 初始化（esp_wifi）、事件驱动重连（最多 5 次）、MQTT client 连接巴法云（`mqtt://{host}:{port}`，client_id=uid）。
- 配置不完整时（缺 ssid/uid/room/bed）仅运行 USB CDC，不阻塞启动。

### Topic 规范化

- `device_config_build_topic()`：`{room}{bed}{stream}` 全部小写拼接，如 `r1203b1tof1`。

### MQTT Payload

- `mqtt_payload.cpp`：使用 mbedtls base64 编码原始 payload，构造 `{"payload_b64":"..."}`。
- 静态 14KB 缓冲区避免堆碎片（完整 ToF 帧 ~10022B → base64 ~13366 字符）。
- base64 内容是传感器原始 payload（完整 MaixSense 帧或 MLX float 数组），不是完整 USB packet。

### USB Packet 契约

- `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`
- CRC16-CCITT（init 0xFFFF, poly 0x1021）只覆盖 payload，LEN 和 CRC 小端序。
- ToF payload 保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`。

### NVS 配置

- 支持 CFGSET ssid/password/uid/host/port/room/bed/device_id。
- `device_config_network_ready()` 检查 ssid+uid+room+bed 全部非空才启动网络。

## 本地测试与编译验证结果

### 修复后最终验证

```
$ python tests\run_public_tests.py project2_task
[public] all public tests passed

$ python tools\run_debug_probe.py project2_task
[probe:ok] admin setup returns 200
[probe:ok] management API rejects missing cookie
[probe:ok] management API rejects forged cookie
[probe:ok] management API accepts valid cookie
[probe:ok] unknown identity session is denied
[probe:ok] expired session is denied
[probe:ok] care_event write rejects missing admin cookie
[probe:ok] care_event normalizes room/bed for create and query
[probe] all visible diagnostic checks passed
```

### ESP-IDF 编译

```
$ python tools\run_espidf_build.py project2_task
[espidf] target = esp32s3
[espidf] Build finished successfully.
stdpro.bin binary size 0xf00c0 bytes. Smallest app partition is 0x100000 bytes. 0xff40 bytes (6%) free.
```

编译环境：Windows EIM 安装的 ESP-IDF v6.0.1，xtensa-esp32s3-elf-g++ 15.2.0，目标 esp32s3。编译通过，生成 stdpro.bin。未执行 flash/monitor/实机测试（本任务不要求）。

## 未验证的残留技术债与风险

- **未实机验证**：Wi-Fi/MQTT 连通性、真实 USB 枚举、ToF 上电时序、MLX90640 I2C 读数准确性均未在硬件上验证（本任务不要求）。
- **Voice 助手 Warning**：probe 打印 informational warning 提示收紧权限后助手若依赖 ambient session 可能取不到敏感上下文。当前 voice_assistant_integrated.py 已正确处理 `allowed=false`（调用 `gateway_denied_reply()`），且 v2 `/api/v2/voice/chat_context` 仍可无 session 访问基础上下文。若后续需要 v3 敏感数据，助手需先通过 face observation 建立有效 session 再带 session_id 请求。
- **App 分区余量**：stdpro.bin 占 96%，若后续增加功能可能需要调整 partition table。
- **旧 SQLite 迁移**：仅覆盖 care_events 表迁移。其他表 schema 未变动，无需迁移。
- **ESP32 静态缓冲区**：MQTT JSON 使用 14KB 静态缓冲，若同时有多个 publish 并发（当前 ToF 和 MLX 在不同任务），理论上存在竞争。当前 MLX 4Hz + ToF 8Hz 交替发送，实际冲突概率极低，但生产环境建议加 mutex 或队列。
