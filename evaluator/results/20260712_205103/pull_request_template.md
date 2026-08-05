# Pull Request 提测说明 (Pull Request Template)

## 初始自检诊断

修改前已按交接要求运行：

- `python tests\run_public_tests.py project2_task`
  - 结果：通过。
- `python tools\run_debug_probe.py project2_task`
  - 结果：失败 6 项。
  - 关键失败：管理 API 接受缺失 Cookie、管理 API 接受伪造 Cookie、unknown identity session 可读上下文、expired session 可读上下文、care_event 写入缺少鉴权行为、care_event room/bed 归一化失败。
  - 诊断还提示 voice 不能依赖 ambient/current session 静默取上下文。

## 修改的文件列表

- `gateway/auth.py`
- `gateway/db.py`
- `gateway/care_events.py`
- `gateway/gateway.py`
- `gateway/sleep_importer.py`
- `voice/voice_assistant_integrated.py`
- `esp32/testpro4/main/main.cpp`
- `esp32/testpro4/main/CMakeLists.txt`
- `esp32/testpro4/main/idf_component.yml`
- `esp32/testpro4/main/protocol_packet.h`
- `esp32/testpro4/main/protocol_packet.cpp`
- `esp32/testpro4/main/maixsense_parser.h`
- `esp32/testpro4/main/maixsense_parser.cpp`
- `esp32/testpro4/main/device_config.h`
- `esp32/testpro4/main/device_config.cpp`
- `esp32/testpro4/main/mqtt_payload.h`
- `esp32/testpro4/main/mqtt_payload.cpp`
- `README.md`
- `gateway/README.md`
- `RK3588_TEST_GUIDE.md`
- `PULL_REQUEST_TEMPLATE.md`

## 架构调整与模块设计

- 保持 gateway 模块边界：HTTP 路由仍在 `gateway.py`，鉴权在 `auth.py`，数据库初始化/迁移在 `db.py`，护理事件在 `care_events.py`，睡眠 CSV 归属在 `sleep_importer.py`。
- `care_events.py` 负责护理事件写入、查询、room/bed 归一化、倒序 limit 查询和 v3 context 摘要生成，避免把业务逻辑堆回主路由文件。
- ESP32-S3 将协议、MaixSense 解析、NVS 配置和 MQTT payload 拆成独立模块，`main.cpp` 只负责串口、Wi-Fi、MQTT 和传感器主流程 glue code。
- voice 保持只消费 gateway 的 v3 授权上下文，不直接拼接睡眠、姿态、情绪等旧接口。

## 安全边界及鉴权设计

- 超级管理员密码改为 salted PBKDF2 hash，不再明文落库。
- HTTP 管理 Cookie 只保存随机 token；数据库保存 token hash，并校验精确 token hash、过期时间和启用状态。
- 本机免鉴权例外已收紧为采集、视觉 gallery、当前 session 和 v3 context 等明确服务接口；管理 API 和护理事件写入不再因为 localhost 自动放行。
- `/api/v3/context/chat` 对无 session、伪造 session、unknown identity、expired session、无 actor、无 assurance 的请求返回拒绝策略，不返回患者详情、记忆、生命体征或护理事件。
- voice 在没有显式 `VOICE_SESSION_ID` 时先调用 `/api/v3/session/current`，再把 session_id 带到 `/api/v3/context/chat`，避免靠隐式 ambient session 泄漏数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

- 睡眠 CSV 继续按行处理：带 `room/bed` 的行写入对应床位；无房床字段的行按无作用域策略处理。
- `SLEEP_IMPORT_UNSCOPED_POLICY=first` 修正为使用第一个配置床位 `beds[0]`，不再误用最后一个床位。
- `skip/all` 语义保持不变，生产环境仍建议设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 或使用 `skip` 避免误归属。

## care_event 实现细节

- `care_events` 表初始化兼容历史 SQLite，迁移时补齐 `severity/source/created_by/ts` 等列并尽量保留旧数据。
- `POST /api/v3/care/events` 支持写入护理事件，要求有效管理员 Cookie 或授权会话，不允许缺失 Cookie 的管理写入绕过。
- `GET /api/v3/care/events` 支持按 `room/bed` 查询并做归一化匹配，返回结果按时间倒序、limit 限制。
- `/api/v3/context/chat` 只在授权通过后把最近护理事件放入 `modalities.care_events`，未授权时不返回事件摘要。

## ESP32-S3 固件接口对齐说明

- `esp32/testpro4` 已按 `reference/espidf_protocol_contract.md` 恢复 Wi-Fi + MQTT + NVS 配置。
- NVS 读取 `ssid/password/uid/room/bed`，配置完整后自动启动 Wi-Fi STA 和 MQTT 客户端。
- topic 统一为小写 `{room}{bed}{kind}`，例如 `r1203b1tof1`、`r1203b1tof2`、`r1203b1mlx1`、`r1203b1mlx2`。
- ToF 保留 USB 输出包格式：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，长度和 CRC 均为 little-endian，CRC 只覆盖 payload。
- ToF MQTT 上传完整 MaixSense 原始帧；MLX MQTT 上传 3072 字节 float 原始 payload，均包装为 `{"payload_b64":"..."}`。
- ESP-IDF 依赖已补齐 `esp_event/esp_netif/esp_wifi/lwip/mbedtls/mqtt` 等，并修复 `-Werror=format-truncation` 构建错误。

## 本地测试与编译验证结果

修复后已运行：

- `python tests\run_public_tests.py project2_task`
  - 结果：通过全部 public tests。
- `python tools\run_debug_probe.py project2_task`
  - 结果：通过全部 visible diagnostic checks。
  - 关键输出：`[probe] all visible diagnostic checks passed`
- `python tools\run_espidf_build.py project2_task --clean-copy --set-target`
  - 结果：ESP-IDF 编译成功。
  - 输出固件：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`
  - 过程说明：首次编译曾因 MQTT 组件名和 `snprintf` 截断警告失败，已分别修正为 `espressif/mqtt: "*"` 和有界字节拷贝。

## 未验证的残留技术债与风险

- 尚未对真实 ESP32-S3 设备执行 flash、串口 monitor 和长时间运行验证。
- 尚未连接真实 Wi-Fi、巴法云 MQTT 或真实 Bemfa 账号验证云端收发。
- 尚未接入真实 ToF/MLX 传感器验证帧时序、payload 内容和带宽压力。
- 尚未在 RK3588 实机验证摄像头、麦克风、ASR、TTS、RKLLM、OpenCV 和 ONNXRuntime 的完整硬件链路。
- 人脸识别阈值、护理事件真实业务字段和多床位现场并发仍需实机/现场数据进一步校准。
