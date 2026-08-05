# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行的命令和关键结果：

- `python tests\run_public_tests.py project2_task` — **all public tests passed**（编译冒烟、功能冒烟、重构模块可调用、网关导入全部通过）。
- `python tools\run_debug_probe.py project2_task` — **failures=6**，初始问题如下：
  1. `management API rejects missing cookie` 失败：无 Cookie 仍返回 200 和完整 subject 列表。
  2. `management API rejects forged cookie` 失败：伪造/任意 Cookie 也能返回 200。
  3. `unknown identity session is denied` 失败：identity_state=unknown 的 session 仍被允许，policy.allowed=true。
  4. `expired session is denied` 失败：已过期 session 仍被允许，policy.allowed=true。
  5. `care_event write rejects missing admin cookie` 失败：`POST /api/v3/care/events` 返回 404（路由未接入）。
  6. `care_event normalizes room/bed for create and query` 失败：room/bed 小写写入、大写查询不匹配，且 create 返回值缺 `ok` 字段。
  7. Voice 路径 Warning：若助手仍依赖隐式 ambient/current session，收紧鉴权后上下文同步可能失败。

## 修改的文件列表

Gateway / 后端：
- `gateway/auth.py` — 修复密码哈希（无盐也生成 salt+hash）、`admin_account_exists()` 真实查 DB、`get_admin_http_session()` 严格按 token_hash 匹配。
- `gateway/db.py` — `care_events` 表新增 `severity/source/created_by/ts` 列定义；新增 `_migrate_care_events_columns()` 迁移旧表缺列。
- `gateway/gateway.py` — 新增 `_is_management_api()` 区分管理 API 和服务接口；`_authorized_for_api()` 管理 API 仅认 admin cookie、本地服务接口放行本机请求；`session_is_authenticated()` 按 identity_state/assurance_level/actor_subject_id/expires 严格判定；`actor_can_access_target()` 无 actor 即拒绝；`build_chat_context_v3()` 新增 `care_events` modality；新增 `GET/POST /api/v3/care/events` 路由。
- `gateway/care_events.py` — 补全 `severity/source/created_by/ts` 字段；room/bed 规范化；`list_care_events` 支持 `limit`、按 ts/created_ts 倒序；`build_care_events_context()` 接入 v3 context；旧表列迁移；`create_care_event` 返回含 `ok: true`。
- `gateway/sleep_importer.py` — 修复 `first` 策略使用 `beds[0]`（此前错用 `beds[-1]`）。
- `voice/voice_assistant_integrated.py` — 新增 `GATEWAY_SESSION_CURRENT_URL`、`fetch_current_gateway_session()`、`resolve_gateway_session_id()`；`build_gateway_context_params()` 在 `VOICE_SESSION_ID` 为空时先取 gateway 当前 session 再带 session_id 调用上下文，避免依赖隐式 ambient 会话。

ESP32-S3 固件：
- `esp32/testpro4/main/main.cpp` — 重构为使用拆分后的各模块；在 `app_main` 中调用 `network_init()`；ToF/MLX 发送路径均调用 `network_publish_sensor()` 并行 MQTT 回传。
- `esp32/testpro4/main/protocol_packet.h` / `protocol_packet.cpp` — USB packet 常量与 CRC16-CCITT。
- `esp32/testpro4/main/maixsense_parser.h` / `maixsense_parser.c` — MaixSense 帧解析器（独立 C 模块，可处理噪声/半帧/坏尾）。
- `esp32/testpro4/main/device_config.h` / `device_config.c` — NVS 配置读写、room/bed 规范化、topic_prefix 构造、`device_config_ready_for_usb/network()` 状态判定。
- `esp32/testpro4/main/mqtt_payload.h` / `mqtt_payload.c` — `{"payload_b64":"..."}` JSON 构造，使用 mbedtls base64，动态估算缓冲区大小。
- `esp32/testpro4/main/network_bemfa.h` / `network_bemfa.c` — Wi-Fi STA 初始化 + 自动重连、巴法云 MQTT 客户端（uid 作 client_id/username）、`network_publish_sensor()` 按 `{topic_prefix}{mlx|tof}{1|2}` 小写 topic 发布原始 payload 的 base64 JSON。
- `esp32/testpro4/main/CMakeLists.txt` — 新增源文件与 REQUIRES（`esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`）。
- `esp32/testpro4/main/idf_component.yml` — 新增 `espressif/mqtt` 依赖。

## 架构调整与模块设计

遵循既有模块边界，所有新增业务逻辑都放在各自模块里，`gateway.py` 只保留路由 glue：

- `auth.py`：管理员账户、密码、HTTP session token（SHA-256 token_hash 存 DB）。
- `db.py`：SQLite 建表与列迁移，`_migrate_care_events_columns` 用 `PRAGMA table_info` 检查旧表并 `ALTER TABLE ADD COLUMN` 补齐缺失列，保留旧数据。
- `care_events.py`：护理事件 CRUD、规范化、context 摘要，不污染 `subjects.py`。
- `sleep_importer.py`：CSV 导入 + 无归属行策略（按行处理，显式行不受策略影响）。
- `gateway.py`：仅负责 HTTP 路由分发、鉴权判定、context 组装。

ESP 固件同样按职责拆分到 5 个 C/C++ 模块，`main.cpp` 只做初始化和任务 glue。

## 安全边界及鉴权设计

- **管理员密码**：PBKDF2-HMAC-SHA256，200,000 轮，随机 16 字节 salt。DB 只存 salt.hex + digest.hex，不明文。
- **管理员 Cookie**：`secrets.token_urlsafe(32)` 随机 token；DB 存 SHA-256 哈希；Cookie 通过 `HttpOnly; SameSite=Lax` 设置。
- **管理 API 鉴权**：`/api/v3/subjects*`、`/api/v3/assignments*`、`/api/v3/memories`、`/api/v3/credentials`、`/api/v3/care/events`、`/api/v3/sessions` 等管理 API，必须携带有效管理员 session cookie，**无论是否本机请求**。
- **本机服务接口例外**（仅本机 IP 可访问，远程仍需鉴权）：
  - `/api/v2/*`
  - `/api/esp/*`
  - `/api/v3/context/chat`
  - `/api/v3/identity/gallery`
  - `/api/v3/identity/match`
  - `/api/v3/vision/observation`
- **身份 gallery 与 credential template**：对非本机请求拒绝返回模板/face gallery。
- **v3 context 权限裁剪**（`session_is_authenticated` 严格模式）：
  - 缺少 `actor_subject_id` → 未认证
  - `expires_ts` 已过期 → 未认证
  - `identity_state=unknown` 或空 → 未认证
  - `assurance_level=none` 或空 → 未认证
  - 通过认证后，admin/staff 可查看任意目标；patient 只能看自己；其余角色拒绝。
  - 未授权时 `modalities` 里 `sleep/vitals/posture/memory/care_events` 均为空，`target.patient/assignment` 不返回明细，`policy.allowed=false`，`policy.reason` 区分 `not_authenticated` 与 `not_authorized_for_target`。
- **Voice 助手路径**：不再依赖"ambient 当前 session 就给数据"的隐式路径。当 `VOICE_SESSION_ID` 未配置时，voice 先调 `/api/v3/session/current` 拿 session_id，再显式带 `session_id` 请求上下文；若当前 session 未认证，上下文接口返回 denied，voice 回复权限提示。

## 睡眠 CSV 无 room/bed 时的特殊处理

- **按行策略**：每一行独立判断是否带 `room/bed` 字段（大小写不敏感匹配列名：`room/Room/ROOM`、`bed/Bed/BED`）。显式带归属的行按归属写，不受策略影响。无归属行才走以下策略。
- `SLEEP_IMPORT_DEFAULT_ROOM` + `SLEEP_IMPORT_DEFAULT_BED` 都设置时 → 写入指定床位。
- `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入配置中的第一个床位（`beds[0]`）。
- `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过不导入。
- `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 仅调试模式，向所有床位广播；不能作为默认。
- 未识别策略 → 保守不导入，防止误扩散。

同一份 CSV 可同时混合"有归属行"和"无归属行"，策略只作用于后者，不会误改或整表丢弃显式行。

## care_event 实现细节

DB schema（`gateway/db.py` + `care_events.py` 双处均有迁移保护）：
- `event_id TEXT PK`、`subject_id`、`room`、`bed`、`kind`、`title`、`content`、`severity`（默认 `info`）、`source`（默认 `manual`）、`created_by`、`ts`（事件时间，可由调用方设置）、`created_ts`、`updated_ts`。
- 索引：`idx_care_events_subject(subject_id, created_ts DESC)`、`idx_care_events_room_bed(room, bed, created_ts DESC)`。
- 旧表迁移：`_migrate_care_events_columns()` 用 `PRAGMA table_info` 检测缺列并 `ALTER TABLE ADD COLUMN`，保留旧数据。

API：
- `POST /api/v3/care/events` — 需管理员登录。创建护理事件，room/bed 在写入前规范化为大写。
- `GET /api/v3/care/events?subject_id=...` — 按 subject 查询。
- `GET /api/v3/care/events?room=...&bed=...` — 按床位查询，room/bed 规范化后匹配（大小写不敏感）。
- `limit` 参数，默认 20，最大 500。
- 排序：`COALESCE(NULLIF(ts, 0), created_ts) DESC`，即事件时间优先、没有则用创建时间。

Context 聚合：
- `build_chat_context_v3` 在授权通过且有 `target_subject_id` 时，返回 `modalities.care_events`（items + brief），并把摘要加入 `brief` 和 `prompt_hints`。
- 未授权时 `care_events` 为空对象。

## ESP32-S3 固件接口对齐说明

工程拆分：`main/protocol_packet.{h,cpp}`、`maixsense_parser.{h,c}`、`device_config.{h,c}`、`mqtt_payload.{h,c}`、`network_bemfa.{h,c}`。`main.cpp` 仅保留初始化、任务创建与 glue。

NVS 配置（`device_config.c`）：
- namespace: `project2`；key: `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`。
- 控制台命令 `CFG? / CFGSET key=value / CFGRESET / REBOOT`，支持 `ssid/password/uid/host/port/room/bed/device_id` 别名。
- `device_config_ready_for_usb()` 检查 room + bed；`device_config_ready_for_network()` 额外要求 wifi_ssid + bemfa_uid。
- `topic_prefix` 构造：`lower(room) + lower(bed)`，用于拼接 `{topic_prefix}tof1 / tof2 / mlx1 / mlx2`。

Wi-Fi + MQTT（`network_bemfa.c`）：
- Wi-Fi STA 模式，`esp_wifi` + `esp_netif` + `esp_event`，断开自动重连。
- 巴法云 MQTT：`mqtt://{bemfa_host}:{bemfa_mqtt_port}`，client_id 和 username 均为 `bemfa_uid`，keepalive 60s，自动重连。
- MQTT 消息 JSON 格式：`{"payload_b64":"<base64 编码的原始 payload>"}`，使用 `mbedtls_base64_encode`。

USB 协议（`protocol_packet.cpp`）：
- 保留 USB packet 契约：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD...][CRC_L][CRC_H]`。
- `TYPE=0x01` MLX90640，`TYPE=0x02` MaixSense ToF。
- CRC16-CCITT 初始值 `0xFFFF`，多项式 `0x1021`，仅覆盖 payload，小端序。
- ToF payload 保持完整 MaixSense 原始帧：`[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`。

发送路径：
- `usb_send_tof_payload()` 和 `mlx_sender_task` 在 USB CDC 发送完成后**额外**调用 `network_publish_sensor()`，两条路径并行。
- 大 payload（ToF 帧约 10KB → base64 约 13.5KB + JSON 包装）用 `malloc` 动态分配 JSON 缓冲区，避免栈上固定 256B 之类的常见坑。
- MQTT 未连接时 `network_publish_sensor` 直接返回 false，不阻塞数据采集主路径。

依赖与构建：
- `main/CMakeLists.txt` REQUIRES 补齐：`esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls` 等。
- `main/idf_component.yml` 增加 `espressif/mqtt` 组件依赖。

## 本地测试与编译验证结果

修复后运行的命令和结果：

- `python tests\run_public_tests.py project2_task` — **all public tests passed**
  - `test_compile.py`：OK
  - `test_functional_smoke.py`：admin page + setup endpoint 均 OK
  - `test_refactored_features.py`：auth / care_events / sleep_importer 模块均可调用
  - `test_smoke_gateway.py`：网关导入 + 睡眠导入正常
- `python tools\run_debug_probe.py project2_task` — **all visible diagnostic checks passed**（8/8 ok，0 failures）
  - admin setup returns 200 ✅
  - management API rejects missing cookie ✅
  - management API rejects forged cookie ✅
  - management API accepts valid cookie ✅
  - unknown identity session is denied ✅
  - expired session is denied ✅
  - care_event write rejects missing admin cookie ✅
  - care_event normalizes room/bed for create and query ✅
  - voice module 提示从 Warning 变为 info：已引用 current-session fetch
- `python tools\run_espidf_build.py project2_task` — **Build finished successfully**
  - 目标：`esp32s3`，ESP-IDF v6.0.1 Windows EIM
  - 产物：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`
  - App 大小：`0xeff20` 字节，分区 `0x100000`，剩余 `6%`
  - 仅有两个无关 warning：`trim_in_place` 未使用（device_config.c 静态函数）、`uart_config_t::flags` 缺初始化（非错误）

## 未验证的残留技术债与风险

1. **ESP 实机验证**：本次只完成了 Windows ESP-IDF 编译通过，未做 `idf.py flash`、`idf.py monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 巴法云连通、ToF 上电时序、MLX90640 I2C 实机读数准确性验证。
2. **MQTT 发布可靠性**：当前传感器帧来时如果 MQTT 未连接直接丢弃，没有队列或重试缓冲。在网络抖动场景下可能丢帧。如需高可靠，可后续加 ring buffer + 重发。
3. **MQTT 内存压力**：ToF payload base64 编码约 13.5KB/帧，发布时 `malloc` 约 20KB 临时缓冲。在 PSRAM 可用的 S3 上问题不大，但如果关了 PSRAM 可能要评估堆压力。
4. **Care event 细粒度权限**：当前 care_events 管理 API 只做了 admin cookie 校验，没有做按 actor 角色/目标患者的细粒度授权检查（API 层是管理 API，已限定 admin）。后续如果开放给 staff 角色，需要增加基于 target subject 的行级授权。
5. **旧 SQLite DB 更老版本的迁移**：目前迁移只处理了 care_events 表缺列的情况。如果存在比当前 schema 更古老、缺更多表/列的数据库，可能还有其它迁移点没覆盖；但 `CREATE TABLE IF NOT EXISTS` 结构上能保证全新库和当前结构一致。
6. **Voice session 缓存有效期**：`fetch_current_gateway_session` 做了简单本地缓存，如果 session 中途过期或被吊销，voice 侧可能短暂继续用旧 session_id 调用；由于 gateway 侧会再查 DB 校验，最坏结果是返回 not_authenticated，不泄露数据。
