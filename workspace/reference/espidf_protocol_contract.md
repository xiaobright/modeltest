# ESP-IDF Build And Protocol Notes

本任务必须修复 `esp32/testpro4`。这份说明用于保持固件工程、gateway 和采集 worker 的协议一致性。

## Windows ESP-IDF 编译

- 不使用 Docker 或 WSL。
- 默认使用 Windows EIM 安装的 ESP-IDF v6.0.1。
- Windows 激活脚本：`$env:ESP_IDF_ACTIVATION_SCRIPT`。
- 推荐命令：`python tools\run_espidf_build.py project2_task`。
- 脚本会先复制 `esp32/testpro4` 到 `$env:ESP_IDF_BUILD_ROOT\project2_task`，再运行 `idf.py -B build set-target esp32s3` 和 `idf.py -B build build`。

## 不在本地编译中验证的内容

- 不要求 `idf.py flash` 或 `idf.py monitor`。
- 不评价 ToF 上电冷启动等待、自动波特率探测、AT 命令时序。
- 不评价真实 USB 枚举、真实 Wi-Fi/MQTT 连通性、真实 I2C 温度读数。

## USB Packet

```text
[AA 55] [TYPE] [ID] [LEN_L] [LEN_H] [PAYLOAD...] [CRC_L] [CRC_H]
```

- `TYPE=0x01`：MLX90640。
- `TYPE=0x02`：MaixSense ToF。
- CRC16-CCITT：初始值 `0xFFFF`，多项式 `0x1021`。
- CRC 只覆盖 payload，不覆盖 header。
- `LEN` 和 CRC 都是小端序。

## ToF Payload

ToF payload 默认保持完整 MaixSense 原始帧：

```text
[00 FF] [LEN_L LEN_H] [META(16)] [IMG(10000)] [CHECKSUM] [DD]
```

不要只输出 10000B 图像区，除非同步更新 collector 和 gateway 契约。

## MQTT

Topic 小写拼接：

```text
{room}{bed}tof1
{room}{bed}tof2
{room}{bed}mlx1
{room}{bed}mlx2
```

JSON：

```json
{"payload_b64": "<base64 raw payload>"}
```

base64 内容是原始 payload，不是完整 USB packet。
