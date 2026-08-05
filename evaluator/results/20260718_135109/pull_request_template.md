# Project2 本地提测说明

## 初始自检诊断

修改前运行：

- `python tests\run_public_tests.py project2_task`：通过，4 个 public test suite 全部通过。
- `python tools\run_debug_probe.py project2_task`：失败 6 项。具体为：管理 API 接受无 Cookie 和伪造 Cookie；unknown identity session 未拒绝；过期 session 未拒绝；`POST /api/v3/care/events` 路由返回 404；care event 的 room/bed 规范化查询失败。probe 同时提示 voice 需要显式取得 session。

## 修改的文件列表

- `gateway/auth.py`
- `gateway/db.py`
- `gateway/care_events.py`
- `gateway/gateway.py`
- `gateway/subjects.py`
- `gateway/sleep_importer.py`
- `voice/voice_assistant_integrated.py`
- `esp32/testpro4/main/main.cpp`
- `esp32/testpro4/main/CMakeLists.txt`
- `esp32/testpro4/main/idf_component.yml`
- `README.md`
- `gateway/README.md`
- `RK3588_TEST_GUIDE.md`
- `esp32/testpro4/README.md`

未修改 `tests/` 或 `tools/`。

## 架构调整与模块设计

网关路由仍由 `gateway.py` 负责 glue；管理员认证和 Cookie session 保留在 `auth.py`；SQLite 建表和迁移保留在 `db.py`；护理事件 CRUD/摘要放在 `care_events.py`；人员/session 逻辑保留在 `subjects.py`；睡眠 CSV 归属继续由 `sleep_importer.py` 处理。v3 context 在授权成功时聚合 sleep、vitals、posture、memory 和 `care_events`，未授权时返回空的敏感 modality。

## 安全边界及鉴权设计

- 管理员密码使用 PBKDF2-HMAC-SHA256、随机 salt 和 200,000 次迭代保存；新建账号不写入明文密码。旧 seed 中无 salt 的记录只在一次成功登录时验证并迁移为哈希。
- Cookie 只保存随机 session token，数据库只保存 token hash；请求必须命中对应 token，伪造或过期 token 不会复用其他活动 session。
- 管理 API 和 care event 写入要求管理员 Cookie。仅 `/api/v2/*`、`/api/esp/*` 和明确的本机 worker 接口保留本机调用例外；本机来源不等于管理员身份。
- v3 context 要求 session 存在、未过期、`identity_state=recognized`、有 `actor_subject_id` 且 `assurance_level` 为 low/medium/high。未知 actor、缺少 subject、unknown identity、none assurance 和过期 session 均不返回患者明细、记忆或护理事件。
- voice 在读取敏感 context 前显式请求 `/api/v3/session/current`，并把解析出的 `session_id` 放入 context 请求，不依赖静默 ambient session。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行处理。带有 `room` 和 `bed` 的行只写入该归属，比较和写入统一规范化；没有归属的行才按以下顺序处理：显式 `SLEEP_IMPORT_DEFAULT_ROOM/BED`，或 `SLEEP_IMPORT_UNSCOPED_POLICY=first` 的第一个配置床位，或 `skip` 丢弃。`all` 仅保留为显式调试模式。混合 CSV 中显式行不会被默认策略改写，也不会因无归属行而整表丢弃。

## care_event 实现细节

新增/补齐 `care_events` 的 `severity`、`source`、`created_by`、`ts` 字段和索引。初始化通过 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` 迁移旧表，并用旧 `created_ts` 填充旧行的 `ts`，不删除历史记录。`POST /api/v3/care/events` 需要管理员登录；GET 支持 subject 或 room/bed、limit、倒序查询，也支持带授权 session 的查询。room/bed 统一大写。context 授权通过后在 `modalities.care_events` 返回最近事件摘要，未授权时保持空对象。

## ESP32-S3 固件接口对齐说明

`esp32/testpro4/main/main.cpp` 已恢复 ESP-IDF Wi-Fi STA 和 `espressif/mqtt` client。固件从 NVS `project2` namespace 读取并校验 `wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed`；配置不足时不启动网络但保留 USB 配置和采集路径。topic 由规范化的小写 `room+bed` 生成：`tof1/tof2/mlx1/mlx2`。

USB 继续使用 `[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 初值 `0xFFFF`、多项式 `0x1021`，仅覆盖 payload，长度和 CRC 均为小端。ToF 发布完整 MaixSense 原始帧，MLX 发布原始 float32 payload；MQTT 消息为 `{"payload_b64":"..."}`，Base64 不包含 USB 包头或 CRC。ToF/MLX 路径在 USB 输出之外并行镜像 MQTT。

## 本地测试与编译验证结果

修复后运行：

- `python tests\run_public_tests.py project2_task`：通过，所有 public tests 通过。
- `python tools\run_debug_probe.py project2_task`：通过，所有 visible diagnostic checks passed。
- `python tools\run_espidf_build.py project2_task`：最终通过，ESP-IDF v6.0.1 / target `esp32s3` 生成 `stdpro.elf` 和 `stdpro.bin`；应用分区检查通过，最小 app 分区剩余约 6%。

ESP 构建中仍有既有告警：`sdkconfig.defaults` 含两个 IDF 6.0 未识别旧符号，MLX 组件使用 legacy I2C driver 且有若干类型范围 warning；这些告警未阻断本次构建，未在本次任务中扩大到硬件驱动迁移。

## 未验证的残留技术债与风险

- 未执行真实 ESP32-S3 烧录、USB 枚举、Wi-Fi 连接、巴法云 MQTT 连通、ToF 冷启动时序或 MLX 实机读数验证。
- 未在 RK3588 实机验证摄像头、ASR/TTS、RKLLM、ONNXRuntime 和 voice 的长期运行；voice 的 session 获取逻辑已完成代码路径验证，但仍需板端服务联调。
- ESP-IDF 的 `sdkconfig.defaults` 旧符号和 MLX legacy I2C 警告仍需后续按 IDF 6.0 迁移指南处理。
- MQTT 大 payload 使用静态约 16 KB JSON 缓冲区，当前覆盖协议约定的 12 KB 原始 payload 上限；若未来扩大传感器帧上限，需要同步调整内存预算和 gateway 契约。
