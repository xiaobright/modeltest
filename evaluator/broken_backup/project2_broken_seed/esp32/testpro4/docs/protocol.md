# 数据协议规范

## 统一数据包格式 (v2.0)

所有传感器使用统一的数据包格式：

```
[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]
```

### 字段说明

| 偏移 | 字段 | 长度 | 说明 |
|------|------|------|------|
| 0 | SYNC1 | 1 B | 同步头 1：`0xAA` |
| 1 | SYNC2 | 1 B | 同步头 2：`0x55` |
| 2 | TYPE | 1 B | 传感器类型：`0x01` = MLX90640, `0x02` = MaixSense ToF |
| 3 | ID | 1 B | 传感器编号：`0x01` / `0x02` |
| 4 | LEN_L | 1 B | Payload 长度低字节（小端序） |
| 5 | LEN_H | 1 B | Payload 长度高字节（小端序） |
| 6 | PAYLOAD | N B | 传感器数据（长度 = `LEN_L | (LEN_H << 8)`） |
| N+6 | CRC_L | 1 B | CRC16-CCITT 校验低字节 |
| N+7 | CRC_H | 1 B | CRC16-CCITT 校验高字节 |

### 包类型

| TYPE | 传感器 | 数据内容 | Payload 大小 |
|------|--------|----------|-------------|
| `0x01` | MLX90640 | 768 个 float32 温度值 | 3072 字节 |
| `0x02` | MaixSense ToF | 原始帧数据（含元数据 + 深度图） | 可变（~10000 字节） |

---

## MLX90640 数据

MLX90640 的每帧数据包含 768 个像素点（24 行 × 32 列）的温度值，以 **float32**（小端序）排列：

```
[温度(0,0)] [温度(0,1)] ... [温度(23,31)]
  ↑ float32   ↑ float32       ↑ float32
```

- 行优先存储
- 单位：摄氏度（°C）
- 总数据量：768 × 4 = 3072 字节 / 传感器 / 帧

### 数据流

```
MLX90640 传感器1 (0x33) ─┐
                          ├── I2C ──→ MLXManager ──→ CDC 0 / TCP
MLX90640 传感器2 (0x34) ─┘
```

- 帧率：4 FPS（由 `MLXManager.hpp` 配置）
- 使用 Melexis 官方 API 计算温度

---

## MaixSense ToF 数据

### 传感器原始帧格式

MaixSense ToF 传感器的 UART 输出帧格式：

```
[00 FF] [LEN_L] [LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]
  ↑       ↑       ↑         ↑           ↑            ↑         ↑
 帧头     长度    长度    元数据16B    深度图      校验和     帧尾
```

- **帧头**：`00 FF`（注意：非 `AA 55`）
- **长度**：2 字节小端序，值为 `10016`
- **元数据**：16 字节，包含传感器状态信息（可跳过）
- **图像数据**：10000 字节，100 × 100 uint8 深度值
- **校验和**：1 字节
- **帧尾**：`0xDD`

### ESP32 端处理

ESP32 在固件端完成帧边界识别（`MaixSenseFrameParser`），将完整帧（含 `AA 55` 统一包头和 CRC）转发给上位机或网关：

```
原始：     [00 FF] [LEN] [META(16)] [IMG(10000)] [CHK] [DD]     ← UART 输入
          │                        │
          ▼                        ▼
          ┌────────────────────────────────┐
          │  ESP32 Frame Parser            │
          │  · 12KB 循环缓冲区             │
          │  · 搜索 00 FF 帧头             │
          │  · 动态读取帧长度              │
          │  · 验证帧尾 0xDD               │
          │  · 跳过 16B 元数据             │
          └────────────────────────────────┘
          │                        │
          ▼                        ▼
输出：     [AA 55] [02] [ID] [LEN] [IMG(10000)] [CRC]            ← USB / TCP 输出
```

---

## CRC16-CCITT

### 算法

- 初始值：`0xFFFF`
- 多项式：`0x1021`（CCITT 标准）
- 仅对 Payload 部分计算（不包含同步头和长度字段）
- 小端序传输

### C 参考实现（ESP32 端）

```cpp
static uint16_t crc16_ccitt(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc <<= 1;
        }
    }
    return crc;
}
```

### Python 参考实现（上位机端）

```python
def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
    return crc & 0xFFFF
```

### 验证数据包

```python
def verify_packet(packet: bytes) -> bool:
    """验证一个完整数据包（含包头和 CRC）的 CRC 校验。"""
    if len(packet) < 8:
        return False
    payload = packet[6:-2]       # 跳过 6 字节包头，去掉末尾 2 字节 CRC
    crc_received = packet[-2] | (packet[-1] << 8)
    crc_calculated = crc16_ccitt(payload)
    return crc_received == crc_calculated
```

---

## USB CDC 通道分配

| 通道 | 端口（Linux） | 用途 | 数据率 |
|------|-------------|------|--------|
| CDC 0 | `/dev/ttyACM0` | MLX90640 × 2 | ~25 KB/s |
| CDC 1 | `/dev/ttyACM1` | MaixSense ToF × 2 | ~162 KB/s |

- 波特率：不需要配置（USB CDC 是虚拟串口，忽略波特率设置）
- 缓冲区：2048 字节

---

## LAN 回传（MQTT 巴法云）

> **v4.0 起** TCP LAN 回传已替换为 MQTT 巴法云回传。

### 通信方式

- **传输层**：MQTT (over TCP)
- **服务器**：bemfa.com:9501
- **ClientID**：巴法云 UID（私钥）
- **数据格式**：Base64 编码的 JSON
- **并行性**：USB CDC 和 MQTT 双通道同时发送，互不干扰

### MQTT 消息格式

```json
{"payload_b64": "<base64_encoded_binary>"}
```

其中 `base64_encoded_binary` 是完整的二进制 payload（MLX: 3072 bytes float32 / ToF: ~10000 bytes raw frame）的 Base64 编码。

### 包流示例

```
USB CDC 0:  [AA 55 01 01 0C 00] [3072B MLX1 数据] [CRC]
USB CDC 1:  [AA 55 02 01 27 10] [10000B ToF1 数据] [CRC]
MQTT:       Topic "r1203b1mlx1" → {"payload_b64": "<base64>"}     ← 同时发送
MQTT:       Topic "r1203b1tof1" → {"payload_b64": "<base64>"}     ← 同时发送
```

### Topic 命名

| Topic | 内容 |
|-------|------|
| `{room}{bed}tof1` | MaixSense ToF Sensor 1 |
| `{room}{bed}tof2` | MaixSense ToF Sensor 2 |
| `{room}{bed}mlx1` | MLX90640 Sensor 1 (0x33) |
| `{room}{bed}mlx2` | MLX90640 Sensor 2 (0x34) |

默认：`r1203b1tof1`, `r1203b1tof2`, `r1203b1mlx1`, `r1203b1mlx2`

---

## 保存文件格式

采集数据保存为以下目录结构：

```
collected_data/
└── <场景名>/
    ├── cam1/   00000.bin, 00001.bin ...  ← ToF1 深度 (100×100, uint8)
    ├── cam2/   00000.bin, 00001.bin ...  ← ToF2 深度 (100×100, uint8)
    ├── long/   00000.bin, 00001.bin ...  ← MLX1 温度 (32×24, float32)
    ├── wide/   00000.bin, 00001.bin ...  ← MLX2 温度 (32×24, float32)
    └── preview/ 00000.png, 00001.png ... ← 预览图像
```

### 读取数据示例

```python
import numpy as np

# 读取 ToF 深度数据
depth = np.fromfile('cam1/00000.bin', dtype=np.uint8).reshape(100, 100)

# 读取 MLX 温度数据
temps = np.fromfile('long/00000.bin', dtype=np.float32).reshape(32, 24)

print(f"深度范围: {depth.min()} ~ {depth.max()}")
print(f"温度范围: {temps.min():.2f}°C ~ {temps.max():.2f}°C")
```

---

## 网关 REST API

网关 (`gateway.py`) 提供以下 REST 接口：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/esp/status` | GET | ESP32 连接状态（是否在线、最近接收时间等） |
| `/api/v2/latest` | GET | 最新传感器数据全集 |
| `/dashboard` | GET | 前端仪表盘页面 |

详细 API 响应格式见 `gateway.py` 源码。
