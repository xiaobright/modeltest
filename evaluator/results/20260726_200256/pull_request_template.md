# Pull Request 提测说明 (Pull Request Template)

本次迭代修复了管理鉴权、v3 授权上下文、care_event 能力、睡眠 CSV 归属策略，
并恢复了 ESP32-S3 固件的 Wi-Fi + MQTT 巴法云回传。

---

## 1. 初始自检诊断（修改前）

### `python tests\run_public_tests.py project2_task`

全部通过（4 个文件：`test_compile` / `test_functional_smoke` /
`test_refactored_features` / `test_smoke_gateway`）。这些是浅层冒烟测试，
其文件头也写明"不检查安全属性、授权策略或数据正确性"，因此**通过并不代表没有缺陷**。

### `python tools\run_debug_probe.py project2_task`

**6 项失败**：

```text
[probe:ok]   admin setup returns 200
[probe:FAIL] management API rejects missing cookie   status=200 data={'subjects': [...]}
[probe:FAIL] management API rejects forged cookie    status=200 data={'subjects': [...]}
[probe:ok]   management API accepts valid cookie
[probe:FAIL] unknown identity session is denied      policy={'allowed': True, ...}
[probe:FAIL] expired session is denied               policy={'allowed': True, ...}
[probe:FAIL] care_event write rejects missing admin cookie  status=404
[probe:FAIL] care_event normalizes room/bed for create and query  rows=[]
[probe:Warning] Voice/assistant path: sensitive context may be denied without session_id...
[probe] failures=6
```

失败项说明：未登录/伪造 Cookie 仍能读取患者名单；`identity_state=unknown` 和已过期
session 仍被判为已授权；`/api/v3/care/events` 路由不存在（404）；care_event 大小写
不一致导致查不到。Warning 指出收紧鉴权后本地助手可能取不到上下文。

---

## 2. 修改的文件列表

### Gateway（Python）

| 文件 | 修改内容 |
|------|----------|
| `gateway/auth.py` | 密码 PBKDF2 加盐哈希；`admin_account_exists()` 改为真实查库；session 按 token 哈希精确匹配；恒定时间比较；过期会话清理 |
| `gateway/db.py` | 新增 `migrate_schema()` / `table_columns()`；`care_events` 表补齐 `severity/source/created_by/ts` 并回填旧行 |
| `gateway/care_events.py` | 重写：完整 CRUD、room/bed 规范化、severity/source 白名单、`limit`、倒序、上下文摘要 |
| `gateway/gateway.py` | 本机服务路径白名单真正生效；`session_is_authenticated` / `actor_can_access_target` 收敛；移除 ambient session 回落；新增 care_event 路由与 `_care_events_read_allowed`；context 增加 `modalities.care_events` |
| `gateway/sleep_importer.py` | `first` 策略由 `beds[-1]` 改为 `beds[0]`；按行处理逻辑与注释澄清 |

### Voice

| 文件 | 修改内容 |
|------|----------|
| `voice/voice_assistant_integrated.py` | 新增 `fetch_current_session_id()`（带缓存）与 `invalidate_session_cache()`；请求上下文前显式取 `session_id`；新增 `GATEWAY_SESSION_AUTO` / `GATEWAY_SESSION_CACHE_MS` |

### ESP32-S3 固件

| 文件 | 修改内容 |
|------|----------|
| `esp32/testpro4/main/protocol_packet.{h,cpp}` | **新增**：USB packet 常量、sensor type/id、CRC16-CCITT、打包与校验 |
| `esp32/testpro4/main/maixsense_parser.{h,cpp}` | **新增**：MaixSense 流式帧解析器（修复原实现的无符号下溢缺陷） |
| `esp32/testpro4/main/device_config.{h,cpp}` | **新增**：NVS key、配置完整性分级、topic 规范化 |
| `esp32/testpro4/main/mqtt_payload.{h,cpp}` | **新增**：`payload_b64` JSON 构造、精确尺寸计算、topic 选择 |
| `esp32/testpro4/main/net_backhaul.{h,cpp}` | **新增**：Wi-Fi STA + 巴法云 MQTT 客户端生命周期与发布 |
| `esp32/testpro4/main/main.cpp` | 移除内联协议逻辑（1116 → 900 行）；改为调用上述模块；ToF/MLX 发送路径并行 MQTT；启动网络回传 |
| `esp32/testpro4/main/CMakeLists.txt` | 补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖和新增源文件 |
| `esp32/testpro4/main/idf_component.yml` | 增加 `espressif/mqtt` 组件依赖 |

### 文档

`README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`CHANGES.md`、
`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`esp32/testpro4/QUICKSTART.md`、
`esp32/testpro4/CHANGELOG.md`。

**未修改**：`tests/`、`tools/` 下的任何测试与诊断脚本。

---

## 3. 架构调整与模块设计

保持既有模块边界，没有把逻辑堆回 `gateway.py`：

- **`care_events.py` 承担 care_event 的全部数据逻辑**（CRUD、规范化、摘要构建），
  `gateway.py` 只保留路由 glue 和一个鉴权判定辅助函数，没有扩大 `subjects.py`。
- **schema 迁移集中在 `db.py`**：`SCHEMA_ADDITIONS` 表驱动 + `migrate_schema()`，
  后续新增列只需改数据表，不必再写一次 ALTER 逻辑。
- **固件按交接文档建议拆分为 5 个模块**：协议打包、帧解析、设备配置、MQTT payload、
  网络回传各自独立，`main.cpp` 只留 ESP-IDF 初始化、任务创建、硬件调用和 glue。
  这样帧解析和 CRC 逻辑可以脱离硬件单独测试（本次即是这么验证的）。

---

## 4. 安全边界及鉴权设计

### 4.1 管理员凭据

- 密码：PBKDF2-HMAC-SHA256，随机 16 字节盐，200000 次迭代。**数据库无明文**。
  原实现 `_password_hash` 在无盐时直接 `return "", password`，即明文入库——已修复。
- Cookie：只放随机 token（`secrets.token_urlsafe(32)`），数据库只存其 SHA-256 哈希。
- 登录比较使用 `hmac.compare_digest`；用户不存在时也执行一次哈希，避免时序区分。
- `admin_account_exists()` 原本硬编码 `return False`，任何人都能重复调用
  `/admin/setup` 覆盖管理员——已改为真实查库。

### 4.2 会话绑定

原 `get_admin_http_session()` 的 SQL **不含 token 条件**（`WHERE s.expires_ts >= ? LIMIT 1`），
只要库里有任意一个未过期会话，任何 Cookie（包括伪造的）都能通过。现按
`token_hash = ?` 精确匹配并校验过期时间与账号状态，返回前剔除 `token_hash` 字段。

### 4.3 本机例外的收敛

原 `_authorized_for_api()` 对**任何** `/api/` 路径只要来自 loopback 就放行，
`_path_allows_local_service()` 定义了却从未被调用。现在：

- 有效管理员 Cookie → 全部放行。
- loopback 且路径在白名单内 → 放行（`/api/v2/*`、`/api/esp/*`、
  `/api/v3/context/chat`、`/api/v3/identity/*`、`/api/v3/vision/observation`、
  `/api/v3/session/current`，以及 `GET /api/v3/care/events`）。
- 其余管理 API **即使本机也必须带 Cookie**。

`GET /api/v3/care/events` 放进白名单是为了让本机助手能走到路由内部的
`_care_events_read_allowed()`，那里仍然要求管理员 Cookie 或一个通过完整
认证+授权检查的 session；按床位查询时会先解析该床位当前占用患者再判权限，
避免用 room/bed 绕过按患者的检查。POST 不在白名单内。

### 4.4 v3 授权上下文

`session_is_authenticated()` 原实现把 `identity_state in ("unknown","")` 判为
**已认证**（注释称"worker 不做人脸认证"），且完全不看过期时间。现按
`reference/api_contracts.md` 收敛，以下一律视为未认证：

- `identity_state` 不是 `recognized`/`verified`
- `assurance_level` 为 `none`/空/`unknown`
- `expires_ts` 缺失或已过期
- 缺少 `actor_subject_id`

`actor_can_access_target()` 原在 actor 为空时 `return True`（"大概是内部 worker 调用"），
现改为**失败关闭**，并额外要求 actor `status=active`。

`build_chat_context_v3()` 原在缺 `session_id` 时回落到 `get_current_session()`，
未认证调用方可以直接继承别人的身份。现已移除该回落：未授权时
`target.patient`、`target.assignment` 和全部 `modalities`（含 `care_events`）均为空。

### 4.5 患者数据零泄漏验证

针对"该拒绝时仍带出患者明细"，写了一条会在授权失败时必然出现的哨兵字符串
（记忆与护理事件各一条），对 6 类被拒场景逐一断言序列化后的响应体中不含该字符串：
缺 actor、assurance=none、无 session_id、未知 session_id、跨患者、已过期。全部通过。

---

## 5. 睡眠 CSV 无 room/bed 时的特殊处理

策略**按行**判定，不是整表一刀切。同一 CSV 内显式行与无归属行可以共存，
策略只作用于无归属行。

- 行带 `room/bed`：只写入对应床位。命中配置床位则用配置的大小写形式；
  未命中也按行内声明写入，不会被重定向或丢弃。
- 行不带 `room/bed`，按优先级：
  1. `SLEEP_IMPORT_DEFAULT_ROOM/BED` 已设置 → 写入该床位
  2. `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过
  3. `=first` → 写入 `BEDS` 的**第一个**床位
  4. `=all` → 广播到所有床位（仅显式调试模式，非默认）
  5. 无法识别的策略 → 不导入，而不是扇出

**修复的缺陷**：`first` 分支原为 `return [beds[-1]]`（注释却写"use the first bed"），
实际写入的是最后一个床位。已改为 `beds[0]`。

验证覆盖了 4 种策略 × 混合行 CSV（1 条无归属 + 2 条不同床位的显式行），
断言无归属行落到正确床位、两条显式行都未被改动或丢弃。

---

## 6. care_event 实现细节

### 数据层

`care_events` 表字段：`event_id / subject_id / room / bed / kind / title /
content / severity / source / created_by / ts / created_ts / updated_ts`，
索引覆盖 `(subject_id, created_ts)`、`(room, bed, created_ts)` 和 `(ts)`。

**旧库迁移**：`CREATE TABLE IF NOT EXISTS` 对已存在的旧表是空操作，因此
`migrate_schema()` 用 `PRAGMA table_info()` 检查缺列并 `ALTER TABLE ... ADD COLUMN`，
再把旧行的 `ts` 用 `created_ts` 回填（否则旧数据 `ts=0` 会永远排在最后）。
迁移幂等，重复启动不会重复执行，旧行数据不丢。

### API

```text
POST /api/v3/care/events                    需要管理员 Cookie
GET  /api/v3/care/events?subject_id=...     管理员 Cookie 或已授权 session
GET  /api/v3/care/events?room=..&bed=..     同上，先解析床位占用患者再鉴权
GET  ...&limit=N                            默认 20，上限 200，按 ts/created_ts 倒序
```

`ts` 是调用方给出的临床事件时间，`created_ts` 是入库时间，补录历史事件时两者不同。
排序以 `ts` 为主、`created_ts` 为次，保证迁移后的旧行与新行混排仍然合理。

### room/bed 大小写

写入和查询两侧都过 `normalize_room()` / `normalize_bed()`，
以 `r1203/b1` 写入的记录能被 `R1203/B1` 查到，反之亦然。

### 上下文集成

授权通过时 `modalities.care_events` 返回最近事件摘要，`policy.allowed_sections`
包含 `care_events`；未授权时为空结构。

---

## 7. ESP32-S3 固件接口对齐说明

### USB packet 契约（未改变，仅集中化）

```text
[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]
```

TYPE `0x01`=MLX90640 / `0x02`=MaixSense ToF；CRC16-CCITT 初值 `0xFFFF`、
多项式 `0x1021`、**只覆盖 payload**；LEN 与 CRC 均小端序。

### ToF payload

保持**完整 MaixSense 原始帧** `[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`
（10022 字节），未裁剪为 10000B 图像区，与 gateway 和采集 worker 契约一致。

### MQTT

- Broker：`mqtt://{bemfa_host}:{bemfa_port}`，默认 `bemfa.com:9501`，
  ClientID 使用巴法云 UID。
- Topic：`{room}{bed}{stream}` 全小写拼接（如 `r1203b1tof1`），
  已与 `gateway/bed_config.py` 的 `topics_for()` 交叉核对一致。
- 消息：`{"payload_b64":"<base64 原始 payload>"}`，
  base64 内容是**原始传感器 payload**，不是完整 USB packet。
- 使用 `esp_mqtt_client_enqueue()` 而非 `publish()`，避免采集任务阻塞在 socket 上；
  QoS 0、retain 0（陈旧深度帧不应下发给新订阅者）。

### 大 payload 缓冲

一个 ToF 帧的 `payload_b64` JSON 约 13.4 KB（10022 → base64 13364 + JSON 包装），
远超任何栈缓冲。实现按 `mqtt_payload_json_size()` 精确计算后从堆分配并及时释放，
分配失败时记录告警并跳过该帧，不影响 USB 路径。

### NVS 配置

键：`wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`。
完整性分两级：`device_config_has_identity()`（room+bed，USB 采集可用）与
`device_config_is_network_ready()`（再加 ssid+uid，才启动 MQTT）。
`wifi_password` 允许为空以支持开放网络。配置不全时固件照常启动，只是 MQTT 休眠。

### 并行性

USB CDC 与 MQTT 互不阻塞：USB 未连接时 MQTT 仍发布；MQTT 未就绪或 Wi-Fi 断开时
USB 照常工作，Wi-Fi 事件处理器持续重连。

### 修复的固件缺陷

原 `parse_maixsense_frame()` 循环上界为 `parser->buffer_len - 1`，`buffer_len == 0`
时无符号下溢为 `0xFFFFFFFF`，会越过 12000 字节缓冲区读取。新实现用
`i + 1 < buffer_len` 规避，并增加了对零长度/超长长度字段的拒绝、
丢帧与噪声字节计数。

---

## 8. 运行过的测试与编译脚本

全部在本机实际执行，以下为最终结果。

### 8.1 `python tests\run_public_tests.py project2_task`

```text
[public] running test_compile.py
[public] running test_functional_smoke.py
[public] running test_refactored_features.py
[public] running test_smoke_gateway.py
[public] all public tests passed
```

### 8.2 `python tools\run_debug_probe.py project2_task`

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
```

初始 6 项失败全部转为 ok；voice 的 Warning 也已转为 info（退出码 0）。

### 8.3 `python tools\run_espidf_build.py project2_task`

**编译成功**：

```text
[espidf] target            = esp32s3
[espidf] activation_script = E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1
NOTICE: [1/4] espressif/esp_tinyusb (2.2.0)
NOTICE: [2/4] espressif/mqtt (1.0.0)
NOTICE: [3/4] espressif/tinyusb (0.19.0~3)
NOTICE: [4/4] idf (6.0.1)
[1030/1100] Building CXX object .../protocol_packet.cpp.obj
[1031/1100] Building CXX object .../maixsense_parser.cpp.obj
[1032/1100] Building CXX object .../device_config.cpp.obj
[1033/1100] Building CXX object .../mqtt_payload.cpp.obj
[1034/1100] Building CXX object .../main.cpp.obj
[1035/1100] Building CXX object .../net_backhaul.cpp.obj
[espidf] output_bin        = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
[espidf] Build finished successfully.
```

已用 `--clean-copy --set-target` 做过一次完整从零构建，同样成功。

**过程中遇到并修复的两个真实编译失败**（保留记录）：

1. `Failed to resolve component 'mqtt' required by component 'main': unknown name.`
   起因：ESP-IDF v6.0 起 esp-mqtt 不再随 IDF 内置，`components/mqtt` 只剩空的
   子模块目录（实测该目录下只有 `test_apps/`，无 `CMakeLists.txt`）。
   处理：在 `main/idf_component.yml` 声明 `espressif/mqtt: "^1.0.0"` 从注册表拉取。

2. `error: 'snprintf' output may be truncated before the last format character
   [-Werror=format-truncation=]`（`net_backhaul.cpp:135/136`）
   起因：本地配置缓冲 `wifi_ssid[33]/wifi_password[65]` 比
   `wifi_config_t` 的 `ssid[32]/password[64]` 各多一字节（我方多留 NUL 位）。
   处理：改用 `strnlen` + `memcpy` 显式按目标长度拷贝——`wifi_config_t` 的字段
   本就不要求 NUL 结尾。

### 8.4 补充验证（自建，非交付物）

公开测试和 probe 都不校验数据正确性，因此额外写了两组临时验证：

**Gateway 场景验证（71 项全过）**，覆盖：旧库迁移与数据保留、密码/Cookie 落库形态、
重复 setup 拒绝、管理 API 四类越权、8 条本机 worker 路径回归、
6 类拒绝场景的患者数据零泄漏、跨患者与过期会话、care_event 大小写与排序与 limit、
4 种睡眠策略 × 混合行 CSV。

**固件协议验证（23 项全过）**，用 MSVC 在主机侧编译 `protocol_packet.cpp` 与
`maixsense_parser.cpp` 运行，覆盖：CRC16-CCITT 标准向量 `"123456789" → 0x29B1`、
包头/CRC 小端序、packet 往返校验、空缓冲不下溢、完整帧解析、
输出为完整原始帧而非仅图像区、前导噪声恢复、512B 分块重组、坏尾字节拒绝、
超长/零长度字段拒绝、半帧等待、连续帧顺序、payload 内假帧头、溢出后恢复。
另验证 base64 尺寸：MLX 3072→4096、ToF 10022→13364，以及 256B 固定缓冲确实不够用。

这两个临时脚本未留在 `project2_task/` 内，不属于交付物。

---

## 9. 未验证的残留技术债与风险

### 未做真实硬件验证（本任务明确不要求）

- 未执行 `idf.py flash` / `monitor`，无真实 USB 枚举。
- **未验证真实 Wi-Fi 连接与巴法云 MQTT 连通性**：broker 地址、ClientID 语义、
  QoS/retain 选择均依据文档契约实现，未经实网握手确认。
- 未验证 ToF 上电冷启动时序、自动波特率探测、MLX90640 实机温度读数。
- MQTT 与 USB 双通道在满速率（ToF ~162 KB/s）下的实际吞吐与丢帧率未测。

### 实现取舍与已知限制

- **MQTT 发布用堆分配**：每帧 ToF 需临时分配约 13.4 KB。板上有 8MB PSRAM，
  常规情况充裕，但长时间高频运行下的堆碎片未做长稳测试；内存不足时会跳过该帧
  并打日志，不会崩溃。
- **MaixSense 解析器缓冲为 12000 字节**，只够容纳一帧（10022）加一个读块，
  **不足以缓存两个完整帧**。因此调用方必须每次 push 后取完（ToF 任务已改为
  `while` 循环排空）。若未排空，溢出时保留最新帧——对实时深度数据是合理语义，
  但会静默丢弃较旧的一帧。此约束已写入头文件注释。
- **ToF 交替发送策略保持原样**：严格 1-2-1-2 交替，某一路长时间无帧时另一路也会
  等待。这是既有行为，本次未改动，但在单传感器故障场景下会降低有效帧率。
- **care_event 无更新/删除接口**：只有创建和查询。若需要修正已写入的护理记录，
  当前只能新增一条事件，没有 PATCH/DELETE 路由。
- **session 缺乏来源绑定**：一个有效 `session_id` 被任何本机进程拿到即可用于
  读取该 actor 权限内的上下文，未与调用方进程/IP 做进一步绑定。
  单护士站部署下可接受，多租户场景需要加强。
- **voice 侧 session 缓存 3 秒**：会话在缓存窗口内失效时，最多一轮对话会拿到
  过期结果；已在被判 `not_authenticated` 时主动清缓存以缩短影响。
- `create_admin_account` 依赖 `admin_accounts` 的主键约束防并发重复创建，
  未使用显式事务锁；两个请求极端同时到达时靠 `sqlite3.IntegrityError` 兜底返回 400。

### 环境相关

- ESP-IDF 编译在 **Windows EIM ESP-IDF v6.0.1** 下验证。
  `espressif/mqtt` 需要能访问组件注册表；完全离线的环境首次构建会失败，
  需预先填充 `managed_components/` 或本地镜像。
- `sdkconfig.defaults` 中 `CONFIG_TINYUSB_ENABLED` 与 `CONFIG_USB_OTG_SUPPORTED`
  在 IDF 6.0 下报 "unknown kconfig symbol" 警告。这是既有配置遗留，
  不影响构建产物，本次未改动以免影响 USB 行为。
