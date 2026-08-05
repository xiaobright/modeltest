# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修复前运行结果：

```
python tests\run_public_tests.py project2_task  → 全部通过 (7/7)

python tools\run_debug_probe.py project2_task   → 6 项失败:
  [probe:FAIL] management API rejects missing cookie (status=200, should be 401)
  [probe:FAIL] management API rejects forged cookie (status=200, should be 401)
  [probe:FAIL] unknown identity session is denied (policy allowed=True, should be False)
  [probe:FAIL] expired session is denied (policy allowed=True, should be False)
  [probe:FAIL] care_event write rejects missing admin cookie (status=404, route not wired)
  [probe:FAIL] care_event normalizes room/bed for create and query (query returned empty)
```

根因分析：
1. `auth.py`: `admin_account_exists()` 永远返回 False，创建管理员账户不阻塞重复创建
2. `auth.py`: `_password_hash()` 空 salt 时返回明文密码
3. `auth.py`: `get_admin_http_session()` 不校验 token_hash，取任意活跃会话
4. `gateway.py`: `session_is_authenticated()` 对 unknown identity_state 返回 True
5. `gateway.py`: `_authorized_for_api()` 对本机请求完全放行，管理 API 无保护
6. `gateway.py`: care_event 路由未接入 POST/GET /api/v3/care/events
7. `care_events.py`: `build_care_events_context()` 为空桩，缺少 severity/source/created_by/ts 字段，room/bed 无规范化，无 limit
8. `sleep_importer.py`: `first` 策略使用 `beds[-1]`（末尾床位）而非 `beds[0]`（首个床位）

## 修改的文件列表

### gateway/ (Python backend)
| 文件 | 修改内容 |
|------|----------|
| `gateway/auth.py` | 修复 `admin_account_exists()` 查 DB；`_password_hash()` 输入空 salt 时生成随机 salt 并正确哈希；`get_admin_http_session()` 按 token_hash 精确匹配 |
| `gateway/gateway.py` | 修复 `session_is_authenticated()`：拒绝 unknown identity/空 assurance/无 actor_subject_id/过期会话；`_authorized_for_api()` 仅对 `_path_allows_local_service()` 路径放行本机；新增 `import care_events` 和 GET/POST `/api/v3/care/events` 路由；`build_chat_context_v3` 新增 `modalities.care_events` 字段和 care_events context |
| `gateway/care_events.py` | `init_care_events_table()` 接受可选 conn 参数避免锁竞争，新增 PRAGMA table_info 迁移逻辑（补 severity/source/created_by/ts）；`create_care_event()` 写入全部列并规范化 room/bed（uppercase）；`list_care_events()` 支持 limit 参数和 room/bed case-insensitive 查询（normalize）；`build_care_events_context()` 从桩实现改为真实查询并构造 brief |
| `gateway/db.py` | `init_management_db()` 中的 care_events 建表 SQL 补全 severity/source/created_by/ts 列；延迟 import `init_care_events_table`（从函数内 import 避免循环依赖），传入已有 conn |
| `gateway/sleep_importer.py` | `first` 策略从 `beds[-1]` 修正为 `beds[0]` |

### esp32/testpro4/ (ESP32-S3 firmware)
| 文件 | 修改内容 |
|------|----------|
| `main/main.cpp` | 重构：引入 Wi-Fi STA 初始化 (`init_wifi_sta`)、MQTT 客户端 (`mqtt_app_start`)、Wi-Fi 事件处理；`usb_send_tof_payload()` 新增 MQTT 并行发布 (`mqtt_publish_raw`)；`mlx_sender_task()` 新增 MQTT 发布 MLX 数据；删除重复定义（crc16_ccitt、packet 常量、MaixSenseFrameParser）改为引用模块头文件 |
| `main/protocol_packet.h` | 新增：USB packet 常量（PACKET_SYNC1/SYNC2/SENSOR_TYPE_*）、crc16_ccitt() 声明、build_usb_packet() 声明 |
| `main/protocol_packet.cpp` | 新增：CRC16-CCITT 实现（初始值 0xFFFF，多项式 0x1021）、完整 USB packet 打包函数 |
| `main/maixsense_parser.h` | 新增：MaixSenseFrameParser 结构体、parse_maixsense_frame() 声明 |
| `main/maixsense_parser.cpp` | 新增：MaixSense 帧解析器实现（处理噪声/分块/坏尾字节/异常长度/半帧） |
| `main/device_config.h` | 新增：device_config_t 结构体、load/save/print/build_topic_names 声明 |
| `main/device_config.cpp` | 新增：NVS 配置读写、room/bed 校验、topic 规范化（lowercase 拼接：`{room}{bed}tof1/tof2/mlx1/mlx2`）、控制台配置命令 |
| `main/mqtt_payload.h` | 新增：payload_b64 JSON 构造、MQTT topic 选择声明 |
| `main/mqtt_payload.cpp` | 新增：mbedtls base64 编码构造 `{"payload_b64":"..."}` JSON、按 sensor type/id 选择 MQTT topic |
| `main/CMakeLists.txt` | 新增 SRCS（4 个新 .cpp 文件）、REQUIRES（esp_wifi/esp_netif/esp_event/lwip/mbedtls）；MQTT 依赖通过 idf_component.yml 管理 |
| `main/idf_component.yml` | 新增 `espressif/esp_mqtt: '*'` MQTT 客户端组件依赖 |

## 架构调整与模块设计

1. **Admin 鉴权闭环**：`auth.py` 独立维护管理员密码 PBKDF2-SHA256 加盐哈希 + token SHA256 哈希存储；Cookie 仅存随机 token；`get_admin_http_session` 严格按 token_hash 匹配并检查过期；管理 API 路径（subjects/assignments/memories/credentials/care_events）拒绝本机无 cookie 请求
2. **Session 权限裁剪**：`session_is_authenticated` 拒绝 identity_state=unknown、assurance_level=none、缺少 actor_subject_id、过期会话；`actor_can_access_target` 限制 patient 角色仅能访问自身数据
3. **care_events 模块**：独立 `gateway/care_events.py` 负责 CRUD 和 context 聚合；不扩大 subjects.py；路由 glue 仅放在 gateway.py
4. **ESP32 模块拆分**：五模块结构（protocol_packet / maixsense_parser / device_config / mqtt_payload / main）分工明确；main.cpp 仅保留初始化、任务创建和 glue
5. **DB 迁移架构**：`init_care_events_table(conn=None)` 同时支持全新建表和旧表迁移（ALTER TABLE ADD COLUMN），传入 conn 时共享事务避免 SQLite 锁

## 安全边界及鉴权设计

| 场景 | 行为 |
|------|------|
| 远程未登录 → 管理 API | 返回 401 `admin authentication required` |
| 远程伪造 Cookie → 管理 API | 返回 401（token_hash 不匹配） |
| 本机无 Cookie → 管理 API | 返回 401（仅 service endpoints 允许本机免登录） |
| 本机无 Cookie → `/api/v2/*`, `/api/esp/*`, `/api/v3/context/chat`, `/api/v3/identity/gallery`, `/api/v3/identity/match`, `/api/v3/vision/observation` | 正常放行 |
| 管理员登录后 → 所有 API | 正常访问 |
| staff/admin session → `/api/v3/context/chat` 查任意患者 | 返回完整上下文 |
| patient session → `/api/v3/context/chat` 查自己 | 返回完整上下文 |
| patient session → 查他人 | 返回 `policy.allowed=false` + 空 modalities |
| unknown identity session | `session_is_authenticated()` 返回 False，context 拒绝 |
| 过期 session | `session_is_authenticated()` 返回 False（expires_ts < now_ms） |

- 管理员密码 PBKDF2-SHA256 加盐哈希存储，不存明文
- Cookie 仅存随机 token（secrets.token_urlsafe(32)），DB 存 token SHA256 hash
- identity gallery / credential template 远程访问返回 403
- voice 助手通过 session_id 参数获取上下文，不再依赖隐式 ambient session

## 睡眠 CSV 无 room/bed 时的特殊处理

策略按 `sleep_importer.py:row_targets()` 逐行处理：

| 行情况 | 行为 |
|--------|------|
| 行含 room + bed | 直接写入对应床位（与配置 BEDS 列表比对确认） |
| 行无 room/bed + `SLEEP_IMPORT_DEFAULT_ROOM/BED` 已设置 | 写入指定床位 |
| 行无 room/bed + `SLEEP_IMPORT_UNSCOPED_POLICY=first` | 写入配置列表第一个床位 `beds[0]`（修正前为 `beds[-1]`） |
| 行无 room/bed + `SLEEP_IMPORT_UNSCOPED_POLICY=skip` | 跳过该行 |
| `SLEEP_IMPORT_UNSCOPED_POLICY=all` | 写入所有配置床位（仅显式调试，不默认） |
| 同一 CSV 混合有无归属行 | 显式归属行不受策略影响；策略仅作用无归属行 |

## care_event 实现细节

**DB Schema**（含旧表迁移）：
- 全新建表包含全部列：event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts
- 旧表缺列时 ALTER TABLE ADD COLUMN 补齐：severity(默认'info'), source(默认'manual'), created_by(默认''), ts(默认0, UPDATE 填充为 created_ts)

**API**：
- `POST /api/v3/care/events`：创建事件，需管理员登录；body 自动规范化 room/bed 为 uppercase
- `GET /api/v3/care/events`：查询支持 subject_id / room / bed / limit，按 ts 倒序；room/bed 参数自动 uppercase 规范化（lowercase 写入的记录也能被 uppercase 查询找到）

**Context 集成**：
- `/api/v3/context/chat` 授权通过后，`modalities.care_events` 返回最近 10 条事件摘要
- 未授权时 care_events 为空 items/brief
- brief 格式：`"kind/title: content | kind/title: content"` 管道分隔

## ESP32-S3 固件接口对齐说明

### 实现的模块
| 模块 | 文件 | 职责 |
|------|------|------|
| 协议封包 | `protocol_packet.{h,cpp}` | USB packet 常量、CRC16-CCITT（初始0xFFFF，多项式0x1021，仅覆盖payload，小端序）、pack/unpack |
| MaixSense 解析 | `maixsense_parser.{h,cpp}` | 字节流解析：[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]，处理噪声/分块/坏尾字节/异常长度/半帧 |
| 设备配置 | `device_config.{h,cpp}` | NVS 读写 ssid/password/uid/room/bed/host/port/device_id；topic 规范化（lowercase 拼接）；CFG?/CFGSET/CFGRESET/REBOOT 控制台命令 |
| MQTT 载荷 | `mqtt_payload.{h,cpp}` | base64 编码 (`mbedtls/base64.h`) 构造 `{"payload_b64":"<base64>"}` JSON；按 sensor_type/id 选择 topic |
| 主程序 | `main.cpp` | Wi-Fi STA 事件驱动 + MQTT 巴法云客户端；USB CDC 保留双输出；ToF 帧解析+交替发送+MQTT 并行发布；MLX 温度数据 USB+MQTT 双发 |

### 协议对齐
- **USB packet**: `[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD...][CRC_L][CRC_H]`，TYPE=0x01(MLX)/0x02(ToF)，CRC16-CCITT 仅覆盖 payload，小端序
- **ToF payload**: 完整 MaixSense 原始帧（不裁剪 10000B 图像区）
- **MQTT topic**: `{room}{bed}tof1`, `{room}{bed}tof2`, `{room}{bed}mlx1`, `{room}{bed}mlx2` — 全部 lowercase
- **MQTT JSON**: `{"payload_b64":"<base64 raw payload>"}` — base64 编码的是原始 payload，不是完整 USB packet
- **NVS 配置**: 统一固件通过串口 CFGSET 写入，REBOOT 后生效；Wi-Fi + 巴法云 UID 缺失时仅运行 USB 模式

## 本地测试与编译验证结果

### 单元/功能测试（通过）
```
python tests\run_public_tests.py project2_task
  → OK (7/7 全部通过)
  - test_core_python_files_compile: ok
  - test_admin_page_is_served: ok
  - test_admin_setup_endpoint_responds: ok
  - test_admin_auth_module_callable: ok
  - test_care_events_module_callable: ok
  - test_sleep_importer_module_callable: ok
  - test_gateway_import_and_management_db: ok
```

### 诊断自检（全部通过）
```
python tools\run_debug_probe.py project2_task
  → [probe] all visible diagnostic checks passed
  [probe:ok] admin setup returns 200
  [probe:ok] management API rejects missing cookie
  [probe:ok] management API rejects forged cookie
  [probe:ok] management API accepts valid cookie
  [probe:ok] unknown identity session is denied
  [probe:ok] expired session is denied
  [probe:ok] care_event write rejects missing admin cookie
  [probe:ok] care_event normalizes room/bed for create and query
  [probe:Warning] Voice/assistant path: 助手需显式通过 session_id 获取上下文
```

### ESP-IDF 编译结果（失败）
```
python tools\run_espidf_build.py project2_task
  → ERROR: build failed
```

**失败位置**：CMake 配置阶段 — 依赖解析失败

**失败原因**：
1. 本机 ESP-IDF v6.0.1 的组件注册表中未找到 `espressif/mqtt` 或 `espressif/esp_mqtt` 组件
2. `E:\esp\v6.0.1\esp-idf\components\mqtt\` 目录存在但无 CMakeLists.txt（v6 中 MQTT 客户端被移出核心仓库，移至 esp-protocols）
3. 组件管理器尝试 `espressif/mqtt ^1.1.0` → 无匹配版本，`espressif/mqtt *` → 无匹配版本，`espressif/esp_mqtt *` → 无匹配版本

**执行命令**：
```powershell
python tools\run_espidf_build.py project2_task
```

等效的 PowerShell 入口：
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_espidf_windows_build.ps1 -ProjectDir .\project2_task -Target esp32s3
```

**当前状态**：ESP32 固件源代码（main.cpp + 4 个新模块 + CMakeLists.txt + idf_component.yml）已按 `reference/espidf_protocol_contract.md` 完整实现。编译阻塞在 MQTT 组件依赖解析阶段。如需编译通过，需：
- 方案 A：在 ESP-IDF v5.x 环境下编译（MQTT 仍为内置组件）
- 方案 B：手动将 `esp-protocols/components/esp_mqtt` 克隆到 `E:\esp\v6.0.1\esp-idf\components\esp_mqtt\`
- 方案 C：在 idf_component.yml 中指定 Git 仓库依赖 `espressif/esp_mqtt` 的特定版本号

**非代码问题**：编译结果中 CMake 配置阶段的 `esp_wifi`、`esp_netif`、`esp_event`、`lwip`、`mbedtls` 等依赖均已通过，仅 MQTT 组件缺失。

## 未验证的残留技术债与风险

| 项目 | 风险说明 |
|------|----------|
| ESP32 固件编译 | 未通过 idf.py build，因 ESP-IDF v6.0.1 MQTT 组件未就绪。推荐在 ESP-IDF v5.x 环境或补装 esp_mqtt 后重试 |
| ESP32 实机测试 | 未执行 idf.py flash/monitor；未验证真实 USB 枚举、Wi-Fi 连接、MQTT 连通性、ToF 上电时序、MLX90640 I2C 读数 |
| Voice/助手路径 | 收紧鉴权后助手需通过 session_id 获取上下文；环境不支持时 voice 可能因无有效 session 拿不到患者数据（此为设计预期） |
| care_events 跨模块查询 | `/api/v3/care/events` 的 room/bed 查询依赖 upper-case 规范化写入；若历史数据混用大小写，需确保查询路径一致使用 normalize_room/normalize_bed |
| 数据库迁移 | care_events 旧表迁移通过 PRAGMA table_info 检测并 ALTER TABLE；若旧表有其他未知列组合，迁移只补齐缺失列，不影响已有数据 |
| 实时环境压测 | 未在多床位、高频传感器数据、大量 care_event 并发写场景下测试 |
| 前端适配 | admin.html / dashboard.html 未针对 care_event 新增面板（需后续前端迭代） |
