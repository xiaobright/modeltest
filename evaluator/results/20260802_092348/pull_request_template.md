# Pull Request 提测说明 (Pull Request Template)

> 本文件由实际自检日志与代码 diff 共同支撑。所有命令均在本地执行并如实记录，未虚报通过项。

## 初始自检诊断（修改前）

运行环境：Windows，Python 3.14，项目根 `E:\Desktop\mytests\modeltest\workspace`。

### `python tests\run_public_tests.py project2_task`

- 结果：**全部通过**（compile / functional_smoke / refactored_features / smoke_gateway）。
- 但日志暴露一个真实缺陷：`test_refactored_features` 的 sleep 导入输出
  `[SLEEP-IMPORT] sleep_epoch rows=1 bed=R1203-B2` —— 配置的 BEDS 为
  `[("R1203","B1"),("R1203","B2")]`，`first` 策略却把无归属行写到了**最后**一张床
  `R1203-B2`（源码 `beds[-1]` 与注释“first bed”不符）。

### `python tools\run_debug_probe.py project2_task`

- 结果：**6 项失败**，与本 Sprint 目标一一对应：

```
[probe:FAIL] management API rejects missing cookie      status=200  ← 本机请求绕过管理鉴权
[probe:FAIL] management API rejects forged cookie       status=200  ← get_admin_http_session 忽略 token
[probe:FAIL] unknown identity session is denied         allowed=True
[probe:FAIL] expired session is denied                  allowed=True
[probe:FAIL] care_event write rejects missing admin cookie  status=404  ← 路由未接
[probe:FAIL] care_event normalizes room/bed for create and query   rows=[]
[probe:Warning] Voice/assistant path: … ambient/current session …
[probe] failures=6
```

## 修改的文件列表

Gateway / 语音侧：

- `gateway/auth.py`：`admin_account_exists()` 改为查库；`_password_hash()` 创建账户时始终生成随机盐（PBKDF2-HMAC-SHA256），消除明文存储；`get_admin_http_session()` 按 `token_hash` 精确匹配并校验过期；登录支持旧版明文账户的自动升级（先比对、再改存加盐哈希）；返回会话不再带 `token_hash`。
- `gateway/db.py`：`care_events` 表补齐 `severity/source/created_by/ts` 列；新增 `migrate_care_events_schema()`（PRAGMA table_info + ALTER TABLE ADD COLUMN，`ts` 回填 `created_ts`，保留旧行）与 `ensure_care_events_schema()`（供 care_events 模块复用）。
- `gateway/care_events.py`：重写 CRUD —— create/list 对 room/bed 做规范化（小写写入、大写可查）；`limit` 参数与 `ts/created_ts` 倒序；`build_care_events_context()` 由空 stub 改为返回最近事件摘要；`init_care_events_table()` 委托给 db 模块。
- `gateway/gateway.py`：
  - 鉴权门：本机不再无条件放行 `/api/`，只对白名单服务路径（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`）开放本机免登录调用；其余管理 API 一律要求有效管理员 Cookie。
  - `session_is_authenticated()`：`identity_state=unknown`、`assurance_level=none/空`、`expires_ts` 过期、缺 `actor_subject_id` 均判为未认证。
  - `actor_can_access_target()`：无 actor 信息一律拒绝（修复“内部调用直接放行”的患者数据泄漏）。
  - `build_chat_context_v3()`：移除“无 session_id 时回退当前 session”的隐式行为；`modalities` 新增 `care_events`（仅授权时返回），`allowed_sections` 同步加入。
  - 新增路由：`GET/POST /api/v3/care/events`（POST 需管理员登录，未登录 401）。
- `gateway/sleep_importer.py`：`first` 策略改为取第一张配置床 `beds[0]`；显式 room/bed 行规范化后只写对应床位；`all` 展开为规范化列表；策略按行生效，支持混合行。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session_id()`，`build_gateway_context_params()` 在未显式指定 session 时先取 `/api/v3/session/current` 再传 `session_id`，保证收紧后本地助手仍能正确带会话取上下文。

ESP32-S3 固件（`esp32/testpro4/`）：

- `main/main.cpp`：恢复 Wi-Fi STA + 巴法云 MQTT 回传；`usb_send_tof_payload()` 与 MLX 发送路径在保留 USB CDC 输出的同时向对应 topic 发布原始 payload；保留 ToF 自动波特率/UART/USB 初始化逻辑，仅将协议与配置逻辑外移。
- `main/protocol_packet.{h,cpp}`（新增）：USB packet 常量、CRC16-CCITT、包头打包（小端序 LEN/CRC）。
- `main/maixsense_parser.{h,cpp}`（新增）：MaixSense 字节流解析器，处理噪声、分块、坏尾、异常长度与半帧。
- `main/device_config.{h,cpp}`（新增）：NVS key、配置完整性校验（ssid/uid/room/bed）、topic 前缀规范化。
- `main/mqtt_payload.{h,cpp}`（新增）：`{"payload_b64":"..."}` JSON 构造与 `{room}{bed}{stream}` 小写 topic。
- `main/network_backhaul.{h,cpp}`（新增）：Wi-Fi STA 事件处理、esp_mqtt 客户端生命周期、发布封装（17KB 预分配 JSON 缓冲 + 互斥锁，避免大 payload 栈/堆抖动）。
- `main/CMakeLists.txt`：补齐 `esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls`（`mqtt` 经组件管理器解析为 `espressif/mqtt`）。
- `main/idf_component.yml`：声明 `espressif/mqtt: "^1.0.0"`（IDF v6.0.1 不再内置 mqtt 源码，`components/mqtt` 仅剩 test_apps）。

文档：

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`：同步更新鉴权边界、session_id 显式传递、care_event、ESP32 MQTT 契约与验收清单。
- `PULL_REQUEST_TEMPLATE.md`：本文件。

## 架构调整与模块设计

- 保持原有模块边界：`gateway.py` 只做路由/glue；schema 与迁移收敛在 `db.py`；care_event 业务放 `care_events.py`（未扩大 `subjects.py`）；鉴权在 `auth.py`。
- 固件侧按交接规范拆出 5 个职责单一模块，`main.cpp` 只保留初始化、任务与硬件 glue。
- v3 上下文授权链路：`session_id → session → actor_subject → role 判定 → 目标裁剪 → modalities（sleep/vitals/posture/memory/care_events）`，未授权时所有患者字段为空。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256（200k 迭代）+ 随机 16B 盐，库中无明文；旧明文账户登录时自动升级。
- Cookie：仅随机 token（`secrets.token_urlsafe(32)`），库中存 SHA-256 哈希；会话过期/伪造/缺失一律 401。
- 管理 API（subjects/assignments/sessions/credentials/care_events/memories）：本机与远程一致要求管理员 Cookie；本机免登录例外仅限白名单服务接口，且 `/api/v3/context/chat` 不在例外中越权返回患者数据（它仍可被本机 worker 调用，但按 session 裁剪）。
- face/credential template 导出：`/api/v3/credentials?include_template=1` 与 `/api/v3/identity/gallery` 仅限本机（远程即使登录也 403），防止模板外泄。
- v3 session 判定：unknown / 无 assurance / 过期 / 缺 actor_subject_id 一律视为未认证；无 actor 的请求不授予任何目标访问权；patient 只能访问自己。
- 上下文不再静默回退 ambient session：无 `session_id` 即 `not_authenticated`，从根上避免“把患者数据交给错误调用方”。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行带 `room/bed`：只写入对应床位（按 gateway 约定规范化为大写；若命中配置床则使用配置中的规范名）。
- 行不带 `room/bed`，按顺序尝试：
  1. `SLEEP_IMPORT_DEFAULT_ROOM/BED` 均已设置 → 写入该指定床位；
  2. `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位（修复 `beds[-1]` 写最后一张床的 bug）；
  3. `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过；
  4. `all` → 仅显式调试模式，展开到全部配置床；
  5. 未知策略 → 不导入。
- 策略按行生效：同一 CSV 内“有归属行”与“无归属行”可混用，策略只作用于无归属行，不误改、不整表丢弃显式行。

## care_event 实现细节

- DB：`care_events` 表含 `event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`；旧表缺列自动 `ALTER TABLE ADD COLUMN` 并回填 `ts`，旧数据保留。
- API：
  - `POST /api/v3/care/events`（需管理员登录，未登录 401）。
  - `GET /api/v3/care/events?subject_id=...` 或 `?room=...&bed=...`，支持 `limit`，按 `ts/created_ts` 倒序（需管理员登录）。
- 规范化：create 与 query 均对 room/bed 做 `normalize_room/normalize_bed`（大写），`r1203/b1` 写入可被 `R1203/B1` 查到。
- 上下文：`/api/v3/context/chat` 授权通过时在 `modalities.care_events` 返回最近事件摘要（`items + brief`），未授权时为空对象。

## ESP32-S3 固件接口对齐说明

- Wi-Fi STA：`esp_netif + esp_wifi`，事件驱动重连；等 IP 后再启动 MQTT。
- MQTT 巴法云：URI `mqtt://bemfa.com:9501`（可 NVS 覆盖 host/port），**ClientID = UID，用户名/密码为空**（与 `sketch_jan22a.ino` 契约一致）。
- NVS：`wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；网络回传要求 ssid+uid+room+bed 齐备，否则保持纯 USB CDC 模式。
- Topic：`{room}{bed}tof1/tof2/mlx1/mlx2`，room/bed 小写拼接（如 `r1203b1tof1`）。
- JSON：`{"payload_b64":"<base64 原始 payload>"}`，base64 是传感器**原始 payload**（ToF = 完整 MaixSense 帧 `[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`；MLX = 3072B float32 温度），**不是**完整 USB packet。
- USB packet 契约保持不变：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD...][CRC_L][CRC_H]`，CRC16-CCITT（init 0xFFFF, poly 0x1021）仅覆盖 payload，LEN/CRC 小端。
- 缓冲：MQTT JSON 用 17KB 预分配缓冲 + 互斥锁，支持最大 ToF 帧 base64，不做栈上大数组。
- 依赖：`REQUIRES` 增加 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`；`espressif/mqtt: ^1.0.0`（本地组件缓存 `E:\esp\tools\components` 与网络均可解析）。

## 本地测试与编译验证结果

### 修改后：`python tests\run_public_tests.py project2_task`

- **全部通过**，且 sleep 导入日志已修正为第一张床（`bed=R1203-B1`）。

### 修改后：`python tools\run_debug_probe.py project2_task`

- **全部通过**（含 voice current-session 提示转为 `[probe:info] voice module appears to reference current-session fetch`）。

### 边界验证（自建脚本 `verify_edge_cases.py`，临时 SQLite，未污染 `data/`）

- 旧 `care_events` 表迁移：4 列补齐、旧行保留、`ts` 回填成功。
- 密码非明文、Cookie 存 token hash。
- 无 `session_id` 的 context 请求被拒（`not_authenticated`）；缺 actor 的 session 被拒。
- 授权上下文含 `care_events`，未授权为空；patient 访问他人被拒。
- 睡眠 CSV 混合行：显式行写自己床位；`first` 写第一床；`skip` 丢无归属行保留显式行；`DEFAULT_ROOM/BED` 生效。
- 共 20 项断言全部通过。

### ESP-IDF：`python tools\run_espidf_build.py project2_task`

- 环境：Windows ESP-IDF v6.0.1（EIM，`E:\esp\v6.0.1\esp-idf`），目标 `esp32s3`，组件从本地缓存/网络解析（`espressif/mqtt: ^1.0.0`、`espressif/esp_tinyusb: ^2.0.1~1`）。
- 第一轮：构建到 1027/1085 时失败，唯一硬错误为
  `error: designator order for field 'esp_mqtt_client_config_t::credentials_t::username' does not match declaration order`
  （esp_mqtt 的 `username` 声明在 `client_id` 之前，C++ 指示符初始化需按声明顺序）。已修正字段顺序。
- 第二轮（增量）：失败于 `-Werror=format-truncation`（`wifi_sta_config_t` 的 ssid[32]/password[64] 小于源缓冲区）。已改用 `strlcpy` 安全截断。
- 第三轮（增量）：**编译成功**，产出 `stdpro.bin`（约 960KB，app 分区余量 6%），命令：
  `[espidf] Build finished successfully.` / `output_bin = …\build\stdpro.bin`。
- 说明：仅编译验证；未执行 `idf.py flash` / `monitor` / 真实 Wi-Fi-MQTT 连通 / USB 枚举 / ToF 上电时序 / MLX 实机读数。编译日志保留在 `/tmp/espidf_build*.log`，镜像位于 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\`。

## 未验证的残留技术债与风险

- **实机未验证**：Wi-Fi/MQTT 到巴法云的真实连通性、MQTT QoS 0 丢包/乱序对 set 聚合的影响、ESP32 长时间运行内存稳定性（esp_mqtt 内部缓冲）、真实传感器帧率与 17KB 发布缓冲的匹配。
- **MQTT set 完整性**：网关 `esp_store` 对云上转发的 ToF/MLX 帧不做 CRC 校验（`bemfa_tcp_sub_loop` 中 `crc_ok=True`、crc=0），若云通道丢帧，四路 set 可能长期不完整；已有 2s 超时轮转逻辑兜底，但未做实机压测。
- **旧管理员账户升级**：老库若存在“明文密码账户”，登录时自动升级为加盐哈希；升级只发生在成功登录时，未登录过的遗留明文账户在升级前仍按明文比对（可接受，但不属于全新部署路径）。
- **`/api/v3/care/events` GET 权限**：实现为“管理员登录”才能查询；合同允许的“授权上下文只暴露给允许访问的 actor”路径由 `context/chat` 的 `modalities.care_events` 承载，未给 GET 增加 session 授权模式（保持最简安全面）。
- **voice 双跳**：voice 每次取上下文前多一次 `/api/v3/session/current` 请求（本机毫秒级，可接受）；若未来高频调用可缓存 session_id。
- **admin.html**：前端未新增 care_event 录入 UI，仅 API 可用（Sprint 范围未要求 UI）。
- **固件文档**：`esp32/testpro4/docs/protocol.md`、README、QUICKSTART、CHANGELOG 中“待恢复 MQTT”的表述已随代码恢复，但未在实机复测链路。
