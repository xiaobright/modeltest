# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行的命令与关键结果（均在 `project2_task` 工作区内执行）：

- `python tests\run_public_tests.py project2_task`
  - 基线结果：**通过**。公开测试覆盖重构后的基本可调用性，但不覆盖下面这些安全绕过问题。
- `python tools\run_debug_probe.py project2_task`
  - 基线结果：**8 项诊断中 6 项失败**，具体问题如下：
    1. 管理类 API 缺少 Cookie 时仍返回 200（应为 401）——本地回环可绕过全部管理 API。
    2. 伪造 Cookie（随机 token）仍返回 200（应为 401）——`get_admin_http_session` 取任意活跃会话。
    3. `identity_state=unknown` 的会话被当作已认证。
    4. 已过期会话被当作已认证。
    5. 写 care_event 缺少管理员 Cookie 时返回 404（应为 401），且未做鉴权。
    6. care_event 写入成功但按 room/bed 查询返回空——`care_events` 表缺少 `severity/source/created_by/ts` 列，查询条件与写入列不一致。
- `python tools\run_espidf_build.py project2_task`
  - 基线结果：**构建失败（exit 1）**。CMake 依赖解析阶段报错：`espressif/esp_wifi / esp_netif / esp_event` 被错误地声明为组件仓库依赖；同时 `mqtt` 组件从清单中丢失（之前重写时误删），且固件此前从未带 Wi-Fi/MQTT 回传编译过。

## 修改的文件列表

**Python（gateway / voice）**

- `project2_task/gateway/auth.py` — 修掉明文密码回退、伪造 Cookie 接受、管理员存在性误判。
- `project2_task/gateway/gateway.py` — 收紧本地回环鉴权、修正会话认证判定、接入 care_event 路由与 v3 上下文。
- `project2_task/gateway/care_events.py` — 重写（create/list/build_context 真实实现）。
- `project2_task/gateway/db.py` — care_events 建表补齐列 + 向后兼容迁移。
- `project2_task/gateway/sleep_importer.py` — 修复 `first` 策略写到最后一张床的 bug。
- `project2_task/voice/voice_assistant_integrated.py` — 显式拉取当前 gateway 会话，避免静默环境会话泄露。

**ESP32-S3 固件（`esp32/testpro4/main`）**

- `protocol_packet.h` / `protocol_packet.cpp`（新增）— USB 包封装、CRC16-CCITT、MaixSense 帧标记。
- `maixsense_parser.h` / `maixsense_parser.cpp`（新增）— 健壮的 MaixSense 原始帧解析（噪声/分片/坏尾/异常长度/半帧）。
- `device_config.h` / `device_config.cpp`（新增）— NVS 读取 + 小写 topic 命名。
- `mqtt_payload.h` / `mqtt_payload.cpp`（新增）— base64 载荷封装 + MQTT 发布。
- `main.cpp`（修改）— 接入 `network_init()` 与 `publish_sensor_payload()`（ToF/MLX 回传）。
- `CMakeLists.txt`（重写）— 新增源文件；`REQUIRES esp_wifi esp_netif esp_event lwip mqtt mbedtls`。
- `idf_component.yml`（重写并修复）— 见下「ESP32-S3 固件接口对齐说明」。

**文档**

- `project2_task/README.md`、`project2_task/gateway/README.md` — 补充 care_events 模块与 API。
- `project2_task/RK3588_TEST_GUIDE.md` — 修正 ESP-IDF 构建状态说明。
- `project2_task/PULL_REQUEST_TEMPLATE.md` — 本文件。

## 架构调整与模块设计

- 护理事件从 `gateway.py` 拆出独立模块 `care_events.py`；`gateway.py` 只保留 HTTP 路由与启动流程，符合模块边界约定。
- ESP32 固件按职责拆分：`protocol_packet`（USB 帧 + CRC）、`maixsense_parser`（ToF 帧解析）、`device_config`（NVS + topic）、`mqtt_payload`（base64 + 发布）。`main.cpp` 仅做胶水：初始化网络、把 ToF/MLX 原始包通过 Bemfa MQTT 回传。
- 模块边界保持不变，未把功能重新堆回 `gateway.py`。

## 安全边界及鉴权设计

- **密码与 Cookie**：`auth.py` 删除明文密码回退分支，始终使用 PBKDF2-SHA256 + 随机 salt；管理员 Cookie 仅存随机 token，DB 中只存 `SHA-256(token)`，绝不存明文密码。
- **伪造 Cookie 拦截**：`get_admin_http_session()` 改为按 `token_hash` 精确匹配活跃且未过期会话，伪造 Cookie 直接 401。
- **本地回环不再绕过管理 API**：`gateway.py` 的 `_authorized_for_api` 原先对本地请求直接放行，现已改为仅放行显式声明的本地服务端点（`v2`、`esp`、`context/chat`、`identity/*`、`vision/observation` 等）；其余管理类 API 即使在 `127.0.0.1` 也要求管理员 Cookie。
- **会话认证判定**：`session_is_authenticated()` 现在对 `identity_state=unknown`、缺少 `assurance_level`、缺少 `actor_subject_id`、或已过期的会话返回 `False`。
- **患者数据零泄露**：v3 上下文仅在 `authenticated && authorized` 时返回 `modalities.*` 与患者/床位信息；未认证时只返回权限提示。
- **语音侧修正**：`voice_assistant_integrated.py` 显式调用 `/api/v3/session/current` 获取当前会话 id，不再依赖静默的环境会话，确保收紧鉴权后语音仍能拿到上下文，且不泄露数据。

## 睡眠 CSV 无 room/bed 时的特殊处理

- `sleep_importer.py` 修复了一个 `first` 策略 bug：原实现在「无房床字段」时实际写到了**最后一张**配置床位（`beds[-1]`），现已改为写到**第一张**配置床位（`beds[0]`），与文档约定一致。
- 逐行处理：同一 CSV 中带/不带 room-bed 的行分别处理；缺少 room/bed 的行按 `SLEEP_IMPORT_UNSCOPED_POLICY`（`first`/`skip`/`all`）回退到 `SLEEP_IMPORT_DEFAULT_ROOM/BED`，避免同一报告广播到所有床位。生产环境建议用 `skip` 或显式设置默认值。

## care_event 实现细节

- `create_care_event`：写入 `severity`/`source`/`created_by`/`ts`；对 room/bed 做归一化（去空格、统一大小写）；`severity` 仅接受白名单（`info/warning/critical`），`source` 仅接受白名单（`manual/device/voice`），避免任意字段入库。
- `list_care_events`：新增 `limit` 参数；对查询做 room/bed 归一化；按 `ts DESC, created_ts DESC` 排序。
- `build_care_events_context`：从桩实现改为真实实现，仅在已授权时构造 `items` 与 `brief`，并挂到 v3 上下文 `modalities.care_events` / `allowed_sections`，供 voice 读取近期护理事件。
- 路由：新增 `GET/POST /api/v3/care/events`（管理类，需管理员 Cookie）。
- **向后兼容迁移**：`db.py` 在初始化时通过 `PRAGMA table_info(care_events)` 检测缺失列，用 `ALTER TABLE ADD COLUMN` 补齐 `severity/source/created_by/ts`，并把旧行的 `ts` 从 `created_ts` 回填；旧数据不丢失。

## ESP32-S3 固件接口对齐说明

按 `reference/espidf_protocol_contract.md` 恢复 Wi-Fi STA + Bemfa MQTT（TCP 9501）回传：

- **USB 数据包**：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD...][CRC_L][CRC_H]`，CRC16-CCITT（init 0xFFFF, poly 0x1021）仅对 PAYLOAD 计算，LEN/CRC 小端。
- **MQTT topic**：小写 `{room}{bed}{tof1|tof2|mlx1|mlx2}`；发布 JSON `{"payload_b64":"<base64 原始传感器载荷>"}`（注意是原始传感器包，不是整包 USB 帧）。
- **NVS 配置**：命名空间 `project2`，键 `wifi_ssid / wifi_pass / bemfa_uid / bemfa_host / bemfa_port / room / bed / device_id`；`dc_is_complete()` 在 wifi+uid+room+bed 齐备前不发布。
- **MaixSense 原始帧**解析交由 `maixsense_parser`，处理噪声、分片、坏尾、异常长度、半帧。
- **构建清单修复**：`idf_component.yml` 中 `esp_wifi / esp_netif / esp_event / lwip / mbedtls` 是 IDF **内置**组件，错误地把它们声明为组件仓库依赖会导致版本解析失败，已移除；保留 `espressif/esp_tinyusb`。`mqtt` 在 IDF 6.x 中**不是**内置组件，而是托管组件 `espressif/mqtt`，已补回 `espressif/mqtt: "^1.0.0"`（与官方 6.0.1 示例一致）。CMakeLists `REQUIRES` 为 `esp_wifi esp_netif esp_event lwip mqtt mbedtls`。
- 编译期另修正：`device_config.h` 移除已废弃的 `<cstdbool>`（IDF 6 工具链 `-Werror=cpp` 下致命）；`main.cpp` 的 `SENSOR_TYPE_*` 宏与 `protocol_packet.h` 的 `constexpr`（位于 `namespace protocol`）重名冲突，改为统一使用 `protocol::SENSOR_TYPE_*`；`mqtt_event_handler` 的事件基判断改为兼容 `MQTT_EVENT_ANY` 注册方式（不再引用不存在的 `MQTT_EVENT` 宏）。

## 本地测试与编译验证结果

- `python tests\run_public_tests.py project2_task` → **全部公开测试通过**（最终）。
- `python tools\run_debug_probe.py project2_task` → **8 项诊断全部通过**：
  - 管理 API 拒绝缺 Cookie；拒绝伪造 Cookie；接受合法 Cookie；
  - unknown identity 会话被拒绝；过期会话被拒绝；
  - 写 care_event 缺管理员 Cookie 被拒（401）；care_event 写入/查询 room/bed 归一化一致；
  - voice 模块引用当前会话拉取。
- `python tools\run_espidf_build.py project2_task` → **BUILD_EXIT=0（构建成功）**。
  - 产物：`esp32/testpro4/build/stdpro.bin`（约 983 KB）。
  - 错误数：0；非致命警告：5（均为 `-Wmissing-field-initializers`，已在编译参数中 `-Wno-error`，不影响构建）。
  - 构建环境：Windows ESP-IDF EIM v6.0.1，目标 `esp32s3`，32 并行任务。

## 未验证的残留技术债与风险

- **固件未烧录真机**：ESP32 固件仅完成**本地编译成功**，未在真实 ESP32-S3 上烧录运行；Wi-Fi 联网、Bemfa MQTT 发布、NVS 读写回环等运行时行为尚未在硬件上验证，仍需上板联调。
- **非致命编译警告**：5 处 `missing-field-initializers`（`MaixSenseFrameParser::buffer_len/frames_parsed` 与 `uart_config_t::flags`），无害，后续可补 `= {0}` 清零以消警告。
- **care_event 端到端**：v3 上下文聚合 care_event 已在路由/单元层面由 probe 验证，但 voice 实际读取 `modalities.care_events` 的端到端链路未在硬件上跑过。
- **Topic 依赖 NVS 完整**：若 NVS 中 room/bed 不全，`dc_is_complete()` 会阻止发布（设计内的安全兜底），需确保烧录配置完整。
- **无 git 仓库**：本工作区不是 git 仓库，差异通过文件清单核对，而非 `git diff`；Reviewer 请按上方「修改的文件列表」逐项比对。
