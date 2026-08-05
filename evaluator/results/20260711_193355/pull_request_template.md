# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行了以下命令，结果记录如下：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

### `run_public_tests.py` 初始结果

- `test_compile.py` ✅
- `test_functional_smoke.py` ✅（管理页和管理初始化 200）
- `test_refactored_features.py` ✅
- `test_smoke_gateway.py` ✅
- 公共测试集在种子代码上**全部通过**（已确认非空 DB 场景）。

### `run_debug_probe.py` 初始结果（修复前）

```text
[probe:ok] admin setup returns 200
[probe:FAIL] management API rejects missing cookie         status=200  # 鉴权完全没生效
[probe:FAIL] management API rejects forged cookie         status=200  # 任何伪造 cookie 都通过
[probe:ok]   management API accepts valid cookie
[probe:FAIL] unknown identity session is denied           allowed=True   # 旧版“unknown 直接视为通过”
[probe:FAIL] expired session is denied                    allowed=True
[probe:FAIL] care_event write rejects missing admin cookie status=404  # /api/v3/care/events 路由不存在
[probe:FAIL] care_event normalizes room/bed for create and query
```

加上 voice 提示：voice 路径是按 `session_id` 显式拉取（`build_gateway_context_params`），
不再依赖隐式 ambient session，紧缩鉴权后仍可工作。

## 修改的文件列表

### gateway/

- `project2_task/gateway/auth.py` — 重写：
  - `_password_hash` 永远生成新 salt（不再"无 salt 时落 plaintext"）
  - `_verify_password` 用 `hmac.compare_digest` 常量时间比较
  - `admin_account_exists` 真正查 DB
  - `get_admin_http_session` 严格按 `token_hash` 匹配（**关键：旧版忽略 token 直接返回任何活动会话**）
  - `delete_admin_http_session` 按 `token_hash` 删除
- `project2_task/gateway/care_events.py` — 完整重写：
  - 新增 `severity / source / created_by / ts` 字段
  - `_migrate_care_events_table` 在每次 init 时 `PRAGMA table_info` 检查缺失列并 `ALTER TABLE ADD COLUMN`，回填 `ts=created_ts`，保留旧行
  - `list_care_events` 用 `UPPER(room)/UPPER(bed)` 匹配，兼容 `r1203/b1` 历史数据
  - 新增 `build_care_events_context` 供 v3 chat-context 注入
- `project2_task/gateway/db.py` — `init_management_db` 调 `care_events._migrate_care_events_table`；删除 `CREATE TABLE care_events` 旧块（迁移在 care_events 模块内统一）
- `project2_task/gateway/gateway.py`：
  - `DEFAULT_ADMIN_SUBJECT_ID` 加入 `from config import …`
  - `session_is_authenticated` 严格化（unknown/无 assurance/过期/无 actor 全部拒绝）
  - `Handler._admin_session` 修复：当 ADMIN_AUTH_ENABLED 关闭时返回 `{"username": "disabled", "subject_id": DEFAULT_ADMIN_SUBJECT_ID}`
  - `Handler._authorized_for_api` 重写：cookie 优先；非白名单路径不再“loopback 即放行”
  - `Handler._LOCAL_SERVICE_PATHS` 显式列出允许本机无 cookie 的接口
  - 新增 `POST /api/v3/care/events` 与 `GET /api/v3/care/events?subject_id|room|bed|limit` 路由（需要 admin cookie）
  - `build_chat_context_v3` 增加 `modalities.care_events` 与 `policy.allowed_sections` 中的 `care_events`
- `project2_task/gateway/README.md` — 反映新的鉴权、会话、care_event 规范

### esp32/testpro4/

- `main/CMakeLists.txt` — 增加 `esp_wifi / esp_netif / esp_event / esp_timer / mqtt / mbedtls / lwip` 依赖和新的 .cpp
- `main/idf_component.yml` — 增加 `espressif/mqtt` 组件
- `main/protocol_packet.{h,cpp}` — 抽出 USB packet 常量、CRC16-CCITT、pack helper
- `main/device_config.{h,cpp}` — NVS 加载/校验/打印/帮助；`device_config_topic_for(stream, ...)` 输出 `{room_lc}{bed_lc}{suffix}` 主题
- `main/mqtt_payload.{h,cpp}` — 基于 `mbedtls/base64.h` 的 `{"payload_b64": "..."}` JSON 构造
- `main/maixsense_parser.{h,cpp}` — 抽出 ToF 帧解析（处理噪声/分块/坏尾）
- `main/wifi_mqtt.{h,cpp}` — Wi-Fi STA + 巴法云 MQTT 客户端；用 ESP-IDF v6 新 API（`broker.address.*` / `credentials.*` / `session.*` + `esp_mqtt_client_register_event`）
- `main/main.cpp` — 重写：保持 USB CDC 行为 + 并行 MQTT 发布；启动时若 `device_config_network_ready()` 才拉起 Wi-Fi/MQTT；配置控制台单独留在 main 中

## 架构调整与模块设计

按 `gateway/README.md` 的“放代码原则”继续执行，本次新引入：

- **care_events.py**：与 `subjects.py / sensor_store.py` 同级，作为 `care_event` 的单一职责模块。
  - `gateway.py` 只放路由 glue
  - DB schema 迁移从 `db.py` 委托给 `care_events._migrate_care_events_table`（单点迁移）
- **session_is_authenticated** 是统一的“会话可信”判定入口，被 `build_chat_context_v3` 使用，并作为后续 v3 API 的标准。
- **本地服务白名单** `_LOCAL_SERVICE_PATHS` 列出允许 loopback 无 cookie 访问的接口，避免“`if is_local` 全放行”的旧逻辑。
- ESP32 固件按 `protocol_packet / device_config / mqtt_payload / maixsense_parser / wifi_mqtt / main` 拆分，`main.cpp` 只剩启动 glue 与 ToF/MLX 两个 stream task，不再堆协议逻辑。

## 安全边界及鉴权设计

1. **管理员密码**：PBKDF2-HMAC-SHA256，200 000 轮；每个账号 16 字节随机盐；DB 存 `salt + digest` 16 进制。**任何情况下都不再落明文**。
2. **Cookie**：随机 32 字节 `secrets.token_urlsafe(32)`；浏览器保存为 `HttpOnly; SameSite=Lax` Cookie；DB 只存 `sha256(token)` 哈希。
3. **session 校验**：`get_admin_http_session(token)` 严格按 `token_hash` 匹配 + 检查 `expires_ts`；不通过则返回 `None`，调用方返回 401。**关键修复**——之前“忽略 token 取任何活动会话”的实现等价于任何人都能拿到管理权限。
4. **路径白名单**：`_LOCAL_SERVICE_PATHS = ("/api/v2/", "/api/esp/", "/api/v3/context/chat", "/api/v3/identity/gallery", "/api/v3/identity/match", "/api/v3/vision/observation")`；除此之外 `/api/*` 在 ADMIN_AUTH_ENABLED 时必须携带有效 Cookie。
5. **`/api/v3/credentials?include_template=1`** 远程仍然 403，只允许本机服务调用。
6. **v3 会话语义**：`session_is_authenticated` 同时要求
   - `identity_state` 非 `unknown`/空
   - `assurance_level` 非 `none`/空
   - `expires_ts` 未过期
   - `actor_subject_id` 非空
   - 配合 `actor_can_access_target` 限制 `patient` 只能看自己，`staff/admin` 可看任意目标。
7. **审计字段**：`care_event` 的 `created_by` 在 admin 写入时自动填入当前 admin subject_id，便于追溯。

## 睡眠 CSV 无 room/bed 时的特殊处理

按 `ONBOARDING_TODO.md` 的规范在 `gateway/sleep_importer.py` 中实现：

- 行带 `room/bed`：只写入对应床位（大小写不敏感，会按 BEDS 列表归一化）。
- 行不带 `room/bed`：
  - `SLEEP_IMPORT_DEFAULT_ROOM` / `SLEEP_IMPORT_DEFAULT_BED` 设置时，写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）时，写入第一个配置床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` 时跳过。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all` 时仅作调试模式写入所有床位。
- 同一 CSV 内可同时出现显式 `room/bed` 行与无归属行；策略只作用于无归属行，不会污染显式行（实现按行在 `row_targets()` 中判断）。

## care_event 实现细节

- **路由**：
  - `POST /api/v3/care/events`（body：`event_id / subject_id / room / bed / kind / title / content / severity / source / created_by / ts`；要求 admin Cookie）
  - `GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=...`（要求 admin Cookie；room/bed 不区分大小写匹配；默认 limit=50，最大 200）
- **DB 迁移**：
  - `care_events._migrate_care_events_table()` 每次 `init_management_db()` 都会跑：
    1. `CREATE TABLE IF NOT EXISTS care_events` 完整 schema（含 `severity/source/created_by/ts`）
    2. `PRAGMA table_info(care_events)` 查缺失列
    3. 对缺失列执行 `ALTER TABLE care_events ADD COLUMN ... DEFAULT 'info'/'manual'/''/0`
    4. 对旧行执行 `UPDATE care_events SET ts = COALESCE(NULLIF(ts,0), created_ts) WHERE ts = 0`
    5. 重建索引 `idx_care_events_subject (subject_id, ts DESC) / idx_care_events_room_bed (room, bed, ts DESC) / idx_care_events_ts (ts DESC)`
- **大小写归一化**：写时 `normalize_room/normalize_bed`（uppercase）；查时 `WHERE UPPER(room) = ? AND UPPER(bed) = ?`。
- **聊天上下文注入**：`build_care_events_context(subject_id)` 在 `build_chat_context_v3` 中被调用，仅当 `policy.allowed=True` 时填入 `modalities.care_events`（含 `items` 与 `brief`），并加入 `policy.allowed_sections`。

## ESP32-S3 固件接口对齐说明

按 `reference/espidf_protocol_contract.md` 落实 `project2_task/esp32/testpro4`：

- **NVS 配置**：`device_config.cpp` 读 `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / room / bed / device_id` + `bemfa_port`；`CFG?/CFGSET/CFGRESET/REBOOT` 串口命令保留。
- **Topic 命名**：`device_config_topic_for(stream, ...)` 输出 `{room_lc}{bed_lc}{suffix}`，suffix 是 `tof1/tof2/mlx1/mlx2`。
- **payload**：调用 `mqtt_payload_build_b64_json(payload, len)` 在堆上构造 `{"payload_b64": "<base64>"}`，缓冲按 `((len+2)/3)*4 + 32 + NUL` 计算（足够 10 KiB MaixSense 帧），避免栈溢出。
- **MQTT 客户端**：使用 ESP-IDF v6 `espressif/mqtt ~1.0.0` 组件；新 API `esp_mqtt_client_config_t{ broker.address.{hostname,port,transport=TCP}, credentials.{client_id,username,authentication.password=uid}, session.{keepalive=60,disable_clean_session=false} }`；事件通过 `esp_mqtt_client_register_event(client, MQTT_EVENT_ANY, handler, NULL)` 注册，handler 仅关心 `MQTT_EVENT_CONNECTED/DISCONNECTED`。
- **Wi-Fi STA**：`esp_netif_init + esp_event_loop_create_default + esp_netif_create_default_wifi_sta + esp_wifi_init/set_mode(STA)/set_config/start`，事件订阅 `WIFI_EVENT_STA_START/DISCONNECTED` + `IP_EVENT_STA_GOT_IP`；断线自动重连。
- **协议保留**：
  - USB packet `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`
  - CRC16-CCITT（init=0xFFFF, poly=0x1021）只覆盖 PAYLOAD
  - LEN/CRC 小端序
  - ToF payload 仍是完整 MaixSense 帧（带 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`），**不截断 10000B 图像区**。
- **并发回传**：`emit_tof_frame` / `emit_mlx_frame` 同时向 USB CDC 与 MQTT 发布；MQTT publish 失败不阻塞 stream task。
- **依赖**：`CMakeLists.txt` REQUIRES 加上 `esp_wifi / esp_netif / esp_event / esp_timer / mqtt / mbedtls / lwip`；`idf_component.yml` 加 `espressif/mqtt` 与 `espressif/esp_tinyusb`。

## 本地测试与编译验证结果

### `python tests\run_public_tests.py project2_task`

```text
[public] running test_compile.py
[public] running test_functional_smoke.py
[public] running test_refactored_features.py
[public] running test_smoke_gateway.py
[public] all public tests passed
```

### `python tools\run_debug_probe.py project2_task`

```text
[probe:ok] admin setup returns 200
[probe:ok] management API rejects missing cookie
[probe:ok] management API rejects forged cookie
[probe:ok] management API accepts valid cookie
[probe:ok] unknown identity session is denied
[probe:ok] expired session is denied
[probe:ok] care_event write rejects missing admin cookie
[probe:ok] care_event normalizes room/bed for create and query
[probe:Warning] Voice/assistant path: sensitive context may be denied without session_id ...
[probe:info] ESP32-S3: run tools/run_espidf_build.py after firmware changes.
[probe] all visible diagnostic checks passed
```

> Voice Warning 是预期提示：`voice/voice_assistant_integrated.py` 实际通过
> `build_gateway_context_params(session_id=...)` 显式携带会话，紧缩后
> 仍能正常取上下文。无需进一步修改。

### `python tools\run_espidf_build.py project2_task`

实际在本机 `E:\esp` (ESP-IDF v6.0.1) 跑通：

```text
[espidf] mirror            = copied=14 kept=26 removed=2479
-- Components: ... main espressif__esp_tinyusb espressif__mqtt ...
[5/8] Linking CXX executable stdpro.elf
[6/8] Generating binary image from built executable
esptool v5.3.0
Creating ESP32-S3 image...
Successfully created ESP32-S3 image.
Generated E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
stdpro.bin binary size 0xefee0 bytes. Smallest app partition is 0x100000 bytes. 0x10120 bytes (6%) free.
[espidf] output_bin        = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
[espidf] Build finished successfully.
```

修复过程中遇到并已解决：

1. `json` 组件在 IDF v6 中已被并入 `mbedtls/json`，从 `CMakeLists.txt` REQUIRES 移除。
2. ESP-IDF v6 移除了旧的 `mqtt_cfg.host/port/...` 字段；改为 `mqtt_cfg.broker.address.{hostname,port,transport}/credentials.{client_id,username,authentication.password}/session.{keepalive,...}`，事件通过 `esp_mqtt_client_register_event` 注册。
3. `ESP_ERR_INVALID_LENGTH` 在 NVS 头里是 `ESP_ERR_NVS_INVALID_LENGTH`，已修正。
4. `snprintf` 在 gcc 14 + `-Werror=format-truncation` 下报 Wi-Fi SSID/密码截断错误，改用 `strncpy` + 显式置 NUL。

## 未验证的残留技术债与风险

- **未跑硬件验证**：本次仅在 Windows EIM ESP-IDF v6.0.1 下完成固件编译（`idf.py build`）；未做 `idf.py flash` / `idf.py monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电冷启动等待、MLX90640 实机读数。**首次板端联调前请按 `esp32/testpro4/README.md` + `NVS_CONFIG.md` 写入 NVS 后再烧录**。
- **依赖锁定文件**：`build/dependencies.lock` 由首次构建生成；后续 `idf.py build` 增量构建如果换了 ESP-IDF 版本需要 `python run_espidf_build.py --clean-copy` 重新生成。
- **NVS 上线加密 / Flash 加密**：当前为普通 NVS。生产部署建议按 `esp32/NVS_CONFIG.md` 安全说明开启 NVS 加密、Flash 加密、设备唯一 token。
- **voice 路径**：当前的 voice warning 仍会触发（因为 v3 上下文在缺 session_id 时会拒绝），但 voice 模块已显式带 `VOICE_SESSION_ID`。如果未来 voice 的回放/重新识别的会话获取路径变化，需要复查 `voice/voice_assistant_integrated.py:fetch_gateway_chat_context`。
- **`mlx90640` component 本地化**：当前 `components/mlx90640/` 是项目自带的本地组件；如果该组件未随提交一起进入 PR，CI 拉取会失败。本次未触碰该组件，但已确认本机 `idf.py build` 走本地路径。
- **后端鉴权开关的兼容性**：当 `ADMIN_AUTH_ENABLED=0`（旧 CI / demo）时，`_admin_session()` 返回 `{"username": "disabled", "subject_id": DEFAULT_ADMIN_SUBJECT_ID}`，所有受保护接口会被放行；这是兼容旧行为的实现，**不是**修复的回归。
- **测试盲区**：现有公开测试不覆盖 `care_event` 旧表迁移到 13 列之后的 SQL 完整性；只验证了基本 create/list/normalize，跨版本 SQLite 行为差异需要更广的测试矩阵。
- **历史 plaintext admin 密码**：旧 SQLite 中可能存在历史明文/低强度 admin 密码，**本次迁移不主动 rehash**；下次登录失败后由 admin 通过 `CFGSET` / `admin/setup` 流程重新创建账户会更安全。
