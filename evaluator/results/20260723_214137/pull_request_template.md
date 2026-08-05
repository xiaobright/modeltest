# Pull Request 提测说明 (Pull Request Template)

本文件记录本次 Sprint 的最终实现、验证与残留风险。CI 与 Reviewer 会将本报告、变更 diff 与自检日志做一致性交叉校验。

## 初始自检诊断（修改前）

在动代码前先运行了要求的两条自检命令：

- `python tests\run_public_tests.py project2_task` → 全部通过（这些是浅层 smoke，只验证能 import/编译/路由起得来，不校验安全性）。
- `python tools\run_debug_probe.py project2_task` → **6 项 FAIL + 1 项 Warning**：
  1. `management API rejects missing cookie` FAIL：`GET /api/v3/subjects` 无 Cookie 仍返回 200。
  2. `management API rejects forged cookie` FAIL：伪造 Cookie 仍返回 200。
  3. `unknown identity session is denied` FAIL：`identity_state=unknown` 的 session 被判为已授权。
  4. `expired session is denied` FAIL：`expires_ts` 已过期的 session 仍被授权。
  5. `care_event write rejects missing admin cookie` FAIL：`POST /api/v3/care/events` 返回 404（路由不存在）。
  6. `care_event normalizes room/bed for create and query` FAIL：小写 `r1203/b1` 写入后大写 `R1203/B1` 查不到。
  - Warning：voice/助手路径未显式获取当前会话，收紧鉴权后可能取不到上下文。

根因定位：
- `auth.py` `get_admin_http_session()` 忽略 token、返回任意活跃会话；`_password_hash()` 空盐时明文存储；`admin_account_exists()` 恒返回 False。
- `gateway.py` `_authorized_for_api()` 对任意本机 `/api/**` 放行（管理 API 也被本机免登录访问）；`session_is_authenticated()` 把 `unknown` 当已认证、且不校验过期/actor；`build_chat_context_v3()` 无 session 时静默借用 ambient 会话；`care_events` 无路由、未接入 context。
- `care_events.py` 未规范化 room/bed、缺 `severity/source/created_by/ts`、CRUD 不完整。
- `db.py` `care_events` 建表缺列且 `CREATE TABLE IF NOT EXISTS` 无法迁移旧表。
- `sleep_importer.py` `first` 策略误用 `beds[-1]`（最后一个床位）而非 `beds[0]`。
- ESP32 `esp32/testpro4` 仅有 USB CDC，Wi-Fi/MQTT/依赖被注释为 TODO。

## 修改的文件列表

Gateway / Python：
- `gateway/db.py`：`care_events` 补全 `severity/source/created_by/ts`；新增 `migrate_care_events()`（`PRAGMA table_info` + `ALTER TABLE`，旧行 `ts` 回填 `created_ts`）；ts 索引移入迁移函数（避免对未加列的旧表建索引失败）。
- `gateway/care_events.py`：CRUD 重写——create/list 规范化 room/bed、补齐新字段、`limit`、`ts DESC` 排序；`build_care_events_context()` 生成授权上下文摘要；schema/迁移委托 `db.py`。
- `gateway/auth.py`：`_password_hash()` 一律 PBKDF2-HMAC-SHA256 加盐哈希；`admin_account_exists()` 查库；`get_admin_http_session()` 按 `token_hash` 精确匹配。
- `gateway/gateway.py`：`session_is_authenticated()` 收紧；`_authorized_for_api()` 本机仅放行服务白名单；`/api/v3/session/current` 加入白名单；新增 `GET/POST /api/v3/care/events` 路由；context 增加 `modalities.care_events`；`build_chat_context_v3()` 去掉 ambient 回退；import `care_events`。
- `gateway/sleep_importer.py`：`first` 策略改为 `beds[0]`。
- `voice/voice_assistant_integrated.py`：新增 `fetch_current_session()/current_session_id()` 与 `GATEWAY_SESSION_CURRENT_URL`，无固定 `VOICE_SESSION_ID` 时显式取当前会话再带 `session_id`。

ESP32-S3 固件 `esp32/testpro4/`：
- 新增 `main/protocol_packet.{h,cpp}`：USB 包常量、CRC16-CCITT、包头打包。
- 新增 `main/device_config.{h,cpp}`：NVS key、`ssid/password/uid/room/bed` 读写与完整性校验、topic 规范化。
- 新增 `main/mqtt_payload.{h,cpp}`：`payload_b64` JSON 构造（堆分配）与 stream/topic 选择。
- 新增 `main/net_backhaul.{h,cpp}`：Wi-Fi STA + 巴法云 MQTT 客户端生命周期与发布。
- `main/main.cpp`：移除已抽取的 CRC/常量/NVS 逻辑；ToF 与 MLX 发送路径在保留 USB CDC 的同时调用 `net_backhaul_publish()`；`app_main` 增加 `net_backhaul_start()`；配置控制台改为委托 `device_config`。
- `main/CMakeLists.txt`：新增源文件与 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 依赖。
- `main/idf_component.yml`：声明托管组件 `espressif/mqtt`（v6.0 已从核心拆出）。

文档：`gateway/README.md`、`README.md`、`RK3588_TEST_GUIDE.md` 同步 care_event/鉴权/会话/MQTT 变更。

## 架构调整与模块设计

- 保持既有模块边界，不把逻辑塞回 `gateway.py`：护理事件独立成 `care_events.py`，`gateway.py` 只保留路由 glue；schema/迁移集中在 `db.py`。
- ESP32 按交接建议拆分为 `protocol_packet` / `device_config` / `mqtt_payload` / `net_backhaul` 四个模块，`main.cpp` 只保留 ESP-IDF 初始化、任务创建、硬件调用和模块 glue。MaixSense 帧解析器与 ToF 任务强耦合、且是已验证的成熟逻辑，保留在 `main.cpp` 内以免破坏时序（未新增第五个模块文件）。

## 安全边界及鉴权设计

- **密码**：PBKDF2-HMAC-SHA256 + 16 字节随机盐 + 200k 轮；数据库存 `salt`/`password_hash`，绝不明文。
- **Cookie/会话**：Cookie 只存随机 `token`，库内只存其 SHA-256 哈希；`get_admin_http_session()` 按 `token_hash` 且未过期匹配，缺失/伪造 Cookie 无法命中。
- **管理 API 边界**：`_authorized_for_api()` = 有效管理员 Cookie，或（本机请求 **且** 命中本机服务白名单）。白名单仅含 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/session/current`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`。`/api/v3/subjects`、`/api/v3/care/events` 等管理 API 即使来自 127.0.0.1 也必须带 Cookie；远程一律需登录。face/credential 模板导出仍限本机服务。
- **v3 授权上下文**：`session_is_authenticated()` 对以下一律判为未认证——无 session、`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 已过期、缺 `actor_subject_id`。授权后 staff/admin 可看任意目标患者，patient 只能看自己；未授权时 `target.patient/assignment` 与各 `modalities`（含 `care_events`）均为空，患者明细零泄漏。
- **不靠静默 ambient session**：`build_chat_context_v3()` 无 `session_id` 时直接按未认证处理，不再借用“当前会话”。本机语音助手改为显式 `GET /api/v3/session/current` 取会话并回传 `session_id`——既解决 probe 的 voice Warning，也避免跨 actor 数据串味。

## 睡眠 CSV 无 room/bed 时的特殊处理（按行策略）

- 行带 `room/bed`：只写入对应床位（大小写不敏感匹配已配置床位；未匹配则按原样写入），显式行不受策略影响、不整表丢弃。
- 行不带 `room/bed`：
  - 设了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入**第一个**配置床位 `beds[0]`（本次修复的 bug：原为 `beds[-1]`）；
  - `=skip` → 跳过；
  - `=all` → 仅显式调试用（默认策略是 `first`）。
- 同一 CSV 中显式行与无归属行可共存，策略只作用于无归属行。

## care_event 实现细节

- 表字段：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`。
- `create_care_event()`：`normalize_room/normalize_bed` 规范化；缺省 `severity=info/source=manual`；`ts` 缺省取 `now_ms`；按 `event_id` upsert。
- `list_care_events()`：`subject_id` 或 `room+bed`（同样规范化）过滤，`ORDER BY ts DESC, created_ts DESC`，`limit` 默认 50、上限 500。
- 路由：`POST /api/v3/care/events`（管理员）、`GET /api/v3/care/events?subject_id=|room=&bed=&limit=`（管理员）。
- Context：授权通过时 `modalities.care_events` 返回目标患者/床位最近事件摘要（`build_care_events_context`）；未授权为空。
- 迁移：旧库若为 `event_id/.../created_ts/updated_ts` 老结构，`migrate_care_events()` 补齐四列并把旧行 `ts` 回填为 `created_ts`，旧数据不丢。

## ESP32-S3 固件接口对齐说明

- **USB packet 契约保持不变**：`[AA 55][TYPE][ID][LEN_L LEN_H][PAYLOAD][CRC_L CRC_H]`，`LEN` 与 CRC 小端，CRC16-CCITT(0xFFFF/0x1021) 只覆盖 payload。
- **ToF payload**：仍是完整 MaixSense 原始帧 `[00 FF][LEN][META(16)][IMG(10000)][CHK][DD]`，未裁成 10000B 图像区。
- **NVS**：从 NVS 读取并校验 `ssid/password/uid/room/bed`（及 `bemfa_host/port/device_id`）；`room+bed` 齐即可跑 USB 采集，`ssid+uid+room+bed` 齐才启动网络回传，缺失则保持 USB-only 不影响采集。
- **Topic**：`device_config_topic()` 用规范化小写拼接 `{room}{bed}{stream}`，stream ∈ `tof1/tof2/mlx1/mlx2`，与 gateway `topics_for()` 一致（如 `r1203b1tof1`）。
- **MQTT**：`net_backhaul` 起 Wi-Fi STA + esp-mqtt，broker `mqtt://{host}:{port}`（默认 bemfa.com:9501），ClientID=巴法云 UID；发布 `{"payload_b64":"<base64 原始 payload>"}`，base64 是**原始 sensor payload**（非完整 USB packet）。
- **大 payload 内存**：完整 ToF 帧 base64 约 13KB，JSON 在**堆**上按需分配（`malloc`/`free`），不使用固定小缓冲，规避原注释里 `char b64_buf[256]` 的溢出坑。
- **并行回传**：`usb_send_tof_payload()` 与 MLX 发送在保留 USB CDC 的同时调用 `net_backhaul_publish()`；MQTT 离线时静默丢弃，不阻塞 USB。

## 本地测试与编译验证结果

- 修改后 `python tests\run_public_tests.py project2_task` → `all public tests passed`（4 个测试文件全绿）。
- 修改后 `python tools\run_debug_probe.py project2_task` → `all visible diagnostic checks passed`（8/8 ok；voice 提示变为 `voice module appears to reference current-session fetch`，Warning 消除）。
- 额外临时脚本验证（已删除，不入库）：密码非明文/盐非空/Cookie 只存哈希/错误密码被拒；旧 `care_events` 表迁移补列且旧行 `ts` 回填、迁移后大小写查询命中；staff 可访任意患者、patient 仅自己、越权/无会话被拒且不带患者明细、授权后含 `care_events`。
- `python tools\run_espidf_build.py project2_task`（Windows EIM ESP-IDF v6.0.1，target esp32s3）：
  - 首轮失败：`Failed to resolve component 'mqtt'` —— v6.0 已把 esp-mqtt 拆为托管组件，核心 `components/mqtt` 为空占位。修复：在 `idf_component.yml` 声明 `espressif/mqtt`。
  - 次轮失败：`net_backhaul.cpp` `snprintf` 触发 `-Werror=format-truncation`（SSID 字段 32B 而源缓冲 33B）。修复：改用 `strnlen`+`memcpy` 写入零初始化的 `wifi_config_t`。
  - **最终成功**：`Successfully created ESP32-S3 image` / `Build finished successfully`，产物 `build/stdpro.bin`（约 0xf0090 ≈ 983KB）。
  - 说明：仅编译验证，未做 `flash`/`monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序或 MLX 实机读数（按契约不在本地编译验证范围内）。

## 未验证的残留技术债与风险

- **未上真机**：Wi-Fi 连接、MQTT 握手/重连、base64 payload 端到端、ToF/MLX 实机数据均未在硬件验证；`net_backhaul` 的连通性只保证能编译与逻辑自洽。
- **App 分区余量偏紧**：加入 Wi-Fi+MQTT+mbedtls 后 `stdpro.bin` 占用约 94%（0x100000 分区仅剩约 6%）。后续再加功能可能需要调分区表或裁剪组件。
- **MQTT 吞吐/内存**：ToF ~8fps×2 路，每帧堆分配约 13KB JSON，长时间高频回传的碎片化/背压未压测；当前 qos0、离线丢弃。
- **MLX topic 语义**：MLX 两路用同一 `MLXManager` 输出，`mlx1/mlx2` 对应 0x01/0x02，与实机 I2C 地址 0x33/0x34 的对应关系未在硬件核对。
- **care_event GET 授权**：直接 `GET /api/v3/care/events` 采用“需管理员登录”的收敛口径；“授权 actor 经上下文可见”通过 `/api/v3/context/chat` 的 `modalities.care_events` 实现，未再为该 REST 端点单独开放 v3 会话直读。
- **bemfa MQTT 鉴权**：按契约以 UID 作 ClientID、topic 明文；未实现 bemfa 可能需要的用户名/密码或订阅侧回读校验。
- `espressif/mqtt` 用 `"*"` 版本，依赖组件仓库可解析到与 IDF v6.0.1 兼容的版本；离线或 registry 变更时需改为固定版本。
