# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前（2026-07-26）运行：

- `python tests\run_public_tests.py project2_task`
  - 结果：**全部通过**（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway）。公共冒烟只验证"可调用不崩溃"，不覆盖安全语义。
- `python tools\run_debug_probe.py project2_task`
  - 结果：**failures=6**，具体：
    1. `management API rejects missing cookie`：无 Cookie GET `/api/v3/subjects` 返回 200 并泄露 subjects 列表（期望 401）。
    2. `management API rejects forged cookie`：伪造 Cookie 同样返回 200（期望 401）。
    3. `unknown identity session is denied`：`identity_state=unknown` 的 session 查询 context 时 `policy.allowed=true`（期望拒绝）。
    4. `expired session is denied`：`expires_ts` 已过期的 session 仍 `policy.allowed=true`（期望拒绝）。
    5. `care_event write rejects missing admin cookie`：POST `/api/v3/care/events` 返回 404（路由不存在，期望鉴权后可用、无 Cookie 401）。
    6. `care_event normalizes room/bed for create and query`：小写 `r1203/b1` 写入后大写查询查不到（rows=[]）。
  - 另有 Warning：voice 助手未引用 `session/current`，收紧鉴权后本地助手会取不到上下文。

初始诊断对应的根因（读码确认）：

- `auth.py`：`admin_account_exists()` 恒返回 False（setup 可无限重放）；`_password_hash()` 空盐时直接返回明文密码作为"hash"；`get_admin_http_session()` 的 SQL 不按 token_hash 过滤——只要库里存在任意有效会话，任何/无 Cookie 都命中（这正是 probe 1/2 失败的原因）。
- `gateway.py`：`_authorized_for_api()` 对本机请求无条件放行所有 `/api/` 路径，管理 API 本机免鉴权；`session_is_authenticated()` 把 `identity_state=unknown` 当成"worker 调用"直接放行且不检查 `expires_ts`/`actor_subject_id`；`actor_can_access_target()` 在查不到 actor 时默认允许；`build_chat_context_v3()` 无 `session_id` 时静默回退 `get_current_session()`（ambient session 漏数据通道）。
- `care_events.py`：只有 9 列旧 schema 草稿，create/list 不做 room/bed 规范化、无 limit/排序，context 聚合是空 stub，gateway 无路由。
- `db.py`：care_events 表用旧 9 列 schema 且仅 `CREATE TABLE IF NOT EXISTS`，旧库缺列无迁移。
- `sleep_importer.py`：`first` 策略实际写的是 `beds[-1]`（最后一个床位，注释还声称 first）；未配置床位的显式行不做大小写规范化。
- `esp32/testpro4`：Wi-Fi/MQTT/base64 回传全部为 TODO 注释，CMakeLists/idf_component.yml 缺网络依赖。

## 修改的文件列表

Gateway（Python）：

- `gateway/auth.py` — 重写鉴权核心：`admin_account_exists()` 查库；PBKDF2 加盐哈希强制生效；`get_admin_http_session()` 严格按 token_hash + 过期时间 + 账号状态过滤；新增旧明文行恒时比较验证 + 登录时自动升级为加盐哈希；session 字典不再外泄 token_hash。
- `gateway/db.py` — care_events 表升级为完整 13 列 schema；新增 `ensure_columns()` 通用缺列迁移与 `migrate_care_events_table()`（PRAGMA table_info + ALTER TABLE ADD COLUMN，旧行保留、`ts` 用 `created_ts` 回填）；索引改按 `ts DESC`。
- `gateway/care_events.py` — 完整 CRUD：create 校验 severity 枚举、room/bed 规范化、`ok=true` 返回；list 支持 subject_id / room+bed / limit（默认 20、上限 200）按 `ts DESC, created_ts DESC` 倒序；`build_care_events_context()` 输出 items+count+brief；模块自身的 `init_care_events_table()` 也走同一迁移。
- `gateway/gateway.py` — 本机例外收紧为白名单（`/api/v2/*`、`/api/esp/*`、context/chat、identity gallery/match、vision/observation、session/current），其余管理 API 本机也要 Cookie；`session_is_authenticated()` 按契约拒绝 unknown/空 identity、none/空 assurance、过期、缺 actor；`actor_can_access_target()` 无 actor 即拒绝；`build_chat_context_v3()` 去掉 ambient 回退（必须显式 session_id）、聚合 `modalities.care_events`、`allowed_sections` 增加 care_events、响应里的 `session` 字段只回显四个非敏感键；新增 `POST/GET /api/v3/care/events` 路由（POST 自动用管理员 subject_id 补 created_by）。
- `gateway/sleep_importer.py` — `first` 策略修正为真正的第一个配置床位 `beds[0]`；策略按行生效（显式 room/bed 行不受任何策略影响）；显式行与 DEFAULT_ROOM/BED 均先大小写不敏感匹配配置床位、未命中时统一规范化为大写，保证与查询端一致。
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session()` / `fetch_current_session_id()`（带 2s 缓存）；`build_gateway_context_params()` 在未指定 `VOICE_SESSION_ID` 时先显式 GET `/api/v3/session/current` 再携带 session_id 请求 context，不再依赖 gateway 静默 ambient session。

ESP32-S3 固件（`esp32/testpro4`）：

- `main/protocol_packet.{h,cpp}` — 新增：AA55 包常量、SENSOR_TYPE、CRC16-CCITT、包头/CRC 填充与整包校验辅助。
- `main/maixsense_parser.{h,cpp}` — 新增：MaixSense 流解析器从 main.cpp 抽出，支持噪声跳过、分块累积、坏尾字节（假帧头继续扫描）、异常长度防死锁（超缓冲的"长度"视为假帧头，修复原实现遇到噪声长度字段时 `i + frame_len <= buffer_len` 永假、缓冲区反复被填满清空的卡死路径）、半帧等待、溢出保最新，并加 `bytes_dropped` 统计。
- `main/device_config.{h,cpp}` — 新增：NVS 读写（namespace `project2`，键 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`）、`usb_ready`（room+bed）与 `network_ready`（ssid/password/uid/room/bed 全非空，缺失项列表）双重完整性校验、`device_config_topic_prefix()` 小写规范化、CFG 命令实现。
- `main/mqtt_payload.{h,cpp}` — 新增：`mqtt_topic_for_sensor()`（`{room}{bed}tof1/tof2/mlx1/mlx2`）与 `mqtt_payload_build_json()`（`{"payload_b64":"..."}`，mbedtls base64，按实际大小 malloc——ToF 原始帧 ~10022B → base64 ~13.4KB，固定小缓冲会截断，这正是原 TODO 注释警告的坑）。
- `main/net_backhaul.{h,cpp}` — 新增：Wi-Fi STA（NVS 配置、断线自动重连）+ esp-mqtt client（`mqtt://bemfa.com:9501`，ClientID=UID，出站缓冲 20KB）生命周期；`net_backhaul_publish_sensor()` 发布原始 payload（QoS 0），未配置/未连接时静默跳过不影响 USB。
- `main/main.cpp` — 重写为初始化/任务/glue：`usb_send_tof_payload()` 保留 USB CDC1 输出并在发送后镜像 MQTT；MLX 路径抽出 `usb_send_mlx_payload()` 并镜像 MQTT（发布原始 3072B float32 payload，不是完整 USB packet）；启动流程接入 `net_backhaul_start()`（配置不完整时 USB-only 并提示）；NVS/解析器/协议逻辑全部改调新模块。ToF 初始化时序、交替发送状态机、MLX 管理器、TinyUSB 初始化保持原行为。
- `main/CMakeLists.txt` — SRCS 增加 5 个新模块；REQUIRES 补 `esp_wifi esp_netif esp_event lwip mqtt mbedtls`。
- `main/idf_component.yml` — 增加 `espressif/mqtt`（ESP-IDF 6.0 起 esp-mqtt 在组件仓库）。

文档：

- `README.md` — ESP32 段落更新为"已恢复"；管理员初始化段写明白名单本机例外与密码/Cookie 存储方式；context/chat 示例改为显式 session_id 并说明未带 session_id 的行为；新增 care_event 接口段。
- `gateway/README.md` — 模块清单加 `care_events.py`；管理员初始化段写明 PBKDF2/token-hash 与本机白名单；新增"v3 会话与上下文授权"规则段；睡眠 CSV 策略改为按行语义描述。
- `RK3588_TEST_GUIDE.md` — 11.2/11.3/12.6/13 的 context 测试改为先取 `/api/v3/session/current` 再显式携带 `session_id`；新增 11.4 care_event 测试段；22.2 故障排查补"必须带 session_id / 检查过期与 actor"；`VOICE_SESSION_ID` 注释更新。
- `CHANGES.md` — testpro4 两行状态从"待修复"改为"已恢复"。
- `esp32/NVS_CONFIG.md` — 状态描述从"仍需恢复"改为"已恢复 + 配置校验行为"。
- `esp32/testpro4/README.md` — 概述/功能表/版本表更新为 v4.1 已恢复状态。
- `esp32/testpro4/CHANGELOG.md` — 新增 v4.1 条目（本次实现细节）。
- `PULL_REQUEST_TEMPLATE.md` — 本文件。

未修改：`tests/`、`tools/` 诊断脚本，`subjects.py`、`sensor_store.py`、`esp_store.py`、`config.py`、`bed_config.py`、`utils.py`、posture/vision/rkllm/sleep_deploy_pack、`sketch_jan22a`、`usb_descriptors.c`、`sdkconfig.defaults`、mlx90640 组件。

## 架构调整与模块设计

- 模块边界维持 reference/architecture_notes.md 的分工：schema 与迁移在 `db.py`，密码/Cookie 会话在 `auth.py`，care_event CRUD 独立在 `care_events.py`（没有扩进 `subjects.py`），`gateway.py` 只加了路由 glue 和授权判断函数的修正，没有业务逻辑回流。
- 迁移策略是通用的 `ensure_columns()`：`PRAGMA table_info` 检查缺列 → `ALTER TABLE ADD COLUMN`（带常量 DEFAULT）→ 旧数据回填（`ts=created_ts`）。`CREATE TABLE IF NOT EXISTS` 只负责全新库。
- 固件按交接文档推荐拆为 protocol_packet / maixsense_parser / device_config / mqtt_payload（外加 net_backhaul 承载 Wi-Fi/MQTT 运行时），`main.cpp` 从 1116 行纯逻辑堆叠变为初始化 + 任务 + glue；协议与解析逻辑均可独立复用/测试。

## 安全边界及鉴权设计

- **密码**：随机 16B 盐 + PBKDF2-HMAC-SHA256（200,000 次迭代），库中无明文；比较用 `hmac.compare_digest`。历史遗留的空盐明文行登录时恒时验证并立即升级为加盐哈希（保留旧账号可用性，不降低新写入的安全性）。
- **Cookie**：`secrets.token_urlsafe(32)` 随机 token 只存在 Cookie（HttpOnly + SameSite=Lax），数据库只存 SHA-256(token)。会话查询严格 `WHERE token_hash=? AND expires_ts>=? AND status='active'`——无 Cookie、伪造 Cookie、过期 Cookie 都是 401；登出删除对应 token_hash 行。
- **本机例外白名单**：仅 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current` 可由 loopback 免 Cookie 调用（worker/voice 联调所需，与 ONBOARDING 列出的服务接口一致，session/current 是 voice 显式取会话所需）。管理 API（subjects/assignments/memories/credentials/sessions/care events）本机也必须带有效 Cookie。
- **远程数据出口**：identity gallery 与 `include_template=1` 的凭据查询保持仅本机（403），远程即使登录也不能导出 face/credential template。
- **v3 session 契约**（reference/api_contracts.md）：`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 过期、缺 `actor_subject_id` 一律视为未认证；staff/admin 可查任意目标，patient 仅自己；无 actor 记录直接拒绝。拒绝响应只含 policy 与空结构（患者明细/记忆/护理事件/睡眠全为空），context 响应中的 `session` 回显也只保留 session_id/identity_state/assurance_level/expires_ts 四个非敏感键。
- **零 ambient 泄漏**：context/chat 不带 `session_id` 就是未认证——调用方（voice）必须先显式 GET `/api/v3/session/current` 拿到会话再请求，杜绝"碰巧有人刷过脸就把数据带给任意本机请求"的通道。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行归属（同一文件可混合两类行，策略只作用于无归属行）：

1. 行带 `room/bed`（大小写不敏感识别列名与值）：只写入对应床位；与配置床位大小写不敏感匹配，未配置的组合规范化为大写后写入。显式行永不受策略/DEFAULT 影响，也不会被整表丢弃。
2. 行不带 `room/bed`：
   - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 同时设置 → 写入该床位（同样先匹配配置床位）；
   - 否则 `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 第一个配置床位 `beds[0]`（修复了原实现写 `beds[-1]` 最后一床的 bug）；
   - `skip` → 跳过并计数打印；
   - `all` → 广播所有床位，仅作显式调试模式，不是默认；
   - 无法识别的策略值 → 安全起见不导入。

## care_event 实现细节

- **Schema**（`db.py`）：`event_id(PK) subject_id room bed kind title content severity source created_by ts created_ts updated_ts`，索引 `(subject_id, ts DESC)` 与 `(room, bed, ts DESC)`。
- **迁移**：旧库只有 9 列（无 severity/source/created_by/ts）时，初始化自动 ALTER 补列（severity='info'、source='manual'、created_by=''），并用 `created_ts` 回填 `ts=0/NULL` 的旧行；旧数据全部保留（临时库自测验证：旧行迁移后可查、新旧行共存、重复初始化幂等）。
- **CRUD**（`care_events.py`）：create 要求 subject_id 或 room+bed 至少其一，room/bed 用与 gateway 相同的 `normalize_room/bed`（strip+upper）写入，severity 白名单（info/warning/critical，非法回落 info），无 ts 用当前时间，返回 `{ok, event_id, subject_id, event}`；list 按 subject_id / room+bed（查询侧同样规范化，`r1203/b1` 写、`R1203/B1` 查可命中）过滤，`limit` 默认 20 上限 200，按 `ts DESC, created_ts DESC` 倒序。
- **路由**（`gateway.py`）：`POST /api/v3/care/events`（管理员登录必需；created_by 缺省取当前管理员 subject_id）、`GET /api/v3/care/events?subject_id=...` / `?room=...&bed=...`（同样管理员必需，本机白名单不含该路径）。
- **Context 聚合**：授权通过时 `modalities.care_events = {items, count, brief}`（目标有 subject_id 按 subject 查，否则按床位查，最多 10 条 + 最近 3 条拼 brief 进总 brief）；未授权为空结构。

## ESP32-S3 固件接口对齐说明

- **Wi-Fi + MQTT 巴法云**：NVS 配置完整（ssid/password/uid/room/bed）时启动 Wi-Fi STA，获取 IP 后启动 esp-mqtt client（`mqtt://{bemfa_host}:{bemfa_port}`，默认 `bemfa.com:9501`，ClientID=巴法云 UID）；Wi-Fi 断线自动重连、esp-mqtt 自带重连。配置缺失时打印缺失项并停留 USB-only 模式（串口 CFGSET 可补配置后 REBOOT）。
- **NVS 配置**：namespace `project2`，键 `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`；`CFG?` 显示 usb_ready/network_ready、缺失项和规范化后的 topic；密码/UID 只显示是否存在。
- **Topic**：`device_config_topic_prefix()` 把 room/bed 小写拼接（`R1203/B1 → r1203b1`），发布 topic `r1203b1tof1/tof2/mlx1/mlx2`，与 `gateway/bed_config.topics_for()` 一致。
- **MQTT JSON**：`{"payload_b64":"<base64 raw payload>"}`。base64 的内容是原始传感器 payload——ToF 是完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`（≈10022B，不是只有 10000B 图像区），MLX 是 3072B float32；均不含 AA55 USB 包头与 CRC。大 payload 编码按 `4*ceil(n/3)` 实际大小 malloc（ToF → ~13.4KB），MQTT 出站缓冲设 20KB，规避固定小缓冲截断。
- **USB packet 契约保持**：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，TYPE 0x01=MLX / 0x02=ToF，CRC16-CCITT（0xFFFF/0x1021）只覆盖 payload，LEN 与 CRC 小端序；`usb_send_tof_payload()` 与 MLX 路径在保留 USB CDC 输出的同时并行 MQTT 发布，MQTT 不通时 USB 不受影响。
- **解析器健壮性**：除保留原有噪声/分块/坏尾/半帧处理外，修复了异常长度导致的死锁路径（噪声伪装的超大"长度"字段现按假帧头跳过，原实现会卡住整个缓冲区）。

## 本地测试与编译验证结果

修复后（2026-07-26）运行：

- `python tests\run_public_tests.py project2_task` → **全部通过**（4 个公共测试文件）。
- `python tools\run_debug_probe.py project2_task` → **all visible diagnostic checks passed**（初始 6 项 FAIL 全部转 ok；voice Warning 变为 `voice module appears to reference current-session fetch`）。
- `python tools\run_espidf_build.py project2_task` → **Build finished successfully**（Windows EIM，ESP-IDF v6.0.1，target esp32s3；组件管理器解析 `espressif/mqtt (1.0.0)` / `esp_tinyusb (2.2.0)`；产物 `stdpro.bin` 0xf01c0 字节，app 分区余 6%。仅有两条既有的 sdkconfig 无关警告：`TINYUSB_ENABLED`、`USB_OTG_SUPPORTED` 为 unknown kconfig symbol，本次未改 sdkconfig.defaults）。
- 补充自检（临时 SQLite，脚本未入库）：29 项断言全部通过，覆盖——旧 9 列 care_events 库迁移（旧行保留、默认值回填、幂等）；admin setup 幂等/登录/伪 token/错密码/登出/哈希落库/旧明文行升级；context 授权矩阵（staff 允许、patient 仅自己、无 session/未知 session/未认证拒绝且零患者字段泄漏、care_events 模态注入）；睡眠导入 first/skip/all/DEFAULT 四策略下混合 CSV 的按行归属与大小写规范化。
- 所有 Python 测试均使用临时 SQLite（tests/tools 自身即如此配置），未触碰 `data/project2.db`。

## 未验证的残留技术债与风险

- **固件实机行为未验证**：本次只做到 ESP-IDF 编译成功。真实 Wi-Fi/MQTT 连通、巴法云限流下 ~13.4KB ToF 消息的实际吞吐（8FPS×2 全速时约 27KB/s×2，可能需要在板上确认丢包率与内存水位）、USB 与 MQTT 并行时的任务调度余量、NVS 串口配置全流程，均需按 RK3588_TEST_GUIDE / QUICKSTART 在硬件上验证。`esp_mqtt` 出站缓冲 20KB 一次只容纳一条 ToF 消息，突发时以丢新帧（QoS 0 语义）为代价，未实测。
- **Wi-Fi 安全模式**：STA 按 WPA-PSK 起步阈值配置，开放网络或 WPA3-only 网络未测。
- **管理会话未做滑动续期/并发上限**：Cookie TTL 固定 8h（可配），无刷新与单账号会话数限制；admin_http_sessions 过期行未做定期清理（只在查询时过滤）。
- **voice 端 2s session 缓存**：护士刚完成识别后最长 2s 内 voice 可能仍用旧 session_id（表现为短暂拒绝或旧 actor），可用 `GATEWAY_SESSION_CACHE_S=0` 关闭。
- **公共测试对 login 的容错**：`test_refactored_features.py` 对 login 异常做了 try/except（种子缺陷时代码不崩溃即可），修复后 login 实际成功，该测试不再掩盖问题，但公共层仍无安全断言，安全语义靠 probe 与隐藏测试兜底。
- **`/api/v2/*` 本机免鉴权保留**：这是交接文档要求的 worker 兼容路径；意味着本机任意进程可注入传感器数据/读取床位数据。单护士站部署可接受，多租户或不可信本机进程场景需要进一步收紧（如 worker token）。
- **sketch_jan22a（radar/env/audio 固件）不在本次范围**，未重新验证其 NVS/MQTT 行为。
