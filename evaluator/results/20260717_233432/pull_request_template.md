# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前在 workspace 根目录运行两条自检脚本（临时 SQLite），关键结果：

- `python tests\run_public_tests.py project2_task` 初始状态通过（公开冒烟只做编译/模块 import/基础页面），但不能暴露鉴权/session/care_event 缺陷。
- `python tools\run_debug_probe.py project2_task` 初始 `failures=6`：
  - `management API rejects missing cookie` → 未登录本地请求也能拿到 `/api/v3/subjects`
  - `management API rejects forged cookie` → 伪造 cookie 同样 200
  - `unknown identity session is denied` → `identity_state=unknown` 仍被认为已认证
  - `expired session is denied` → 过期 session 仍能拿患者明细
  - `care_event write rejects missing admin cookie` → 路由不存在（404）
  - `care_event normalizes room/bed for create and query` → `care_events.py` 仅 draft，缺字段/规范化/排序
- Voice bridge hint: `voice_assistant_integrated.py` 只通过 env/常量 session_id 调 `/api/v3/context/chat`，收紧鉴权后若会话过期会导致本地助手丢上下文。

## 修改的文件列表

Gateway/Python：

- `gateway/auth.py` — 修复密码加盐哈希、`admin_account_exists` 查库、`get_admin_http_session` 按 `token_hash` 精确匹配、`hmac.compare_digest` 校验。
- `gateway/db.py` — 新增 `migrate_management_db()`：对旧 `care_events` 表做 `ALTER TABLE ADD COLUMN` 补齐 `severity/source/created_by/ts` 并回填默认值；care_events 索引改为按 `ts DESC`。
- `gateway/care_events.py` — 完整 CRUD：字段校验、room/bed 规范化、参数化查询、按 `ts/created_ts DESC` 排序、limit、`build_care_events_context()` 生成 items+brief。
- `gateway/gateway.py` —
  - `_authorized_for_api` 改成「admin cookie 有效」或「本机 loopback 且在白名单本地服务路径」，本机不再默认放行全部 `/api/*`。
  - 白名单本地服务路径保留 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat|identity/gallery|identity/match|vision/observation|session/current`。
  - `actor_can_access_target` 去掉无 actor 默认放行；`session_is_authenticated` 强制 `identity_state≠unknown`、`assurance_level≠none`、`actor_subject_id` 非空、`expires_ts` 未过期。
  - `build_chat_context_v3` 未授权时完全不返回患者/assignment/care_events 明细，新增 `modalities.care_events` 仅授权后填充。
  - 新增 `GET /api/v3/care/events`、`POST /api/v3/care/events` 路由 glue。
- `gateway/sleep_importer.py` — 修复 `first` 策略误返回 `beds[-1]`，改为 `beds[0]`。
- `voice/voice_assistant_integrated.py` — 新增 `GATEWAY_CURRENT_SESSION_URL`、`fetch_current_session_id()`；调用 context 时若未显式传 session_id 则先拉 `/api/v3/session/current` 获取最新有效 session，避免依赖 ambient session。

ESP32-S3 固件（`esp32/testpro4/main/`）：

- 新增 `protocol_packet.h/.cpp`：USB packet 常量、`crc16_ccitt`、小端读写辅助。
- 新增 `maixsense_parser.h/.cpp`：MaixSense 原始帧流解析（溢出丢弃旧数据、半帧等待、假头跳过）。
- 新增 `device_config.h/.cpp`：NVS key 管理、room/bed 规范化（lowercase）、topic 拼接、config complete & network ready 校验。
- 新增 `mqtt_payload.h/.cpp`：动态 base64 缓冲 + `{"payload_b64":"..."}` JSON 构造，避免固定 256B 缓冲放不下 ToF payload。
- 新增 `network.h/.cpp`：Wi-Fi STA + 巴法云 MQTT 客户端（`espressif/mqtt` v1.0.0），带 event group、重连计数、publish 封装。
- 重写 `main.cpp`：移除重复的 CRC/NVS/parser 代码，改调上述模块；`usb_send_tof_payload`/`mlx_sender_task` 保留 USB CDC 同时调用 `mqtt_publish_raw` 把原始 payload（非完整 USB packet）base64 发布到 `{room}{bed}{tof1|tof2|mlx1|mlx2}` topic。
- `main/CMakeLists.txt` 补齐 SRCS 和 `REQUIRES esp_wifi esp_netif esp_event lwip mqtt mbedtls ...`。
- `main/idf_component.yml` 加入 `espressif/mqtt: ^1.0.0`（IDF v6.0.1 把 MQTT 迁出核心）。

## 架构调整与模块设计

保持原有模块边界：

- `gateway.py` 只做 HTTP glue（路由、Cookie 解析、admin HTML），不再增长业务逻辑。
- `auth.py` 专注管理员账号 + Cookie session（密码 PBKDF2-SHA256 200k 轮，token 只在 Cookie 中随机；DB 存 `token_hash = sha256(token)`，查时按 hash 精确匹配）。
- `subjects.py` 维持人员/绑定/凭证/会话；`sessions` 表在迁移中补齐 `created_ts/last_seen_ts`。
- `care_events.py` 独立承载 CRUD + context summary；`db.py` 显式 `PRAGMA table_info` + `ALTER TABLE` 做旧库迁移，保留旧数据。
- `sleep_importer.py` 行级策略：显式 `room/bed` 优先匹配配置床位，无归属行按 env（`SLEEP_IMPORT_DEFAULT_ROOM/BED`）、`SLEEP_IMPORT_UNSCOPED_POLICY ∈ {first,skip,all}` 处理，同一文件混合行不互斥。
- ESP 侧拆出 `protocol_packet / maixsense_parser / device_config / mqtt_payload / network` 五个纯逻辑模块，`main.cpp` 只保留初始化、任务调度和 glue。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256（200,000 轮）+ 16 字节随机 salt，不存明文。
- Cookie：服务端生成 `secrets.token_urlsafe(32)`，仅把 `sha256(token)` 写入 `admin_http_sessions`；Cookie 设置 HttpOnly/SameSite=Lax/有限 Max-Age；伪造 token 在 DB 按 hash 精确查不到 → 返回 401。
- 本机 worker 例外路径收敛到白名单：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`；其余 `/api/*` 必须带有效管理员 Cookie。
- `/api/v3/identity/gallery` 保留远端 403；`/api/v3/credentials?include_template=1` 保留远端 403，face/credential template 不外泄。
- v3 会话鉴权收紧：`identity_state=unknown`、`assurance_level=none/空`、缺 `actor_subject_id`、`expires_ts` 过期都视为未认证；`actor_can_access_target` 仅 staff/admin 或 patient 本人。未授权时 `target.patient / target.assignment / modalities.sleep/vitals/posture/memory/care_events` 全部返空。
- Voice/本地助手：新增 `/api/v3/session/current` 本机可访问，voice 模块优先用 `VOICE_SESSION_ID`，否则主动拉取当前有效 session 再请求敏感上下文，不再依赖隐式 ambient session 漏数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行级策略。`row_targets()` 对每行独立判断：
  - 行中显式 `room/bed`（支持 `room/Room/ROOM` 等大小写）→ 匹配配置床位（大小写不敏感）后写入；若不在配置里按行值写入。
  - 无归属行：
    1. 若 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 都设置 → 写入该床位。
    2. 否则按 `SLEEP_IMPORT_UNSCOPED_POLICY`：`first` 写入 `beds[0]`、`skip` 跳过、`all` 广播（显式调试模式，非默认）。
- 已修复原实现中 `first` 误取 `beds[-1]` 的 off-by-one bug。

## care_event 实现细节

- Schema：`event_id PK, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts`。
- 迁移：`db.init_management_db()` 中 `migrate_management_db()` 对旧表 `PRAGMA table_info`，缺什么补什么，旧行 `severity='info', source='manual', created_by='', ts=created_ts`，不丢失数据。
- CRUD：`create_care_event()` 校验必填 + `normalize_room/bed`（存成大写 R1203/B1），`list_care_events(subject_id, room, bed, limit=50)` 按 `ts DESC, created_ts DESC`，room/bed 匹配大小写不敏感。
- API：`POST /api/v3/care/events` 需要管理员 cookie；`GET /api/v3/care/events?subject_id|room|bed|limit` 同样走管理员鉴权（gateway 全局 auth gate）。
- chat context：授权通过时 `modalities.care_events = build_care_events_context(subject_id, limit=5)` 返回最近护理事件 items+brief；未授权完全为空。

## ESP32-S3 固件接口对齐说明

- 保持 USB CDC 双口（CDC0=MLX, CDC1=ToF），packet 契约不变：`[AA 55] [TYPE] [ID] [LEN_L LEN_H] [PAYLOAD] [CRC_L CRC_H]`，CRC16-CCITT（初值 0xFFFF, poly 0x1021）小端，payload 覆盖 ToF 完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`。
- Wi-Fi STA + 巴法云 MQTT：`network.cpp` 内完成 `esp_netif_init / esp_event_loop_create_default / esp_wifi_init/start/connect`，拿到 IP 后起 `esp_mqtt_client` 连 `mqtt://{bemfa_host}:{bemfa_mqtt_port}`（默认 bemfa.com:9501），`username = bemfa_uid`。
- NVS：`device_config.cpp` 读/写 `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`；`config_is_complete` 仅要求 room/bed（USB-only 模式），`network_ready` 额外要求 ssid+uid。
- Topic：`device_config_build_topic()` 把 room/bed lower-copy 后拼接 suffix → `{room}{bed}tof1|tof2|mlx1|mlx2`（符合 gateway `bed_config.topics_for()` 规则）。
- Payload：`mqtt_payload_build_json()` 动态分配 base64 缓冲（ToF ~10KB 帧 base64 后约 14KB），构造 `{"payload_b64":"<base64 of raw sensor payload>"}`，base64 内容是原始 payload（不是完整 USB packet，符合契约）。
- 发布路径：`usb_send_tof_payload()` 和 `mlx_sender_task()` 在 CDC 写完 payload 后调 `mqtt_publish_raw(suffix, payload, len)`，USB/MQTT 并行不互斥。
- 工程：`main/CMakeLists.txt` 补 `esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls`；`idf_component.yml` 引 `espressif/mqtt ^1.0.0`。

## 本地测试与编译验证结果

修复后运行：

- `python tests\run_public_tests.py project2_task` → 全部 7 个用例 OK，最后输出 `[public] all public tests passed`。
- `python tools\run_debug_probe.py project2_task` → `[probe] all visible diagnostic checks passed`，failures=0。Voice hint 从 warning 变为 `voice module appears to reference current-session fetch`。
- `python tools\run_espidf_build.py project2_task`（Windows EIM IDF v6.0.1, target esp32s3）→ Build finished successfully：
  - `stdpro.bin binary size 0xeffb0 bytes. Smallest app partition is 0x100000 bytes. 0x10050 bytes (6%) free.`
  - `[espidf] output_bin = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`
  - 中间踩到 `espressif/mqtt` 不在 IDF v6 核心、`mbedtls/base64.h` 缺 include、`uart_config_t` 缺零初始化等编译错误，均已修复。

## 未验证的残留技术债与风险

- 仅做了「编译通过 + 公共/探针测试」级别的自检，没有 `idf.py flash/monitor` 实机验证 Wi-Fi/MQTT 连通、ToF 冷启动 AT 时序、MLX90640 I2C 实读数。按 ONBOARDING 要求这些不在本任务验收范围。
- MQTT 发送路径目前未做 QoS/离线缓存；Wi-Fi/MQTT 短时掉线时 payload 直接丢（和之前 USB-only 相比没有回归，USB 仍实时输出）。
- ToF payload base64 后约 14KB JSON，在 heap 紧张时 `malloc` 可能失败并返回 -3/-5；监控 heap 水位后可考虑静态缓冲或 heap_caps_malloc。
- `build_care_events_context` 目前只按 `subject_id`/`room+bed` 取最近 5 条，未做按 staff 权限的更细粒度裁剪（staff 已在 `actor_can_access_target` 层通吃）。
- 历史 admin_accounts 若之前已被错误写入明文密码（salt 为空的旧逻辑），需管理员重新 setup 才能正常登录；当前代码在 `create_admin_account` 阶段强制加盐哈希，新写入账号已安全。
- 未跑过 `RK3588_TEST_GUIDE` 涉及的端到端联调，rkllm/piper/webrtc 运行时不在本次修改范围。
