# Pull Request 提测说明 — Project2 护理/睡眠联调工程

## 初始自检诊断

修改前运行结果：

`python tests/run_public_tests.py project2_task` → 全部通过（4 套件 OK）。

`python tools/run_debug_probe.py project2_task` → 6 项失败：

```
[probe:ok] admin setup returns 200
[probe:FAIL] management API rejects missing cookie status=200
[probe:FAIL] management API rejects forged cookie status=200
[probe:ok] management API accepts valid cookie
[probe:FAIL] unknown identity session is denied policy={'allowed': True, ...}
[probe:FAIL] expired session is denied policy={'allowed': True, ...}
[probe:FAIL] care_event write rejects missing admin cookie status=404
[probe:FAIL] care_event normalizes room/bed for create and query rows=[]
[probe] failures=6
```

## 修改的文件列表

### Gateway（Python 后端）

- `gateway/auth.py`：修复密码哈希（PBKDF2+随机盐）、`admin_account_exists()` 实际查库、`get_admin_http_session()` 按 token_hash 精确匹配、登录时旧明文密码自动迁移为哈希。
- `gateway/gateway.py`：收紧管理 API 鉴权（仅本地服务路径免 Cookie）、`session_is_authenticated` 按契约拒绝 unknown/expired/无 actor 会话、新增 `POST/GET /api/v3/care/events` 路由、`build_chat_context_v3` 集成 `modalities.care_events`。
- `gateway/care_events.py`：完整重写，补全 severity/source/created_by/ts 字段、room/bed 规范化、limit 参数、`build_care_events_context` 实现。
- `gateway/db.py`：care_events 表新增 severity/source/created_by/ts 列、`_migrate_care_events()` 迁移旧表并回填 ts。
- `gateway/sleep_importer.py`：修复 `first` 策略 bug（`beds[-1]` → `beds[0]`）。

### ESP32-S3 固件（`esp32/testpro4/main/`）

- `main/protocol_packet.h`（新增）：USB packet 常量、CRC16-CCITT inline、header/CRC 构造辅助。
- `main/maixsense_parser.h`（新增）：MaixSense 字节流帧解析器（处理噪声、分块、坏尾、异常长度）。
- `main/device_config.h`（新增）：NVS 配置结构体、topic 规范化、网络就绪判断接口。
- `main/device_config.cpp`（新增）：NVS 读写实现、`{room}{bed}{kind}` 小写 topic 构造、配置完整性校验。
- `main/mqtt_payload.h`（新增）：Wi-Fi STA + MQTT 初始化和 `payload_b64` 发布接口。
- `main/mqtt_payload.cpp`（新增）：Wi-Fi STA 连接（含重试）、MQTT client（bemfa 契约）、base64 JSON 构造（mbedtls）、大 payload 动态分配。
- `main/main.cpp`（重写）：使用新模块替代内联逻辑、`usb_send_tof_payload` 和 `mlx_sender_task` 同时向 MQTT topic 发布原始 payload、`network_backhaul_task` 启动 Wi-Fi+MQTT。
- `main/CMakeLists.txt`：新增源文件 device_config.cpp/mqtt_payload.cpp、新增 REQUIRES esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls。
- `main/idf_component.yml`：新增 espressif/mqtt 依赖、IDF 版本要求 >=5.0.0。

## 架构调整与模块设计

保持已有模块边界，不将业务逻辑塞回 gateway.py：

- `gateway.py`：仅路由 glue + 上下文聚合。
- `auth.py`：管理员账户、密码哈希、HTTP session token 管理。
- `care_events.py`：护理事件 CRUD 和 context 摘要构建。
- `db.py`：schema 定义 + 迁移逻辑。
- `sleep_importer.py`：CSV 按行归属策略。
- `subjects.py`：身份/会话/凭证/记忆（未修改）。

ESP32 固件按推荐拆分为 4 个模块（protocol_packet / maixsense_parser / device_config / mqtt_payload），`main.cpp` 只保留初始化、任务创建和硬件 glue。

## 安全边界及鉴权设计

- 管理员密码使用 PBKDF2-HMAC-SHA256（200k 迭代 + 16 字节随机盐），不再明文存储。旧明文密码在首次登录时自动迁移为哈希。
- Cookie 只保存随机 `token_urlsafe(32)`，数据库存 SHA-256(token)。
- `get_admin_http_session` 严格按 token_hash 匹配，不再返回任意活跃 session。
- 管理 API（subjects/assignments/credentials/care_events 等）即使本机请求也必须携带有效 Cookie；仅 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation` 允许本机免 Cookie。
- `session_is_authenticated` 按 API 契约拒绝：identity_state=unknown、assurance_level=none/空、expires_ts 过期、缺少 actor_subject_id。
- 未授权时 `build_chat_context_v3` 返回空 modalities，不泄露患者数据。
- 远程未登录用户不能访问 face template / credential template（include_template 限本机）。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行策略（`row_targets`）：

- 行带 room/bed：只写入对应床位（大小写不敏感匹配已配置床位）。
- 行不带 room/bed：
  - 设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位（修复了原来错误使用 `beds[-1]` 的 bug）。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过。
  - `all` 仅作为显式调试模式。
- 同一 CSV 内显式行与无归属行混合时，策略只作用于无归属行，不影响显式行。

## care_event 实现细节

- 表结构：event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts。
- 迁移：`_migrate_care_events()` 检测旧表缺失列并 ALTER TABLE 补齐，回填 `ts = created_ts`。
- API：`POST /api/v3/care/events`（需管理员 Cookie）、`GET /api/v3/care/events?subject_id=&room=&bed=&limit=`（需管理员 Cookie）。
- room/bed 写入和查询均经过 `normalize_room/normalize_bed`（大写化），小写写入的数据可被大写查询命中。
- Context 集成：`build_chat_context_v3` 授权通过时在 `modalities.care_events` 返回最近 5 条事件摘要；未授权时返回空。

## ESP32-S3 固件接口对齐说明

### Wi-Fi + MQTT

- `mqtt_payload.cpp`：Wi-Fi STA 初始化（esp_wifi + esp_netif + esp_event），连接失败最多重试 5 次。MQTT client 连接巴法云（`mqtt://{host}:{port}`），UID 作为 username/client_id。
- `network_backhaul_task`：延迟 3s 启动（让 USB 和传感器先就绪），检查 NVS 配置完整性后初始化网络。

### NVS 配置

- `device_config.cpp`：从 NVS namespace `project2` 读取 wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id。
- `device_config_network_ready()`：ssid + password + uid + room + bed 全非空才启用网络。
- 控制台命令 CFGSET/CFG?/CFGRESET/REBOOT 保持不变。

### Topic 规范化

- `device_config_build_topic()`：`{room}{bed}{kind}` 全小写拼接，如 `r1203b1tof1`。

### MQTT JSON 与 base64

- `mqtt_publish_payload()`：`{"payload_b64":"<base64>"}`，base64 内容是原始传感器 payload（MaixSense 完整帧或 MLX 温度数据），不是完整 USB packet。
- 大 payload（ToF ~10KB → base64 ~13.4KB）使用动态 malloc 分配，避免栈溢出。MQTT buffer 设为 16384。

### USB packet 契约

- 保持 `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`。
- CRC16-CCITT（init=0xFFFF, poly=0x1021）只覆盖 payload，LEN 和 CRC 小端序。
- ToF payload 保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`。

### 双路回传

- `usb_send_tof_payload()`：USB CDC1 输出 + MQTT 发布到 `{room}{bed}tof1/tof2`。
- `mlx_sender_task()`：USB CDC0 输出 + MQTT 发布到 `{room}{bed}mlx1/mlx2`。

## 本地测试与编译验证结果

### 修复后最终验证

```
python tests/run_public_tests.py project2_task
→ [public] all public tests passed

python tools/run_debug_probe.py project2_task
→ [probe:ok] admin setup returns 200
→ [probe:ok] management API rejects missing cookie
→ [probe:ok] management API rejects forged cookie
→ [probe:ok] management API accepts valid cookie
→ [probe:ok] unknown identity session is denied
→ [probe:ok] expired session is denied
→ [probe:ok] care_event write rejects missing admin cookie
→ [probe:ok] care_event normalizes room/bed for create and query
→ [probe] all visible diagnostic checks passed
```

### ESP-IDF 编译

```
python tools/run_espidf_build.py project2_task
→ [espidf] target = esp32s3
→ [espidf] output_bin = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin
→ [espidf] Build finished successfully.
```

环境：Windows EIM ESP-IDF v6.0.1，target=esp32s3，32 并行 jobs。编译通过，生成 stdpro.bin。未执行 flash/monitor/实机连通测试。

## 未验证的残留技术债与风险

- **Voice/助手路径 Warning**：`run_debug_probe.py` 打印 Warning 提示收紧权限后若本地助手仍依赖隐式 ambient session（不提供 session_id），护理上下文同步可能失败。当前设计意图是助手应通过 `/api/v3/vision/observation` 或 `POST /api/v3/sessions` 先建立有效会话再请求 context/chat。若现有 voice 模块未适配此流程，需要后续迭代补全。
- **ESP32 实机未验证**：编译通过但未进行 `idf.py flash`、真实 Wi-Fi/MQTT 连通、ToF 上电时序或 MLX90640 实机读数验证。
- **旧 SQLite 迁移**：`_migrate_care_events` 处理了缺列情况，但未覆盖更极端的旧库损坏场景（如表完全不存在时由 CREATE TABLE IF NOT EXISTS 兜底）。
- **巴法云 MQTT 大 payload**：ToF 帧 base64 后约 13.4KB，接近 MQTT buffer 上限（16KB）。若实际帧更大或 QoS 要求更高，可能需要分片或调整 buffer。
- **admin 密码迁移**：旧明文密码在首次登录时迁移为哈希。若管理员从未登录过（setup 后直接升级），密码仍为明文存储直到首次登录。建议后续增加启动时批量迁移。
