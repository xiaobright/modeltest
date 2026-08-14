# Pull Request 提测说明 (Pull Request Template)

本次 PR 完成 Project2 护理/睡眠 gateway 的提测修复：管理员认证与 Cookie 会话、
v3 授权上下文权限裁剪、care_event 护理事件全链路、睡眠 CSV 按行归属策略、
ESP32-S3 固件 Wi-Fi + MQTT 巴法云回传恢复与模块化整理，以及相关文档同步。

## 初始自检诊断

修改前运行（2026-08-14，Ubuntu 24.04 / WSL）：

`python tests/run_public_tests.py project2_task` —— 4 个公开 smoke 文件全部通过
（仅验证可编译与路由存在，不验证安全属性）。

`python tools/run_debug_probe.py project2_task` —— exit 1，6 项 FAIL + 1 项 Warning：

```text
[probe:FAIL] management API rejects missing cookie status=200   <- 本机无 Cookie 仍可读 subjects
[probe:FAIL] management API rejects forged cookie status=200    <- get_admin_http_session 忽略 token，任意取一个活跃会话
[probe:FAIL] unknown identity session is denied policy={allowed: True}   <- session_is_authenticated 对 unknown 放行
[probe:FAIL] expired session is denied policy={allowed: True}           <- 未校验 expires_ts
[probe:FAIL] care_event write rejects missing admin cookie status=404   <- /api/v3/care/events 路由缺失
[probe:FAIL] care_event normalizes room/bed for create and query rows=[] <- 大小写不一致查询不到
[probe:Warning] Voice/assistant path: voice 未显式获取当前会话
```

## 修改的文件列表

gateway：

- `gateway/auth.py` —— PBKDF2-HMAC-SHA256 加盐哈希（修复明文落库）、按 token 哈希
  校验会话（修复任意会话/伪造 Cookie 放行）、admin_account_exists 改为查库、
  兼容历史明文账户并登录后自动迁移为哈希。
- `gateway/gateway.py` —— `_authorized_for_api` 收紧：本机例外只覆盖固定服务接口
  清单，管理 API 本机访问也要求有效 Cookie；新增 `POST/GET /api/v3/care/events`
  路由；`session_is_authenticated`/`actor_can_access_target` 按契约收紧；
  v3 context 增加 `modalities.care_events`；admin logout 不再要求 JSON body。
- `gateway/care_events.py` —— CRUD、room/bed 大写规范化、旧表缺列迁移
  （severity/source/created_by/ts + 回填）、最近事件上下文摘要。
- `gateway/db.py` —— care_events 表结构与迁移下沉到 care_events.py 并延迟调用，
  避免循环依赖。
- `gateway/sleep_importer.py` —— 按行归属策略修复：`first` 策略改为真正写入第一个
  配置床位（原为 `beds[-1]`）；显式行与无归属行混排时互不影响；目标床位规范化。
- `gateway/sensor_store.py` —— `_bed_key` 统一大写规范化，避免大小写分裂缓存键。

voice：

- `voice/voice_assistant_integrated.py` —— 新增 `fetch_current_session()`：本地助手
  显式从 `/api/v3/session/current` 同步当前视觉会话并把 `session_id` 携带到
  `/api/v3/context/chat`，不再依赖隐式 ambient session（`GATEWAY_SESSION_SYNC=1`
  默认开启，可用环境变量关闭）。

ESP32-S3（esp32/testpro4）：

- 新增 `main/protocol_packet.{h,cpp}`、`main/maixsense_parser.{h,cpp}`、
  `main/device_config.{h,cpp}`、`main/mqtt_payload.{h,cpp}`、
  `main/network_backhaul.{h,cpp}`；`main/main.cpp` 重写为 glue（初始化/任务/
  硬件调用/模块编排）。
- `main/CMakeLists.txt` 补齐 `esp_wifi / esp_netif / esp_event / lwip / mqtt /
  mbedtls` 依赖；`main/idf_component.yml` 增加 `espressif/mqtt`（v6.0 已将 mqtt
  移出 IDF 源码树，锁定 1.0.0 与构建环境组件镜像一致）。

文档：

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、
  `esp32/testpro4/{README,QUICKSTART,CHANGELOG}.md`、`esp32/testpro4/docs/protocol.md`、
  `CHANGES.md` —— 同步 care_event、鉴权边界、睡眠归属策略与固件 MQTT 契约。

## 架构调整与模块设计

保持既有模块边界：`gateway.py` 只放路由 glue，认证留在 `auth.py`，care_event 的
schema/迁移/CRUD 集中在 `care_events.py`（不扩大 `subjects.py`），睡眠归属在
`sleep_importer.py`。固件侧按交接建议拆分协议包（protocol_packet）、MaixSense 解析
（maixsense_parser）、NVS 配置与 topic 规范化（device_config）、payload_b64 JSON 与
topic 发布（mqtt_payload）、Wi-Fi + MQTT 生命周期（network_backhaul），main.cpp 不再
堆放纯协议逻辑。

## 安全边界及鉴权设计

- 管理员密码 PBKDF2-HMAC-SHA256（200k 迭代、随机盐）哈希落库，绝不存明文；
  历史明文账户登录成功后即时迁移为哈希。
- Cookie 只保存随机 token（token_urlsafe(32)）；数据库只保存 token 的 SHA-256 哈希。
- 会话校验按 token 哈希精确匹配并检查过期与账户状态：缺失/伪造/过期 Cookie 一律 401。
- 管理 API（subjects/assignments/memories/credentials/care_events 等）即使来自本机
  也要求有效管理员 Cookie；本机 worker 例外仅限
  `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、
  `/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`。
- 远程用户不能导出 face/credential template（identity gallery 与 include_template 仍限本机）。
- v3 会话契约收紧：`identity_state=unknown`、`assurance_level=none/空`、已过期、
  缺少 `actor_subject_id` 一律视为未认证；`actor_can_access_target` 在无 actor 时
  不再兜底放行；未授权时 `target.patient/assignment`、`modalities`（含 memory 与
  care_events）全部为空，不泄露患者明细。
- voice 显式携带会话获取上下文，未认证时只收到权限提示，不静默取数。

## 睡眠 CSV 无 room/bed 时的特殊处理

归属策略按行执行，同一 CSV 内显式 room/bed 行与无归属行可混排、互不影响：

- 行带 room/bed：只写入该床位（大小写不敏感匹配配置床位，未配置床位按行内值写入）。
- 行不带 room/bed：1) 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 时写入指定床位；
  2) `SLEEP_IMPORT_UNSCOPED_POLICY=first` 写入第一个配置床位（默认策略，
  修复了原先误写最后一个床位的 bug）；3) `skip` 跳过该行；
  4) `all` 仅作为显式调试模式，不会成为默认行为。
- 所有目标床位经 `normalize_room/normalize_bed` 规范化后写入。

## care_event 实现细节

- 表结构含 `event_id/subject_id/room/bed/kind/title/content/severity/source/
  created_by/ts/created_ts/updated_ts`；初始化时对旧表执行
  `PRAGMA table_info` 检查并 `ALTER TABLE ADD COLUMN` 补齐缺失列，
  `ts` 从 `created_ts` 回填，旧行全部保留。
- `POST /api/v3/care/events` 需管理员登录；`GET /api/v3/care/events` 支持
  `subject_id` / `room+bed` / `limit` 过滤，按 `ts, created_ts` 倒序。
- room/bed 统一大写规范化存储与查询：小写 `r1203/b1` 写入可用大写 `R1203/B1`
  查询命中。
- `/api/v3/context/chat` 授权通过时返回 `modalities.care_events` 最近事件摘要
  （并进入 brief 与 prompt_hints）；未授权时不返回任何护理事件内容。

## ESP32-S3 固件接口对齐说明

- 恢复 Wi-Fi STA 初始化与 MQTT 客户端（esp-mqtt，`client_id = bemfa UID`，
  `mqtt://bemfa.com:9501`，断线自动重连）；配置不完整（缺
  ssid/uid/room/bed）时保持 USB-only 模式并打印配置帮助。
- NVS（namespace `project2`）读取并校验
  `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；
  `CFGSET/CFG?/CFGRESET/REBOOT` 命令保持不变。
- topic 规范化小写拼接 `{room}{bed}tof1/tof2/mlx1/mlx2`（R1203/B1 → r1203b1tof1）。
- MQTT 消息 `{"payload_b64":"..."}`：base64 内容是传感器原始 payload
  （MLX: 768×float32=3072B；ToF: 完整 MaixSense 原始帧
  `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`），不含 USB 包头与 CRC；
  大 payload 使用 17KB 静态缓冲 + mbedtls base64 编码，避免小缓冲溢出。
- `usb_send_tof_payload()` 与 MLX 发送路径保留 USB CDC 输出的同时向对应 MQTT
  topic 并行发布原始 payload。
- USB packet 契约不变：`[AA 55][TYPE][ID][LEN_L LEN_H][PAYLOAD][CRC_L CRC_H]`，
  CRC16-CCITT（初值 0xFFFF、多项式 0x1021）只覆盖 payload，LEN 与 CRC 小端序。
- 依赖：`main/CMakeLists.txt` 增加 esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls；
  `main/idf_component.yml` 增加 `espressif/mqtt: 1.0.0`（ESP-IDF v6.0 将 mqtt
  移入组件管理器，版本与构建环境本地组件镜像一致）。

## 本地测试与编译验证结果

修复后运行（均为最新代码）：

```text
$ python tests/run_public_tests.py project2_task
[public] running test_compile.py          -> OK
[public] running test_functional_smoke.py -> OK
[public] running test_refactored_features.py -> OK
[public] running test_smoke_gateway.py    -> OK
[public] all public tests passed          (exit 0)

$ python tools/run_debug_probe.py project2_task
[probe:ok] admin setup returns 200
[probe:ok] management API rejects missing cookie
[probe:ok] management API rejects forged cookie
[probe:ok] management API accepts valid cookie
[probe:ok] unknown identity session is denied
[probe:ok] expired session is denied
[probe:ok] care_event write rejects missing admin cookie
[probe:ok] care_event normalizes room/bed for create and query
[probe:info] voice module appears to reference current-session fetch
[probe] all visible diagnostic checks passed   (exit 0)

$ python tools/run_espidf_linux_build.py project2_task
[espidf] ESP-IDF v6.0 (activate_idf_v6.0.sh, /home/xiaoming/.espressif/tools)
[espidf] target esp32s3
[espidf] 组件解析: espressif/esp_tinyusb 2.1.1 + espressif/tinyusb 0.19.0~2
             + espressif/mqtt 1.0.0 + idf 6.0.0
[espidf] Build finished successfully.
[espidf] output_bin = .../esp32/testpro4/build/stdpro.bin
stdpro.bin binary size 0xef040 bytes (smallest app partition 0x100000, 7% free)
```

额外手工验证（临时 SQLite）：

- 历史库迁移：旧 care_events 表（缺 severity/source/created_by/ts）初始化后 4 列
  全部补齐，旧行保留且 `ts` 从 `created_ts` 回填。
- 明文历史 admin 账户登录成功并即时迁移为加盐哈希，迁移后可再次登录；
  伪造 token 会话查询返回 None。
- HTTP 端到端：setup/login/logout、logout 后旧 Cookie 401、带 Cookie 创建/查询
  care_event（小写入参大写查询命中、ts 倒序）、无 Cookie 401、
  staff/patient 会话上下文授权矩阵（staff 可看、patient 仅本人、unknown 拒绝、
  无会话拒绝且 target/modalities 为空）。

## 未验证的残留技术债与风险

- ESP-IDF 编译通过不代表实机验证：未做 `idf.py flash/monitor`、真实 USB 枚举、
  真实 Wi-Fi/MQTT 连通、巴法云链路、ToF 上电时序、MLX 实机读数（任务范围不要求）。
- Windows EIM（`tools/run_espidf_build.py`）未在本机运行；`espressif/mqtt`
  固定为 1.0.0（与 Linux 构建环境组件镜像一致），Windows 注册表同样存在该版本，
  但尚未在 Windows 环境实测编译。
- MQTT 队列满时发布丢弃（`esp_mqtt_client_enqueue` 返回 <0 仅记日志），
  QoS 0 无重发；高帧率下巴法云带宽是否够用需实机压测。
- `/api/v3/session/current` 加入本机服务白名单（供 voice 显式同步会话），
  该接口仅限 127.0.0.1，远程仍要求管理员 Cookie。
- 巴法云 UID / 密码等 NVS 明文存储沿用交接文档说明（NVS 非强安全存储），
  NVS/flash 加密未在本次范围。
- 旧 `/api/v2/voice/*` 与 `/api/v2/ingest/*` 仍按本机服务放行，保留兼容。
