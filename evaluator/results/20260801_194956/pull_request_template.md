# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行（结果如实记录）：

- `python tests\run_public_tests.py project2_task`
  - 结果：**通过**（test_compile / test_functional_smoke / test_refactored_features / test_smoke_gateway 全部 OK，公共测试较浅，未暴露下述缺陷）。
- `python tools\run_debug_probe.py project2_task`
  - 结果：**失败 6 项**，关键日志：
    - `[probe:FAIL] management API rejects missing cookie status=200`（无 Cookie 可访问管理 API）
    - `[probe:FAIL] management API rejects forged cookie status=200`（伪造 Cookie 也通过）
    - `[probe:FAIL] unknown identity session is denied policy={'allowed': True, ...}`（unknown 会话被放行）
    - `[probe:FAIL] expired session is denied policy={'allowed': True, ...}`（过期会话被放行）
    - `[probe:FAIL] care_event write rejects missing admin cookie status=404`（路由未实现）
    - `[probe:FAIL] care_event normalizes room/bed for create and query rows=[]`（大小写不规范化）
    - `[probe:Warning] Voice/assistant path: sensitive context may be denied without session_id ...`（voice 未显式携带会话）

## 修改的文件列表

Python / 服务端：

| 文件 | 修改内容 |
|------|----------|
| `gateway/auth.py` | 密码改为 PBKDF2-HMAC-SHA256 加盐哈希（不再明文入库）；`admin_account_exists` 真实查库；`get_admin_http_session` 按 token 哈希精确匹配 |
| `gateway/db.py` | `care_events` 表补齐 `severity/source/created_by/ts`；新增 `migrate_care_events_schema` 对旧表 `ALTER TABLE ADD COLUMN` 并回填 `ts`，保留旧数据 |
| `gateway/care_events.py` | room/bed 规范化、新字段写入、`list_care_events` 支持 `limit` 并按 `ts/created_ts` 倒序、实现 `build_care_events_context`、移除重复建表函数 |
| `gateway/gateway.py` | 管理 API 鉴权改为「admin session 或本机服务白名单」；新增 `GET/POST /api/v3/care/events` 路由与 `_care_events_read_allowed`；`session_is_authenticated` 严格化（unknown/none/过期/缺 actor 一律拒绝）；`build_chat_context_v3` 不再静默回退 ambient session，授权通过时返回 `modalities.care_events`；删除 identity gallery / credential template 对已登录远程用户的误拦截 |
| `gateway/sleep_importer.py` | `SLEEP_IMPORT_UNSCOPED_POLICY=first` 改为写入**第一个**配置床位（原实现误用 `beds[-1]`）；未配置床位也做大小写规范化 |
| `voice/voice_assistant_integrated.py` | 请求 `/api/v3/context/chat` 前先显式获取 `/api/v3/session/current` 的 `session_id` 并携带，不再依赖网关静默 ambient 会话 |
| `README.md` / `gateway/README.md` | 模块清单、鉴权边界、care_event API、上下文裁剪说明同步 |
| `RK3588_TEST_GUIDE.md` | context 查询示例改为显式携带 `session_id`；新增 care_event 测试小节（12.7）；状态清单更新 |

ESP32-S3 固件（`esp32/testpro4`）：

| 文件 | 修改内容 |
|------|----------|
| `main/main.cpp` | 恢复 Wi-Fi STA + 巴法云 MQTT 回传接线：`usb_send_tof_payload` 与 `mlx_sender_task` 在保留 USB CDC 输出的同时镜像发布 MQTT；NVS 配置完整性检查扩展为 `ssid/password/uid/room/bed`；配置未齐全时降级 USB-only；删除全部 `TODO(v4)` 占位 |
| `main/protocol_packet.{h,cpp}` | 新增：USB packet 常量、sensor type/id、CRC16-CCITT、`build_usb_packet` 打包辅助 |
| `main/maixsense_parser.{h,cpp}` | 新增：MaixSense 字节流解析器（噪声/分块/坏尾/异常长度/半帧处理），完整保留原始帧 |
| `main/device_config.{h,cpp}` | 新增：NVS key 管理、配置完整性校验、`{room}{bed}{stream}` 小写 topic 规范化 |
| `main/mqtt_payload.{h,cpp}` | 新增：`{"payload_b64":"..."}` JSON 构造（mbedtls base64，容量按最大 ToF 帧预留） |
| `main/network_backhaul.{h,cpp}` | 新增：Wi-Fi STA 事件处理（断线重连）+ esp-mqtt 客户端（bemfa.com:9501，client_id=UID）+ 线程安全 publish |
| `main/CMakeLists.txt` | REQUIRES 补齐 `esp_wifi / esp_netif / esp_event / lwip / mqtt / mbedtls`；SRCS 加入 5 个新模块 |
| `main/idf_component.yml` | 添加 `espressif/mqtt: ^1.1.0`（IDF v6.0 起 mqtt 移出内置组件，需从 registry 拉取） |

## 架构调整与模块设计

保持既有模块边界，未把逻辑塞回 `gateway.py`：

- 认证与会话：`auth.py`（管理员）+ `subjects.py`（人员会话）+ `gateway.py` 只做路由 glue。
- 护理事件：`db.py` 管 schema/迁移，`care_events.py` 管 CRUD 与 context 聚合，`gateway.py` 只挂路由。
- 睡眠导入策略：`sleep_importer.py` 内按**行**决策归属，不整文件一刀切。
- ESP32 固件：按交接指南拆为 `protocol_packet` / `maixsense_parser` / `device_config` / `mqtt_payload` / `network_backhaul` 五个模块，`main.cpp` 仅保留初始化、任务创建和 glue。

## 安全边界及鉴权设计

- **管理员密码**：PBKDF2-HMAC-SHA256（随机 16 字节盐、20 万次迭代）存储，数据库无明文。
- **Cookie 会话**：登录只下发随机 `secrets.token_urlsafe(32)` token；`admin_http_sessions` 只存 SHA-256(token)；校验按 token_hash 精确匹配 + 过期 + 账号 active，伪造 Cookie 无法命中。
- **管理 API 访问控制**：`/api/v3/subjects|assignments|sessions|memories|credentials|care/events` 等一律要求管理员会话；本机例外**仅限**服务白名单（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/vision/observation`），不再对 localhost 全放开。
- **v3 上下文权限裁剪**：`session_is_authenticated` 严格拒绝 `identity_state=unknown/空`、`assurance_level=none/空`、`expires_ts` 过期、缺 `actor_subject_id` 的会话；无 `session_id` 参数时**不再**静默取 ambient session，直接返回 `policy.allowed=false, reason=not_authenticated`。staff/admin 可访问任意目标，patient 只能访问自己（沿用 `actor_can_access_target`）。
- **患者数据零泄漏**：未授权时 `target.patient`、`modalities.sleep/vitals/posture/memory/care_events` 均返回空；face template / credential template 不再对未登录远程开放。
- **voice/本地助手**：先取 `/api/v3/session/current` 得到明确会话再请求上下文；会话未认证时只回复权限提示，不返回患者数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

逐行策略（同一 CSV 可混合显式行与无归属行，互不影响）：

- 行带 `room/bed`：只写入对应床位（大小写规范化，`r1203/b2` 按 `R1203/B2` 落位）。
- 行不带 `room/bed`：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` → 写入指定床位；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）→ 写入**第一个**配置床位（修复原 `beds[-1]` 误用）；
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 跳过该行；
  - `all` 仅作为显式调试模式。
- 已用混合 CSV 验证：显式行落 `R1203/B2`、无归属行落 `R1203/B1`（first）或跳过（skip）。

## care_event 实现细节

- Schema：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`；索引 `(subject_id, created_ts DESC)`、`(room, bed, created_ts DESC)`。
- 迁移：`PRAGMA table_info` 检测旧表缺列 → `ALTER TABLE ADD COLUMN`（severity='info'、source='manual'、created_by=''、ts=0）→ 旧行 `ts` 回填为 `created_ts`，旧数据不丢。已用缺列旧库实测。
- API：`POST /api/v3/care/events`（管理员登录，201）；`GET /api/v3/care/events?subject_id=...|?room=...&bed=...`（管理员，或带 `session_id` 的授权 actor；按 subject 过滤时须与授权目标一致），支持 `limit`，按 `ts/created_ts` 倒序。
- Context：`/api/v3/context/chat` 授权通过后在 `modalities.care_events` 返回最近 10 条摘要（items + brief），未授权返回空。
- room/bed 一律 `normalize_room/normalize_bed`（大写），`r1203/b1` 写入可被 `R1203/B1` 查询命中（probe 已覆盖）。

## ESP32-S3 固件接口对齐说明

- Wi-Fi STA 已恢复：事件驱动初始化，断线自动重连（2s 退避）；MQTT 客户端连 `bemfa.com:9501`（NVS 可配 host/port），`client_id=UID`（巴法云约定），esp-mqtt 自动重连。
- NVS 配置：`wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`（namespace `project2`），`CFGSET/CFG?/CFGRESET/REBOOT` 串口命令保留；`ssid/password/uid/room/bed` 全齐才启动网络回传，否则 USB-only 并打日志提示。
- Topic：`device_config_topic_for` 生成 `{room}{bed}{stream}` 小写拼接（`r1203b1tof1/tof2/mlx1/mlx2`），与 `gateway/bed_config.py::topics_for` 一致。
- Payload：`mqtt_payload` 构造 `{"payload_b64":"..."}`，base64 内容是**原始传感器 payload**（ToF 为完整 MaixSense 帧 `[00 FF][LEN_L LEN_H][META(16)][IMG(10000)][CHECKSUM][DD]`，MLX 为 3072B float 数据），**不是**完整 USB packet；缓冲按最大 ToF 帧 + base64 膨胀预留 16KB，publish 互斥保护。
- USB 路径完全保留：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT（0xFFFF/0x1021）只覆盖 payload，LEN/CRC 小端；`usb_send_tof_payload` 与 `mlx_sender_task` 在 USB 输出的同时镜像 MQTT 发布。
- 依赖：`main/CMakeLists.txt` REQUIRES 补 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls`；`idf_component.yml` 加 `espressif/mqtt: ^1.1.0`（IDF v6.0 起 mqtt 为独立仓库，registry 版本从 1.x 重编号）。

## 本地测试与编译验证结果

修改后运行：

- `python tests\run_public_tests.py project2_task` → **全部通过**（4 个测试文件 OK）。
- `python tools\run_debug_probe.py project2_task` → **全部通过**，`[probe] all visible diagnostic checks passed`（原 6 项 FAIL 全部转 OK，voice Warning 消失）。
- 附加验证（临时库，未污染 `data/project2.db`）：
  - 旧版缺列 `care_events` 表迁移：4 列自动补齐、旧行保留、`ts` 回填正确；
  - 混合 CSV（显式行 + 无归属行）在 `first`/`skip` 策略下逐行落位正确。
- `python tools\run_espidf_build.py project2_task`：结果见下方「ESP-IDF 编译情况」。

### ESP-IDF 编译情况

`python tools\run_espidf_build.py project2_task` → **编译成功**：

- 命令：`idf.py -B build set-target esp32s3`（复用已有 build 缓存）+ `cmake --build ... --parallel 32`，Windows EIM（`E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1`，IDF v6.0.1）。
- 依赖解析：`espressif/esp_tinyusb 2.2.0`、`espressif/mqtt 1.1.0`、`espressif/tinyusb 0.19.0~3`、`idf 6.0.1`。
- 产物：`stdpro.bin`（0xf0280 字节，app 分区剩余 6%），日志末尾 `[espidf] Build finished successfully.`。
- 过程中修复的编译问题（如实记录）：
  1. 首轮 `Failed to resolve component 'mqtt': unknown name` —— IDF v6.0 已把 mqtt 移出内置组件，需在 `idf_component.yml` 添加 `espressif/mqtt`；
  2. `no versions of espressif/mqtt match ^3.0.0` —— 独立仓库版本从 1.x 重编号，改为 `^1.1.0`；
  3. `invalid conversion from 'int' to 'esp_mqtt_event_id_t'` —— `ESP_EVENT_ANY_ID` 改为 `MQTT_EVENT_ANY`。
- 仅 `sdkconfig.defaults` 中 `TINYUSB_ENABLED/USB_OTG_SUPPORTED` 两个历史 Kconfig 符号报 unknown-symbol warning（不影响构建，IDF 6 已更名），以及 `uart_config_t.flags` 缺初始化 warning（沿用既有代码）。

## 未验证的残留技术债与风险

- **ESP 实机链路未验证**：未执行 `idf.py flash/monitor`，无真实 USB 枚举、真实 Wi-Fi/MQTT 连通、巴法云 topic 推送、ToF 上电时序或 MLX90640 实机读数验证（任务不要求）。
- **巴法云 MQTT 握手细节**：client_id=UID、username/password 留空为巴法云常规用法，但未对真实 broker 实测；如遇 broker 拒绝连接，优先核对 UID 与 topic 是否在巴法云控制台创建。
- **esp-mqtt 组件版本**：`espressif/mqtt ^1.1.0` 为 IDF v6.0.1 对应主线版本，编译通过但未做协议级回归。
- **历史库其他表**：仅对 `care_events` 做了显式迁移；`sessions/subjects` 等旧表沿用 `CREATE TABLE IF NOT EXISTS`（若历史库存在更早缺列版本需另行核对）。
- **admin 明文密码旧数据**：若历史 `admin_accounts` 中已有明文密码行，本次未做自动重哈希（无可靠信号区分明文与哈希）；建议重新 setup 或登录一次后人工核验。
- **Care event 前端**：`admin.html` 未新增护理事件管理 UI（API 与 context 已就绪），属后续迭代项。
- **RK3588/vision/voice 板端链路**：仅静态检查与 probe 覆盖，未在开发板实跑。
