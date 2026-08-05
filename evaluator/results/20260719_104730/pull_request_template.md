# Project2 提测说明

## 初始自检诊断

修改前已运行 `python tests\run_public_tests.py project2_task`，4 个公开测试脚本全部通过。随后运行 `python tools\run_debug_probe.py project2_task`，诊断出 6 项失败：缺失 Cookie 和伪造 Cookie 均可访问管理 API；`identity_state=unknown` 和已过期 session 被错误授权；护理事件 POST 路由缺失；护理事件 create/query 的 room/bed 大小写不一致。

该探针还提示 voice 未显式获取 session，收紧 context 后可能依赖 ambient/current session 而导致联调失败。

## 修改的文件列表

- `gateway/auth.py`：管理员账户存在性、PBKDF2-SHA256 加盐哈希、旧明文密码一次性登录迁移，以及 token-hash 精确查询。
- `gateway/db.py`、`gateway/care_events.py`：护理事件 schema 迁移、CRUD、规范化与 context 摘要。
- `gateway/gateway.py`：本机服务例外收窄、session 认证校验、care event 路由和 context 聚合。
- `gateway/sleep_importer.py`：修正 `first` 为第一个配置床位，且仍按行处理显式 room/bed。
- `voice/voice_assistant_integrated.py`：先读取 current session，再显式携带 session_id 请求 v3 context。
- `esp32/testpro4/main/{main.cpp,protocol_packet.*,device_config.*,mqtt_payload.*,CMakeLists.txt,idf_component.yml}`：Wi-Fi STA、MQTT、Base64 payload、NVS 校验与组件依赖。
- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`esp32/testpro4/{README.md,QUICKSTART.md}`：同步接口、鉴权、导入和固件说明。

## 架构调整与模块设计

HTTP 路由仍在 `gateway.py`，护理事件持久化和摘要保持在 `care_events.py`。数据库初始化使用 `PRAGMA table_info` 进行增量列迁移，避免以重建表的方式丢失历史记录。固件将 CRC/USB 常量拆到 `protocol_packet`，NVS 完整性与 topic 拼接拆到 `device_config`，Wi-Fi/MQTT/Base64 发布放到 `mqtt_payload`，`main.cpp` 保留初始化和任务 glue。

## 安全边界及鉴权设计

管理员密码以 PBKDF2-SHA256（200,000 轮、随机 salt）保存；Cookie 仅包含随机 token，SQLite 仅保存 SHA-256 token hash。认证查询必须匹配提交 token 的 hash，不能选择任意有效会话。受影响的旧明文管理员条目只会在正确登录后就地换成 hash。

管理 API 不再因 loopback 地址自动放行；本机例外仅保留给规定的 v2/ESP worker、vision/identity 和 v3 context/current-session 服务路径。v3 context 需要 actor subject、`identity_state=recognized`、非 none assurance 和未过期 session；拒绝时不返回患者、床位绑定、记忆、护理事件或其他患者模态。voice 显式获取并传递 session_id，不依赖隐式 ambient session。

## 睡眠 CSV 无 room/bed 时的特殊处理

每行独立判定：带 room/bed 的行写入其自身规范化床位；无 room/bed 的行先使用 `SLEEP_IMPORT_DEFAULT_ROOM/BED`，否则按 `SLEEP_IMPORT_UNSCOPED_POLICY` 处理。`first` 使用第一个配置床位，`skip` 丢弃无归属行，`all` 仅在显式调试配置下生效；显式床位行不会被无归属策略覆盖。

## care_event 实现细节

实现 `POST /api/v3/care/events` 和 `GET /api/v3/care/events`，两者走管理员鉴权。事件保存 `severity/source/created_by/ts`，room/bed 统一大写，查询按 `ts, created_ts` 倒序并限制最大 100 条。旧数据库缺少这四列时原表原数据保留并补默认值，`ts` 回填为 `created_ts`。授权 context 返回最近事件摘要到 `modalities.care_events`；未授权返回空结构。

## ESP32-S3 固件接口对齐说明

`testpro4` 从 NVS 读取 `wifi_ssid/wifi_pass/bemfa_uid/room/bed` 并要求其完整后才启动网络，host/port 保持 `bemfa.com:9501` 默认值。topic 使用小写 `{room}{bed}tof1/tof2/mlx1/mlx2`。Wi-Fi STA 与 MQTT client 并行于 USB CDC 工作，断线时 Wi-Fi 重连。

MQTT 消息固定为 `{"payload_b64":"..."}`。Base64 输入是 MLX 的 3072-byte 原始温度 payload 或完整 MaixSense 原始帧，不含 USB 的 `AA 55` header/CRC。编码和 JSON 缓冲按实际 payload 长度动态分配。USB 保持 `[AA 55][TYPE][ID][LEN_LE][PAYLOAD][CRC16-CCITT_LE]`，CRC 仅覆盖 payload。

## 本地测试与编译验证结果

- 初始：`python tests\run_public_tests.py project2_task` 通过；`python tools\run_debug_probe.py project2_task` 失败 6 项，详见初始诊断。
- 修复后：`python -m py_compile` 覆盖修改的 gateway 与 voice Python 模块，通过。
- 修复后：`python tests\run_public_tests.py project2_task` 通过，全部公开测试成功。
- 修复后：`python tools\run_debug_probe.py project2_task` 通过，所有可见诊断检查成功，voice 路径识别到 current-session 获取。
- 固件：`python tools\run_espidf_build.py project2_task` 在 Windows EIM ESP-IDF v6.0.1 成功；输出 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`。应用大小 `0xeff50`，最小 app 分区剩余 `0x100b0`。

## 未验证的残留技术债与风险

未执行 flash/monitor，也未连接真实 Wi-Fi、巴法云 MQTT、USB CDC、MaixSense 或 MLX90640 硬件，因此真实网络认证、Broker 限制、断线重连节奏和传感器吞吐仍需在板端验证。构建阶段的既有 `sdkconfig.defaults` 产生 unknown-symbol/迁移提示，但不阻塞 ESP-IDF v6.0.1 成功构建；本次未扩展处理该历史配置噪声。旧明文管理员密码仅在该管理员下一次正确登录时升级，无法在不知道原密码的情况下安全地预先替换。
