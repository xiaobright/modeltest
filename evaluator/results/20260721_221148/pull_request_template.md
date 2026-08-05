# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前先跑了两轮 baseline：

### `python tests\run_public_tests.py project2_task`

```text
test_compile.py                 → 1/1 OK
test_functional_smoke.py        → 2/2 OK
test_refactored_features.py     → 3/3 OK
test_smoke_gateway.py           → 1/1 OK
[public] all public tests passed
```

公共测试通过，但**它们不覆盖安全/迁移/上下文策略**，因此单独跑 debug probe 才是这次任务真正暴露问题的入口。

### `python tools\run_debug_probe.py project2_task`

```text
[probe:ok] admin setup returns 200
[probe:FAIL] management API rejects missing cookie       status=200
[probe:FAIL] management API rejects forged cookie        status=200
[probe:ok] management API accepts valid cookie
[probe:FAIL] unknown identity session is denied          policy.allowed=True
[probe:FAIL] expired session is denied                   policy.allowed=True
[probe:FAIL] care_event write rejects missing admin cookie  status=404
[probe:FAIL] care_event normalizes room/bed for create and query  rows=[]
[probe:Warning] voice module current-session fetch
[probe] failures=6
```

可看到四类症状：管理 API 不查 Cookie、上下文策略漏放行、care_event 路由缺失 + room/bed 不归一、voice/助手提示隐式会话问题。

---

## 修改的文件列表

### Gateway (Python)

- `gateway/auth.py`：`_password_hash` 始终生成随机盐 + PBKDF2-HMAC-SHA256（20 万次）；`admin_account_exists` 改为查 DB；`get_admin_http_session` 按 `token_hash` 精确查找而非“任一活动会话”。
- `gateway/db.py`：`care_events` 表补齐 `severity / source / created_by / ts` 列；`init_management_db` 在执行 `CREATE TABLE IF NOT EXISTS` 后再用 `PRAGMA table_info` + `ALTER TABLE` 对旧表补列；旧行 `ts=0` 自动回填 `created_ts`；索引只在新结构上重建。
- `gateway/care_events.py`：完整重写为单职责模块。`create_care_event` 严格按 v3 契约做 room/bed 归一、severity/source 白名单、ts 兜底；`list_care_events` 按 `ts/created_ts` 倒序并支持 `limit`；`build_care_events_context` 输出 v3 context 摘要。
- `gateway/gateway.py`：`session_is_authenticated` 按 v3 契约（identity_state≠unknown、assurance_level≠none、expires_ts 未过期、actor_subject_id 存在）四道检查；`_authorized_for_api` 改为“管理员会话 OR (本机 + 路径白名单)”，堵住本地全放行的口子；新增 `POST/GET /api/v3/care/events` 路由 glue；`/api/v3/context/chat` 在授权通过时把 `care_events` 摘要放进 `modalities` 和 `brief`；`do_POST` 把 `/api/v3/admin/logout` 提前到 JSON 解析之前，避免空 body 被 400 误拒。
- `gateway/sleep_importer.py`：`row_targets` 改回“`first` ⇒ 第一个配置床位”（原代码错误地用了 `beds[-1]`）；同一 CSV 内可同时处理有/无归属行。
- `gateway/README.md`：更新模块职责、admin/session 安全策略、care_event 章节。

### Voice

- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session()`，在没有显式 `VOICE_SESSION_ID` 时主动拉取 `/api/v3/session/current` 注入到 `/api/v3/context/chat` 的查询里，避免收紧策略后本地助手被静默 ambient session 卡死。

### ESP32-S3 (C++)

按“职责拆分”重构 `esp32/testpro4/main/`，新增：

- `main/protocol_packet.{h,cpp}`：USB 包格式常量、`protocol_packet_crc16`、`protocol_packet_build`、stream 名查表。
- `main/maixsense_parser.{h,cpp}`：流式 MaixSense 帧解析，容忍噪声字节、分块、坏尾字节、异常长度。
- `main/device_config.{h,cpp}`：NVS 读/写 `ssid/password/uid/host/port/room/bed/device_id`；`device_config_topic(stream)` 输出小写 `{room}{bed}{stream}`。
- `main/mqtt_payload.{h,cpp}`：用 `mbedtls/base64.h` 生成 `{"payload_b64": "..."}`，并根据 `room+bed` 拼接 `topic_for(stream)`。
- `main/wifi_mqtt.{h,cpp}`：Wi-Fi STA + MQTT 客户端生命周期。事件组 `WIFI_CONNECTED_BIT` / `MQTT_CONNECTED_BIT`；`wifi_mqtt_publish()` 在连接未建立时安全降级为 no-op。

`main/main.cpp` 现在只剩 glue：NVS/USB/ToF 初始化、MLX 启动、串口控制台解析（`CFG? / CFGSET / CFGRESET / REBOOT`）、按 stream 把 USB 包和 MQTT publish 并行发出。

`main/CMakeLists.txt`：`REQUIRES` 增补 `esp_wifi esp_netif esp_event esp_timer lwip mqtt mbedtls`；新加 `protocol_packet.cpp / maixsense_parser.cpp / device_config.cpp / mqtt_payload.cpp / wifi_mqtt.cpp`。

`main/idf_component.yml`：`espressif/mqtt: "^1.0.0"`（v6.0.1 的 component-manager 实际可用版本是 1.x，不是 5.x）。

---

## 架构调整与模块设计

- `gateway/gateway.py` 不再存放任何业务逻辑，只做 HTTP 路由 glue。
- 新增 `gateway/care_events.py` 单职责模块；`build_chat_context_v3` 通过 `build_care_events_context(subject_id)` 拉数据。
- ESP32 固件拆为 `protocol_packet / maixsense_parser / device_config / mqtt_payload / wifi_mqtt` 五个模块；`main.cpp` 不再写死任何 NVS / 协议 / topic 字符串。
- 数据库 schema 调整采用“`CREATE TABLE IF NOT EXISTS` + `PRAGMA table_info` + `ALTER TABLE` 补列”的双层迁移策略，老数据不丢；`ts=0` 行回填 `created_ts`。
- 睡眠 CSV 导入改为**按行**处理：显式 `room/bed` 行继续走显式映射；无归属行才按 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 或 `SLEEP_IMPORT_UNSCOPED_POLICY` 决定归宿。

---

## 安全边界及鉴权设计

- **密码**：PBKDF2-HMAC-SHA256，16 字节随机盐，20 万次迭代。盐 + 摘要分两列存 `admin_accounts`；明文密码不留盘。
- **Cookie**：`secrets.token_urlsafe(32)` 随机 token 写入 `Set-Cookie`；DB 仅存 `SHA-256(token)`；服务端严格按 `token_hash` 查表，找不到即视为未登录。
- **会话过期**：默认 8 小时；TTL 由 `ADMIN_SESSION_TTL_MS` 控制；`expires_ts < now()` 一律视为未登录。
- **管理 API 鉴权**：`_authorized_for_api(path)` 改为 `admin_session OR (loopback AND path in worker_allowlist)`。`/api/v3/subjects`、`/api/v3/care/events` (POST) 等管理类**不再接受本机绕过**。`/api/v3/care/events` (GET) 同时校验本机调用方的 session 满足 `session_is_authenticated`。
- **上下文授权**：`session_is_authenticated` 严格四道检查（`identity_state != unknown`、`assurance_level != none`、`expires_ts > now()`、`actor_subject_id` 存在）；任何一条不满足即视为未认证；`build_chat_context_v3` 的 `policy.allowed` 因此能正确反映 unknown / expired / no-actor 的请求。
- **Voice/助手兜底**：在没有显式 `VOICE_SESSION_ID` 时主动拉取 `/api/v3/session/current`，把“ambient session 漏数据”收敛为“显式带最新识别会话”。`probe:Warning` 提示因 voice 模块已经引用 `session/current` 切换为 `probe:info`，不再警告。
- **未授权管理 API 行为**：返回 `{"error": "unauthorized", "path": ...}` 与 HTTP 401，浏览器侧会回到 setup/auth 页面。

---

## 睡眠 CSV 无 room/bed 时的特殊处理

- 同一 CSV 内可同时出现“有归属行”和“无归属行”，策略**只对无归属行生效**。
- `row_targets` 现在严格：
  - 行带 `room/bed` → 只写入对应床位（在配置中找 case-insensitive 匹配，命中就归一到大写）。
  - 行不带 `room/bed`：
    - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 设置 → 写指定床位。
    - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写**第一个**配置床位（修了原 `beds[-1]` 错位 bug）。
    - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过。
    - `=all` → 仅作为显式调试模式，按 `BEDS` 全量广播。
  - 未知策略值 → 安全起见返回空（不导入）。
- `test_refactored_features` 用 `SLEEP_IMPORT_UNSCOPED_POLICY=first` 跑无归属行，最终命中 `R1203-B1`（即 `BEDS[0]`），证明 first 语义正确。

---

## care_event 实现细节

### Schema (db.py)

```sql
CREATE TABLE care_events (
    event_id    TEXT PRIMARY KEY,
    subject_id  TEXT NOT NULL DEFAULT '',
    room        TEXT NOT NULL DEFAULT '',
    bed         TEXT NOT NULL DEFAULT '',
    kind        TEXT NOT NULL DEFAULT 'note',
    title       TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL DEFAULT 'info',
    source      TEXT NOT NULL DEFAULT 'manual',
    created_by  TEXT NOT NULL DEFAULT '',
    ts          INTEGER NOT NULL DEFAULT 0,
    created_ts  INTEGER NOT NULL DEFAULT 0,
    updated_ts  INTEGER NOT NULL DEFAULT 0
);
```

迁移路径：`CREATE TABLE IF NOT EXISTS` 之后用 `PRAGMA table_info` 找出缺失列，逐个 `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT <safe>`；再用 `UPDATE … SET ts = created_ts WHERE ts = 0` 把旧行时间戳回填，最后重建索引。本任务下用一份手工构造的旧表跑过端到端验证，列补齐成功、旧行 `event_id='legacy1'` 保留。

### API

- `POST /api/v3/care/events` — 需要管理员登录；body 直接喂给 `create_care_event`，自动归一 room/bed / severity / source / ts。
- `GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=50` — 管理员任意查；本机调用方必须 `session_is_authenticated(session)` 且 `actor_can_access_target(actor, target)`，否则 403。
- `list_care_events(...)` 按 `COALESCE(NULLIF(ts, 0), created_ts) DESC` 排序，`limit` 钳位在 `[1, 500]`。

### Context 集成

`build_chat_context_v3` 在 `allowed` 为真且 `target_subject_id` 非空时调用 `build_care_events_context(subject_id, limit=5)`，把 5 条最近事件放进 `modalities.care_events` 和 `brief`。`policy.allowed_sections` 因此新增 `"care_events"`。

---

## ESP32-S3 固件接口对齐说明

### 协议（USB）

保持原契约不变：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`，CRC16-CCITT（init 0xFFFF，poly 0x1021）只覆盖 payload，LEN/CRC 小端序。`protocol_packet_build()` 提供统一构造函数。

### MQTT

- Topic 命名：`{room}{bed}{stream}`（全小写拼接）。`device_config_topic("tof1", ...)` 产出 e.g. `r1203b1tof1`。
- JSON：`{"payload_b64": "<base64>"}`。`mqtt_payload_build` 用 `mbedtls/base64_encode` 把 raw payload 编成 base64，包成 JSON；足够大的栈缓冲（`json_buf[16384]`）容纳 ~10 KiB ToF raw payload + base64 膨胀。
- `mirror_tof_payload()` 在 USB CDC 写出之后调用 `mqtt_mirror_payload("tof1"/"tof2", ...)`，**只发 raw 帧**（不是 framed USB packet）。MLX 任务同样在 CDC 输出后调用 `mqtt_mirror_payload("mlx1"/"mlx2", ...)`。

### NVS

`device_config_*` API 全部从 NVS 读 / 写 `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`。`device_config_is_complete()` 要求同时具备 `ssid + uid + room + bed`。Console 命令：`CFG? / CFGSET / CFGRESET / REBOOT / CFGHELP` 在 `main.cpp` 维护。CFG 输出额外打印 4 个 topic 便于现场核对。

### Wi-Fi + MQTT 客户端

- `wifi_mqtt_start_wifi(ssid, pass)`：初始化 `esp_netif` / `esp_event_loop`，注册 `WIFI_EVENT` / `IP_EVENT` 处理器，启动 STA。
- `wifi_mqtt_start(broker)`：初始化 ESP-MQTT 客户端，配置 `hostname / port / transport=TCP / client_id / username=uid`；事件订阅 `MQTT_EVENT_ANY`；`connected`/`disconnected` 通过 `xEventGroupSetBits/ClearBits` 同步。
- `wifi_mqtt_publish`：仅在事件组里 `MQTT_CONNECTED_BIT` 置位时调用 `esp_mqtt_client_publish(..., qos=0, retain=0)`；未连上时直接返回 false，不阻塞采集循环。

### Module 边界

- `protocol_packet` / `maixsense_parser` / `device_config` / `mqtt_payload` / `wifi_mqtt` 五个文件**互不耦合**，每个有独立头文件；`main.cpp` 只调用它们的 public API。

---

## 本地测试与编译验证结果

### `python tests\run_public_tests.py project2_task`

```text
test_compile.py                 → 1/1 OK
test_functional_smoke.py        → 2/2 OK
test_refactored_features.py     → 3/3 OK
test_smoke_gateway.py           → 1/1 OK
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
[probe:info] voice module appears to reference current-session fetch
[probe:info] ESP32-S3: run tools/run_espidf_build.py after firmware changes.
[probe] all visible diagnostic checks passed
```

### `python tools\run_espidf_build.py project2_task`

构建成功，最终输出：

```text
[espidf] source            = E:\Desktop\mytests\modeltest\workspace\project2_task
[espidf] build_copy        = E:\esp\builds\modeltest\project2_task
[espidf] firmware_copy     = E:\esp\builds\modeltest\project2_task\esp32\testpro4
[espidf] activation_script = E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1
[espidf] target            = esp32s3
[espidf] jobs              = 32
[espidf] clean_copy        = False
[espidf] set_target        = False
[espidf] mirror            = copied=13 kept=27 removed=0
[espidf] note=Windows EIM incremental build; no Docker, WSL, flash, or monitor
...
[1/8] Performing build step for 'bootloader'
[3/8] Completed 'bootloader'
[5/8] Linking CXX executable stdpro.elf
[6/8] Generating binary image from built executable
esptool v5.3.0
Creating ESP32-S3 image...
Merged 3 ELF sections.
Successfully created ESP32-S3 image.
Generated E:/esp/builds/modeltest/project2_task/esp32/testpro4/build/stdpro.bin
[7/8] partition check: stdpro.bin 0xf0300 bytes, 0xfd00 bytes (6%) free
[espidf] output_bin        = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
[espidf] Build finished successfully.
```

构建链路上踩到过的非致命问题（已修复）：

1. `espressif/mqtt` 版本约束写成 `^5.0.0` 时 Component Manager 找不到匹配；该组件在 IDF v6.0.1 实际可用版本是 `^1.0.0`，已在 `main/idf_component.yml` 修正。
2. MQTT 客户端 `broker.address.host` 字段在 managed-component 版本里改名 `hostname`；`esp_mqtt_client_publish` 的 `data` 参数是 `const char *`；`esp_mqtt_client_register_event` 的 `event` 参数是 `esp_mqtt_event_id_t`。这三点已在 `main/wifi_mqtt.cpp` 修正。

---

## 未验证的残留技术债与风险

- **没有真机/USB 流量验证**：按任务约束本机只做 `idf.py build`，没有 `idf.py flash / idf.py monitor`，也未连真实 MaixSense / MLX90640 板子。Wi-Fi 实际握手、MQTT 实际与 bemfa.com 9501 建链、ToF 真实 UART 流，都只是代码层面的完成。
- **Paho 兼容层未做**：本固件用 ESP-IDF 自带 MQTT 客户端走 TCP/MQTT，与 bemfa.com 的标准 MQTT broker 通信；如果生产环境 bemfa 实际期望 HTTP TCP bridge（gateway/bed_config.py 的 `BEMFA_TCP_PORT=8344`），那 ESP 端与 gateway 端需要再加一层桥接。目前 `gateway.bemfa_tcp_sub_loop()` 继续走 TCP 订阅，ESP 端走 MQTT publish，两端在协议上各自独立。
- **base64 JSON 缓冲静态分配 16 KiB**：当前 `mqtt_mirror_payload` 使用栈上的 `char json_buf[16384]`，可被 `ToF 10022B → b64 ≈ 13364 chars + JSON overhead` 覆盖，但极端情况下（payload 异常超长）会失败；目前已知 ToF 帧是固定 ~10000 字节，没看到会越界，但生产前可以改成 `malloc` 或 `freertos heap_caps_calloc`。
- **Wi-Fi 重连日志噪音**：`wifi_event_handler` 在 `WIFI_EVENT_STA_DISCONNECTED` 直接 `esp_wifi_connect()`，可能在 NVS 里没有 ssid/password 时仍然不断尝试。启动时已经校验 `device_config_is_complete()`，但如果用户在 `REBOOT` 前清掉 ssid 仍会触发重连。生产前建议加最大重试间隔。
- **voice 模块 fetch_current_session 失败时的 fallback**：当 gateway 不可达时，voice 会回退到“ambient session”路径（`get_current_session()`），新收紧的策略会让这条路径在 ambient session 不满足四道检查时拒绝。这意味着语音助手在 gateway 离线 / 启动顺序错误时不会拿到 context。生产前可加 retry 与本地缓存。
- **未做长时间压测**：基线 CDC 流量 ~160 KB/s 加上 MQTT 上报后是否会触发 PSRAM / Wi-Fi 带宽上限未实测；MLX + ToF + 4 个 topic 同时上报在 2-4 Hz 下粗算 < 100 KB/s，应可承受，但建议在板端长跑 24h+ 验证。
- **未触达的 USB CDC + MQTT 同步一致性**：当前设计是 USB 与 MQTT 各自独立发送，MQTT 失败不会重传但 USB 成功；如果你需要两者保证至少一次同步（MQTT 失败要缓存/重试），需要再加一个轻量 outbound queue；本次没做。
- **legacy care_events 测试只覆盖了一行旧数据**：迁移路径已在隔离目录手写一个旧表跑过（见 `tests` 之外的临时脚本），但 `data/legacy_sample.db` 中可能还有别的未知列被历史业务写入过；生产前最好跑一次真实的 legacy DB 迁移。
