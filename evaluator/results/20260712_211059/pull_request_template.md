# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前已按交接要求运行：

- `python tests\run_public_tests.py project2_task`
  - 结果：公开测试通过。
- `python tools\run_debug_probe.py project2_task`
  - 结果：失败 6 项。
  - 初始失败项：
    - `management API rejects missing cookie`
    - `management API rejects forged cookie`
    - `unknown identity session is denied`
    - `expired session is denied`
    - `care_event write rejects missing admin cookie`
    - `care_event normalizes room/bed for create and query`

## 修改的文件列表

- `gateway/auth.py`
- `gateway/db.py`
- `gateway/care_events.py`
- `gateway/gateway.py`
- `gateway/sleep_importer.py`
- `gateway/README.md`
- `voice/voice_assistant_integrated.py`
- `README.md`
- `RK3588_TEST_GUIDE.md`
- `esp32/NVS_CONFIG.md`
- `esp32/testpro4/README.md`
- `esp32/testpro4/main/CMakeLists.txt`
- `esp32/testpro4/main/idf_component.yml`
- `esp32/testpro4/main/main.cpp`
- `esp32/testpro4/main/device_config.cpp`
- `esp32/testpro4/main/device_config.h`
- `esp32/testpro4/main/maixsense_parser.cpp`
- `esp32/testpro4/main/maixsense_parser.h`
- `esp32/testpro4/main/mqtt_payload.cpp`
- `esp32/testpro4/main/mqtt_payload.h`
- `esp32/testpro4/main/network_backhaul.cpp`
- `esp32/testpro4/main/network_backhaul.h`
- `esp32/testpro4/main/protocol_packet.cpp`
- `esp32/testpro4/main/protocol_packet.h`
- `PULL_REQUEST_TEMPLATE.md`

## 架构调整与模块设计

- 管理员认证继续集中在 `gateway/auth.py`，HTTP glue 留在 `gateway/gateway.py`。
- SQLite schema 和兼容迁移集中在 `gateway/db.py`，补齐旧 `care_events` 表缺列时先迁移、后建索引。
- 护理事件 CRUD 与 context 摘要放入 `gateway/care_events.py`，避免继续扩大 `subjects.py`。
- Voice 显式读取 `/api/v3/session/current` 后携带 `session_id` 请求 `/api/v3/context/chat`，不依赖隐式 ambient session。
- ESP32-S3 固件拆出 `device_config`、`protocol_packet`、`maixsense_parser`、`mqtt_payload`、`network_backhaul` 模块，`main.cpp` 保留采集任务和 glue。

## 安全边界及鉴权设计

- 管理员密码使用 PBKDF2-HMAC-SHA256 加盐哈希保存；旧开发库若存在空 salt 明文 `password_hash`，仅在密码校验成功后原地升级为 salted hash。
- Cookie 仅保存随机 token，数据库只保存 token hash；`get_admin_http_session()` 现在必须按当前 Cookie token hash 精确匹配，不能再拿任意活跃 session。
- 本机服务白名单仅保留 `/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`/api/v3/session/current`、identity gallery/match 和 vision observation。
- 人员、床位、凭据、记忆、护理事件等管理类 API 即使来自本机也需要管理员 Cookie。
- v3 context 需要 recognized identity、非 none assurance、未过期、且存在 actor_subject_id；staff/admin 可查看目标患者，patient 仅可查看自己。
- 未认证或越权时，context 不返回患者详情、assignment、memory 或 care_events 内容。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 每一行独立处理归属，允许同一 CSV 混合显式 `room/bed` 行和无归属行。
- 行带 `room/bed` 时只写入该床位，并进行大小写无关匹配。
- 行不带 `room/bed` 时：
  - 若设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED`，写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` 时写入配置中的第一个床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` 时跳过。
  - `all` 仍保留为显式调试模式，不作为默认安全行为。

## care_event 实现细节

- 新增/补全 `care_events` 字段：`event_id / subject_id / room / bed / kind / title / content / severity / source / created_by / ts / created_ts / updated_ts`。
- `init_management_db()` 会迁移旧表缺失的 `severity/source/created_by/ts` 列，并保留旧数据；旧 `room/bed` 会规范化为大写。
- 新增管理接口：
  - `POST /api/v3/care/events`
  - `GET /api/v3/care/events?subject_id=...`
  - `GET /api/v3/care/events?room=...&bed=...&limit=...`
- 查询按 `ts, created_ts` 倒序，`room/bed` 查询大小写无关。
- 授权通过的 `/api/v3/context/chat` 在 `modalities.care_events` 返回最近护理事件；未授权时返回空 context，不暴露护理内容。

## ESP32-S3 固件接口对齐说明

- `esp32/testpro4` 保留 USB CDC 双通道输出：
  - CDC0：MLX90640
  - CDC1：MaixSense ToF
- USB packet 仍为 `[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`。
- CRC16-CCITT 只覆盖 payload，`LEN` 和 CRC 保持小端序。
- ToF MQTT payload 保持完整 MaixSense 原始帧，不裁剪 10000B 图像区。
- NVS 配置通过 `project2` namespace 读取：`wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`。
- Topic 由规范化后的 `{room}{bed}{kind}` 小写拼接，例如 `r1203b1tof1`、`r1203b1mlx2`。
- MQTT 使用巴法云 broker，默认 `bemfa.com:9501`，JSON 格式为 `{"payload_b64":"..."}`。
- `payload_b64` 编码的是原始传感器 payload，不是完整 USB packet。
- `usb_send_tof_payload()` 和 MLX 发送路径在保留 USB CDC 输出的同时并行调用 MQTT 发布。
- `CMakeLists.txt`/`idf_component.yml` 已补齐 `esp_wifi`、`esp_netif`、`esp_event`、`lwip`、`mqtt`、`mbedtls` 等依赖。

## 本地测试与编译验证结果

修复后已运行：

- `python -m compileall project2_task\gateway project2_task\voice`
  - 结果：通过；`voice/collect_results.py` 有既有 SyntaxWarning，不影响编译结果。
- `python tests\run_public_tests.py project2_task`
  - 结果：`[public] all public tests passed`。
- `python tools\run_debug_probe.py project2_task`
  - 结果：`[probe] all visible diagnostic checks passed`。
- 旧 SQLite 迁移小样本：
  - 结果：旧 `care_events` 缺列迁移、room/bed 规范化、旧明文管理员密码首次登录后重哈希均通过。
- `python tools\run_espidf_build.py project2_task`
  - 初次失败：`espressif/esp-mqtt` 组件名不存在。
  - 修正为 `espressif/mqtt` 后继续编译。
  - 后续失败：Wi-Fi SSID/password `snprintf` 被 `-Werror=format-truncation` 拦截。
  - 修正为边界明确的 `strncpy` 后编译通过。
  - 最终结果：ESP-IDF Windows EIM 构建成功，生成 `E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`。

## 未验证的残留技术债与风险

- 未做硬件实机测试：未验证真实 USB 枚举、ToF/MLX 上电采集、真实 I2C/UART 时序。
- 未做真实 Wi-Fi/MQTT 连通性测试：ESP-IDF 编译通过，但未验证巴法云账号、topic 实收和 gateway 端真实数据闭环。
- `sdkconfig.defaults` 仍有 ESP-IDF 6.0.1 提示的历史 Kconfig warning：`TINYUSB_ENABLED`、`USB_OTG_SUPPORTED` 为未知 symbol；当前不阻断构建。
- `voice/collect_results.py` 存在既有无效 escape SyntaxWarning；本次未改动该评测辅助脚本。
- NVS 非强安全存储，生产部署建议结合 flash encryption / NVS encryption / 每设备独立 token。
