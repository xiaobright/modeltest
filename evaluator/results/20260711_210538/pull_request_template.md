# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前运行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

结果：

- `run_public_tests.py`：**全部通过**（compile / functional smoke / refactored features / gateway smoke）
- `run_debug_probe.py`：**6 项 FAIL**
  1. management API rejects missing cookie（本机无 Cookie 仍返回 200 + subjects）
  2. management API rejects forged cookie（伪造 Cookie 仍返回 200）
  3. unknown identity session is denied（`identity_state=unknown` 仍 `allowed=True`）
  4. expired session is denied（过期 session 仍 `allowed=True`）
  5. care_event write rejects missing admin cookie（路由 404）
  6. care_event normalizes room/bed for create and query（`r1203/b1` 写入后 `R1203/B1` 查不到）
  - 附加 Warning：voice 未主动取 `session/current`，收紧权限后可能拿不到上下文

## 修改的文件列表

### Gateway / 业务

- `gateway/auth.py` — 密码强制加盐哈希；Cookie token 精确匹配；`admin_account_exists` 查库
- `gateway/db.py` — care_events 创建与迁移接入 `init_management_db`
- `gateway/care_events.py` — 完整字段、room/bed 规范化、limit/倒序、上下文摘要、旧表列迁移
- `gateway/gateway.py` — 管理 API 鉴权收紧；session 认证语义；care_event 路由；context 聚合 care_events
- `gateway/sleep_importer.py` — `first` 策略改为第一个配置床位；按行处理保留显式 room/bed
- `gateway/README.md`、`README.md`、`RK3588_TEST_GUIDE.md` — 同步鉴权/care_event/睡眠策略说明

### Voice

- `voice/voice_assistant_integrated.py` — `fetch_current_session` / `resolve_voice_session_id`，取上下文前补 session_id

### ESP32-S3 (`esp32/testpro4`)

- `main/protocol_packet.{h,cpp}` — USB packet 常量、CRC16-CCITT、header/CRC 辅助
- `main/maixsense_parser.{h,cpp}` — MaixSense 流解析（噪声/半帧/坏尾）
- `main/device_config.{h,cpp}` — NVS 配置完整性、topic 小写拼接
- `main/mqtt_payload.{h,cpp}` — `{"payload_b64":...}` 堆分配构造与 topic 选择
- `main/network_uplink.{h,cpp}` — Wi-Fi STA + 巴法云 MQTT 生命周期与发布
- `main/main.cpp` — 接入模块；USB 并行 MQTT；NVS 配置驱动网络
- `main/CMakeLists.txt`、`main/idf_component.yml` — `esp_wifi/esp_netif/esp_event/lwip/mbedtls` + `espressif/mqtt`

### 提测说明

- `PULL_REQUEST_TEMPLATE.md`（本文件）

## 架构调整与模块设计

- 保持既有边界：`gateway.py` 只做 HTTP glue；鉴权在 `auth.py`；护理事件在 `care_events.py`；睡眠归属在 `sleep_importer.py`。
- ESP 固件将协议/配置/MQTT JSON 从 `main.cpp` 拆出，`main.cpp` 保留硬件初始化、任务与 glue。
- 管理 API 与本机 worker 例外路径分离：loopback 不能替代 Cookie。

## 安全边界及鉴权设计

1. **管理员密码**：PBKDF2-HMAC-SHA256 + 随机 salt；Cookie 仅随机 token；DB 存 `token_hash`。
2. **管理 API**：无 Cookie / 伪造 Cookie → 401；有效 Cookie → 200。loopback 不再放行 `/api/v3/subjects` 等管理接口。
3. **本机 worker 白名单**：`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`identity/gallery|match`、`vision/observation`、`session/current`。
4. **v3 context**：以下视为未认证，不返回患者明细/记忆/护理事件  
   - `identity_state=unknown`  
   - `assurance_level=none` 或空  
   - 缺少 `actor_subject_id`  
   - `expires_ts` 已过期  
5. staff/admin 可访问任意目标患者；patient 仅本人。
6. face/credential template 仍限制本机导出。

## 睡眠 CSV 无 room/bed 时的特殊处理

按**行**策略（同一文件可混合有/无归属行）：

| 条件 | 行为 |
|------|------|
| 行含 room/bed | 只写入匹配床位（大小写不敏感规范化） |
| 无归属 + `SLEEP_IMPORT_DEFAULT_ROOM/BED` | 写入指定床位 |
| 无归属 + `UNSCOPED_POLICY=first` | 写入**第一个**配置床位（修复了误用最后一个的 bug） |
| 无归属 + `skip` | 跳过该行 |
| `all` | 仅显式调试，非默认 |

## care_event 实现细节

- 表字段：`event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts`
- 旧库缺列：`ALTER TABLE` 补齐，`ts` 从 `created_ts` 回填，旧行保留
- API：
  - `POST /api/v3/care/events`（需管理员 Cookie）
  - `GET /api/v3/care/events?subject_id=...` 或 `room&bed`，`limit` 倒序
- room/bed 写入/查询统一 `normalize_room/bed`（大写）
- 授权通过的 `/api/v3/context/chat` 在 `modalities.care_events` 返回摘要

## ESP32-S3 固件接口对齐说明

- **USB packet**：`[AA 55][TYPE][ID][LEN_LE][PAYLOAD][CRC_LE]`，CRC16-CCITT 仅覆盖 payload
- **ToF payload**：完整 MaixSense 原始帧（含 meta/img/checksum/tail），非仅 10000B 图像区
- **MQTT**：巴法云 `bemfa.com:9501`，client_id = NVS `bemfa_uid`
- **Topic**：小写 `{room}{bed}tof1|tof2|mlx1|mlx2`
- **JSON**：`{"payload_b64":"<base64 raw payload>"}`，堆分配避免固定 256B 缓冲溢出
- **NVS namespace `project2`**：`wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`
- 网络就绪条件：ssid + uid + room + bed；不完整时仅 USB，不阻断采集

## 本地测试与编译验证结果

修复后再次运行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
python tools\run_espidf_build.py project2_task
```

| 命令 | 结果 |
|------|------|
| `run_public_tests.py` | **全部通过** |
| `run_debug_probe.py` | **all visible diagnostic checks passed**（0 FAIL）；voice 路径显示已引用 current-session fetch |
| `run_espidf_build.py` | **Build finished successfully**；产物 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`（约 0xeff50 bytes） |

构建环境：Windows EIM ESP-IDF v6.0.1，target `esp32s3`。未执行 flash/monitor。

## 未验证的残留技术债与风险

1. **未做实机验证**：ESP32 Wi-Fi 连通、巴法云 MQTT 在线、ToF 上电时序、MLX90640 实机温度、USB 枚举。
2. **大 payload MQTT**：ToF 完整帧 base64 JSON 较大，依赖 MQTT out buffer（16384）与 QoS0；弱网下丢包/分片未压测。
3. **管理员 Cookie 范围**：`/api/v3/beds` 等也需 Cookie；浏览器需完成 login 后再调管理 API。
4. **voice 依赖 session 质量**：若 vision 未建立 recognized session，助手仍会拿不到敏感上下文（符合安全设计，需联调确认 UX）。
5. **历史明文密码账户**：登录成功时会迁移为加盐哈希；未登录前旧明文行仍可能短暂存在。
6. **隐藏/私有测试集**：公开 smoke 与 debug probe 通过，不保证隐藏评测全覆盖。
7. CMake 提示 IDF 内置 `components/mqtt` 无 CMakeLists；实际使用 component manager `espressif/mqtt`，增量构建已成功。
