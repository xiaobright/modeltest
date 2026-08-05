# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行（2026-08-03，工作区初始状态）：

- `python tests\run_public_tests.py project2_task`
  - 结果：4 个测试文件全部通过（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway，输出 `[public] all public tests passed`）。
  - 说明：公共冒烟只覆盖编译、admin 页面/setup、模块可调用性和基础导入，不暴露安全问题。
- `python tools\run_debug_probe.py project2_task`
  - 结果：`failures=6`，初始失败项：
    1. `management API rejects missing cookie` — 缺 Cookie 时 `GET /api/v3/subjects` 仍返回 200 并带出 subject 明细。
    2. `management API rejects forged cookie` — 伪造 Cookie 同样返回 200。
    3. `unknown identity session is denied` — `identity_state=unknown` 的 session 仍被放行（`reason=role_allowed`）。
    4. `expired session is denied` — 已过期 session 仍被放行。
    5. `care_event write rejects missing admin cookie` — `POST /api/v3/care/events` 路由不存在（404），更谈不上鉴权。
    6. `care_event normalizes room/bed for create and query` — 模块可写入但 lowercase 写入后 uppercase 查询不到。
  - 另有 voice/助手路径 Warning（依赖隐式 ambient session）。

代码阅读后确认的根因（初始诊断的补充）：

- `auth.py::_password_hash` 在无 salt 时直接返回明文密码入库；`admin_account_exists()` 恒为 `False`（setup 永远可用）；`get_admin_http_session()` 忽略 token 本身，任意有效 session 都能通过伪造 Cookie 命中。
- `gateway.py::_authorized_for_api` 对一切本机请求无条件放行（`_path_allows_local_service` 白名单存在但从未被调用）。
- `gateway.py::session_is_authenticated` 对 `unknown` 身份返回 True，且不校验过期时间与 `actor_subject_id`；`actor_can_access_target` 对缺失 actor 的请求默认放行。
- `care_events.py` 只有草案 schema（缺 `severity/source/created_by/ts`），未做 room/bed 规范化，无路由接线，context 摘要为空 stub。
- `sleep_importer.py` 的 `first` 策略实际取的是 `beds[-1]`（最后一个配置床位），与文档"第一个配置床位"相反。
- `db.py` 初始化只 `CREATE TABLE IF NOT EXISTS`，旧库缺列时不迁移；索引与 `care_events` 旧表缺 `ts` 列冲突会直接报错。
- ESP32 固件 Wi-Fi/MQTT 整体缺失（仅有 TODO 注释），NVS 骨架已存在但未接线；`main/CMakeLists.txt` / `idf_component.yml` 缺网络依赖。

## 修改的文件列表

gateway（Python）：

- `gateway/auth.py` — 密码强制加盐哈希；setup 幂等校验；token 精确匹配；登录常数时间比较。
- `gateway/db.py` — `care_events` 完整 schema；新增 `_LEGACY_COLUMN_MIGRATIONS` + `migrate_legacy_columns()` 旧库缺列迁移；索引创建移到迁移之后。
- `gateway/care_events.py` — 完整重写：CRUD、room/bed 规范化、limit、context 摘要。
- `gateway/sleep_importer.py` — 修复 `first` 策略床位选择；默认归属对齐配置床位大小写；按行策略注释。
- `gateway/gateway.py` — 修复 `_authorized_for_api` 本机白名单收敛、`session_is_authenticated` 完整校验、`actor_can_access_target` 拒绝无 actor 请求；新增 care_event GET/POST 路由；v3 context 接入 `modalities.care_events`。
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session()`，上下文请求显式携带当前 session_id，不再依赖网关侧隐式 ambient session。

ESP32-S3 固件（`esp32/testpro4/`）：

- 新增 `main/protocol_packet.{h,cpp}`、`main/maixsense_parser.{h,cpp}`、`main/device_config.{h,cpp}`、`main/mqtt_payload.{h,cpp}`、`main/network_backhaul.{h,cpp}`。
- 重写 `main/main.cpp` 为初始化/任务/glue 层。
- `main/CMakeLists.txt` — 新增源文件与 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖。
- `main/idf_component.yml` — 新增 `espressif/mqtt` 托管组件依赖。
- `README.md`、`CHANGELOG.md` — 同步恢复后的架构与文件说明。

文档：

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md` — 同步鉴权边界、care_event、CSV 策略、ESP32 回传状态。

## 架构调整与模块设计

- 维持现有 gateway 模块边界：`gateway.py` 只放路由 glue；care_event 数据访问独立成 `care_events.py`，未扩大 `subjects.py`；schema 与迁移集中在 `db.py`。
- `db.py` 迁移策略：`CREATE TABLE IF NOT EXISTS` 建全量新 schema → `migrate_legacy_columns()` 用 `PRAGMA table_info` 逐列比对并 `ALTER TABLE ADD COLUMN`（带常量默认值，旧数据自动回填保留）→ 再创建索引（避免旧表缺列导致 `CREATE INDEX` 失败）。`care_events.ts` 后补为 0 时用 `created_ts` 回填；旧数据 room/bed 统一归一化为大写（幂等）。
- ESP32 固件按职责拆分五个模块，`main.cpp` 只保留 ESP-IDF 初始化、任务创建、硬件调用和模块 glue：采集任务（ToF/MLX）→ `usb_send_packet`（USB packet 契约）与 `network_backhaul_publish`（MQTT 契约）双通道并行，协议逻辑全部下沉到模块。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256（200k 迭代）加盐哈希存储，任何路径不落明文；登录用 `hmac.compare_digest` 常数时间比较。
- Cookie：只保存 `secrets.token_urlsafe(32)` 随机 token；DB 只存 token 的 SHA-256 哈希；`get_admin_http_session` 按 `token_hash` 精确匹配并校验过期与账号状态。
- setup 只有一次：`admin_account_exists()` 真实查库，已有管理员时拒绝重复初始化。
- 管理 API（subjects/assignments/sessions/memories/credentials/care/events 等）：必须持有效管理员 Cookie；缺失或伪造 Cookie 一律 401，本机请求也不例外。
- 本机 worker 例外收敛到白名单：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`，其余路径不享受例外；face gallery 仍仅限本机，credential template 不允许远程导出。
- v3 context session 认证四要素缺一不可：`identity_state != unknown`、`assurance_level != none`、带 `actor_subject_id`、`expires_ts` 未过期；actor 必须能解析到 subject。staff/admin 可看任意目标患者，patient 只能看自己；未授权时 `target` 与全部 `modalities`（含 care_events）返回空结构，患者数据零泄漏。
- voice 助手：先调用 `/api/v3/session/current` 显式获取当前 session_id 再请求上下文（可用 `VOICE_SESSION_ID` 覆盖），不再依赖隐式 ambient session。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行处理，同一 CSV 内显式行与无归属行互不影响：

- 行带 `room/bed`：大小写不敏感对齐到配置床位，只写该床位。
- 行不带 `room/bed`：
  - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 已设置 → 写入指定床位（同样对齐配置大小写）；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 写入第一个配置床位（修复了原先错取最后一个床位的 bug）；
  - `=skip` → 跳过并打印 skipped 计数；
  - `=all` → 仅显式调试模式，扇出到全部床位，不作为默认。
- 未识别策略为安全起见不导入。

## care_event 实现细节

- `db.py`：`care_events` 表（`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`）+ `(subject_id, ts, created_ts)` 与 `(room, bed, ts, created_ts)` 索引；旧表缺列自动迁移并保留旧数据。
- `care_events.py`：`create_care_event`（room/bed 写入统一大写、severity 白名单 `info/warning/critical`、ts 缺省取当前时间）、`list_care_events`（查询条件同样规范化、按 `ts/created_ts` 倒序、limit 默认 20 上限 200）、`build_care_events_context`（items + brief 摘要）。
- 路由：`POST /api/v3/care/events`、`GET /api/v3/care/events?subject_id=... / ?room=...&bed=...&limit=...`，均要求管理员 Cookie（不在本机白名单内）；lowercase 写入的 `r1203/b1` 可被 uppercase `R1203/B1` 查询命中（写入规范化 + 旧数据迁移双重保证）。
- context：`/api/v3/context/chat` 授权通过时 `modalities.care_events` 返回最近 10 条摘要并计入 `brief/prompt_hints`，`allowed_sections` 增加 `care_events`；未授权时返回空结构。

## ESP32-S3 固件接口对齐说明

- 恢复 Wi-Fi STA（`esp_wifi` STA 模式、事件组、断线自动重连）与巴法云 MQTT client（broker `mqtt://{bemfa_host}:{bemfa_port}`，默认 `bemfa.com:9501`，ClientID=UID，keepalive 30s，自动重连）。
- NVS：沿用 `project2` namespace，读取并校验 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；`device_config_network_ready()` 要求 ssid/uid/room/bed 齐全（password 允许为空用于开放网络）；配置不完整时不连网、打印 CFG 帮助，USB 采集不受影响。串口 CFG 命令保持不变，密码与 UID 只显示存在性。
- topic：`{room}{bed}tof1/tof2/mlx1/mlx2` 全小写拼接（`device_config_build_topic`），与 `gateway/bed_config.py::topics_for()` 契约一致。
- MQTT JSON：`{"payload_b64":"..."}`，base64 内容是传感器原始 payload（ToF 完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHK][DD]`，MLX 为 768×float32），不是完整 USB packet。大 payload（~10022B → base64 ~13.4KB + JSON）使用堆缓冲（`mqtt_payload_build_json`），避免固定小缓冲溢出。
- 发送路径：`usb_send_tof_payload()` 与 MLX 任务在保留 USB CDC packet 输出（`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 仅覆盖 payload、小端）的同时，向对应 MQTT topic 并行发布原始 payload。
- `main/CMakeLists.txt` 补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`；`main/idf_component.yml` 增加 `espressif/mqtt`（IDF v6 起 esp-mqtt 为托管组件，registry 当前版本线已重发为 v1.x，故用 `"*"` 约束）。
- ToF payload 保持完整原始帧（未裁剪为 10000B 图像区），gateway/collector 契约无需变更。

## 本地测试与编译验证结果

修复后（2026-08-03）：

- `python tests\run_public_tests.py project2_task`
  - 结果：全部通过（`[public] all public tests passed`）。
- `python tools\run_debug_probe.py project2_task`
  - 结果：8 项检查全部 `[probe:ok]`，failures=0；voice 路径提示变为 `[probe:info] voice module appears to reference current-session fetch`。
- `python tools\run_espidf_build.py project2_task`
  - 结果：**编译成功**。环境：Windows EIM ESP-IDF v6.0.1，target esp32s3。
  - 过程中修过两处构建问题并如实记录：① `REQUIRES mqtt` 失败（IDF v6 内置 `components/mqtt` 已无 CMakeLists）→ 改为 `idf_component.yml` 声明 `espressif/mqtt`；② `^3.5.1` 版本约束不匹配（registry 已重发 v1.x 版本线）→ 改为 `"*"`。
  - 产物：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（0xf0370 字节，app 分区余量 0xfc90 字节 / 6%），`main` 组件下 5 个新模块全部编译链接。
- 额外手工验证（临时 SQLite，不污染 `data/project2.db`）：
  - 旧版 `care_events` 表（缺 4 列 + lowercase room/bed 存量行）初始化后自动迁移，旧数据保留且可被查到大写规范化后的结果。
  - setup→login→Cookie 链路：密码以 salt+hash 落库、伪造 token 拒绝、错误密码拒绝、二次 setup 拒绝。
  - staff 会话授权 context 返回 `modalities.care_events`；patient 看自己被允许、看他人被拒且 payload 全空；不存在/过期/unknown 会话均 `not_authenticated`。
  - 混合 CSV（显式行 + 无归属行）：显式行写入指定床位、无归属行按 `first` 写第一个配置床位、`skip` 时仅跳过无归属行。

## 未验证的残留技术债与风险

- 未做 `idf.py flash / monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序、MLX90640 实机读数验证（按任务要求不在本地编译范围内）；MQTT 发布路径仅编译期验证，实机回传需在硬件上复测。
- 固件 app 分区余量仅 6%（0xfc90 字节）：后续加功能需关注体积，必要时调大 app 分区或裁剪组件。
- MQTT 回传带宽：ToF 8fps 双路 + MLX 4Hz 双路全量上行约 90KB/s，巴法云侧 QoS0 无重传保证，弱网下可能丢帧；如需可靠回传需另行评估 QoS/降采样（本任务未改契约）。
- NVS 明文存储 Wi-Fi 密码与巴法云 UID：真实部署建议启用 NVS encryption / flash encryption（`esp32/NVS_CONFIG.md` 已注明）。
- 旧 v2/v3 API、worker 调用路径保持兼容，但未覆盖全部隐藏测试场景；`/api/v3/context/chat` 对无 session_id 的本机调用仍回退到"当前最近会话"（该会话本身必须通过四要素认证），如需更严格可后续移除该回退。
- `espressif/mqtt` 使用 `"*"` 版本约束（registry 版本线重发导致），后续建议锁定到具体已验证版本。
