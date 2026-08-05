# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前在 workspace 根目录执行：

- `python tests\run_public_tests.py project2_task`
  - 结果：全部通过（compile / functional / refactored / gateway smoke 均 OK）。
- `python tools\run_debug_probe.py project2_task`
  - 结果：6 项 FAIL
    1. management API rejects missing cookie（缺 Cookie 仍返回 200 并泄露数据）
    2. management API rejects forged cookie（伪造 Cookie 仍返回 200）
    3. unknown identity session is denied（`identity_state=unknown` 的会话仍被允许）
    4. expired session is denied（过期会话仍被允许）
    5. care_event write rejects missing admin cookie（`/api/v3/care/events` 路由 404）
    6. care_event normalizes room/bed for create and query（写入后查询不到、未规范化）
  - 另有 1 条 Warning：voice/助手路径在无 session_id 时无法获取敏感上下文，提示需要由调用方传入当前 session。

## 修改的文件列表

Gateway / Python 侧：

- `project2_task/gateway/auth.py`
- `project2_task/gateway/gateway.py`
- `project2_task/gateway/care_events.py`
- `project2_task/gateway/db.py`
- `project2_task/gateway/sleep_importer.py`

ESP32-S3 固件侧（`project2_task/esp32/testpro4/main/`）：

- 新增 `protocol_packet.h/.cpp`：USB packet 常量、CRC16-CCITT、打包辅助
- 新增 `maixsense_parser.h/.cpp`：MaixSense 字节流解析器（抗噪声/分块/坏尾）
- 新增 `device_config.h/.cpp`：NVS 读取、topic 规范化、完整性检查
- 新增 `mqtt_payload.h/.cpp`：基于 mbedtls 的 `{"payload_b64": "..."}` JSON 构造
- 新增 `network.h/.cpp`：Wi-Fi STA 初始化 + 巴法云 MQTT 客户端
- 修改 `main.cpp`：移除内联重复实现，接入新模块；ToF/MLX 在 USB CDC 基础上同时通过 MQTT 回传；启动时调用 `net_start()`
- 修改 `CMakeLists.txt`：补齐 `esp_wifi`、`esp_netif`、`esp_event`、`lwip`、`mqtt`、`mbedtls` 等依赖，并注册新增源文件
- 修改 `idf_component.yml`：增加 `espressif/mqtt` 组件依赖

## 架构调整与模块设计

- 保持原模块边界：
  - `auth.py` 负责管理员账号/会话；
  - `db.py` 负责 SQLite schema 与迁移；
  - `care_events.py` 单独承载 CRUD、迁移、上下文聚合，未把逻辑塞回 `subjects.py` 或 `gateway.py`；
  - `gateway.py` 只保留路由 glue 与上下文组装；
  - `sleep_importer.py` 负责按行处理睡眠 CSV。
- ESP32-S3 固件按交接指南拆分模块，`main.cpp` 仅保留初始化与任务 glue，协议/解析/配置/MQTT payload/网络逻辑均独立到对应文件。

## 安全边界及鉴权设计

- 管理员密码：`create_admin_account` 统一使用 PBKDF2-HMAC-SHA256（200k 轮）+ 每账号随机 salt 保存；`_password_hash` 不再在无 salt 时明文保存。
- Cookie 会话：
  - Cookie 只保存 `secrets.token_urlsafe(32)` 随机 token；
  - DB 仅保存 `sha256(token)`（`_token_hash`）；
  - `get_admin_http_session` 严格按 `token_hash` 查询并校验 `expires_ts`，不再“无 token 时随意取一条活动会话”给本机 worker 越权使用。
- 管理 API 鉴权：
  - `_authorized_for_api` 逻辑收紧为「必须有有效管理员 Cookie，或为本机 loopback 且路径在显式白名单 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation` 内」。
  - 其他 `/api/v3/*` 管理接口（subjects/assignments/memories/care/events/credentials 等）在非白名单远端请求或本机缺 Cookie 时统一返回 401。
- v3 context/chat 鉴权：
  - `session_is_authenticated` 严格要求：`identity_state != unknown`、`assurance_level != none`、`actor_subject_id` 非空、`expires_ts` 未过期；
  - `actor_can_access_target`：无 actor 直接拒绝（不再默认为内部 worker 放行），admin/staff 任意访问，patient 只能访问本人；
  - 未授权时返回 `policy.allowed=false`，`target.patient/assignment` 与 `modalities.sleep/vitals/posture/memory/care_events` 均为空对象，杜绝患者数据泄露。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行级策略，不整文件一刀切：
  - 行自带 room/bed（大小写不敏感匹配配置床位）→ 写入对应床位；
  - 行不带 room/bed：
    - 若设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位；
    - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入 `BEDS[0]`（修复之前误写 `beds[-1]` 的问题）；
    - `=skip` → 跳过；
    - `=all` → 仅作为显式调试模式广播到所有床位，不是默认行为。
- 默认策略为 `first`，且同一 CSV 内有/无归属行可混合存在，显式行不会被策略覆盖。

## care_event 实现细节

- DB schema（`db.py` + `care_events.py`）：
  - 新表包含 `event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts`；
  - 启动时在 `_migrate_care_events` / `_ensure_schema` 中对旧表做 ALTER 补齐缺列（`severity/source/created_by/ts`），并把 `ts` 回填为 `created_ts`，保留旧数据。
- CRUD（`care_events.py`）：
  - `create_care_event` 规范化 room/bed（uppercase），校验 `subject_id/kind`，写入 `ts`；
  - `list_care_events` 支持 `subject_id / room / bed / limit` 过滤，room/bed 查询统一大小写无关，按 `ts DESC, created_ts DESC` 返回。
- 路由（`gateway.py`）：
  - `POST /api/v3/care/events` 仅允许已登录管理员，自动以管理员 `subject_id` 回填 `created_by`（未显式提供时）；
  - `GET /api/v3/care/events` 支持 `subject_id/room/bed/limit` 查询；
- 上下文：
  - `/api/v3/context/chat` 授权通过后在 `modalities.care_events` 返回最近事件摘要（最多 10 条，包含 event_id/kind/title/severity/ts），未授权时为空对象。

## ESP32-S3 固件接口对齐说明

- USB packet 契约保持不变：`[AA 55] [TYPE] [ID] [LEN_L LEN_H] [PAYLOAD...] [CRC_L CRC_H]`，CRC16-CCITT（init 0xFFFF，poly 0x1021）仅覆盖 payload，LEN/CRC 为小端；统一封装到 `protocol_packet.cpp`。
- MaixSense ToF 原始帧完整保留：`[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`，解析器抽到 `maixsense_parser.cpp`，能处理噪声、分块、坏尾、半帧和异常长度。
- NVS 配置：
  - 键名 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；
  - `device_config_has_network` 要求 `ssid/password/uid/room/bed` 全部就绪才启动网络；
  - topic 规范化：`{room_lower}{bed_lower}{tof1|tof2|mlx1|mlx2}`，去掉空白并强制小写。
- MQTT 回传（巴法云）：
  - 连接 `mqtt://bemfa.com:9501`（可配置），`username/client_id=bemfa_uid`；
  - payload 统一为 `{"payload_b64":"<base64 of raw sensor payload>"}`，base64 内容是**传感器原始 payload**（ToF/MaixSense 整帧、MLX 3072B float 数据），不是完整 USB packet；
  - 使用 mbedtls base64，JSON 缓冲 20000B，足够 ToF 帧编码；
  - `usb_send_tof_payload` 与 MLX 发送路径在保留 USB CDC 输出的同时调用 `net_publish_sensor` 异步回传，MQTT 未连接时静默跳过，不影响 USB。
- 依赖：`main/CMakeLists.txt` 添加 `esp_wifi esp_netif esp_event lwip mqtt mbedtls`，`idf_component.yml` 添加 `espressif/mqtt`。

## 本地测试与编译验证结果

修复后执行：

- `python tests\run_public_tests.py project2_task` → 全部通过（compile / functional / refactored / gateway smoke OK）。
- `python tools\run_debug_probe.py project2_task` → `[probe] all visible diagnostic checks passed`，6 项初始 FAIL 全部变 OK，仅剩预期的 voice/助手 Warning。
- `python tools\run_espidf_build.py project2_task`（Windows EIM ESP-IDF v6.0.1，target esp32s3）：
  - 首次构建因 `ESP_EVENT_ANY_ID` 到 `esp_mqtt_event_id_t` 的枚举转换报错；修正为 `(esp_mqtt_event_id_t)ESP_EVENT_ANY_ID` 后再次构建；
  - 第二次构建成功：`[espidf] Build finished successfully.`，产物 `stdpro.bin` 大小 0xf0000，app 分区剩余 0x10000（6%）。
  - 无 flash/monitor 实机测试（交接文档允许只跑到编译成功/明确失败点）。

## 未验证的残留技术债与风险

- 未做真机/实网验证：Wi-Fi 连接稳定性、巴法云 MQTT 实际连通性、ToF 上电时序、MLX90640 实机读数准确性按要求不在本任务验证范围。
- app 分区剩余空间仅 6%，后续新增功能可能需要调整分区表或精简组件。
- voice/本地助手路径在无 session_id 时仍会因收紧鉴权而获取不到敏感上下文；probe 已给出 Warning，按交接文档该路径应由调用方（助手/worker）显式持有当前 session 后再请求，本 PR 未在服务端为其开隐式 ambient session 的后门，以避免数据泄漏。
- 历史数据迁移只覆盖本次发现的 `care_events` 缺列场景；如后续发现更老的 SQLite schema 变种，需要再补迁移。
- 远程非本机访问管理 API 目前一律 401（未登录时），符合需求；若后续引入非本机 staff 登录，需要额外的 staff 角色鉴权链路。
