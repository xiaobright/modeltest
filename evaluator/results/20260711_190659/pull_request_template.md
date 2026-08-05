# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行 `python tests\run_public_tests.py project2_task` 和 `python tools\run_debug_probe.py project2_task`，结果如下：

**公共测试**：全部通过（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway），但公共测试仅做冒烟检查，不覆盖安全边界。

**Debug Probe 诊断**：6 项失败：
1. `management API rejects missing cookie` — 缺少 Cookie 时 `/api/v3/subjects` 返回 200，应为 401。根因：`_authorized_for_api` 对所有本机请求放行，未限制到白名单路径。
2. `management API rejects forged cookie` — 伪造 Cookie 时 `/api/v3/subjects` 返回 200，应为 401。根因：`get_admin_http_session` 查询任意活跃 session 而非按 token_hash 匹配。
3. `unknown identity session is denied` — `identity_state=unknown` 的 session 仍被判定为已认证。根因：`session_is_authenticated` 对 unknown 状态特殊放行。
4. `expired session is denied` — 过期 session 仍被判定为已认证。根因：`session_is_authenticated` 未检查 `expires_ts`。
5. `care_event write rejects missing admin cookie` — `POST /api/v3/care/events` 返回 404。根因：路由未注册。
6. `care_event normalizes room/bed for create and query` — 写入 `r1203/b1` 后用 `R1203/B1` 查询返回空。根因：`create_care_event` / `list_care_events` 未规范化 room/bed。

另有 Voice 路径 Warning：voice 模块未显式获取 current session，收紧鉴权后可能无法取上下文。

## 修改的文件列表

### Gateway Python
| 文件 | 修改内容 |
|------|----------|
| `gateway/auth.py` | 修复明文密码存储（始终生成 salt + PBKDF2 哈希）；`admin_account_exists` 改为查 DB；`get_admin_http_session` 改为按 token_hash 查询而非任意活跃 session |
| `gateway/db.py` | `care_events` 表新增 `severity/source/created_by/ts` 列；新增 `_migrate_care_events()` 对旧表执行 `ALTER TABLE ADD COLUMN` 迁移，保留旧数据并回填 `ts` |
| `gateway/care_events.py` | 补全 `severity/source/created_by/ts` 字段写入；`create_care_event` 和 `list_care_events` 规范化 room/bed 到大写；`list_care_events` 添加 `limit` 参数并按 `ts` 倒序；实现 `build_care_events_context()` |
| `gateway/gateway.py` | `_authorized_for_api` 限制本机放行仅限白名单服务路径；`session_is_authenticated` 严格检查 identity_state/assurance_level/expires_ts/actor_subject_id；`actor_can_access_target` 不再对无 actor 放行；新增 `GET/POST /api/v3/care/events` 路由；`build_chat_context_v3` modalities 增加 `care_events`；导入 `DEFAULT_ADMIN_SUBJECT_ID` 和 `care_events` 模块 |
| `gateway/sleep_importer.py` | 修复 `first` 策略 bug：`beds[-1]` → `beds[0]`（应写入第一个配置床位而非最后一个） |
| `voice/voice_assistant_integrated.py` | 新增 `fetch_current_session()` 函数，请求 `/api/v3/session/current` 获取当前 session_id；`fetch_gateway_chat_context` 在无 session_id 时主动获取，不再依赖隐式 ambient session |

### ESP32-S3 固件
| 文件 | 修改内容 |
|------|----------|
| `esp32/testpro4/main/protocol_packet.h` | 新建：USB packet 常量、`protocol_build_header()` 内联函数、`crc16_ccitt()` 声明 |
| `esp32/testpro4/main/protocol_packet.cpp` | 新建：CRC16-CCITT 实现（init 0xFFFF, poly 0x1021） |
| `esp32/testpro4/main/device_config.h` | 新建：device_config_t 结构、NVS 加载/校验、topic 规范化、控制台命令接口 |
| `esp32/testpro4/main/device_config.cpp` | 新建：从原 main.cpp 抽取的 NVS 配置管理（CFG?/CFGSET/CFGRESET/REBOOT）、topic 构建 `{room}{bed}{suffix}` 小写拼接 |
| `esp32/testpro4/main/mqtt_payload.h` | 新建：`mqtt_payload_build_json()` 声明和 `mqtt_payload_json_size()` 大小计算 |
| `esp32/testpro4/main/mqtt_payload.cpp` | 新建：使用 mbedtls/base64.h 编码 payload，构建 `{"payload_b64":"..."}` JSON |
| `esp32/testpro4/main/network_backhaul.h` | 新建：Wi-Fi STA + MQTT 客户端初始化和发布接口 |
| `esp32/testpro4/main/network_backhaul.cpp` | 新建：Wi-Fi STA 连接管理（自动重连）、巴法云 MQTT 客户端（broker=bemfa.com:9501, client_id=uid）、`network_backhaul_publish()` 构建 topic 并发布 base64 payload |
| `esp32/testpro4/main/main.cpp` | 重构：使用 protocol_packet/device_config/network_backhaul 模块替代内联代码；`usb_send_tof_payload()` 和 `mlx_sender_task()` 在 USB CDC 输出同时向 MQTT topic 发布原始 payload；`app_main()` 新增 `esp_netif_init()` + `esp_event_loop_create_default()` + `network_backhaul_init()` |
| `esp32/testpro4/main/CMakeLists.txt` | 新增源文件和 `REQUIRES`: esp_wifi, esp_netif, esp_event, mqtt, mbedtls |
| `esp32/testpro4/main/idf_component.yml` | 新增 `espressif/mqtt: "*"` 依赖 |
| `esp32/testpro4/sdkconfig.defaults` | 新增 Wi-Fi 和 MQTT Kconfig 配置项 |

## 架构调整与模块设计

Gateway 保持已有模块边界，未将逻辑塞回 `gateway.py`：

- `auth.py` — 管理员账号、密码 PBKDF2 哈希、Cookie token 会话
- `db.py` — SQLite schema + care_events 旧表迁移
- `care_events.py` — care_event CRUD + context 构建
- `gateway.py` — 仅路由 glue，不含业务逻辑
- `sleep_importer.py` — CSV 导入 + 无归属行策略

ESP32 固件按 ONBOARDING_TODO 推荐拆分：
- `protocol_packet.{h,cpp}` — USB packet 常量和 CRC16-CCITT
- `device_config.{h,cpp}` — NVS 配置和 topic 规范化
- `mqtt_payload.{h,cpp}` — base64 JSON 构造
- `network_backhaul.{h,cpp}` — Wi-Fi + MQTT 生命周期管理
- `main.cpp` — ESP-IDF 初始化、任务创建、硬件调用和模块 glue

## 安全边界及鉴权设计

1. **管理员密码**：使用 PBKDF2-HMAC-SHA256（200k 迭代）+ 随机 16 字节 salt 哈希存储，数据库只保存 salt_hex 和 digest_hex，不保存明文。
2. **Cookie 会话**：Cookie 只存随机 token（`secrets.token_urlsafe(32)`），数据库保存 `token_hash`（SHA-256）。`get_admin_http_session` 严格按 token_hash 查询，不再返回任意活跃 session。
3. **管理 API 鉴权**：`_authorized_for_api` 仅在以下情况放行：
   - 有效的管理员 Cookie session（token_hash 匹配 + 未过期）
   - 本机请求 **且** 路径在白名单内（`/api/v2/*`, `/api/esp/*`, `/api/v3/context/chat`, `/api/v3/identity/*`, `/api/v3/vision/observation`）
   - 其他本机管理 API（如 `/api/v3/subjects`）无 Cookie 时返回 401
4. **V3 授权上下文**：`session_is_authenticated` 严格按 api_contracts.md 约束：
   - `identity_state=unknown` 或空 → 未认证
   - `assurance_level=none` 或空 → 未认证
   - `expires_ts` 已过期 → 未认证
   - 缺少 `actor_subject_id` → 未认证
5. **actor 权限裁剪**：`actor_can_access_target` 不再对无 actor 放行；admin/staff 可访问任意目标，patient 只能访问自己。
6. **Voice 路径**：voice 模块新增 `fetch_current_session()` 显式获取 session_id，不依赖 gateway 隐式 ambient session。收紧鉴权后未认证请求返回 `policy.allowed=false`，voice 只回复权限提示不返回患者数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

按 ONBOARDING_TODO 规范实现逐行策略（`sleep_importer.py` 的 `row_targets`）：

- 行带 `room/bed`：只写入对应床位（与配置床位大小写不敏感匹配）
- 行不带 `room/bed`：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 时 → 写入指定床位
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入第一个配置床位 `beds[0]`（**修复了原 `beds[-1]` bug**）
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 写入所有配置床位（仅调试模式）
- 同一 CSV 内混合有归属行和无归属行时：策略只作用于无归属行，有归属行按原值写入，不误改或丢弃。

## care_event 实现细节

**DB Schema**（`db.py`）：
```sql
CREATE TABLE IF NOT EXISTS care_events (
    event_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    room TEXT NOT NULL,
    bed TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'info',
    source TEXT NOT NULL DEFAULT 'manual',
    created_by TEXT NOT NULL DEFAULT '',
    ts INTEGER NOT NULL DEFAULT 0,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);
```

**旧表迁移**（`_migrate_care_events`）：使用 `PRAGMA table_info` 检查缺失列，对 `severity/source/created_by/ts` 逐个 `ALTER TABLE ADD COLUMN`，旧行 `ts` 从 `created_ts` 回填，旧数据不丢失。

**API 路由**（`gateway.py`）：
- `POST /api/v3/care/events` — 需要管理员登录，无 Cookie 返回 401
- `GET /api/v3/care/events` — 需要管理员登录，支持 `subject_id` / `room+bed` / `limit` 查询参数
- room/bed 写入和查询均规范化为大写，`r1203/b1` 写入可被 `R1203/B1` 查询到
- 查询结果按 `COALESCE(NULLIF(ts, 0), created_ts)` 倒序排列

**Context 集成**（`build_chat_context_v3`）：授权通过后在 `modalities.care_events` 返回最近 10 条事件摘要 + brief；未授权时不返回。

## ESP32-S3 固件接口对齐说明

**Wi-Fi STA**（`network_backhaul.cpp`）：
- 从 NVS 读取 `wifi_ssid/wifi_password`，初始化 Wi-Fi STA 模式
- 事件处理器处理 `WIFI_EVENT_STA_START`（自动连接）、`WIFI_EVENT_STA_DISCONNECTED`（1s 后重连）、`IP_EVENT_STA_GOT_IP`
- `device_config_network_ready()` 校验 ssid/uid/room/bed 均非空

**MQTT 巴法云**（`network_backhaul.cpp`）：
- Broker: `mqtt://{bemfa_host}:{bemfa_port}`（默认 bemfa.com:9501）
- ClientID: NVS 中的 `bemfa_uid`
- 事件处理：`MQTT_EVENT_CONNECTED` / `MQTT_EVENT_DISCONNECTED` / `MQTT_EVENT_ERROR`
- `network_backhaul_publish()` 在 MQTT 连接就绪时发布，否则静默跳过

**Topic 规范化**（`device_config.cpp`）：
- `device_config_build_topic(dst, len, suffix)` 构建 `{room}{bed}{suffix}` 全小写 topic
- suffix: `tof1` / `tof2` / `mlx1` / `mlx2`

**MQTT Payload**（`mqtt_payload.cpp`）：
- JSON: `{"payload_b64":"<base64>"}`
- base64 内容是传感器原始 payload（ToF 完整 MaixSense 帧 / MLX 3072 字节 float32），**不是**完整 USB packet
- 使用 mbedtls/base64.h 编码，JSON buffer 在堆上分配（ToF payload ~10KB → base64 ~14KB）

**USB + MQTT 双通道**：
- `usb_send_tof_payload()`：USB CDC 1 输出完整 USB packet（`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`），同时向 MQTT topic `{room}{bed}tof{1|2}` 发布原始 payload 的 base64
- `mlx_sender_task()`：USB CDC 0 输出 MLX packet，同时向 MQTT topic `{room}{bed}mlx{1|2}` 发布原始 payload 的 base64

**USB Packet 契约**（`protocol_packet.h/cpp`）：
- 格式：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`
- TYPE: 0x01=MLX, 0x02=ToF
- CRC16-CCITT: init 0xFFFF, poly 0x1021，只覆盖 payload
- LEN 和 CRC 均为小端序

**ToF Payload**：保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`，不裁剪为 10000B 图像区。

**NVS 配置**：通过串口命令配置，`CFGSET ssid=...` / `CFGSET password=...` / `CFGSET uid=...` / `CFGSET room=...` / `CFGSET bed=...`，`REBOOT` 生效。

**idf_component.yml**：新增 `espressif/mqtt: "*"` 依赖（解析为 1.0.0）。

**CMakeLists.txt**：REQUIRES 新增 `esp_wifi esp_netif esp_event mqtt mbedtls`。

## 本地测试与编译验证结果

修复后运行：

### 公共测试
```
python tests\run_public_tests.py project2_task
```
结果：**全部通过**（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway）

### Debug Probe 诊断
```
python tools\run_debug_probe.py project2_task
```
结果：**全部 7 项检查通过**（0 failures）
- [probe:ok] admin setup returns 200
- [probe:ok] management API rejects missing cookie
- [probe:ok] management API rejects forged cookie
- [probe:ok] management API accepts valid cookie
- [probe:ok] unknown identity session is denied
- [probe:ok] expired session is denied
- [probe:ok] care_event write rejects missing admin cookie
- [probe:ok] care_event normalizes room/bed for create and query
- [probe:info] voice module appears to reference current-session fetch

### ESP-IDF 编译
```
python tools\run_espidf_build.py project2_task
```
说明：`idf.py` 在本机环境中无法找到 Ninja（PowerShell 子进程 PATH 传递问题），因此改为直接通过 `cmake -G Ninja` 配置 + `cmake --build build` 编译。ESP-IDF v6.0.1 + Ninja 1.12.1 + xtensa-esp-elf-gcc 15.2.0。

结果：**编译成功**
- 配置阶段：1099 个编译目标，依赖解析通过（espressif/mqtt 1.0.0, espressif/esp_tinyusb 2.2.0, espressif/tinyusb 0.19.0~3）
- 编译阶段：全部 152 步通过，0 个编译错误
- 链接阶段：`stdpro.elf` 和 `stdpro.bin` 生成成功
- 固件大小：`stdpro.bin` = 0xefff0 bytes (983,024 bytes)，1MB factory 分区剩余 6%（0x10010 bytes free）
- Bootloader：`bootloader.bin` = 0x5760 bytes，32% free

输出文件：
- `E:/esp/builds/modeltest/project2_task/esp32/testpro4/build/stdpro.bin`
- `E:/esp/builds/modeltest/project2_task/esp32/testpro4/build/bootloader/bootloader.bin`
- `E:/esp/builds/modeltest/project2_task/esp32/testpro4/build/partition_table/partition-table.bin`

编译警告（不影响功能）：
- `CONFIG_TINYUSB_ENABLED` 和 `CONFIG_USB_OTG_SUPPORTED` 在 IDF v6.0 中已更名（kconfig warning）
- `CONFIG_ESP32S3_SPIRAM_SUPPORT` → `CONFIG_SPIRAM`，`CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240` → `CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240`（自动替换）
- `MQTT_TASK_STACK_SIZE` kconfig 符号在 managed_component 中定义为 disabled（不影响编译）

## 未验证的残留技术债与风险

1. **ESP-IDF `idf.py` Ninja PATH 问题**：本机 `idf.py` 内部调用 cmake 时无法找到 Ninja，需用 `cmake --build` 直接替代。这是环境配置问题，不是代码问题。
2. **Wi-Fi/MQTT 实机连通性**：本任务不要求真实 Wi-Fi/MQTT 连接、真实 I2C 温度读数、真实 USB 枚举或 ToF 上电时序。编译通过但不验证实机行为。
3. **sdkconfig.defaults Kconfig 符号更名**：`CONFIG_TINYUSB_ENABLED` 和 `CONFIG_USB_OTG_SUPPORTED` 在 IDF v6.0 中可能已更名，当前仅产生 warning 不影响编译。后续可更新为正确符号名。
4. **固件分区余量**：`stdpro.bin` 占用 1MB factory 分区的 94%，剩余 6%（约 64KB）。后续如需添加 OTA 或更大功能，需扩大 partition table。
5. **ESP32 `mqtt_client.h` 类型转换**：`ESP_EVENT_ANY_ID`（int -1）到 `esp_mqtt_event_id_t` 的转换在 C++ 中需要显式 cast（已在代码中处理）。
6. **Voice 模块实机验证**：`fetch_current_session()` 函数已添加，但在无 gateway 运行或无活跃 session 时返回 None，voice 会使用空 session_id 请求上下文（gateway 会返回 `policy.allowed=false`）。实机需确保 gateway 先启动并完成身份识别。
7. **旧 SQLite 迁移测试**：care_events 迁移逻辑已实现 `ALTER TABLE ADD COLUMN` + `ts` 回填，但未使用真实 legacy_sample.db 实测。公共测试和 probe 均使用临时空库。
8. **隐藏测试覆盖**：公共测试和 debug probe 不覆盖所有安全边界。hidden tests 可能检查更严格的越权场景、face template 导出鉴权、credential template 防泄漏等。
