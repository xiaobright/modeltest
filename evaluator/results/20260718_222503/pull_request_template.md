# Project2 提测说明

## 初始自检诊断

修改前已执行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

公开测试当时通过，但诊断探针有 6 项失败：缺失或伪造 Cookie 仍可访问
`/api/v3/subjects`；`identity_state=unknown` 和过期的 session 仍被 v3 context
授权；`POST /api/v3/care/events` 缺失且未认证时返回 404；直接创建的
care_event 没有规范化 room/bed，导致大小写不同的查询查不到记录。探针还提示
voice 未显式携带 session id。

## 修改的文件

- `gateway/auth.py`：修复管理员存在性查询、PBKDF2-HMAC-SHA256 加盐哈希、
  constant-time 密码比较和精确 token-hash 会话查询。
- `gateway/db.py`、`gateway/care_events.py`：增加 care_events v3 字段和旧表
  迁移，提供规范化 CRUD、limit、倒序查询和上下文摘要。
- `gateway/gateway.py`：接入 care event GET/POST 路由、严格 v3 session
  授权和受控的 loopback service 路径。
- `gateway/sleep_importer.py`：`first` 政策改为第一个配置床位；显式 room/bed
  行继续逐行保留。
- `voice/voice_assistant_integrated.py`：先读取本机 current session，再将
  session id 传给授权 context 请求。
- `esp32/testpro4/main/main.cpp`、`main/CMakeLists.txt`、`main/idf_component.yml`：
  恢复 Wi-Fi STA、MQTT 生命周期、NVS 完整配置检查和依赖。
- `esp32/testpro4/main/protocol_packet.{h,cpp}`：抽离 USB CRC16-CCITT 常量和实现。
- `esp32/testpro4/main/mqtt_payload.{h,cpp}`：按动态长度生成
  `{"payload_b64":"..."}`，并规范化 topic。
- `README.md`、`gateway/README.md`、`RK3588_TEST_GUIDE.md` 与 ESP32 README、
  protocol、changelog：同步安全边界、care event、显式 voice session 和固件协议。

## 架构与安全边界

认证仍集中在 `auth.py`，网关仅做 HTTP glue。管理员密码不以明文写库，Cookie
只携带随机 token，数据库仅保存 SHA-256 token hash。管理接口（包括人员、床位、
会话写入和 care event）必须使用有效管理员 Cookie；回环例外仅保留既有 v2/ESP
worker 接口以及 context、current session、identity/vision 服务接口。

v3 context 只有在 session 有 actor subject、`identity_state=recognized`、非空
assurance 且未过期时才认证。staff/admin 可读目标患者，patient 仅可读本人。
未授权响应不带患者、传感器、记忆或护理事件内容。voice 不依赖隐式 ambient
session，而是显式读取 current session 后传递 session id。

## 睡眠 CSV

CSV 逐行分流。带 room/bed 的行写入该行对应床位；没有 room/bed 的行先使用
`SLEEP_IMPORT_DEFAULT_ROOM/BED`，否则 `first` 只选择第一个配置床位，`skip`
跳过，`all` 仅用于显式调试。混合文件不会将显式行改写为默认床位。

## care_event

实现了 `POST /api/v3/care/events` 与 `GET /api/v3/care/events`。事件包含
`severity`、`source`、`created_by`、业务时间 `ts`，并按 `ts/created_ts` 倒序、
受 `limit` 限制。创建和查询统一规范化 room/bed。数据库初始化使用
`PRAGMA table_info` 与 `ALTER TABLE` 补齐历史表缺列，并以旧 `created_ts` 回填
`ts`，不替换或删除历史行。授权 chat context 在 `modalities.care_events` 返回近期事件。

## ESP32-S3 协议实现

NVS 读取并校验 `ssid/password/uid/room/bed`，仅完整配置时启动 Wi-Fi STA 与
MQTT。连接后以 UID 为 client id 连接 `bemfa.com:9501`（host/port 仍可由 NVS
覆盖）。topic 是小写 `{room}{bed}tof1/tof2/mlx1/mlx2`。

USB CDC 仍发送 `[AA 55][TYPE][ID][LEN_LE][PAYLOAD][CRC16_LE]`，CRC16-CCITT
只覆盖 payload。ToF MQTT 发布完整 MaixSense 原始帧，MLX 发布 3072-byte 原始
float payload；两者均只发布 payload 的 base64 JSON，绝不包含 USB header/CRC。
base64 JSON 缓冲按输入长度动态分配，避免大 ToF 帧被固定缓冲截断。

## 最终验证

已执行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
python -m py_compile project2_task\gateway\auth.py project2_task\gateway\db.py project2_task\gateway\care_events.py project2_task\gateway\sleep_importer.py project2_task\gateway\gateway.py project2_task\voice\voice_assistant_integrated.py
```

结果：公开测试全部通过；诊断探针全部通过（包括缺失/伪造 Cookie 拒绝、unknown/
expired session 拒绝、未认证 care event 拒绝、房床大小写规范化以及 voice current
session 检查）。额外临时 SQLite 断言确认历史 care_events 行被保留并回填 v3
列；混合 CSV 断言确认显式 `R1203/B2` 行保留在 B2，而无归属行只进入首个 B1。

## ESP-IDF 编译

执行了：

```powershell
python tools\run_espidf_build.py project2_task
python tools\run_espidf_build.py project2_task --clean-copy --jobs 4
```

初次增量构建因旧镜像目录的 `WinError 145` / `build.ninja` 状态失败。经确认后仅
清理了可再生镜像 `E:\esp\builds\modeltest\project2_task\esp32\testpro4`，未触碰
workspace 源码。全新 IDF 6.0.1 构建进入 `main.cpp`，发现并修复 Wi-Fi 字段
`snprintf` 的 `-Werror=format-truncation`。修复后构建目录存在 `stdpro.bin`，且
`main.cpp.obj`、`mqtt_payload.cpp.obj`、`protocol_packet.cpp.obj` 均已生成。

ESP-IDF 输出仍有已有 sdkconfig 的 unknown TinyUSB symbol 和旧 Kconfig 默认值
通知；未执行 flash、monitor 或真实 Wi-Fi/MQTT/传感器实机验证。

## 未验证风险

- 未在实际 ESP32-S3 上验证 NVS 配置、Wi-Fi 重连、巴法云连通或大帧吞吐/内存压力。
- 未做真实 USB CDC、ToF、MLX 上电采集和 MQTT 消息互操作测试。
- Windows 临时 SQLite 迁移断言通过，但解释器退出时曾打印临时文件句柄延迟清理
  警告；项目数据库和测试库未被直接删除或修改。
- 现有 `sdkconfig.defaults` 仍产生 TinyUSB/Kconfig 兼容性通知，建议作为后续
  ESP-IDF 配置整理项。
