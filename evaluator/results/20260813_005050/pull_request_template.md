# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行命令及关键结果（运行环境：Windows 10 + Git Bash，Python 3.14）：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

`run_public_tests.py` 初始结果：4 个公开测试文件（compile / functional_smoke / refactored_features / smoke_gateway）全部通过（公开冒烟测试不检查安全属性，通过不代表无缺陷）。

`run_debug_probe.py` 初始结果：**6 项失败**：

| 检查项 | 初始结果 |
|--------|----------|
| management API rejects missing cookie | FAIL：本机请求无 Cookie 也返回 200（`_authorized_for_api` 对本机请求全放行） |
| management API rejects forged cookie | FAIL：伪造 Cookie 返回 200（`get_admin_http_session` 忽略 token，抓取任意活跃会话） |
| unknown identity session is denied | FAIL：`identity_state=unknown` 的会话被当作已认证（`session_is_authenticated` 明确跳过 unknown 检查） |
| expired session is denied | FAIL：过期会话未校验 `expires_ts` |
| care_event write rejects missing admin cookie | FAIL：`POST /api/v3/care/events` 返回 404（路由未接线） |
| care_event normalizes room/bed for create and query | FAIL：小写 `r1203/b1` 写入后，大写 `R1203/B1` 查询不到（无规范化） |
| voice bridge hint | Warning：voice 模块未显式获取当前会话，依赖网关隐式 ambient session |

另经代码审阅确认的遗留缺陷：

- `auth.py`：新密码无盐、以明文入库；`admin_account_exists()` 恒为 False（TODO stub）。
- `db.py`：`care_events` 表缺少 `severity/source/created_by/ts` 列，且无旧表迁移逻辑。
- `sleep_importer.py`：`SLEEP_IMPORT_UNSCOPED_POLICY=first` 误用 `beds[-1]`（最后一个床位），与「第一个配置床位」语义不符。
- `gateway.py`：`DEFAULT_ADMIN_SUBJECT_ID` 未导入（`ADMIN_AUTH_ENABLED=0` 时运行会 NameError）。
- `esp32/testpro4`：Wi-Fi + MQTT 回传整体缺失（TODO），CMake 依赖未补齐。

## 修改的文件列表

Gateway（Python）：

- `gateway/auth.py` — 修复：密码一律「随机盐 + PBKDF2-HMAC-SHA256」入库；`admin_account_exists()` 改为查库；`get_admin_http_session()` 严格按 token hash 匹配并校验过期；`login_admin_account()` 对历史明文账户（空 salt）做常量时间校验并在首次成功登录时自动迁移为加盐哈希。
- `gateway/gateway.py` — 修复：`_authorized_for_api()` 只对「管理员会话有效」或「本机请求 + 白名单服务路径」放行，管理 API 一律要求 Cookie；`session_is_authenticated()` 拒绝 unknown 身份 / 无 assurance / 缺 actor / 过期会话；`actor_can_access_target()` 对无法解析 actor 的会话拒绝访问；新增 `GET/POST /api/v3/care/events` 路由；`/api/v3/context/chat` 增加 `modalities.care_events`；导入 `DEFAULT_ADMIN_SUBJECT_ID`；gallery/credential template 导出收紧为「管理员登录或本机服务」。
- `gateway/db.py` — 新增 `_ensure_care_events_columns()`：`PRAGMA table_info` 检查旧表，`ALTER TABLE ADD COLUMN` 补齐 `severity/source/created_by/ts`，旧数据保留。
- `gateway/care_events.py` — 重写：`create_care_event`/`list_care_events`（room/bed 大小写规范化、limit、按 `ts/created_ts` 倒序）、`build_care_events_context` 上下文摘要。
- `gateway/sleep_importer.py` — 修复：`first` 策略改为 `beds[0]`；显式 room/bed 行按行规范化写入；无归属行按策略处理，`all` 仅作显式调试模式。
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session()`/`resolve_session_id()`：请求敏感上下文前先经 `GET /api/v3/session/current` 显式获取当前视觉会话并携带 `session_id`，不再依赖隐式 ambient session。
- 文档同步：`README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`。

ESP32-S3 固件（`esp32/testpro4/`）：

- `main/protocol_packet.{h,cpp}`（新增）— USB packet 常量、CRC16-CCITT（init 0xFFFF / poly 0x1021，只覆盖 payload）、header/CRC 打包辅助（小端序）。
- `main/maixsense_parser.{h,cpp}`（新增）— MaixSense 帧解析器：噪声字节、分块接收、坏尾字节、异常长度（0 或 >10032）与半帧处理；输出完整原始帧（帧头+长度+META+IMG+校验+帧尾），不裁剪 10000B 图像区。
- `main/device_config.{h,cpp}`（新增）— NVS 读写（`wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`）、串口控制台（CFG?/CFGSET/CFGRESET/REBOOT）、location/network 就绪判定、topic 小写拼接 `{room}{bed}{kind}`。
- `main/mqtt_payload.{h,cpp}`（新增）— `{"payload_b64":"..."}` JSON 构造（mbedtls base64，按 payload 长度动态分配 heap 缓冲，避免小栈溢出）。
- `main/device_network.{h,cpp}`（新增）— Wi-Fi STA 初始化与重连、`espressif/mqtt` 客户端（broker `mqtt://{bemfa_host}:{bemfa_port}`，client_id=UID，buffer 16KB）、非阻塞网络任务。
- `main/main.cpp` — 清理纯协议逻辑至上述模块；`usb_send_tof_payload()` 与 MLX 发送路径保留 USB CDC 输出并并行发布 tof1/tof2/mlx1/mlx2 原始 payload；启动流程加入网络回传初始化。
- `main/CMakeLists.txt` — 补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖与新源文件。
- `main/idf_component.yml` — 增加 `espressif/mqtt: ^1.0.0`。
- 文档同步：`README.md`、`CHANGELOG.md`、`docs/protocol.md`。

未修改：`tests/`、`tools/`、`components/mlx90640/`、`usb_descriptors.c`、`tusb_config.h`。

## 架构调整与模块设计

保持既有模块边界，`gateway.py` 只留 HTTP 路由与 glue：

- 鉴权：`auth.py`（账号/会话） + `gateway.py`（HTTP 层判定）。判定逻辑统一为：管理员会话有效 → 放行；否则仅「本机 loopback 请求 + 白名单服务路径」放行；其余 401。白名单仅含 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`。
- 会话授权：`session_is_authenticated()` 要求 `identity_state∈{recognized,...}`、`assurance_level∉{none,空}`、`actor_subject_id` 非空、`expires_ts` 未过期；`actor_can_access_target()` 中 admin/staff 可访问任意目标，patient 仅可访问自己，无法解析 actor 的会话一律拒绝。
- care_event：CRUD 在 `care_events.py`，表迁移在 `db.py`，路由 glue 在 `gateway.py`，上下文聚合在 `build_chat_context_v3()`。
- 睡眠导入：`sleep_importer.py` 按行决策归属，与 `gateway.py` 解耦（依赖注入 normalizer/replace_items）。
- 固件：协议/配置/网络逻辑拆为 5 个模块，`main.cpp` 保留 ESP-IDF 初始化、任务创建与硬件调用。

## 安全边界及鉴权设计

- 管理员密码：只存「随机 16B 盐 + PBKDF2-HMAC-SHA256（200k 轮）」哈希，绝不明文入库；历史明文遗留账户在首次成功登录时自动迁移（迁移前仍可登录，迁移后即销毁明文）。密码比对使用 `hmac.compare_digest`。
- Cookie 会话：Cookie 只保存 `secrets.token_urlsafe(32)` 随机 token；数据库只保存 token 的 SHA-256 哈希；服务端按 token hash 精确匹配并校验 `expires_ts`，伪造/缺失 Cookie 一律 401；logout 删除会话记录并使 Cookie 失效。
- 管理 API：所有 `/api/v3/*` 管理接口（subjects/assignments/memories/credentials/sessions/care events）必须携带有效管理员 Cookie，即使请求来自 127.0.0.1 也不例外。
- 数据导出：face gallery / credential template 仅限管理员登录或本机服务，远程未登录用户 403/401。
- 患者数据零泄漏：v3 上下文在未认证/越权时返回 `policy.allowed=false`、空 `modalities`、空 `target.patient`，不含记忆与护理事件；patient 角色只能读取自己的目标。
- 本机 worker 链路：vision（`/api/v3/vision/observation`、`/api/v3/identity/gallery`）、posture（`/api/v2/*`、`/api/esp/set/latest`）、voice（`/api/v3/session/current` + `/api/v3/context/chat`）均为本机调用，落在白名单内，联调不受影响。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行决策（同一 CSV 内显式行与无归属行可混合）：

1. 行带 `room/bed`：规范化（大写）后只写入对应床位；与配置床位大小写不敏感匹配时使用配置中的标准写法。
2. 行不带 `room/bed`：
   - 设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位。
   - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位（修复了原实现误用最后一个床位的 bug）。
   - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过。
   - `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 广播所有床位，仅作为显式调试模式，不能作为默认行为。
   - 未识别策略 → 安全起见不导入（不扩散）。
3. 策略只作用于无归属行，不会修改或丢弃显式归属行。已验证混合 CSV：显式行进 r1203b2，无归属行进首个床位 r1203b1。

## care_event 实现细节

- 表：`care_events(event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts)`，索引 `(subject_id, created_ts DESC)`、`(room, bed, created_ts DESC)`。
- 迁移：旧表缺 `severity/source/created_by/ts` 时 `ALTER TABLE ADD COLUMN`（默认 `info/manual/''/0`），旧行保留（已用 legacy 库验证）。
- CRUD：`create_care_event` 校验 subject 存在、room/bed 必填并统一大写；`list_care_events` 支持 `subject_id` 或 `room+bed` 过滤与 `limit`（默认 20，上限 500），按 `COALESCE(ts, created_ts)` 倒序。小写写入可用大写查询命中。
- 路由：`POST /api/v3/care/events`（需管理员登录）；`GET /api/v3/care/events?subject_id=...|room=...&bed=...&limit=...`（需管理员登录）。
- 上下文：`/api/v3/context/chat` 授权通过且存在 target subject 时，`modalities.care_events` 返回最近事件摘要（items + brief），并加入 brief/prompt_hints；未授权时返回空结构。

## ESP32-S3 固件接口对齐说明

- **Wi-Fi STA**：恢复 `esp_netif`/`esp_wifi` 初始化，断线自动重连（最多 8 次，此后由 MQTT auto-reconnect 兜底）。
- **MQTT 客户端**：`espressif/mqtt ^1.0.0`，broker `mqtt://{bemfa_host}:{bemfa_port}`（NVS 配置，默认 bemfa.com:9501），ClientID = NVS `bemfa_uid`；buffer/out_size 16KB 以承载 ~13.4KB 的 ToF base64 消息。
- **NVS**：读取并校验 `wifi_ssid/wifi_pass/bemfa_uid/room/bed`；网络就绪需四者齐备，缺配置时保持 USB-only 采集并在串口提示（`CFGSET` + `REBOOT` 生效）。
- **topic**：`{room}{bed}{kind}` 小写拼接（r1203b1tof1 / tof2 / mlx1 / mlx2），由 `device_config_build_topic()` 生成，不落盘。
- **MQTT JSON**：`{"payload_b64":"<base64 原始 payload>"}`，base64 内容是传感器原始 payload（ToF 为完整 MaixSense 原始帧、MLX 为 3072B float 数组），**不是**完整 USB packet；JSON 缓冲按 payload 长度动态 malloc。
- **并行回传**：`usb_send_tof_payload()` 与 MLX 发送路径保留 USB CDC 输出，同时发布对应 MQTT topic。
- **USB packet 契约不变**：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 只覆盖 payload，LEN/CRC 小端序。
- **ToF payload**：保持完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`，未裁剪图像区；解析器新增噪声/坏尾/异常长度/半帧处理。

## 本地测试与编译验证结果

修复后运行的命令与结果：

```powershell
python tests\run_public_tests.py project2_task
# 结果：4/4 公开测试文件全部通过（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway）

python tools\run_debug_probe.py project2_task
# 结果：全部检查通过（admin 鉴权 3 项、unknown/expired 会话拒绝 2 项、care_event 鉴权与规范化 2 项、voice session 引用提示 1 项）

python tools\run_espidf_build.py project2_task
# 结果：编译成功（EXIT=0），生成 stdpro.bin（0xf0220 字节），bootloader 0x5760 字节
```

额外的本地验证（临时库、未改动 tests/tools）：

- legacy 库迁移：旧 `care_events`（缺 4 列）经 `init_management_db()` 自动补列，旧行保留。
- 旧明文管理员账户登录后自动迁移为加盐哈希；新账户入库即加盐哈希。
- HTTP 端到端：无 Cookie/伪造 Cookie 访问 subjects → 401；登录后 200；care/events 无 Cookie POST/GET → 401；带 Cookie 小写写入 + 大写查询命中；授权上下文含 care_events；patient 查他人上下文被拒且无 care_events；未知身份会话拒绝。
- 睡眠混合 CSV：显式行→对应床位，无归属行→首床位（`first`）。

## 未验证的残留技术债与风险

1. **ESP32 实机链路未验证**：本任务环境完成了 Windows EIM（ESP-IDF v6.0.1）编译通过，但未执行 `idf.py flash/monitor`，未验证真实 Wi-Fi/MQTT 连通、巴法云 UID 有效性、ToF 上电时序、MLX 实机读数与 USB 枚举（任务明确不要求，如实记录）。
2. **巴法云 MQTT 主题命名**：按 `reference/espidf_protocol_contract.md` 与 gateway `topics_for()` 以 `{room}{bed}{kind}` 直发（与 TCP 订阅 topic 一致）；若巴法云侧实际要求带 UID 前缀的 topic，需在实机联调时确认。
3. **旧明文密码迁移**：迁移只在「登录成功」时发生；从未再登录的旧明文行仍保留在库中，需运维侧强制改密或人工清理。
4. **语音链路依赖视觉会话**：voice 现在显式拉取 `/api/v3/session/current`，若护士站视觉未识别到人（无 recognized session），语音对患者类意图只回复权限提示（符合设计，但需确认板端用户体验预期）。
5. **上下文音量**：care_events/memory 注入前 10/5 条摘要，长期数据增多后需考虑按严重度/时间窗口二次压缩。
6. **固件内存**：ToF 帧 8FPS×2 路 + MLX 4FPS×2 路并发发布时 MQTT outbox 压力未实测，必要时需降频或增大 outbox。
