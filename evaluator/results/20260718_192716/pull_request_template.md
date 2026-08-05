# Pull Request 提测说明 (Pull Request Template)

本 PR 将本地护理/睡眠联调工程（Project2）修复至可提测状态。涉及后端网关（鉴权、care_event、
睡眠导入、voice 会话上下文）+ ESP32-S3 固件（Wi-Fi + 巴法云 MQTT 网络回传）。合并时 CI 与
Reviewer 会自动对本报告、变更 diff 做交叉一致性校验。

## 初始自检诊断

修改前运行两条诊断脚本（基线，全部 FAIL / 风险项）：

- `python tests\run_public_tests.py project2_task`
  - 通过公共测试入口 smoke / compile / functional / refactored_features，但后端存在多项安全与功能缺陷（见下）。
- `python tools\run_debug_probe.py project2_task` —— 初始 8 项探针 **全部 FAIL / 风险**：
  1. management API 不拒绝缺失 Cookie（GET /api/v3/subjects 无 Cookie → 期望 401，实际 200）
  2. management API 不拒绝伪造 Cookie（Cookie=project2_admin=not-a-real-token → 期望 401，实际 200）
  3. management API 合法 Cookie 才接受（缺失"拒绝伪造"前提）
  4. unknown identity 会话仍被放行（build_chat_context_v3 中 identity_state="unknown" 的 session，policy.allowed 应为 False，实际 True）
  5. expired 会话仍被放行（expires_ts 过期 → allowed 应为 False，实际 True）
  6. care_event 写入未拒绝缺失 admin Cookie（POST /api/v3/care/events 无 Cookie → 期望 401，实际 404/200）
  7. care_event 路由 404，且 room/bed 未归一化（创建 room="r1203"/bed="b1" 后 list_care_events(room="R1203",bed="B1") 查不到）
  8. voice 模块依赖环境变量静默 ambient session 取得上下文（告警，存在患者数据泄漏风险）
  - ESP32-S3：固件仅有 USB CDC 回传，无 Wi-Fi/MQTT 网络回传（TODO(v4) 占位）。

## 修改的文件列表

网关后端（gateway/）：
- `gateway/auth.py`：移除明文密码回退，管理员账号存在性按 `admin_accounts.status='active'` 判定，`get_admin_http_session` 按 `token_hash` + 过期 + 账号活跃三重校验。
- `gateway/gateway.py`：`session_is_authenticated` 增加过期 / identity_state / assurance_level 检查；`_authorized_for_api` 收紧为"仅 admin session 或显式允许的本地服务"，不再允许任意本地请求绕 Cookie；接线 care_event 的 POST/GET 路由；`build_chat_context_v3` 加入 care_events 摘要（零泄漏裁剪）。
- `gateway/db.py`：care_events 表扩展字段（severity/source/created_by/ts）；新增 `migrate_management_db` 列迁移，尽量保留旧数据。
- `gateway/care_events.py`：重写 create/list/build_care_events_context，全字段写入 + room/bed 归一化 + 倒序分页。
- `gateway/sleep_importer.py`：修复无归属行 first 策略错误（原返回 `beds[-1]`，改为 `beds[0]`）。
- `gateway/voice/voice_assistant_integrated.py`：新增 `fetch_current_session()` + `resolve_session_id()`，显式携带 session_id 取上下文，消除静默 ambient session 数据泄漏风险。

ESP32-S3 固件（esp32/testpro4/）：
- `main/main.cpp`：补全 Wi-Fi STA + 巴法云 MQTT 网络回传（事件处理、客户端、base64 动态缓冲发布、topic 生成、`config_is_complete` 完整性校验、`app_main` 启动链路）。
- `main/CMakeLists.txt`：REQUIRES 增加 esp_wifi / esp_event / esp_netif / mqtt / mbedtls。
- `main/idf_component.yml`：声明托管组件 `espressif/mqtt: "^1.0.0"`（ESP-IDF v6 起 esp-mqtt 已抽离为托管组件，组件名仍为 `mqtt`）。
- `sdkconfig.defaults`：补充 Wi-Fi / MQTT 配置项（含 `CONFIG_MQTT_BUFFER_SIZE=16384`）。

构建工具（tools/）：
- `tools/run_espidf_build.py`：新增 `_augment_idf_tools_env()`，确保 IDF 自带 ninja/ccache/cmake 在 PATH 中、并在派生 PowerShell 中剥离 `MSYSTEM`，使 Windows EIM 非交互式构建可稳定配置（纯构建基础设施，不改诊断逻辑）。

## 架构调整与模块设计

- 鉴权与授权分离：`auth.py` 只负责"这个 token 对应的 admin session 是否有效"；`gateway.py` 的
  `session_is_authenticated` 负责"当前请求主体（含过期、身份状态、保证级别）是否可信"。
- care_event 作为独立模块，与采集/睡眠/语音解耦：建表迁移在 `db.py`，CRUD 与上下文聚合在
  `care_events.py`，由 `gateway.py` 路由与 `build_chat_context_v3` 调用，未把逻辑塞回单一文件。
- ESP32 网络回传与 USB CDC 并行：USB 路径不依赖网络配置（未配置 Wi-Fi/UID 时固件仍以 USB 运行），
  MQTT 仅作为镜像通道，不改变既有的传感器解析/采集时序。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256 + 随机 16 字节 salt，数据库中只存 salt 与 hash，**无明文**。
- 会话：随机 `secrets.token_urlsafe(32)` token；Cookie 只存 `token_hash`，服务端按 hash 校验，
  无法由 Cookie 反推 token。
- 授权上下文（v3）：unknown 身份、过期、assurance_level 为 none 一律拒绝；allowed 时才裁剪
  care_events 等摘要进 prompt_hints，原始患者数据不进上下文（零泄漏）。
- 本地服务（如 `/api/v3/session/current`）单独列入白名单，不再允许任意本地请求绕过 Cookie。
- voice 助手改为显式 `session_id`（优先显式参数 > 配置 > 网关当前 session），不再依赖环境变量
  静默 ambient session，避免跨患者数据泄漏。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 按行策略处理：显式含 room/bed 的行归入对应床位；无归属行根据 `SLEEP_IMPORT_UNSCOPED_POLICY`
  走 first / skip / all 策略。
- 修复 first 策略 bug：原实现错误返回 `beds[-1]`，现改为 `beds[0]`（首条配置床位），与契约一致。

## care_event 实现细节

- `POST /api/v3/care/events`：要求 admin Cookie，写入 event_id/subject_id/room/bed/kind/title/
  content/severity/source/created_by/ts；room/bed 入库前归一化（大写等）。
- `GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=...`：支持按 subject 或房间/床位
  过滤，room/bed 查询同样归一化，`ORDER BY ts DESC, created_ts DESC LIMIT n` 倒序。
- `build_chat_context_v3` 的 modalities.care_events 返回 `{items, brief}` 摘要（默认最近 5 条）。

## ESP32-S3 固件接口对齐说明

- Topic 命名严格对齐 `gateway/bed_config.py.topics_for`：`{room.lower()}{bed.lower()}{kind}`，
  四路姿态流 tof1/tof2/mlx1/mlx2（如 r1203b1tof1）。
- MQTT JSON 对齐 `reference/espidf_protocol_contract.md`：`{"payload_b64":"<base64 原始 payload>"}`，
  base64 编码的是**原始 payload**（ToF 完整 MaixSense 帧 / MLX 帧），不是完整 USB packet。
- 缓冲分配：ToF payload ~10002 字节，base64 后约 13336 字符。`publish_payload` 动态分配
  `((len+2)/3)*4+1` 字节 base64 缓冲与 `b64_len+32` 字节 JSON 缓冲，**未使用固定小缓冲**（规避
  `char b64_buf[256]` 截断整帧的常见错误）。
- 协议字段：CRC16-CCITT（init 0xFFFF, poly 0x1021，仅覆盖 payload）、LEN/CRC 小端序均保持与既有 USB 实现一致，未改动。
- NVS：Wi-Fi SSID/密码、巴法云 UID/host/port、room/bed、device_id 均沿既有 NVS 读写；
  `config_is_complete` 现要求 bed 配置 + 网络配置（wifi_ssid/bemfa_uid/host/port）齐全。

## 本地测试与编译验证结果

修复后运行：

- `python tests\run_public_tests.py project2_task` → **全部 public 测试通过**（test_compile /
  test_functional_smoke / test_refactored_features / test_smoke_gateway 均 OK）。
- `python tools\run_debug_probe.py project2_task` → **8 项探针全部 [probe:ok]**，voice 由告警变为
  `[probe:info] voice module appears to reference current-session fetch`。
- `python tools\run_espidf_build.py project2_task` → ESP-IDF v6.0.1 编译结果见下。

### ESP-IDF 编译结果

- 环境：Windows EIM，ESP-IDF v6.0.1；目标 `esp32s3`；`E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1`。
- 初始编译失败：`components/mqtt` 在 v6 已抽离为托管组件 `espressif/mqtt`，`REQUIRES mqtt` 无法解析。
  修复：`idf_component.yml` 声明 `espressif/mqtt: "^1.0.0"`，组件名仍为 `mqtt`，REQUIRES 不变。
- 构建工具问题：`run_espidf_build.py` 在非交互式环境下 cmake 找不到 Ninja/ccache，且 Git-Bash 派生的
  PowerShell 因 `MSYSTEM=MINGW64` 导致 `idf.py set-target` 拒绝创建 build 目录。已在
  `run_espidf_build.py` 增加 `_augment_idf_tools_env()`（补充 IDF 工具 PATH + 剥离 MSYSTEM）修复。
- 额外编译错误（修复后复跑暴露）：`main.cpp` 的 `wifi_init_sta` 用 `snprintf("%s", s_device_config.wifi_ssid)`
  写入 `wifi_config.sta.ssid`（32 字节），因源 `wifi_ssid` 为 33 字节触发 `-Werror=format-truncation`
  （main.cpp:550/552 两处）。改为 `strncpy` + 显式补 `\0`，规避该误报且不改变截截断上限。
- **最终编译结果：PASS ✅**。ESP-IDF v6.0.1 完整编译通过：
  - `Build finished successfully`，产物 `build/stdpro.bin`（0xed460 字节，约 944 KiB；最小 app 分区 0x100000，余 7%）。
  - `build/bootloader/bootloader.bin`（0x5760 字节）、`build/partition_table/partition-table.bin` 同步生成。
  - 全量组件（含 `espressif__mqtt`、`esp_wifi`、`esp_netif`、`mlx90640`、`espressif__esp_tinyusb`）均链接成功，无 error / warning 升级为错误。
  - （注：本段在编译任务完成后回填；若 CI 复跑请以其输出为准。）

## 未验证的残留技术债与风险

1. 真实硬件未验证：本环境未对 ESP32-S3 真实设备 `flash`/`monitor`，未验证真实 Wi-Fi 关联、巴法云
   MQTT 连通、真实 ToF 上电冷启动与自动波特率探测时序（任务文档明确不在本地编译中验证这些内容）。
2. 真实 USB 枚举、真实 I2C 温度读数、真实网络连通性未做端到端联调。
3. 巴法云 broker 实际 topic 权限 / UID 鉴权行为依赖外部账号配置，未做线上验证；仅按契约实现发布。
4. SQLite 迁移 `migrate_management_db` 在历史库缺列时补列，已尽量保留旧数据；极端旧 schema（缺
   整张 care_events 表）走 `executescript` 重建 + 迁移，未做 1.0 之前多种中间态的回归。
5. voice 显式 session 取上下文依赖网关 `GET /api/v3/session/current` 路由返回正确 session；该路由
   已加入白名单，但未对"网关未配置 VOICE_SESSION_ID 且当前无 session"的边界做线上验证。
6. `_augment_idf_tools_env` 假设 IDF 工具装在 `E:\esp\tools\{ninja,ccache,cmake}\<ver>\` 标准形式；
   若用户 EIM 安装路径不同，需相应调整（脚本已优先读取 `ESP_IDF_TOOLS_PATH` 环境变量）。
