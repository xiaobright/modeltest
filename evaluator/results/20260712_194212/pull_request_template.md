# Project2 提测说明

## 初始自检诊断

修改前执行了 `python tests\run_public_tests.py project2_task` 和 `python tools\run_debug_probe.py project2_task`。

- 公开测试全部通过。
- 探针发现 6 项问题：缺少 Cookie 和伪造 Cookie 仍可读取 `/api/v3/subjects`；`identity_state=unknown` 与过期 session 仍获 v3 context；`POST /api/v3/care/events` 未接线且未拒绝未登录写入；护理事件 room/bed 写入查询未规范化。
- 探针额外提示 voice 需要避免通过 ambient/current session 读取敏感 context。

## 修改的文件列表

- `gateway/auth.py`、`gateway/gateway.py`、`gateway/db.py`、`gateway/care_events.py`、`gateway/sleep_importer.py`
- `voice/voice_assistant_integrated.py`
- `esp32/testpro4/main/main.cpp`、`main/CMakeLists.txt`、`main/idf_component.yml`
- 新增 `main/protocol_packet.*`、`main/maixsense_parser.*`、`main/device_config.*`、`main/mqtt_payload.*`
- `README.md`、`gateway/README.md`、`esp32/testpro4/README.md`、`RK3588_TEST_GUIDE.md`

## 架构调整与模块设计

HTTP 路由仍在 `gateway.py`，管理员账号与 HTTP 会话逻辑集中在 `auth.py`，护理事件读写和摘要集中在 `care_events.py`，数据库迁移留在 `db.py`。v3 context 只调用护理事件摘要，不直接拼接 SQL。

ESP32 主程序只保留硬件初始化、USB glue 和任务创建。CRC/包常量位于 `protocol_packet`，MaixSense 流解析位于 `maixsense_parser`，NVS 配置完整性和 topic 前缀规范化位于 `device_config`，Wi-Fi STA、MQTT 和 Base64 JSON 位于 `mqtt_payload`。

## 安全边界及鉴权设计

管理员密码使用随机 salt 的 PBKDF2-HMAC-SHA256 保存，登录使用 constant-time 比较。浏览器 Cookie 仅保存随机 token，SQLite 仅保存 token hash；会话查询按该 token hash 精确匹配，不能再回退到任一活跃管理员会话。

本机来源不再自动拥有管理权限，只有明确列出的 v2、ESP、视觉和 v3 worker 服务接口可走本机例外。人员、绑定、凭据、session 管理和护理事件写入必须有有效管理员 Cookie。v3 chat 不再使用最近的 ambient session，缺少 `session_id`、未知身份、无 assurance、过期 session 或缺少 actor subject 时均拒绝患者数据。voice 在未配置 `VOICE_SESSION_ID` 时先请求本机 current-session，再把取得的 ID 显式传入 context 请求。

## 睡眠 CSV 无 room/bed 时的特殊处理

导入按行处理。显式 room/bed 行只写入该床位；无归属行优先用 `SLEEP_IMPORT_DEFAULT_ROOM/BED`，否则 `first` 只写入第一个配置床位，`skip` 跳过，`all` 仅在显式调试设置时使用。修复了 `first` 错写最后一个床位的问题，因此混合 CSV 不会误改显式行。

## care_event 实现细节

新增 `POST /api/v3/care/events` 与 `GET /api/v3/care/events`。写入要求管理员并记录管理员 subject 为 `created_by`；事件校验必要字段和 severity，room/bed 在写入及查询时规范化。查询支持 `subject_id`、`room`、`bed`、`limit`，以 `ts/created_ts` 倒序返回。管理员或持有显式授权 session 的 actor 才能读取目标患者事件。

初始化会在历史 `care_events` 表缺少 `severity`、`source`、`created_by`、`ts` 时执行 `ALTER TABLE`，并以现有 `created_ts` 回填 ts，不删除旧行。授权 context 将最近事件放进 `modalities.care_events`。

## ESP32-S3 固件接口对齐说明

固件从 NVS 读取并校验 `ssid/password/uid/room/bed`；缺失时保留 USB CDC，禁用 MQTT。配置完整时启动 Wi-Fi STA 和巴法云 MQTT（默认 `bemfa.com:9501`），topic 按净化后的小写 `{room}{bed}tof1/tof2/mlx1/mlx2` 生成。ToF 和 MLX 都保留 USB 包 `[AA 55][TYPE][ID][LEN_LE][payload][CRC_LE]`，CRC16-CCITT 仅覆盖 payload。

MQTT 发布为 `{"payload_b64":"..."}`，Base64 编码的是原始 ToF 完整 MaixSense 帧或 MLX 原始 float payload，不是 USB 包；编码缓冲按输入大小动态分配，避免大 ToF 帧固定缓冲溢出。CMake/manifest 已加入 Wi-Fi、netif、event、lwip、mbedtls 和 ESP MQTT 组件依赖。

## 本地测试与编译验证结果

- 修改后再次执行 `python tests\run_public_tests.py project2_task`：全部公开测试通过。
- 修改后再次执行 `python tools\run_debug_probe.py project2_task`：全部可见诊断通过，包括伪造 Cookie 拒绝、unknown/expired session 拒绝、护理事件鉴权与 room/bed 规范化。
- 执行了多次 `python tools\run_espidf_build.py project2_task`，使用 Windows EIM ESP-IDF v6.0.1 与 `esp32s3`。可见日志确认 `protocol_packet.cpp`、`device_config.cpp`、`maixsense_parser.cpp`、`mqtt_payload.cpp` 和 `main.cpp` 都完成编译，并链接 `esp-idf/main/libmain.a`。Codex 终端在后续链接阶段截断，未返回脚本的 `Build finished successfully` 或明确 `ERROR` 终态，不能声称完整固件编译已通过。

## 未验证的残留技术债与风险

- ESP-IDF 完整应用链接终态需要在常规 PowerShell 终端复跑并确认脚本最终成功标记；现有可见日志没有报出新增源码的编译错误。
- 未进行 flash、USB 枚举、真实 ToF/MLX 读数、Wi-Fi 接入或巴法云 MQTT 实机测试。
- MQTT 当前按 NVS UID 作为用户名；需结合实际巴法云账号策略完成一次实机连接验证。
- 未用生产历史数据库直接演练迁移，只实现了保留行的增量列迁移；提测前应在其副本上演练并备份。
