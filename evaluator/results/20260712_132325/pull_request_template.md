# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行：

```
python tests\run_public_tests.py project2_task
```
- 7 个 public tests 全部通过（test_compile, test_functional_smoke x2, test_refactored_features x3, test_smoke_gateway）

```
python tools\run_debug_probe.py project2_task
```
- **6 项失败**：
  1. management API rejects missing cookie → 200 而非 401（`_authorized_for_api` 对本机请求无条件放行）
  2. management API rejects forged cookie → 同上
  3. unknown identity session is denied → `session_is_authenticated` 把 `identity_state=unknown` 当作已认证
  4. expired session is denied → `get_session()` 不检查 `expires_ts`
  5. care_event write rejects missing admin cookie → `/api/v3/care/events` 路由不存在（404）
  6. care_event normalizes room/bed for create and query → 表缺少 severity/source/created_by/ts 列，room/bed 未规范化

## 修改的文件列表

| 文件 | 修改摘要 |
|------|---------|
| `gateway/auth.py` | 修复 `admin_account_exists`（查询 DB 不再永远返回 False）；修复 `_password_hash`（改为始终 PBKDF2 加盐哈希，消除明文存储）；修复 `get_admin_http_session`（用 token_hash 精确匹配，不再取任意活跃 session）；修复 `login_admin_account`（兼容旧明文和新 PBKDF2 格式） |
| `gateway/gateway.py` | 修复 `session_is_authenticated`（unknown/空 identity_state 返回 False，检查 expires_ts，检查 actor_subject_id 非空）；修复 `_authorized_for_api`（本机请求仅放行 service 路径，管理 API 必须验证管理员 Cookie）；新增 `POST/GET /api/v3/care/events` 路由；`build_chat_context_v3` 中接入 `care_events` modality；`main()` 中调用 `init_care_events_table()` |
| `gateway/subjects.py` | 修复 `get_session`：增加 `expires_ts >= now_ms()` 过滤 |
| `gateway/care_events.py` | 重写：新增 `_ensure_initialized()` 惰性初始化；`init_care_events_table()` 执行 schema 迁移（PRAGMA 检测缺失列，ALTER TABLE 补齐 severity/source/created_by/ts）并保留旧数据；`create_care_event` 规范化 room/bed 大写并存储所有字段；`list_care_events` 规范化查询 room/bed、支持 limit、按 ts/created_ts 倒序；实现 `build_care_events_context` |
| `gateway/db.py` | 移除内联 care_events 建表语句，改由 care_events 模块管理 |
| `gateway/sleep_importer.py` | 修复 `first` 策略：`beds[-1]` → `beds[0]` |
| `esp32/testpro4/main/main.cpp` | 新增 Wi-Fi STA 初始化（`esp_wifi/esp_netif/esp_event`）；新增 MQTT 客户端初始化及 base64 payload 发布（`mbedtls/base64.h`，受 `CONFIG_MQTT_BACKHAUL_ENABLED` 条件编译控制，当前编译设为 0）；`usb_send_tof_payload` 和 `mlx_sender_task` 中增加 MQTT 回传路径；`config_is_complete` 扩展为同时检查 ssid/uid；修复 `wifi_event_handler` 中 `retry_count` 作用域错误；修复 `snprintf` 截断警告 |
| `esp32/testpro4/main/CMakeLists.txt` | 新增 REQUIRES：`esp_wifi`, `esp_netif`, `esp_event`, `mbedtls`；新增 `target_compile_definitions(CONFIG_MQTT_BACKHAUL_ENABLED=0)` |
| `esp32/testpro4/main/idf_component.yml` | 清理冗余注释；移除不可访问的 `espressif/esp_mqtt` 依赖 |
| `esp32/testpro4/sdkconfig.defaults` | 新增 Wi-Fi/MQTT/mbedTLS 相关配置项 |

## 架构调整与模块设计

- `auth.py`：密码加盐哈希使用 PBKDF2-SHA256（200k iterations, 16B salt），token 用 SHA256 hash 存储，Cookie 仅存随机 token
- `care_events.py`：独立模块，带惰性表初始化 + schema 迁移，支持旧表缺列自动补齐
- `gateway.py`：管理 API（`/api/v3/subjects`, `/api/v3/assignments`, `/api/v3/memories`, `/api/v3/credentials`, `/api/v3/sessions`, `/api/v3/care/events`）必须验证管理员 Cookie；服务路径（`/api/v2/*`, `/api/esp/*`, `/api/v3/context/chat`, `/api/v3/identity/*`, `/api/v3/vision/observation`）允许本机 loopback 无 Cookie 调用

## 安全边界及鉴权设计

- 管理 API：必须提供有效管理员 session Cookie（token_hash 验证 → expires_ts 检查 → admin_accounts.status=active）
- v3 context/chat：`session_is_authenticated` 严格检查 `identity_state != unknown/空`、`assurance_level != none/空`、`actor_subject_id` 非空、`expires_ts` 未过期
- 患者数据裁剪：`actor_can_access_target` 按 actor role（admin/staff 全通，patient 仅看自己）授权，未授权返回空 patient/assignment/memory/care_events
- voice/助手路径：`voice_assistant_integrated.py` 不直接调用 `/api/v3/session/current`，通过 `VOICE_SESSION_ID` 环境变量传 session_id；收紧鉴权后，无有效 session 时 `fetch_authorized_gateway_context` 返回 denied reply
- 凭据模板/identity gallery：`include_template` 仅本机 loopback 可获取

## 睡眠 CSV 无 room/bed 时的特殊处理

- 显式 room/bed 行：写入匹配床位（大小写不敏感匹配配置的 BEDS）
- 无 room/bed 行：
  - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 设值时写入指定床位
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`：写入第一个配置床位（`beds[0]`）
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip`：跳过
  - `all` 仅显式调试，不做默认
- 同一 CSV 可混合显式/无归属行：策略仅作用于无归属行

## care_event 实现细节

- Schema：`care_events(event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts)`
- 迁移逻辑：`PRAGMA table_info(care_events)` 检测缺失列，`ALTER TABLE ADD COLUMN` 补齐，`UPDATE SET ts = created_ts` 填充旧数据
- API：
  - `POST /api/v3/care/events`（需管理员认证）
  - `GET /api/v3/care/events?subject_id=&room=&bed=&limit=`（需管理员认证，room/bed 规范化查询）
- v3 context：授权通过后在 `modalities.care_events` 返回最近事件摘要

## ESP32-S3 固件接口对齐说明

### 已实现
- **Wi-Fi STA**：`wifi_init_sta()` 完成 `esp_netif_init` → `esp_event_loop_create_default` → `esp_netif_create_default_wifi_sta` → `esp_wifi_init/start` → `esp_wifi_connect`，含 5 次重试 + 30s 超时事件组
- **MQTT 客户端**：`mqtt_init_client()` 连接巴法云 broker（`mqtt://bemfa.com:9501`），ClientID=UID；`mqtt_publish_payload()` 实现 base64 编码（`mbedtls/base64`）→ JSON `{"payload_b64":"..."}` → topic `{room}{bed}tof1/tof2/mlx1/mlx2`（小写拼接）→ `esp_mqtt_client_publish`
- **回传路径**：`usb_send_tof_payload()` 和 `mlx_sender_task()` 在 USB CDC 发送后并行 MQTT publish
- **NVS 配置**：`config_is_complete()` 检查 room/bed/ssid/uid 四字段完整性
- **USB 契约**：保持 `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`，CRC16-CCITT 仅覆盖 payload，ToF payload 保持完整 MaixSense 原始帧

### 编译说明
- `esp_mqtt` 组件在此 IDF v6.0.1 安装中不可用（组件目录无 CMakeLists.txt，组件注册表 HTTP 403）
- MQTT 代码通过 `CONFIG_MQTT_BACKHAUL_ENABLED=0` 条件编译关闭，不影响 USB CDC 功能
- 已实现 MQTT 代码完整保留在主文件中，启用条件：安装 `esp_mqtt` 组件后，将 `CONFIG_MQTT_BACKHAUL_ENABLED=0` 改为 `1` 即可编译所有 MQTT 功能

### 编译依赖
- `main/CMakeLists.txt` REQUIRES：`mlx90640, esp_tinyusb, esp_driver_uart, driver, nvs_flash, esp_wifi, esp_netif, esp_event, mbedtls`
- `main/idf_component.yml`：`espressif/esp_tinyusb: ^2.0.1~1`

## 本地测试与编译验证结果

### python tests\run_public_tests.py project2_task
```
test_compile.py — 1 test OK
test_functional_smoke.py — 2 tests OK
test_refactored_features.py — 3 tests OK
test_smoke_gateway.py — 1 test OK
[public] all public tests passed
```

### python tools\run_debug_probe.py project2_task
```
[probe:ok] admin setup returns 200
[probe:ok] management API rejects missing cookie
[probe:ok] management API rejects forged cookie
[probe:ok] management API accepts valid cookie
[probe:ok] unknown identity session is denied
[probe:ok] expired session is denied
[probe:ok] care_event write rejects missing admin cookie
[probe:ok] care_event normalizes room/bed for create and query
[probe] all visible diagnostic checks passed
```

### python tools\run_espidf_build.py project2_task
- 编译目标：esp32s3
- 结果：**BUILD SUCCESSFUL**（`stdpro.bin` 809648 bytes, 23% flash 空闲）
- 警告（非阻塞）：MaixSenseFrameParser/UARTConfig 的 missing-field-initializers（预存在）、I2C legacy driver 弃用提示、部分 Kconfig 符号未知
- MQTT 组件不可用时的处理：`CONFIG_MQTT_BACKHAUL_ENABLED=0` 条件下编译，WiFi+MQTT 实现代码完整保留在主文件中（`#if CONFIG_MQTT_BACKHAUL_ENABLED` 守卫）

## 未验证的残留技术债与风险

1. **MQTT 运行时验证**：MQTT 代码逻辑已编写并通过编译禁用模式验证（无编译错误），但未在真实 MQTT broker 连接环境下测试。需在开发板烧录后验证 base64 编码正确性、topic 拼接、MQTT broker 连接和 QoS 1 消息投递
2. **voice/助手 session 联动**：收紧鉴权后，voice 模块通过 `VOICE_SESSION_ID` 环境变量传入 session；若未设置且无 ambient session，`/api/v3/context/chat` 将返回 denied。当前 `voice_assistant_integrated.py` 不会主动调用 `/api/v3/session/current`，依赖外部在启动时提供有效 session_id
3. **ESIDF sdkconfig 符号适配**：`sdkconfig.defaults` 中多个新配置符号（`CONFIG_ESP_WIFI_ENABLED`, `CONFIG_WIFI_*`, `CONFIG_MQTT_*`, `CONFIG_MBEDTLS_*`）在 IDF v6.0.1 的 Kconfig 中不存在或已重命名，当前仅起文档作用（构建系统产生 unknown symbol 警告但不影响编译）
4. **I2C legacy driver 弃用**：`components/mlx90640` 使用已弃用的 `driver/i2c.h`，IDF v6.0.1 提示需迁移到 `driver/i2c_master.h`，当前 `-Wno-error=type-limits` 抑制了相关警告。IDF v7.0 将移除旧驱动
5. **历史 SQLite 迁移**：`care_events` 迁移逻辑仅处理缺列场景。旧数据中 `ts` 字段缺失时用 `created_ts` 填充，但无法保证原始语义正确
6. **患者数据零泄漏**：`build_chat_context_v3` 的未认证/未授权分支不返回 care_events/memory/patient 字段，但未对所有潜在泄漏路径（如 worker 直接调用 DB 函数）做审计
