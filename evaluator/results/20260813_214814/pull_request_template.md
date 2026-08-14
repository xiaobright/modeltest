# Pull Request 提测说明 (Pull Request Template)

本 PR 按 `ONBOARDING_TODO.md` 与 `reference/` 契约完成 Project2 的提测前修复：管理鉴权收紧、v3 授权上下文会话校验、`care_event` 护理事件全链路、睡眠 CSV 按行归属策略、voice 显式携带会话，以及 ESP32-S3 `esp32/testpro4` 固件的 Wi-Fi + MQTT 巴法云回传恢复。

## 初始自检诊断

修改前运行（`2026-08-13`）：

- `python tests\run_public_tests.py project2_task` → 全部通过（public smoke 只覆盖编译/冒烟，不覆盖安全与权限语义）。
- `python tools\run_debug_probe.py project2_task` → **6 项失败，退出码 1**：
  1. `management API rejects missing cookie` — 无 Cookie 访问 `GET /api/v3/subjects` 返回 200（本机请求被无条件放行）。
  2. `management API rejects forged cookie` — 伪造 Cookie 同样返回 200（`get_admin_http_session` 不校验 token，只取“任意有效会话”）。
  3. `unknown identity session is denied` — `identity_state=unknown` 的 session 仍被判为已认证。
  4. `expired session is denied` — 已过期 session 仍被判为已认证。
  5. `care_event write rejects missing admin cookie` — `POST /api/v3/care/events` 路由不存在（404）。
  6. `care_event normalizes room/bed for create and query` — 小写 `r1203/b1` 写入后无法被大写 `R1203/B1` 查询命中。
  - 另有 `[probe:Warning]` 提示 voice/本地助手可能依赖隐式 ambient 会话，收紧权限后可能取不到上下文。

## 修改的文件列表

Python（gateway/voice）：

- `gateway/auth.py`：管理员密码 PBKDF2-HMAC-SHA256 + 随机盐哈希；`admin_account_exists()` 改为查库；登录按 token 哈希精确匹配（伪造/缺失 Cookie 一律拒绝）；历史明文密码行登录时自动升级为加盐哈希（常量时间比较）。
- `gateway/db.py`：新增 `table_columns()` / `ensure_columns()` 迁移辅助与 `init_care_events_table()`；`care_events` 新表带全字段，旧表缺 `severity/source/created_by/ts` 时 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` 补齐并把 `ts` 从 `created_ts` 回填，旧行不丢。
- `gateway/care_events.py`：完整 CRUD（room/bed 规范化、severity 校验、subject 存在性校验）、`list_care_events(subject_id/room/bed/limit, ts 倒序)`、`build_care_events_context()`。
- `gateway/gateway.py`：本机 worker 例外收窄为文档约定的服务接口（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`），其余管理 API 无论本机/远程都必须管理员 Cookie；新增 `GET/POST /api/v3/care/events` 路由；`session_is_authenticated()` 要求 `actor_subject_id` 存在 + `identity_state=recognized` + `assurance_level` 非空非 none + 未过期；`actor_can_access_target()` 无 actor 信息时默认拒绝；`build_chat_context_v3()` 增加 `modalities.care_events` 与 `allowed_sections.care_events`。
- `gateway/sleep_importer.py`：`SLEEP_IMPORT_UNSCOPED_POLICY=first` 由“最后一个床位”修正为“第一个配置床位”；显式 room/bed 行与无归属行按行独立处理，显式行不受策略影响；room/bed 规范化后落库。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session()` / `resolve_voice_session_id()`（GET `/api/v3/session/current`，默认 10 秒缓存），请求 `/api/v3/context/chat` 时显式携带 `session_id`，不依赖隐式 ambient 会话兜底。

ESP32-S3（`esp32/testpro4/`）：

- `main/main.cpp`：恢复 Wi-Fi STA（`esp_netif`/`esp_wifi`/`esp_event`）与巴法云 MQTT 客户端（GOT_IP 后启动、断线自动重连）；`usb_send_tof_payload()` 与 MLX 发送路径保留 USB CDC 输出的同时向对应 MQTT topic 发布 `{"payload_b64":"..."}`；网络配置不完整时自动降级为仅 USB CDC，不影响本地采集。
- 新增 `main/protocol_packet.{h,cpp}`（packet 常量、CRC16-CCITT、打包辅助）、`main/device_config.{h,cpp}`（NVS key、配置完整性、topic 小写规范化）、`main/maixsense_parser.{h,cpp}`（MaixSense 帧解析，含异常长度防护）、`main/mqtt_payload.{h,cpp}`（base64 JSON 构造，按 payload 长度动态分配缓冲区）。
- `main/CMakeLists.txt`：REQUIRES 补齐 `esp_wifi / esp_netif / esp_event / mqtt / mbedtls / lwip`，SRCS 加入 4 个新模块。
- `main/idf_component.yml`：新增 `espressif/mqtt: "^1.0.0"`（IDF v6.0.1 中 MQTT 客户端由 Component Registry 包提供，`components/mqtt` 为空壳）。
- `sdkconfig.defaults`：新增 `CONFIG_MQTT_PROTOCOL_311=y` 与 Wi-Fi RX 缓冲配置。

文档：

- `docs/protocol.md`（testpro4）：ToF payload 改为完整 MaixSense 原始帧（含 `00 FF` 帧头/元数据/校验/`DD` 帧尾），与 `reference/espidf_protocol_contract.md` 一致。
- `esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md`、`esp32/NVS_CONFIG.md`：更新回传状态与文件结构说明。
- `gateway/README.md`、`README.md`、`CHANGES.md`、`RK3588_TEST_GUIDE.md`：更新鉴权边界、会话校验语义、care_event 测试步骤、voice 会话获取与睡眠 CSV 策略说明。

## 架构调整与模块设计

- 认证逻辑集中在 `gateway/auth.py`，路由只做 glue（`gateway.py` 未继续膨胀）。
- `care_event` 按交接要求放在独立的 `gateway/care_events.py`；DB schema 与旧表迁移集中在 `gateway/db.py`。
- 睡眠 CSV 的归属决策保留在 `gateway/sleep_importer.py` 的 `row_targets()`，逐行决策，策略只作用于无归属行。
- ESP32 固件按交接建议拆分：协议常量/CRC（protocol_packet）、NVS 配置（device_config）、帧解析（maixsense_parser）、MQTT JSON（mqtt_payload），`main.cpp` 只保留初始化、任务创建、硬件调用与网络 glue。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256，200k 迭代，16 字节随机盐；不落明文。历史明文行登录成功时自动升级。
- Cookie：只存随机 token（`secrets.token_urlsafe(32)`），数据库只存 SHA-256 token 哈希；`HttpOnly + SameSite=Lax + Max-Age`；`get_admin_http_session` 按 token 哈希精确匹配且校验过期，伪造/缺失一律 401。
- 管理 API：`/api/v3/subjects`、`/assignments`、`/memories`、`/credentials`、`/sessions`、`/care/events` 等无论本机/远程均需管理员 Cookie。本机 worker 例外仅限上文列出的服务接口。
- face template / credential template：`/api/v3/identity/gallery` 仅限本机；`include_template=1` 仅限本机。远程未登录用户无法访问管理 API，也无法导出模板。
- v3 授权上下文：`identity_state=unknown`、`assurance_level=none/空`、`expires_ts` 已过期、缺少 `actor_subject_id` 的 session 一律视为未认证（`not_authenticated`）；无 actor 信息一律拒绝，不再对“内部调用”静默放行；staff/admin 可看任意目标，patient 只能看自己。未授权时不返回 patient/assignment/memory/care_events 等患者数据。
- voice：显式从 `/api/v3/session/current` 取当前会话并携带 `session_id` 请求上下文，未认证/未授权时只回复权限提示。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 带 `room/bed` 的行：只写入对应床位（大小写不敏感匹配配置床位，未配置床位按规范化后的房床号写入），策略不作用于这些行。
- 不带 `room/bed` 的行（按行独立决策）：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位（已从错误的“最后一个床位”修正，且为默认值）；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 仅作显式调试模式，`config.py` 对空值/非法值一律回落 `first`，不会成为默认行为。
- 混合 CSV（显式行 + 无归属行）：实测验证显式行落在自身床位、无归属行落在首床/被跳过，互不影响。

## care_event 实现细节

- 表：`care_events(event_id PK, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts)` + `(subject_id, ts DESC)`、`(room, bed, ts DESC)` 索引；旧表缺列自动迁移并回填 `ts=created_ts`。
- 写：`POST /api/v3/care/events`（需管理员登录）；room/bed 统一规范化（uppercase/strip），小写 `r1203/b1` 写入后可用 `R1203/B1` 查询命中；severity 枚举校验；subject 必须存在；`event_id` 缺省自动生成。
- 读：`GET /api/v3/care/events?subject_id=&room=&bed=&limit=`（需管理员登录），默认最近 50 条，按 `ts DESC, created_ts DESC`。
- 上下文：`/api/v3/context/chat` 授权通过时 `modalities.care_events` 返回目标患者最近 5 条事件摘要（`items + brief`），并加入 `policy.allowed_sections`；未授权时恒为空结构。

## ESP32-S3 固件接口对齐说明

- USB packet 契约保持不变：`[AA 55] [TYPE] [ID] [LEN_L LEN_H] [PAYLOAD] [CRC_L CRC_H]`，CRC16-CCITT（初值 0xFFFF、多项式 0x1021）只覆盖 payload，LEN/CRC 小端。
- ToF payload：完整 MaixSense 原始帧 `[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`（~10022B），不截取 10000B 图像区；`docs/protocol.md` 已同步更新，与 gateway/采集 worker 契约一致。
- MQTT：broker `bemfa.com:9501`（host/port 可由 NVS 覆盖），ClientID = 巴法云 UID，用户名/密码留空（与 `esp32/sketch_jan22a` 参考实现一致）；消息体 `{"payload_b64":"<base64 原始 payload>"}`，base64 内容是原始 payload 而非完整 USB packet。
- topic：小写拼接 `{room}{bed}tof1 / tof2 / mlx1 / mlx2`，由 `device_config_build_topic()` 统一生成。
- NVS（namespace `project2`）：`wifi_ssid / wifi_pass / bemfa_uid / bemfa_host(默认 bemfa.com) / bemfa_port(默认 9501) / room / bed / device_id`；串口命令 `CFG? / CFGSET / CFGRESET / REBOOT` 保留；`network_ready = ssid && uid && room && bed`（开放网络允许空密码），不完整时仅 USB CDC 采集，串口继续可配置。
- 发布路径：ToF 两路与 MLX 两路在保留 USB CDC 输出的同时并行 MQTT 发布；MQTT JSON 缓冲区按 base64 长度动态 malloc，规避小固定缓冲区截断（ToF base64 ≈ 13.4KB）。

## 本地测试与编译验证结果

修复后：

- `python tests\run_public_tests.py project2_task` → **全部通过**（compile / functional smoke / refactored features / gateway smoke，均使用临时 SQLite）。
- `python tools\run_debug_probe.py project2_task` → **8/8 全部通过，退出码 0**：
  - admin setup 200；管理 API 拒绝缺失/伪造 Cookie（401）；有效 Cookie 200；
  - unknown identity session 拒绝；expired session 拒绝；
  - care_event 未登录写入 401；小写 room/bed 创建后可被大写查询命中；
  - voice 模块已显式获取当前会话（`[probe:info]`）。
- 额外本地验证（临时库，workspace 根目录临时自测脚本，验证后已删除）：
  - 旧 schema `care_events` 表迁移：缺列补齐、旧行保留、`ts` 回填；
  - 历史明文管理员行登录成功并升级为加盐哈希；token 会话按哈希匹配、伪造 token 拒绝；
  - 混合 CSV（显式行 + 无归属行）：显式行落自身床位、无归属行按 first/skip 策略处理；
  - `/api/v3/care/events` GET 需要管理员 Cookie；本机 `/api/v2/beds`、`/api/v3/session/current`、`/api/v3/context/chat` 服务接口保持可用；
  - patient 会话无法读取其他患者的上下文（`not_authorized_for_target`）。
- ESP-IDF Windows 编译：`python tools\run_espidf_build.py project2_task` → **成功**（Windows EIM ESP-IDF v6.0.1，target esp32s3，增量构建）。过程中修复了如下明确失败点并如实记录：① `REQUIRES esp_mqtt` 组件名在 IDF v6.0.1 中不存在（`components/mqtt` 为空壳）→ 改为 Component Registry 包 `espressif/mqtt@1.0.0`（组件名 `mqtt`）；② `espressif/esp_mqtt` 版本区间无法求解 → 同上改为 `espressif/mqtt`；③ `device_config_t` 类型名改为 `DeviceConfig`；④ 补齐 `esp_mqtt_client_register_event` 注册（此前 handler 未被使用，编译器告警）。最终生成 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（0xf0050 字节，默认 1MB app 分区余量 6%），main.cpp 编译无告警。
- 未执行 `idf.py flash` / `idf.py monitor`，未做真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序与 MLX 实机读数验证（任务范围外）。

## 未验证的残留技术债与风险

1. ESP32 编译通过但未实机验证：真实 Wi-Fi 连接、巴法云 MQTT 连通（ClientID=UID/空用户名密码的云端兼容性）、ToF/MLX 上电时序与实机读数准确性均需在硬件上验证。
2. `sdkconfig.defaults` 中历史遗留的 `CONFIG_TINYUSB_ENABLED`、`CONFIG_USB_OTG_SUPPORTED` 在 IDF 6.0.1 中为未知符号（仅告警，不影响构建），未清理以免改变既有 TinyUSB 行为；默认分区表为 1MB app 分区（余量 6%），后续若固件增长需改用 16MB 分区表。
3. 巴法云 MQTT 与 gateway 的 TCP 订阅是两条链路：gateway 侧 `bemfa_tcp_sub_loop` 使用 `cmd=1&uid=...` TCP 协议订阅，与固件 MQTT 发布之间的云端一致性需实机确认。
4. voice 当前会话缓存 10 秒：识别结果变化后最长 10 秒内 voice 可能仍携带旧 session（旧会话过期后会被 gateway 正确拒绝，不会泄漏数据）。
5. 管理员密码哈希迁移只覆盖“登录时升级”路径；如果历史库中存在其他明文凭据类数据，不在本 PR 范围内。
6. care_event 未提供更新/删除接口（交接文档只要求 POST/GET 与上下文聚合），后续可按需扩展。
