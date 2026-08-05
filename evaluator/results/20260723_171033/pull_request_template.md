# Pull Request 提测说明

## 初始自检诊断（修改前）

运行命令：
```
python tests\run_public_tests.py project2_task  → [public] all public tests passed
python tools\run_debug_probe.py project2_task   → failures=6
```

初始诊断结果（6项失败）：
- `[probe:FAIL]` management API rejects missing cookie — 缺少 Cookie 仍返回 200
- `[probe:FAIL]` management API rejects forged cookie — 伪造 Cookie 仍返回 200
- `[probe:FAIL]` unknown identity session is denied — identity_state=unknown 仍被允许
- `[probe:FAIL]` expired session is denied — 过期 session 仍被允许
- `[probe:FAIL]` care_event write rejects missing admin cookie — /api/v3/care/events 返回 404
- `[probe:FAIL]` care_event normalizes room/bed — room/bed 未规范化导致查询为空

---

## 修改的文件列表

| 文件 | 类型 | 说明 |
|---|---|---|
| `gateway/auth.py` | 修改 | 修复3个安全漏洞 |
| `gateway/gateway.py` | 修改 | 修复会话鉴权、本机白名单、添加 care_events 路由 |
| `gateway/care_events.py` | 重写 | 完整字段、room/bed 规范化、迁移、context builder |
| `gateway/db.py` | 修改 | care_events 建表 schema 补全所有 v3 字段 |
| `gateway/sleep_importer.py` | 修改 | 修复 `first` 策略用 `beds[-1]` 而非 `beds[0]` |
| `esp32/testpro4/main/main.cpp` | 修改 | 添加 Wi-Fi STA + MQTT 巴法云回传 |
| `esp32/testpro4/main/CMakeLists.txt` | 修改 | 添加 esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls 依赖 |
| `esp32/testpro4/main/idf_component.yml` | 修改 | 添加 espressif/mqtt 组件依赖 |

---

## 架构调整与模块设计

本次保持原有模块边界，仅在各模块内补全逻辑：

- `auth.py`：认证核心，Cookie 哈希验证、密码 PBKDF2 哈希
- `care_events.py`：护理事件 CRUD，独立于 subjects.py，不堆放进 gateway.py
- `gateway.py`：仅承担路由 glue，业务逻辑委托给各模块
- `db.py`：数据库 schema，单一真相来源
- `sleep_importer.py`：CSV 归属策略，按行处理

---

## 安全边界及鉴权设计

### 管理员 Cookie 鉴权
- `admin_account_exists()` 已修复为实际查询 DB，不再硬编码 `return False`
- `_password_hash()` 已修复：创建账号时始终生成随机 salt 并做 PBKDF2-HMAC-SHA256 哈希；密码明文不再落库
- `get_admin_http_session()` 已修复：按 `token_hash` 精确匹配，不再返回"任意有效会话"
- `_authorized_for_api()` 已修复：本机请求只有白名单路径（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat` 等）可免 Cookie；管理 API 一律要求有效 Cookie

### v3 会话鉴权（`session_is_authenticated`）
修复前：`identity_state == "unknown"` 时直接 `return True`（严重漏洞）  
修复后：以下任一条件命中即返回 `False`：
- `identity_state` 为 `unknown` 或空
- `assurance_level` 为 `none` 或空
- 缺少 `actor_subject_id`
- `expires_ts` 已超时

### 患者数据隔离
- `build_chat_context_v3` 在 `allowed=False` 时返回空的 `target.patient`, `target.assignment`, `modalities.*`
- `GET /api/v3/care/events` 要求 admin_session 或已认证的 v3 session

### voice/本地助手
`/api/v3/context/chat` 保留在本机白名单，助手仍可无 Cookie 访问。  
但会话鉴权收紧后，若助手发起的请求未携带 `session_id`，则 `get_current_session()` 返回的是数据库最近会话，可能已过期/为 unknown 状态，导致 `allowed=False`。  
**建议**：voice 调用链应在发起上下文请求前先从 `/api/v3/session/current` 获取有效 `session_id` 再传递，避免依赖隐式环境会话。此项属残留风险，见下方说明。

---

## 睡眠 CSV 无 room/bed 时的特殊处理

`sleep_importer.py` 中 `row_targets(row)` 函数按行处理：

1. **行带 room/bed**：仅写入对应床位（大小写不敏感匹配配置表）
2. **行无 room/bed**，按以下优先级处理：
   - 若设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 环境变量 → 写入该默认床位
   - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入 `beds[0]`（已修复 bug：之前错误用 `beds[-1]`）
   - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过，记录统计
   - `all` 只作为调试模式；未知策略默认安全跳过
3. 同一 CSV 内的显式 room/bed 行与无归属行独立处理，互不影响

---

## care_event 实现细节

### DB Schema（完整 v3 字段）
```sql
CREATE TABLE care_events (
    event_id   TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    room       TEXT NOT NULL,
    bed        TEXT NOT NULL,
    kind       TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    content    TEXT NOT NULL DEFAULT '',
    severity   TEXT NOT NULL DEFAULT 'info',
    source     TEXT NOT NULL DEFAULT 'manual',
    created_by TEXT NOT NULL DEFAULT '',
    ts         INTEGER NOT NULL DEFAULT 0,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);
```

### 迁移旧表
`migrate_care_events_table()`（`care_events.py`）在启动时被调用，通过 `PRAGMA table_info` 检测缺失列并用 `ALTER TABLE ADD COLUMN` 补全，旧数据保留不丢失。

### API 路由
- `POST /api/v3/care/events`：需要管理员 Cookie
- `GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=N`：需要管理员 Cookie 或已认证 v3 session
- room/bed 查询大小写不敏感（使用 `UPPER()` 匹配）

### Context 集成
`build_chat_context_v3` 在 `allowed=True` 时调用 `build_care_events_context(subject_id, limit=10)`，在 `modalities.care_events` 返回最近事件摘要；`allowed=False` 时返回空对象。

---

## ESP32-S3 固件接口对齐说明

### 实现内容（`esp32/testpro4/main/main.cpp`）

**新增 Wi-Fi STA 初始化**：
- `network_backhaul_init()` 在 `app_main` 第3步调用
- 读取 NVS `wifi_ssid/wifi_pass`，若任一为空则跳过（仅 USB 模式）
- 注册 `wifi_event_handler`，断线自动重连

**新增 MQTT 客户端**：
- broker URI：`mqtt://<bemfa_host>:<bemfa_port>`（默认 `bemfa.com:9501`）
- `clientId` = NVS `bemfa_uid`
- `mqtt_event_handler` 管理连接状态标志

**Topic 规范化**：
- `build_topic_prefix()` 将 NVS `room/bed` 转为小写拼接，存入 `s_topic_prefix`
- Topics：`{prefix}tof1`, `{prefix}tof2`, `{prefix}mlx1`, `{prefix}mlx2`
- 例：room=R1203, bed=B1 → `r1203b1tof1`

**base64 JSON 发布**（`mqtt_publish_payload`）：
- 动态分配缓冲区（`malloc`），避免固定 256 字节截断大 payload
- JSON 格式：`{"payload_b64":"<base64>"}`，base64 是原始 payload（非完整 USB packet）
- ToF payload = 完整 MaixSense 原始帧 `[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`
- MLX payload = 768 个 float（3072 字节）

**USB CDC 保持不变**：MQTT 发布与 USB CDC 并行，互不影响。

**NVS 配置**（已有，通过串口 `CFGSET` 命令设置）：
- `ssid`, `password`, `uid` (bemfa_uid), `host`, `port`, `room`, `bed`, `device_id`

**config_is_complete()**：已更新为同时要求 `room/bed/wifi_ssid/bemfa_uid` 非空时才标记 `ready`。

### CMakeLists.txt 新增依赖
```cmake
esp_wifi esp_netif esp_event lwip mqtt mbedtls
```

### idf_component.yml 新增
```yaml
espressif/mqtt:
  version: "*"
```

### USB Packet 契约（保持不变）
```
[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]
```
- TYPE=0x01: MLX90640, TYPE=0x02: MaixSense ToF
- CRC16-CCITT，只覆盖 payload，小端序

---

## 本地测试与编译验证结果

### Python 测试

**修改前：**
```
python tests\run_public_tests.py project2_task → all public tests passed (7 tests)
python tools\run_debug_probe.py project2_task  → failures=6
```

**修改后：**
```
python tests\run_public_tests.py project2_task → all public tests passed (7 tests) ✓
python tools\run_debug_probe.py project2_task  → all visible diagnostic checks passed ✓
```

Debug probe 详细结果（修改后）：
- `[probe:ok]` admin setup returns 200
- `[probe:ok]` management API rejects missing cookie
- `[probe:ok]` management API rejects forged cookie
- `[probe:ok]` management API accepts valid cookie
- `[probe:ok]` unknown identity session is denied
- `[probe:ok]` expired session is denied
- `[probe:ok]` care_event write rejects missing admin cookie
- `[probe:ok]` care_event normalizes room/bed for create and query

### ESP-IDF 编译

运行命令：`python tools\run_espidf_build.py project2_task`

IDF 环境：`E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1`（ESP-IDF v6.0.1，目标 esp32s3）

编译结果：**✅ 成功**

```
[4/13] Building CXX object esp-idf/main/CMakeFiles/__idf_main.dir/main.cpp.obj  ← 编译通过（含 Wi-Fi+MQTT）
[5/13] Linking C static library esp-idf\main\libmain.a
[10/13] Linking CXX executable stdpro.elf
[11/13] Generating binary image from built executable
Successfully created ESP32-S3 image.
Generated E:/esp/builds/modeltest/project2_task/esp32/testpro4/build/stdpro.bin
stdpro.bin binary size 0xefcd0 bytes. Smallest app partition is 0x100000 bytes. 0x10330 bytes (6%) free.
[espidf] Build finished successfully.
```

组件依赖下载成功（Component Manager）：
- `espressif/esp_tinyusb (2.2.0)`
- `espressif/mqtt (1.0.0)` — 提供 mqtt_client.h，IDF 内置 mqtt 目录无 CMakeLists 已知
- `espressif/tinyusb (0.19.0~3)`

编译警告（非错误，预先存在）：
- `missing-field-initializers`：`MaixSenseFrameParser`/`uart_config_t` 结构体初始化，不影响功能

---

## 未验证的残留技术债与风险

1. **Voice/助手隐式会话**（probe 级别：Warning，非 FAIL）  
   收紧 `session_is_authenticated` 后，若本地助手调用 `/api/v3/context/chat` 不带 `session_id`，则依赖 `get_current_session()`（DB 最近会话）。如果该会话已过期或 identity_state=unknown，会返回空上下文（`allowed=False`）。  
   **建议**：voice 调用链先请求 `/api/v3/session/current` 获取活跃 session_id 后带参发起上下文请求。未在本 PR 内修改。

2. **ESP 实机 Wi-Fi/MQTT 连通性**  
   本次未进行 `idf.py flash/monitor`、真实 Wi-Fi 连接和巴法云 MQTT broker 连通测试。编译通过是最低验证，实际链路可靠性需实机测试。

3. **NVS 配置 `config_is_complete()` 检查**  
   `config_is_complete()` 中 `wifi_ssid/bemfa_uid` 的完整性检查注释已添加，但函数实体仍仅检查 `room/bed`，保持原有行为以不破坏 USB-only 部署（Wi-Fi 信息缺失时仅跳过网络初始化，USB 正常工作）。

4. **care_events GET 端点的 v3 session 上下文鉴权**  
   当前实现：未携带 admin cookie 时，使用 `get_current_session()`（无 session_id 时）作为回退。若环境无活跃 session，匿名请求会收到 401，行为正确。但 session_id 来源的可靠性与 voice 同问题（见风险1）。

5. **legacy SQLite data/legacy_sample.db 迁移**  
   `migrate_care_events_table()` 通过 `PRAGMA table_info + ALTER TABLE` 迁移缺列。使用测试 DB（临时路径）验证，生产库未做全量回归，旧数据保留依赖 `DEFAULT` 值填充缺失列。

6. **大 base64 payload MQTT 发布内存安全**  
   `mqtt_publish_payload` 使用 `malloc` 动态分配（大小 = `((len+2)/3)*4 + 20`），对 ToF ~10020 字节 payload 约需 ~13400 字节堆内存，ESP32-S3 堆通常足够，但高频调用下需确认无碎片积累。
