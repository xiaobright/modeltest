# 项目改造总结 — 单床局域网 → 多床巴法云

> 2026-05-11 补充：
> 当前 `project2` 已继续向下演进，新增了独立 `vision/` 模块、`emotion` 写入链路、统一 `chat_context`、前端情绪面板，以及 `start_project.py` 中的视觉 worker 启动参数。
> 这一轮改动先按“默认床位 + 身份占位为空”的简化策略集成，便于先做板端联调；后续医院版的身份识别、视觉归床和权限裁剪将继续在此基础上扩展。

> 改造日期：2026-04-27  
> 目标：将原单床位局域网直连架构改造为多床位巴法云中继架构，适用于医院等多床位场景

---

## 1. 架构变化

### 改造前 (v1.0)

```
ESP32 ──TCP:9101──► Gateway (TCP Ingest) ──► HTTP API (单床) ──► Dashboard / Worker / Voice
```

### 改造后 (v2.0)

```
ESP32 #1 (R1203-B1) ──MQTT──►  巴法云  ◄──TCP sub── Gateway:8765 ──► Dashboard (多床)
ESP32 #2 (R1203-B2) ──MQTT──► bemfa.com │             │              ├─ Posture Worker (多床轮询)
ESP32 #N (R1204-B1) ──MQTT──►           │             └─ HTTP API   ├─ Voice Assistant (指定床位)
                                        │                (per-bed)  └─ Sleep Module
```

---

## 2. 文件变更清单

### 新增文件 (1)

| 文件 | 说明 |
|------|------|
| `gateway/bed_config.py` | 床位配置模块：Topic 命名、巴法云连接参数、床位列表管理 |

### 重写文件 (3)

| 文件 | 变更量 | 说明 |
|------|--------|------|
| `gateway/gateway.py` | ~1207→~620 行 | 移除 TCP:9100/9101，新增巴法云 TCP 订阅线程，数据层改为 per-bed，所有 API 加 room/bed 参数 |
| `gateway/dashboard.html` | 360→~310 行 | 新增床位概览面板 + 房间/床位选择器 + bed-chip 可点击切换 |
| `esp32/sketch_jan22a/sketch_jan22a.ino` | 288→~295 行 | TCP 直连改为 MQTT 巴法云发布，新增 room/bed/uid 配置，保留雷达解析逻辑 |

### 修改文件 (6)

| 文件 | 变更量 | 说明 |
|------|--------|------|
| `posture/posture_worker.py` | ~80 行新增 | 多床轮询：`/api/v2/beds` 获取床位列表，依次推理，每床独立 set_id 追踪 |
| `voice/voice_assistant_integrated.py` | ~60 行新增 | 新增 `VOICE_ROOM`/`VOICE_BED` 上下文绑定，mock 数据改为实时网关查询 |
| `start_project.py` | ~20 行改动 | 新增 `--voice-room`/`--voice-bed` 参数，移除 sleep-demo 逻辑 |
| `esp32/testpro4/main/main.cpp` | 待修复 | 当前迁移分支保留 USB CDC，Wi-Fi + MQTT/base64 巴法云回传需要恢复 |
| `esp32/testpro4/main/CMakeLists.txt` | 待修复 | 需要补齐 `esp_wifi` / `mqtt` / `mbedtls` 等依赖 |
| `esp32/testpro4/docs/protocol.md` | 参考契约 | LAN TCP 章节已替换为 MQTT 巴法云目标契约 |

### 文档更新 (5)

| 文件 | 说明 |
|------|------|
| `README.md` | 完整重写：新架构图、Topic 规范、API 列表、环境变量、ESP32 固件说明、v1/v2 对比 |
| `esp32/testpro4/README.md` | 更新架构图、新增 MQTT 配置章节、多床位部署指南 |
| `esp32/testpro4/QUICKSTART.md` | 更新为 MQTT 配置 + 编译流程 + 网关验证 |
| `esp32/testpro4/CHANGELOG.md` | 记录 TCP→MQTT 目标契约和当前待恢复状态 |
| `CHANGES.md` (本文件) | 完整改造总结 |

### 未修改文件

| 目录/文件 | 原因 |
|-----------|------|
| `posture/posture_model/` | 模型不变 |
| `posture/build_model.sh` | 编译方式不变 |
| `sleep_deploy_pack/` | 算法不变 |
| `rkllm_py/` | SDK 不变 |
| `voice/voice_loop_talk.py` | 辅助脚本不变 |
| `voice/intent_tuner.py` | 辅助脚本不变 |
| `esp32/testpro4/components/` | MLX 驱动不变 |
| `esp32/testpro4/managed_components/` | 依赖组件不变 |
| `requirements.txt` | 无新增 Python 依赖 |

---

## 3. 关键设计变更

### 3.1 数据存储层：flat → nested per-bed

```python
# 改造前
history[kind] = deque(items)

# 改造后
history[(room, bed)][kind] = deque(items)
esp_state[(room, bed)] = {
    "sets": deque,
    "current_set": {...},
    "last_packet": {...},
    ...
}
```

### 3.2 Topic 命名规范

```
{room}{bed}{kind}  →  r1203b1radar, r1203b1env, r1203b1audio
                      r1203b1tof1, r1203b1tof2, r1203b1mlx1, r1203b1mlx2
```

### 3.3 网络层：TCP Socket → MQTT

| 维度 | 旧方案 | 新方案 |
|------|--------|--------|
| ESP32 发送 | `send(sock, ...)` TCP | MQTT publish + base64 |
| Gateway 接收 | `socketserver.TCPServer` | `socket.connect(bemfa.com:8344)` TCP 订阅 |
| 二进制数据 | 原始 binary over TCP | base64 JSON over MQTT |
| 数据完整性 | CRC16-CCITT (ESP→Gateway) | MQTT QoS 0（云上转发不做 CRC） |
| 重连机制 | ESP32 自己重连 TCP | MQTT 自动重连 |

### 3.4 API 参数：全部加 room/bed

```
改造前: GET /api/v2/latest
改造后: GET /api/v2/latest?room=R1203&bed=B1  (默认首床)
```

新增端点：
```
GET /api/v2/beds → 返回所有床位列表及在线状态
```

### 3.5 Posture Worker：单 set → 多床轮询

```python
# 改造前
while True:
    set = fetch_latest_esp_set()  # 单床
    infer(set)
    sleep(2)

# 改造后
while True:
    beds = fetch_bed_list()       # 多床列表
    for bed in beds:
        process_one_bed(bed)      # 每床独立推理
        sleep(0.5)
    sleep(2)
```

### 3.6 Voice Assistant：无上下文 → 床位绑定

```python
# 新增环境变量
VOICE_ROOM = "R1203"
VOICE_BED = "B1"

# 所有网关查询自动带 room/bed
GATEWAY_SLEEP_CTX_URL = f"{GATEWAY_BASE}/api/v2/voice/sleep_context?room={VOICE_ROOM}&bed={VOICE_BED}"
```

### 3.7 Dashboard：单床静态 → 多床动态切换

```javascript
// 新增组件
- 床位概览面板（bed-chip 可点击切换）
- 房间/床位下拉选择器
- 每床在线状态指示灯（绿/红 dot）
- 切换时自动重新拉取数据
```

---

## 4. 部署清单

### 4.1 环境变量（必设）

```bash
export BEMFA_UID="your_bemfa_uid"  # 巴法云私钥
```

### 4.2 ESP32 固件配置（每床设置）

**sketch_jan22a (Arduino)**:
```cpp
const char *bemfa_uid = "YOUR_BEMFA_UID_HERE";
const char *room_id = "r1203";  // 按床位修改
const char *bed_id = "b1";      // 按床位修改
```

**testpro4 (ESP-IDF)**:
```c
#define BEMFA_UID  "YOUR_BEMFA_UID_HERE"
#define BEMFA_ROOM "r1203"  // 按床位修改
#define BEMFA_BED  "b1"     // 按床位修改
```

### 4.3 床位管理

```bash
# 默认 3 床 (R1203/B1, R1203/B2, R1204/B1)
# 自定义床位：
export BEDS_CONFIG='{"beds":[["R1203","B1"],["R1203","B2"],["R1204","B1"],["R1204","B2"]]}'
```

### 4.4 启动命令

```bash
# 全部服务
python start_project.py --target all --voice-input text --with-posture \
    --voice-room R1203 --voice-bed B1

# 仅网关
python start_project.py --target gateway

# 仅语音助手
python start_project.py --target voice --voice-input text \
    --voice-room R1203 --voice-bed B1
```

---

## 5. 兼容性说明

- **向后不相容**：v2.0 无法直接兼容 v1.0 的 ESP32 固件（网络协议不同）
- **数据格式兼容**：ESP32 传感器驱动层（MLX/ToF 解析）和 Posture 模型推理层完全未变
- **USB CDC 保留**：testpro4 USB 调试通道完整保留，`collectdata_esp32.py` 仍可正常使用
- **Python 依赖**：未新增任何 Python 包，`requirements.txt` 无需变动

---

## 6. 待完成事项

| 事项 | 优先级 | 说明 |
|------|--------|------|
| 获取巴法云 UID | 高 | 在 `bemfa.com` 注册并获取私钥 |
| 在巴法云创建 topic | 高 | 为每个床位创建 7 个 topic（radar/env/audio/tof1/tof2/mlx1/mlx2） |
| 填入 UID 到固件 | 高 | 两个固件中的 `YOUR_BEMFA_UID_HERE` 占位符需要替换 |
| 编译烧录 ESP32 | 高 | 每个床位编译并烧录对应固件 |
| 联调测试 | 中 | ESP32 → 巴法云 → Gateway 全链路联调 |
| 小程序适配 | 低 | 将 `others/bemfa_mini_led/bemfa_mini2/` 小程序对接新版 API |
