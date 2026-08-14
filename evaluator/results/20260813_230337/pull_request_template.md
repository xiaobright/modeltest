# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前（进入代码修改之前）已按要求先运行：

- `../.venv/bin/python tests/run_public_tests.py project2_task`
- `../.venv/bin/python tools/run_debug_probe.py project2_task`

结果：

- 公开测试：4 个测试文件全部通过（compile / functional_smoke / refactored_features / smoke_gateway）。
- 调试探针：6 项失败，退出码为 1：
  1. `management API rejects missing cookie`：127.0.0.1 缺少 Cookie 访问 `/api/v3/subjects` 返回 200。
  2. `management API rejects forged cookie`：伪造 Cookie 仍返回 200。
  3. `unknown identity session is denied`：`identity_state=unknown` 的 session 仍获得 `allowed=true`。
  4. `expired session is denied`：已过期 session 仍获得 `allowed=true`。
  5. `care_event write rejects missing admin cookie`：`POST /api/v3/care/events` 返回 404 而非 401。
  6. `care_event normalizes room/bed for create and query`：care_event 创建/查询大小写规范化不完整。
- 另见探针 Warning：voice 助手依赖隐式 ambient/current session，收紧鉴权后可能拿不到上下文。

ESP-IDF 基线固件在修改前可编译，但 `main.cpp` 中 Wi-Fi + MQTT 回传仍是 TODO，CMake 也未声明 `mqtt/mbedtls` 等网络依赖。

## 修改的文件列表

核心 Python 代码：

- `gateway/auth.py`：管理员密码 PBKDF2-SHA256 加盐哈希；DB 只存随机 Cookie 的 token hash；修复 token 校验；支持旧明文密码记录首次登录时迁移。
- `gateway/db.py`：SQLite 初始化改为“建新表 + PRAGMA 检查 + 缺列 ALTER”，重点原地迁移旧 `care_events` 缺列并保留旧行。
- `gateway/care_events.py`：补齐 `severity/source/created_by/ts`、room/bed 规范化、limit 倒序查询、context 摘要；保留 `init_care_events_table` 兼容入口。
- `gateway/gateway.py`：管理 API 与 worker API 鉴权分流；新增 `POST/GET /api/v3/care/events`；v3 context 权限裁剪、显式 `session_id`、admin Cookie fallback、care_events modality。
- `gateway/sleep_importer.py`：无 `room/bed` 行按行执行 first/skip/all/default 策略，`first` 修正为 `beds[0]`，显式行不被整表策略误改。
- `gateway/esp_store.py`：`append_esp_packet` 统一累计 `bytes_rx`/`crc_fail`。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_gateway_session()`，先显式获取 `/api/v3/session/current`，再把 `session_id` 传给 `/api/v3/context/chat`。

ESP32-S3 固件：

- `esp32/testpro4/main/main.cpp`：改为模块 glue，恢复网络初始化调用，ToF/MLX USB 与 MQTT 并行发送。
- 新增 `main/protocol_packet.{h,cpp}`：USB packet 常量、CRC16-CCITT、小端包头/CRC 打包。
- 新增 `main/maixsense_parser.{h,cpp}`：完整 MaixSense 原始帧解析，处理噪声、分块、半帧、坏尾、异常长度。
- 新增 `main/device_config.{h,cpp}`：NVS 读取/写入/校验，支持 `ssid/password` 与 `wifi_ssid/wifi_pass` 等别名。
- 新增 `main/mqtt_payload.{h,cpp}`：`{room}{bed}{stream}` 小写 topic 和动态堆内存 `{"payload_b64":"..."}` 构造。
- 新增 `main/network_backhaul.{h,cpp}`：Wi-Fi STA、事件重连、Bemfa MQTT 客户端与发布路径。
- `esp32/testpro4/main/CMakeLists.txt`：登记新源文件并补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`。
- `esp32/testpro4/main/idf_component.yml`：增加 `espressif/mqtt`（本地组件仓库解析为 1.0.0）。

文档：

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`：补齐 care_event、显式 session、睡眠归属策略、MQTT 状态说明。
- `esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md`、`docs/protocol.md`：更新 ESP32 已恢复的 Wi-Fi/MQTT 实现和完整 ToF payload 契约。
- `CHANGES.md`：清除 ESP32 固件/CMake “待修复”描述。
- `PULL_REQUEST_TEMPLATE.md`：即本提测说明。

## 架构调整与模块设计

保持原有模块边界，`gateway.py` 只做路由 glue：

- 管理员密码与 HTTP 会话：`auth.py`。
- SQLite schema/迁移：`db.py`。
- 人员/床位/记忆/凭据/session：`subjects.py`。
- 护理事件 CRUD 与摘要：`care_events.py`。
- 睡眠 CSV 归属策略：`sleep_importer.py`。
- 传感器缓存和 ESP set 聚合：`sensor_store.py` / `esp_store.py`。
- v3 context 组装仍在 `gateway.py`，但依赖各模块函数完成裁剪，未塞回单文件。

ESP32 固件按交接要求拆成协议、解析器、NVS 配置、MQTT payload、网络回传 5 个独立文件，`main.cpp` 保留任务创建和硬件 glue。

## 安全边界及鉴权设计

- `/api/v3/admin/*` 只允许 setup/login/logout/auth 公开；其他 `/api/v3/*` 管理路由即使来自 127.0.0.1 也必须携带有效管理员 Cookie。
- 本机 worker 例外只保留：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`。
- 远程未登录不能访问管理 API；`credentials?include_template=1` 与 identity gallery 也受同一管理鉴权门控制。
- 管理员密码使用随机 16 字节 salt + PBKDF2-SHA256（200,000 次）保存；历史无 salt 明文记录在首次成功登录时立即重哈希，不再保留明文。
- HTTP Cookie 只写随机 token；数据库只写 `SHA-256(token)`；校验按 token hash 精确匹配，不再“取任意活跃会话”。`/api/v3/admin/auth` 不回传 `token_hash`。
- v3 session 必须满足：有 `actor_subject_id`、`identity_state` 非 unknown/空、`assurance_level` 非 none/空、`expires_ts` 未过期。
- `staff/admin` 可访问任意目标患者；`patient` 只能访问自己。
- v3 context 不再静默复用最近 ambient session；voice 助手显式获取当前 session 后携带 `session_id`。
- 有明确 room/bed 时，以该床位的 active assignment 作为授权目标；显式 `target_subject_id` 与床位归属冲突时不会让 patient 借自己的 subject id 读取别人床位。
- 未授权 context 返回空 `patient/assignment/modalities`，不返回记忆或护理事件内容。
- 管理员登录后的 `/admin` 页面通过已认证 admin Cookie 请求 context（非 ambient session），保持页面可用。

## 睡眠 CSV 无 room/bed 时的特殊处理

`SLEEP_IMPORT_DEFAULT_ROOM/BED` 与 `SLEEP_IMPORT_UNSCOPED_POLICY` 按行生效：

- 行内同时有 `room` 和 `bed`：只写该床位，并规范化为大写 `R1203/B1`。
- 行内缺 `room/bed`：
  - 设置默认房床：写指定床位；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）：写配置中的第一个床位；
  - `skip`：跳过该行；
  - `all`：仅显式调试模式，向所有床位广播，不会成为默认。
- 同一 CSV 内显式归属行和无归属行可混合；策略只作用于无归属行。

## care_event 实现细节

- 表字段：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`。
- 旧表原地迁移：缺 `severity/source/created_by/ts` 时 `ALTER TABLE ADD COLUMN`，并把旧行 `ts` 回填为 `created_ts`，旧数据不删除。
- 创建：room/bed 规范化，`severity` 默认 `info`、`source` 默认 `manual`，`event_id` 可自动生成。
- 查询：支持 `subject_id`、`room` + `bed`、`limit`（默认 20，最大 200），按 `ts, created_ts` 倒序。
- 路由：`POST /api/v3/care/events` 和 `GET /api/v3/care/events`，写接口需要管理员 Cookie；GET 查询同样受管理鉴权保护。
- 授权上下文：仅 `allowed=true` 时在 `modalities.care_events` 返回最近 5 条摘要；未授权时为空。

## ESP32-S3 固件接口对齐说明

- Wi-Fi：NVS 读取 `wifi_ssid/wifi_pass`（兼容 `ssid/password`）后初始化 STA，注册 `WIFI_EVENT` / `IP_EVENT` 事件，断线自动重连，获取 IP 后启动 MQTT。
- MQTT：`bemfa_host` 默认 `bemfa.com`、`bemfa_port` 默认 `9501`；ClientID 使用 `bemfa_uid`，用户名/密码为空，匹配巴法云契约。
- topic：读取并校验 `room/bed`，用规范化小写拼接 `{room}{bed}tof1/tof2/mlx1/mlx2`。
- payload：MQTT 发布 `{"payload_b64":"<base64 raw payload>"}`；ToF 是完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`，MLX 是 3072B float32 原始数组，都不是 USB packet。
- USB：保留 `[AA 55][TYPE][ID][LEN_L LEN_H][PAYLOAD][CRC_L CRC_H]`，`LEN`/CRC 小端，CRC16-CCITT 初始 `0xFFFF`、多项式 `0x1021`，仅覆盖 payload。
- 发送路径：`usb_send_tof_payload()` 在 USB CDC 输出后同步发布 MQTT；MLX 任务即使 CDC0 未连接也向 `mlx1/mlx2` 发布。
- 大 payload：base64/JSON 使用 `std::string` 和计算后容量动态分配，没有 256B 固定缓冲区。
- 配置完整性：`ssid/password/uid/room/bed/host/port` 缺失时保持 USB 采集可运行，Wi-Fi/MQTT 关闭并提示串口 `CFGSET + REBOOT`。

## 本地测试与编译验证结果

最终执行：

```bash
../.venv/bin/python tests/run_public_tests.py project2_task
../.venv/bin/python tools/run_debug_probe.py project2_task
../.venv/bin/python tools/run_espidf_linux_build.py project2_task
```

结果：

- 公开测试：4 个测试文件全部通过，退出码 0。
- 调试探针：全部 `probe:ok`，退出码 0；voice 路径已提示使用 current-session fetch。
- ESP-IDF v6.0 编译：成功，退出码 0。
  - 输出 `stdpro.bin`：`/home/xiaoming/.cache/modeltest/espidf/project2_task/esp32/testpro4/build/stdpro.bin`
  - 分区占用：`stdpro.bin 0xef6f0`，最小 app 分区 `0x100000`，剩余 6%。
  - 无新错误；仅有既有 warning：MLX 组件 type-limits、`uart_config_t.flags` missing initializer、两个历史 sdkconfig 未知 Kconfig 符号。
  - 未执行 `idf.py flash` 或 `idf.py monitor`。
- 过程记录：首次声明 `espressif/mqtt: ^1.3.0` 时本地 component registry 无匹配版本；改为 `espressif/mqtt: "*"` 后解析为 `espressif__mqtt 1.0.0` 并编译成功。此过程保留在构建日志中。

## 未验证的残留技术债与风险

- 未做真实硬件验证：Wi-Fi 连接、巴法云 MQTT 实连、USB CDC 枚举、ToF 上电时序/AT 命令、MLX90640 I2C 读数均未在实机测试。
- 未验证 Windows EIM 环境下的 `run_espidf_build.py`；本次只运行了 Linux runner。
- 固件 app 分区仅剩约 6% 空间，后续增加功能或日志级别时需重新评估分区表/裁剪。
- 旧 SQLite 只针对已知列做 ALTER 迁移；若出现未知旧 schema 主键/约束变化，需要单独迁移脚本。
- 语音 ASR/TTS、RKLLM 加载、camera 模式和真实人脸识别仍未在本次环境验证。
- Bemfa 云端 CRC 无法校验，MQTT 路径按 `crc_ok=true` 记入；未来可在 gateway 侧对 ToF 帧尾/长度做二次校验。
