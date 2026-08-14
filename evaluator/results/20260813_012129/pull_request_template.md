# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

修改前运行：

- `python tests\run_public_tests.py project2_task` → **通过**（1 个编译冒烟 + 3 个功能冒烟 + 1 个 gateway 冒烟，共 7 个用例全部 OK）。
- `python tools\run_debug_probe.py project2_task` → **退出码 1，6 项失败**：

```text
[probe:FAIL] management API rejects missing cookie status=200 ...
[probe:FAIL] management API rejects forged cookie status=200 ...
[probe:FAIL] unknown identity session is denied policy={'allowed': True, ...}
[probe:FAIL] expired session is denied policy={'allowed': True, ...}
[probe:FAIL] care_event write rejects missing admin cookie status=404 ...
[probe:FAIL] care_event normalizes room/bed for create and query result=... rows=[]
[probe:Warning] Voice/assistant path: sensitive context may be denied without session_id ...
```

根因：`_authorized_for_api` 对本机请求全部放行；`get_admin_http_session` 不校验 token、取任意会话；密码明文、`admin_account_exists` 恒 False；`session_is_authenticated` 对 unknown identity 返回 True；`/api/v3/care/events` 路由缺失且模块不归一化 room/bed；voice 未带会话取上下文。

## 修改的文件列表

### Gateway（Python）

- `gateway/auth.py` — 密码强制加盐哈希（PBKDF2-SHA256，200k 迭代，随机 16B salt）；`admin_account_exists()` 改为真实查库；`get_admin_http_session()` 按 `sha256(token)` 精确匹配并校验过期；历史明文行登录时自动升级为加盐哈希。
- `gateway/db.py` — `care_events` 完整 schema（`severity/source/created_by/ts`）；新增 `table_columns()`/`ensure_columns()`/`migrate_legacy_tables()`，用 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` 迁移旧表并回填 `ts=created_ts`，旧行不丢失。
- `gateway/care_events.py` — 完整 CRUD：room/bed 写入与查询归一化（大写）；`severity/source/created_by/ts` 落库；`list_care_events` 支持 `limit`、按 `COALESCE(ts, created_ts)` 倒序；`build_care_events_context()` 输出事件摘要供 chat context 使用。
- `gateway/gateway.py` — `_authorized_for_api` 收紧：管理员会话 或 本机且路径在本机服务例外清单（`/api/v2/*`、`/api/esp/*`、`/api/v3/context/chat`、`identity/gallery`、`identity/match`、`vision/observation`、`session/current`）；新增 `GET/POST /api/v3/care/events` 路由（写需管理员，读支持管理员或授权 session）；`session_is_authenticated` 拒绝 unknown identity / 空 assurance / 过期 / 缺 actor_subject_id；`actor_can_access_target` 对未知 actor 拒绝；`build_chat_context_v3` 要求显式 `session_id`（不再静默回退 ambient session），管理员 Cookie 可作为 admin actor，授权时聚合 `modalities.care_events`；logout 支持无 body POST；gallery/credential template 远程访问改为"管理员或本机"。
- `gateway/sleep_importer.py` — 修复 `UNSCOPED_POLICY=first` 误用 `beds[-1]`（改为 `beds[0]`）；显式 room/bed 行按行归一化大小写；策略只作用于无归属行，`all` 仅作显式调试模式。
- `voice/voice_assistant_integrated.py` — 新增 `fetch_current_session()`（读 `/api/v3/session/current`）；`fetch_gateway_chat_context` 在未显式给 session_id 时先取当前会话再带 `session_id` 请求 context。

### ESP32-S3 固件（`esp32/testpro4/`）

- `main/protocol_packet.{h,cpp}` — 新增：USB packet 常量、CRC16-CCITT（init 0xFFFF / poly 0x1021，只覆盖 payload）、6B header 与 2B CRC 小端打包。
- `main/maixsense_parser.{h,cpp}` — 新增：MaixSense 字节流解析器类，处理噪声、分块、坏尾字节、异常长度、半帧；只输出完整帧 `[00 FF][LEN][META16][IMG10000][CHECK][DD]`。
- `main/device_config.{h,cpp}` — 新增：NVS 读写（`ssid/password/uid/room/bed/host/port/device_id`）、`is_complete()` 校验五要素齐全、topic 小写拼接 `{room}{bed}{stream}`、stream 名映射。
- `main/mqtt_payload.{h,cpp}` — 新增：mbedtls base64 构造 `{"payload_b64":"..."}`，容量按 `payload_len*4/3+32` 计算，避免固定小缓冲。
- `main/network_backhaul.{h,cpp}` — 新增：`esp_netif`/事件循环初始化、Wi-Fi STA（断线自动重连）、esp-mqtt 客户端（`mqtt://{host}:{port}`，client_id=UID，自动重连，outbox 256KB）、`publish_payload()` 按 sensor type/id 选 topic 发布。
- `main/main.cpp` — 重构为 glue：USB CDC 发送路径改用协议模块；`usb_send_tof_payload()` 与 MLX 发送路径在 USB 之外并行 MQTT 发布原始 payload；`app_main` 在 NVS 配置齐全时启动网络回传，否则打印警告继续 USB-only；保留 AT 命令时序、自动波特率、CFG 控制台。
- `main/CMakeLists.txt` — REQUIRES 补齐 `esp_wifi esp_netif esp_event lwip mqtt mbedtls`。
- `main/idf_component.yml` — 新增 `espressif/mqtt: ^1.0.0`。

### 文档

- `README.md`（项目级）、`gateway/README.md`、`RK3588_TEST_GUIDE.md`、`esp32/testpro4/README.md`、`esp32/testpro4/CHANGELOG.md` — 同步 care_event、v3 会话、安全边界、睡眠归属策略与固件回传说明。

## 架构调整与模块设计

保持既有模块边界：认证逻辑留在 `auth.py`，schema 与迁移留在 `db.py`，care_event CRUD 留在新增的 `care_events.py`，`gateway.py` 只加路由 glue 与授权判定。v3 上下文改为“调用方显式携带会话凭证”：voice 通过 `/api/v3/session/current` 取会话后携带 `session_id`，gateway 不再静默使用 ambient session，避免收紧鉴权后靠隐式会话漏数据。ESP32 固件按推荐结构拆成 5 个协议/配置模块，`main.cpp` 只保留初始化、任务和硬件调用。

## 安全边界及鉴权设计

- 管理员密码 PBKDF2-SHA256 加盐哈希存储；Cookie 只保存 `secrets.token_urlsafe(32)` 随机 token，数据库只存 `sha256(token)`；会话按 token 精确匹配、校验过期、退出后失效（已验证退出后旧 Cookie 401）。
- 管理 API 缺 Cookie / 伪造 Cookie 一律 401；本机例外仅限采集、视觉、身份 gallery/match、vision observation、session/current 和 v3 context 服务接口；远程未登录不能访问管理 API，也不能导出 face/credential template（远程管理员登录后可访问）。
- v3 会话认证要求：`identity_state` 非 unknown/空、`assurance_level` 非 none/空、`expires_ts` 未过期、`actor_subject_id` 非空；staff/admin 可查任意目标，patient 只能查自己，其余一律 `allowed=false` 且不返回患者明细、记忆、护理事件。
- care_event 写需管理员；读需管理员或对目标有权限的授权 session。

## 睡眠 CSV 无 room/bed 时的特殊处理

按行处理：行带 `room/bed` 只写入对应床位（大小写归一化、不影响其它行）；无归属行按序判断——`SLEEP_IMPORT_DEFAULT_ROOM/BED` 指定则写指定床位，`SLEEP_IMPORT_UNSCOPED_POLICY=first`（默认）写第一个配置床位，`skip` 跳过，`all` 仅显式调试模式（非默认）。同一 CSV 混有/无归属行时互不干扰。

## care_event 实现细节

- DB：`care_events` 含 `event_id/subject_id/room/bed/kind/title/content/severity/source/created_by/ts/created_ts/updated_ts` + subject 与 room/bed 索引；旧表缺列自动 `ALTER TABLE` 补齐并回填 `ts=created_ts`。
- API：`POST /api/v3/care/events`（管理员）；`GET /api/v3/care/events?subject_id=&room=&bed=&limit=`（管理员或授权 session），按 ts/created_ts 倒序；room/bed 大小写归一化（`r1203/b1` 写入可用 `R1203/B1` 查到）。
- Context：授权通过时 `modalities.care_events` 返回最近 5 条摘要并汇入 `brief`/`prompt_hints`；未授权不返回。

## ESP32-S3 固件接口对齐说明

- USB packet 契约不变：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT 只覆盖 payload，LEN/CRC 小端。
- ToF payload 保持完整 MaixSense 原始帧，不裁剪 10000B 图像区。
- MQTT：`mqtt://{bemfa_host}:{bemfa_port}`（默认 bemfa.com:9501），client_id=巴法云 UID；JSON `{"payload_b64":"..."}`，base64 为原始 payload（非完整 USB packet）；topic 为小写 `{room}{bed}tof1/tof2/mlx1/mlx2`。
- NVS：`wifi_ssid/wifi_pass/bemfa_uid/bemfa_host/bemfa_port/room/bed/device_id`，五要素齐全才启动网络回传；串口命令 `CFG?/CFGSET/CFGRESET/REBOOT` 保留。
- 依赖：`main/CMakeLists.txt` 与 `idf_component.yml` 已补齐 `esp_wifi/esp_netif/esp_event/lwip/mqtt/mbedtls` 与 `espressif/mqtt ^1.0.0`。

## 本地测试与编译验证结果

修复后运行：

- `python tests\run_public_tests.py project2_task` → **通过**（`[public] all public tests passed`）。
- `python tools\run_debug_probe.py project2_task` → **通过**（`[probe] all visible diagnostic checks passed`，8 项 probe:ok，voice 提示变为 `[probe:info] voice module appears to reference current-session fetch`）。
- 附加手工验证（临时库，未改 tests/）：
  - 旧库迁移：缺列 `care_events` 表迁移后旧行保留，`ts=created_ts` 回填，新列默认值正确。
  - 缺 Cookie / 伪造 Cookie / 有效 Cookie 访问管理 API → 401 / 401 / 200。
  - logout 无 body POST → 200，随后旧 Cookie 访问管理 API → 401。
  - unknown identity / 过期 session / 无 session_id → context `allowed=false`（`not_authenticated`）；patient 越权查他人 → `not_authorized_for_target` 且无患者明细；staff session → `allowed=true` 且 `modalities.care_events` 有摘要；管理员 Cookie 请求 context → `allowed=true`。
  - care_event 用小写 `r1203/b1` 写入后可用 `R1203/B1` 查询命中。
- `python tools\run_espidf_build.py project2_task`（等价于 `run_espidf_windows_build.ps1 -ProjectDir .\project2_task -Target esp32s3`）→ **成功**：Windows EIM ESP-IDF v6.0.1，`idf.py set-target esp32s3` + 增量编译通过，生成 `stdpro.bin`（0xf05c0 字节，最小 app 分区 0x100000，剩余 6%）。首次运行暴露 3 个编译错误（`<initializer_list>` 缺失、2 处 `-Wformat-truncation`），修复后二次运行成功；其余为既有 `-Wmissing-field-initializers` 警告（main 组件已按既有约定降级为非 error）。

## 未验证的残留技术债与风险

1. **ESP32 未做实机验证**：未执行 `idf.py flash/monitor`，未验证真实 Wi-Fi/MQTT 连通、USB 枚举、ToF 上电时序、MLX90640 读数。MQTT 发布在传感器任务内同步调用，网络拥塞时可能拖慢 USB 发送节奏（后续可改为独立发布队列/任务）。
2. **巴法云吞吐**：ToF 8FPS×2 的 13KB 级 MQTT 消息对巴法云压力较大，QoS 0 丢包语义适合传感器遥测；如丢帧过多需降频或改直连网关。
3. **app 分区余量**：`stdpro.bin` 距离默认 app 分区仅剩约 6%，后续加功能需调整分区表。
4. **ESP32 构建依赖网络**：`esp_tinyusb`/`mqtt` 组件由 IDF component manager 从注册表解析，离线环境需预置缓存。
5. **session/current 本机例外**：为让 voice 取当前会话，`/api/v3/session/current` 加入了本机服务例外清单；它只暴露 actor 身份/情绪元数据，不含患者数据，但若未来该接口内容扩大需重新评估。
6. **voice 未在板端实测**：只做了静态调用链与编译检查，未跑真实 faster-whisper/RKLLM 链路；`voice_loop_talk.py` 为不依赖网关的独立 demo，未改动。
7. **管理员会话无 CSRF 防护之外的加固**：Cookie 为 SameSite=Lax + HttpOnly，生产环境建议再加 TLS 与速率限制。
