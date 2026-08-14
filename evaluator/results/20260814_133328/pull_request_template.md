# Pull Request 提测说明 (Pull Request Template)

本文件记录本次 Sprint 的最终实现说明。CI 与 Reviewer 会对本自检报告与实际 diff、自检日志做交叉一致性校验。

## 初始自检诊断（修改前）

修改前在 workspace 根目录运行（Linux 等价命令）：

```text
../.venv/bin/python tests/run_public_tests.py project2_task
../.venv/bin/python tools/run_debug_probe.py project2_task
```

结果：

- `run_public_tests.py`：4 个公开测试文件全部通过（compile / functional smoke / refactored features / smoke gateway）。公开测试本身不校验安全属性。
- `run_debug_probe.py`：**6 项失败 + 1 条 voice Warning**：
  1. `management API rejects missing cookie` — 无 Cookie 请求 `/api/v3/subjects` 返回 200 并带出数据；
  2. `management API rejects forged cookie` — 伪造 Cookie 同样返回 200（session 查询不校验 token hash）；
  3. `unknown identity session is denied` — `identity_state=unknown` 的 session 被当作已认证；
  4. `expired session is denied` — `expires_ts` 过期未检查；
  5. `care_event write rejects missing admin cookie` — `POST /api/v3/care/events` 路由不存在，返回 404；
  6. `care_event normalizes room/bed for create and query` — 小写 `r1203/b1` 写入后大写查询查不到。
- Voice Warning：`voice_assistant_integrated.py` 未引用当前会话获取逻辑，收紧鉴权后本地助手可能取不到上下文。
- ESP32-S3 `testpro4`：`main.cpp` 中 Wi-Fi/MQTT 回传整体缺失（TODO 注释），`main/CMakeLists.txt`/`idf_component.yml` 缺少网络组件依赖，尚未跑编译。

## 修改的文件列表

### Gateway（Python）

- `gateway/auth.py`：管理员密码改为「随机盐 + PBKDF2-HMAC-SHA256」；`admin_account_exists()` 改为真实查库；`get_admin_http_session()` 按 token hash 精确匹配并检查过期；历史明文密码行在首次成功登录时自动重哈希；响应中不再泄漏 `token_hash`。
- `gateway/gateway.py`：管理 API 统一要求有效管理员 Cookie（本机请求不再放行）；本机 worker 例外收窄到指定服务接口（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/session/current`、`/api/v3/identity/gallery|match`、`/api/v3/vision/observation`）；`session_is_authenticated()`/`actor_can_access_target()` 按契约收紧；`build_chat_context_v3()` 支持管理员 Cookie 作为认证 actor、未授权时彻底清空 `target/actor/modalities`；新增 `POST/GET /api/v3/care/events` 路由。
- `gateway/db.py`：`care_events` 新 schema（`severity/source/created_by/ts`）+ `migrate_care_events_table()` 旧表迁移（PRAGMA table_info 检查缺列、ALTER TABLE 补列、`ts=created_ts` 回填，旧行不丢）。
- `gateway/care_events.py`：care_event CRUD（room/bed trim+大写规范化、subject 存在性校验、`limit` 与 `ts/created_ts` 倒序）、`build_care_events_context()` 摘要，模块不再只是 TODO 骨架。
- `gateway/sleep_importer.py`：`SLEEP_IMPORT_UNSCOPED_POLICY=first` 修正为写入第一个配置床位（原实现误取 `beds[-1]`）。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session()`（读 `/api/v3/session/current`），`fetch_gateway_chat_context()` 在无显式 `VOICE_SESSION_ID` 时先取当前会话再显式携带 `session_id` 请求 v3 上下文。

### ESP32-S3 固件（`esp32/testpro4`）

- 新增 `main/protocol_packet.{h,cpp}`：USB 包常量（`AA 55`、TYPE=0x01 MLX / 0x02 ToF）、CRC16-CCITT（初始 0xFFFF、多项式 0x1021）、包头/CRC 小端序构造。
- 新增 `main/maixsense_parser.{h,cpp}`：MaixSense 帧解析器（`00 FF ... DD`），处理噪声、分块/半帧、坏尾字节、异常长度与缓冲区溢出；ToF payload 保持完整原始帧，不裁剪成 10000B 图像区。
- 新增 `main/device_config.{h,cpp}`：NVS namespace `project2` 配置读写（`wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`）、完整性校验（ssid+uid+room+bed）、`CFG?/CFGSET/CFGRESET/REBOOT` 串口命令。
- 新增 `main/mqtt_payload.{h,cpp}`：topic 小写拼接 `{room}{bed}tof1/tof2/mlx1/mlx2` 与 `{"payload_b64":"<base64>"}` JSON 构造（mbedtls base64，容量上限校验）。
- 新增 `main/network_backhaul.{h,cpp}`：Wi-Fi STA（esp_wifi/esp_netif/esp_event）+ 巴法云 MQTT 客户端（`mqtt://bemfa.com:9501`，client id/username/password = UID，断线自动重连）。
- `main/main.cpp`：改为模块 glue；`usb_send_tof_payload()` 与 MLX 发送路径在保留 USB CDC 输出的同时向对应 MQTT topic 并行发布原始 payload；启动顺序为 NVS → 配置 → 网络回传 → USB → ToF 初始化 → MLX → 任务。
- `main/CMakeLists.txt`：补齐 `esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls` 依赖并登记新源文件。
- `main/idf_component.yml`：新增 `espressif/mqtt: '^1.0.0'`。

### 文档

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`CHANGES.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md`：同步管理员鉴权、v3 上下文权限、care_event API、睡眠 CSV 按行归属策略、ESP32 Wi-Fi+MQTT 回传与编译自检说明。

## 架构调整与模块设计

- 认证逻辑收敛在 `gateway/auth.py`，路由只做 glue；care_event CRUD 放 `gateway/care_events.py`，schema/迁移放 `gateway/db.py`，未把业务逻辑塞回 `gateway.py`。
- 固件按「协议常量 / 帧解析 / 设备配置 / MQTT 封装 / 网络回传 / main glue」拆成 6 个文件，纯协议逻辑不再堆在 `main.cpp`。
- v3 context 授权判定统一走 `session_is_authenticated()` + `actor_can_access_target()`，未授权响应结构固定裁剪为空对象，避免散落的 if 判断导致数据泄漏。

## 安全边界及鉴权设计

- 管理员密码不落明文：PBKDF2-HMAC-SHA256（16 字节随机盐，20 万次迭代）；旧明文行登录时自动迁移重哈希。
- Cookie 只携带随机 token（`secrets.token_urlsafe(32)`），数据库只存 SHA-256(token)；每次校验按 token hash 精确查找并检查 `expires_ts`，伪造/过期 Cookie 一律 401。
- 管理 API（subjects/assignments/memories/credentials/sessions/care events 等）无论本机或远程都必须带有效管理员 Cookie；远程未登录请求同样被拒，不能导出 face/credential template（`include_template` 仅限本机服务）。
- 本机 worker 例外仅限指定服务接口（见上），`/api/v3/session/current` 仅本机可取，用于 voice 显式携带会话。
- v3 session 视为未认证的条件：`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 过期、缺少 `actor_subject_id`。
- 授权：staff/admin 可查看任意目标患者；patient 只能查看自己；未授权时 `target.patient/assignment`、`modalities`（含记忆与护理事件）全部为空，reason 明确区分 `not_authenticated` / `not_authorized_for_target`。
- voice 通过 `/api/v3/session/current` 取当前会话并显式传 `session_id`，不再依赖静默 ambient session 泄漏数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 按「行」执行归属策略，同一 CSV 内显式 `room/bed` 行与无归属行可混排：
  - 行带 `room/bed`：只写入对应床位，策略不作用于该行；
  - 行不带：设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位；否则 `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 第一个配置床位；`skip` → 跳过；`all` 仅为显式调试模式，不是默认行为。
- 修复了 `first` 误取最后一个床位（`beds[-1]`）的缺陷；未知策略宁可跳过也不广播。

## care_event 实现细节

- 表：`care_events(event_id PK, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts)`，索引覆盖 subject 与 room+bed，按 `ts` 倒序。
- 旧表迁移：`PRAGMA table_info` 检查缺列 → `ALTER TABLE ADD COLUMN`（severity/source/created_by/ts）→ `UPDATE care_events SET ts=created_ts WHERE ts=0`，旧行保留。
- 路由：`POST /api/v3/care/events`（管理员登录，400 校验错误）；`GET /api/v3/care/events?subject_id= | room=+bed= | limit=`（管理员登录，默认 50 条，`ts/created_ts` 倒序）。
- room/bed 写入与查询都做 trim + 大写规范化：`r1203/b1` 写入可用 `R1203/B1` 查到。
- `/api/v3/context/chat` 授权通过时在 `modalities.care_events` 返回最近事件摘要（items + brief），未授权返回空。

## ESP32-S3 固件接口对齐说明

- 恢复 Wi-Fi STA 初始化与 MQTT 客户端连接；broker 默认 `bemfa.com:9501`（NVS 可配 host/port），MQTT client id/username/password 使用巴法云 UID。
- 从 NVS 读取并校验 `ssid/password/uid/room/bed`；任一缺失则不启动网络回传、仅走 USB CDC 并打印配置帮助。
- topic 使用规范化后的 `{room}{bed}tof1/tof2/mlx1/mlx2` 小写拼接。
- MQTT JSON 为 `{"payload_b64":"..."}`，base64 内容是传感器原始 payload（ToF 为完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`，MLX 为 768×float32=3072B），不是完整 USB packet；编码缓冲按 16KB 校验上限，避免大 payload 溢出。
- `usb_send_tof_payload()` 与 MLX 发送路径在保留 USB CDC 输出的同时向对应 MQTT topic 发布原始 payload，双通道并行。
- USB packet 契约保持 `[AA 55][TYPE][ID][LEN_L LEN_H][PAYLOAD][CRC_L CRC_H]`，CRC16-CCITT（0xFFFF/0x1021）只覆盖 payload，LEN 与 CRC 小端序。
- `main/CMakeLists.txt` 补齐 `esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls` 依赖；`idf_component.yml` 增加 `espressif/mqtt: ^1.0.0`。

## 本地测试与编译验证结果（修复后）

```text
../.venv/bin/python tests/run_public_tests.py project2_task
```

结果：**全部通过**（compile / functional smoke / refactored features / smoke gateway）。

```text
../.venv/bin/python tools/run_debug_probe.py project2_task
```

结果：**全部通过** — admin setup 200、管理 API 拒绝缺失/伪造 Cookie、接受有效 Cookie、unknown/expired session 被拒、care_event 无 Cookie 写入 401、room/bed 规范化查询命中；voice 已引用 current-session 获取；无失败项。

```text
../.venv/bin/python tools/run_espidf_linux_build.py project2_task
```

结果：**ESP-IDF v6.0 编译成功**（Linux runner，`/home/xiaoming/.espressif/tools`）。`stdpro.bin` 生成（大小 0xeefb0 ≈ 978KB，最小 app 分区 0x100000，剩余 7%）；bootloader 0x5760。修复过程中曾遇到并解决：`network_backhaul.cpp` 命名空间内未限定 `DeviceConfig` 的编译错误、Wi-Fi 配置 `snprintf` 的 `-Werror=format-truncation` 告警。未执行 flash/monitor（按规范要求）。

补充本地验证（临时 SQLite，未污染 `data/project2.db`）：

- 密码哈希落库验证（非明文、32 位盐）、重复 setup 拒绝、错误密码拒绝、登录成功。
- 旧 schema `care_events` 库初始化后补列成功、旧行保留、`ts` 回填。
- 无 Cookie/伪造 Cookie 的管理 API 全部 401；本机服务接口（v2 ingest/latest、esp、context/chat、session/current、identity/gallery/match、vision/observation）无 Cookie 仍可调用。
- care_event HTTP 往返（小写写入、大写查询命中、按 subject 查询、无 Cookie 401）。
- 上下文 RBAC：staff 全量、patient 只看自己、patient 越权拒绝且响应无患者明细、无会话/过期/缺 actor 拒绝、管理员 Cookie 视为认证 actor。
- 睡眠 CSV：显式行只写对应床位、无归属行 first→首床、DEFAULT_ROOM/BED 覆盖、skip 跳过、all 显式广播，混排行互不影响。

## 未验证的残留技术债与风险

1. **ESP32 未做实机验证**：未执行 `idf.py flash/monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序与 MLX90640 实机读数均未验证（任务规范不要求）。巴法云 MQTT 的认证参数按常见约定（client id/username/password 均为 UID）实现，若巴法云侧有差异需在实机联调时确认。
2. **MQTT 大包断网时的行为**：链路未连接时 `publish()` 直接丢弃帧（不排队），弱网下会有数据空洞；如需保证完整回放需要引入有界发送队列。
3. **NVS 非强安全存储**：Wi-Fi 密码与 UID 以明文存在 NVS，部署建议已在 `NVS_CONFIG.md` 标注（NVS/flash encryption、每设备独立 token）。
4. **管理员会话清理**：过期的 `admin_http_sessions` 行目前只靠查询过滤，没有后台清理任务，长期运行会有少量垃圾行（不影响鉴权正确性）。
5. **`all` 归属策略**未在真实多床睡眠导出文件上回归，仅按行策略单测覆盖。
6. **远程来源判定依赖 client_address**：WSL/容器网络环境下非回环地址一律按远程处理，需要管理员登录后才能访问服务接口；如果现场反向代理（如 Nginx）转发本地请求，需在代理层做来源控制或补 X-Forwarded-For 白名单。
