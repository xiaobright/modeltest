# Pull Request 提测说明 (Pull Request Template)

Sprint 目标：管理鉴权闭环、v3 授权上下文收紧、care_event 全链路、睡眠 CSV 按行归属、ESP32-S3 testpro4 Wi-Fi+MQTT 回传恢复。以下内容与实际 diff 一一对应。

## 初始自检诊断

修改前在 workspace 根目录运行：

- `python tests\run_public_tests.py project2_task`
  - 结果：4 个公开测试文件全部通过（公开冒烟不覆盖安全/迁移正确性）。
  - 注意到 `[SLEEP-IMPORT] sleep_epoch rows=1 bed=R1203-B2`：`first` 策略把无归属行导入了**最后一个**床位（B2），暴露 `beds[-1]` 笔误。
- `python tools\run_debug_probe.py project2_task`
  - 结果：`failures=6`：
    1. `management API rejects missing cookie`：无 Cookie 本机请求 `/api/v3/subjects` 返回 200（应 401）。
    2. `management API rejects forged cookie`：伪造 Cookie 也返回 200。
    3. `unknown identity session is denied`：`identity_state=unknown` 的 session 仍 `allowed=true`。
    4. `expired session is denied`：`expires_ts` 已过期的 session 仍 `allowed=true`。
    5. `care_event write rejects missing admin cookie`：`POST /api/v3/care/events` 返回 404（路由未接）。
    6. `care_event normalizes room/bed for create and query`：小写写入后大写查询查不到（rows=[]）。
  - 另有 `[probe:Warning]`：voice 模块无 `session/current` 引用，收紧后本地助手可能取不到上下文。

根因排查补充（读代码确认）：

- `auth.py::_password_hash(password, "")` 空盐时直接返回明文密码当哈希 → **管理员密码明文入库**。
- `auth.py::admin_account_exists()` 恒返回 False → setup 可被重复调用。
- `auth.py::get_admin_http_session()` 的 SQL 没有按 `token_hash` 过滤（`LIMIT 1` 取任意活跃会话）→ 任意/伪造 Cookie 均可通过。
- `gateway.py::_authorized_for_api()` 对所有 loopback 请求放行 → 本机无 Cookie 也能访问全部管理 API。
- `gateway.py::session_is_authenticated()` 把 `identity_state=unknown` 当已认证，且不校验 `expires_ts` / `actor_subject_id`。
- `gateway.py::actor_can_access_target()` 无 actor 时直接放行。
- `gateway.py::build_chat_context_v3()` 无 `session_id` 时静默回退 `get_current_session()`（ambient session 漏数据风险）。
- `db.py`/`care_events.py` 的 care_events 表缺 `severity/source/created_by/ts`，无旧表迁移，room/bed 不规范化，list 无 limit/排序不符契约。
- `gateway.py::_admin_session()` 在 `ADMIN_AUTH_ENABLED=0` 时引用未导入的 `DEFAULT_ADMIN_SUBJECT_ID`（潜在 NameError）。
- `maixsense parser` 在 `buffer_len==0` 时 `buffer_len - 1` 无符号下溢（越界扫描风险）。

## 修改的文件列表

Gateway / Python：

- `project2_task/gateway/auth.py`：PBKDF2 加盐哈希；`admin_account_exists` 查库；token 精确匹配 + 过期校验；旧明文账号登录时自动升级。
- `project2_task/gateway/db.py`：care_events 全字段建表 + `ensure_care_events_schema()` 旧表迁移（PRAGMA table_info + ALTER TABLE + ts 回填）；新增 `idx_care_events_ts`。
- `project2_task/gateway/care_events.py`：完整重写 CRUD（room/bed 规范化、severity/source/created_by/ts、limit、`ts/created_ts` 倒序）与 `build_care_events_context()`。
- `project2_task/gateway/gateway.py`：鉴权白名单收紧、session/actor 语义修复、去 ambient session、care_event 路由、context `modalities.care_events`、补 `DEFAULT_ADMIN_SUBJECT_ID` 导入。
- `project2_task/gateway/sleep_importer.py`：`first` 策略 `beds[-1]` → `beds[0]`。
- `project2_task/voice/voice_assistant_integrated.py`：新增 `fetch_current_session()` / `resolve_session_id()`，上下文请求显式携带 `session_id`。
- `project2_task/gateway/admin.html`：context 预览先取 `/api/v3/session/current` 再带 `session_id` 查询。

ESP32-S3 固件（`project2_task/esp32/testpro4/`）：

- `main/protocol_packet.{h,cpp}`（新增）：USB packet 常量、CRC16-CCITT、打包/校验辅助。
- `main/maixsense_parser.{h,cpp}`（新增）：MaixSense 字节流解析器（修复空缓冲下溢；容错噪声/分块/坏尾/异常长度/半帧）。
- `main/device_config.{h,cpp}`（新增）：NVS 读写、`usb_ready`/`network_ready` 校验、topic 规范化。
- `main/mqtt_payload.{h,cpp}`（新增）：`{"payload_b64": ...}` JSON 堆上构造（mbedtls base64）。
- `main/main.cpp`：接入上述模块；新增 Wi-Fi STA + 巴法云 MQTT 客户端与并行发布 glue。
- `main/CMakeLists.txt`：新增源文件；REQUIRES 补 `esp_wifi esp_netif esp_event lwip mqtt mbedtls`。
- `main/idf_component.yml`：新增 `espressif/mqtt`（IDF v6 不再内置 esp-mqtt）。

文档：

- `project2_task/README.md`、`gateway/README.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`esp32/testpro4/QUICKSTART.md`、`esp32/testpro4/CHANGELOG.md`、`RK3588_TEST_GUIDE.md`、`CHANGES.md`：同步鉴权边界、session 语义、care_event API、睡眠策略与固件回传状态。
- 本文件 `PULL_REQUEST_TEMPLATE.md`。

## 架构调整与模块设计

保持既有模块边界，未把逻辑塞回 `gateway.py`：

- schema 与迁移归 `db.py`（`ensure_care_events_schema` 供 `init_management_db` 与 `care_events.init_care_events_table` 复用）。
- care_event CRUD 与 context 摘要归 `care_events.py`；`gateway.py` 只加两条路由 glue 和 context 聚合调用。
- 密码/Token 逻辑全部在 `auth.py`；HTTP 层只调用 `get_admin_http_session()`。
- 固件按交接建议拆为 protocol_packet / maixsense_parser / device_config / mqtt_payload 四个模块，`main.cpp` 只保留 ESP-IDF 初始化、任务创建、硬件访问和 glue。

## 安全边界及鉴权设计

- 密码：PBKDF2-HMAC-SHA256，16 字节随机盐，200,000 轮；不存明文。历史缺陷产生的“空盐+明文”行在下次成功登录时用 `hmac.compare_digest` 验证后自动重哈希（保留旧账号数据）。
- Cookie：只下发 `secrets.token_urlsafe(32)` 随机 token（HttpOnly + SameSite=Lax）；库中只存 SHA-256(token)；校验必须 `token_hash` 精确匹配且 `expires_ts` 未过期，伪造/过期一律 401；logout 删除记录。
- 管理 API：`_authorized_for_api` = 有效管理员会话，或（loopback 且路径在服务白名单）。白名单仅 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`——保证 posture/vision/voice worker 本机可用；subjects/assignments/memories/credentials/sessions/care events 等管理 API 即使本机也要 Cookie。
- 模板零泄漏：`/api/v3/identity/gallery` 与 `credentials?include_template=1` 保持本机-only（远程即使登录也 403）。
- v3 session 语义（与 `reference/api_contracts.md` 对齐）：`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 过期、缺 `actor_subject_id` 一律视为未认证；staff/admin 可看任意患者，patient 只能看自己；拒绝时 `target.patient/assignment` 与 `modalities.*`（含 memory、care_events）全部为空。
- ambient session：`/api/v3/context/chat` 不带 `session_id` 时不再静默用“当前会话”，按 `not_authenticated` 处理。voice 改为先 `GET /api/v3/session/current`（带 2s 缓存）再显式携带 `session_id`，probe 的 voice Warning 消除；admin 页 context 预览同样显式带 session。

## 睡眠 CSV 无 room/bed 时的特殊处理

`sleep_importer.row_targets()` 按**行**决策，同一 CSV 可混合显式行与无归属行：

1. 行带 room/bed：只写对应床位（与配置床位大小写不敏感匹配）。显式行永不受策略影响。
2. 行不带 room/bed：
   - 设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写指定床位；
   - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 写第一个配置床位（修复了原 `beds[-1]` 写到最后一个床位的 bug）；
   - `skip` → 跳过并打印 skipped 计数；
   - `all` → 广播到所有床位，仅显式调试用，不是默认；
   - 无法识别的策略值 → 安全起见不导入。

手动验证：双行混合 CSV（显式 R1203/B2 + 无归属行）在 `first` 下分别落 B2 / B1；`skip` 下显式行保留、无归属行丢弃。

## care_event 实现细节

- 表结构（`db.py`）：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`，索引 subject、room+bed、ts。
- 旧库迁移：旧表只有 9 列时，`PRAGMA table_info` 检测缺列并 `ALTER TABLE ADD COLUMN`（severity 默认 'info'、source 默认 'manual'、created_by 默认 ''、ts 默认 0 并用 `created_ts` 回填），旧行全部保留。已用手工构造的旧 schema 库验证。
- 写入：`event_id` 缺省自动生成 `care_xxx`；room/bed 统一 `normalize_room/bed`（大写）；severity 白名单（info/warning/critical，非法回落 info）；`ts` 缺省当前毫秒。要求至少 `subject_id` 或 `room+bed`。
- 查询：`subject_id` 或 `room+bed`（查询参数同样规范化，小写写入可被大写查询命中），`limit` 默认 50 上限 500，`ORDER BY ts DESC, created_ts DESC`。
- 路由：`POST /api/v3/care/events`、`GET /api/v3/care/events`，都在管理 API 门禁之后（需要管理员 Cookie，本机也不例外）。
- context：授权通过时 `build_care_events_context()` 把最近事件放入 `modalities.care_events`（items + brief），brief 同时并入 context `brief`；`allowed_sections` 增加 `care_events`；未授权时为空。

## ESP32-S3 固件接口对齐说明

- **USB packet**（不变，与 gateway/collector 兼容）：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`；TYPE 0x01=MLX、0x02=ToF；CRC16-CCITT（init 0xFFFF, poly 0x1021）只覆盖 payload；LEN/CRC 小端。打包统一走 `protocol_packet`。
- **ToF payload**：保持完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHK][DD]`（≈10022B），未改为只发图像区，gateway/worker 契约不变。
- **NVS**：namespace `project2`，键 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；`CFGSET/CFG?/CFGRESET/REBOOT` 串口命令保留。`network_ready` 要求 ssid+uid+room+bed 齐全（密码可为空以支持开放网络），不齐全时降级为仅 USB CDC 并打印提示。
- **Wi-Fi + MQTT**：Wi-Fi STA（断线自动重连）；获取 IP 后启动 esp-mqtt 客户端，broker `bemfa.com:9501`（NVS 可覆盖），ClientID=巴法云 UID，keepalive 60s，自动重连。
- **topic**：`device_config_build_topic()` 生成小写 `{room}{bed}tof1/tof2/mlx1/mlx2`，与 `gateway/bed_config.py::topics_for()` 一致。
- **base64 payload**：MQTT JSON 为 `{"payload_b64":"..."}`，内容是原始 payload（ToF 完整原始帧 / MLX 768×float32），**不是**完整 USB packet。JSON 在堆上构造（完整 ToF JSON ≈13.4KB），MQTT 出站缓冲 20KB，避免了交接备注里提示的小固定缓冲截断问题。
- **并行回传**：`usb_send_tof_payload()` 尾部与 `mlx_sender_task` 每周期分别调用 `network_publish_sensor_payload()`；USB 未连接时 MQTT 照发，MQTT 未连接时静默跳过，互不阻塞。
- **依赖**：`main/CMakeLists.txt` REQUIRES 补 `esp_wifi esp_netif esp_event lwip mqtt mbedtls`；`idf_component.yml` 增加 `espressif/mqtt`。
- 顺带修复：解析器空缓冲 `buffer_len-1` 无符号下溢、异常帧长直接当假帧头跳过。

## 本地测试与编译验证结果

修复后（最终状态）：

- `python tests\run_public_tests.py project2_task` → **exit 0**，`[public] all public tests passed`（4/4 文件）。
- `python tools\run_debug_probe.py project2_task` → **exit 0**，8 项 `[probe:ok]` 全通过，voice 提示变为 `[probe:info] voice module appears to reference current-session fetch`，`all visible diagnostic checks passed`。
- `python tools\run_espidf_build.py project2_task`（Windows EIM，ESP-IDF v6.0.1，esp32s3）：
  - 第 1 次失败：`Failed to resolve component 'mqtt'` —— IDF v6 的 `components/mqtt` 目录为空，esp-mqtt 已移到组件注册表。修复：`idf_component.yml` 增加 `espressif/mqtt`。
  - 第 2 次失败：`main.cpp: '++' expression of 'volatile'-qualified type is deprecated [-Werror=volatile]`（C++20）。修复：统计计数器去掉 volatile。
  - 第 3 次：**编译成功**，`Generated .../build/stdpro.bin`（app 0xefff0 bytes，分区余量 6%），`protocol_packet/maixsense_parser/device_config/mqtt_payload/main` 全部编译进 app，`espressif__mqtt` 组件参与构建。
- 额外手动验证（临时库脚本，不触碰 `data/project2.db`）：
  - 旧 schema care_events 库迁移后补齐 4 列、旧行保留、ts 回填；
  - 旧“空盐明文”管理员登录成功并自动升级为加盐哈希，错误密码拒绝，伪造 token 拒绝；
  - staff recognized session 可取 context 且含 care_events；无 session / 患者跨目标均拒绝且患者明细为空；
  - 混合 CSV `first`/`skip` 策略按行生效。

按契约未验证（本任务不要求）：`idf.py flash/monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序、MLX 实机读数。

## 未验证的残留技术债与风险

1. **固件仅编译验证**：Wi-Fi/MQTT 逻辑未在实机跑通；巴法云对 ~13KB/条、ToF 8fps×2 的发布频率可能限流，实测后可能需要抽帧/节流策略。
2. **MQTT QoS0 无重传**：云端链路丢帧由 gateway 的 set 聚合超时兜底，与旧行为一致，但未实测丢帧率。
3. **v2 兼容接口仍是本机免鉴权**（契约要求保留）：`/api/v2/*` 可读床位聚合数据，若未来 worker 拆机部署需要引入 token 机制。
4. **`/api/v3/session/current` 加入本机白名单**：这是 voice 显式取会话的前提，仅暴露当前操作者会话元数据（不含患者数据）；如需更严可改为 voice 专用 token。
5. **admin_http_sessions 无自动清理**：过期行只失效不删除，长期运行建议加定期清理。
6. **登录无速率限制/锁定**：本机护士站场景暂可接受，公网部署前需补。
7. **admin.html 存在历史编码乱码字符串**（个别 showNotice 文案），非本次引入，功能不受影响，未整体重写以控制 diff 范围。
8. **legacy `data/legacy_sample.db` 样例文件在本工作区不存在**，迁移逻辑用等价构造的旧 schema 临时库验证。
