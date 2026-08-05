# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

### `run_public_tests.py`（修改前）

- 结果：**全部通过**（compile / functional_smoke / refactored_features / smoke_gateway）
- 说明：公开 smoke 较宽松，未覆盖鉴权/迁移/归属正确性。

### `run_debug_probe.py`（修改前）

- **failures=6**：
  1. management API rejects missing cookie → 本机无 Cookie 仍返回 200 与 subjects 列表
  2. management API rejects forged cookie → 伪造 Cookie 仍返回 200
  3. unknown identity session is denied → `identity_state=unknown` 仍 `allowed=True`
  4. expired session is denied → 过期 session 仍 `allowed=True`
  5. care_event write rejects missing admin cookie → `POST /api/v3/care/events` 返回 **404**（路由缺失）
  6. care_event normalizes room/bed for create and query → 写入 `r1203/b1` 后按 `R1203/B1` 查不到
- Warning：voice 未显式拉取 current session，收紧权限后可能断链

## 修改的文件列表

### Gateway / Auth / Sleep / Care

- `gateway/auth.py` — 管理员存在性检查、PBKDF2 加盐哈希、按 token_hash 校验 Cookie
- `gateway/db.py` — `care_events` 完整 schema、`ensure_columns` 迁移、旧行 ts 回填
- `gateway/care_events.py` — CRUD、room/bed 规范化、limit/倒序、`build_care_events_context`
- `gateway/gateway.py` — 路径级本机白名单、session 严格鉴权、care 路由、context 聚合 care_events
- `gateway/sleep_importer.py` — `first` 策略改为首个配置床位（原错误用 `beds[-1]`）
- `gateway/README.md`、`README.md`、`RK3588_TEST_GUIDE.md` — 文档同步

### Voice

- `voice/voice_assistant_integrated.py` — `fetch_current_session()` + 取 context 前带 `session_id`

### ESP32-S3 (`esp32/testpro4`)

- `main/protocol_packet.{h,cpp}` — USB 包常量、CRC16-CCITT
- `main/maixsense_parser.{h,cpp}` — MaixSense 流式帧解析
- `main/device_config.{h,cpp}` — NVS 读写、topic 小写拼接、配置完整性
- `main/mqtt_payload.{h,cpp}` — `{"payload_b64":...}` JSON、topic 选择
- `main/wifi_mqtt.{h,cpp}` — Wi-Fi STA + 巴法云 MQTT 客户端与发布
- `main/main.cpp` — 接入模块；USB 与 MQTT 并行镜像 raw payload
- `main/CMakeLists.txt` — 源文件与 `esp_wifi/esp_netif/esp_event/mqtt/mbedtls/lwip` 依赖
- `main/idf_component.yml` — `espressif/mqtt`（IDF 6 内置 mqtt 目录无 CMakeLists）

## 架构调整与模块设计

- 保持职责边界：`gateway.py` 只做 HTTP glue；auth / care_events / sleep_importer / db 各自独立。
- v3 context：`session_is_authenticated` + `actor_can_access_target` 双重门禁；通过后才填充 sleep/vitals/posture/memory/**care_events**。
- 本机服务例外为**路径白名单**（v2、esp、context/chat、session/current、identity、vision/observation），管理 API 即使本机也需 Cookie。
- ESP 固件：协议/解析/配置/MQTT payload/网络与硬件 glue 分离，main 保留任务与传感器初始化。

## 安全边界及鉴权设计

| 边界 | 行为 |
|------|------|
| 管理员密码 | PBKDF2-HMAC-SHA256（200k）+ 16B 随机盐；库中不存明文 |
| 管理 Cookie | 仅随机 token；DB 存 SHA-256(`token`)；伪造/缺失 → 401 |
| 管理 API | 需有效 Cookie；loopback 不自动放行 |
| 本机 worker | 仅白名单路径可无 Cookie 调用 |
| v3 session | 拒绝：`identity_state=unknown`、`assurance` 空/none、缺 `actor_subject_id`、`expires_ts` 已过期 |
| 目标访问 | staff/admin 可访问任意患者；patient 仅自己；无 actor → 拒绝 |
| care_event 写 | 必须管理员 Cookie |
| care_event 读 | 管理员 Cookie，或已认证且对目标有权的 session |
| face/credential template | 远程不可导出（保留原 local-only 限制） |
| 患者数据 | 未授权 context 返回空 modalities，reason=`not_authenticated` / `not_authorized_for_target` |

## 睡眠 CSV 无 room/bed 时的特殊处理

按**行**处理，不整文件一刀切：

1. 行含 room/bed → 写入匹配床位（大小写不敏感）；无配置匹配时仍按该 room/bed 写入。
2. 行无 room/bed：
   - `SLEEP_IMPORT_DEFAULT_ROOM` + `SLEEP_IMPORT_DEFAULT_BED` 均设置 → 写入默认床。
   - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → **第一个**配置床位。
   - `skip` → 跳过该行。
   - `all` → 仅调试扇出，非默认。
3. 混合 CSV：有归属行照常写入；策略只作用于无归属行。

## care_event 实现细节

- 表字段：`event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts`
- 旧库迁移：`ensure_columns` 补 `severity/source/created_by/ts`；`ts` 缺省回填 `created_ts`；旧行保留。
- `create_care_event`：`normalize_room` / `normalize_bed`（大写）。
- `list_care_events`：按 `COALESCE(NULLIF(ts,0), created_ts) DESC`，支持 `limit`。
- 路由：
  - `POST /api/v3/care/events`（admin）
  - `GET /api/v3/care/events?subject_id=...` 或 `?room=&bed=`
- Context：`modalities.care_events = {items, brief, count}`，仅 `policy.allowed=true` 时非空。

## ESP32-S3 固件接口对齐说明

| 项 | 实现 |
|----|------|
| Wi-Fi | STA，SSID/密码来自 NVS |
| MQTT | 巴法云 `mqtt://{host}:{port}`，client_id=`bemfa_uid` |
| Topic | 小写 `{room}{bed}tof1|tof2|mlx1|mlx2` |
| JSON | `{"payload_b64":"<base64 raw payload>"}`（非完整 USB 包） |
| ToF payload | 完整 MaixSense 原始帧（含 00 FF 头与尾） |
| USB | 仍发 `[AA 55][TYPE][ID][LEN_LE][PAYLOAD][CRC_LE]`，CRC 仅覆盖 payload |
| NVS | namespace `project2`：ssid/password/uid/room/bed/host/port/device_id |
| 并行 | USB CDC 与 MQTT 同时尝试；网络未配置时 USB-only |

首次编译失败点：`REQUIRES mqtt` 在 IDF 6.0.1 中目录无 CMakeLists；改为 `espressif/mqtt: ^1.0.0` 后配置与链接成功。

## 本地测试与编译验证结果

### 修复后

```powershell
python tests\run_public_tests.py project2_task
# → [public] all public tests passed

python tools\run_debug_probe.py project2_task
# → [probe] all visible diagnostic checks passed
#    voice: appears to reference current-session fetch
#    sleep first-policy 现写入 R1203-B1（首床）
```

### ESP-IDF 编译

```powershell
python tools\run_espidf_build.py project2_task
```

- 环境：Windows EIM ESP-IDF v6.0.1，`target=esp32s3`
- 首次失败：`Failed to resolve component 'mqtt'`（IDF 内置 mqtt 空壳 + 组件规则跳过）
- 修复依赖后：**Build finished successfully**
- 产物：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（约 0xf0030 bytes）
- 未执行：`idf.py flash` / `monitor` / 实机 Wi-Fi·MQTT·ToF·MLX

## 未验证的残留技术债与风险

1. **实机未验**：ESP Wi-Fi 连接、巴法云连通、ToF 冷启动/波特率、MLX I2C 读数、USB 枚举。
2. **MQTT 大包**：完整 ToF 帧 base64 约 14KB+，弱网或 broker 限制下可能丢包；QoS0、无本地重试队列。
3. **管理 API 本机不再免鉴权**：依赖 admin Cookie 的自动化脚本需更新。
4. **Voice**：依赖 gateway 已有 recognized session；无 vision 认证时 context 仍会 deny（符合安全设计）。
5. **旧明文密码账户**：历史若曾写入无盐明文，登录会失败，需重新 setup（仅新库/正确哈希路径受支持）。
6. **隐藏回归/硬件联调**：公开测试与 probe 非完备 CI；板端 RK3588 + 多床 Bemfa 端到端仍需按 `RK3588_TEST_GUIDE.md` 手工验收。
