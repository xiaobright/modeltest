# Pull Request 提测说明 (Pull Request Template)

> 本文件为最终实现说明，与代码 diff、自检日志一致。

## 1. 修改的文件列表

### Gateway / Voice（Python）
- `gateway/auth.py`：管理员密码加盐哈希（PBKDF2-HMAC-SHA256）、`admin_account_exists()` 查询 DB、HTTP 会话严格按 Cookie token hash 匹配（不再"取任意活跃会话"）。
- `gateway/db.py`：`care_events` 完整 schema（新增 `severity/source/created_by/ts`）+ 旧表迁移（`PRAGMA table_info` + `ALTER TABLE ADD COLUMN`，旧行保留、`ts` 回填 `created_ts`、`room/bed` 规范化大写）+ 索引。
- `gateway/care_events.py`：完整 CRUD（`create_care_event / list_care_events / build_care_events_context`），写读均做 room/bed 规范化，按 `ts/created_ts` 倒序，支持 `limit`。
- `gateway/gateway.py`：管理 API 门禁收紧（本机例外仅限指定服务接口）、`/api/v3/care/events` POST/GET 路由、`build_chat_context_v3` 会话策略修复（未知/过期/缺 actor 一律拒绝）、`modalities.care_events` 聚合、`/api/v3/session/current` 加入本机服务例外、`POST /api/v3/admin/logout` 支持无 body。
- `gateway/sleep_importer.py`：无 room/bed 行的 `first` 策略改为写入**第一个**配置床位（原实现误写 `beds[-1]`）；默认 room/bed 规范化；按行策略保留。
- `voice/voice_assistant_integrated.py`：请求敏感上下文前显式获取 `/api/v3/session/current` 并携带 `session_id`，不再依赖静默 ambient session。

### ESP32-S3 固件（esp32/testpro4）
- 新增 `main/protocol_packet.{h,cpp}`：USB packet 常量、CRC16-CCITT、包头/CRC 构造。
- 新增 `main/maixsense_parser.{h,cpp}`：MaixSense 字节流解析（噪声/分块/坏尾/异常长度/半帧处理），输出完整原始帧。
- 新增 `main/device_config.{h,cpp}`：NVS 配置读写/校验/打印/topic 规范化（`{room}{bed}{kind}` 小写）。
- 新增 `main/mqtt_payload.{h,cpp}`：`{"payload_b64":"..."}` JSON 构造与发布（大 payload 缓冲按完整 ToF 帧估算 ~13.4KB）。
- 新增 `main/network_backhaul.{h,cpp}`：Wi-Fi STA + esp-mqtt 巴法云客户端生命周期与事件重连。
- 重写 `main/main.cpp`：保留 UART/AT 时序、TinyUSB、MLXManager glue；`usb_send_tof_payload()` 与 MLX 发送路径在 USB CDC 基础上并行 MQTT 发布；`app_main` 启动网络回传。
- `main/CMakeLists.txt`：补齐 `esp_wifi / esp_netif / esp_event / lwip / espressif__mqtt / mbedtls` 与新源文件。
- `main/idf_component.yml`：新增 `espressif/mqtt`（IDF v6 的 `components/mqtt` 仅为 test_apps 占位，需组件管理器提供）。
- 文档：`esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md` 同步更新。

### 文档
- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`：care_event API、CSV 归属策略、管理 API 鉴权边界、voice 会话链路、ESP32 状态同步更新。

## 2. 修改前初始诊断结果

- `python tests\run_public_tests.py project2_task`：**通过**（4 个 public 测试文件全过；但均为浅层 smoke，未覆盖安全属性）。
- `python tools\run_debug_probe.py project2_task`：**6 项失败**：
  1. `management API rejects missing cookie`（无 Cookie 返回 200）
  2. `management API rejects forged cookie`（伪造 Cookie 返回 200）
  3. `unknown identity session is denied`（identity_state=unknown 仍被放行）
  4. `expired session is denied`（过期 session 仍被放行）
  5. `care_event write rejects missing admin cookie`（路由 404，且本机请求未被门禁拦截）
  6. `care_event normalizes room/bed for create and query`（lowercase 写入后 uppercase 查不到）
- 另观察到：睡眠 CSV 无 room/bed 时 `first` 策略误写入 `R1203-B2`（`beds[-1]`）；`admin_accounts` 以明文保存密码；`get_admin_http_session` 忽略 token 取任意活跃会话；care_event 无 HTTP 路由/无 context 聚合；voice 依赖 ambient session。

## 3. 架构设计说明

- 保持既有模块边界：`gateway.py` 只做路由 glue；DB schema/迁移在 `db.py`；管理员会话在 `auth.py`；护理事件 CRUD 在 `care_events.py`（未扩大 `subjects.py`）。
- v3 上下文策略收敛为单一入口 `build_chat_context_v3`：`session_is_authenticated()`（actor/identity/assurance/expiry 全量校验）+ `actor_can_access_target()`（无 actor 一律拒绝；staff/admin 可查任意目标患者，patient 只能查自己）+ 授权通过才填充 `sleep/vitals/posture/memory/care_events`，未授权全部为空对象。
- 管理 API 门禁：管理员 Cookie 是管理类 API 的唯一凭证；本机 worker 例外收敛为显式白名单（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/*`、`/api/v3/vision/observation`、`/api/v3/session/current`）。
- 固件按职责拆分 5 个模块，`main.cpp` 保留硬件/任务 glue。

## 4. 安全边界及鉴权设计

- 管理员密码：随机 16 字节盐 + PBKDF2-HMAC-SHA256（20 万次迭代）落库，任何路径不再存明文。
- Cookie：仅存随机 token（`secrets.token_urlsafe(32)`），DB 只存 SHA-256(token)；校验严格按 `token_hash = ?` 匹配且未过期、账号 active；登出即删除并清 Cookie。
- 会话：`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 缺失或过期、缺 `actor_subject_id` 的 session 一律视为未认证；`policy.reason` 区分 `not_authenticated` / `not_authorized_for_target`。
- 零泄漏：未授权响应中 `target.patient/assignment`、`modalities.*`（含 `care_events`）均为空；face template / credential template 仍仅限本机服务读取。
- voice：请求 `/api/v3/context/chat` 前显式拉取当前 session 并传 `session_id`，不再依赖隐式 ambient session；未认证时按策略提示权限不足，不返回患者数据。

## 5. 睡眠 CSV 无 room/bed 时的处理

- 按**行**处理，不整文件一刀切：
  - 行带 `room/bed`：只写入该行对应床位（与配置床位匹配则用配置值，否则用行内值）。
  - 行不带 `room/bed`：
    - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位（规范化）。
    - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 写入**第一个**配置床位（修复原 `beds[-1]` 误写最后一个床位的 bug）。
    - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过。
    - `all` 仅显式调试模式（默认不启用）。
  - 同一 CSV 可混合显式行与无归属行，显式行不受策略影响。

## 6. care_event 实现细节

- DB：`care_events` 表含 `event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`；旧表（缺 `severity/source/created_by/ts`）自动迁移并保留旧数据，`ts` 回填 `created_ts`，旧 lowercase room/bed 迁移为 uppercase。
- API：
  - `POST /api/v3/care/events`：需管理员登录（无 Cookie → 401）。
  - `GET /api/v3/care/events?subject_id=...` 或 `?room=...&bed=...&limit=50`：需管理员登录，或本机经授权上下文（必须通过 v3 session 策略校验）。
  - 查询按 `ts DESC, created_ts DESC` 倒序，`limit` 默认 50、上限 500。
- Context：`/api/v3/context/chat` 授权通过时返回 `modalities.care_events`（最近 10 条摘要：`event_id/kind/title/severity/source/created_by/room/bed/ts` + brief）；未授权时返回空。

## 7. ESP32-S3 固件接口对齐说明

- **NVS 配置**：namespace `project2`，键 `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host(默认 bemfa.com) / bemfa_port(默认 9501) / room / bed / device_id`；完整性校验（缺任一关键项则不启动网络，打印 CFGHELP）；`CFGSET/CFG?/CFGRESET/REBOOT` 控制台命令保留。
- **Wi-Fi**：STA 模式，事件驱动（`WIFI_EVENT_STA_DISCONNECTED` 自动重连，`IP_EVENT_STA_GOT_IP` 记录 IP）。
- **MQTT（巴法云契约）**：`mqtt://bemfa.com:9501`，ClientID = 巴法云 UID，无用户名/密码；`MQTT_EVENT_CONNECTED/DISCONNECTED/ERROR` 维护连接状态；esp-mqtt 自带重连。
- **Topic**：`{room}{bed}tof1 / tof2 / mlx1 / mlx2`，全部小写拼接，不落 NVS。
- **Payload**：MQTT JSON 为 `{"payload_b64":"<base64>"}`，base64 内容是**原始传感器 payload**（ToF 完整 MaixSense 帧 `[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`；MLX 为 3072B float 块），**不是**完整 USB packet；JSON 缓冲按 ~13.4KB 预留。
- **USB 契约不变**：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD...][CRC_L][CRC_H]`，CRC16-CCITT（init 0xFFFF/poly 0x1021）只覆盖 payload，LEN/CRC 小端；ToF/MLX 发送路径保留 USB CDC 输出的同时并行发布 MQTT。

## 8. 本地测试与编译验证结果

- `python tests\run_public_tests.py project2_task` → **全部通过**（4/4 文件，7 个用例 OK）。
- `python tools\run_debug_probe.py project2_task` → **8/8 检查通过**（含 voice 路径提示：模块已显式获取当前 session）。
- 附加手工验证（临时 SQLite 库，未污染 `data/project2.db`）：
  - 旧版 `care_events` 表迁移：缺列补齐、旧行保留、ts 回填、lowercase room/bed 可被大写查询命中。
  - 管理员密码落库为盐+PBKDF2 哈希（非明文）；正确密码登录 200、错误密码 401；登出后旧 Cookie 失效 401。
  - care_event POST/GET 全链路（含大小写规范化、limit、无 Cookie 401）。
  - 零泄漏：ambient unknown session 拒绝返回患者/护理数据；显式 recognized staff session 正常返回并含 `modalities.care_events`。
  - CSV 混合行策略：`first`（含显式行+无归属行）→ 显式行写各自床位、无归属行写第一个床位；`skip` → 无归属行跳过；默认 room/bed → 无归属行写默认床位。
- `python tools\run_espidf_build.py project2_task`（Windows EIM ESP-IDF v6.0.1，target esp32s3）：
  - 首次失败点：`Failed to resolve component 'mqtt'`（IDF v6 内置 `components/mqtt` 仅为 test_apps 占位）→ 在 `idf_component.yml` 增加 `espressif/mqtt`，REQUIRES 改为 `espressif__mqtt` 后解决。
  - 第二次失败点：`ESP_EVENT_ANY_ID` int→`esp_mqtt_event_id_t` 转换错误 → 显式 cast 修复。
  - 最终：增量构建与 `--clean-copy` 全新构建均成功，产出 `stdpro.bin`（`[espidf] Build finished successfully.`）。

## 9. 未验证的残留技术债与风险

- **固件**：`idf.py flash/monitor`、真实 Wi-Fi/MQTT 连通、巴法云 topic 可达性、ToF 上电冷启动时序、MLX90640 实机读数、TinyUSB 实机枚举均未验证（本任务范围不要求；需现场板测）。sdkconfig 中 `TINYUSB_ENABLED`/`USB_OTG_SUPPORTED` 两个 Kconfig 符号在 IDF v6 已迁移，构建仅告警不报错，后续可按 IDF v6 新符号整理。
- **gateway**：face 识别 runtime 依赖 `onnxruntime/opencv`，本机未做真实摄像头链路验证；`/api/v2/voice/chat_context` 等 legacy 端点仍按本机服务例外开放（未加管理员门禁），符合 legacy 兼容要求，但生产部署应限制监听地址。
- **voice**：显式获取当前 session 后，若 gateway 当前 session 为 unknown（如无 vision 识别），voice 会按策略返回权限提示——这是预期行为；`VOICE_SESSION_ID` 仍可显式指定 session。
- **care_event GET**：本机"授权上下文"路径依赖 gateway 当前 session 或显式 `session_id` 参数；若部署时禁用本机例外（收紧网络边界），远程读取 care events 必须走管理员 Cookie。
- 未做并发/压力测试；SQLite 为单文件本地库，多进程写入需保持现有进程内单写模式。
