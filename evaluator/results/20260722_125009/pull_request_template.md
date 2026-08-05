# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前：
- `python tests\run_public_tests.py project2_task` — 9 tests passed
- `python tools\run_debug_probe.py project2_task` — **6 failures**:
  - `management API rejects missing cookie` FAIL (returned 200)
  - `management API rejects forged cookie` FAIL (returned 200)
  - `unknown identity session is denied` FAIL (allowed=True)
  - `expired session is denied` FAIL (allowed=True)
  - `care_event write rejects missing admin cookie` FAIL (404 not found)
  - `care_event normalizes room/bed for create and query` FAIL (result ok, rows=[])
- `python tools\run_espidf_build.py project2_task` — **编译失败**: 变量名拼写错误 `framebuffer2` vs `frame_buffer2`

## 修改的文件列表

| 文件 | 操作 |
|------|------|
| `gateway/auth.py` | 修复: admin_account_exists / password_hash / session lookup / token hash |
| `gateway/gateway.py` | 修复: session_is_authenticated / _authorized_for_api / care_events 路由+上下文 |
| `gateway/care_events.py` | 完全重写: 完整 schema, 大小写归一化, 上下文构建, DB 迁移 |
| `gateway/db.py` | 修复: care_events 表初始 schema, 旧表迁移逻辑 |
| `gateway/sleep_importer.py` | 修复: first policy 使用 beds[0] 而非 beds[-1] |
| `voice/voice_assistant_integrated.py` | 修复: 新增 fetch_current_session 获取当前会话 identity |
| `esp32/testpro4/main/main.cpp` | 重构: 清理重复逻辑, 集成模块化组件, 启动网络回传 |
| `esp32/testpro4/main/protocol_packet.c/.h` | 新增: USB packet 常量, CRC16-CCITT, 打包辅助 |
| `esp32/testpro4/main/device_config.c/.h` | 新增: NVS 配置, room/bed 规范化, topic 生成 |
| `esp32/testpro4/main/mqtt_payload.c/.h` | 新增: JSON payload_b64 构造 |
| `esp32/testpro4/main/network_backhaul.c/.h` | 新增: Wi-Fi STA + MQTT 巴法云回传客户端 |
| `esp32/testpro4/main/CMakeLists.txt` | 更新: 新增源文件和组件依赖 |
| `esp32/testpro4/main/idf_component.yml` | 更新: 版本约束和 mqtt 依赖 |

## 架构调整与模块设计

Gateway 模块边界保持不变, 按照 architecture_notes.md 拆分:
- `auth.py` 独立负责账号/密码哈希/Cookie session
- `care_events.py` 独立负责护理事件的 CRUD + 上下文聚合
- `gateway.py` 只负责路由 glue 和辅助函数
- `voice/` 本地助手通过独立 HTTP 调用获得已授权上下文, 不直接访问 DB

ESP32-S3 固件新增四个 C 模块:
- `protocol_packet` — 包格式常量, CRC16-CCITT, 打包辅助
- `device_config` — NVS 配置读写, room/bed 大小写规范化, MQTT topic 拼接
- `mqtt_payload` — base64 + `{"payload_b64":"..."}` JSON 构造
- `network_backhaul` — Wi-Fi STA + MQTT 客户端, 发布到巴法云

## 安全边界及鉴权设计

1. **管理员密码**: 始终 pbkdf2_hmac sha256 (200k iterations) + 16B 随机 salt, 不留明文; 兼容旧库无 salt 时首次登录自动重哈希
2. **Cookie**: 仅存储 `secrets.token_urlsafe(32)` 随机 token, DB 存 sha256(token)
3. **Session 查找**: 按 `token_hash` 精确匹配 + `expires_ts >= now`, 不再回退到"任意活跃 session"
4. **管理 API 鉴权**: `_authorized_for_api` 不再对所有 `/api/` 放行本地请求, 仅对约定本机服务接口(`/api/v2/*`, `/api/esp/*`, `/api/v3/context/chat` 等)例外, `/api/v3/subjects`, `/api/v3/care/events` 等管理接口即本机也需 admin Cookie
5. **会话鉴权**: `session_is_authenticated` 拒绝 `identity_state=unknown`, `assurance_level=none`, `expires_ts` 过期, `actor_subject_id` 缺失的 session
6. **care_event 写入**: 要求 admin Cookie, 写入时 room/bed 归一化为大写
7. **care_event 查询**: room/bed 归一化处理, 保证大写查询能命中小写写入的记录
8. **患者数据隔离**: `build_chat_context_v3` 在未授权返回空 `assignment/patient`, `modalities` 也可能为空

## 睡眠 CSV 无 room/bed 时的特殊处理

按行策略, 不整文件一刀切:
- 行带 room/bed: 只写入匹配的床位(大小写不敏感匹配已配置床位)
- 行不带 room/bed: 应用策略
  - `SLEEP_IMPORT_DEFAULT_ROOM/BED` 环境变量非空时写入指定床位(最高优先级)
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` → 写入 `beds[0]`(第一个配置床位)
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` → 丢弃该行
  - `SLEEP_IMPORT_UNSCOPED_POLICY=all` → 写入所有床位(显式调试模式, 非默认)
- 同一 CSV 内可同时存在显式行与无归属行, 策略仅对无归属行生效

## care_event 实现细节

DB Schema (`care_events`):
```
event_id TEXT PRIMARY KEY
subject_id TEXT NOT NULL
room TEXT NOT NULL (归一化大写)
bed TEXT NOT NULL (归一化大写)
kind TEXT NOT NULL
title TEXT NOT NULL DEFAULT ''
content TEXT NOT NULL DEFAULT ''
severity TEXT NOT NULL DEFAULT 'info'
source TEXT NOT NULL DEFAULT 'manual'
created_by TEXT NOT NULL DEFAULT ''
ts INTEGER NOT NULL DEFAULT 0 (事件时间, 0 时使用 created_ts)
created_ts INTEGER NOT NULL
updated_ts INTEGER NOT NULL
```
索引: `idx_care_events_subject(subject_id, created_ts DESC)`, `idx_care_events_room_bed(room, bed, created_ts DESC)`, `idx_care_events_ts(ts DESC)`

迁移: `init_management_db` 与每次读写前都调用 `_migrate_care_events`/`ensure_care_events_schema`, 检查 `PRAGMA table_info` 补齐缺失列

路由:
- `POST /api/v3/care/events` — 需 admin auth
- `GET /api/v3/care/events?subject_id=&room=&bed=&limit=` — 需 admin auth, 按 `ts/created_ts` 倒序

上下文: `build_chat_context_v3` 在授权通过后将最近 5 条 care_events 摘要写入 `modalities.care_events`, 包含于 `brief` 和 `allowed_sections`

## ESP32-S3 固件接口对齐说明

恢复 Wi-Fi + MQTT 巴法云回传能力:
- Wi-Fi: STA 模式, 自动重连(最多 10 次), 等待 got_ip 15 秒超时
- MQTT: `espressif__mqtt` 1.0.0 组件, 连接 `mqtt://bemfa_host:bemfa_port`, client_id 取 `device_id` 或自动生成
- Topic: `{room_lower}{bed_lower}{stream}` 小写拼接, 符合 `gateway/bed_config.py` `topics_for()` 约定
- MQTT JSON: `{"payload_b64":"..."}` base64 内容为传感器原始 payload, 不是完整 USB packet
- USB packet: `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`, CRC16-CCITT 只覆盖 payload, LEN/CRC 小端序
- ToF payload: 保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`, 不截断 10000B
- USB CDC 输出与 MQTT 回传并行, `usb_send_tof_payload()` / `mlx_sender_task()` 同时向网络镜像
- NVS 配置校验: `config_is_complete()` 只需 room+bed, `network_network_ready()` 还需 wifi_ssid+bemfa_uid
- base64 buffer 动态计算: `mbedtls_base64_encode` 需要 `((raw_len + 2) / 3) * 4 + 1` 输出空间

依赖: `esp_wifi`, `esp_netif`, `esp_event`, `lwip`, `mqtt`, `mbedtls` (CMakeLists.txt)

## 本地测试与编译验证结果

```powershell
python tests\run_public_tests.py project2_task
# result: [public] all public tests passed
# 9 tests (compile + functional_smoke + refactored_features + smoke_gateway)

python tools\run_debug_probe.py project2_task
# result: [probe] all visible diagnostic checks passed
# 8 checks all ok + voice/current-session hint ok

python tools\run_espidf_build.py project2_task
# result: [espidf] Build finished successfully
# output_bin = E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin (0xf0190 bytes)
```

## 未验证的残留技术债与风险

1. **Wi-Fi/MQTT 实机连通**: 编译通过, 未在真实硬件验证 Wi-Fi 连接, MQTT broker 可达性, topic 发布
2. **巴法云回传端到端**: 未验证完整链路 ESP32 → 巴法云 → gateway TCP 订阅 → posture store
3. **ToF 传感器上电时序/波特率探测**: 保持原有逻辑, 未在实机验证冷启动, 自动波特率探测成功率
4. **face template 向量化**: `vision/identity_runtime` 依赖 onnxruntime + OpenCV FaceDetectorYN, 未在实机测试注册/匹配准确率
5. **RKLLM 本地推理**: `voice/voice_assistant_integrated.py` 依赖 `librkllmso.so` + RK3588 模型, 未在板端验证
6. **wifi_assistant session bridge**: voice 模块的 `fetch_current_session` 仅做获取, 并不写回, 本地操作者识别仍然依赖 vision worker 的 `identity_observation` 接口
7. **care_event 历史数据**: 若生产库旧表缺失 `ts` 列但已有 `created_ts`, 迁移会设 `ts = created_ts`, 语义正确
8. **mqtt_payload base64 buffer**: 若传感器帧超过 ~30000B (当前 ToF ~10016B + MLX 3072B, 远小于限制), buffer 可能不足
