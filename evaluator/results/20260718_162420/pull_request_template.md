# Pull Request 提测说明

## 初始自检诊断

修改前在 workspace 根目录运行：

- `python tests\run_public_tests.py project2_task`
  - 结果：公共测试全部通过。
  - 诊断输出同时显示 `SLEEP_IMPORT_UNSCOPED_POLICY=first` 实际导入到 `R1203-B2`，暴露出“首床取成最后一床”的未覆盖回归。
- `python tools\run_debug_probe.py project2_task`
  - 结果：退出码 1，共 6 项失败。
  - 缺少 Cookie 和伪造 Cookie 均可访问 `/api/v3/subjects`。
  - `identity_state=unknown` 和已过期 session 仍被允许读取患者 context。
  - `/api/v3/care/events` 未接路由，未登录写入返回 404 而不是 401。
  - care event 写入未规范化 room/bed，`r1203/b1` 无法通过 `R1203/B1` 查询。
  - probe 另有 voice 警告：收紧 context 后，如果仍依赖 ambient session，助手可能失去上下文或继续使用旧身份。

## 修改的文件列表

- Gateway 与 voice：
  - `gateway/db.py`
  - `gateway/auth.py`
  - `gateway/subjects.py`
  - `gateway/care_events.py`
  - `gateway/sleep_importer.py`
  - `gateway/gateway.py`
  - `voice/voice_assistant_integrated.py`
- ESP32-S3：
  - `esp32/testpro4/main/main.cpp`
  - `esp32/testpro4/main/protocol_packet.{h,cpp}`
  - `esp32/testpro4/main/maixsense_parser.{h,cpp}`
  - `esp32/testpro4/main/device_config.{h,cpp}`
  - `esp32/testpro4/main/mqtt_payload.{h,cpp}`
  - `esp32/testpro4/main/CMakeLists.txt`
  - `esp32/testpro4/main/idf_component.yml`
  - `esp32/testpro4/sdkconfig.defaults`
- 文档：
  - `README.md`
  - `gateway/README.md`
  - `RK3588_TEST_GUIDE.md`
  - `esp32/NVS_CONFIG.md`
  - `esp32/testpro4/README.md`
  - `esp32/testpro4/QUICKSTART.md`
  - `esp32/testpro4/docs/protocol.md`
  - `PULL_REQUEST_TEMPLATE.md`

## 架构调整与模块设计

- 保持 `gateway.py` 只承担 HTTP 路由和聚合 glue；care event CRUD/context 位于 `care_events.py`，迁移位于 `db.py`。
- SQLite 初始化改为“建基础表 -> 检查 `PRAGMA table_info` -> `ALTER TABLE ADD COLUMN` -> 回填旧数据 -> 建索引”，避免 `CREATE TABLE IF NOT EXISTS` 无法升级旧库。
- SQLite 连接上下文退出时会提交/回滚并关闭，减少 Windows 临时测试库锁文件。
- ESP 固件将纯逻辑拆为 USB packet/CRC、MaixSense parser、NVS config/topic、MQTT base64 JSON 四个模块；`main.cpp` 保留硬件任务、TinyUSB、Wi-Fi 和 MQTT 生命周期。

## 安全边界及鉴权设计

- 管理员密码使用随机 16-byte salt 和 PBKDF2-HMAC-SHA256 200,000 次迭代保存；旧分支中 `salt=''` 的明文记录会在初始化时原地升级为哈希。
- Cookie 仅保存 `secrets.token_urlsafe(32)` 随机 token；SQLite 仅保存 SHA-256 token hash。会话查询必须精确匹配 token hash，并检查账号状态和过期时间。
- 管理 API 不再因为请求来自 loopback 自动放行。本机无 Cookie 例外仅限 v2、ESP、identity、vision、`session/current` 和 context 等 worker 路径。
- `/api/v3/context/chat` 不再静默读取最近 session，必须显式提供 `session_id`。session 必须有 actor、`identity_state=recognized`、非 `none` assurance 且未过期。
- staff/admin 可访问目标患者；patient 只能访问自己。目标 subject 与 room/bed assignment 不一致时拒绝。
- 未认证响应清空 target patient/assignment、memory、care events 和其它患者 modalities；无效会话本身也不回传。
- voice 未配置固定 `VOICE_SESSION_ID` 时，先从本机 `/api/v3/session/current` 获取绝对最新会话；若最新会话是 unknown/no-gallery/disabled/match-error，则返回空，不会越过它复用旧 recognized session。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 每行独立判断，不再按整文件统一处理。
- 显式 `room/bed` 行规范化后只进入对应床位，即使同一 CSV 还包含无归属行也不会被策略覆盖。
- 无归属行优先使用 `SLEEP_IMPORT_DEFAULT_ROOM/BED`。
- `first` 使用 `beds[0]`；`skip` 跳过；`all` 仅在显式配置时广播。
- 默认值和显式值均统一规范化为大写 room/bed。

## care_event 实现细节

- `care_events` 新 schema 包含 `severity/source/created_by/ts`，旧表缺列时补列并以 `created_ts` 回填 `ts`，保留旧行。
- 新增并接通：
  - `POST /api/v3/care/events`
  - `GET /api/v3/care/events?subject_id=...`
  - `GET /api/v3/care/events?room=...&bed=...&limit=...`
- 直接读写需要管理员 Cookie；room/bed 写入和查询均规范化；结果按 `ts, created_ts` 倒序，limit 限制为 1-200。
- 授权通过的 v3 context 在 `modalities.care_events` 返回最近事件摘要；未授权时为空。

## ESP32-S3 固件接口对齐说明

- 从 NVS 读取并校验 `wifi_ssid/wifi_pass/bemfa_uid/room/bed`，默认 broker 为 `bemfa.com:9501`。
- 恢复 Wi-Fi STA、断线重连和 ESP-MQTT client；Client ID 使用巴法云 UID。
- topic 由规范化后的小写 `{room}{bed}` 加 `tof1/tof2/mlx1/mlx2` 拼接。
- MQTT 消息严格为 `{"payload_b64":"..."}`，base64 内容是原始传感器 payload，不包含 USB `AA 55` packet。
- MLX MQTT payload 为 3072-byte float32 数据；ToF MQTT/USB payload 保留完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`。
- USB packet 保持 `[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 仅覆盖 payload，LEN/CRC 均为小端序。
- MaixSense parser 可处理噪声、分块、半帧、异常长度、坏尾字节和缓冲溢出。
- 大 payload 的 base64 JSON 按实际长度动态分配，优先使用 PSRAM，避免固定小缓冲。
- CMake/manifest 已加入 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 和 `espressif/mqtt` 依赖。

## 本地测试与编译验证结果

- `python tests\run_public_tests.py project2_task`
  - 最终结果：退出码 0，4 个公共测试文件全部通过。
  - 一次中间并行验证曾因两个 Python 编译进程同时替换 `__pycache__` 在 Windows 上出现 `WinError 5`；改为规定的串行命令后稳定通过。
- `python tools\run_debug_probe.py project2_task`
  - 最终结果：退出码 0，全部 visible diagnostic checks passed。
  - 缺失/伪造 Cookie、unknown/expired session、care event 鉴权和 room/bed 规范化均通过。
- 临时库定向检查：
  - 旧 care event 缺列迁移及旧行保留通过。
  - 旧明文管理员口令升级、真实/伪 token 区分通过。
  - 授权 context 包含 care event、未授权零泄漏通过。
  - 最新 unknown 会话阻断旧 recognized ambient session 通过。
  - 混合 CSV 中显式 `R1203-B2` 行和无归属首床 `R1203-B1` 行分别落床通过。
- `python tools\run_espidf_build.py project2_task`
  - 第一次编译明确失败于 GCC `-Werror=format-truncation`，位置是 Wi-Fi SSID/password 的 `snprintf`；改为长度受控的定长拷贝。
  - 最终结果：退出码 0，Windows EIM ESP-IDF v6.0.1、target `esp32s3` 编译成功。
  - 产物：`stdpro.bin`，大小 `0xEF7D0`；最小 app 分区剩余 `0x10830`，约 6%。
  - 未执行 flash/monitor，符合本任务构建验证范围。

## 未验证的残留技术债与风险

- 未做 ESP32-S3 实机 flash/monitor、真实 USB CDC 枚举、真实 Wi-Fi/巴法云 MQTT 连通和断线恢复压力测试。
- 未验证双 ToF + 双 MLX 实际并发帧率下，约 13 KB MQTT JSON 的长期吞吐、巴法云限流和 PSRAM 碎片情况。
- 固件 app 分区只剩约 6%，后续增加 OTA、TLS 或更多诊断功能前需要评估分区表和固件体积。
- 未验证真实 MaixSense 上电时序、MLX90640 温度准确度、摄像头/人脸阈值、RK3588 ONNX/RKLLM 环境。
- ESP-IDF 配置报告仍显示 IDF v6.0.1 自带的 BT/FATFS 默认值通知，但不影响本次构建成功。
