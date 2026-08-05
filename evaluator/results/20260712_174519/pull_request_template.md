# Project2 提测说明

## 初始自检诊断

修改前已运行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

公共测试通过，但 debug probe 发现 6 项问题：管理 API 接受缺失 Cookie、管理 API 接受伪造 Cookie、`identity_state=unknown` session 仍获得 context、过期 session 仍获得 context、未登录护理事件写入路由缺失（404）、以及小写 room/bed 写入后无法由大写查询命中。

## 修改文件

- Gateway：`gateway/auth.py`、`gateway/db.py`、`gateway/care_events.py`、`gateway/sleep_importer.py`、`gateway/gateway.py`。
- Voice/启动：`voice/voice_assistant_integrated.py`、`start_project.py`。
- ESP32-S3：`esp32/testpro4/main/CMakeLists.txt`、`idf_component.yml`、`main.cpp`，新增 `device_config.*`、`protocol_packet.*`、`mqtt_payload.*`、`network_backhaul.*`。
- 文档：根 `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`esp32/testpro4/README.md`。

## 架构调整

管理员账户、密码哈希和 HTTP token 校验仍归 `auth.py`；DB schema/migration 归 `db.py`；护理事件的规范化、持久化、排序和 context 摘要归 `care_events.py`；`gateway.py` 只增加 HTTP glue、授权检查和 context 聚合。ESP32 将配置完整性、USB 包 CRC、MQTT JSON 编码和网络状态分别放入独立模块，`main.cpp` 保留硬件初始化、USB 输出和任务 glue。

## 安全边界

- 管理员密码用随机盐 PBKDF2-HMAC-SHA256（200,000 iterations）保存；登录采用常量时间摘要比较。Cookie 仅保存随机 token，SQLite 仅保存 token SHA-256；查询会精确匹配 token hash，伪造 token 不能命中任意有效会话，认证状态响应也不回传 token hash。
- 本机例外仅保留既有 v2/ESP 采集、identity gallery/match、vision observation 和 context 服务路径。subjects、assignments、credentials、sessions、memories 和 care events 等管理 API 即使由 loopback 请求也要求管理员 Cookie。首次管理员 setup 限制为 loopback。
- v3 敏感 context 必须携带 `session_id` 与目标范围；不再回退到最近 session。只有 actor subject 存在、session 未过期、`identity_state=recognized` 且 assurance 不为 `none` 时才认证。staff/admin 可访问患者，patient 仅可访问本人；拒绝结果清空患者、assignment、sleep、vitals、posture、memory 和 care_events。
- voice 在没有 `VOICE_SESSION_ID` 时本地返回未认证策略，不请求 gateway 猜测当前会话；启动参数和 RK3588 文档已同步。

## 睡眠 CSV 归属

有 `room/bed` 的行逐行写入该行指定床位；无归属行优先使用 `SLEEP_IMPORT_DEFAULT_ROOM/BED`，否则按 `first` 写入第一配置床位、`skip` 跳过、`all` 仅为显式调试模式。修复了原先 `first` 错选最后床位的问题；同一 CSV 的显式行与无归属行可并存，互不覆盖。

## care_event

`care_events` 表包含 `severity`、`source`、`created_by`、`ts`，初始化会通过 `PRAGMA table_info` 和 `ALTER TABLE` 迁移旧表；旧事件保留，缺失 `ts` 回填为 `created_ts`。新增：

- `POST /api/v3/care/events`：管理员 Cookie 必需。
- `GET /api/v3/care/events?subject_id=...` 或 `?room=...&bed=...&limit=...`：管理员 Cookie 必需，按 `ts/created_ts` 倒序。
- room/bed 在创建和查询时统一为大写；授权 context 的 `modalities.care_events` 仅返回最近事件摘要。

## ESP32-S3 协议对齐

NVS 读取并校验 `ssid/password/uid/room/bed`，未完整配置时仅保留 USB CDC。完整配置时启动 Wi-Fi STA，获得 IP 后连接 `mqtt://bemfa.com:9501`（或 NVS host/port），UID 用作 MQTT client id。ToF/MLX 都保留 USB packet `[AA 55][TYPE][ID][LEN_LE][PAYLOAD][CRC16-CCITT_LE]`，CRC 只覆盖 payload。

MQTT topic 由 `room + bed + stream` 小写规范化生成（`tof1/tof2/mlx1/mlx2`）；消息是 `{"payload_b64":"..."}`。Base64 输入是原始 ToF 完整 MaixSense frame 或 3072-byte MLX payload，不包含 USB header/CRC。ToF parser 保留完整 raw frame，并增加异常长度拒绝以避免噪声帧阻塞解析。

## 最终验证

已运行并通过：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
python tools\run_espidf_build.py project2_task
```

- 最终 public tests：全部通过。
- 最终 debug probe：6 项初始失败均通过。其语音静态提示仍出现，因为脚本只搜索 `session/current`/`fetch_current_session` 文本；实际 voice 代码不使用 ambient/current session，缺少显式 ID 时返回拒绝策略。
- 补充临时 SQLite 验证：旧 care_events migration 保留历史内容并补齐列；混合 CSV 的显式 `R1203-B2` 与无归属行分别进入 `B2` 与 `first` 的 `B1`；管理员 PBKDF2 hash/Cookie、护理事件 HTTP 写读、授权 context 注入和缺失 session 的零泄漏均通过。
- ESP-IDF v6.0.1：首次构建发现 MQTT event 枚举不匹配，第二次发现固定长度 Wi-Fi 数组的 `snprintf` 截断被 `-Werror` 拒绝；均已修复。最终构建成功，产物为 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`，app 占 `0xf0470`，最小分区剩余 `0xfb90`（约 6%）。SDK 配置仍打印已有 `TINYUSB_ENABLED` / `USB_OTG_SUPPORTED` 未知符号迁移警告，但 exit code 为 0。

## 未验证风险

- 未执行 flash/monitor，未连接真实 Wi-Fi、巴法云、ToF UART、MLX90640 或 USB CDC 主机；网络重连、broker 鉴权和大 payload 在真实设备上的吞吐仍需板端联调。
- 现有 SDK defaults 的 TinyUSB Kconfig 迁移警告未在本变更中扩展处理。
- 语音、视觉和 context 的硬件/模型全链路未在 RK3588 实机验证；部署时必须由识别/会话创建方显式传入 `VOICE_SESSION_ID`。
