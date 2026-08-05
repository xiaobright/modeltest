# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行结果：

`python tests\run_public_tests.py project2_task`
```
[public] all public tests passed
```
7/7 公开测试通过。

`python tools\run_debug_probe.py project2_task`
```
[probe:ok] admin setup returns 200
[probe:FAIL] management API rejects missing cookie status=200
[probe:FAIL] management API rejects forged cookie status=200
[probe:ok] management API accepts valid cookie
[probe:FAIL] unknown identity session is denied policy={'allowed': True}
[probe:FAIL] expired session is denied policy={'allowed': True}
[probe:FAIL] care_event write rejects missing admin cookie status=404
[probe:FAIL] care_event normalizes room/bed for create and query rows=[]
[probe:Warning] Voice/assistant path warning
[probe] failures=6
```

## 修改的文件列表

### Gateway（Python 后端）
- `gateway/auth.py` — 修复密码哈希（始终加盐 PBKDF2）、admin_account_exists 查询实际 DB、session token 精确匹配
- `gateway/db.py` — care_events 表补全 severity/source/created_by/ts 列，新增 _migrate_missing_columns 迁移逻辑
- `gateway/care_events.py` — 完全重写：完整 schema、room/bed 规范化、limit 参数、context 聚合实现
- `gateway/gateway.py` — 管理 API 鉴权区分本地服务 vs 管理路由、session_is_authenticated 收紧、新增 care_event 路由（POST/GET）、chat context v3 集成 care_events、补全 DEFAULT_ADMIN_SUBJECT_ID 导入
- `gateway/subjects.py` — get_session 增加 expires_ts 过期检查
- `gateway/sleep_importer.py` — 修复 unscope policy 'first' 使用 beds[0] 而非 beds[-1]

### ESP32-S3 固件（esp32/testpro4/main/）
- `protocol_packet.h` / `protocol_packet.cpp` — USB packet 常量、CRC16-CCITT、小端序辅助（新建）
- `maixsense_parser.h` / `maixsense_parser.cpp` — MaixSense 帧解析器，处理噪声/分块/坏尾/异常长度（新建）
- `device_config.h` / `device_config.cpp` — NVS 配置读写、room/bed/topic 规范化、网络就绪检查（新建）
- `mqtt_payload.h` / `mqtt_payload.cpp` — payload_b64 JSON 构造、MQTT publish 封装（新建）
- `main.cpp` — 模块化重构，新增 Wi-Fi STA 初始化、MQTT 客户端初始化（stub）、USB CDC + MQTT 双路回传
- `CMakeLists.txt` — 添加新源文件和 esp_wifi/esp_netif/esp_event/lwip/mbedtls 依赖
- `idf_component.yml` — 更新依赖说明，记录 MQTT 组件当前不可用原因

## 架构调整与模块设计

本次修复遵循项目已有的模块拆分原则，每个文件只负责一个明确领域：

- `auth.py` — 管理员账户与会话认证（不扩大）
- `db.py` — SQLite 连接、建表、迁移（新增迁移逻辑）
- `care_events.py` — 护理事件 CRUD（独立模块，不扩大 subjects.py）
- `subjects.py` — 人员/床位/凭据/身份/会话（仅修复过期检查）
- `sensor_store.py` / `esp_store.py` — 传感器与 ESP 数据缓存（未修改）
- `sleep_importer.py` — 睡眠 CSV 导入与归属策略（修复 first policy）
- `gateway.py` — 仅保留 HTTP 路由 glue 代码

ESP32 固件拆分为独立模块：protocol_packet（协议常量/CRC）、maixsense_parser（帧解析）、device_config（NVS 配置）、mqtt_payload（MQTT JSON 构造）。main.cpp 只保留 ESP-IDF 初始化、任务创建和硬件调用。

## 安全边界及鉴权设计

- **管理员密码**：始终使用 PBKDF2-HMAC-SHA256 加盐哈希（200,000 轮）。修复前首次创建时存储明文。
- **Cookie 会话**：只存随机 token（secrets.token_urlsafe），数据库存 SHA-256(token hash)。修复前 get_admin_http_session 忽略传入 token，返回任意活跃 session。
- **管理 API 鉴权**：区分本地服务 API（/api/v2/*, /api/esp/*, /api/v3/context/chat, /api/v3/identity/gallery, /api/v3/identity/match, /api/v3/vision/observation）和管理 API（/api/v3/subjects, /api/v3/beds, /api/v3/care/events 等）。本地服务 API 允许本机无 cookie 访问；管理 API 始终需要有效管理员 cookie，即使来自 localhost。
- **Session 认证**：收紧 session_is_authenticated，仅 identity_state 为 "recognized" 或 "candidate" 且 assurance_level 非空非 "none" 的 session 才视为已认证。修复前 identity_state="unknown" 也被视为已认证。
- **Session 过期**：get_session 现在检查 expires_ts >= 当前时间，过期 session 返回 None。修复前不检查过期。
- **Context 权限**：build_chat_context_v3 未授权时不返回任何患者数据（sleep、vitals、posture、memory、care_events 均为空）。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行带 room/bed：写入对应床位（大小写不敏感匹配已配置床位）
- 行不带 room/bed：
  - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 设置时：写入指定床位
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）：写入 beds[0]（修复前错误地写入 beds[-1]）
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip`：跳过
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all`：写入所有床位（仅显式调试模式）
- 同一 CSV 内可同时出现显式行和无归属行，策略只作用于无归属行，不误改或丢弃显式行

## care_event 实现细节

- **Schema**：event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts
- **路由**：
  - `POST /api/v3/care/events` — 创建事件（需要管理员鉴权）
  - `GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=...` — 查询事件（支持过滤、limit 默认 20、按 ts/created_ts 倒序）
- **Room/Bed 规范化**：创建和查询时均 uppercase（r1203/b1 → R1203/B1）
- **Context 集成**：chat context v3 授权通过时，modalities.care_events 返回最近 5 条事件摘要
- **Legacy DB 迁移**：db.py 和 care_events.py 都包含 _migrate_missing_columns 逻辑，旧表缺列时自动补齐并保留旧数据

## ESP32-S3 固件接口对齐说明

### Wi-Fi STA 初始化
- 使用 esp_wifi + esp_netif + esp_event 标准 IDF API
- 从 NVS 读取 ssid/password，WPA2-PSK 认证
- 连接失败最多重试 5 次，获取 IP 后触发 MQTT 初始化

### MQTT 巴法云回传
- 使用巴法云契约：`mqtt://{bemfa_host}:{port}`，username 为 bemfa_uid
- Topic 规范化：`{room}{bed}{stream}` 全小写（如 r1203b1tof1, r1203b1mlx2）
- JSON 格式：`{"payload_b64":"<base64 raw payload>"}`
- base64 内容是传感器原始 payload，不是完整 USB packet
- ToF 和 MLX 发送路径在保留 USB CDC 输出的同时，向对应 MQTT topic 发布原始 payload

### 当前状态（IDF v6.0.1 限制）
ESP-IDF v6.0.1 已将 MQTT 客户端从内置组件移至外部组件管理，但 `espressif/mqtt` 和 `espressif/esp_mqtt` 在当前组件注册表中均未找到可用版本。因此：
- Wi-Fi STA 已完整实现并可编译链接
- MQTT publish 路径使用 stub 实现（日志警告并返回 -1）
- 所有 MQTT 相关代码已完整编写，一旦组件可用，只需在 CMakeLists.txt REQUIRES 添加 `mqtt` 并恢复 mqtt_init_client 中的真实初始化代码即可启用

### NVS 配置
- 支持命令：CFGSET ssid/password/uid/host/port/room/bed/device_id, CFG?, CFGRESET, REBOOT
- dc_network_ready() 检查 ssid + password + uid + room + bed 全部非空
- dc_minimal_ready() 仅检查 room + bed（USB-only 模式）

### USB Packet 契约
- 包头：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H]`
- TYPE=0x01：MLX90640，TYPE=0x02：MaixSense ToF
- CRC16-CCITT：初始值 0xFFFF，多项式 0x1021，只覆盖 payload
- LEN 和 CRC 均为小端序
- ToF payload 保持完整 MaixSense 原始帧：`[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`

### 工程整理
- `protocol_packet.{h,cpp}`：USB packet 常量、sensor type/id、CRC16-CCITT、打包/校验辅助
- `maixsense_parser.{h,cpp}`：MaixSense 字节流解析器，能处理噪声、分块、坏尾字节、异常长度和半帧
- `device_config.{h,cpp}`：NVS key、room/bed 配置完整性、topic 规范化
- `mqtt_payload.{h,cpp}`：payload_b64 JSON 构造和 topic 选择
- `main.cpp`：保留 ESP-IDF 初始化、任务创建、硬件调用和模块 glue

## 本地测试与编译验证结果

### 修复后 run_public_tests.py
```
[public] all public tests passed
```
7/7 测试通过。

### 修复后 run_debug_probe.py
```
[probe:ok] admin setup returns 200
[probe:ok] management API rejects missing cookie
[probe:ok] management API rejects forged cookie
[probe:ok] management API accepts valid cookie
[probe:ok] unknown identity session is denied
[probe:ok] expired session is denied
[probe:ok] care_event write rejects missing admin cookie
[probe:ok] care_event normalizes room/bed for create and query
[probe:Warning] Voice/assistant path warning (信息性，非失败)
[probe] all visible diagnostic checks passed
```
8/8 诊断检查通过。

### ESP-IDF 编译
```
命令: python tools/run_espidf_build.py project2_task
目标: esp32s3 (Windows EIM ESP-IDF v6.0.1)
结果: Build finished successfully
输出: stdpro.bin binary size 0xd2490 bytes (860KB)
分区: Smallest app partition is 0x100000 bytes. 0x2db70 bytes (18%) free.
```

## 未验证的残留技术债与风险

- **MQTT 实际连通性**：固件编译通过但 MQTT publish 为 stub（IDF v6.0.1 组件注册表无可用 MQTT 组件）。Wi-Fi STA 初始化代码完整，待 MQTT 组件可用后即可启用。启用方式：在 CMakeLists.txt REQUIRES 添加 `mqtt`，恢复 mqtt_init_client 中的 esp_mqtt_client_init 调用。
- **Voice 助手 session 路径**：debug probe 打印了 Warning，提示收紧权限后如果本地助手仍依赖隐式 ambient session 可能同步失败。voice_assistant_integrated.py 不在本次修改范围内，建议后续确认 voice 模块在请求 /api/v3/context/chat 时先通过 /api/v3/session/current 获取有效 session_id。
- **真实硬件验证**：未进行 idf.py flash/monitor、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序或 MLX90640 实机读数验证（按任务要求不要求实机测试）。
- **SQLite 旧库迁移**：迁移逻辑已编写（_migrate_missing_columns），但未使用 data/legacy_sample.db 实际验证（按任务要求使用临时库测试）。
- **ESP-IDF sdkconfig.defaults 警告**：两个 kconfig symbol 已在 IDF v6.0.1 中更名（CONFIG_ESP32S3_SPIRAM_SUPPORT → CONFIG_SPIRAM, CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240 → CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240），不影响编译但建议后续更新。
