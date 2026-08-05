# ESP32 统一固件 + NVS 配置说明

目标是两个 ESP32 程序都采用“固件只编译一次，床位/WiFi/巴法云配置写入 NVS”。当前 `testpro4` 迁移分支已保留 NVS 配置读取骨架，但仍需要恢复 Wi-Fi + MQTT 回传。

涉及文件：

- `esp32/sketch_jan22a/sketch_jan22a.ino`
  - 角色：`radar_env_audio`
  - 上传：`radar / env / audio`
- `esp32/testpro4/main/main.cpp`
  - 角色：`posture_sensors`
  - 上传：`tof1 / tof2 / mlx1 / mlx2`

## 配置项

NVS namespace：

```text
project2
```

核心配置：

```text
wifi_ssid
wifi_pass
bemfa_uid
bemfa_host    默认 bemfa.com
bemfa_port    默认 9501
room          例如 R1203
bed           例如 B1
device_id     可选
```

topic 不直接存储，由 `room + bed + 数据类型` 自动拼接：

```text
r1203b1radar
r1203b1env
r1203b1audio
r1203b1tof1
r1203b1tof2
r1203b1mlx1
r1203b1mlx2
```

## 串口配置命令

两套固件使用同一套命令：

```text
CFG?
CFGSET ssid=your_wifi
CFGSET password=your_password
CFGSET uid=your_bemfa_uid
CFGSET room=R1203
CFGSET bed=B1
CFGSET host=bemfa.com
CFGSET port=9501
CFGSET device_id=esp32-r1203-b1-radar-001
CFGRESET
REBOOT
```

说明：

- `CFG?` 查看当前配置，密码和 UID 只显示是否存在。
- `CFGSET key=value` 立即写入 NVS。
- 写完配置后执行 `REBOOT`，让网络和 topic 重新初始化。
- `CFGRESET` 清空 NVS 中的 `project2` 配置。

## 首次配置流程

1. 烧录统一固件。
2. 打开串口监视器。
3. 写入配置：

```text
CFGSET ssid=HospitalWiFi
CFGSET password=your_password
CFGSET uid=your_bemfa_uid
CFGSET room=R1203
CFGSET bed=B1
CFGSET device_id=esp32-r1203-b1-radar-001
CFG?
REBOOT
```

4. 重启后设备会自动：

```text
读取 NVS -> 连接 WiFi -> 连接巴法云 MQTT -> 自动拼接 topic -> 上传数据
```

## 配置不完整时的行为

如果缺少 `wifi_ssid / bemfa_uid / room / bed` 等必要配置：

- 设备不会连接 WiFi。
- 设备不会连接 MQTT。
- 串口会打印配置帮助。
- 仍可继续通过串口写入 NVS 配置。

## 批量部署建议

当前最简单可靠的方式是：

```text
统一固件 + 串口命令写 NVS + REBOOT
```

后续如果床位数量较多，可以进一步做：

- ESP-IDF 的 NVS 分区批量生成。
- 烧录同一 app 固件，再刷不同床位的 NVS 分区。
- 或由 gateway 维护设备注册中心，让设备按 `device_id` 拉取配置。

## 安全注意

- WiFi 密码和巴法云 UID 不再写入源码。
- NVS 不是强安全存储，真实部署时建议进一步评估：
  - NVS encryption
  - flash encryption
  - 每设备独立 token
  - 配置写入需要物理按键或管理员确认
