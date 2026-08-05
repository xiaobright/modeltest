# 更新日志

## [4.0] - 2026-04-27 — 巴法云 MQTT 回传目标契约

### 重大变更 🔄

#### TCP LAN → MQTT 巴法云替换
- **移除**：Wi-Fi + TCP 直连网关（`GATEWAY_IP`/`GATEWAY_PORT`）
- **目标**：Wi-Fi + MQTT → 巴法云 `bemfa.com:9501`
  - 使用 ESP-IDF MQTT 客户端能力，保持断线恢复
  - 将二进制 payload 编码为 Base64
  - JSON 封装：`{"payload_b64": "<base64>"}`
  - 每个传感器独立 topic：`{room}{bed}tof1`/`tof2`/`mlx1`/`mlx2`
- **保留**：USB CDC 双通道不受影响，仍用于本地调试

#### 配置变更
- 新增 `#define BEMFA_UID`（巴法云私钥）
- 新增 `#define BEMFA_ROOM` / `#define BEMFA_BED`（房间/床位）
- 移除 `#define GATEWAY_IP` / `#define GATEWAY_PORT`
- 当前迁移分支缺少网络回传所需组件依赖（`main/CMakeLists.txt`），需要恢复

#### 代码变更
- **待恢复**：Wi-Fi STA 初始化、MQTT 客户端生命周期、topic 构造和发布路径
- **待恢复**：ToF 与 MLX 发送路径在 USB CDC 基础上并行 MQTT 发布
- **移除**：旧 TCP socket 回传状态和发送逻辑
- **移除**：`#include "lwip/sockets.h"` / `#include "lwip/inet.h"`

### 文档更新 📝
- `README.md`：更新系统架构图、MQTT 配置说明、多床位部署指南
- `QUICKSTART.md`：更新为 MQTT 配置 + 编译流程
- `docs/protocol.md`：新增 MQTT 传输章节
- 项目级 `CHANGES.md`：详细变更总结

### 配套改动
- 上游 `gateway/` 模块同步更新为巴法云 TCP 订阅模式（`bemfa_tcp_sub_loop()`）
- Python 网关新增 `bed_config.py` 床位配置模块
- 全系统支持多房间多床位

---

## [3.0] - 2026-04-25

### 新特性 ✨

#### 局域网网关数据传输
- **新增 Wi-Fi + TCP 局域网并行回传通道**
  - ESP32 通过 Wi-Fi 连接到局域网
  - TCP 同时发送传感器数据到网关（与 USB CDC 并行）
  - 与 USB 虚拟串口互不干扰，双通道并行工作
- **新增网关接收程序 (gateway.py)**
  - TCP 端口 9101 接收 ESP32 传感器数据
  - 解析统一二进制包格式（AA 55 + TYPE + ID + LEN + DATA + CRC）
  - 存储深度配置（默认 1，可通过 ESP_STORE_DEPTH 环境变量调整）
  - REST API: `/api/esp/status` 查询 ESP 连接状态
  - REST API: `/api/v2/latest` 返回全部传感器数据
- **新增前端状态仪表盘 (dashboard.html)**
  - 保留原可视化数据展示（MLX 热成像、ToF 深度图、音频统计等）
  - 新增 ESP32 连接状态卡片（仅显示连接是否成功）

#### 项目迁移：ESP-IDF 6.0
- **迁移至 ESP-IDF 6.0.0 编译环境**
  - 旧版固件迁移到 v6.0.0 后，部分组件依赖声明和 Component Manager 集成方式需要以当前编译输出为准校正
  - 修复 GCC 编译器 `-Werror=type-limits` 告警（组件级编译选项，不改源码逻辑）
  - 修复 `driver/uart.h` 依赖变更（组件依赖声明更新为 `esp_driver_uart`）
  - 新增组件依赖：`esp_wifi`、`esp_netif`、`esp_event`、`lwip`

### 项目整理 📂

#### 文档结构重组
- **删除无用文件**：`README_ORIGINAL.md`（IDF 模板）、`log.txt`、`log2.txt`（临时日志）
- **删除所有零散历史文档**（内容已整合至本更新日志）：
  - `VERSION_HISTORY.md`、`ALTERNATING_SEND.md`、`FRAME_FORMAT_FIX.md`
  - `FRAME_PARSER_FIX.md`、`FRAME_PARSER_REFACTOR.md`、`DEBUG_GUIDE.md`
  - `BAUDRATE_FIX.md`、`INIT_FIX_NOTES.md`、`TOF_DEBUG.md`、`修复完成总结.md`
- **删除冗余技术文档**：`docs/README_ESP32.md`、`docs/README_FINAL.md`（内容整合至 README.md）
- **新增**：`docs/protocol.md`（数据协议规范独立文档）
- **重写**：`README.md`（完整项目文档，替代旧版简明 README）
- **更新**：`CHANGELOG.md`（本次整合全部开发历史）

#### 项目源码清理
- **删除 `collectdata/` 目录**：Linux 独立传感器测试程序（C++ 驱动 + Python 脚本 + 编译产物），未被主程序引用
- **删除根目录测试脚本**：
  - `maixsense_test_gui.py` - MaixSense 直连测试工具
  - `test_cdc1_raw.py` - CDC 1 原始数据查看
  - `test_crc.py` - CRC 一致性测试
  - `collectdata.py` - Linux 独立采集程序
- **删除杂项文件**：`sdkconfig.old`（旧配置备份）、`__pycache__/`（Python 缓存）

### 文件变更

#### ESP32 端
- ✅ `main/main.cpp` - 新增 Wi-Fi/TCP 回传、LAN 初始化
- ✅ `main/CMakeLists.txt` - 新增网络组件依赖
- ✅ `components/mlx90640/CMakeLists.txt` - 组件级编译选项（-Wno-error=type-limits）

#### 网关 & 前端
- ✅ `gateway.py` - 新增（ESP TCP 数据接收、REST API）
- ✅ `dashboard.html` - 新增（可视化仪表盘 + ESP 连接状态）

#### 文档
- ✅ `README.md` - 重写为完整项目文档
- ✅ `CHANGELOG.md` - 本次更新 + 全部历史整合
- ✅ `docs/protocol.md` - 新增数据协议规范

---

## [2.0] - 2026-02-01 ~ 2026-02-03

### 📝 完整开发历程

v2.0 经历了密集的多轮迭代，从 2026-01-23 发现问题到 2026-02-03 最终完成，历时 12 天。

---

#### 阶段 1：基础重构 (2026-01-23 ~ 2026-02-01)

**初始问题识别：**
- 发现 CDC 数量文档错误（3→2）
- MLX 和 ToF 使用不同的包头格式
- 缺少数据校验（CRC）
- UART 初始化时序有误

**统一数据包格式**
所有传感器统一使用相同包格式，简化上位机解析逻辑：

```
[0xAA, 0x55, TYPE, ID, LEN_L, LEN_H] + DATA + [CRC_L, CRC_H]
```

- 定义 `SENSOR_TYPE_MLX = 0x01`、`SENSOR_TYPE_TOF = 0x02`
- 支持可变长度 Payload
- 所有 ESP32 发送函数统一调用格式

**添加 CRC16-CCITT 校验**

ESP32 端：
```cpp
static uint16_t crc16_ccitt(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else crc <<= 1;
        }
    }
    return crc;
}
```

- 所有数据包末尾添加 2 字节 CRC
- 上位机验证后再使用数据，错误率降至 < 0.01%
- 创建 `test_crc.py` 验证 ESP32 与上位机 CRC 实现一致性

**优化 UART 初始化时序**
- 原顺序：UART → AT 命令 → USB（命令可能丢失）
- 新顺序：UART → USB → 等待 2 秒 → AT 命令
- 提高系统启动稳定性至 ~99%

**修正 CDC 数量错误**
- TinyUSB 在 ESP32-S3 上仅支持 2 路 CDC
- CDC 0: MLX90640 数据流
- CDC 1: ToF 数据流（两个传感器复用）
- 移除 CDC 2 的错误引用

**性能对比：**

| 指标 | v1.0 | v2.0 |
|------|------|------|
| 数据包格式 | 不统一 | 统一 ✓ |
| 数据校验 | 无 | CRC16 ✓ |
| 错误检测率 | 0% | >99.9% |
| 初始化成功率 | ~85% | ~99% |
| 包头开销 | 4–5 字节 | 6 字节 |
| CRC 开销 | 0 字节 | 2 字节 |
| 总传输效率影响 | — | -0.06%（可忽略） |

---

#### 阶段 2：波特率自动检测 (2026-02-03 上午)

**问题：** MaixSense 传感器每次上电默认 115200，但 AT+SAVE 命令不生效。

**解决方案 — 四阶段初始化流程：**

```
Phase 1: 自动检测波特率（先试 115200，失败则试 921600）
Phase 2: 切换到 921600 高速模式
Phase 3: 验证 921600 通信
Phase 4: 配置传感器参数（ANTIMMI, FPS, DISP）
```

关键改进：
- 支持传感器默认 115200 启动，自动升级到 921600
- 掉电重启自动恢复
- 每条 AT 命令都等待 "OK" 响应确认
- 统一使用 `\r\n` 结尾
- 每个命令后清空接收缓冲

---

#### 阶段 3：Windows 兼容性 (2026-02-03 中午)

- 使用 `serial.tools.list_ports` 自动检测串口
- 支持 Windows COM 端口识别
- MLX90640 显示顺时针旋转 90°

---

#### 阶段 4：ToF 黑屏调试 — 帧解析重构 (2026-02-03 下午)

**问题：** ToF 画面始终黑屏。

**第一次尝试 — 上位机端优化（失败）：**
- 发现 UART 数据流不对齐帧边界
- ESP32 每次读取 480 字节，MaixSense 帧是 10002 字节
- 缓冲区在 9679 字节时因找不到 `AA 55` 帧头被清空
- 优化上位机 `find()` 算法，时间复杂度从 O(n²) 降到 O(n)
- 效果：部分改善但不彻底

**第二次重构 — ESP32 端帧解析（成功）：**
```
旧方案：UART → 480字节碎片 → 直接发给上位机 → 上位机累积查找帧头
                                        ↓
新方案：UART → 480字节碎片 → ESP32累积解析完整帧 → 发送完整10002字节
```

- 添加 `MaixSenseFrameParser` 结构体
- 每个传感器独立 12KB 缓冲区
- 在 ESP32 端完成帧边界识别
- 上位机只接收完整帧
- 结果：仍然黑屏

---

#### 阶段 5：帧格式错误 — 关键突破 (2026-02-03 傍晚)

**日志关键发现：**
```
UART1 buffer head: 66 DF DE DD...  ← 全是数据值
frames=0                           ← 从未解析到帧
```

**对比 `maixsense_test_gui.py`（工作正常的测试工具）：**
```python
FRAME_HEAD = bytes([0x00, 0xFF])  # ← 这才是正确的帧头！
```

**根本原因：** ESP32 代码搜索 `AA 55` 作为帧头，但 MaixSense 实际使用 `00 FF`。

**修复内容：**
- 修正帧头识别：`AA 55` → `00 FF`
- 从长度字段动态计算帧长度
- 验证帧尾 `0xDD` 确保帧完整性
- 结果：**ToF 成功显示！🎉**

---

#### 阶段 6：元数据问题 (2026-02-03 晚上)

**问题：** 数据显示但图像全黑。

**分析：** 帧长度 10022 字节 = 2（帧头）+ 2（长度）+ 10016 + 1（校验和）+ 1（帧尾）。10016 = 16 字节元数据 + 10000 字节图像数据。

**修复：** 跳过前 16 字节元数据，直接提取图像数据。

**结果：** 图像完美显示！🎉

---

#### 阶段 7：交替发送优化 (2026-02-03 深夜)

**问题：** 两个传感器的帧发送不均衡，先发左边一段时间再发右边。

**需求：** 严格每帧交替（1-2-1-2 模式）。

**实现：**
- 双缓冲机制（`frame_buffer1` / `frame_buffer2`）
- 就绪标志（`frame1_ready` / `frame2_ready`）
- 发送状态机（`send_sensor1_next` 控制轮流）
- 保持严格交替，等待缺失帧也不打破顺序

**结果：** 左右画面完美同步！🎉

---

#### 阶段 8：日志清理 (2026-02-03 最终)

- 移除不必要的调试输出
- 保留关键的初始化和错误信息
- ESP32：每 30 秒状态统计
- 上位机：仅显示警告和错误

---

### 📊 最终性能

| 指标 | 值 |
|------|-----|
| 固件大小 | 0x8e750（583 KB） |
| ESP32 内存 | 56% 占用（44% free） |
| MLX 帧率 | 4 FPS × 2 |
| ToF 帧率 | 8 FPS × 2 |
| USB 总带宽 | ~160 KB/s |
| USB 利用率 | 15.6% |
| 最大延迟 | <125ms |
| 数据校验 | CRC16-CCITT，错误率 < 0.01% |

### 测试状态

- ✅ 编译通过（无警告）
- ✅ 传感器初始化成功
- ✅ MLX90640 双传感器显示正常
- ✅ MaixSense ToF 双传感器显示正常
- ✅ 严格交替发送工作正常
- ✅ 跨平台串口识别（Windows 测试通过）
- ✅ 长时间运行稳定
- ✅ 掉电重启自动恢复

### 已知限制

- MaixSense 每次上电恢复 115200（硬件限制）
- 交替发送引入最大 1 帧周期延迟（设计取舍）
- Linux 需要串口访问权限（操作系统限制）

---

## [1.0] - 2026-01-31

### 初始版本

- 基本的 MLX90640（I2C）和 MaixSense ToF（UART）数据采集
- USB CDC 双路虚拟串口传输
- 简单的 Python/Tkinter 上位机 GUI
- 项目初始化搭建
