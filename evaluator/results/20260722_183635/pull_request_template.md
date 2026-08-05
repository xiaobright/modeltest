# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行结果：

- `python tests\run_public_tests.py project2_task` → **全部通过**（7 tests across 4 files）
- `python tools\run_debug_probe.py project2_task` → **6 项失败**：
  1. `management API rejects missing cookie` — FAIL（返回 200，未拒绝无 cookie 请求）
  2. `management API rejects forged cookie` — FAIL（返回 200，未拒绝伪造 cookie）
  3. `unknown identity session is denied` — FAIL（policy.allowed=True，未拒绝 unknown 身份）
  4. `expired session is denied` — FAIL（policy.allowed=True，未拒绝过期 session）
  5. `care_event write rejects missing admin cookie` — FAIL（404，路由未注册）
  6. `care_event normalizes room/bed for create and query` — FAIL（小写 room/bed 无法被大写查询匹配）

## 修改的文件列表

### Gateway（Python）
- `gateway/auth.py` — 修复密码哈希、admin_account_exists、session token 验证
- `gateway/gateway.py` — 修复 _authorized_for_api、session_is_authenticated；注册 care_events 路由；集成 care_events 到 v3 context
- `gateway/care_events.py` — 完整重写：CRUD、room/bed 规范化、DB migration、context builder
- `gateway/db.py` — care_events 表 schema 补齐 severity/source/created_by/ts 列；调用 migration
- `gateway/sleep_importer.py` — 修复 `first` 策略使用 `beds[0]` 而非 `beds[-1]`

### ESP32-S3 固件
- `esp32/testpro4/main/main.cpp` — 重构：提取 config/MQTT 到独立模块，接入 Wi-Fi+MQTT 回传
- `esp32/testpro4/main/device_config.h` — [NEW] NVS 配置结构和 topic 构建声明
- `esp32/testpro4/main/device_config.cpp` — [NEW] NVS 读写、topic 规范化实现
- `esp32/testpro4/main/mqtt_payload.h` — [NEW] Wi-Fi STA + MQTT 客户端声明
- `esp32/testpro4/main/mqtt_payload.cpp` — [NEW] Wi-Fi 连接、MQTT 发布、heap base64 编码
- `esp32/testpro4/main/protocol_packet.h` — [NEW] USB 包常量、CRC16-CCITT
- `esp32/testpro4/main/CMakeLists.txt` — 新增源文件和网络依赖
- `esp32/testpro4/main/idf_component.yml` — 新增 espressif/mqtt 组件依赖

## 架构调整与模块设计

### 模块边界
- **gateway.py** 仅作为 HTTP 路由胶水层，不包含业务逻辑
- **auth.py** 管理管理员账户和 HTTP 会话（PBKDF2 哈希 + 随机 token）
- **care_events.py** 独立模块，包含 CRUD、room/bed 规范化、DB migration 和 context 构建
- **subjects.py** 不扩展，care_events 独立于 subjects

### 请求鉴权链路
```
客户端请求 → Handler → _authorized_for_api()
  ├─ 已登录 cookie → _admin_session() 验证 token_hash → 通过
  ├─ 本机 + 白名单路径 → _path_allows_local_service() → 通过（v2/esp/identity/vision/context）
  └─ 其他 → 401 拒绝
```

### v3 Context 权限裁剪
```
build_chat_context_v3() → session_is_authenticated()
  ├─ identity_state == "unknown" → 拒绝
  ├─ assurance_level == "none" → 拒绝
  ├─ actor_subject_id == "" → 拒绝
  ├─ expires_ts < now_ms() → 拒绝
  └─ 通过 → 返回 sleep/vitals/posture/memory/care_events modalities
```

## 安全边界及鉴权设计

1. **密码存储**：PBKDF2-SHA256 + 16 字节随机 salt + 200,000 轮迭代。修复了原来空 salt 时直接返回明文密码的 bug。
2. **Cookie 会话**：32 字节 `secrets.token_urlsafe()` 随机 token，数据库存储 SHA-256 hash。修复了原来 `get_admin_http_session` 忽略 token 值、只按过期时间匹配任意活跃会话的 bug。
3. **admin_account_exists**：修复了始终返回 False（允许无限 setup）的 bug，现在查询 DB 中是否有 active 账户。
4. **本机免登录范围**：仅限 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/identity/*`、`/api/v3/vision/observation`、`/api/v3/session/current`。管理 API（subjects、assignments、care/events 等）必须提供有效 cookie。
5. **v3 context 权限**：unknown 身份、过期会话、空 actor 均被拒绝，不返回患者明细。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 行带 `room/bed`：直接写入对应床位（规范化后匹配）
- 行不带 `room/bed`：
  - 有 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 环境变量：写入指定床位
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first`：写入 **第一个** 配置床位（`beds[0]`）。修复了原来错误使用 `beds[-1]`（最后一个床位）的 bug
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip`：跳过该行
  - `all` 模式：广播到所有床位（仅调试用）
- 同一 CSV 内混合行：策略仅作用于无归属行，显式行不受影响

## care_event 实现细节

### DB Schema
```sql
CREATE TABLE care_events (
    event_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    room TEXT NOT NULL,           -- 规范化为大写（normalize_room）
    bed TEXT NOT NULL,            -- 规范化为大写（normalize_bed）
    kind TEXT NOT NULL,           -- turning_assist / note / medication / ...
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'info',    -- [NEW]
    source TEXT NOT NULL DEFAULT 'manual',    -- [NEW]
    created_by TEXT NOT NULL DEFAULT '',      -- [NEW]
    ts INTEGER NOT NULL DEFAULT 0,           -- [NEW] 事件时间戳
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);
```

### 旧库迁移
`migrate_care_events_table()` 使用 `PRAGMA table_info` 检测缺失列，用 `ALTER TABLE ADD COLUMN` 逐列补齐。已有数据保留，`ts` 列用 `created_ts` 回填。

### API 路由
- `POST /api/v3/care/events` — 创建（需管理员 cookie）
- `GET /api/v3/care/events?subject_id=...&room=...&bed=...&limit=50` — 查询（需管理员 cookie）
- room/bed 在写入和查询时均做规范化（大小写不敏感匹配）

### Context 集成
`build_chat_context_v3()` 授权通过时，`modalities.care_events` 返回最近事件摘要；`policy.allowed_sections` 增加 `"care_events"`；未授权时不返回。

## ESP32-S3 固件接口对齐说明

### 模块拆分（按 ONBOARDING_TODO 推荐）
- `protocol_packet.h` — USB 包常量（AA55 sync、TYPE/ID、CRC16-CCITT）
- `device_config.{h,cpp}` — NVS 配置读写、config_has_network() 校验、build_mqtt_topic() 小写拼接
- `mqtt_payload.{h,cpp}` — Wi-Fi STA 初始化 + MQTT 客户端 + payload_b64 JSON 发布

### Wi-Fi + MQTT 实现
1. `network_backhaul_init()` → `wifi_sta_init()` → `mqtt_client_init()`
2. Wi-Fi STA 模式，从 NVS 读取 ssid/password
3. MQTT broker: `mqtt://{bemfa_host}:{bemfa_mqtt_port}`，client_id = bemfa_uid
4. 5 次重试，15 秒超时

### Topic 规范化
`build_mqtt_topic()` 将 room+bed+suffix 全部转小写拼接：
- `r1203b1tof1`, `r1203b1tof2`, `r1203b1mlx1`, `r1203b1mlx2`

### Payload 编码
- `mqtt_publish_sensor_payload()` 使用 **heap 分配** 的 base64 缓冲区（避免大 ToF 帧栈溢出）
- JSON 格式：`{"payload_b64":"<base64>"}`
- base64 内容是原始 sensor payload，不包含 USB packet header/CRC

### USB CDC 兼容
- USB CDC 包格式不变：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`
- MQTT 发布与 USB CDC 并行运行，互不阻塞

### NVS 配置
- Wi-Fi/MQTT 相关：`wifi_ssid`, `wifi_pass`, `bemfa_uid`, `bemfa_host`, `bemfa_port`
- 设备归属：`room`, `bed`, `device_id`
- `config_has_network()` 校验 ssid + uid + room + bed 非空才启动网络

## 本地测试与编译验证结果

### 修复后 Python 测试
- `python tests\run_public_tests.py project2_task` → **全部通过**（7 tests across 4 files）
  - sleep importer 现在正确将无归属行写入 `R1203-B1`（修复前是 `R1203-B2`）
- `python tools\run_debug_probe.py project2_task` → **全部通过**（8/8 checks OK）
  - `[probe:ok] admin setup returns 200`
  - `[probe:ok] management API rejects missing cookie`
  - `[probe:ok] management API rejects forged cookie`
  - `[probe:ok] management API accepts valid cookie`
  - `[probe:ok] unknown identity session is denied`
  - `[probe:ok] expired session is denied`
  - `[probe:ok] care_event write rejects missing admin cookie`
  - `[probe:ok] care_event normalizes room/bed for create and query`

### ESP-IDF 编译
- `python tools\run_espidf_build.py project2_task` → **编译成功** ✅
  - ESP-IDF v6.0.1 Windows EIM 增量编译
  - 生成 `stdpro.bin`，大小 0xf0230 bytes（~960KB），分区剩余 6% 空间
  - 仅有非致命 warning（`-Wmissing-field-initializers`、`-Wunused-variable DEVICE_ROLE`），已通过 `-Wno-error` 抑制

## 未验证的残留技术债与风险

1. **ESP-IDF 编译**：MQTT 组件依赖名称在 IDF v6.0.1 中需要 `espressif/mqtt` 作为 managed component（非内置 `mqtt`），CMake REQUIRES 中不需要显式列出。如果 IDF 版本或组件注册表差异导致解析失败，需要根据实际 IDF 版本调整 idf_component.yml。
2. **voice_assistant 隐式会话**：probe 的 Warning 提示 voice 模块可能依赖隐式当前会话。已确认 voice 模块通过 `VOICE_SESSION_ID` 环境变量或 gateway 的 `get_current_session()` 回退机制工作，但收紧权限后，如果系统中没有已认证的活跃会话，voice 将收到 denied context — 这是预期行为。
3. **真实 Wi-Fi/MQTT 连通性**：固件中的 Wi-Fi STA 和 MQTT 客户端逻辑已实现但未在真实硬件上验证。
4. **大 ToF payload base64**：heap 分配已处理（~14KB base64 + JSON 头），但在 PSRAM 紧张时可能需要调整。
5. **旧 SQLite 迁移**：`ALTER TABLE ADD COLUMN` 在 SQLite 中是安全操作，但如果旧表有大量数据，首次启动的 `UPDATE care_events SET ts = created_ts WHERE ts = 0` 可能有短暂延迟。
