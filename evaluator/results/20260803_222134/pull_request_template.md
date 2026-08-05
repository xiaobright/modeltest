# Pull Request 提测说明 (Pull Request Template)

本文件记录了 Project2 Sprint 的实际实现、测试与未验证风险。Reviewer 会与代码 diff 和 CI 自检日志做交叉一致性校验。

## 修改前初始自检结果

在动手前先运行了交接文档要求的两个自检脚本，得到以下基线：

### `python tests\run_public_tests.py project2_task`
通过：`[public] all public tests passed`（4 个测试文件全绿）。

### `python tools\run_debug_probe.py project2_task`
初始有 6 项实际症状 FAIL：

1. `management API rejects missing cookie`（缺 Cookie 访问 `/api/v3/subjects` 仍 200）
2. `management API rejects forged cookie`（伪造 Cookie 仍 200）
3. `unknown identity session is denied`（`identity_state=unknown` 会话仍被放行）
4. `expired session is denied`（已过期会话仍被放行）
5. `care_event write rejects missing admin cookie`（`/api/v3/care/events` 路由 404，且未鉴权）
6. `care_event normalizes room/bed`（大小写未归一化，查询不命中）

另外脚本打印 `[probe:Warning]` 提示 voice/本地助手仍依赖隐式 ambient session。

## 修改的文件列表

**网关 Python 端**
- `gateway/auth.py`：管理员密码强制加盐哈希（pbkdf2-sha256）、`admin_account_exists()` 真实查库、HTTP session 按 token_hash 精确匹配。
- `gateway/db.py`：`init_management_db` 委托 `care_events.init_care_events_table()` 创建并迁移 `care_events` 表（在独立连接上执行，避免 SQLite 锁）。
- `gateway/care_events.py`：重写为完整 CRUD（create/list/get）+ `build_care_events_context`，room/bed 归一化，旧表迁移补齐 `severity/source/created_by/ts` 并保留旧数据。
- `gateway/gateway.py`：
  - `_authorized_for_api`：本机 worker 例外仅限声明的 local-service 接口，管理 API（含 subjects/assignments/memories/credentials/care-events）一律要求有效管理员 session；
  - `session_is_authenticated`：`identity_state=unknown` / `assurance_level=none` / 过期 / 缺 `actor_subject_id` 均判未认证；
  - 新增 `/api/v3/care/events`（POST 需 admin，GET 支持 `subject_id`/`room+bed`/`limit`）与 `/api/v3/care/events/{id}`；
  - `build_chat_context_v3` 在授权通过后返回 `modalities.care_events`，未授权不返回；
  - `/api/v3/session/current` 加入本地 service 白名单。
- `gateway/sleep_importer.py`：`UNSCOPED_POLICY=first` 写入**第一个**配置床位（原为最后一个），per-row 归属策略只作用于无 room/bed 行。

**voice 路径**
- `voice/voice_assistant_integrated.py`：新增 `fetch_gateway_current_session()`；context 请求缺省时显式先取网关当前 session 再传 `session_id`，不再依赖网关隐式 ambient 兜底。

**ESP32-S3 固件**（`esp32/testpro4/main/`）
- 新增 `protocol_packet.{h,cpp}`：packet 常量、CRC16-CCITT、USB 包头构建。
- 新增 `device_config.{h,cpp}`：NVS 配置读写、完整性校验（room/bed、Wi-Fi ssid、bemfa_uid）、topic 前缀 `{room}{bed}` 小写归一化。
- 新增 `mqtt_payload.{h,cpp}`：`{"payload_b64":"..."}` JSON 构造（按 payload 动态缓冲）、topic 选择 `tof1/tof2/mlx1/mlx2`。
- 新增 `network_backhaul.{h,cpp}`：Wi-Fi STA + MQTT（巴法云 bemfa.com:9501）客户端、事件重连、`publish`（heap 缓冲，处理大 ToF 帧）。
- `main/main.cpp`：改用 `device_config` 统一 NVS 配置；`net_backhaul_init()` 在 `app_main` 启动；`usb_send_tof_payload` 与 `mlx_sender_task` 在保留 USB 输出同时发布对应 MQTT topic；`System Ready` 日志更新。
- `main/CMakeLists.txt`、`main/idf_component.yml`：补齐 `esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls` 依赖与托管 `espressif/mqtt`。

**文档**
- `README.md`、`esp32/testpro4/README.md`：同步 MQTT 已实现、新增模块文件清单、依赖。
- `PULL_REQUEST_TEMPLATE.md`：本文件。

## 架构调整与模块设计

- 沿用既有模块边界：`auth.py`（管理账号/密码/Cookie）、`db.py`（schema/迁移）、`subjects.py`（人员/床位/记忆/会话）、`sensor_store.py`（传感/睡眠/姿态/情绪缓存）、`esp_store.py`（ESP set 聚合）、`sleep_importer.py`（CSV 导入）、`care_events.py`（护理事件）。
- 关键策略：**鉴权收敛在 gateway 路由层**（`_authorized_for_api`）与 **上下文授权收敛在 `build_chat_context_v3`**；care_event 只作为数据层存在，不持有鉴权逻辑。
- ESP 端按 ONBOARDING 推荐的模块切分：协议打包 / NVS 配置 / MQTT payload / 网络回传，`main.cpp` 只做 glue。

## 安全边界及鉴权设计

- 管理员密码：`pbkdf2_hmac('sha256', password, salt, 200_000)`，salt 每次 `secrets.token_bytes(16)` 生成，DB 只存 salt + digest，**绝不明文**。
- Cookie：`secrets.token_urlsafe(32)`，DB 只存 `sha256(token)`，服务端按 token_hash 精确匹配且校验 `expires_ts`，伪造/过期/缺失均 401。
- 管理 API（subjects/assignments/memories/credentials/care-events 等）：即使本机（127.0.0.1）也要求有效管理员 Cookie；本机 worker 免 cookie 例外**仅**给予 `_path_allows_local_service` 声明的 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery|match`、`/api/v3/vision/observation`、`/api/v3/session/current`。
- v3 会话鉴权：`identity_state=unknown`、`assurance_level∈{none,''}`、`expires_ts` 已到、缺 `actor_subject_id` → 一律不可授权，敏感上下文（patient/assignment/memory/care_events）不返回。
- face template / credential template：远程未登录禁止导出；本地 worker 例外仅限白名单接口。
- voice 不再靠隐式 ambient session：先 `GET /api/v3/session/current` 取当前会话再显式携带 `session_id` 请求 context/chat，避免静默漏数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 按**行**处理：带 `room/bed` 的行只写入对应配置床位；不带的行才进入归属策略，不误改、不整表丢弃显式行。
- 无归属行策略（`SLEEP_IMPORT_UNSCOPED_POLICY`）：
  - `first`（默认）：写入**第一个**配置床位（已修正原 `beds[-1]` 最后一个的 bug）；
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED`：写入指定床位；
  - `skip`：跳过；
  - `all`：仅显式调试模式，非默认。

## care_event 实现细节

- DB：`care_events` 表含 `event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`；对旧库缺列用 `ALTER TABLE ADD COLUMN` 迁移并以 `ts=created_ts` 回填、`severity='info'`、`source='manual'` 兜底，旧行完整保留；索引 `(subject_id, ts, created_ts)` 与 `(room, bed, ts, created_ts)`。
- 归一化：写入与查询均用 `normalize_room/normalize_bed`（大写），`r1203/b1` 与 `R1203/B1` 互通。
- API：`POST /api/v3/care/events`（需管理员）、`GET /api/v3/care/events?subject_id=...`、`GET ?room=...&bed=...`、`limit` 参数，按 `ts/created_ts` 倒序。
- 上下文：授权通过后注入 `modalities.care_events`（最近 5 条摘要），未授权时为空，不泄漏护理内容。

## ESP32-S3 固件接口对齐说明

- **Wi-Fi + MQTT 巴法云回传已恢复**：Wi-Fi STA 初始化（`esp_netif/esp_event/esp_wifi`），MQTT client 连 `bemfa.com:9501`（ClientID/Username/Password 均用巴法云 UID），断线自动重连。
- **NVS 校验**：读取并校验 `ssid/password/uid/room/bed`，任缺网络键时退化为仅 USB 采集（`ready=false`）。
- **Topic**：小写拼接 `{room}{bed}tof1/tof2/mlx1/mlx2`（如 `r1203b1tof1`）。
- **Payload**：`{"payload_b64":"<base64>"}`，base64 为传感器原始 payload（MLX 3072B float 温度；ToF 完整 MaixSense 原始帧 `[00 FF][LEN][META16][IMG 10000][CHK][DD]`），**不是**完整 USB packet。
- **并行性**：USB CDC 输出保留，MQTT 独立发布，大 ToF payload 按需 heap 缓冲（约 13KB 上限），避免固定小缓冲。
- **CRC/包头**：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 只覆盖 payload，LEN/CRC 小端序。
- **依赖**：`CMakeLists.txt` 补 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`，`idf_component.yml` 补 `espressif/mqtt`。

## 本地测试与编译验证结果

- `python tests\run_public_tests.py project2_task` → `[public] all public tests passed`。
- `python tools\run_debug_probe.py project2_task` → `[probe] all visible diagnostic checks passed`；8 项原 FAIL 全修复，voice warning 已清除。

  ```
  [probe:ok] admin setup returns 200
  [probe:ok] management API rejects missing cookie
  [probe:ok] management API rejects forged cookie
  [probe:ok] management API accepts valid cookie
  [probe:ok] unknown identity session is denied
  [probe:ok] expired session is denied
  [probe:ok] care_event write rejects missing admin cookie
  [probe:ok] care_event normalizes room/bed for create and query
  [probe:info] voice module appears to reference current-session fetch
  ```

- 数据库迁移（legacy `care_events` 仅旧 9 列）：实测补齐 `severity/source/created_by/ts`，旧行保留、`ts` 回填、索引建立。
- `python tools\run_espidf_build.py project2_task` → **ESP-IDF v6.0.1 编译成功**：
  ```
  [espidf] output_bin = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
  [espidf] Build finished successfully.
  ```
  （set-target esp32s3 + 全量 `cmake --build`，无 Docker/WSL/flash/monitor。）

## 未验证的残留技术债与风险

- **未做真机验证**：Wi-Fi/MQTT 连通、巴法云账号可用性、真实 UART/I2C 时序、ToF 上电冷启动与自动波特率探测、MLX90640 实测温度均未在本地硬件运行（本任务不要求，ENTEST 范围仅编译）。
- MQTT 大 payload（~13KB）依赖巴法云对单条消息尺寸/频率的限流，真实部署需实测；如被截断需在网关侧分片约定。
- `network_backhaul` 使用 `esp_mqtt_client_publish`（对应 topic 需在巴法云侧已订阅/允许），未做 QoS/retain 策略，丢包时无本地补发。
- voice 显式取 current session：若关联的 session 已过期/未知，context 会被拒，本地助手会给出“未认证”提示（符合收紧预期，但需在护士站完成识别）。
- `esp_mqtt` 组件由组件管理器拉取（`espressif/mqtt`），不同 IDF 小版本升级后 `esp_mqtt_client_config_t` 字段可能有细微差异，重新编译时请复核。
- `collectdata_esp32.py`（USB 上位机采集脚本）与 `sketch_jan22a.ino` 未改动，仍为既有实现。
