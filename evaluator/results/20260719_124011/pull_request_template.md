# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前在工作区根目录运行（Windows PowerShell）：

- `python tests\run_public_tests.py project2_task`
  - 结果：全部通过（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway，`[public] all public tests passed`）。公开冒烟只覆盖浅层行为，不能反映下面的安全问题。
- `python tools\run_debug_probe.py project2_task`
  - 结果：`[probe] failures=6`，失败项：
    1. `management API rejects missing cookie`：`GET /api/v3/subjects` 无 Cookie 仍返回 200 并带出 subject 列表（本机请求被无条件放行）。
    2. `management API rejects forged cookie`：伪造 Cookie 同样返回 200（`auth.get_admin_http_session` 不校验 token，抓取任意有效会话）。
    3. `unknown identity session is denied`：`identity_state=unknown` 的 session 仍被判为已认证并返回患者明细。
    4. `expired session is denied`：已过期的 session 仍被接受（无 `expires_ts` 检查）。
    5. `care_event write rejects missing admin cookie`：`POST /api/v3/care/events` 路由不存在（404）。
    6. `care_event normalizes room/bed for create and query`：care_event 模块缺少规范化与查询链路。
  - 另有 voice/助手路径 Warning（收紧后需显式携带 session）与 ESP32 编译提示。

## 修改的文件列表

Gateway（Python）：

- `gateway/auth.py`：修复密码明文存储、管理员存在性检查、HTTP 会话 token 校验、旧明文账号迁移。
- `gateway/db.py`：`care_events` 完整建表 + 基于 `PRAGMA table_info` 的旧表缺列迁移（保留旧数据）。
- `gateway/care_events.py`：补完 care_event CRUD、room/bed 规范化、上下文聚合。
- `gateway/gateway.py`：管理 API 鉴权收敛、v3 session 认证语义、care_event 路由、`modalities.care_events`、补 `DEFAULT_ADMIN_SUBJECT_ID` 导入。
- `gateway/sleep_importer.py`：修复 `first` 策略错用 `beds[-1]`（改为 `beds[0]`），显式行/默认床位统一规范化。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session()`/`resolve_voice_session_id()`，上下文请求显式携带 session_id。

ESP32-S3 固件（`esp32/testpro4`）：

- `main/main.cpp`：重写为 glue（ESP-IDF 初始化、任务、硬件调用），USB 发送改走 `protocol_packet` 辅助函数，并接入 MQTT 镜像发送。
- `main/protocol_packet.{h,cpp}`（新增）：USB packet 常量、CRC16-CCITT、打包辅助。
- `main/maixsense_parser.{h,cpp}`（新增）：MaixSense 字节流解析器。
- `main/device_config.{h,cpp}`（新增）：NVS 配置、完整性校验、串口命令、topic 前缀规范化。
- `main/mqtt_payload.{h,cpp}`（新增）：`payload_b64` JSON 构造、topic 选择。
- `main/network_backhaul.{h,cpp}`（新增）：Wi-Fi STA + 巴法云 MQTT client 与发布链路。
- `main/CMakeLists.txt`：新增源文件；`REQUIRES` 补齐 `esp_wifi/esp_netif/esp_event/lwip/espressif__mqtt/mbedtls`。
- `main/idf_component.yml`：新增 `espressif/mqtt`（IDF v6 中 esp-mqtt 不再内置，经组件管理器引入）。

文档：

- `gateway/README.md`、`README.md`、`RK3588_TEST_GUIDE.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`：同步 care_event、鉴权边界、睡眠 CSV 策略与 ESP32 回传已恢复的说明。
- `PULL_REQUEST_TEMPLATE.md`：本文件。

## 架构调整与模块设计

- 保持既有模块边界：`gateway.py` 只加路由 glue 与上下文编排；护理事件业务逻辑放 `care_events.py`；schema 与迁移放 `db.py`；管理员账号/会话放 `auth.py`。没有把逻辑堆回单文件。
- `db.init_management_db` 在建表后调用 `migrate_management_db`：对 `_TABLE_COLUMN_MIGRATIONS` 中声明的表/列执行 `PRAGMA table_info` 检查 + `ALTER TABLE ADD COLUMN`，再做数据回填；只增不删，旧库平滑升级。
- 固件按交接规范拆成 5+1 个模块：`protocol_packet`（协议常量/CRC/打包）、`maixsense_parser`（帧解析）、`device_config`（NVS/校验/topic）、`mqtt_payload`（base64 JSON/topic 选择）、`network_backhaul`（Wi-Fi/MQTT 生命周期）、`main.cpp`（glue）。

## 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256（200k 迭代）+ 16 字节随机盐，绝不明文落库；登录用 `hmac.compare_digest` 常量时间比较。旧库中 `salt` 为空的明文行，在首次成功登录时自动重写为加盐哈希（迁移而非降低要求）。
- Cookie 会话：Cookie 只携带 `secrets.token_urlsafe(32)` 随机 token；DB 只存 token 的 SHA-256。`get_admin_http_session` 严格按 token hash + 有效期 + 账号状态查询，伪造/过期 Cookie 一律 401。
- 管理 API 鉴权收敛：`_authorized_for_api` = 有效管理员会话，或（本机 loopback **且** 路径在本机服务白名单内）。白名单仅：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`（voice 显式取会话用）。`/api/v3/subjects`、`/api/v3/care/events` 等管理接口本机无 Cookie 也 401；face gallery 与 credential 模板仍禁止远程导出。
- v3 上下文裁剪：session 满足「存在 + 未过期 + 有 actor_subject_id + identity_state ∈ {recognized, authenticated} + assurance_level 非 none/空」才算已认证；staff/admin 可看任意目标，patient 只能看自己，其余（含 actor 缺失）拒绝。拒绝时 `target.patient/assignment` 与全部 modalities（sleep/vitals/posture/memory/care_events）返回空，患者数据零泄漏。
- voice 侧：通过 `/api/v3/session/current` 显式解析当前 session 并在 context 请求中携带 `session_id`（带 3s 缓存），不再依赖网关静默 ambient session；未认证时只回权限提示。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行处理（同一 CSV 可混合两类行）：

- 行带 `room/bed`：只写入对应床位；命中配置床位时采用配置大小写，未命中按 gateway 大写约定规范化。
- 行不带 `room/bed`：优先 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 指定床位；否则 `SLEEP_IMPORT_UNSCOPED_POLICY`：`first` 写第一个配置床位（修复了原来错写 `beds[-1]` 的 bug）、`skip` 跳过、`all` 仅作显式调试广播（非默认）；策略只作用于无归属行，不误改显式行。

## care_event 实现细节

- `db.py`：`care_events(event_id PK, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts)` + subject / room-bed 两个索引；旧表缺 `severity/source/created_by/ts` 时自动 `ADD COLUMN`（默认 `info/manual/''/0`）并 `UPDATE care_events SET ts=created_ts WHERE ts=0` 回填，旧行不丢失。
- `care_events.py`：`create_care_event` 校验 subject 存在、room/bed 必填并按大写规范化、severity/source 白名单收敛；`list_care_events` 支持 `subject_id`、`room+bed`、`limit`，按 `ts/created_ts` 倒序；`build_care_events_context` 输出最近事件摘要。
- 路由：`POST /api/v3/care/events` 与 `GET /api/v3/care/events` 均为管理接口（需管理员登录；未登录 401）。授权通过的 `/api/v3/context/chat` 在 `modalities.care_events` 返回目标患者最近 10 条摘要，未授权为空。
- 已验证：lowercase 写入 `r1203/b1` 可被 uppercase `R1203/B1` 查询命中。

## ESP32-S3 固件接口对齐说明

- Wi-Fi STA：`network_backhaul_start()` 从 NVS 读取 `wifi_ssid/wifi_pass`，WPA2（空密码按开放网络处理并告警）；断线自动重连，拿到 IP 置位事件组。
- MQTT 巴法云：broker `mqtt://{bemfa_host}:{bemfa_port}`（默认 `bemfa.com:9501`），ClientID/Username = `bemfa_uid`，keepalive 60s，异常自动重连；发布串行化（mutex），发送/丢弃计数。
- NVS 校验：`device_config_core_ready`=room+bed（USB 可跑），`device_config_network_ready`=room+bed+ssid+uid（缺项则只跑 USB 并打印帮助）；`device_id` 缺省派生 `esp32-{room}{bed}-posture`。
- Topic：`device_config_topic_prefix` 将 room/bed 小写拼接，`{room}{bed}tof1/tof2/mlx1/mlx2`（如 `r1203b1tof1`），与 `gateway/bed_config.py` 的 `topics_for` 一致。
- Payload：MQTT JSON 固定为 `{"payload_b64":"..."}`，mbedtls base64 编码传感器**原始 payload**（非完整 USB packet）；按精确尺寸 `malloc`（ToF ~13.4KB JSON），发布后即释放，避免小固定缓冲与内存泄漏。
- 并行回传：`usb_send_tof_payload()` 与 MLX 发送路径保留 USB CDC 输出（含包头+CRC），同时向对应 topic 镜像发布；MQTT 不依赖 USB 是否连接，MQTT 未就绪时只丢弃并计数，不影响 USB。
- USB 契约保持：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT（0xFFFF/0x1021）只覆盖 payload，LEN/CRC 小端；ToF payload 保持完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHECKSUM][DD]`。
- 解析器：处理噪声前缀、分块、坏尾字节（假帧头跳过）、异常长度（0 或超上限视为噪声）与半帧缓存；溢出时丢弃最旧字节。
- IDF v6 适配：`espressif/mqtt` 经组件管理器引入（CMake 引用 `espressif__mqtt`），`esp_wifi/esp_netif/esp_event/lwip/mbedtls` 为内置组件。

## 本地测试与编译验证结果

修复后再次运行：

- `python tests\run_public_tests.py project2_task` → 全部通过：`[public] all public tests passed`（4 个测试文件全 OK）。
- `python tools\run_debug_probe.py project2_task` → 全部通过：`[probe] all visible diagnostic checks passed`（8 项 ok，voice 提示变为 info：已引用 current-session fetch）。
- `python tools\run_espidf_build.py project2_task` → **编译成功**（exit 0）：Windows EIM ESP-IDF v6.0.1、`idf.py set-target esp32s3` + `cmake --build`，产物 `stdpro.bin`（大小 0xf0010，分区余量 6%）。过程中修复 2 个真实编译问题：`mqtt` 组件名解析（IDF v6 改为 `espressif__mqtt`）、`device_config.cpp` 的 `-Werror=format-truncation`。
- 额外自写临时库校验（非修改 tests/tools）：旧 schema SQLite 迁移（旧行保留、`ts` 回填）、明文 admin 登录后自动升级为加盐哈希、伪造 token 拒绝、staff/patient-self/patient-cross 上下文策略、混合有/无 room-bed 的 CSV 在 `first` 与 `skip` 策略下的按行归属，全部符合预期。

## 未验证的残留技术债与风险

- 未做 `idf.py flash/monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序与 MLX90640 实机读数验证（任务范围外）；Wi-Fi 事件回调里的重连延迟用 `vTaskDelay`，事件组等待时间可能略长于预期，建议实机观察。
- 巴法云 MQTT 的具体认证细节（是否要求额外 password/特殊 ClientID 格式）按公开契约以 UID 作为 ClientID+Username 实现，未经真实 broker 联调。
- 高帧率 ToF（~8fps×13.4KB）MQTT 上行对弱网/小内存设备有压力；当前未做 QoS/降频策略，必要时在 `network_backhaul` 加发布节流。
- 旧库 `sessions`/`admin_http_sessions` 只按现有列创建，未验证更老版本表结构（本任务样例库仅覆盖 care_events 类缺列场景）；迁移框架可复用扩展。
- voice 的 `fetch_current_session` 依赖网关 `/api/v3/session/current`（已加入本机白名单）；若管理员希望voice 走固定身份，仍建议显式设置 `VOICE_SESSION_ID`。
- `all` 广播策略保留为显式调试入口，生产部署请使用 `skip` 或默认床位。
