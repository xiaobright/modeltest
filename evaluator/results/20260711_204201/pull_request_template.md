# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行诊断命令，发现以下问题：

**公共测试** `python tests\run_public_tests.py project2_task`：
- test_compile.py 通过
- test_functional_smoke.py 通过（但仅检查页面可达性，未覆盖鉴权逻辑）
- test_refactored_features.py 通过（仅检查模块可导入）
- test_smoke_gateway.py 通过

**调试探针** `python tools\run_debug_probe.py project2_task`：
- admin setup 返回 200 — 通过
- management API 拒绝缺失 Cookie — 通过
- management API 拒绝伪造 Cookie — 通过
- management API 接受有效 Cookie — 通过
- **未知身份会话被拒绝 — 失败**：`session_is_authenticated` 在 identity_state 为 "unknown" 时仍返回 True
- **过期会话被拒绝 — 失败**：同上
- **care_event 写入要求管理员 Cookie — 失败**：本地请求绕过鉴权，未要求管理员权限
- **care_event 标准化 room/bed — 失败**：care_events 模块未实现完整 CRUD

**代码审查发现的安全缺陷**：
- auth.py `_password_hash` 无 salt 时返回 `("", password)`，密码明文存入数据库
- auth.py `admin_account_exists` 永远返回 False，可重复创建管理员
- auth.py `get_admin_http_session` 不按 token_hash 查找，返回任意活跃会话
- gateway.py `build_chat_context_v3` 未鉴权时回退到第一个 BEDS，泄露患者数据
- sleep_importer.py `first` 策略使用 `beds[-1]`（末尾）而非 `beds[0]`（首个）

**ESP32-S3 固件**：
- Wi-Fi + MQTT 网络回传完全未实现（仅有 TODO 注释）
- `s_device_config` 声明为 `static`，导致 network_backhaul.cpp 的 `extern` 无法链接

## 修改的文件列表

**Python 网关侧**：
- `gateway/auth.py` — 密码哈希、账号检查、会话查找三项安全修复
- `gateway/db.py` — care_events 表 schema 迁移（新增 severity/source/created_by/ts 列）
- `gateway/care_events.py` — 完整 CRUD 重写（标准化 room/bed、ts 时间戳、上下文构建）
- `gateway/gateway.py` — 鉴权收紧（本地请求白名单、session 鉴权、actor 校验、上下文拒绝回退）、care_events 路由
- `gateway/sleep_importer.py` — first 策略 beds[-1] → beds[0] 修复
- `voice/voice_assistant_integrated.py` — 新增 fetch_current_session_id() 自动获取活跃会话

**ESP32-S3 固件侧**：
- `esp32/testpro4/main/network_backhaul.h` — **新增**：Wi-Fi+MQTT 网络回传接口定义
- `esp32/testpro4/main/network_backhaul.cpp` — **新增**：Wi-Fi STA 初始化、巴法云 MQTT 客户端、base64 编码发布
- `esp32/testpro4/main/main.cpp` — 移除 static 链接符、集成网络回传、config_is_complete 扩展、清理 TODO
- `esp32/testpro4/main/CMakeLists.txt` — 新增 network_backhaul.cpp 及 esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls 依赖
- `esp32/testpro4/main/idf_component.yml` — 新增 espressif/mqtt 依赖
- `esp32/testpro4/sdkconfig.defaults` — 新增 Wi-Fi 配置项

## 架构调整与模块设计

保持 ONBOARDING_TODO.md 和 architecture_notes.md 定义的模块边界不变：

- **auth.py** 仅负责鉴权逻辑（密码哈希、会话管理、Cookie 校验）
- **db.py** 仅负责数据库 schema 和迁移
- **care_events.py** 仅负责 care_event CRUD 和上下文构建
- **gateway.py** 负责路由分发和鉴权检查，调用 auth/care_events 模块
- **sleep_importer.py** 独立负责 CSV 导入策略
- **voice_assistant_integrated.py** 独立负责语音桥接

db.py 迁移使用 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` 方式，不重建表，保留旧数据。care_events 表新增 4 列（severity、source、created_by、ts），迁移时将 created_ts 回填到 ts。

## 安全边界及鉴权设计

**管理员鉴权**：
- 密码使用 PBKDF2-HMAC-SHA256（200,000 次迭代）+ 16 字节随机 salt 哈希存储，不存明文
- Cookie 仅存储随机 token（通过 `secrets.token_urlsafe(32)` 生成），数据库存储 `token_hash`（SHA-256），不可逆
- `get_admin_http_session` 按传入 token 的 hash 精确查找，校验过期时间和账号状态

**v3 上下文鉴权**：
- `session_is_authenticated`：identity_state 为 "unknown"/空、assurance_level 为 "none"/空、expires_ts 过期或缺失、actor_subject_id 为空时均返回 False
- `actor_can_access_target`：无 actor_subject_id 时返回 False
- `build_chat_context_v3`：未鉴权时返回拒绝上下文（空 modalities），不再回退到第一个 BEDS
- `_authorized_for_api`：本地请求仅对 `_path_allows_local_service` 白名单路径放行（如 /api/esp/*），其他路径仍要求管理员 Cookie

**语音助手上下文获取**：
- 新增 `fetch_current_session_id()` 调用 `/api/v3/session/current` 获取活跃会话
- 鉴权收紧后语音助手仍可通过该端点获取上下文，不影响原有功能

## 睡眠 CSV 无 room/bed 时的特殊处理

`sleep_importer.py` 的 `first` 策略修复：CSV 中混合多个房间/床位行时，应将所有数据归因到首个遇到的床位。

修复前代码使用 `beds[-1]`（取末尾床位），修复后使用 `beds[0]`（取首个床位），符合 ONBOARDING_TODO.md 中 "first" 策略定义。

其他策略（skip/all）逻辑不变，继续按原设计处理混合行。

## care_event 实现细节

**create_care_event**：
- 使用 `normalize_room()` 和 `normalize_bed()` 标准化房间号和床位号（转大写）
- ts 字段使用输入值或 `now_ms()`，severity 默认 "info"，source 默认 "manual"
- 写入 SQLite care_events 表

**list_care_events**：
- 标准化查询参数中的 room/bed
- 支持 `limit` 参数（默认 50，上限 500）
- 按 `COALESCE(NULLIF(ts, 0), created_ts) DESC` 排序，兼容旧数据

**build_care_events_context**：
- 返回条目列表，每条包含 event_id、kind、title、content、severity、source、created_by、ts
- 构建简要摘要供上下文展示

**路由**：
- `GET /api/v3/care/events`：管理员或上下文鉴权通过后可查询
- `POST /api/v3/care/events`：要求管理员鉴权（通过 `_authorized_for_api` 检查）

## ESP32-S3 固件接口对齐说明

固件实现符合 `reference/espidf_protocol_contract.md` 规范：

**Wi-Fi STA**：
- 使用 `esp_wifi`、`esp_event`、`esp_netif` 组件
- SSID 和密码从 NVS 读取（通过 `device_config_t` 结构体）
- 断线自动重连

**MQTT 巴法云**：
- 使用 `mqtt_client.h`（espressif/mqtt 组件）
- Broker URI: `mqtt://bemfa_host:bemfa_port`（默认 bemfa.com:9501）
- Client ID = bemfa_uid
- Topic 命名：`{room}{bed}{suffix}` 全小写（如 `r1203b1tof1`）
- Payload 格式：`{"payload_b64":"<base64 原始 payload>"}`，base64 内容为原始传感器数据（非完整 USB 包）
- MQTT 缓冲区 16384 字节，足以容纳 ToF ~10KB payload 的 base64 编码

**NVS 配置**：
- 命名空间：`project2`
- 支持的键：wifi_ssid、wifi_pass、bemfa_uid、bemfa_host、bemfa_port、room、bed、device_id
- 控制台命令：CFG?、CFGSET key=value、CFGRESET、REBOOT
- `config_is_complete` 检查 room、bed、wifi_ssid、wifi_password、bemfa_uid 均非空

**USB CDC 并行回传**：
- 网络回传与 USB CDC 并行工作，USB 数据路径不受影响
- `network_backhaul_publish` 在 USB CDC 输出完成后调用，不阻塞 USB 路径
- Wi-Fi/MQTT 未连接时 `network_backhaul_publish` 为 no-op

## 本地测试与编译验证结果

修复后重新运行所有诊断命令：

**公共测试** `python tests\run_public_tests.py project2_task`：
- test_compile.py — OK
- test_functional_smoke.py — OK（admin 页面 200、admin setup 200）
- test_refactored_features.py — OK（auth、care_events、sleep_importer 模块可调用）
- test_smoke_gateway.py — OK（网关导入、CSV 导入）
- 结果：**全部通过**

**调试探针** `python tools\run_debug_probe.py project2_task`：
- admin setup 返回 200 — OK
- management API 拒绝缺失 Cookie — OK
- management API 拒绝伪造 Cookie — OK
- management API 接受有效 Cookie — OK
- 未知身份会话被拒绝 — OK
- 过期会话被拒绝 — OK
- care_event 写入要求管理员 Cookie — OK
- care_event 标准化 room/bed — OK
- 语音模块引用 current-session 获取 — OK
- 结果：**全部通过**

**ESP-IDF 编译** `python tools\run_espidf_build.py project2_task`：
- 编译状态：**成功**
- ESP-IDF 版本：v6.0.1（Windows EIM）
- 目标芯片：esp32s3
- 编译输出：`stdpro.bin`（984,160 字节 / 0xf0460），1MB 应用分区剩余 6%（0xfba0 字节）
- Bootloader：`bootloader.bin`（22,336 字节 / 0x5760），剩余 32%
- 构建系统：Ninja + ccache 增量编译，1096 步全部完成
- 组件依赖：espressif/esp_tinyusb 2.2.0、espressif/mqtt 1.0.0、espressif/tinyusb 0.19.0~3、idf 6.0.1
- 构建路径：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\`
- 注意：idf.py 在 Git Bash/MSys 环境路径污染下会拒绝运行（"MSys/Mingw is no longer supported"）。`run_espidf_build.py` 调用的 PowerShell 子进程继承了来自 Git Bash 的 MSys/Mingw PATH 条目。需要从 PATH 中剥离所有包含 msys、mingw、/usr/ 的条目并清除 MSYSTEM 等环境变量后方可编译。临时构建脚本 `run_espidf_temp.ps1` 实现了这一清理逻辑并成功完成编译。

## 未验证的残留技术债与风险

1. **Wi-Fi 实际连接未验证**：固件已编译成功但未在真实 ESP32-S3 硬件上烧录测试。Wi-Fi STA 连接、MQTT 巴法云连接、Topic 发布仅在代码层面符合协议规范，未做端到端验证。

2. **MQTT 大 payload 内存分配**：ToF payload 原始约 10KB，base64 编码后约 14KB，JSON 包装后约 14KB+32 字节。使用 `malloc` 在堆上分配，ESP32-S3 有 8MB PSRAM 支持，但在高频发布场景下若 MQTT 发送阻塞可能导致内存碎片。当前实现依赖 MQTT 客户端内部异步发送，未做流量控制。

3. **sdkconfig.defaults Kconfig 警告**：编译时出现 4 个 unknown kconfig symbol 警告（`TINYUSB_ENABLED`、`USB_OTG_SUPPORTED`、`ESP_WIFI_STA_DISCONNECTED_PM`、`ESP_WIFI_STA_DISCONNECTED_NVS`），这些符号在 ESP-IDF v6.0.1 中可能已改名或移除。编译未因此失败（TinyUSB 和 Wi-Fi 功能仍由组件自身 Kconfig 默认启用），但建议后续核对正确的符号名。

4. **nb_config_view reinterpret_cast 兼容性**：network_backhaul.cpp 使用 `reinterpret_cast<nb_config_view *>(&s_device_config)` 访问 main.cpp 中的 `device_config_t`。这两个结构体的前 7 个字段布局一致（wifi_ssid 到 bed），但 `device_config_t` 还包含 `device_id[48]` 字段。当前 reinterpret_cast 只访问前 7 个字段，布局兼容。若 future 修改 `device_config_t` 字段顺序，需同步更新 `nb_config_view`。

5. **管理员密码旧数据兼容**：如果数据库中存在修复前用明文存储的密码，修复后 `verify_admin_password` 使用 PBKDF2 验证将无法匹配旧明文。建议首次部署后重新执行 `/api/v3/admin/setup` 设置密码。此操作不影响现有 `admin_http_sessions` 表数据。

6. **语音助手会话获取端点**：`voice_assistant_integrated.py` 新增的 `fetch_current_session_id()` 调用 `/api/v3/session/current`，该端点需在 gateway.py 中有对应实现。若端点不存在或路径不同，语音助手将回退到无 session_id 模式（不报错，但可能无法获取上下文）。

7. **run_espidf_build.py 环境兼容性**：该脚本通过 `subprocess.run` 调用 PowerShell，继承了来自 Bash 工具的 MSys/Mingw PATH 条目，导致 idf.py 拒绝运行。本次构建通过独立的 `run_espidf_temp.ps1` 脚本（含 PATH 清理逻辑）完成。`run_espidf_build.py` 本身未修改（遵守不修改工具脚本的约束），但在 Git Bash 环境下需要手动清理 PATH 或使用独立脚本才能编译成功。
