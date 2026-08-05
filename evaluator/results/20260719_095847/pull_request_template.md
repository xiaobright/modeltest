# Pull Request 提测说明 (Pull Request Template)

本次迭代把 Project2 修复到可提测状态：管理 API 鉴权闭环、v3 授权上下文权限收敛、care_event 全链路、睡眠 CSV 逐行归属策略、ESP32-S3 testpro4 Wi-Fi + MQTT 巴法云回传恢复，并同步更新受影响文档。

## 初始自检诊断（修改前）

- `python tests\run_public_tests.py project2_task`：**全部通过**（公开冒烟不覆盖安全属性）。
- `python tools\run_debug_probe.py project2_task`：**failures=6**：
  1. `management API rejects missing cookie`：无 Cookie 的本机请求 `GET /api/v3/subjects` 返回 200 并带出 subjects 数据（`_authorized_for_api` 对本机请求无条件放行）。
  2. `management API rejects forged cookie`：伪造 Cookie 同样 200（`auth.get_admin_http_session` 忽略 token，`LIMIT 1` 取任意活跃会话）。
  3. `unknown identity session is denied`：`identity_state=unknown` 的 session 仍 `policy.allowed=true`（`session_is_authenticated` 把 unknown 当已认证放行）。
  4. `expired session is denied`：过期 session 仍放行（完全没有检查 `expires_ts`）。
  5. `care_event write rejects missing admin cookie`：`POST /api/v3/care/events` 返回 404（路由未接线）。
  6. `care_event normalizes room/bed for create and query`：小写 `r1203/b1` 写入后大写查询查不到（无规范化）。
  - 另有 `[probe:Warning]` voice 路径提示：收紧鉴权后本地助手若依赖隐式 ambient session 会取不到上下文。
- 代码审查中额外确认的种子缺陷（probe 未直接覆盖）：
  - `auth._password_hash(password, "")` 直接返回明文密码作为 hash（首次 setup 即明文入库）。
  - `auth.admin_account_exists()` 恒为 False：可重复 setup 开新管理员账号，`/api/v3/admin/auth` 的 `setup_required` 永远为 true。
  - `sleep_importer` 的 `first` 策略实际写入 `beds[-1]`（最后一个床位）。
  - `db.py`/`care_events.py` 的 care_events 表是旧 schema（缺 `severity/source/created_by/ts`），无迁移逻辑。
  - `actor_can_access_target(None, ...)` 返回 True（无 actor 直接放行）。

## 修改的文件列表

Gateway / Python：

- `gateway/auth.py`：密码强制加盐 PBKDF2；`admin_account_exists()` 查库；`get_admin_http_session()` 按 token hash + 过期时间校验；遗留明文行登录时自动升级重哈希；`hmac.compare_digest` 常数时间比较；顺带清理过期管理会话。
- `gateway/db.py`：care_events 全量 schema（新库）+ `ensure_care_events_schema()` 旧库迁移（`PRAGMA table_info` + `ALTER TABLE ADD COLUMN`，`ts` 用 `created_ts` 回填）；新增按 `ts` 的索引。
- `gateway/care_events.py`：重写 CRUD——room/bed 写入与查询规范化、`severity/source/created_by/ts` 字段与校验、`limit`（默认 50/上限 200）+ `ts DESC` 排序、`build_care_events_context()` 真实实现。
- `gateway/gateway.py`：`_authorized_for_api` 本机豁免收窄到固定白名单；`session_is_authenticated` 按契约四条硬校验；`actor_can_access_target` 无 actor 拒绝；`build_chat_context_v3` 移除 ambient session 隐式回退、新增 `modalities.care_events`；新增 `GET/POST /api/v3/care/events` 路由（POST 缺省 `created_by` 回填管理员 subject）；白名单加入 `/api/v3/session/current`。
- `gateway/sleep_importer.py`：`first` 策略改为 `beds[0]`；未配置的显式 room/bed 行按 `normalize_room/bed` 规范化；策略只作用于无归属行（显式行不受影响，逐行判定）。
- `gateway/admin.html`：context 预览带上当前 `session_id`（适配收紧后的 context 鉴权）。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session()` / `resolve_session_id()`（带 3s 缓存），无显式 `VOICE_SESSION_ID` 时先请求 `/api/v3/session/current` 再带 `session_id` 查询敏感上下文，不再依赖网关静默 ambient 回退。

ESP32-S3 固件（`esp32/testpro4`）：

- `main/protocol_packet.{h,cpp}`（新增）：USB packet 常量、CRC16-CCITT、包头/CRC 填充辅助。
- `main/maixsense_parser.{h,cpp}`（新增）：MaixSense 帧解析器模块化（含 buffer_len<2 下溢保护、异常长度帧头跳过、溢出丢旧保新）。
- `main/device_config.{h,cpp}`（新增）：NVS 读写、`CFG?`/`CFGSET`/`CFGRESET`/`REBOOT` 控制台命令、room/bed 完整性校验、topic 小写规范化。
- `main/mqtt_payload.{h,cpp}`（新增）：巴法云 MQTT client（ClientID=UID、自动重连）、`{"payload_b64":...}` JSON 堆分配构造、每 topic 500ms 限速。
- `main/main.cpp`：改为模块 glue；恢复 Wi-Fi STA（事件驱动重连）+ GOT_IP 后启动 MQTT；ToF/MLX 发送路径在 USB CDC 基础上并行 MQTT 发布。
- `main/CMakeLists.txt`：新增源文件与 `esp_wifi esp_netif esp_event lwip mqtt mbedtls esp_timer` 依赖。
- `main/idf_component.yml`：新增 `espressif/mqtt: '^1'`（ESP-IDF v6.0 起 esp-mqtt 移出 IDF 主仓库，本机 `E:\esp\v6.0.1\esp-idf\components\mqtt` 仅剩 test_apps）。

文档：

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/{README,QUICKSTART,CHANGELOG,docs/protocol}.md`：同步 care_event API、context 需显式 session_id、管理鉴权说明、MQTT 恢复状态；修正 protocol.md 中 ToF 输出为「完整原始帧」（旧文与契约/实现矛盾）。

## 架构调整与模块设计

- 遵循既有模块边界：schema/迁移在 `db.py`，管理员认证在 `auth.py`，care_event CRUD 独立在 `care_events.py`（未扩大 `subjects.py`），`gateway.py` 只加路由 glue。
- 固件按交接指南拆出 `protocol_packet` / `maixsense_parser` / `device_config` / `mqtt_payload` 四个模块，`main.cpp` 收敛为 ESP-IDF 初始化、任务创建、硬件调用和 glue（Wi-Fi STA 事件处理属于 IDF glue，留在 main.cpp）。
- `ensure_care_events_schema` 放 `db.py` 并被 `care_events.init_care_events_table()` 复用，避免 db↔care_events 循环依赖。

## 安全边界及鉴权设计

- 密码：PBKDF2-HMAC-SHA256，16B 随机盐，200k 迭代；无明文存储；历史明文行首次登录成功后自动重哈希升级。
- Cookie：只下发随机 `token_urlsafe(32)`；库中仅存 SHA-256(token)；校验按 token hash + `expires_ts` + 账号 active，伪造/过期一律 401；HttpOnly + SameSite=Lax。
- 管理 API：本机豁免仅限白名单（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`），其余（subjects/assignments/memories/credentials/sessions/care events 等）本机也需管理员 Cookie；远程未登录全部 401。
- 模板零泄漏：identity gallery 与 `include_template=1` 保持本机专用（远程 403），face template/credential template 不出机器。
- v3 session 判定（与 `reference/api_contracts.md` 一致）：缺 `actor_subject_id`、`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 过期 → 一律未认证；未认证/越权时 `target.patient`、`assignment`、memory、care_events、sleep/vitals/posture 全部为空，响应中的 `session` 字段也只在授权通过时回显。
- 角色规则：staff/admin 可查任意患者；patient 仅能查自己；无 actor 拒绝（内部 worker 也必须携带能解析到 subject 的 session）。
- `/api/v3/context/chat` 不再隐式使用「最新 ambient session」，必须显式 `session_id`；voice 通过 `/api/v3/session/current`（本机白名单接口，仅会话元数据、无患者数据）解析当前会话后再请求，避免静默漏数据同时保住本地助手链路。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 显式带 room/bed 的行：只写对应床位；能匹配配置床位则用配置的规范名，否则 normalize 后原样落位；策略永不改写显式行。
- 无归属行：`SLEEP_IMPORT_DEFAULT_ROOM/BED` 优先 → `first`（默认，**已修复为 beds[0]**）→ `skip` 跳过 → `all` 仅显式调试；未知策略安全兜底为不导入。
- 同一 CSV 混合两类行时逐行判定（`row_targets` 按行调用），不会整表一刀切；跳过行有计数日志。

## care_event 实现细节

- 表结构：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts` + subject/room-bed 两组（created_ts 与 ts）索引。
- 旧库迁移：`PRAGMA table_info(care_events)` 检查缺列，`ALTER TABLE ADD COLUMN` 补 `severity('info')/source('manual')/created_by('')/ts(0)`，`ts` 用 `created_ts` 回填，旧行全部保留（已用 legacy 老表 + 数据实测验证）。
- API：`POST /api/v3/care/events`（管理员）创建，severity 枚举校验（info/notice/warning/critical），`ts` 缺省取当前时间；`GET /api/v3/care/events` 支持 `subject_id` 或 `room+bed` 过滤 + `limit`（默认 50，上限 200），`ORDER BY ts DESC, created_ts DESC`。
- 规范化：写入与查询都过 `normalize_room/normalize_bed`，小写写入 `r1203/b1` 可被大写 `R1203/B1` 查询命中（probe 通过）。
- 上下文集成：授权通过的 `/api/v3/context/chat` 在 `modalities.care_events` 返回最近 10 条摘要（items+brief），`allowed_sections` 增加 `care_events`；未授权为空。

## ESP32-S3 固件接口对齐说明

- **USB packet**：保持 `[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`；CRC16-CCITT（init 0xFFFF, poly 0x1021）只覆盖 payload；LEN/CRC 小端。行为与改造前一致，只是打包辅助收敛到 `protocol_packet`。
- **ToF payload**：保持完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`（~10022B），未改成仅 10000B 图像区；`docs/protocol.md` 中与实现矛盾的旧描述已修正。
- **NVS**：`project2` 命名空间读取 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；`ssid+uid+host+port+room+bed` 完整才启动网络回传，缺 room/bed 仅保留 USB CDC 并提示 CFGSET；串口命令与 `NVS_CONFIG.md` 保持一致。
- **Topic**：`{room}{bed}tof1/tof2/mlx1/mlx2`，room/bed trim + 小写规范化（R1203/B1 → r1203b1tof1），与 `gateway/bed_config.topics_for()` 一致。
- **MQTT**：`mqtt://{host}:{port}`（默认 bemfa.com:9501），ClientID=UID、空用户名密码，keepalive 60，esp-mqtt 自动重连；JSON `{"payload_b64":"..."}`，base64 为**原始 payload**（ToF 完整原始帧 / MLX 3072B float32），不是完整 USB packet。
- **大 payload 缓冲**：ToF base64 约 13.4KB，JSON 缓冲按需 `malloc`（规避了源代码注释里提示的固定 256B 缓冲坑），MQTT out buffer 提到 16KB；每 topic 500ms 发布限速保护云端中继，USB CDC 仍全帧率。
- **并行性**：`usb_send_tof_payload()` 和 MLX 发送路径先走 USB CDC，再无条件（不依赖 USB 是否连接）尝试 MQTT 发布。
- **依赖**：`main/CMakeLists.txt` REQUIRES 补 `esp_wifi esp_netif esp_event lwip mqtt mbedtls esp_timer`；esp-mqtt 在 IDF v6.0.1 已不随 IDF 内置，经 `idf_component.yml` 的 `espressif/mqtt: '^1'` 从组件仓库解析（REQUIRES 中的 `mqtt` 由组件管理器别名映射）。

## 本地测试与编译验证结果（修改后）

- `python tests\run_public_tests.py project2_task`：**`[public] all public tests passed`**（compile / functional_smoke / refactored_features / smoke_gateway 全过）。
- `python tools\run_debug_probe.py project2_task`：**`[probe] all visible diagnostic checks passed`**（8 项 ok，0 failures；voice 路径 Warning 消失，显示 `voice module appears to reference current-session fetch`）。
- `python tools\run_espidf_build.py project2_task`：
  - 第一次运行在 CMake 配置阶段失败：`Failed to resolve component 'mqtt' required by component 'main': unknown name`，日志显示 `Component directory E:/esp/v6.0.1/esp-idf/components/mqtt does not contain a CMakeLists.txt`（IDF v6.0 该目录仅剩 test_apps）。
  - 在 `idf_component.yml` 增加 `espressif/mqtt: '^1'` 后重跑：**Build finished successfully**，产物 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（0xf0570 bytes，app 分区余 6%），依赖锁包含 esp_tinyusb 2.2.0 / tinyusb 0.19.0~3 / espressif mqtt / idf 6.0.1。最终又复跑一次增量构建确认成功。
- 额外临时脚本验证（临时目录运行、临时 SQLite，未写入 `data/project2.db`、未改动 tests/tools）：
  - 旧 schema care_events 库经 `init_management_db()` 迁移后补齐 4 列、旧行保留、`ts` 回填成功；小写写入大写查询命中；`limit`/倒序正确；缺 room/bed 与非法 severity 被拒。
  - admin_accounts 中无明文密码、salt 存在；第二次 setup 被拒；伪造 token 拒绝、正确 token 通过、错误密码拒绝；库中不存原始 token；遗留明文行登录后自动重哈希且可再次登录。
  - context v3：有效 staff session 放行且含 care_events；无 session 拒绝（not_authenticated，患者/记忆/事件零泄漏）；patient 查他人拒绝（not_authorized_for_target）、查自己放行。

## 未验证的残留技术债与风险

- **未做实机验证**（任务范围明确不要求）：`idf.py flash/monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、巴法云账号限额行为、ToF 上电时序、MLX 实机读数。MQTT 大包（~13.5KB JSON）在真实巴法云免费通道上的吞吐/限流表现未实测，已用 500ms/topic 限速缓释；若云端仍拒绝大包，需要实机调 `MQTT_MIN_PUBLISH_INTERVAL_MS` 或压缩策略。
- Wi-Fi 断线采用事件内立即 `esp_wifi_connect()` 重试（无退避）；弱网环境可能日志较密，属可接受的联调行为，可后续加退避。
- `sdkconfig.defaults` 保留了历史 `CONFIG_FREERTOS_UNICORE=y`，Wi-Fi/MQTT/USB/解析同核运行；编译通过且带宽估算可行，但高负载下的实时性需实机确认（未改动以免引入新行为差异）。
- 管理端 `/api/v2/*` 对远程仍要求管理员 Cookie（本机 worker 不受影响）；若未来有远程采集端直推 HTTP 的需求，需要单独的设备凭证机制（当前数据链路走巴法云订阅，不受影响）。
- `admin.html` 存在历史遗留的个别中文字符串乱码（本次未触碰的区域），不影响功能；建议后续统一重新保存为 UTF-8。
- voice 的 current-session 解析有 3s 缓存：护士站换人后最多 3s 内仍可能使用上一个会话（可用 `GATEWAY_SESSION_CACHE_TTL_S` 调整）；语音链路完整端到端（ASR/RKLLM 实机）未在本机跑通，仅验证了上下文获取路径的代码逻辑与探针检查。
- 旧库迁移目前只针对 `care_events`（任务重点）；其他表如有更老的历史 schema 变体，仍需按同一模式扩展 `ensure_*_schema`。
