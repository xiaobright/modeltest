# 快速开始指南

## 快速上手

### 1. 编译统一固件

`main/main.cpp` 的目标形态是不再写死 WiFi、巴法云 UID、房间和床位。当前迁移分支需要先恢复 Wi-Fi + MQTT 回传，再用 NVS 写入具体床位配置。

### 2. 编译 & 烧录

```powershell
# 在 workspace 目录运行推荐编译入口
python tools\run_espidf_build.py project2_task

# 直接烧录时进入固件目录并激活 Windows ESP-IDF
Set-Location .\project2_task\esp32\testpro4
. '$env:ESP_IDF_ACTIVATION_SCRIPT'
idf.py flash
idf.py monitor
```

当前开发机固定使用 Windows ESP-IDF v6.0.1。这个固件目录从旧版 ESP-IDF 迁移而来，遇到组件依赖或 Component Manager 相关编译错误时，以当前构建输出为准修复声明，不要降级 IDF 或更换目标芯片。

### 3. 写入 NVS 配置

在 `idf.py monitor` 中输入：

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

**修复后预期输出 (monitor窗口):**
```
I (xxx) MAIN: ESP32-S3 Multi-Sensor Bridge Starting...
I (xxx) MAIN: Config role=posture_sensors ready=yes
I (xxx) MAIN: WiFi+MQTT init done, MQTT target=bemfa.com:9501
I (xxx) MAIN: Waiting for ToF sensors to boot...
I (xxx) MAIN: Sending MaixSense configuration commands...
I (xxx) MAIN: MaixSense configuration completed
I (xxx) MAIN: MLXManager started successfully
I (xxx) MAIN: MQTT topics: r1203b1tof1 / r1203b1tof2 / r1203b1mlx1 / r1203b1mlx2
I (xxx) MAIN: MQTT connected to bemfa.com
I (xxx) MAIN: System Ready.
```

### 4. 验证数据

完成 Wi-Fi + MQTT 修复后，在项目网关所在的机器上：

```bash
# 启动网关（需设置 BEMFA_UID）
export BEMFA_UID="your_bemfa_uid"
python gateway/gateway.py

# 浏览器打开仪表盘，确认数据到达
# http://127.0.0.1:8765/dashboard
```

### 5. USB 本地调试（可选）

```powershell
python .\collectdata_esp32.py
```

## ⚙️ 故障排除

### 问题1: MQTT 连接不上巴法云

**原因**: UID 未配置或 WiFi 未连接

**解决**:
1. 在 monitor 中执行 `CFG?`，确认 `ready=yes`
2. 确认 WiFi SSID/密码正确
3. 查看 monitor 日志确认连接状态

### 问题2: 没有 USB CDC 设备

**原因**: USB 未连接或驱动问题

**解决**:
```bash
dmesg | tail -20
sudo chmod 666 /dev/ttyACM*
```

### 问题3: 数据显示异常或黑屏

**原因**: 传感器未初始化或数据包损坏

**解决**:
1. 检查 ESP32 日志: `idf.py monitor`
2. 等待传感器初始化（5-10 秒）
3. 按下开发板 RST 按钮重启

## 📊 数据格式说明

### 保存的文件结构

```
collected_data/
└── <场景名>/
    ├── cam1/00000.bin      # ToF1深度数据 (100x100 uint8)
    ├── cam2/00000.bin      # ToF2深度数据 (100x100 uint8)
    ├── long/00000.bin      # MLX1温度数据 (32x24 float32)
    ├── wide/00000.bin      # MLX2温度数据 (32x24 float32)
    └── preview/00000.png   # 预览图像
```

### 读取数据示例

```python
import numpy as np

# 读取ToF深度数据
depth = np.fromfile('cam1/00000.bin', dtype=np.uint8).reshape(100, 100)

# 读取MLX温度数据
temps = np.fromfile('long/00000.bin', dtype=np.float32).reshape(32, 24)

print(f"深度范围: {depth.min()} ~ {depth.max()}")
print(f"温度范围: {temps.min():.2f}°C ~ {temps.max():.2f}°C")
```

## 🔧 性能优化建议

### 提高帧率

修改 `components/mlx90640/include/MLXManager.hpp`:
```cpp
// 原值: FPS = 2 (0.5秒/帧)
static const int FPS = 2;

// 改为: FPS = 4 (0.25秒/帧)
static const int FPS = 4;
```

### 降低数据量

如果USB传输不稳定,可以考虑:
1. 只使用一个ToF传感器
2. 降低MLX刷新率
3. 实现数据压缩

## 📞 获取帮助

- 查看详细文档: [README_ESP32.md](README_ESP32.md)
- 查看更新日志: [CHANGELOG.md](CHANGELOG.md)
- 运行CRC测试: `python3 test_crc.py`
