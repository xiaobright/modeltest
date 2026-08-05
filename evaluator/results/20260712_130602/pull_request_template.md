## Pull Request: Project2 护理/睡眠联调工程修复

### 修改文件

- `gateway/auth.py` - 修复管理员账户存在性检查、密码哈希、会话查找
- `gateway/gateway.py` - 修复鉴权边界、session 认证、添加 care_event 路由和上下文集成
- `gateway/care_events.py` - 重写：补齐字段、room/bed 规范化、实现上下文构建器
- `gateway/db.py` - 添加 care_events 表缺失列的迁移逻辑
- `gateway/sleep_importer.py` - 修复 `first` 策略使用第一个床位
- `esp32/testpro4/main/main.cpp` - 恢复 Wi-Fi + MQTT 巴法云回传能力
- `esp32/testpro4/main/CMakeLists.txt` - 添加网络相关组件依赖
- `esp32/testpro4/main/idf_component.yml` - 添加 MQTT 组件依赖

### 架构设计说明

1. **管理员认证**: 密码使用 PBKDF2-HMAC-SHA256 (200k iterations) + 随机盐哈希存储；Cookie 仅保存随机 token 的 SHA-256 hash。
2. **API 鉴权**: 管理 API (`/api/v3/subjects` 等) 始终需要管理员会话，即使本机请求也不例外；仅有 worker 服务指定接口 (`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat` 等) 允许本机绕过。
3. **v3 Session 认证**: 拒绝 `identity_state=unknown`、`assurance_level=none` 和已过期的 session。
4. **care_event**: 独立模块 (`care_events.py`)，最小字段集包含 severity/source/created_by/ts，room/bed 规范化为大写写入/查询，旧表迁移补齐缺失列。
5. **Chat Context v3**: 当 `policy.allowed=true` 时包含 `modalities.care_events`，返回最近事件摘要和 brief hint。
6. **睡眠 CSV**: 按行策略处理；`first` 策略正确写入 `beds[0]`；行带 room/bed 按行写入，无归属行按策略处理。
7. **ESP32-S3**: Wi-Fi STA 初始化 + 巴法云 MQTT 客户端；base64 编码原始 payload 通过 MQTT 发布到 `{room}{bed}tof1/tof2/mlx1/mlx2` 小写 topic，JSON 格式 `{"payload_b64":"..."}`。

### 安全边界说明

- 管理员密码不以明文存储；Cookie 只存随机 token
- 远程未登录用户不能访问 management API，也不能 export credential template
- Identity gallery 和 credential template 的远程导出被拒绝 (403)
- 患者数据零泄漏：v3 session 认证失败或越权时仅返回 `policy.allowed=false` 的空 modalities
- 本机 worker 调用路径 (`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat` 等) 仍可正常调用

### care_event 实现说明

- DB: `gateway/db.py` 在 `init_management_db()` 中对旧 `care_events` 表做 `ALTER TABLE ADD COLUMN` 迁移
- 模块: `gateway/care_events.py` 放 CRUD + `build_care_events_context()`，不扩大 `subjects.py`
- 路由: `gateway/gateway.py` 仅做 glue (`POST /api/v3/care/events`, `GET /api/v3/care/events`)
- 上下文: `build_chat_context_v3()` 在 `allowed` 时调用 `build_care_events_context()` 加入 `modalities.care_events`

### ESP32-S3 固件实现说明

- USB Packet: `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`，CRC16-CCITT 仅覆盖 payload，小端序
- USB CDC 行为保持不变（MLX → CDC0, ToF → CDC1），新增 MQTT 并行镜像
- ToF payload 保持完整 MaixSense 原始帧（含头尾），不做截断
- MQTT broker 通过 NVS `ssid/password/uid/host/port` 配置；topic 使用 `{room}{bed}` 小写拼接
- base64 动态分配缓冲区（最大 32KB payload），避免占用过多静态 DRAM

### 测试与编译结果

| 脚本 | 结果 |
|------|------|
| `python tests/run_public_tests.py project2_task` | 全部通过 (5/5) |
| `python tools/run_debug_probe.py project2_task` | 全部通过 (8/8) |
| `python tools/run_espidf_build.py project2_task` | 编译成功，生成 `stdpro.bin` |

初始诊断失败项 (6项)：
1. `management API rejects missing cookie` → 已通过管理/worker 路径分离修复
2. `management API rejects forged cookie` → 已通过管理/worker 路径分离修复
3. `unknown identity session is denied` → 通过修复 `session_is_authenticated` 对 unknown state 返回 False 修复
4. `expired session is denied` → 通过添加 `expires_ts` 检查修复
5. `care_event write rejects missing admin cookie` → 添加路由后自动经过 `/api/` auth 检查
6. `care_event normalizes room/bed` → 添加 normalize_room/normalize_bed 后修复

### ESP-IDF 编译/失败情况

- 编译成功: `stdpro.bin` (0xEFD20 bytes, app 分区 6% 余量)
- 过程中遇到的编译错误:
  1. `mqtt_cfg.credentials.username` 为 `const char*`，不能使用 snprintf → 改为直接指针赋值
  2. 200KB 静态 base64 缓冲区导致 DRAM 溢出 → 改为 malloc 动态分配
  3. WiFi 配置 `snprintf` 触发 format-truncation 警告 → 改用 strncpy

### 未验证或残留技术债

- Voice/assistant 路径依赖 `session/current` 获取当前会话，收紧鉴权后若环境中无已认证的 session，voice 将无法获取敏感上下文。建议 voice worker 在启动时主动通过视觉/身份识别建立会话。
- ESP32 NVS 配置需通过串口 CFGSET 命令设置，未提供 Web 配网界面
- care_event HTTP GET 接口暂不支持组合查询（如同时按 subject_id + room），当前为 OR 逻辑分组
- `init_care_events_table()` 函数保留但未被 `init_management_db` 直接调用（迁移逻辑已整合到 db.py 中）；care_events 模块的 `_migrate_care_events_table()` 在每次写操作时作为安全网运行
