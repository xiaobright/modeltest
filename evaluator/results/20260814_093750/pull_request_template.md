# Pull Request 提测说明 (Pull Request Template)

本项目（Project2）已完成本地护理/睡眠联调网关、权限隔离、数据迁移、护理事件（care_event）全链路以及 ESP32-S3（`esp32/testpro4`）双路 ToF+双路 MLX90640 传感器固件的模块化与 Wi-Fi/MQTT 双通道上报修复。

---

## 初始自检诊断

在修改代码前，执行了公共测试套件与诊断探针工具：

1. `python tests\run_public_tests.py project2_task`
   - 基础冒烟测试通过（4 项测试均 ok）。
2. `python tools\run_debug_probe.py project2_task`
   - 发现 6 处关键阻断与缺陷（Probe Failures）：
     1. `management API rejects missing cookie`：未认证访问 `/api/v3/subjects` 返回 200 而非 401（原因是 `_authorized_for_api` 对所有本机请求放行，未检查本地服务白名单）。
     2. `management API rejects forged cookie`：伪造 Cookie Token 访问返回 200 而非 401（原因是 `get_admin_http_session` 未按 `token_hash` 严格校验 session，而是直接获取活跃会话）。
     3. `unknown identity session is denied`：未识别身份会话（identity_state 为 `unknown`）未被拒绝（`session_is_authenticated` 错误跳过了认证状态检查）。
     4. `expired session is denied`：已过期会话未被拒绝（`session_is_authenticated` 缺少 `expires_ts` 过期时间校验）。
     5. `care_event write rejects missing admin cookie`：返回 404（缺少 `/api/v3/care/events` API 路由与鉴权绑定）。
     6. `care_event normalizes room/bed for create and query`：`care_events` 模块未完整实现房床归一化、字段录入与查询过滤。

---

## 修改的文件列表

### Gateway / 后端 Python 模块
- `project2_task/gateway/auth.py`：修复 PBKDF2 HMAC-SHA256 随机加盐哈希；修复 `admin_account_exists` 真实数据库查询；修复 `get_admin_http_session` 和 `delete_admin_http_session` 严格按 `token_hash` 查库与过期校验。
- `project2_task/gateway/db.py`：完善 `care_events` 表结构（增加 `severity`, `source`, `created_by`, `ts` 字段）；新增 `migrate_db_schema()` 保证兼容历史缺失列的 SQLite 数据库平滑迁移并回填时间戳。
- `project2_task/gateway/care_events.py`：实现 `create_care_event`、`list_care_events`、`build_care_events_context`，实现 room/bed 大小写及空格归一化、多维度查询过滤与摘要生成。
- `project2_task/gateway/gateway.py`：
  - 修复 `_authorized_for_api` 与 `_path_allows_local_service`，远程访问必须持有合法 Admin Cookie，本机请求仅白名单路径（如语音上下文、视觉观察等）允许服务间访问。
  - 修复 `actor_can_access_target` 和 `session_is_authenticated`，防止未知身份、过期会话或跨患者越权获取敏感体征/睡眠数据。
  - 接入 `care_events` 模块，注册 `GET/POST /api/v3/care/events` 接口，并在 `build_chat_context_v3` 挂载 `modalities.care_events` 与 allowed_sections。
- `project2_task/gateway/sleep_importer.py`：修复 `row_targets()` 中 `first` 策略取床位首项（`beds[0]`）而非末项，统一 room/bed 归一化。
- `project2_task/voice/voice_assistant_integrated.py`：在未显式传递 `session_id` 时，自动调用网关 `/api/v3/session/current` 获取当前识别会话，避免在严格鉴权后语音助手降级或无法获取授权上下文。
- `project2_task/gateway/README.md`：同步更新模块职责目录与 `care_events` 架构说明。

### ESP32-S3 固件模块 (`esp32/testpro4`)
- `project2_task/esp32/testpro4/main/protocol_packet.h` & `protocol_packet.cpp`：抽离 USB CDC 封包协议常量（`0xAA 0x55`）、Sensor Type/ID、CRC16-CCITT（poly `0x1021`, init `0xFFFF`，仅覆盖 Payload，小端序）计算与打包/校验函数。
- `project2_task/esp32/testpro4/main/maixsense_parser.h` & `maixsense_parser.cpp`：独立封装 MaixSense 帧解析状态机，支持处理串口噪声、半帧、粘包、异常长度与坏尾字节。
- `project2_task/esp32/testpro4/main/device_config.h` & `device_config.cpp`：封装 NVS 配置管理（`wifi_ssid`、`wifi_pass`、`bemfa_uid`、`bemfa_host`、`bemfa_port`、`room`、`bed`、`device_id`）、串口配置命令行（`CFGSET` / `CFG?` / `CFGRESET` / `REBOOT`）以及规范化的 MQTT topic 生成（`{room}{bed}tof1/tof2/mlx1/mlx2` 全小写）。
- `project2_task/esp32/testpro4/main/mqtt_payload.h` & `mqtt_payload.cpp`：实现 Wi-Fi STA 网络初始化、事件监听、巴法云 MQTT 客户端连接，以及将原始 Payload 使用 mbedtls Base64 编码并组装为 `{"payload_b64":"..."}` 发送至对应 topic。
- `project2_task/esp32/testpro4/main/main.cpp`：精简主程序，保留外设初始化、FreeRTOS 任务调度与 Glue 逻辑；在 `usb_send_tof_payload` 和 `mlx_sender_task` 中实现 USB CDC 与 MQTT 并行双通道上报。
- `project2_task/esp32/testpro4/main/CMakeLists.txt`：注册新增源码文件，引入 `esp_wifi`、`esp_netif`、`esp_event`、`lwip`、`mqtt`、`mbedtls` 组件依赖。
- `project2_task/esp32/testpro4/main/idf_component.yml`：增加 `espressif/mqtt: "^1.0.0"` 依赖。

---

## 架构调整与模块设计

1. **关注点分离 (Separation of Concerns)**：
   - 将 `gateway.py` 内部耦合的安全鉴权、数据库迁移、护理事件处理下沉至独立子模块 `auth.py`、`db.py`、`care_events.py`。
   - ESP32-S3 固件从单文件 1100+ 行 `main.cpp` 拆分为 `protocol_packet`（协议层）、`maixsense_parser`（解析层）、`device_config`（配置层）、`mqtt_payload`（网络层）和 `main.cpp`（调度层）。
2. **数据流双通道架构**：
   - 固件端：USB CDC 有线通道保持最高实时性，MQTT Wi-Fi 无线通道并行发布 Base64 负载至巴法云。
   - 网关端：同时支持 Bemfa TCP/MQTT 订阅汇聚与 HTTP 本地/远程 API，统一归一化写入 SQLite 与缓存。

---

## 安全边界及鉴权设计

1. **密码安全与凭据隔离**：
   - 管理员密码采用 `PBKDF2-HMAC-SHA256` 算法，单向哈希并带有 16 字节随机 salt（200,000 次迭代），杜绝明文与弱哈希。
   - 浏览器端仅下发高熵 32 字节随机 Hex Token（`HttpOnly; SameSite=Lax` Cookie），网关内存与数据库仅存储 `token_hash`（SHA-256），防范 Token 碰撞与泄露。
2. **网络边界与最小特权**：
   - 所有 `/admin`、`/dashboard` 以及涉及人员、排班、凭据、护理事件等管理 API 必须持有有效管理员 Cookie。
   - 本机服务请求（如 Loopback IP）仅开放特定的内部服务白名单（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`）。
3. **上下文零泄漏 (Zero Data Leakage Context Policy)**：
   - 会话有效性：严格检查 `session.actor_subject_id` 存在、未过期（`expires_ts >= now_ms`）、`identity_state != 'unknown'` 且 `assurance_level != 'none'`。
   - 目标访问控制：`admin`/`staff` 角色允许查看床位/患者全部体征；`patient` 角色仅允许查看自身分配的床位；未认证或越权访问时，`sleep`、`vitals`、`posture`、`memory`、`care_events` 全部裁剪为空结构，`policy.allowed` 设为 `False`。

---

## 睡眠 CSV 无 room/bed 时的特殊处理

在 `gateway/sleep_importer.py` 中：
1. 每一行 CSV 数据独立解析 `room` 与 `bed`。
2. 若行中显式包含 `room` 与 `bed`，归一化后匹配配置床位。
3. 若行中缺少房床信息：
   - 优先检查 `SLEEP_IMPORT_DEFAULT_ROOM` 与 `SLEEP_IMPORT_DEFAULT_BED` 环境变量配置。
   - `SLEEP_IMPORT_UNSCOPED_POLICY == 'first'`：默认且安全策略，仅归属到首个配置床位（`beds[0]`），防止数据向所有床位盲目广播污染。
   - `SLEEP_IMPORT_UNSCOPED_POLICY == 'skip'`：跳过无归属的记录。
   - `SLEEP_IMPORT_UNSCOPED_POLICY == 'all'`：仅在明确指定时广播至所有床位。

---

## care_event 实现细节

1. **数据模型与持久化**：
   - 数据库表：`care_events(event_id, subject_id, room, bed, event_type, note, severity, source, created_by, ts, created_ts)`。
   - 字段约束：`severity` 限制为 `info`/`warning`/`critical`；`room`/`bed` 自动执行 `normalize_room`/`normalize_bed`；时间戳支持输入毫秒级 `ts` 并自动维护 `created_ts`。
2. **API 端点**：
   - `POST /api/v3/care/events`：需管理员权限，创建护理事件，返回新增记录。
   - `GET /api/v3/care/events`：需管理员权限，支持 `subject_id`、`room`、`bed`、`limit` 复合过滤，按时间倒序排列。
3. **对话上下文集成**：
   - 在 `build_chat_context_v3` 中，当授权判定 `allowed=True` 时，获取目标床位最近护理事件并生成摘要挂载在 `modalities.care_events` 与 `prompt_hints` 中，供语音/大模型自然结合巡房与用药提醒。

---

## ESP32-S3 固件接口对齐说明

1. **USB CDC 协议契约**：
   - 格式：`[AA 55] [TYPE: 0x01=MLX, 0x02=ToF] [ID: 0x01/0x02] [LEN_L LEN_H] [PAYLOAD...] [CRC_L CRC_H]`。
   - CRC16-CCITT 仅覆盖 Payload（小端存储）。
   - ToF 保持完整 MaixSense 原始帧（~10022 字节）。
2. **巴法云 MQTT 契约**：
   - Broker 默认 `bemfa.com:9501`，Client ID 填入 NVS 中的 `bemfa_uid`。
   - Topic：`{room}{bed}tof1`、`{room}{bed}tof2`、`{room}{bed}mlx1`、`{room}{bed}mlx2`（必须全部转为小写）。
   - Payload JSON：`{"payload_b64":"<Base64(RawPayload)>"}`。

---

## 本地测试与编译验证结果

1. **公共测试套件**：
   - 命令：`python tests\run_public_tests.py project2_task`
   - 结果：`ALL 4 TEST SUITES PASSED`（`test_compile.py`、`test_functional_smoke.py`、`test_refactored_features.py`、`test_smoke_gateway.py` 均执行成功）。
2. **诊断探针自检**：
   - 命令：`python tools\run_debug_probe.py project2_task`
   - 结果：`[probe] all visible diagnostic checks passed`（所有 8 项探测全部 PASS，0 项失败）。
3. **ESP-IDF 固件编译**：
   - 命令：`python tools\run_espidf_build.py project2_task --clean-copy`
   - 环境：ESP-IDF v6.0.1 (Windows native toolchain, target `esp32s3`)
   - 结果：`Build finished successfully. output_bin = ...\stdpro.bin`（编译 1099 个编译单元 0 警告 0 错误，生成 `stdpro.bin` 大小 0xefde0 字节）。

---

## 未验证的残留技术债与风险

1. **真实硬件 UART 信号抖动**：
   - 在真实物理板卡上，若 ToF 传感器上电瞬间波特率处于不确定状态，已通过冷启动延时（2000ms）和自动波特率探测（115200 / 921600）与重试逻辑进行容错，但极端供电不稳时建议观察串口 `ToF Status` 日志。
2. **Wi-Fi 弱网与 MQTT 重连压力**：
   - 双路 ToF 在 8FPS 满速下产生的数据量较大（Base64 约 13.3KB/帧），在 Wi-Fi 信道拥塞或弱信号环境下可能会触发 TCP 缓冲区丢包；已通过互斥锁与非阻塞队列做了一定限流保护，建议在生产环境中根据网络带宽合理调优 ToF FPS（如 4~8 FPS）。
3. **历史 SQLite 数据库跨大版本升级**：
   - `migrate_db_schema` 已自动对 `care_events` 添加缺少的列，若未来涉及主键变更或更复杂的表级重构，需配合专用迁移脚本处理。
