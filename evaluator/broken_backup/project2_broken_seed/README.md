# Project2 集成说明

`project2/` 是面向医院环境改造的版本，已经保留了多床位基础结构。当前这次迁移，重点把另一个项目里已经跑通的三部分能力移植了进来：

- 独立视觉模块 `vision/`
- 情绪识别结果写入 `gateway`
- 统一聊天上下文 `chat_context`

这一阶段已经加入基础身份识别和权限会话。视觉结果仍不做视觉分床，但会识别护士站当前操作者，并由 gateway 按 session 裁剪上下文。

## 当前目录

```text
project2/
├── gateway/                     # 多床位网关 / API / Dashboard
│   ├── bed_config.py
│   ├── config.py
│   ├── db.py
│   ├── auth.py
│   ├── subjects.py
│   ├── sensor_store.py
│   ├── esp_store.py
│   ├── sleep_importer.py
│   ├── utils.py
│   ├── gateway.py
│   ├── admin.html
│   └── dashboard.html
├── posture/                     # 睡姿分类 Worker
├── vision/                      # 视觉模块：mock / camera / emotion / identity
│   ├── frame_source.py
│   ├── emotion_runtime.py
│   ├── identity_runtime.py
│   ├── vision_worker.py
│   ├── models/
│   │   ├── face_detection_yunet_2023mar.onnx
│   │   └── emotion_mamba.onnx
│   └── README.md
├── voice/                       # 语音交互与 RKLLM 对话
├── sleep_deploy_pack/           # 睡眠算法及示例输出
├── rkllm_py/                    # RKLLM SDK
├── start_project.py             # 一键启动入口
├── requirements.txt
└── gateway/README.md            # gateway 内部模块说明
```

## Gateway 模块拆分

`gateway.py` 现在只保留 HTTP 路由、页面服务、启动入口和 Bemfa 订阅主循环。其它职责已经拆到独立模块：

- `config.py`：环境变量、路径和运行参数
- `db.py`：SQLite 连接、建表和床位配置同步
- `auth.py`：首次创建超级管理员、登录、Cookie 管理会话
- `subjects.py`：人员、床位绑定、记忆、凭据、身份匹配和会话
- `sensor_store.py`：传感器、睡眠、姿态、情绪历史缓存
- `esp_store.py`：ESP32 ToF/MLX 二进制帧和完整 set 聚合
- `sleep_importer.py`：睡眠 CSV 导入与无房床字段归属策略
- `utils.py`：通用类型转换、时间、JSON 和 ID 工具

更详细的维护说明见 `gateway/README.md`。

## 当前架构

```text
巴法云 / 传感器 / ESP32
        |
        v
     gateway
        |
        +--> dashboard
        +--> posture worker
        +--> vision worker -> emotion + identity observation
        +--> subject/session policy -> unified chat context
                           |
                           v
                         voice
```

## 这次迁移完成的内容

### 1. Gateway 增加 emotion 与统一上下文

新增能力：

- `emotion` 存储与最新快照
- `/api/v2/emotion/latest`
- `/api/v2/emotion/history`
- `/api/v2/voice/emotion_context`
- `/api/v2/voice/chat_context`
- `/api/v3/context/chat`
- `/api/v2/ingest/emotion`
- `/api/v3/credentials/enroll`
- `/api/v3/identity/gallery`
- `/api/v3/identity/match`
- `/api/v3/vision/observation`

统一聊天上下文由 gateway 按当前 session 权限裁剪后返回，当前会聚合：

- 当前操作者身份、认证级别和情绪
- 目标床位/患者的睡眠摘要
- 生命体征、体动、鼾声等实时摘要
- 睡姿结果
- subject 级记忆摘要

### 2. Vision 模块独立并接入 session

当前视觉模块已从 demo 程序中抽离，具备：

- `mock` 模式联调
- `camera` 模式取流
- YuNet 人脸检测
- `emotion_mamba.onnx` + `onnxruntime` 的 CPU 推理
- 人脸照片注册为向量凭据
- 摄像头主脸与 gateway face gallery 比对
- 识别结果写入当前 session，供权限裁剪使用

默认运行频率约 `1Hz`，优先保证板端不被抢占。

### 3. Voice 改为使用统一上下文

语音侧不再直接拼 v2 睡眠、姿态、情绪接口。普通聊天和心率、睡眠、离床、睡姿、鼾声这些床位/患者类意图，统一读取：

- `/api/v3/context/chat`

当前注入策略：

- gateway 先判断当前 session 是否完成认证
- gateway 按 actor role 和 target patient 裁剪上下文
- voice 只消费 `policy / actor / target / modalities / brief / prompt_hints`
- 未认证或无权限时，voice 只回复权限提示，不返回患者数据

### 4. Dashboard 增加情绪面板

前端现在可以直接看到：

- 视觉在线状态
- 当前情绪
- 置信度
- 镜头内人数
- 视觉源 / 状态
- 稳定时长
- 推理耗时
- 推理次数

## 当前简化策略

为了先把板端联调跑通，这一版先保持下面的简化假设：

- 暂时不做视觉分床
- 人脸识别先采用本地 OpenCV 特征向量，后续可替换为 ArcFace/InsightFace
- 权限裁剪已经接入 v3 context，只有 recognized 且有 assurance 的 session 才可读目标上下文
- 情绪结果默认写入当前配置里的首个床位
- 指纹、卡片等认证方式先保留 credential/enroll 接口，不做真实采集

这和你当前的开发目标一致：先验证视觉链路、网关展示和对话注入是否可行。

## 安装依赖

```bash
pip install -r requirements.txt
```

新增视觉相关依赖：

- `onnxruntime`
- `opencv-contrib-python`

`FaceDetectorYN` 依赖 contrib 版本的 OpenCV。

## ESP32 配置方式

两个 ESP32 程序现在采用“统一固件 + NVS 配置”：

- `esp32/sketch_jan22a/sketch_jan22a.ino`：上传 `radar / env / audio`
- `esp32/testpro4/main/main.cpp`：上传 `tof1 / tof2 / mlx1 / mlx2`，本任务需要恢复 Wi-Fi + MQTT 巴法云回传

WiFi、巴法云 UID、房间和床位不再写死在源码里。烧录统一固件后，通过串口命令写入配置，例如：

```text
CFGSET ssid=HospitalWiFi
CFGSET password=your_password
CFGSET uid=your_bemfa_uid
CFGSET room=R1203
CFGSET bed=B1
CFG?
REBOOT
```

详细说明见 `esp32/NVS_CONFIG.md`。

## 启动方式

### 推荐：无摄像头联调

```bash
python start_project.py --target all --voice-input text --with-posture --with-vision --vision-source mock --voice-room R1203 --voice-bed B1
```

### 仅启动网关

```bash
python start_project.py --target gateway
```

首次打开 `http://127.0.0.1:8765/admin` 或 `/dashboard` 时，如果还没有超级管理员账户，会进入初始化页面。创建后管理台和管理类 API 需要登录。本机 worker/voice 的服务接口仍可在本机调用，便于单护士站联调。

### 启动语音

```bash
python start_project.py --target voice --voice-input text --voice-room R1203 --voice-bed B1
```

### 后续有摄像头时

```bash
python start_project.py --target all --voice-input text --with-posture --with-vision --vision-source camera --vision-camera-index 0 --voice-room R1203 --voice-bed B1
```

## 启动参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--target` | 启动 `all / gateway / voice` | `all` |
| `--voice-input` | `mic / text` | `text` |
| `--with-posture` | 启动睡姿 worker | 关闭 |
| `--posture-poll-interval` | 睡姿轮询间隔（秒） | `2.0` |
| `--with-vision` | 启动视觉 worker | 关闭 |
| `--vision-source` | `mock / camera / auto` | `mock` |
| `--vision-interval` | 视觉推理间隔（秒） | `1.0` |
| `--vision-camera-index` | 摄像头索引 | `0` |
| `--vision-mock-label` | mock 模式默认情绪 | `自然` |
| `--vision-identity` | 是否启用视觉身份识别，`on / off` | `on` |
| `--vision-mock-subject-id` | mock 模式绑定的 subject_id | 空 |
| `--voice-room` | 语音绑定房间 | `R1203` |
| `--voice-bed` | 语音绑定床位 | `B1` |
| `--voice-session-id` | 指定 voice 使用的 gateway session | 空，默认使用当前 session |
| `--voice-subject-id` | 指定 voice 查询的目标 subject | 空，默认使用 `voice-room/voice-bed` |

## 关键接口

### 当前床位快照

```text
GET /api/v2/latest?room=R1203&bed=B1
```

### 情绪结果

```text
GET  /api/v2/emotion/latest?room=R1203&bed=B1
GET  /api/v2/emotion/history?room=R1203&bed=B1&limit=20
POST /api/v2/ingest/emotion
```

### 对话上下文

```text
GET /api/v3/context/chat?target_room=R1203&target_bed=B1
GET /api/v3/context/chat?session_id=sess_xxx&target_subject_id=sub_patient_xxx
```

`/api/v2/voice/*` 仍保留兼容，但 voice 主程序已经切到 v3 授权上下文。

### 人员、认证与视觉会话

```text
GET  /admin
POST /api/v3/subjects
POST /api/v3/credentials/enroll
GET  /api/v3/identity/gallery?type=face
POST /api/v3/identity/match
POST /api/v3/vision/observation
GET  /api/v3/session/current
```

`/api/v3/credentials/enroll` 当前支持 `type=face` 图片上传自动向量化；其他认证方式可以先按同一接口提交 `template/payload`，后续再替换为真实采集逻辑。

## 当前默认行为说明

虽然 `project2` 保留了多床位结构，但本次迁移为了尽快验证视觉链路，先采用如下默认策略：

- `voice` 仍用 `VOICE_ROOM + VOICE_BED` 作为默认 target，但只调用 `/api/v3/context/chat`
- `vision` 不主动上传 `room/bed`，它只识别当前操作者
- `gateway` 在 `/api/v2/ingest/emotion` 中会把没有床位信息的视觉情绪结果落到默认床位
- `gateway` 在 `/api/v3/context/chat` 中按当前 session 的身份、角色和目标患者裁剪上下文

后续你进入 `project2` 新工作区后，再继续做“视觉归床 / 身份识别 / 权限策略”会更自然。

## 板端验证建议

完整 RK3588 测试手册见 `RK3588_TEST_GUIDE.md`。后续切到开发板，或者让其他开发者在没有历史上下文的情况下继续测试，优先从这份文档开始。

你下一步可以先按这个顺序测试：

1. `mock` 模式启动整套服务，确认 dashboard 与 voice 都能读到 emotion。
2. 在板端验证 `vision -> gateway -> chat_context` 这条链路是否稳定。
3. 拿到摄像头后，再切到 `camera` 模式测试真实取流。
4. 最后再考虑把视觉结果映射到具体床位或主体。
