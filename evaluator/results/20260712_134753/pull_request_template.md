# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行 `run_debug_probe.py` 结果（6 项失败）：

```
[probe:FAIL] management API rejects missing cookie status=200
[probe:FAIL] management API rejects forged cookie status=200
[probe:ok] management API accepts valid cookie
[probe:FAIL] unknown identity session is denied policy={'allowed': True}
[probe:FAIL] expired session is denied policy={'allowed': True}
[probe:FAIL] care_event write rejects missing admin cookie status=404
[probe:FAIL] care_event normalizes room/bed for create and query rows=[]
[probe:Warning] Voice/assistant path: sensitive context may be denied without session_id
[probe] failures=6
```

`run_public_tests.py` 初始运行：全部通过（4 个测试文件），但仅覆盖编译和基本冒烟，不检查安全边界。

## 修改的文件列表

### Gateway (Python)
- `gateway/auth.py` — 修复管理员密码哈希、账号存在检查、会话 token 验证
- `gateway/gateway.py` — 修复管理 API 鉴权绕过、session 认证逻辑、care_event 路由、context 集成
- `gateway/care_events.py` — 完善字段、room/bed 规范化、context builder
- `gateway/db.py` — care_events 表 schema 更新 + 旧表迁移
- `gateway/sleep_importer.py` — 修复 `first` 策略 `beds[-1]` → `beds[0]` bug

### Voice
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session_id()`，收紧后自动获取当前会话

### ESP32-S3 固件
- `esp32/testpro4/main/main.cpp` — 集成网络回传、重构 packet builder、移除 TODO
- `esp32/testpro4/main/network_backhaul.h` — 新增：网络回传接口定义
- `esp32/testpro4/main/network_backhaul.cpp` — 新增：Wi-Fi STA + 巴法云 MQTT 实现
- `esp32/testpro4/main/protocol_packet.h` — 新增：USB packet 常量、CRC16-CCITT、打包辅助
- `esp32/testpro4/main/maixsense_parser.h` — 新增：MaixSense 帧解析器（独立模块）
- `esp32/testpro4/main/device_config.h` — 新增：room/bed 规范化、topic 拼接、配置完整性检查
- `esp32/testpro4/main/mqtt_payload.h` — 新增：`payload_b64` JSON 构造（大缓冲）
- `esp32/testpro4/main/CMakeLists.txt` — 补齐 esp_wifi/esp_netif/esp_event/mqtt/mbedtls 依赖
- `esp32/testpro4/main/idf_component.yml` — 添加 `espressif/mqtt` 依赖
- `esp32/testpro4/sdkconfig.defaults` — 添加 `CONFIG_ESP_WIFI_ENABLED=y`

## 架构调整与模块设计

保持既有模块边界，未将逻辑塞回 `gateway.py`：

- **auth.py**：管理员账号 CRUD、密码加盐哈希（PBKDF2-SHA256, 200k iterations）、Cookie 会话 token 验证
- **care_events.py**：care_event CRUD + context builder，独立于 `subjects.py`
- **db.py**：SQLite schema 和迁移逻辑，`care_events` 旧表 ALTER TABLE 补列
- **sleep_importer.py**：CSV 导入归属策略，按行处理
- **gateway.py**：仅路由 glue 和 context 聚合调用
- **ESP32**：协议逻辑拆到 `protocol_packet.h`、`maixsense_parser.h`、`device_config.h`、`mqtt_payload.h`，网络回传独立到 `network_backhaul.cpp`

## 安全边界及鉴权设计

### 管理员密码
- 密码使用 PBKDF2-HMAC-SHA256 加盐哈希（16 字节随机 salt，200,000 次迭代）
- 数据库只存 `salt` + `password_hash`，不存明文
- 登录验证使用 `hmac.compare_digest` 防止时序攻击

### Cookie 会话
- Cookie 只存随机 token（`secrets.token_urlsafe(32)`）
- 数据库存 token 的 SHA-256 hash，不存明文 token
- `get_admin_http_session(token)` 严格按 `token_hash` 查询，不再"抓取任意活跃会话"
- Cookie 设置 `HttpOnly; SameSite=Lax`，Max-Age 跟随 TTL

### 管理 API 鉴权
- `_authorized_for_api(path)` 现在区分：
  - 管理路径（`/api/v3/*` 非 local-service）：必须有效 admin cookie
  - 本机服务路径（`/api/v2/*`、`/api/esp/*`、`context/chat`、`identity/gallery`、`identity/match`、`vision/observation`）：本机请求免认证
- 远程未登录请求被拒绝（401），伪造 cookie 被拒绝（401）
- `admin_account_exists()` 现在查询 DB 而非永远返回 False

### v3 授权上下文
- `session_is_authenticated()` 修复：
  - `identity_state=unknown` 或空 → 拒绝（不再放行）
  - `assurance_level=none` 或空 → 拒绝
  - `expires_ts` 已过期 → 拒绝
- `actor_can_access_target()` 修复：
  - 无 actor subject → 拒绝（不再隐式放行 worker 调用）
  - admin/staff → 允许任意目标
  - patient → 仅允许查看自己
- 未授权时 `target.patient`、`target.assignment`、所有 `modalities` 返回空对象，零患者数据泄漏

### Voice 助手会话
- 收紧后 voice 路径新增 `fetch_current_session_id()`：调用 `/api/v3/session/current` 获取当前会话 ID
- `fetch_gateway_chat_context()` 在无 `VOICE_SESSION_ID` 时自动获取当前 session_id 再请求 context
- 不再依赖静默 ambient session 漏数据

## 睡眠 CSV 无 room/bed 时的特殊处理

按行策略（非整文件一刀切）：

- 行带 `room/bed`：匹配配置床位（大小写不敏感），写入对应床位
- 行不带 `room/bed`：
  - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 非空 → 写入指定床位
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位（**修复了原 `beds[-1]` bug**）
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 写入所有床位（仅调试用）
- 同一 CSV 内显式 `room/bed` 行和无归属行混合时，策略只作用于无归属行，显式行不受影响

## care_event 实现细节

### DB Schema
`care_events` 表完整字段：`event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts`

### 迁移
- 旧表可能只有 `event_id/subject_id/room/bed/kind/title/content/created_ts/updated_ts`
- `init_management_db()` 和 `care_events.init_care_events_table()` 使用 `PRAGMA table_info` 检测缺失列，`ALTER TABLE ADD COLUMN` 补齐 `severity/source/created_by/ts`
- 旧数据 `ts` 列从 `created_ts` 回填，不丢失旧行

### API 路由
- `POST /api/v3/care/events` — 需要管理员登录，创建护理事件
- `GET /api/v3/care/events?subject_id=...` — 按患者查询
- `GET /api/v3/care/events?room=...&bed=...` — 按床位查询
- `GET` 支持 `limit`（默认 20，上限 200），按 `ts/created_ts` 倒序

### room/bed 规范化
- 写入时 `normalize_room()` → 大写、`normalize_bed()` → 大写
- 查询时同样规范化，`r1203/b1` 写入后可用 `R1203/B1` 查到

### Context 集成
- `build_care_events_context(subject_id, limit)` 返回最近事件摘要
- `build_chat_context_v3()` 在 `allowed=True` 时将 `care_events` 注入 `modalities.care_events`
- `allowed_sections` 包含 `"care_events"`
- 未授权时不返回 care_events 内容

## ESP32-S3 固件接口对齐说明

### Wi-Fi + MQTT 巴法云回传
- `network_backhaul.cpp` 实现 Wi-Fi STA 初始化（`esp_wifi`）+ MQTT 客户端连接（`espressif/mqtt`）
- MQTT broker URI：`mqtt://{bemfa_host}:{bemfa_mqtt_port}`（默认 `bemfa.com:9501`）
- Wi-Fi 断连自动重连，MQTT 断连自动重连
- Wi-Fi 和 USB CDC 并行回传，互不阻塞

### NVS 配置
- 从 NVS 读取并校验 `wifi_ssid/wifi_password/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`
- `config_has_network()` 检查 `ssid + uid + room + bed` 全部非空才启动网络回传
- 网络配置不完整时降级为 USB-only 模式，不影响本地采集

### Topic 规范化
- `device_config.h` 的 `normalize_room_lower()` 将 room/bed 转小写
- `build_sensor_topic()` 拼接 `{room_lower}{bed_lower}{stream}`，如 `r1203b1tof1`
- 四个 topic：`{room}{bed}tof1`、`{room}{bed}tof2`、`{room}{bed}mlx1`、`{room}{bed}mlx2`

### Base64 Payload
- `mqtt_payload.h` 的 `build_payload_b64_json()` 构造 `{"payload_b64":"..."}`
- base64 内容是传感器原始 payload（MaixSense 完整帧或 MLX float32 数组），**不是**完整 USB packet
- 缓冲区 16384 字节，可容纳 ToF ~10000B → base64 ~13333 chars

### USB Packet 契约
- `protocol_packet.h` 保持 `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`
- CRC16-CCITT（初始值 0xFFFF，多项式 0x1021），只覆盖 payload
- `LEN` 和 CRC 小端序
- ToF payload 保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`

### 依赖补齐
- `main/CMakeLists.txt` REQUIRES 添加 `esp_wifi`、`esp_netif`、`esp_event`、`mqtt`、`mbedtls`
- `main/idf_component.yml` 添加 `espressif/mqtt: "*"`（ESP-IDF v6.0 MQTT 外部组件）
- `sdkconfig.defaults` 添加 `CONFIG_ESP_WIFI_ENABLED=y`

### 模块拆分
- `protocol_packet.h`：packet 常量、CRC、打包辅助
- `maixsense_parser.h`：MaixSense 帧解析器（处理噪声、分块、坏尾、半帧）
- `device_config.h`：NVS key、room/bed 规范化、topic 拼接
- `mqtt_payload.h`：base64 JSON 构造
- `network_backhaul.h/cpp`：Wi-Fi + MQTT 初始化、连接管理、sensor payload 发布
- `main.cpp`：保留 ESP-IDF 初始化、任务创建、硬件调用和模块 glue

## 本地测试与编译验证结果

### Python 测试（修复后）
```
python tests\run_public_tests.py project2_task
→ [public] all public tests passed (4 个文件全部 OK)
```

### Debug Probe（修复后）
```
python tools\run_debug_probe.py project2_task
→ [probe:ok] admin setup returns 200
→ [probe:ok] management API rejects missing cookie
→ [probe:ok] management API rejects forged cookie
→ [probe:ok] management API accepts valid cookie
→ [probe:ok] unknown identity session is denied
→ [probe:ok] expired session is denied
→ [probe:ok] care_event write rejects missing admin cookie
→ [probe:ok] care_event normalizes room/bed for create and query
→ [probe:info] voice module appears to reference current-session fetch
→ [probe] all visible diagnostic checks passed (failures=0)
```

### ESP-IDF 编译
```
python tools\run_espidf_build.py project2_task
→ [espidf] Build finished successfully.
→ output_bin = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
→ stdpro.bin binary size 0xee100 bytes. 0x11f00 bytes (7%) free.
```

编译环境：Windows EIM ESP-IDF v6.0.1，target `esp32s3`，无 Docker/WSL。
编译过程有一次中间修复：`ESP_EVENT_ANY_ID` 类型转换（`int` → `esp_mqtt_event_id_t`），修复后增量编译成功。

## 未验证的残留技术债与风险

1. **真实 Wi-Fi/MQTT 连通性**：编译通过但未在真实 ESP32-S3 硬件上验证 Wi-Fi 连接、巴法云 MQTT 握手和实际数据回传。

2. **巴法云 MQTT 认证细节**：巴法云 MQTT 协议的具体认证方式（client_id/username 使用 UID）基于公开文档推断，未对照真实 broker 验证。如果巴法云要求不同的认证字段组合，可能需要调整 `mqtt_cfg.credentials` 配置。

3. **MQTT 大 payload 分片**：ToF 帧约 10000 字节，base64 后约 13333 字节。`esp_mqtt_client_publish` 默认 outbox 可能对大消息有限制，实机可能需要调整 MQTT buffer 配置或分片发送。

4. **旧 SQLite 迁移实测**：迁移逻辑基于 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`，已在代码层面覆盖 `care_events` 缺列场景，但未用真实 `data/legacy_sample.db` 实测（测试均用临时库）。

5. **voice 助手在板端的完整链路**：`fetch_current_session_id()` 已添加，但依赖 `/api/v3/session/current` 在本机可用。如果 gateway 未启动或 session 表为空，voice 将无法获取授权上下文（这是预期行为，但需确认板端部署时 gateway 先于 voice 启动）。

6. **I2C 旧驱动弃用警告**：MLX90640 组件使用 `driver/i2c.h`（ESP-IDF v6.0 标记 EOL），编译有 pragma 警告，不影响编译通过，但 v7.0 将移除。后续需迁移到 `driver/i2c_master.h`。

7. **`config_has_network()` 和 USB-only 降级**：NVS 中无 Wi-Fi 配置时固件降级为 USB-only，这是预期行为，但部署文档需明确说明 `CFGSET ssid/password/uid` 后需要 `REBOOT` 才会启动网络回传。
