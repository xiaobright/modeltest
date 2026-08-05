# Pull Request 提测说明 (Pull Request Template)

本 PR 把 `project2_task` 修复到可提测状态。CI 与 Reviewer 会就本文件的自检报告、变更 diff 做交叉一致性校验。

## 初始自检诊断

修改前先运行项目自带的诊断门禁，得到驱动修复的工作清单（逐项见 `CHANGES.md` 的「待修复 → 已修复」）：

- `python tests\run_public_tests.py project2_task`
  - 收到工程时：`gateway` 侧存在未落地的鉴权 / care_event / 睡眠导入 / 语音助手集成缺口，公共测试覆盖面不足。
  - 修复后（见「本地测试与编译验证结果」）：`all public tests passed`。
- `python tools\run_debug_probe.py project2_task`
  - 收到工程时：管理 API 缺少会话/ Cookie 鉴权、care_event 缺规范化、睡眠 CSV 缺 room/bed 兜底策略。
  - 修复后：`all visible diagnostic checks passed`（6 项 probe 全部 `probe:ok`）。
- `python tools\run_espidf_build.py project2_task`
  - 收到工程时：`network_backhaul` 未实现、`main.cpp` / `CMakeLists.txt` 留 TODO，且 `esp-mqtt` 在本工具链不可解析。
  - 修复后：`Build finished successfully`，产物 `stdpro.bin`（见「本地测试与编译验证结果」）。

## 修改的文件列表

网关 / 服务端（Python，Tasks #1–#5，已通过诊断）：

- `gateway/auth.py` — 管理员账户、会话、Cookie 鉴权（新建/重做）。
- `gateway/gateway.py` — 路由与管理 API、会话/上下文鉴权、主题派生。
- `gateway/care_events.py` — care_event CRUD、表迁移、规范化、按 subject/room/bed 作用域查询。
- `gateway/db.py` — SQLite 管理库、旧表列迁移（保留历史行）。
- `gateway/sleep_importer.py` — 睡眠 CSV 逐行导入、room/bed 兜底策略。
- `gateway/voice_assistant_integrated.py` — 语音助手集成，显式拉取当前会话。

固件（ESP32-S3，Task #6，本会话实现并通过编译）：

- `esp32/testpro4/main/protocol_packet.h` / `.cpp` — USB 包封包/校验（CRC16-CCITT，小端，payload-only）。
- `esp32/testpro4/main/mqtt_payload.h` / `.cpp` — 主题派生、base64、JSON 封套。
- `esp32/testpro4/main/network_backhaul.h` / `.cpp` — Wi-Fi STA + Bemfa MQTT 回传（自包含 MQTT 3.1.1 over LWIP）。
- `esp32/testpro4/main/main.cpp` — 接入 `network_backhaul`，ToF/MLX 帧并行发布；`config_is_network_ready()` 门控。
- `esp32/testpro4/main/CMakeLists.txt` — 新增 3 个源文件；REQUIRES 调整为 `esp_wifi`/`esp_netif`/`esp_event`/`lwip`/`mbedtls`。
- `esp32/testpro4/main/idf_component.yml` — 保留 `esp_tinyusb`；移除不可解析的 `esp-mqtt`，改用 LWIP 自包含客户端。
- `esp32/testpro4/CHANGELOG.md` — 追加 `[4.1]` 回传恢复说明与偏差记录。

工程跟踪：

- `CHANGES.md` — 两条「待修复」改为「已修复」，附说明。

## 架构调整与模块设计

网关与服务端保持既有模块边界，新增/补全职责：

- **鉴权层** `auth.py`：与业务解耦，统一负责账户、会话、Cookie，业务模块不接触明文密码。
- **care_event 层** `care_events.py`：只做持久化/规范化/按作用域读取；授权在 HTTP/网关层完成，模块本身不泄漏跨主体数据。
- **数据导入层** `sleep_importer.py`：把睡眠算法的 epoch / quality CSV 逐行映射为按床位的 `sleep_epoch` / `sleep_quality` 项，支持缺 room/bed 兜底。
- **语音层**：显式携带 session，避免隐式复用他人上下文。

固件侧采用「USB CDC 上行 + MQTT 回传并行」的双通道结构：

- `protocol_packet`：与既有的 USB 包契约对齐（同步头 `AA 55`、TYPE 0x01=MLX / 0x02=ToF、CRC16-CCITT）。
- `mqtt_payload`：把 `(room,bed,type,id)` 推导成小写主题与 base64+JSON 封套，**只回传裸 payload（非整包 USB 帧）**。
- `network_backhaul`：Wi-Fi STA 接入 + Bemfa MQTT 发布；与 `main.cpp` 通过 `publish_posture_frame()` 解耦，后续可整体替换为 `esp-mqtt` 而不动调用方。

## 安全边界及鉴权设计

- **密码永不明文**：`auth._password_hash` 使用 PBKDF2-HMAC-SHA256 + 随机 16 字节盐（20 万次迭代），数据库只存 `salt` + `password_hash`。空 salt 表示「生成新盐」，绝不表示「跳过哈希」。
- **会话 Cookie 为随机令牌**：`secrets.token_urlsafe(32)` 生成，库中只存其 SHA-256 哈希（`_token_hash`），令牌本身不可逆推出。
- **鉴权强制且零泄漏**：
  - `get_admin_http_session` 要求令牌存在、未过期、且关联账户 `active`；缺令牌/伪造/过期一律返回 `None`（debug probe 三项 `ok` 已验证）。
  - care_event / 上下文组装仅在授权通过后按 `subject_id` 或规范化 `room/bed` 作用域返回，不返回未授权目标的数据。
- **防接管**：`admin_account_exists()` 保证超级管理员仅首次 setup 可创建，之后重复 setup 直接拒绝。
- **旧库兼容（不降安全）**：若旧 DB 以空盐 + 明文存储，登录命中后**就地**迁移为加盐哈希，不长期保留明文。
- **SQLite 迁移保旧数据**：`care_events` / 管理库缺失列在 `ALTER TABLE` 中原位补齐并回填 `ts`，历史行全部保留。

## 睡眠 CSV 无 room/bed 时的特殊处理

`sleep_importer.row_targets` 逐行处理（非整文件一刀切）：

1. 兼容大小写列名：`room/Room/ROOM`、`bed/Bed/BED`。
2. 行内同时有 room+bed：与已配置床位做**大小写不敏感**匹配；命中则用规范 `(room,bed)`，未命中则按行内值写入。
3. 缺 room/bed 时按策略兜底（均只影响无作用域行，其余有值行照常写入）：
   - 同时配置了 `SLEEP_IMPORT_DEFAULT_ROOM` / `SLEEP_IMPORT_DEFAULT_BED` → 落到该默认床位；
   - 否则按 `SLEEP_IMPORT_UNSCOPED_POLICY`：`all`=写入所有配置床位；`skip`=跳过该行；`first`=写入首个配置床位（**默认策略**）；
   - 策略值无法识别 → **出于安全不扩散**，该行不导入（仅记录 skipped 日志）。
4. 跳过的行打印 `[SLEEP-IMPORT] ... skipped=N rows without room/bed`，便于审计。

## care_event 实现细节

- **幂等迁移**：`init_care_events_table` / `_migrate_columns` 对旧表缺失列（`severity`/`source`/`created_by`/`ts`）做 `ALTER TABLE` 补足，并用 `UPDATE ... SET ts = created_ts` 回填历史行的 `ts`，旧数据可查。
- **规范化**：`create_care_event` 对 `room`/`bed` 规范化（大写），使 `r1203/b1` 与 `R1203/B1` 落到同一记录；`severity` 限定为 `{info, warning, critical}`，越界回退 `info`。
- **作用域读取**：`list_care_events` 按 `subject_id` 或规范化 `room/bed` 过滤，查询值同样规范化；结果按 `ts DESC, created_ts DESC` 排序，`limit` 封顶 `MAX_LIMIT=200`。
- **上下文组装**：`build_care_events_context` 只在授权通过后调用，按目标 subject/room/bed 取数，绝不返回未授权主体数据。
- **边界安全**：模块只管持久化/规范化，授权在 HTTP/网关层；与鉴权层解耦。

## ESP32-S3 固件接口对齐说明

- **契约**（详见 `reference/espidf_protocol_contract.md` 与 `esp32/testpro4/docs/protocol.md`）：
  - USB 包：`[AA 55][TYPE][ID][LEN_L][LEN_H][PAYLOAD][CRC_L][CRC_H]`，CRC16-CCITT（init 0xFFFF，poly 0x1021，仅 payload，小端）。TYPE 0x01=MLX，0x02=ToF。
  - MQTT 主题（小写，无 UID 前缀）：`{room}{bed}tof1|tof2|mlx1|mlx2`，与网关 `bed_config.topics_for()` 一致。
  - MQTT 载荷：`{"payload_b64":"<base64 裸 payload>"}`（**裸 payload，非整包 USB 帧**）。
  - 服务器 `bemfa.com:9501`；ClientID = UID，username = UID，clean session，keep-alive 60s，QoS0。
- **固件实现**：
  - `main.cpp`：ToF 帧（`usb_send_tof_payload`）与 MLX 双流（`mlx_sender_task`，MLX1/MLX2）在保留 USB CDC 上行的同时调用 `network_backhaul::publish_posture_frame()`。
  - `config_is_network_ready()`：仅当 `room`/`bed`/`wifi_ssid`/`bemfa_uid` 均非空才启动回传，否则仅记录缺哪些配置并继续以纯 USB CDC 运行。
  - `network_backhaul`：Wi-Fi STA 事件驱动联网 → DNS 解析 → TCP 连接 → CONNECT/CONNACK → 发布；断线率控重连（5s），空闲 30s 发 PINGREQ 保活；发布失败标记离线并等待下次重连。MQTT 不可达时**不阻塞 USB CDC 采集**。
- **偏差记录（重要）**：本工具链的 ESP-IDF v6.0.1 Windows EIM **无法解析 `espressif/esp-mqtt`**（公共仓库无该组件、in-tree `components/mqtt` 仅为占位）。为保证在本机与任何健康 ESP-IDF 安装上均可编译，`network_backhaul` 改为基于 LWIP BSD socket 的**自包含最小 MQTT 3.1.1 客户端**（契约不变）。该模块与 `main.cpp` / `mqtt_payload` 解耦，后续可整体换回 `esp-mqtt` 而无需改动调用方。

## 本地测试与编译验证结果

- `python tests\run_public_tests.py project2_task`
  - 结果：`[public] all public tests passed`（含 `GatewaySmokeTest.test_gateway_import_and_management_db ... ok`，`Ran 1 test ... OK`）。
- `python tools\run_debug_probe.py project2_task`
  - 结果：`all visible diagnostic checks passed`，6 项探针 `probe:ok`：
    - `admin setup returns 200`
    - `management API rejects missing cookie`
    - `management API rejects forged cookie`
    - `management API accepts valid cookie`
    - `unknown identity session is denied`
    - `expired session is denied`
    - `care_event write rejects missing admin cookie`
    - `care_event normalizes room/bed for create and query`
  - 另附信息项：`voice module appears to reference current-session fetch`、`ESP32-S3: run tools/run_espidf_build.py after firmware changes.`
- `python tools\run_espidf_build.py project2_task`
  - 结果：**`Build finished successfully.`**（退出码 0）
  - 产物：`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`，大小 `0xd6fd0`（约 880 KB），app 分区余 `0x29030`（16%）空闲。
  - 修复点：最初因 `network_backhaul.cpp` 缺少 `namespace network_backhaul {` 开括号导致编译失败（`expected declaration before '}'`），已补回并复编通过。
  - 备注：编译期有一条 CMake 工具版本探测警告（无法读取 `xtensa-esp32s3-elf-gcc` 版本），属环境探测性提示，不影响构建成功。

## 未验证的残留技术债与风险

1. **esp-mqtt 偏差**：因工具链不可解析 `esp-mqtt`，回传改用 LWIP 自包含客户端。功能等价但未走官方组件，后续若换回 `esp-mqtt` 需回归测试。
2. **真实联网未验证**：本机仅做本地编译验证，未接入真实 Wi-Fi / Bemfa 进行端到端 MQTT 收发（参考契约声明「不在本地编译中验证」联网）。运行时需下发 `room`/`bed`/`wifi_ssid`/`wifi_password`/`bemfa_uid`。
3. **部署配置待办**：本地诊断显示 `BEMFA_UID 未设置（环境变量 BEMFA_UID）` 警告；固件侧 UID / 主题 / 房间床位为运行时下发项，属上线配置，不在本次修复范围。
4. **硬件行为未实测**：ToF 全帧 / MLX 热成像解析、USB CDC 实测吞吐仅在结构层面对齐契约，未在实体 ESP32-S3 + 传感器上跑通。
5. **工具链警告**：gcc 版本探测警告为环境侧探测问题，已在 CHANGELOG 标注，不影响产物。
6. **边界假设**：`strncpy` 写入 Wi-Fi SSID/密码/UID 时依赖字段长度上限；若后续配置字段扩容需同步加长缓冲。
