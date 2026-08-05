# ESP32-S3 多传感器数据采集系统

[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v6.0.0-blue)](https://github.com/espressif/esp-idf)
[![Platform](https://img.shields.io/badge/platform-ESP32--S3-orange)](https://www.espressif.com/)

基于 ESP32-S3 的四路传感器同步数据采集系统。当前迁移分支保留 USB CDC 本地调试通道，但 Wi-Fi + MQTT 巴法云远程回传尚未实现，需要按公开协议恢复。

---

## 📋 目录

- [系统概述](#-系统概述)
- [硬件配置](#-硬件配置)
- [系统架构](#-系统架构)
- [数据协议](#-数据协议)
- [快速开始](#-快速开始)
- [MQTT 配置](#-mqtt-配置)
- [工具说明](#-工具说明)
- [性能指标](#-性能指标)
- [项目文件](#-项目文件)

---

## 🎯 系统概述

### 主要功能

| 功能 | 说明 |
|------|------|
| **传感器** | 2× MLX90640（红外热成像，24×32）+ 2× MaixSense（ToF 深度，100×100） |
| **USB 回传** | 双路 USB CDC 虚拟串口，CDC 0 传 MLX，CDC 1 传 ToF |
| **MQTT 回传** | 待恢复：Wi-Fi + MQTT → 巴法云 (bemfa.com:9501)，Base64 编码二进制 payload |
| **数据校验** | CRC16-CCITT 每包校验，错误率 < 0.01% |
| **交替发送** | 1-2-1-2 严格交替机制，左右画面完美同步 |
| **自动波特率** | 自动检测 MaixSense 传感器波特率（115200/921600） |
| **上位机** | Python GUI 实时预览 + 数据保存 + 前端仪表盘 |
| **跨平台** | Windows / Linux / macOS |

### 版本信息

| 版本 | 日期 | 说明 |
|------|------|------|
| v4.0 | 2026-04-27 | 目标契约：巴法云 MQTT 回传（当前迁移分支待恢复） |
| v3.0 | 2026-04-25 | ESP-IDF 6.0 迁移、LAN 回传、前端仪表盘 |
| v2.0 | 2026-02-01 | 统一包格式、CRC 校验、帧解析重构 |
| v1.0 | 2026-01-31 | 初始版本 |

---

## 🔧 硬件配置

### 引脚分配

| 接口 | 引脚 | 设备 |
|------|------|------|
| **I2C** | SDA: GPIO 1, SCL: GPIO 2 | MLX90640 × 2（地址 0x33 / 0x34） |
| **UART1** | TX: GPIO 17, RX: GPIO 18 | MaixSense ToF 传感器 1 |
| **UART2** | TX: GPIO 47, RX: GPIO 48 | MaixSense ToF 传感器 2 |
| **USB** | 内置 USB OTG (TinyUSB) | CDC 0（MLX）/ CDC 1（ToF） |

### 传感器参数

| 参数 | MLX90640 | MaixSense ToF |
|------|----------|---------------|
| 分辨率 | 24 × 32（768 像素） | 100 × 100（10000 像素） |
| 帧率 | 4 FPS | 8 FPS（可调 1–20） |
| 接口 | I2C | UART（921600 baud） |
| 数据 | float32 温度值 | uint8 深度值 |
| 每帧大小 | 3072 字节 | ~10000 字节 |

---

## 🏗 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                        ESP32-S3                           │
├──────────────────────────────────────────────────────────┤
│  I2C (GPIO 1/2)   │ UART1 (17/18)  │ UART2 (47/48)      │
│   ├ MLX90640 #1    │  ├ ToF #1      │  ├ ToF #2           │
│   └ MLX90640 #2    │  └ (921600)    │  └ (921600)         │
├───────────────────┴───────────────┴──────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────┐   │
│  │ MLXManager   │  │ MaixSense Frame Parser ×2        │   │
│  │ (C++ thread) │  │ (12KB buffer + CRC)              │   │
│  └──────┬───────┘  └──────────┬───────────────────────┘   │
│         │                     │                            │
│         ▼                     ▼                            │
│  ┌────────────────────────────────────────┐               │
│  │      交替发送调度器 (1-2-1-2)          │               │
│  └────┬──────────────┬────────────────────┘               │
│       │              │                                     │
│       ▼              ▼                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐     │
│  │ USB CDC0 │  │ USB CDC1 │  │ Wi-Fi → MQTT         │     │
│  │ (MLX)    │  │ (ToF)    │  │ → 巴法云 bemfa.com   │     │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘     │
└───────┼──────────────┼───────────────────┼─────────────────┘
        │              │                    │
        ▼              ▼                    ▼
   ┌─────────┐  ┌─────────┐  ┌──────────────────────────┐
   │ PC 上位机│  │ PC 上位机│  │ 巴法云 → 本地 Gateway    │
   │  MLX GUI │  │  ToF GUI │  │ → Dashboard / Posture   │
   └─────────┘  └─────────┘  └──────────────────────────┘
```

### 数据传输流程

1. **MLX90640** → I2C → MLXManager → 交替调度器 → USB CDC 0；修复后并行 MQTT (base64 JSON)
2. **MaixSense** → UART → Frame Parser（ESP32 端完成帧边界识别） → 交替调度器 → USB CDC 1；修复后并行 MQTT (base64 JSON)

---

## 📦 数据协议

所有传感器使用 **统一数据包格式**，详见 [docs/protocol.md](docs/protocol.md)。

### 快速参考

```
[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]
│       │      │    │       │       │            │
│       │      │    │       │       │            └ CRC16-CCITT（小端序）
│       │      │    │       │       └ 传感器数据
│       │      │    │       └ 数据长度高字节
│       │      │    └ 数据长度低字节
│       │      └ 传感器 ID（1 / 2）
│       └ 类型: 0x01 = MLX, 0x02 = ToF
└ 同步头 (0xAA 0x55)
```

---

## 🚀 快速开始

### 1. 编译统一固件

`main/main.cpp` 不再写死 WiFi、巴法云 UID、房间和床位。固件只需要编译一次，具体床位配置通过 NVS 写入。

### 2. 编译烧录

```powershell
# 推荐从 workspace 根目录运行，脚本会复制到受控构建目录，不污染源码
python tools\run_espidf_build.py project2_task

# 如需直接在固件目录操作：
. '$env:ESP_IDF_ACTIVATION_SCRIPT'
idf.py set-target esp32s3
idf.py build

# 烧录 + 监控
idf.py flash monitor
```

### 3. 写入 NVS 配置

在 monitor 中输入：

```text
CFGSET ssid=HospitalWiFi
CFGSET password=your_password
CFGSET uid=your_bemfa_uid
CFGSET room=R1203
CFGSET bed=B1
CFGSET device_id=esp32-r1203-b1-posture-001
CFG?
REBOOT
```

更多说明见 `../NVS_CONFIG.md`。

**修复后预期 monitor 输出**:
```
I (xxx) MAIN: ESP32-S3 Multi-Sensor Bridge Starting...
I (xxx) MAIN: Config role=posture_sensors ready=yes
I (xxx) MAIN: WiFi+MQTT init done, MQTT target=bemfa.com:9501
I (xxx) MAIN: WiFi connected, IP=192.168.x.x
I (xxx) MAIN: MQTT client started, UID=***
I (xxx) MAIN: MQTT connected to bemfa.com
I (xxx) MAIN: MQTT topics: r1203b1tof1 / r1203b1tof2 / r1203b1mlx1 / r1203b1mlx2
I (xxx) MAIN: System Ready.
```

### 4. 本地 USB 调试（可选）

```bash
# 运行上位机（USB CDC 可视化）
python3 collectdata_esp32.py
```

## 📡 MQTT 配置目标

### 巴法云 Topic 命名

| Topic | 数据内容 | 编码 |
|-------|---------|------|
| `{room}{bed}tof1` | MaixSense ToF Sensor 1 深度帧 | Base64 JSON |
| `{room}{bed}tof2` | MaixSense ToF Sensor 2 深度帧 | Base64 JSON |
| `{room}{bed}mlx1` | MLX90640 Sensor 1 温度阵 | Base64 JSON |
| `{room}{bed}mlx2` | MLX90640 Sensor 2 温度阵 | Base64 JSON |

### MQTT 消息格式

```json
{"payload_b64": "<base64编码的二进制数据>"}
```

- MLX: 768 float32 = 3072 bytes → base64 ≈ 4096 chars
- ToF: ~10000 bytes → base64 ≈ 13333 chars

### 多床位部署

| 床位 | NVS `room` | NVS `bed` | 示例 Topic |
|------|------------|-----------|-----------|
| R1203 床1 | R1203 | B1 | r1203b1tof1 |
| R1203 床2 | R1203 | B2 | r1203b2tof1 |
| R1204 床1 | R1204 | B1 | r1204b1tof1 |

---

## 🛠 工具说明

| 文件 | 用途 | 依赖 |
|------|------|------|
| `collectdata_esp32.py` | **USB 上位机**：实时 4 路可视化 + 数据保存 | pyserial, numpy, pillow, tkinter |
| `../../gateway/gateway.py` | **项目网关**：巴法云 TCP 订阅 → REST API + 仪表盘 | Python 3.x |
| `../../gateway/dashboard.html` | **前端仪表盘**：多床位可视化 | 浏览器 |

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| MLX 帧率 | 4 FPS × 2（250ms/帧） |
| ToF 帧率 | 8 FPS × 2（125ms/帧） |
| USB 总带宽 | ~160 KB/s |
| MQTT 单包大小 | MLX: ~4KB / ToF: ~13KB |
| 最大延迟 | <125ms |
| ESP32 CPU | <50% |
| ESP32 内存 | 44% free |

---

## 📁 项目文件

```
testpro4/
├── main/                         # ESP32 主程序
│   ├── main.cpp                  # 主逻辑：传感器采集、USB 发送，需恢复 MQTT glue
│   ├── CMakeLists.txt            # 组件编译配置，需补齐 mqtt + mbedtls 等依赖
│   ├── tusb_config.h             # TinyUSB 配置
│   └── usb_descriptors.c         # USB 描述符（2 路 CDC）
├── components/
│   └── mlx90640/                 # MLX90640 驱动组件 (不变)
├── docs/
│   └── protocol.md               # 数据协议规范
├── CMakeLists.txt                # 项目级 CMake 配置
├── sdkconfig                     # ESP-IDF 配置
└── build/                        # 编译输出
```

## ❓ 常见问题

**Q: MQTT 连接不上巴法云？**
A: 执行 `CFG?` 确认 `ready=yes`，并检查 WiFi、巴法云 UID 是否正确。

**Q: 如何切换床位？**
A: 执行 `CFGSET room=R1203` 和 `CFGSET bed=B1` 后 `REBOOT`，不需要重新编译固件。

**Q: USB CDC 设备找不到？**
A: `dmesg | grep tty` 检查内核消息，可能需要 `sudo usermod -aG dialout $USER`。

**Q: ToF 画面黑屏？**
A: 等待 5–10 秒传感器初始化；检查 monitor 日志确认初始化成功。

**Q: 如何调整传感器帧率？**
A: 修改 `main.cpp` 中 MaixSense 的 AT+FPS 参数，MLX 帧率在 `MLXManager.hpp` 中调整。
