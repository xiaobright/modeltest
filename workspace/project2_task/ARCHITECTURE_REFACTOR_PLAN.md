# Project2 完整改造方案

## 1. 目标定位

`project2` 的最终形态不是单纯的传感器展示 demo，而是一个面向医院/护理场景的本地智能网关系统。

核心目标：

- 每个床位的设备独立联网。
- 设备通过巴法云上传床位传感器数据。
- 本地 gateway 订阅巴法云数据，按床位处理、存储、展示。
- 前端同时支持床位视图和患者视图。
- 摄像头位于网关/护士站侧，用于识别当前操作者的人脸和情绪。
- 人脸识别辅助权限管理，情绪识别辅助大模型对话风格。
- 患者、工作人员、权限、记忆按 `subject` 管理，不直接绑定死在床位上。
- 大模型上下文由 gateway 统一拼接和裁剪，voice 只消费已经授权的上下文。
- ESP32 固件改为统一固件 + NVS 配置，不再为每张床位重新改源码编译。

当前阶段仍然以可落地、可联调为优先，不急于一次性实现完整后台管理系统，但数据结构和接口要为后续扩展留好位置。

## 2. 总体架构

```text
床位 ESP32 设备
  - radar / env / audio
  - tof1 / tof2 / mlx1 / mlx2
        |
        v
巴法云 MQTT/TCP 中继
        |
        v
本地 gateway
  ├─ 巴法云订阅
  ├─ 按床位解析和存储传感器数据
  ├─ 睡姿 worker / 睡眠算法结果接入
  ├─ 护士站视觉模块
  │   ├─ 人脸检测
  │   ├─ 表情识别
  │   └─ 人脸身份识别
  ├─ subject / bed / assignment / credential / memory 管理
  ├─ 权限会话和上下文裁剪
  ├─ dashboard API
  └─ chat context API
        |
        +--> dashboard 前端
        +--> voice / RKLLM 对话
```

关键分工：

- 床位数据属于 `room + bed`。
- 人员身份、角色、认证凭据、长期记忆属于 `subject_id`。
- 患者与床位的当前关系通过 `bed_assignment` 连接。
- 当前站在网关摄像头前的人是 `actor`，不一定是被查询的患者。
- 被查询的患者或床位是 `target`。
- gateway 根据 `actor`、`target` 和权限策略生成大模型上下文。

## 3. 床位模型

医院床位通常是相对固定的，因此床位拓扑建议作为稳定配置维护。

当前可以继续沿用：

```text
R1203-B1
R1203-B2
R1204-B1
```

后续可以扩展字段：

```json
{
  "room": "R1203",
  "bed": "B1",
  "display_name": "1203房 1床",
  "ward": "sleep-care",
  "enabled": true,
  "device_group": "r1203b1",
  "notes": ""
}
```

床位视图重点展示：

- 当前床位是否启用。
- 巴法云 topic 列表。
- radar/env/audio 是否在线。
- tof1/tof2/mlx1/mlx2 是否在线。
- 最近一帧 ESP set 状态。
- 姿态推理状态。
- 当前绑定患者。
- 最近告警和异常。

床位视图主要服务硬件维护和护士快速巡检。

## 4. 患者与工作人员模型

人员统一抽象为 `subject`。

建议基础字段：

```json
{
  "subject_id": "sub_000001",
  "name": "张三",
  "role": "patient",
  "status": "active",
  "gender": "",
  "age": null,
  "notes": "",
  "created_ts": 0,
  "updated_ts": 0
}
```

`role` 初期建议保留：

```text
admin     超级管理员
staff     工作人员
patient   患者
visitor   访客/家属，后续可选
unknown   未识别或未认证
```

默认系统应内置一个超级管理员，用于初始化工作人员、患者、床位绑定和认证凭据。

患者视图重点展示：

- 患者基本信息。
- 当前绑定床位。
- 历史入住/换床记录。
- 睡眠摘要。
- 生理指标摘要。
- 姿态/鼾声/环境趋势。
- 经过压缩的长期记忆和护理备注。
- 当前可用认证方式。

工作人员视图重点展示：

- 角色与权限范围。
- 是否启用。
- 可访问的病区/房间/床位。
- 认证凭据状态。

## 5. 床位绑定关系

患者不要直接写死在床位上，而应通过入住/绑定关系连接。

建议结构：

```json
{
  "assignment_id": "assign_000001",
  "subject_id": "sub_patient_001",
  "room": "R1203",
  "bed": "B1",
  "status": "active",
  "start_ts": 0,
  "end_ts": 0,
  "created_by": "sub_admin_001"
}
```

规则：

- 同一时间一张床最多一个 active 患者。
- 同一时间一个患者通常最多一个 active 床位。
- 换床时关闭旧 assignment，创建新 assignment。
- 出院时关闭 active assignment，但保留患者记忆和历史数据索引。

这样可以支持患者换床、出院、再次入院，而不会把记忆错误地留在床位上。

## 6. 护士站视觉模块

摄像头位于 gateway/护士站，不放在每张床旁边。

因此视觉模块不负责“视觉归床”，它负责识别当前操作者：

- 当前是谁。
- 是患者、工作人员、管理员还是未知人员。
- 当前情绪状态如何。
- 认证可信度有多高。

视觉处理建议复用同一条视频流：

```text
camera frame
  -> face detection
  -> face crop / align
     ├─ emotion model
     └─ face embedding model
            -> identity match
```

这样可以避免两个 worker 同时抢摄像头，也能减少重复推理。

当前 `vision/` 模块可以逐步改造成：

```text
vision/
  frame_source.py        摄像头/mock 取流
  face_detector.py       人脸检测
  emotion_runtime.py     表情识别
  identity_runtime.py    人脸 embedding 与比对
  vision_worker.py       统一调度和结果上报
```

当前阶段可以先保留 `mock` 模式，用于联调 identity 和 emotion 的数据通路。

## 7. 人脸识别方案

人脸识别通常不建议用原始图片直接逐张比对，而是使用特征向量。

标准流程：

```text
注册阶段：
  拍摄/上传人脸图像
  -> 人脸检测
  -> 人脸对齐
  -> embedding 模型
  -> 得到人脸向量
  -> 存入 credentials

识别阶段：
  摄像头实时帧
  -> 人脸检测
  -> 人脸对齐
  -> embedding 模型
  -> 当前向量
  -> 与数据库向量做相似度比对
  -> 得到候选 subject + confidence
```

数据库里主要保存：

- 人脸 embedding 向量。
- 模型名称和版本。
- 注册时间。
- 凭据状态。
- 可选的注册图像引用。

不建议把原始人脸照片作为主要比对依据。若保留注册图像，也应仅用于人工审核、重新建模或问题排查，并在后续考虑加密存储。

建议 `credentials` 结构：

```json
{
  "credential_id": "cred_000001",
  "subject_id": "sub_000001",
  "type": "face",
  "provider": "local_face_embedding",
  "template": {
    "embedding": [0.01, -0.02],
    "embedding_dim": 512,
    "model": "face_model_name",
    "model_version": "v1"
  },
  "status": "active",
  "created_ts": 0,
  "updated_ts": 0
}
```

后续指纹、工牌、NFC、PIN 都可以复用同一张 credentials 表：

```text
type: face / fingerprint / card / nfc / pin / device
```

指纹也应保存硬件或 SDK 生成的 template，而不是原始指纹图像。

## 8. 认证与权限

权限不要只依赖人脸识别。人脸识别可以作为一种认证方式，但后续应允许多因素共同认证。

统一认证结果建议抽象为：

```json
{
  "actor_subject_id": "sub_staff_001",
  "role": "staff",
  "auth_methods": ["face"],
  "confidence": 0.86,
  "assurance_level": "medium",
  "identity_state": "recognized",
  "expires_ts": 0
}
```

`assurance_level` 初期建议：

```text
none     未认证
low      仅弱识别，例如人脸低置信度
medium   单因素可靠认证，例如高置信度人脸
high     多因素认证，例如人脸 + 指纹
```

权限策略建议：

- `admin`：可管理人员、床位、凭据、绑定关系，可查看所有数据。
- `staff`：可查看授权范围内床位和患者信息。
- `patient`：只能查看自己的数据和自己的记忆摘要。
- `unknown`：只能使用非常有限的普通问答，不返回隐私数据。

后续可以加权限范围：

```json
{
  "subject_id": "sub_staff_001",
  "scope": {
    "wards": ["sleep-care"],
    "rooms": ["R1203", "R1204"],
    "beds": []
  },
  "permissions": [
    "bed.read",
    "patient.read",
    "sensor.read",
    "memory.read_summary"
  ]
}
```

## 9. 会话模型

当有人站在护士站前使用系统时，gateway 应创建或更新一个短期 session。

建议结构：

```json
{
  "session_id": "sess_000001",
  "actor_subject_id": "sub_staff_001",
  "role": "staff",
  "auth_methods": ["face"],
  "assurance_level": "medium",
  "last_emotion": {
    "label": "自然",
    "confidence": 0.88,
    "ts": 0
  },
  "created_ts": 0,
  "last_seen_ts": 0,
  "expires_ts": 0
}
```

短期目标：

- 可以先不做显式登录。
- 由视觉模块持续上报 actor 识别结果。
- gateway 维护一个当前活跃 actor/session。
- voice 和 dashboard 查询上下文时带上 `session_id` 或使用当前活跃 session。

长期目标：

- 支持人脸 + 指纹等多因素更新同一个 session。
- 支持会话过期。
- 支持手动切换/确认当前操作者。

## 10. 情绪识别与对话上下文

情绪识别结果应绑定当前操作者 actor，而不是默认绑定床位。

例如护士查询患者数据时：

- 摄像头看到的是护士。
- 情绪上下文表示护士当前状态。
- 大模型应据此调整回应护士的语气。
- 不应把护士的情绪写成患者情绪。

只有当当前 actor 是患者本人时，情绪才可以自然作为患者当前状态的一部分。

建议 gateway 上下文拆成三部分：

```text
actor_context
  当前使用系统的人：身份、角色、认证级别、当前情绪

target_context
  当前被查询的人或床位：患者、床位、睡眠、生理、姿态等

memory_context
  按 subject 存储的长期偏好、护理备注、对话摘要
```

示例：

```json
{
  "scene": "nurse_station_dialogue",
  "actor": {
    "subject_id": "sub_staff_001",
    "role": "staff",
    "identity_state": "recognized",
    "assurance_level": "medium",
    "emotion": {
      "label": "自然",
      "confidence": 0.88
    }
  },
  "target": {
    "target_type": "bed",
    "room": "R1203",
    "bed": "B1",
    "patient_subject_id": "sub_patient_001"
  },
  "policy": {
    "allowed": true,
    "allowed_sections": ["sleep", "vitals", "posture", "memory_summary"]
  },
  "brief": "",
  "prompt_hints": []
}
```

voice 不应自行拼权限相关上下文。voice 只调用：

```text
GET /api/v3/context/chat?session_id=...&target_room=R1203&target_bed=B1
```

gateway 返回已经裁剪好的内容。

## 11. 记忆系统

记忆应按 `subject_id` 存储，不按床位存储。

建议记忆类型：

```text
preference      偏好，例如喜欢被怎样称呼
care_note       护理备注，例如夜间容易焦虑
conversation    对话摘要
health_summary  健康/睡眠长期摘要
family_note     家属补充信息，后续可选
```

建议结构：

```json
{
  "memory_id": "mem_000001",
  "subject_id": "sub_patient_001",
  "kind": "preference",
  "content_compressed": "患者喜欢被称呼为李阿姨，睡前喜欢听轻音乐。",
  "visibility_scope": "care_team",
  "source": "manual",
  "confidence": 1.0,
  "created_ts": 0,
  "updated_ts": 0
}
```

上下文注入原则：

- 患者本人：可以注入自己的偏好、关怀型摘要、近期对话摘要。
- 工作人员：可以注入目标患者的护理相关摘要，但不应注入无关隐私。
- 未认证用户：不注入任何患者记忆。
- 大模型上下文只放压缩摘要，不放原始长对话。

短期可以先做手动写入和读取，后续再做自动摘要压缩。

## 12. 前端视图设计

### 12.1 床位视图

床位视图围绕固定床位组织。

建议信息块：

- 床位概览。
- 当前绑定患者。
- 设备在线状态。
- 传感器最新数据。
- 睡姿推理状态。
- 睡眠评分。
- 最近异常。
- 巴法云 topic 状态。

适合护士站大屏、设备调试和巡检。

### 12.2 患者视图

患者视图围绕 subject 组织。

建议信息块：

- 患者基本资料。
- 当前床位。
- 历史床位绑定。
- 睡眠趋势。
- 健康摘要。
- 压缩记忆。
- 护理备注。
- 可用认证凭据。

适合护理记录和个体关怀。

### 12.3 操作者/会话视图

后续可以增加一个轻量区域显示当前识别到的操作者：

- 当前 actor。
- 角色。
- 认证方式。
- 认证级别。
- 当前情绪。
- 会话剩余时间。

这个视图对调试权限和防止误识别很有帮助。

## 13. ESP32 统一固件 + NVS 配置方案

当前两个 ESP32 程序已经改为从 NVS 读取 WiFi、巴法云 UID、房间和床位。

改造前问题：

- `esp32/sketch_jan22a/sketch_jan22a.ino` 写死 `ssid/password/bemfa_uid/room_id/bed_id`。
- `esp32/testpro4/main/main.cpp` 需要从 NVS 读取 `BEMFA_UID/BEMFA_ROOM/BEMFA_BED/WIFI_SSID/WIFI_PASSWORD` 并恢复 Wi-Fi + MQTT 回传。

现在行为：

```text
固件只编译一次
  -> 启动时从 NVS 读取配置
  -> 配置完整则联网并上传
  -> 配置缺失则进入配置模式
```

统一配置结构：

```json
{
  "config_version": 1,
  "device_id": "esp32-r1203-b1-radar-001",
  "device_role": "radar_env_audio",
  "room": "R1203",
  "bed": "B1",
  "wifi_ssid": "hospital_wifi",
  "wifi_password": "password",
  "bemfa_uid": "your_bemfa_uid",
  "bemfa_host": "bemfa.com",
  "bemfa_mqtt_port": 9501
}
```

`device_role` 初期建议：

```text
radar_env_audio   Arduino 版，上传 radar/env/audio
posture_sensors   ESP-IDF 版，上传 tof1/tof2/mlx1/mlx2
```

topic 不建议直接存进 NVS，而应由配置自动拼接：

```text
prefix = room.lower() + bed.lower()
radar  = prefix + "radar"
env    = prefix + "env"
audio  = prefix + "audio"
tof1   = prefix + "tof1"
tof2   = prefix + "tof2"
mlx1   = prefix + "mlx1"
mlx2   = prefix + "mlx2"
```

这样可以减少人工配置错误。

### 13.1 配置方式分阶段

第一阶段：USB 串口配置。

- 统一固件烧录后，通过串口发送简单的 `key=value` 配置命令。
- ESP32 解析后写入 NVS。
- 重启后生效。
- 最适合当前开发和小批量部署。

示例命令协议：

```text
CFG? 
CFGSET ssid=HospitalWiFi
CFGSET password=your_password
CFGSET uid=your_bemfa_uid
CFGSET room=R1203
CFGSET bed=B1
CFGRESET
REBOOT
```

第二阶段：NVS 分区批量烧录。

- ESP-IDF 可以生成不同床位的 `nvs.bin`。
- 固件完全相同。
- 批量部署时只刷不同的 NVS 配置分区。
- 适合机械化烧录。

第三阶段：AP 配网。

- 设备首次启动发现无配置时，开启临时 WiFi 热点。
- 手机或电脑进入配置页面。
- 填写 WiFi、床位、UID。
- 保存到 NVS 后重启。
- 适合现场维护，但实现量更大。

第四阶段：设备注册中心。

- 设备只烧 `device_id`。
- 设备上线后向 gateway 拉取配置。
- gateway 统一管理设备与床位关系。
- 最完整，但当前阶段不优先。

### 13.2 安全建议

- WiFi 密码和 `BEMFA_UID` 不应继续写入源码。
- NVS 不是绝对安全，但比进代码仓库安全很多。
- 后续真实部署时考虑：
  - NVS encryption。
  - Flash encryption。
  - 每设备独立 token。
  - 巴法云 UID 权限隔离。
  - 配置写入需要物理按键确认或管理员授权。

## 14. Gateway 数据层建议

人员、床位绑定、认证凭据、权限会话和记忆建议从一开始使用 SQLite。

原因：

- 不需要单独安装数据库服务，只是一个本地 `.db` 文件。
- Python 标准库自带 `sqlite3`，适合当前本地 gateway。
- 支持事务，能避免 JSON 文件并发写入时互相覆盖。
- 适合表达 `subject -> assignment -> bed`、`subject -> credentials`、`subject -> memories` 这类关系。
- 后续如果需要迁移到 MySQL/PostgreSQL，表结构也更容易迁移。

建议 SQLite 管理这些低频但重要的数据：

```text
beds
subjects
bed_assignments
credentials
sessions
memories
sensor_history
posture_history
emotion_history
sleep_epoch
sleep_quality
```

传感器实时数据不必第一阶段全部进入 SQLite。当前 `history[(room, bed)][kind]` 的内存滚动缓存仍然适合实时 dashboard 和 worker 联调。

第一阶段建议：

- 保留当前 `history[(room, bed)][kind]` 内存结构存实时传感器窗口。
- 新增 `data/project2.db` 作为本地 SQLite 数据库。
- 在 gateway 启动时自动建表。
- 将 `bed_config.py` 中的固定床位同步到 `beds` 表。
- 自动创建默认超级管理员 subject。
- 后续 patient/staff、床位绑定、凭据、记忆、session 都写入 SQLite。

## 15. API 规划

### 15.1 床位 API

```text
GET /api/v3/beds
GET /api/v3/beds/{room}/{bed}
GET /api/v3/beds/{room}/{bed}/latest
GET /api/v3/beds/{room}/{bed}/device_status
```

当前 `/api/v2/beds` 和 `/api/v2/latest` 可以继续兼容。

### 15.2 患者/人员 API

```text
GET  /api/v3/subjects
POST /api/v3/subjects
GET  /api/v3/subjects/{subject_id}
PUT  /api/v3/subjects/{subject_id}
```

### 15.3 床位绑定 API

```text
POST /api/v3/assignments
POST /api/v3/assignments/{assignment_id}/close
GET  /api/v3/subjects/{subject_id}/assignments
GET  /api/v3/beds/{room}/{bed}/assignment
```

### 15.4 凭据 API

```text
POST /api/v3/credentials/face/enroll
POST /api/v3/credentials/fingerprint/enroll
GET  /api/v3/subjects/{subject_id}/credentials
POST /api/v3/credentials/{credential_id}/disable
```

### 15.5 视觉与会话 API

```text
POST /api/v3/vision/observation
GET  /api/v3/session/current
POST /api/v3/session/confirm
POST /api/v3/session/clear
```

`vision/observation` 可接收：

```json
{
  "face_present": true,
  "face_count": 1,
  "emotion": {
    "label": "自然",
    "confidence": 0.88
  },
  "identity": {
    "subject_id": "sub_staff_001",
    "confidence": 0.86,
    "identity_state": "recognized"
  },
  "source": "nurse_station_camera",
  "ts": 0
}
```

### 15.6 上下文 API

```text
GET /api/v3/context/chat?session_id=...&target_room=R1203&target_bed=B1
GET /api/v3/context/chat?session_id=...&target_subject_id=sub_patient_001
```

gateway 根据 session 权限裁剪结果。

## 16. 当前代码迁移路径

### 阶段 1：文档和配置梳理

- 保留当前 v2 API。
- 建立本方案文档。
- 更新 `NEXT_STEPS.md`，把重点从“视觉归床”改为“护士站 actor 识别 + 权限会话”。
- 明确床位固定、患者动态绑定的设计。

### 阶段 2：ESP32 NVS 配置

- Arduino 程序增加 NVS/Preferences 配置读取。
- ESP-IDF 程序增加 NVS 配置读取。
- 两个程序都支持串口配置命令。
- 删除源码中的真实 WiFi 密码和 UID。
- 添加配置示例和批量烧录说明。

### 阶段 3：Gateway subject 基础结构

- 增加 `subjects`、`assignments`、`credentials`、`memories`、`sessions` 的基础数据结构。
- 使用 SQLite 保存，默认路径为 `data/project2.db`。
- 增加最小 CRUD API。
- Dashboard 增加患者视图入口。

### 阶段 4：视觉模块调整

- 把现有 emotion 上报从“默认床位”改为“当前 actor/session observation”。
- 保留 `/api/v2/ingest/emotion` 兼容一段时间。
- 新增 `/api/v3/vision/observation`。
- 增加 identity mock。
- 后续接入真实 face embedding。

### 阶段 5：权限上下文

- 新增 session 当前操作者识别结果。
- 新增权限裁剪函数。
- `/api/v3/context/chat` 返回 actor/target/memory 三段上下文。
- voice 改为只读取 v3 chat context。

### 阶段 6：记忆系统

- 新增 subject 级 memory。
- 支持手动护理备注和偏好。
- 普通对话后可生成压缩摘要。
- 按权限注入 memory summary。

### 阶段 7：前端完善

- 床位视图：设备状态、数据状态、当前患者。
- 患者视图：个人资料、当前床位、历史、记忆。
- 会话视图：当前识别操作者、认证强度、情绪。
- 管理员功能：添加工作人员、添加患者、绑定床位、录入凭据。

## 17. 近期最小落地版本

建议近期不要一次做完整后台，而是做一个可跑通的最小版本：

1. 保留当前床位数据链路。
2. 新增 SQLite 数据库 `data/project2.db`。
3. 新增 subject / assignment / memory / session 基础表。
4. 新增一个默认 admin 和一个示例 patient。
5. Dashboard 上同时显示床位视图和患者视图。
6. 视觉 mock 上报 actor emotion 和 actor identity。
7. gateway 生成 v3 chat context。
8. voice 改读 v3 chat context。
9. 两个 ESP32 程序改为 NVS 配置。

这个版本能验证完整主线：

```text
床位设备数据 -> gateway 分床存储 -> 床位/患者视图
护士站摄像头 -> actor 身份/情绪 -> 权限会话
subject 记忆 -> gateway 上下文裁剪 -> voice 大模型对话
```

## 18. 关键风险

### 18.1 隐私与误识别

人脸识别会有误识别风险。后续涉及真实患者数据时，不能只依赖单一人脸识别。

缓解方式：

- 设置置信度阈值。
- 低置信度只作为提示，不授权。
- 支持工作人员手动确认。
- 支持指纹或工牌二次认证。
- 会话短时过期。

### 18.2 床位与患者混淆

传感器数据按床位来，记忆按患者来。上下文构建时必须通过 active assignment 做映射。

缓解方式：

- 所有患者上下文都先解析 `room/bed -> active_patient_id`。
- 无 active patient 时不注入患者记忆。
- 患者换床时关闭旧 assignment。

### 18.3 上下文过量

未来数据很多，不能直接塞给大模型。

缓解方式：

- gateway 做摘要。
- 只注入当前目标相关内容。
- 长期记忆压缩后再注入。
- 按角色裁剪内容。

### 18.4 ESP32 配置丢失

NVS 配置可能损坏或被清空。

缓解方式：

- 配置带 `config_version`。
- 启动时校验必要字段。
- 提供 `CFG?` 查询。
- 提供 `CFGRESET` 重置。
- 缺配置进入配置模式。

## 19. 结论

推荐的最终设计是：

```text
固定床位拓扑
  + 动态患者绑定
  + subject 级身份/权限/记忆
  + 护士站视觉 actor 识别
  + gateway 统一上下文裁剪
  + ESP32 统一固件 NVS 配置
```

这条路线与当前 `project2` 的多床位 gateway、`chat_context`、`emotion` 字段、`subject_id` 占位和 worker 架构兼容度较高，不需要推翻现有代码。

下一步最值得优先实现的是：

1. ESP32 NVS 配置，解决批量部署和安全问题。
2. gateway 增加 subject/assignment/memory/session 的基础结构。
3. 视觉从“床位情绪”调整为“当前操作者 actor 情绪 + 身份”。
4. 新增 `/api/v3/context/chat`，由 gateway 统一生成授权后的大模型上下文。
