# Project2 内部交接与开发指南 (Onboarding Guide)

你正在接手一个本地护理/睡眠联调项目。工作目录是 `project2_task/`，参考材料在 `reference/`，基础测试在 `tests/public/`。

请只依赖当前目录内可见内容完成工程实现，不要删除既有功能来绕过需求。
若历史说明文档和本交接指南有冲突，以本 `ONBOARDING_TODO.md`、`reference/` 和当前源码为准。

## 必须遵守的团队开发规范

为了保证本次 Sprint 迭代的代码质量，我们团队推型 **Pull Request 本地提测自检规范**。在提交分支合并请求前，请遵循以下闭环流程：

开始修改前，必须先在本地运行并阅读当前的自检输出：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

`run_debug_probe.py` 是团队提供的本地自检诊断脚本，会暴露当前分支的若干真实症状，例如管理 API 鉴权、session/context 权限、care_event 路由和 room/bed 规范化等问题。它不是完备的 CI 检查，不能替代最终的代码 Review 审核。

在修复 ESP32-S3 固件后，必须优先使用提供的脚本在本地或开发机进行编译，或至少运行到明确失败点：

```powershell
python tools\run_espidf_build.py project2_task

# 等价 PowerShell 入口：
powershell -ExecutionPolicy Bypass -File .\tools\run_espidf_windows_build.ps1 `
  -ProjectDir .\project2_task `
  -Target esp32s3
```

如果你的本地开发环境目前无法完成 ESP-IDF 编译，必须在 `project2_task/PULL_REQUEST_TEMPLATE.md` 中如实记录运行了什么命令、失败在哪一步、保留了哪些错误日志。请不要在 PR 说明中声称通过但实际未经验证。

完成前必须再次运行：

```powershell
python tests\run_public_tests.py project2_task
python tools\run_debug_probe.py project2_task
```

并将初始诊断、最终验证结果、未验证风险写入 `project2_task/PULL_REQUEST_TEMPLATE.md`（PR 提测说明）。
**我们的合并流水线和 Reviewer 会自动对 PR 提测说明、实际代码 diff、自检日志进行一致性交叉校验**。任何虚报通过或声称修改了不存在的辅助文件来规避 CI 的行为都将导致 PR 被直接拒绝。

## 本次 Sprint 目标

请完善 Project2，使它满足护理/睡眠 gateway 的核心工程要求：

1. 完成管理员初始化、登录、Cookie 会话和管理 API 鉴权。
2. 完成 v3 授权上下文的权限裁剪，避免未认证或越权访问泄露患者数据。
3. 完善睡眠 CSV 多床位归属策略。
4. 新增 `care_event` 护理事件能力，贯穿 DB、API、授权上下文和文档。
5. 保持旧 v2/v3 API、worker 调用路径和 ESP set 聚合接口兼容。
6. 修复并整理 `esp32/testpro4` ESP32-S3 固件，使 Wi-Fi + MQTT 巴法云回传、协议打包、NVS 配置和 gateway 契约一致。
7. 同步更新 README、gateway README、RK3588 测试说明中受影响内容，并在 `project2_task/PULL_REQUEST_TEMPLATE.md` 写明最终实现、测试和风险。

## 已知问题

不要把下面的现象当成唯一问题，它们只是第一轮调试入口：

- 管理页面能打开，但部分管理 API 在缺少或伪造 Cookie 时仍可能被本机请求访问。
- 部分 v3 session 看起来存在，但身份状态、过期时间、actor subject 语义并不可靠；请求敏感上下文时可能出现“该拒绝时仍带出患者明细”或“收紧后本地助手取不到上下文”的症状。
- `care_event` 模块已有雏形，但 DB schema、API 路由、授权、context 聚合和 room/bed 大小写一致性都需要核查。
- 睡眠 CSV 无 room/bed 时的默认归属容易写错；真实导出文件可能混合“有归属行”和“无归属行”，需要按行处理而不是整文件一刀切。
- ESP32-S3 固件当前保留 USB CDC 路径，但 Wi-Fi/MQTT/NVS/topic/base64 payload 与 `reference/espidf_protocol_contract.md` 的契约并不完整；大 payload 编码时注意缓冲与内存。
- 历史 SQLite 库可能已经存在旧版表结构（见 `data/legacy_sample.db` 样例，**测试请用临时库**），不能只考虑全新空库。
- `run_debug_probe.py` 可能打印 voice/助手路径的 Warning：收紧权限后若助手仍依赖隐式会话，护理上下文同步可能失败——请自行核查跨模块调用链。

## 关键工程约束

- 这是一个已有工程的迭代任务，不是从零写 demo。
- 需要读现有代码，遵循已有模块边界。
- 不要把所有业务逻辑塞回 `gateway/gateway.py`。
- 管理员密码不能明文存储，Cookie 只能保存随机 token，数据库保存 token hash。
- 测试必须使用临时 SQLite，不要污染 `data/project2.db`。
- 必须考虑旧 SQLite schema 的迁移：如果旧表已存在但缺列，初始化逻辑需要补齐缺失列并保留旧数据。
- 本机服务接口仍应可被本机 worker 调用：
  - `/api/v2/*`
  - `/api/esp/*`
  - `/api/v3/context/chat`
  - `/api/v3/identity/gallery`
  - `/api/v3/identity/match`
  - `/api/v3/vision/observation`
- 远程未登录用户不能访问管理 API，也不能导出 face template / credential template。
- 必须提交 `project2_task/PULL_REQUEST_TEMPLATE.md` 用作 PR 提测说明。
- 不要通过删除路由、跳过旧 API、降低鉴权要求、硬编码测试数据或修改测试脚本来绕过问题。

## care_event 开发规范

新增护理事件 `care_event`，最小字段：

```json
{
  "event_id": "care_xxx",
  "subject_id": "sub_patient_test",
  "room": "R1203",
  "bed": "B1",
  "kind": "turning_assist",
  "title": "协助翻身",
  "content": "22:10 已协助患者由仰卧调整为侧卧。",
  "severity": "info",
  "source": "manual",
  "created_by": "sub_staff_test",
  "ts": 1710000000000
}
```

推荐实现：

- `gateway/db.py`：新增 `care_events` 表和索引。
- `gateway/care_events.py`：放 CRUD，不要继续扩大 `subjects.py`。
- `gateway/gateway.py`：只放路由 glue。
- `POST /api/v3/care/events`
- `GET /api/v3/care/events?subject_id=...`
- `GET /api/v3/care/events?room=...&bed=...`
- `GET` 查询支持 `limit`，默认返回最近事件，按 `ts/created_ts` 倒序。
- `/api/v3/context/chat` 授权通过时，在 `modalities.care_events` 返回最近事件摘要；未授权时不能返回。

## 睡眠 CSV 归属策略

- 行带 `room/bed`：只写入对应床位。
- 行不带 `room/bed`：
  - 设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED` 时，写入指定床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=first` 时，写入第一个配置床位。
  - `SLEEP_IMPORT_UNSCOPED_POLICY=skip` 时跳过。
  - `all` 只作为显式调试模式，不能作为默认行为。
- 同一 CSV 内可同时出现显式 `room/bed` 行与无归属行：策略只作用于无归属行，不得误改或整表丢弃显式行。

## ESP32-S3 固件接口对齐要求

`esp32/testpro4` 是本次交付的必要部分。请阅读 `reference/espidf_protocol_contract.md`，并修复当前固件中被临时注释或未完成的 Wi-Fi + MQTT 巴法云回传能力。

主要工作目录：

```text
project2_task/esp32/testpro4/
```

最低要求：

- 恢复 Wi-Fi STA 初始化和 MQTT client 连接，MQTT broker 使用巴法云契约。
- 从 NVS 读取并校验 `ssid/password/uid/room/bed`，topic 使用规范化后的 `{room}{bed}tof1/tof2/mlx1/mlx2` 小写拼接。
- MQTT JSON 使用 `{"payload_b64":"..."}`，base64 内容是传感器原始 payload，不是完整 USB packet。
- `usb_send_tof_payload()` 和 MLX 发送路径在保留 USB CDC 输出的同时，向对应 MQTT topic发布原始 payload。
- `main/CMakeLists.txt`、`idf_component.yml` 补齐 `esp_wifi`、`esp_netif`、`esp_event`、`lwip`、`mqtt`、`mbedtls` 等依赖。
- 保持 USB packet 契约：`[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]`，CRC16-CCITT 只覆盖 payload，`LEN` 和 CRC 都是小端序。
- ToF payload 默认保持完整 MaixSense 原始帧 `[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]`，不要只发送 10000B 图像区，除非同步更新 gateway 和采集 worker 契约。

推荐的工程整理：

- `main/protocol_packet.{h,cpp}`：USB packet 常量、sensor type/id、CRC16-CCITT、打包/校验辅助。
- `main/maixsense_parser.{h,cpp}`：MaixSense 字节流解析器，能处理噪声、分块、坏尾字节、异常长度和半帧。
- `main/device_config.{h,cpp}`：NVS key、room/bed 配置完整性、topic 规范化。
- `main/mqtt_payload.{h,cpp}`：`payload_b64` JSON 构造和 topic 选择。
- `main.cpp`：保留 ESP-IDF 初始化、任务创建、硬件调用和模块 glue，避免继续堆放纯协议逻辑。

ESP-IDF Windows 编译不是硬件实机测试，但建议在提测前运行自检：

```powershell
python tools\run_espidf_build.py project2_task

# 等价 PowerShell 入口：
powershell -ExecutionPolicy Bypass -File .\tools\run_espidf_windows_build.ps1 `
  -ProjectDir .\project2_task `
  -Target esp32s3
```

本任务不要求 `idf.py flash`、`idf.py monitor`、真实 USB 枚举、真实 Wi-Fi/MQTT 连通、ToF 上电时序或 MLX90640 实机读数准确性。

## 本地单元测试

在当前开发目录下运行：

```powershell
python tests\run_public_tests.py project2_task
```

## Pull Request 提测说明应包含：

1. 修改了哪些文件。
2. 修改前运行 `run_public_tests.py` 和 `run_debug_probe.py` 的初始结果。
3. 架构设计说明。
4. 安全边界说明。
5. 睡眠 CSV 无 room/bed 时如何处理。
6. care_event 实现说明。
7. ESP32-S3 固件实现说明，包括 MQTT/USB 协议、NVS 配置、topic 和 base64 payload。
8. 运行过哪些测试和编译脚本，结果如何；ESP-IDF 未能完成时要写明原因。
9. 未验证或残留技术债。

请把同样内容写入 `project2_task/PULL_REQUEST_TEMPLATE.md`。Reviewer 会将该文件与实际 diff 记录、CI自检日志做严格的一致性检查。
