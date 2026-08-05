# Pull Request 提测说明 (Pull Request Template)

本项目为护理/睡眠 gateway（Project2）迭代。以下内容与本次实际代码 diff 和自检日志一致。

## 1. 修改的文件列表

### Python Gateway / 模块
- `gateway/auth.py` — 密码加盐哈希、`admin_account_exists` 真实查询、Cookie 会话按 token 精确校验
- `gateway/db.py` — `care_events` 表补列（severity/source/created_by/ts）、通用旧库缺列迁移、ts 回填
- `gateway/care_events.py` — 完整 CRUD：room/bed 规范化、limit、按 ts/created_ts 倒序、v3 上下文摘要
- `gateway/gateway.py` — 管理 API 鉴权收紧（本机豁免仅限指定服务路径）、`/api/v3/care/events` 路由、v3 会话鉴权语义、context 增加 `modalities.care_events`、修复 `DEFAULT_ADMIN_SUBJECT_ID` 缺失导入
- `gateway/sleep_importer.py` — 按行归属策略（显式 room/bed 行 / 默认房床 / first=第一个床位 / skip / all 仅调试）
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session()`，请求敏感上下文前显式携带 session_id

### ESP32-S3 固件（esp32/testpro4）
- `main/main.cpp` — 保留初始化/任务/硬件 glue，接入网络回传
- `main/protocol_packet.{h,cpp}` — 新增：USB packet 常量、CRC16-CCITT、header 打包、stream key
- `main/maixsense_parser.{h,cpp}` — 新增：MaixSense 字节流解析器（噪声/分块/坏尾/异常长度/半帧）
- `main/device_config.{h,cpp}` — 新增：NVS 配置、ssid/password/uid/room/bed 完整性校验、topic 前缀规范化
- `main/mqtt_payload.{h,cpp}` — 新增：`{"payload_b64":"..."}` JSON 构造（动态缓冲）、topic 选择
- `main/net_backhaul.{h,cpp}` — 新增：Wi-Fi STA + 巴法云 MQTT 客户端生命周期与发布路径
- `main/CMakeLists.txt` — REQUIRES 补齐 esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls/esp_timer
- `main/idf_component.yml` — 注册 `espressif/mqtt`（版本对齐本机离线 EIM 组件库 1.0.0）

### 文档
- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`esp32/testpro4/QUICKSTART.md`

## 2. 修改前初始诊断结果

### `python tests\run_public_tests.py project2_task`
- 结果：4 个测试文件全部通过（该套件为浅层 smoke，不校验安全属性）。

### `python tools\run_debug_probe.py project2_task`
- 结果：`failures=6`：
  1. `management API rejects missing cookie` — 无 Cookie 仍返回 200（本机请求被整体豁免）
  2. `management API rejects forged cookie` — 伪造 Cookie 仍返回 200（会话查询忽略 token）
  3. `unknown identity session is denied` — `identity_state=unknown` 的会话仍被放行
  4. `expired session is denied` — 已过期会话仍被放行
  5. `care_event write rejects missing admin cookie` — 路由不存在（404）
  6. `care_event normalizes room/bed for create and query` — 小写 r1203/b1 查询不到
- 另有 Warning：voice 依赖 ambient session 取上下文。

## 3. 架构调整与模块设计

- `gateway.py` 只保留路由 glue；新增职责落在独立模块：`care_events.py`（护理事件 CRUD/上下文）、`db.py`（迁移）、`auth.py`（会话）。
- 固件按 `reference/espidf_protocol_contract.md` 拆分为 `protocol_packet` / `maixsense_parser` / `device_config` / `mqtt_payload` / `net_backhaul`，`main.cpp` 只做初始化与 glue。
- 本机服务接口例外从“所有本机请求”收敛为白名单路径（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`、`/api/v3/session/current`），管理 API 与 face/credential template 不再豁免。

## 4. 安全边界及鉴权设计

- 管理员密码：PBKDF2-HMAC-SHA256（16 字节随机盐，200,000 迭代）哈希存储，任何情况下不落明文；旧库若存在明文行，首次登录时自动重哈希迁移。
- Cookie：只保存随机 token（`secrets.token_urlsafe(32)`），数据库只存 token 的 SHA-256 哈希；校验按 `token_hash` 精确匹配且检查 `expires_ts` 与账号状态（修复了“任意非空 Cookie 命中任意活跃会话”的漏洞）。
- v3 会话鉴权：`identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 过期、缺 `actor_subject_id` 四种情况一律视为未认证；未认证/未授权请求不返回患者明细、记忆、护理事件（`target.patient`/`assignment` 为空对象，modalities 为空）。
- `actor_can_access_target`：admin/staff 可读任意目标患者；patient 只能读自己；actor 信息缺失一律拒绝（不再有“内部调用放行”隐式捷径）。
- `/api/v3/care/events`：写入需管理员 Cookie；读取需管理员登录，或本机 worker 携带通过 v3 授权检查的会话。
- 远程未登录用户不能访问管理 API、不能导出 face/credential template（gallery/template 仅本机服务路径）。

## 5. 睡眠 CSV 无 room/bed 时的特殊处理

按行处理，同一 CSV 可混用显式行与无归属行：

- 行带 `room/bed`：只写入对应床位（规范化大小写），不套用无归属策略。
- 行不带 `room/bed`：
  - 设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位；
  - 否则按 `SLEEP_IMPORT_UNSCOPED_POLICY`：`first`（默认）→ 第一个配置床位；`skip` → 跳过；`all` → 写入全部（仅显式调试，非默认）。
- 修复了原实现 `first` 误用 `beds[-1]`（最后一个床位）的问题，改为 `beds[0]`。

## 6. care_event 实现细节

- `gateway/db.py`：`care_events` 表 + `(subject_id, ts DESC)` / `(room, bed, ts DESC)` 索引；旧库缺列迁移（ALTER TABLE ADD COLUMN severity/source/created_by/ts，默认值 info/manual/''/0）并回填 `ts=created_ts`，保留旧数据。
- `gateway/care_events.py`：`create_care_event`（event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts）、`list_care_events(subject_id, room, bed, limit)` 按 `ts DESC, created_ts DESC` 倒序、`build_care_events_context` 最近事件摘要。
- 路由：`POST /api/v3/care/events`（管理员）、`GET /api/v3/care/events?subject_id=...` / `?room=...&bed=...&limit=...`。
- room/bed 统一规范化：小写 `r1203/b1` 写入后，`R1203/B1` 查询可命中。
- v3 上下文：授权通过时 `modalities.care_events` 返回 `{items, brief}`；未授权返回空 items，不泄露内容。

## 7. ESP32-S3 固件接口对齐说明

- Wi-Fi STA：`net_backhaul_init()` 在 NVS 配置完整（ssid/password/uid/room/bed）时启动；缺任一项仅日志提示并保留 USB CDC 采集。
- MQTT：巴法云 `bemfa.com:9501`，client_id = UID；断线自动重连（esp-mqtt 内置）。
- topic：`{room}{bed}tof1/tof2/mlx1/mlx2`，小写拼接规范化（R1203+B1 → r1203b1tof1）。
- 消息体：`{"payload_b64":"<base64>"}`，base64 内容为原始传感器 payload（ToF 完整 MaixSense 原始帧 / MLX 3072B float32），不包含 AA 55 包头；JSON 缓冲按 payload 长度动态分配（PSRAM 优先），覆盖 ~13.5KB 的 ToF base64 消息。
- USB packet 契约保持：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD...][CRC_L][CRC_H]`，CRC16-CCITT 只覆盖 payload，LEN/CRC 小端序。
- `usb_send_tof_payload()` 与 MLX 发送路径：USB CDC 输出保持不变，同时并行 MQTT 发布。
- 依赖：`main/CMakeLists.txt` REQUIRES 补齐 esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls/esp_timer；`idf_component.yml` 声明 `espressif/mqtt`（版本对齐本机离线 EIM 组件库）。

## 8. 本地测试与编译验证结果

### 修复后复跑
- `python tests\run_public_tests.py project2_task` → **全部通过**（4 个文件，compile/functional/refactored/smoke）。
- `python tools\run_debug_probe.py project2_task` → **全部通过**（`[probe] all visible diagnostic checks passed`，0 failures；voice 路径提示消失，显示已引用 current-session fetch）。
- 额外手工验证（临时库，未入库）：
  - 旧版 `care_events` 表缺列迁移：补列成功、旧行保留、ts 回填成功；
  - 无会话/未知身份/无 assurance/过期/缺 actor 的 context 请求全部 `allowed=false` 且不泄露患者/记忆/护理事件；
  - staff 会话可取 `modalities.care_events`，patient 只能读自己；
  - HTTP 层：care/events 无 Cookie 写入 401、伪造 Cookie 401、管理员 200、本机已授权会话 GET 200、未授权会话 401；
  - 混合 CSV（显式行 + 无归属行）：first/skip/默认房床三种策略按行生效。

### ESP-IDF 编译
- `python tools\run_espidf_build.py project2_task` → **构建成功**（`Build finished successfully`，产出 `build/stdpro.bin`，ESP-IDF v6.0.1，target esp32s3）。
- 期间遇到的问题与处理：`espressif/mqtt ^3.0.0` 在本机离线组件库无匹配版本（只有 1.0.0），已将对齐为 `^1.0.0` 并从 EIM 离线库解析；mqtt 1.0.0 的配置结构为 `credentials.client_id`，已按该版本 API 修正；`ESP_EVENT_ANY_ID` 需显式转换为 `esp_mqtt_event_id_t`。
- 未执行：`idf.py flash` / `idf.py monitor` / 真实 USB 枚举 / 真实 Wi-Fi/MQTT 连通 / ToF 上电时序 / MLX90640 实机读数（按任务说明不要求）。

## 9. 未验证的残留技术债与风险

- 固件仅完成编译验证：Wi-Fi/MQTT 真实连通、巴法云 broker 兼容性、大 payload（~13.5KB）实际发送、断线重连行为需实机验证。
- MLX90640/ToF 实机读数与 I2C/UART 时序未在本机验证（无硬件）。
- `esp32/testpro4/gateway.py`（固件目录内的旧版网关副本）与 `collectdata_esp32.py` 未改动，仍按原协议运行；未与新版 gateway 模块做行为对账。
- `ADMIN_AUTH_ENABLED=0` 仅用于封闭调试环境；该模式下管理类 API 不校验（保持既有降级语义），但 v3 context 的患者数据仍需会话授权。
- sleep CSV `all` 策略仅作显式调试模式，未在真实多床位部署下压测。
- 远程非本机（非 loopback）访问路径只做了代码级校验，未在双网卡/代理环境实测。
