# Project2 PR 提测说明

## 1. 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `gateway/auth.py` | 修复 | `get_admin_http_session()` 增加 token_hash 过滤；`admin_account_exists()` 改为真实 DB 查询 |
| `gateway/gateway.py` | 修复+新增 | `session_is_authenticated()` 增加过期检查、拒绝 unknown 身份；`_authorized_for_api()` 要求管理 API 必须有合法 Cookie；新增 `GET/POST /api/v3/care/events` 路由；v3 context 注入 `modalities.care_events` |
| `gateway/db.py` | 修复 | `care_events` 表增加 `severity/source/created_by/ts` 列；新增 `_migrate_db()` 迁移旧表 |
| `gateway/care_events.py` | 重写 | 新增 `_migrate_care_events()` 迁移；`create_care_event()` 增加字段、room/bed 归一化；`list_care_events()` 增加 limit、归一化；`build_care_events_context()` 改为真实查询 |
| `gateway/sleep_importer.py` | 修复 | `first` 策略使用 `beds[0]` 而非 `beds[-1]` |
| `esp32/testpro4/main/main.cpp` | 新增 | 实现 Wi-Fi STA + MQTT 巴法云回传；`usb_send_tof_payload` 和 `mlx_sender_task` 增加 MQTT 发布 |
| `esp32/testpro4/main/protocol_packet.h` | 新增 | USB packet 常量、CRC16-CCITT |
| `esp32/testpro4/main/mqtt_payload.h` | 新增 | MQTT topic 拼接、`{"payload_b64":"..."}` JSON 构造 |
| `esp32/testpro4/main/CMakeLists.txt` | 修改 | 增加 `esp_wifi/esp_netif/esp_event/lwip/mbedtls` 依赖 |
| `esp32/testpro4/main/idf_component.yml` | 修改 | 增加 `espressif/mqtt` 依赖 |

## 2. 初始诊断结果

`python tools\run_debug_probe.py project2_task` 初始失败 6 项：

- `management API rejects missing cookie` — 无 Cookie 仍返回 200
- `management API rejects forged cookie` — 伪造 Cookie 仍返回 200
- `unknown identity session is denied` — unknown 身份未拒绝
- `expired session is denied` — 过期会话未拒绝
- `care_event write rejects missing admin cookie` — 无 Cookie 可写 care_event
- `care_event normalizes room/bed for create and query` — room/bed 未归一化

`python tests\run_public_tests.py project2_task` 初始全通过。

## 3. 架构设计说明

保持 `gateway/` 模块拆分不变：
- `auth.py`：管理员账户/Cookie 会话管理，密码 PBKDF2 加盐存储
- `care_events.py`：护理事件 CRUD，独立模块不扩大 `subjects.py`
- `db.py`：SQLite 建表 + 旧表迁移
- `gateway.py`：仅路由 glue + 数据聚合

ESP32 固件按推荐模块拆分：
- `protocol_packet.h`：USB 包格式、CRC
- `mqtt_payload.h`：base64 JSON、topic 拼接
- `main.cpp`：ESP-IDF 初始化、任务创建、Wi-Fi/MQTT 启动、USB/MQTT 双路回传

## 4. 安全边界说明

- 管理员密码：PBKDF2-SHA256 200000 轮加盐，DB 不存明文
- Cookie：`secrets.token_urlsafe(32)` 随机 token，DB 存 SHA256 hash
- 管理 API：`_authorized_for_api()` 要求有效 Cookie；本机 localhost 仅对白名单路径（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`）免鉴权
- Session 过期：`session_is_authenticated()` 检查 `expires_ts`，拒绝过期会话
- 身份未知：`identity_state="unknown"` 的 session 不再通过鉴权
- v3 context：`actor_can_access_target()` 按 role 裁剪；未授权时不返回 `sleep/vitals/posture/memory/care_events` 患者数据
- Face template/credential template：`include_template=true` 时仅允许本机 localhost 访问

## 5. 睡眠 CSV 无 room/bed 策略

`gateway/sleep_importer.py` 按行处理：
- 行含 `room/bed`：仅写入对应床位
- 行不含 `room/bed`：
  - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 设置时 → 写入指定床位
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → `beds[0]`（已修复原 `beds[-1]` bug）
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过
  - `all` 仅显式调试模式，非默认
- 同一 CSV 可混合有/无归属行，策略仅作用于无归属行

## 6. care_event 实现说明

- DB schema：`care_events` 表含 `event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`
- 旧表迁移：`_migrate_care_events()` 通过 `PRAGMA table_info` 检查缺失列，`ALTER TABLE ADD COLUMN` 补齐
- API：
  - `POST /api/v3/care/events` — 创建护理事件
  - `GET /api/v3/care/events?subject_id=...` — 按患者查询
  - `GET /api/v3/care/events?room=...&bed=...` — 按床位查询
  - 支持 `limit` 参数，默认 `50`
- Context：`/api/v3/context/chat` 授权通过时在 `modalities.care_events` 返回最近 10 条摘要
- room/bed 归一化：create/list 均调用 `normalize_room()/normalize_bed()` 统一大写

## 7. ESP32-S3 固件实现说明

### MQTT 协议
- Topic 小写拼接：`{room}{bed}tof1/tof2/mlx1/mlx2`
- JSON 格式：`{"payload_b64":"<base64 raw payload>"}`
- base64 内容为原始传感器 payload（非完整 USB packet）
- MQTT broker：巴法云，地址/端口/UID 从 NVS 读取

### USB 协议（保留）
- 包格式：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`
- TYPE=0x01：MLX90640，TYPE=0x02：MaixSense ToF
- CRC16-CCITT：初始值 0xFFFF，多项式 0x1021，仅覆盖 payload
- LEN 和 CRC 均为小端序
- ToF payload 保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`

### NVS 配置
- NVS namespace：`project2`
- Key：`wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`
- 串口命令：`CFGSET key=value` 写入，`CFG?` 查看，`CFGRESET` 清除，`REBOOT` 重启
- `config_is_complete()` 检查 `room/bed/wifi_ssid/bemfa_uid` 全部非空

### 回传路径
- `usb_send_tof_payload()`：USB CDC 1 输出 + 向对应 MQTT topic 发布 `tof1/tof2`
- `mlx_sender_task()`：USB CDC 0 输出 + 向对应 MQTT topic 发布 `mlx1/mlx2`
- MQTT 连接在 `network_init()` 中启动，Wi-Fi 等待 30s，MQTT 等待 15s
- 不阻塞传感器采集，MQTT 不可用时仅通过 USB 回传

## 8. 测试与编译结果

### Public Tests
`python tests\run_public_tests.py project2_task` — **全部通过**

### Debug Probe
`python tools\run_debug_probe.py project2_task` — **全部通过（0 failures）**

```
[probe:ok] admin setup returns 200
[probe:ok] management API rejects missing cookie
[probe:ok] management API rejects forged cookie
[probe:ok] management API accepts valid cookie
[probe:ok] unknown identity session is denied
[probe:ok] expired session is denied
[probe:ok] care_event write rejects missing admin cookie
[probe:ok] care_event normalizes room/bed for create and query
[probe:Warning] Voice/assistant path: sensitive context may be denied without session_id
[probe] all visible diagnostic checks passed
```

### ESP-IDF 编译
运行 `python tools\run_espidf_build.py project2_task`：

**结果：失败**（CMake configure error）

错误原因：
```
Failed to resolve component 'mqtt' required by component 'main': unknown name.
```

已修正：将 `mqtt` 从 `CMakeLists.txt` REQUIRES 移除，改为在 `idf_component.yml` 中添加 `espressif/mqtt: "^1.0.0"`。

修正后再次编译，CMake configure 阶段通过了 mqtt 组件解析，但后续仍有 `espressif__tinyusb` 相关的 cmake install 文件问题，最终 `ninja: error: rebuilding 'build.ninja': subcommand failed`。环境中的 ESP-IDF v6.0.1 组件依赖较为复杂，本地无完整 IDF 编译环境。

建议在有完整 ESP-IDF v6.0.1 + Windows EIM 的 CI 环境或开发机上运行完整编译验证。

## 9. 未验证或残留技术债

1. **ESP-IDF 编译未通过**：CMake configure 已修正，但完整 build 因环境组件依赖问题失败。需在 CI 或开发机上运行完整编译。
2. **Voice 模块 session 警告**：`run_debug_probe.py` 提示 voice 模块可能仍依赖 ambient session。已确认 `voice_assistant_integrated.py` 中有 `session_id` 参数传递路径（`build_gateway_context_params` → `fetch_gateway_chat_context`），但未在实机联调中验证。
3. **ToF 大 payload base64 编码**：MQTT payload buffer 为 18000 字节，理论可容纳完整 MaixSense 帧（~10020B 原始 → ~13360B base64 + 16B JSON 包裹）。但未测试真实帧是否超出或触发 mbedtls_base64_encode 缓冲区限制。
4. **MLX 4Hz 刷新率**：`mlx_sender_task` 固定 250ms 延迟，未与 MLXManager 内部 FPS 联动。
5. **BEMFA UID 认证**：MQTT `username` 设置为 `bemfa_uid`，但未确认巴法云 MQTT broker 的具体认证方式（部分巴法云版本使用 client_id 而非 username）。
6. **无实机硬件测试**：Wi-Fi/MQTT 连接、ToF 传感器初始化、MLX90640 I2C 通信均需实机验证。
7. **历史 SQLite 迁移测试**：`_migrate_db()` 通过 `PRAGMA table_info` 做列检测，但未在真实遗留 DB 文件上验证。
