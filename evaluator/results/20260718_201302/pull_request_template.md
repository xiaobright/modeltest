# Pull Request 提测说明

## 初始自检诊断

修改前运行：

- `python tests\run_public_tests.py project2_task`：通过，compile 1 项、functional 2 项、refactored 3 项、gateway smoke 1 项，共 7 项。
- `python tools\run_debug_probe.py project2_task`：失败 6 项。缺失/伪造 Cookie 均可访问管理 API；unknown identity 和过期 session 仍获授权；`POST /api/v3/care/events` 未接路由；care event 的 room/bed 大小写查询不一致。另有 voice 依赖 ambient session 的 warning。

## 修改的文件列表

- Gateway：`gateway/auth.py`、`gateway/db.py`、`gateway/care_events.py`、`gateway/gateway.py`、`gateway/sleep_importer.py`、`gateway/README.md`。
- Voice：`voice/voice_assistant_integrated.py`。
- ESP32-S3：`esp32/testpro4/main/main.cpp`、`main/CMakeLists.txt`、`main/idf_component.yml`；新增 `device_config.{h,cpp}`、`maixsense_parser.{h,cpp}`、`mqtt_payload.{h,cpp}`、`protocol_packet.{h,cpp}`。
- 文档：`README.md`、`RK3588_TEST_GUIDE.md`、`esp32/testpro4/README.md`、`QUICKSTART.md`、`CHANGELOG.md`、`docs/protocol.md`、本文件。

## 架构调整与模块设计

- `gateway.py` 只增加 HTTP 路由和授权 glue；护理事件 CRUD/摘要留在 `care_events.py`，schema/迁移留在 `db.py`。
- v3 context 不再静默选取当前 session，必须显式携带 `session_id`。voice 未配置固定 session 时先调用 `/api/v3/session/current`，再把取得的 ID 带入 context 请求。
- ESP 固件把 USB packet/CRC、MaixSense 流解析、NVS 配置/topic、Wi-Fi/MQTT/base64 分成独立模块；`main.cpp` 保留硬件初始化、任务和双通道发送 glue。

## 安全边界及鉴权设计

- 管理员密码使用随机 16-byte salt 和 PBKDF2-HMAC-SHA256（200000 次）；旧 seed 若曾把明文放进 `password_hash`，初始化会原地哈希后清除明文。
- Cookie 只保存 `secrets.token_urlsafe(32)` 随机 token，SQLite 只保存 SHA-256 token hash。查询严格匹配传入 token、账户状态和过期时间，伪造 token 不再命中任意活跃会话。
- 本机免 Cookie 只允许明确的 v2/ESP worker 路径和指定的 v3 context/vision/identity/session/care 服务路径；subjects、assignments、sessions、credentials 等管理 API 仍需管理员 Cookie。
- 敏感 context 要求 session 存在 actor、`identity_state=recognized`、assurance 非 none、未过期且 actor subject 有效。staff/admin 可访问目标患者，patient 只能访问自己；未授权响应不返回患者、assignment、memory、care event 或传感器明细。
- face/credential template 对本机 worker 或已认证管理员开放，远程未登录请求在通用 API 鉴权层被拒绝。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 每行独立决定归属，显式 `room/bed` 行不受无归属策略影响，支持同一 CSV 混合两类行。
- 同时设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 时，无归属行写入指定床位；否则 `first` 写入 `BEDS[0]`，`skip` 跳过，`all` 仅保留为显式调试模式。
- 修复了原实现把 `first` 错写成 `beds[-1]` 的问题。

## care_event 实现细节

- `care_events` 补齐 `severity/source/created_by/ts`，按 `ts, created_ts` 倒序并支持 subject 或规范化 room/bed 查询和 `limit`。
- 历史表启动时用 `PRAGMA table_info` 检查并 `ALTER TABLE` 补列，旧行回填 `ts=created_ts`、规范化 room/bed，不删除旧数据。
- `POST /api/v3/care/events` 仅管理员可写；GET 支持管理员，或本机调用方携带可访问目标患者的有效 session。
- 授权通过的 `/api/v3/context/chat` 返回 `modalities.care_events`；拒绝时该区域为空。

## ESP32-S3 固件接口对齐说明

- 从 NVS `project2` namespace 读取并校验 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`；缺少 ssid/password/uid/room/bed 时继续 USB，但不启动网络。
- Wi-Fi STA 使用 ESP-IDF event/netif/wifi，MQTT 使用 `espressif/mqtt` 连接 `mqtt://bemfa.com:9501`，ClientID 为 Bemfa UID；断线后由 Wi-Fi/MQTT 客户端重连。
- topic 由规范化小写 `{room}{bed}{tof|mlx}{1|2}` 生成。MQTT JSON 固定为 `{"payload_b64":"..."}`，动态分配足够缓冲，base64 只编码原始 payload，不编码 USB header/CRC。
- USB 保持 `[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 仅覆盖 payload。MLX payload 为 3072-byte float32；ToF payload 保留完整 MaixSense 原始帧，未截成 10000-byte 图像区。
- MaixSense parser 可处理前导噪声、分块/半帧、异常长度、缓冲溢出和坏尾字节。

## 本地测试与编译验证结果

- 最终 `python tests\run_public_tests.py project2_task`：通过，共 7 项。
- 最终 `python tools\run_debug_probe.py project2_task`：全部通过；missing/forged/valid Cookie、unknown/expired session、care_event 未授权写入和 room/bed 规范化均符合预期；voice 检测到 current-session 显式获取路径。
- 临时库附加检查通过：密码非明文且伪造 token 无效；旧 care schema 原地迁移并保留旧行；混合睡眠 CSV 的显式 B2 行和无归属 first/B1 行分别落床；管理员 HTTP 写 care event 后，有效 staff session 的 context 能读取对应 `modalities.care_events`。
- `python tools\run_espidf_build.py project2_task` 首轮明确失败于 `mqtt_payload.cpp` 的 `-Werror=format-truncation`；改为显式有界拷贝后重跑成功。
- ESP-IDF v6.0.1 最终生成 `stdpro.bin`，大小 `0xefed0`，最小 app 分区剩余 `0x10130`（6%）。编译仍报告既有 sdkconfig 未识别项、MLX 类型范围警告和 legacy I2C EOL 警告，但不影响本次构建成功。

## 未验证的残留技术债与风险

- 未执行 `idf.py flash/monitor`，未验证真实 ESP32-S3 USB 枚举、ToF/MLX 读数、Wi-Fi 关联、Bemfa 鉴权/topic 到达率和大 payload 长时间吞吐/背压。
- MQTT 当前按每帧动态分配 base64 JSON；构建通过，但需实机压测 4 路高频发布时的堆碎片、网络拥塞和掉线恢复。
- NVS encryption、flash encryption 和配置写入的物理确认尚未启用，真实部署前需完成设备侧安全加固。
- RK3588 摄像头、人脸阈值、RKLLM、麦克风/ASR/TTS 未在本机硬件验证。
- ESP-IDF v7 前需将 MLX90640 legacy I2C driver 迁移到 `driver/i2c_master.h`，并清理 sdkconfig 的旧符号。
