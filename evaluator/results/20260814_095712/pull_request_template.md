# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前已按要求运行：

- `../.venv/bin/python tests/run_public_tests.py project2_task`
  - 结果：`[public] all public tests passed`，4 个测试文件共 7 个用例全部通过。
- `../.venv/bin/python tools/run_debug_probe.py project2_task`
  - 结果：exit=1，共 6 项失败：
    1. `management API rejects missing cookie`：本机无 Cookie 仍返回 200。
    2. `management API rejects forged cookie`：伪造 Cookie 仍返回 200。
    3. `unknown identity session is denied`：unknown session 被放行。
    4. `expired session is denied`：过期 session 被放行。
    5. `care_event write rejects missing admin cookie`：路由 404。
    6. `care_event normalizes room/bed for create and query`：room/bed 未规范化。
  - 另有 voice/assistant ambient session 的 Warning。
- ESP-IDF：修改前曾用 Linux runner 跑过一次 baseline，当前 seed 本身可编译，但固件缺少 Wi-Fi/MQTT 回传；后续修复后重新验证见下文。

## 修改的文件列表

Gateway：

- `gateway/auth.py`：PBKDF2-SHA256 加盐哈希、DB 账号存在性判断、Cookie token hash 精确校验、旧明文密码登录时迁移。
- `gateway/db.py`：care_events 新表/旧表迁移、旧 admin 明文密码初始化时重哈希。
- `gateway/care_events.py`：完整 CRUD、字段默认值、room/bed 规范化、limit 排序、context 摘要。
- `gateway/gateway.py`：管理 API 与本机服务接口分流鉴权、care_event 路由、v3 context 严格授权与 care_events 聚合。
- `gateway/sleep_importer.py`：无 room/bed 行按行归属，`first` 改为 `beds[0]`。
- `gateway/subjects.py`：observation 不再静默返回 ambient/current session。
- `gateway/esp_store.py`：bytes_rx/crc_fail 计数在包入口统一维护。
- `voice/voice_assistant_integrated.py`：voice 先取 `/api/v3/session/current`，再显式携带 `session_id` 请求 context，不依赖 ambient session。

文档：

- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`CHANGES.md`、`esp32/NVS_CONFIG.md`、`esp32/testpro4/README.md`、`esp32/testpro4/QUICKSTART.md`、`esp32/testpro4/docs/protocol.md`、`esp32/testpro4/CHANGELOG.md`、`PULL_REQUEST_TEMPLATE.md`。

ESP32-S3 `esp32/testpro4`：

- `main/main.cpp`：恢复 Wi-Fi STA + 巴法云 MQTT，USB CDC 与 MQTT 并行发送。
- `main/protocol_packet.{h,cpp}`（新增）：USB packet 常量、CRC16-CCITT、包头/CRC 小端打包。
- `main/maixsense_parser.{h,cpp}`（新增）：MaixSense 字节流解析，处理噪声、分块、坏尾、异常长度和半帧。
- `main/device_config.{h,cpp}`（新增）：NVS `ssid/password/uid/room/bed/host/port/device_id` 读写校验，兼容旧 key。
- `main/mqtt_payload.{h,cpp}`（新增）：topic 小写拼接、按实际 base64 长度动态分配 `{"payload_b64":"..."}` JSON。
- `main/CMakeLists.txt`、`main/idf_component.yml`：补齐 `esp_wifi/esp_netif/esp_event/lwip/mbedtls/espressif__mqtt`。

## 架构调整与模块设计

保持既有模块边界：

- `gateway.py` 仅保留 HTTP glue、context 组装和路由；care_event 逻辑在 `care_events.py`，schema 在 `db.py`。
- 管理 API 鉴权统一收口在 `Handler._authorized_for_api`：有效管理员 Cookie > 明确的本机服务路径白名单 > 拒绝。
- `build_chat_context_v3` 不再从 `session_id` 缺失时回退 `get_current_session()`；voice 通过 `/session/current` 取得 session_id 后显式传入。
- ESP32 固件按协议关注点拆成 packet / parser / config / mqtt_payload 四个组件，`main.cpp` 只做任务与 glue。

## 安全边界及鉴权设计

- 管理员密码使用随机 16-byte salt + PBKDF2-SHA256（200,000 次）保存，不存明文；初始化时会重哈希早期种子可能遗留的明文 admin 行。
- Cookie 只保存 `secrets.token_urlsafe(32)` 随机 token；数据库只保存 `sha256(token)`，查询必须 `token_hash` 精确匹配且 session 未过期。
- 管理 API（subjects/assignments/memories/credentials/care_events 等）即使来自 127.0.0.1，缺少有效 Cookie 也返回 401。
- 仅以下本机服务路径允许无 Cookie 本机调用，且仍受自身 session/授权逻辑约束：
  `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/gallery`、`/api/v3/identity/match`、`/api/v3/session/current`、`/api/v3/vision/observation`。
- v3 context 仅在 `identity_state=recognized`、assurance 非空/非 none、`actor_subject_id` 存在、session 未过期且 actor subject active 时授权；staff/admin 可读目标，patient 仅本人；未授权时 patient/assignment/memory/care_events/sleep/vitals/posture 全部置空。
- face/credential template 远程导出仍保持 local-service only 限制。

## 睡眠 CSV 无 room/bed 时的特殊处理

`row_targets` 按行执行：

1. 行含 room+b：匹配配置床位后写入该床位；未在配置中则写入该行自己的（规范化）床位。
2. 行无 room/bed：优先 `SLEEP_IMPORT_DEFAULT_ROOM/BED`；否则 `first` 写入配置顺序第一个床位，`skip` 跳过，`all` 仅显式启用。
3. 同一 CSV 混合显式/无归属行时，只对无归属行应用默认策略，显式行不会被改床或丢弃。

## care_event 实现细节

- `db.init_management_db` 显式 `PRAGMA table_info(care_events)` 检查并 `ALTER TABLE` 补齐 `severity/source/created_by/ts`，旧行回填默认值并保留；旧 lowercase room/bed 会统一迁移为 uppercase。
- `care_events.create_care_event`：规范化 room/bed，生成 event_id，支持 `ts/created_ts/updated_ts`，默认 severity=info、source=manual、created_by 可空。
- `care_events.list_care_events`：支持 `subject_id`、`room+bed`、`limit`，按 `ts DESC, created_ts DESC` 返回。
- 路由：`POST /api/v3/care/events`（管理员 Cookie），`GET /api/v3/care/events`（管理员 Cookie）。
- 授权通过的 `build_chat_context_v3` 在 `modalities.care_events` 返回最近事件摘要，并在 `allowed_sections` 标记 `care_events`。

## ESP32-S3 固件接口对齐说明

- NVS：主 key 为 `ssid/password/uid/room/bed`，兼容读取旧 `wifi_ssid/wifi_pass/bemfa_uid` 等；配置不完整时仅 USB CDC 工作，补齐并 `REBOOT` 后启用网络。
- Wi-Fi：STA 初始化、默认 netif/event loop、断线重连。
- MQTT：broker `mqtt://bemfa.com:9501`，ClientID=巴法云 UID；启动后自动开始/重连。
- Topic：`{room}{bed}tof1/tof2/mlx1/mlx2` 全小写自动拼接。
- MQTT 消息：`{"payload_b64":"<base64(raw payload)>"}`；base64 编码的是传感器原始 payload，不是 USB packet。缓冲区按 mbedtls 计算出的实际长度动态分配，避免 ToF 大帧 256B 固定缓冲溢出。
- USB packet 契约保持：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`，LEN/CRC 小端，CRC16-CCITT(0xFFFF/0x1021) 只覆盖 payload。
- ToF payload 发送完整 MaixSense 原始帧 `[00 FF] [LEN] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`；MLX payload 为 768 个 float32 原始 3072 字节。

## 本地测试与编译验证结果

修复后最终运行：

- `../.venv/bin/python tests/run_public_tests.py project2_task`
  - exit=0，`[public] all public tests passed`。
- `../.venv/bin/python tools/run_debug_probe.py project2_task`
  - exit=0，全部 `[probe:ok]`，voice 路径显示 `session/current` 已接入。
- `../.venv/bin/python tools/run_espidf_linux_build.py project2_task`
  - exit=0，`[espidf] Build finished successfully`。
  - ESP-IDF v6.0，target esp32s3；`stdpro.bin` 0xef390 bytes，最小 app 分区 0x100000，剩余约 7%。
  - 未执行 `flash` 或 `monitor`。

额外手工验证（临时 SQLite）：

- 管理员 password_hash 与 salt 为 PBKDF2 密文，登录成功；伪造/缺失 Cookie 401，有效 Cookie 200。
- legacy care_events 旧表缺列迁移后旧行保留，lowercase 查询 uppercase 命中。
- legacy 明文 admin 行初始化后重哈希，原密码仍可登录。
- v3 context：no-session/unknown/expired/越权患者均 denied；staff/本人允许且 care_events 摘要存在。

## 未验证的残留技术债与风险

- 未做真实硬件验证：真实 Wi-Fi 连接、巴法云 MQTT 收发、USB 枚举、ToF 上电时序、MLX90640 实机读数均未实测。
- 未运行 Windows EIM `tools/run_espidf_build.py`；本机已用 Linux runner 完整编译通过，Windows 路径仍需按环境实跑。
- 固件 app 分区剩余约 7%，功能可编译但后续新增功能应关注 flash 余量。
- Bemfa 云到 gateway 的实网数据链路、真实 topic 订阅和姿态 set 完整性未做硬件联调。
- 旧库其它表若存在未在本次范围内的缺列/损坏，仍需人工巡检；本次自动迁移重点是 `care_events` 与旧 admin 明文。
