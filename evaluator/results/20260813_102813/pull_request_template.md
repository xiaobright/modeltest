# Pull Request 提测说明 (Pull Request Template)

本文件记录 Project2（本地护理/睡眠联调工程）本次迭代的完整实现、自检结果与风险，供 CI 与 Reviewer 交叉校验。

## 初始自检诊断

修改前先运行并阅读了自检输出：

- `python tests\run_public_tests.py project2_task` → **全部通过**（`test_compile` / `test_functional_smoke` / `test_refactored_features` / `test_smoke_gateway`）。这些是浅层冒烟测试，不校验鉴权、授权与数据正确性。
- `python tools\run_debug_probe.py project2_task` → **6 项失败**（初始症状）：

```text
[probe:FAIL] management API rejects missing cookie status=200（期望 401）
[probe:FAIL] management API rejects forged cookie status=200（期望 401）
[probe:FAIL] unknown identity session is denied policy={'allowed': True, ...}
[probe:FAIL] expired session is denied policy={'allowed': True, ...}
[probe:FAIL] care_event write rejects missing admin cookie status=404（路由未接线）
[probe:FAIL] care_event normalizes room/bed for create and query（rows=[]）
```

根因定位：

1. `auth.get_admin_http_session(token)` 忽略 token，直接 `LIMIT 1` 取任意活跃会话，伪造/缺失 Cookie 都会被放行。
2. `gateway._authorized_for_api()` 对**本机请求一律放行所有 `/api/*`**，管理类 API 不校验管理员 Cookie。
3. `auth._password_hash()` 在无盐时**明文落库**（返回 `("", password)`），`admin_account_exists()` 恒返回 `False`。
4. `gateway.session_is_authenticated()` 对 `identity_state in ("unknown","")` 返回 `True`，且不校验 `expires_ts` / `assurance_level` / `actor_subject_id`。
5. `care_events` 表缺 `severity/source/created_by/ts` 列，`create_care_event` 未做 room/bed 规范化，路由未接线，`build_care_events_context` 是空 stub。
6. `sleep_importer` 的 `first` 策略误用 `beds[-1]`（应 `beds[0]`），无归属行落错床位。

## 修改的文件列表

### Gateway（核心逻辑）

| 文件 | 修改 |
|------|------|
| `gateway/auth.py` | `admin_account_exists()` 改为查库；`_password_hash()` 恒用随机盐 + PBKDF2-SHA256（200k 迭代），不再明文；`get_admin_http_session()` 按 `token_hash` 精确匹配并校验过期。 |
| `gateway/gateway.py` | `_authorized_for_api()` 改为「管理员 Cookie 或（本机 + 本机服务白名单）」；`session_is_authenticated()` 收紧（未知/空 identity、空 assurance、缺 actor、过期均拒绝）；`actor_can_access_target()` 对空 actor 拒绝；补 `DEFAULT_ADMIN_SUBJECT_ID` 导入；接线 `GET/POST /api/v3/care/events`；`build_chat_context_v3` 增加 `modalities.care_events`；`/api/v3/session/current` 加入本机服务白名单。 |
| `gateway/db.py` | `care_events` 全量 schema（含 `severity/source/created_by/ts`）+ `migrate_care_events()` 迁移旧表并回填 `ts=created_ts`。 |
| `gateway/care_events.py` | 重写 CRUD：room/bed 统一大写规范化、`limit` + `ts/created_ts` 倒序、`build_care_events_context()` 返回摘要。 |
| `gateway/sleep_importer.py` | `first` 策略改为 `beds[0]`，并保持按行处理（显式 room/bed 行与无归属行互不影响）。 |

### Voice / 本地助手

| 文件 | 修改 |
|------|------|
| `voice/voice_assistant_integrated.py` | 新增 `fetch_current_session()` / `resolve_gateway_session_id()`，请求 `/api/v3/context/chat` 前显式解析并携带 `session_id`，不再依赖静默 ambient session。 |

### ESP32-S3 固件（`esp32/testpro4/`）

| 文件 | 修改 |
|------|------|
| `main/main.cpp` | 重写为模块 glue：恢复 Wi-Fi STA + 巴法云 MQTT 客户端；`usb_send_tof_payload()` 与 MLX 发送路径在保留 USB CDC 的同时向对应 MQTT topic 发布原始 payload。 |
| `main/protocol_packet.h/.cpp` | 新增：USB 包常量、CRC16-CCITT、打包/校验、`stream_name()`。 |
| `main/maixsense_parser.h/.cpp` | 新增：MaixSense 帧解析器（处理噪声、分块、坏尾字节、异常长度、半帧）。 |
| `main/device_config.h/.cpp` | 新增：NVS 配置读写、完整性校验、topic 规范化。 |
| `main/mqtt_payload.h/.cpp` | 新增：`{"payload_b64":"..."}` JSON 构造（mbedtls base64）与 topic 选择。 |
| `main/CMakeLists.txt` | 增加 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖，登记新源文件。 |
| `main/idf_component.yml` | 增加 `espressif/mqtt: ^1.0.0`。 |

### 文档

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`：同步 care_events 与 ESP32 状态。
- `esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md`：将「待恢复」改为「已实现」并补充模块结构。

## 架构调整与模块设计

- 保持既有模块边界：`gateway.py` 仅保留路由/页面/启动/Bemfa 订阅 glue；care_event 的 schema 与迁移在 `db.py`，CRUD 在 `care_events.py`，context 聚合函数在 `care_events.py` 中，由 `build_chat_context_v3` 调用。
- 鉴权集中在 `auth.py`（管理员）与 `subjects.py`（v3 session），路由层只做「管理员 Cookie / 本机服务白名单」分流。
- ESP32 固件按 ONBOARDING 建议拆成 `protocol_packet` / `maixsense_parser` / `device_config` / `mqtt_payload` 四个模块，`main.cpp` 只保留初始化、任务与硬件 glue。

## 安全边界及鉴权设计

- 管理员密码：`PBKDF2-SHA256` + 随机 16 字节盐，200k 迭代；数据库不落明文。
- Cookie：仅保存随机 `secrets.token_urlsafe(32)`，数据库存 `sha256(token)`，查询按 hash 精确匹配并校验 `expires_ts`。
- 管理类 API（`/api/v3/subjects|assignments|sessions|memories|credentials|care/events` 等）：远程与**本机均需管理员 Cookie**。
- 本机服务接口例外仅限：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`。远程访问仍需管理员 Cookie；`identity/gallery` 与 `credentials?include_template=1` 额外限制为仅本机。
- v3 授权：`session_is_authenticated()` 要求 `identity_state=recognized`、`assurance_level` 非空、存在 `actor_subject_id` 且未过期；`actor_can_access_target()` 要求 actor 可解析，admin/staff 全量、patient 仅本人。未授权时 `target.patient/assignment`、`modalities`（含 `care_events`）均为空，不泄露患者明细、记忆或护理事件。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行处理（非整文件一刀切）：

- 行带 `room/bed`：仅写入对应床位（大小写不敏感匹配配置床位，未命中则按原始值写入）。
- 行不带 `room/bed`：`SLEEP_IMPORT_DEFAULT_ROOM/BED` 存在 → 写入指定床位；`SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位（已修复 `beds[-1]` → `beds[0]`）；`skip` → 跳过；`all` 仅作显式调试模式。
- 同一 CSV 中显式行与无归属行并存时，策略只作用于无归属行，显式行不受影响（已用混合 CSV 验证：显式 → R1203-B2，无归属 → R1203-B1）。

## care_event 实现细节

- schema：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`。
- 迁移：`init_management_db()` 调用 `migrate_care_events()`，用 `PRAGMA table_info` 探测缺失列并 `ALTER TABLE ... ADD COLUMN`（默认 `severity='info'`、`source='manual'`、`created_by=''`），`ts` 从 `created_ts` 回填，旧行保留（已用旧 schema 样例库验证）。
- CRUD：`create_care_event` 大写规范化 room/bed，`list_care_events` 支持 `subject_id`、`room+bed` 过滤与 `limit`（默认 50，上限 500），按 `ts DESC, created_ts DESC` 倒序。
- 路由：`POST /api/v3/care/events`（需管理员）、`GET /api/v3/care/events?subject_id=&room=&bed=&limit=`（需管理员）。
- 上下文：授权通过且存在 `target_subject_id` 时，`modalities.care_events` 返回最近事件摘要并注入 `brief`/`prompt_hints`；未授权时为空。

## ESP32-S3 固件接口对齐说明

- Wi-Fi STA：`esp_netif` + `esp_event` + `esp_wifi`，断线自动重连。
- MQTT：`espressif/mqtt`（esp-mqtt 1.0.0），broker `bemfa.com:9501`，`client_id = bemfa_uid`，用户名/密码为空，`keepalive=60`，自动重连。
- NVS：`project2` namespace，键 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；`config_is_complete` 校验 ssid/uid/room/bed/host/port。
- topic：`{room.lower()}{bed.lower()}{stream}`，即 `r1203b1tof1/tof2/mlx1/mlx2`。
- payload：`{"payload_b64":"<base64 原始 payload>"}`；base64 内容是传感器原始 payload（ToF 完整 MaixSense 帧、MLX 768×float32），**不含** USB 包头/CRC。
- USB 包契约保持不变：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT（init 0xFFFF, poly 0x1021）只覆盖 payload，LEN/CRC 小端序。
- `usb_send_tof_payload()` 与 MLX 发送路径保留 USB CDC 输出，同时调用 `mqtt_publish_raw()` 发布对应 topic。

## 本地测试与编译验证结果

### 修复后回归（均通过）

```text
python tests\run_public_tests.py project2_task   → [public] all public tests passed
python tools\run_debug_probe.py project2_task    → [probe] all visible diagnostic checks passed
```

`run_debug_probe.py` 修复后 8 项全绿：admin setup 200、管理 API 缺 Cookie 401、伪造 Cookie 401、有效 Cookie 200、unknown session 拒绝、过期 session 拒绝、care_event 写缺 Cookie 401、care_event room/bed 规范化命中。voice 提示已识别到「fetch current session」。

### 额外手工验证

- 旧 schema `care_events` 库迁移：新列齐全、旧行保留、`ts` 回填 `created_ts`。
- 密码非明文、盐非空、`admin_account_exists()`/`login`/token 校验正确、伪造 token 被拒。
- 混合 CSV（显式 R1203-B2 + 无归属）：无归属行落到首个配置床位 R1203-B1，显式行不受影响。

### ESP-IDF 编译

```text
python tools\run_espidf_build.py project2_task --set-target
```

- **成功**：Windows EIM ESP-IDF v6.0.1，`espressif/mqtt` 组件解析并编译（`libespressif__mqtt.a` 已生成）。
- 输出：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（`0xf2b10` 字节，1MB app 分区剩余约 5%）。
- 未执行 `idf.py flash/monitor`，未验证真实 Wi-Fi/MQTT 连通、真实 USB 枚举、ToF 上电时序与 MLX 实机读数。

## 未验证的残留技术债与风险

1. **ESP32 实机联调**：Wi-Fi/MQTT/巴法云 topic 上传只做了编译验证，未做真实联网与实机读数（本任务不要求 flash/monitor）。
2. **固件体积**：引入 Wi-Fi+lwip+MQTT 后 `stdpro.bin` 约 0xf2b10 字节，1MB app 分区仅剩约 5%。若后续继续加功能需考虑分区扩容或裁剪组件。
3. **会话非多因素**：v3 授权仍以单一人脸/手动 session 为主，`assurance_level` 语义未做多因素叠加；生产应接入指纹/卡片二次认证（架构文档已有规划）。
4. **人脸 embedding 为本地 OpenCV 向量**：非 ArcFace/InsightFace，阈值与误识别风险需实机回归（RK3588_TEST_GUIDE 已列验证步骤）。
5. **NVS 非强安全存储**：Wi-Fi 密码与巴法云 UID 仍在明文 NVS；真实部署建议 NVS/flash 加密与每设备独立 token。
6. **Piper TTS / RKLLM / OpenCV contrib / onnxruntime 在 ARM64 的可用性**未在本机（x64）验证，需按 RK3588_TEST_GUIDE 在板端逐项确认。
7. 巴法云 MQTT 为 QoS 0 云端转发，ESP→网关链路本身无端到端 CRC；CRC 仅保留在 USB 本地通道。
