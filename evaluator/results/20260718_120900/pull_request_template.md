# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

**public tests**：全部通过（compile / functional smoke / refactored features / gateway smoke）。

**debug probe（6 failures）**：

| 检查项 | 初始结果 |
|--------|----------|
| admin setup returns 200 | ok |
| management API rejects missing cookie | **FAIL** status=200（本机无 Cookie 仍可读 subjects） |
| management API rejects forged cookie | **FAIL** status=200（伪造 Cookie 仍可读） |
| management API accepts valid cookie | ok |
| unknown identity session is denied | **FAIL** policy.allowed=True |
| expired session is denied | **FAIL** policy.allowed=True |
| care_event write rejects missing admin cookie | **FAIL** status=404（路由缺失） |
| care_event normalizes room/bed for create and query | **FAIL** 写入小写 r1203/b1 后用 R1203/B1 查不到 |
| voice ambient session | Warning：未显式拉 session/current |

另见代码层缺陷：管理员密码可能明文入库、`get_admin_http_session` 不校验 token、睡眠 CSV `first` 策略取了 `beds[-1]`、`care_events` 缺列且无迁移、ESP Wi-Fi/MQTT 未实现。

## 修改的文件列表

### Gateway / Voice
- `gateway/auth.py` — 加盐 PBKDF2、admin 存在性、按 token hash 查会话、legacy 明文升级
- `gateway/db.py` — `care_events` 全量 schema + `ALTER` 迁移补列并回填 `ts`
- `gateway/care_events.py` — CRUD、room/bed 规范化、limit、倒序、context 摘要
- `gateway/gateway.py` — 管理鉴权收紧、session 严格门禁、care 路由、context 含 care_events
- `gateway/sleep_importer.py` — `first` 使用 `beds[0]`；按行处理有/无 room-bed
- `gateway/README.md`、`README.md`、`RK3588_TEST_GUIDE.md` — 文档同步
- `voice/voice_assistant_integrated.py` — 无 `VOICE_SESSION_ID` 时先 `GET /api/v3/session/current`

### ESP32-S3 (`esp32/testpro4`)
- `main/main.cpp` — 接入模块；USB 与 MQTT 双通道发送
- `main/protocol_packet.{h,cpp}` — USB 包头/CRC16-CCITT
- `main/device_config.{h,cpp}` — NVS、topic 小写拼接、配置完整性
- `main/mqtt_payload.{h,cpp}` — Wi-Fi STA + Bemfa MQTT + heap base64 JSON
- `main/maixsense_parser.{h,cpp}` — MaixSense 分帧
- `main/CMakeLists.txt`、`main/idf_component.yml` — wifi/netif/event/lwip/mqtt/mbedtls
- `esp32/testpro4/CHANGELOG.md` — 记录 v4.1 恢复

### 提测说明
- `project2_task/PULL_REQUEST_TEMPLATE.md`（本文件）

## 架构调整与模块设计

- 保持既有边界：`gateway.py` 只做 HTTP glue；业务在 `auth` / `care_events` / `sleep_importer` / `db`。
- care_event 不塞进 `subjects.py`。
- ESP 协议/配置/MQTT/解析从 `main.cpp` 拆出，main 保留任务与硬件 glue。
- 本机 worker 白名单：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、identity gallery/match、vision observation；**管理 API 不在白名单**。

## 安全边界及鉴权设计

1. **管理员密码**：PBKDF2-HMAC-SHA256 + 16 字节随机盐；库内只存 salt + digest；legacy 明文行登录成功后重哈希。
2. **Cookie**：只存 `secrets.token_urlsafe` 随机 token；库内 `sha256(token)`；伪造/缺失 → 401。
3. **管理 API**：有效 admin session 才可访问；本机不再“放行全部 API”。
4. **v3 context**：以下一律 `allowed=false`、敏感 modalities 为空：
   - 无 session / 无 `actor_subject_id`
   - `identity_state=unknown`（或空）
   - `assurance_level=none`（或空）
   - `expires_ts` 已过期
5. **角色**：staff/admin 可看目标患者；patient 仅本人；无 actor → 拒绝。
6. **care_event 写/读 API**：需管理员 Cookie；授权 context 才带 `modalities.care_events`。
7. **Voice**：主动拉 `session/current` 再请求 context，避免静默 ambient 漏数据或断链。

## 睡眠 CSV 无 room/bed 时的特殊处理

`sleep_importer.row_targets` **按行**决策：

| 行内容 | 行为 |
|--------|------|
| 带 room+bed | 只写匹配（或原始）床位，不受 unscoped 策略影响 |
| 无 room/bed 且设置了 `SLEEP_IMPORT_DEFAULT_ROOM/BED` | 写入指定床位 |
| 无归属 + `SLEEP_IMPORT_UNSCOPED_POLICY=first` | 写入 **第一个** 配置床位（`beds[0]`，已修掉错误的 `beds[-1]`） |
| 无归属 + `skip` | 跳过该行 |
| 无归属 + `all` | 写入全部床位（显式调试模式，非默认） |

同一 CSV 可混合有/无归属行；策略只作用于无归属行。

## care_event 实现细节

- 表字段：`event_id, subject_id, room, bed, kind, title, content, severity, source, created_by, ts, created_ts, updated_ts`
- 旧库缺列时 `PRAGMA table_info` + `ALTER TABLE ... ADD COLUMN`，`ts` 从 `created_ts` 回填，**保留旧行**
- `POST /api/v3/care/events`、`GET /api/v3/care/events?subject_id|room&bed&limit`
- room/bed 写入与查询均 `normalize_*` 为大写
- 列表默认最近 20 条，`ORDER BY COALESCE(ts, created_ts) DESC`
- 授权 context：`modalities.care_events = {items, brief}`

## ESP32-S3 固件接口对齐说明

- **USB**：`[AA 55][TYPE][ID][LEN_LE][PAYLOAD][CRC_LE]`，CRC16-CCITT 只覆盖 payload
- **ToF payload**：完整 MaixSense 原始帧（含 00 FF 头与元数据），非仅 10000B 图像
- **MQTT**：NVS 齐备时连 Wi-Fi + `mqtt://bemfa_host:port`，client_id = UID  
  Topic：`{room}{bed}tof1|tof2|mlx1|mlx2`（小写）  
  Body：`{"payload_b64":"<raw payload base64>"}`  
  大帧用堆缓冲，避免 256B 栈缓冲截断
- **配置不全**：跳过联网，USB CDC 仍工作；串口 `CFGSET` / `CFG?` / `REBOOT`
- **依赖**：`esp_wifi` / `esp_netif` / `esp_event` / `lwip` / `mqtt` / `mbedtls` 等

## 本地测试与编译验证结果

### 修复后 public tests
```text
python tests\run_public_tests.py project2_task
→ [public] all public tests passed
```
（睡眠导入日志确认 unscoped 落到 `R1203-B1`，即 first 床）

### 修复后 debug probe
```text
python tools\run_debug_probe.py project2_task
→ [probe] all visible diagnostic checks passed
→ [probe:info] voice module appears to reference current-session fetch
```
（原 6 项 FAIL 全部 ok）

### ESP-IDF 编译
```text
python tools\run_espidf_build.py project2_task
```
- 环境：Windows EIM ESP-IDF **v6.0.1**，target **esp32s3**
- 复制目录：`E:\esp\builds\modeltest\project2_task\esp32\testpro4`
- 结果：**Build finished successfully**
- 产物：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（约 0xf0070 bytes）
- 说明：未执行 flash/monitor/真机 Wi-Fi/MQTT；编译期有 field-initializer 警告，已用组件级 `-Wno-error=...` 保持可构建

## 未验证的残留技术债与风险

1. **未做真机**：ESP flash、USB 枚举、ToF 上电时序、MLX I2C 读数、真实 Wi-Fi/巴法云连通与 topic 订阅端到端。
2. **MQTT 吞吐**：ToF ~10KB 帧 base64 后更大，QoS0 在弱网下可能丢帧；未做限流/分片。
3. **care_event GET 授权细化**：当前读 API 要求管理员 Cookie；患者 actor 仅能通过已授权的 `context/chat` 拿摘要，未单独做“会话级 care GET”。
4. **隐藏/回归测试**：workspace 仅有 public smoke + debug probe；完整安全/迁移/混合 CSV 边界依赖 CI 隐藏集。
5. **admin setup 可重复**：setup 成功后 `admin_account_exists` 会挡住再次 setup；多管理员/重置流程未做。
6. **Voice/RKLLM/摄像头/板端性能**：仍需按 `RK3588_TEST_GUIDE.md` 在 RK3588 实机验证。
