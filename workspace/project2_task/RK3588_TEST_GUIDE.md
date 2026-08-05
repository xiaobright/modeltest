# Project2 RK3588 测试指南

这份文档用于在 RK3588 开发板上独立验证 `project2` 改造后的完整链路。它假设读者没有之前的对话上下文，因此会从系统目标、当前完成状态、测试顺序、命令、预期结果和排错方式开始说明。

## 1. 当前改造状态

截至当前版本，核心软件改造已经基本完成：

- SQLite 管理层已完成：`beds / subjects / bed_assignments / credentials / memories / sessions / admin_accounts / admin_http_sessions`。
- Gateway 已完成模块化拆分：`config / db / auth / subjects / sensor_store / esp_store / sleep_importer / utils`。
- Gateway 管理页面已完成：首次访问 `/admin` 或 `/dashboard` 可初始化超级管理员；之后管理页和管理类 API 需要登录。
- ESP32 统一固件 + NVS 配置已完成，ESP-IDF 编译已验证通过。
- 视觉模块已接入 session/权限系统：
  - mock 模式可上报身份和情绪。
  - camera 模式可复用同一视频流做人脸检测、情绪识别和人脸身份比对。
- 人脸照片可在 `/admin` 上传并向量化存入 SQLite；face gallery 仅供本机视觉服务读取，不建议远程导出模板。
- Voice 已切到 gateway 的 v3 授权上下文：
  - voice 不再直接拼 v2 睡眠、姿态、情绪接口。
  - 心率、睡眠、离床、睡姿、鼾声和普通聊天统一读取 `/api/v3/context/chat`。
  - 未认证或无权限时，voice 不返回患者/床位隐私数据。

当前仍需要在真实硬件上验证：

- RK3588 上 Python 依赖、OpenCV、ONNXRuntime、RKLLM 是否可正常加载。
- 摄像头是否可被 `vision_worker.py` 读取。
- 真实人脸注册与识别阈值是否合适。
- ESP32 实机 NVS 配置、联网、巴法云 topic 上传是否正常。
- 巴法云到 gateway 的实际数据链路是否稳定。
- 麦克风、ASR、TTS 和 RKLLM 在板端的实际性能。

## 2. 最终系统链路

目标链路如下：

```text
ESP32 床位设备
  -> 巴法云
  -> gateway 按 room/bed 接收、解析、缓存、展示
  -> SQLite 管理 subject / bed / assignment / credential / memory / session
  -> vision 在护士站识别当前操作者身份和情绪
  -> gateway 生成经过权限裁剪的 /api/v3/context/chat
  -> voice/RKLLM 只消费 gateway 返回的授权上下文
```

核心原则：

- 传感器数据按床位存：`room + bed`。
- 人员、认证凭据、长期记忆按 `subject_id` 存。
- 患者和床位通过 `bed_assignments` 动态绑定。
- 摄像头位于 gateway/护士站，不做床位归属判断，只识别当前操作者。
- voice 只读 v3 context，不绕过 gateway 权限系统。

## 3. 推荐测试顺序

建议严格按下面顺序测试，不要一上来就跑全部硬件：

1. 代码静态检查。
2. RK3588 Python 环境和依赖检查。
3. gateway 单独启动和 SQLite 初始化。
4. 首次创建超级管理员，然后用 API 或管理页创建测试人员、患者、床位绑定和 session。
5. v3 权限上下文测试。
6. 注入模拟传感器数据，确认 v3 context 能输出 `sleep/vitals/posture/memory`。
7. vision mock 测试，确认 `vision -> gateway session -> context`。
8. voice text 模式测试，确认 voice 只读 v3 context。
9. 摄像头 camera 模式测试。
10. 人脸照片注册和真实识别测试。
11. RKLLM 模型加载和普通聊天测试。
12. ESP32 实机 + 巴法云链路测试。
13. 全量联调。

如果某一步失败，先停在该步骤排错，不要继续堆叠更多模块。

## 4. RK3588 环境准备

以下命令以 Ubuntu/Debian 系 RK3588 系统为例。

### 4.1 系统依赖

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-dev python3-pip \
  build-essential cmake pkg-config git curl \
  libsndfile1 ffmpeg v4l-utils \
  libportaudio2 portaudio19-dev \
  libopenblas-dev
```

如果后续使用麦克风，还需要确认当前用户有音频设备权限。必要时检查：

```bash
arecord -l
aplay -l
groups
```

如果摄像头接入 USB 或 CSI，先确认系统能看到设备：

```bash
v4l2-ctl --list-devices
ls -l /dev/video*
```

### 4.2 Python 虚拟环境

在项目根目录执行：

```bash
cd /path/to/project2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

注意：

- `opencv-contrib-python` 在 ARM64 上可能因为系统环境不同而安装失败。
- `onnxruntime` 在 ARM64 上也可能需要匹配板端系统的 wheel。
- 如果依赖安装失败，先不要测试 camera，人脸注册和情绪模型；可以先用 `vision-source mock` 跑通 gateway/session/voice 主链路。

依赖检查命令：

```bash
python - <<'PY'
import sys
print("python", sys.version)
import requests
print("requests ok")
import numpy
print("numpy", numpy.__version__)
try:
    import cv2
    print("cv2", cv2.__version__, "has FaceDetectorYN =", hasattr(cv2, "FaceDetectorYN"))
except Exception as e:
    print("cv2 failed:", e)
try:
    import onnxruntime as ort
    print("onnxruntime", ort.__version__)
except Exception as e:
    print("onnxruntime failed:", e)
PY
```

通过标准：

- `requests ok`。
- `numpy` 正常导入。
- 如果要测 camera/人脸注册，`cv2` 必须正常导入，且最好 `has FaceDetectorYN = True`。
- 如果要测情绪模型，`onnxruntime` 必须正常导入。

## 5. 关键文件和服务

项目根目录关键文件：

```text
start_project.py                 一键启动入口
gateway/gateway.py               HTTP 路由、页面服务、Bemfa 订阅和启动入口
gateway/config.py                环境变量、路径、运行参数
gateway/db.py                    SQLite 连接、建表、床位同步
gateway/auth.py                  超级管理员、登录、Cookie 会话
gateway/subjects.py              人员、绑定、记忆、凭据、身份匹配、session
gateway/sensor_store.py          传感器/睡眠/姿态/情绪历史缓存
gateway/esp_store.py             ESP32 ToF/MLX 帧和完整 set 聚合
gateway/sleep_importer.py        睡眠 CSV 导入和无房床字段归属策略
gateway/README.md                gateway 内部模块维护说明
gateway/admin.html               管理页面
vision/vision_worker.py          视觉 worker
vision/identity_runtime.py       人脸向量注册与比对
voice/voice_assistant_integrated.py  voice/RKLLM 主程序
posture/posture_worker.py        睡姿 worker
esp32/NVS_CONFIG.md              ESP32 NVS 配置说明
data/project2.db                 默认 SQLite 数据库
```

默认端口：

```text
gateway HTTP: 8765
```

gateway 监听 `0.0.0.0:8765`，因此在同一局域网其他电脑可以访问：

```text
http://<RK3588_IP>:8765/
http://<RK3588_IP>:8765/admin
```

注意：

- `/admin` 和 `/dashboard` 远程访问时需要管理员登录。
- 本机进程仍可调用采集、vision gallery、context 等服务接口，用于单护士站联调。
- 远程浏览器调用管理类 API 时，应先登录管理台；命令行测试可按 9.4 使用 Cookie jar。测试脚本仍建议直接在 RK3588 本机执行。

## 6. 常用环境变量

### 6.1 Gateway

```bash
export PROJECT2_DATA_DIR="$PWD/data"
export PROJECT2_DB_FILE="$PWD/data/project2.db"
export BEMFA_UID="your_bemfa_uid"
export ADMIN_AUTH_ENABLED="1"
export ADMIN_SESSION_TTL_MS="28800000"
export MAX_JSON_BODY_BYTES="8388608"
```

说明：

- `PROJECT2_DB_FILE` 可用于指定测试库，避免污染真实数据。
- `BEMFA_UID` 不设置时 gateway 仍会启动，只是跳过巴法云订阅。
- `ADMIN_AUTH_ENABLED=1` 是默认值；只在封闭调试环境临时排障时才考虑设为 `0`。
- `MAX_JSON_BODY_BYTES` 控制 HTTP JSON 请求体上限，避免大 base64 请求拖死 gateway。
- 睡眠 CSV 如果没有 `room/bed` 字段，默认只导入第一个配置床位。生产环境建议显式设置：

```bash
export SLEEP_IMPORT_DEFAULT_ROOM="R1203"
export SLEEP_IMPORT_DEFAULT_BED="B1"
# 或者无房床字段时直接跳过：
export SLEEP_IMPORT_UNSCOPED_POLICY="skip"
```

### 6.2 Vision

```bash
export GATEWAY_BASE="http://127.0.0.1:8765"
export VISION_SOURCE="mock"        # mock / camera / auto
export VISION_CAMERA_INDEX="0"
export VISION_INTERVAL_S="1.0"
export VISION_IDENTITY_ENABLED="1"
export VISION_MOCK_LABEL="自然"
export VISION_MOCK_SUBJECT_ID="sub_staff_test"
```

常用阈值：

```bash
export VISION_FACE_SCORE_THRESHOLD="0.75"
export FACE_MATCH_RECOGNIZED_THRESHOLD="0.82"
export FACE_MATCH_CANDIDATE_THRESHOLD="0.72"
```

### 6.3 Voice / RKLLM

```bash
export GATEWAY_BASE="http://127.0.0.1:8765"
export VOICE_INPUT_MODE="text"       # text / mic
export VOICE_ROOM="R1203"
export VOICE_BED="B1"
export VOICE_SESSION_ID=""           # 空表示使用 gateway 当前 session
export VOICE_TARGET_SUBJECT_ID=""    # 空表示用 VOICE_ROOM + VOICE_BED
```

RKLLM 默认路径：

```text
rkllm_py/librkllmrt.so
../model/Qwen3-1.7B_W8A8_RK3588.rkllm
```

如果模型或 so 不在默认位置：

```bash
export RKLLM_PROJECT_DIR="$PWD/rkllm_py"
export RKLLM_SO_PATH="$PWD/rkllm_py/librkllmrt.so"
export RKLLM_MODEL_PATH="/path/to/Qwen3-1.7B_W8A8_RK3588.rkllm"
```

## 7. 测试前先做静态检查

在项目根目录执行：

```bash
source .venv/bin/activate
python -m py_compile \
  start_project.py \
  gateway/gateway.py \
  gateway/config.py \
  gateway/db.py \
  gateway/auth.py \
  gateway/subjects.py \
  gateway/sensor_store.py \
  gateway/esp_store.py \
  gateway/sleep_importer.py \
  gateway/utils.py \
  gateway/bed_config.py \
  vision/identity_runtime.py \
  vision/vision_worker.py \
  vision/emotion_runtime.py \
  vision/frame_source.py \
  posture/posture_worker.py \
  voice/voice_assistant_integrated.py
```

通过标准：

- 命令无输出且退出码为 `0`。

失败处理：

- 如果提示缺 Python 语法支持，确认 Python 版本。
- 如果提示导入错误，通常不是 `py_compile` 阶段的问题；先确认是不是文件路径错误。

## 8. 使用干净测试数据库

建议第一次板端测试使用独立测试库：

```bash
export PROJECT2_DB_FILE="$PWD/data/rk3588_test.db"
rm -f "$PROJECT2_DB_FILE" "$PROJECT2_DB_FILE-wal" "$PROJECT2_DB_FILE-shm"
```

这样可以反复测试初始化、创建人员和权限，不影响 `data/project2.db`。

## 9. Gateway 单独测试

### 9.1 启动 gateway

终端 A：

```bash
source .venv/bin/activate
export PROJECT2_DB_FILE="$PWD/data/rk3588_test.db"
python start_project.py --target gateway
```

预期日志：

```text
[DB] SQLite management database: ...
[HTTP] http://127.0.0.1:8765/health
[HTTP] http://127.0.0.1:8765/admin
```

如果没有设置 `BEMFA_UID`，会看到类似：

```text
BEMFA_UID 未设置：将跳过巴法云订阅，但继续启动本地 HTTP/API
```

这是正常的，本地测试可以先忽略。

### 9.2 健康检查

终端 B：

```bash
curl -s http://127.0.0.1:8765/health
```

通过标准：

- 返回 JSON。
- HTTP 状态为 `200`。

### 9.3 管理页检查

在浏览器打开：

```text
http://127.0.0.1:8765/admin
```

或从电脑访问：

```text
http://<RK3588_IP>:8765/admin
```

通过标准：

- 如果测试库还没有超级管理员，会先显示“初始化超级管理员”页面。
- 创建超级管理员后，页面正常加载。
- 能看到人员、床位、绑定、凭据、记忆、session 和 context 预览等管理区域。

首次初始化建议：

```text
username: admin
password: 自行设置，至少 8 位
```

不要把真实密码写进文档或提交到仓库。

### 9.4 命令行登录管理 API

后续如果用 `curl` 创建人员、绑定床位或手动创建测试 session，需要先拿到管理员 Cookie。下面命令只用于测试库；真实环境请使用自己的强密码。

如果是新测试库、还没有超级管理员：

```bash
export ADMIN_COOKIE="/tmp/project2_admin_cookie.txt"
curl -s -c "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/admin/setup \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "display_name": "超级管理员",
    "password": "password123",
    "password_confirm": "password123"
  }'
```

如果已经创建过超级管理员：

```bash
export ADMIN_COOKIE="/tmp/project2_admin_cookie.txt"
curl -s -c "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/admin/login \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "password": "password123"
  }'
```

后续管理类 API 都加上：

```bash
-b "$ADMIN_COOKIE"
```

## 10. 创建基础测试数据

下面使用 API 创建一个工作人员、一个患者，并把患者绑定到 `R1203-B1`。

注意：这些管理类 API 需要管理员登录。先完成 9.4 获取 `ADMIN_COOKIE`，或者直接在管理页创建相同数据。

### 10.1 创建工作人员

```bash
curl -s -b "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/subjects \
  -H 'Content-Type: application/json' \
  -d '{
    "subject_id": "sub_staff_test",
    "name": "测试护士",
    "role": "staff",
    "status": "active"
  }'
```

### 10.2 创建患者

```bash
curl -s -b "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/subjects \
  -H 'Content-Type: application/json' \
  -d '{
    "subject_id": "sub_patient_test",
    "name": "测试患者",
    "role": "patient",
    "status": "active",
    "age": 72,
    "notes": "RK3588 联调用测试患者"
  }'
```

### 10.3 绑定床位

```bash
curl -s -b "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/assignments \
  -H 'Content-Type: application/json' \
  -d '{
    "subject_id": "sub_patient_test",
    "room": "R1203",
    "bed": "B1",
    "created_by": "sub_staff_test"
  }'
```

### 10.4 添加患者记忆

```bash
curl -s -b "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/memories \
  -H 'Content-Type: application/json' \
  -d '{
    "subject_id": "sub_patient_test",
    "kind": "preference",
    "content_compressed": "患者喜欢被称呼为李阿姨，睡前喜欢听轻音乐。",
    "visibility_scope": "care_team",
    "source": "manual",
    "confidence": 1.0
  }'
```

### 10.5 检查数据

```bash
curl -s -b "$ADMIN_COOKIE" http://127.0.0.1:8765/api/v3/subjects
curl -s -b "$ADMIN_COOKIE" http://127.0.0.1:8765/api/v3/beds
```

通过标准：

- `subjects` 中能看到 `sub_staff_test` 和 `sub_patient_test`。
- `beds` 中 `R1203-B1` 的 `assignment` 指向 `sub_patient_test`。

## 11. 权限上下文测试

### 11.1 未认证时查询 context

在没有 session 或没有 recognized session 时执行：

```bash
curl -s 'http://127.0.0.1:8765/api/v3/context/chat?target_room=R1203&target_bed=B1'
```

通过标准：

- `policy.allowed` 应为 `false`。
- `policy.reason` 应为 `not_authenticated`。
- `modalities.sleep / modalities.vitals / modalities.posture / modalities.memory` 应为空或无隐私内容。
- `target.patient` 应为空对象。

如果这里未认证却返回了患者详情，说明权限裁剪有问题，需要停止继续测试。

### 11.2 创建工作人员认证 session

这一步是本机调试捷径，用于快速验证权限裁剪。真实流程推荐通过 vision mock、camera 人脸识别或后续接入的指纹/卡片认证来更新 session。

```bash
curl -s -b "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/sessions \
  -H 'Content-Type: application/json' \
  -d '{
    "actor_subject_id": "sub_staff_test",
    "role": "staff",
    "auth_methods": ["manual_test"],
    "assurance_level": "medium",
    "identity_state": "recognized",
    "emotion": {
      "label": "自然",
      "confidence": 0.88
    }
  }'
```

通过标准：

- 返回 `session.session_id`。
- `actor_subject_id` 为 `sub_staff_test`。
- `identity_state` 为 `recognized`。

### 11.3 已认证 staff 查询 context

```bash
curl -s 'http://127.0.0.1:8765/api/v3/context/chat?target_room=R1203&target_bed=B1'
```

通过标准：

- `policy.allowed` 应为 `true`。
- `target.patient.subject_id` 应为 `sub_patient_test`。
- `actor.subject_id` 应为 `sub_staff_test`。
- `actor.emotion.label` 应为 `自然`。
- `modalities.memory.brief` 应包含第 10.4 步写入的记忆摘要。

## 12. 注入模拟床位数据

这一步不需要 ESP32，用 API 模拟床位数据，验证 gateway 和 voice 的上下文结构。

### 12.1 注入 radar 数据

```bash
curl -s -X POST 'http://127.0.0.1:8765/api/v2/ingest?room=R1203&bed=B1' \
  -H 'Content-Type: application/json' \
  -d '{
    "kind": "radar",
    "payload": {
      "heart_bpm": 72,
      "breath_bpm": 16,
      "motion": 0.25,
      "turning": 1
    }
  }'
```

### 12.2 注入 audio 数据

```bash
curl -s -X POST 'http://127.0.0.1:8765/api/v2/ingest?room=R1203&bed=B1' \
  -H 'Content-Type: application/json' \
  -d '{
    "kind": "audio",
    "payload": {
      "snore_level": 2,
      "snore_count_1min": 3
    }
  }'
```

### 12.3 注入 sleep quality

```bash
curl -s -X POST 'http://127.0.0.1:8765/api/v2/ingest/sleep_quality?room=R1203&bed=B1' \
  -H 'Content-Type: application/json' \
  -d '{
    "record": "rk3588-test",
    "total_score": 82,
    "grade": "良好",
    "sleep_h": 6.5
  }'
```

### 12.4 注入 sleep epoch

```bash
curl -s -X POST 'http://127.0.0.1:8765/api/v2/ingest/sleep_epoch?room=R1203&bed=B1' \
  -H 'Content-Type: application/json' \
  -d '{
    "record": "rk3588-test",
    "Final_stage": "N2"
  }'
```

### 12.5 注入 posture

```bash
curl -s -X POST 'http://127.0.0.1:8765/api/v2/ingest/posture?room=R1203&bed=B1' \
  -H 'Content-Type: application/json' \
  -d '{
    "class_idx": 1,
    "class_name": "侧卧",
    "confidence": 0.91,
    "confidence_flag": "high",
    "probabilities": [0.05, 0.91, 0.04],
    "infer_ms": 18.5
  }'
```

### 12.6 检查 v3 context 聚合结果

```bash
curl -s 'http://127.0.0.1:8765/api/v3/context/chat?target_room=R1203&target_bed=B1'
```

通过标准：

- `policy.allowed` 为 `true`。
- `modalities.vitals.heart_bpm` 为 `72`。
- `modalities.vitals.snore_level` 为 `2`。
- `modalities.sleep.sleep_score` 为 `82`。
- `modalities.sleep.sleep_h` 为 `6.5`。
- `modalities.posture.posture_class` 为 `侧卧`。
- `brief` 中应包含操作者情绪、睡眠摘要或记忆摘要。

## 13. Vision mock 测试

这一步验证 `vision -> gateway session -> /api/v3/context/chat`，不需要摄像头。

确保第 10 步已经创建 `sub_staff_test`。

终端 C：

```bash
source .venv/bin/activate
export PROJECT2_DB_FILE="$PWD/data/rk3588_test.db"
export GATEWAY_BASE="http://127.0.0.1:8765"
python vision/vision_worker.py
```

默认 `vision_worker.py` 是 mock 模式。如果要明确指定：

```bash
export VISION_SOURCE="mock"
export VISION_MOCK_LABEL="自然"
export VISION_MOCK_SUBJECT_ID="sub_staff_test"
python vision/vision_worker.py
```

也可以用一键入口：

```bash
python start_project.py \
  --target gateway \
  --with-vision \
  --vision-source mock \
  --vision-mock-label 自然 \
  --vision-mock-subject-id sub_staff_test
```

检查当前 session：

```bash
curl -s -b "$ADMIN_COOKIE" http://127.0.0.1:8765/api/v3/session/current
```

通过标准：

- `session.actor_subject_id` 为 `sub_staff_test`。
- `session.identity_state` 为 `recognized`。
- `session.assurance_level` 不为 `none`。
- `session.emotion.label` 为 mock 设置的情绪。

再查 context：

```bash
curl -s 'http://127.0.0.1:8765/api/v3/context/chat?target_room=R1203&target_bed=B1'
```

通过标准：

- `policy.allowed` 为 `true`。
- `actor.subject_id` 为 `sub_staff_test`。

## 14. Voice text 模式测试

这一步验证 voice 是否只读 `/api/v3/context/chat`。

终端 D：

```bash
source .venv/bin/activate
export PROJECT2_DB_FILE="$PWD/data/rk3588_test.db"
export GATEWAY_BASE="http://127.0.0.1:8765"
export VOICE_INPUT_MODE="text"
python voice/voice_assistant_integrated.py
```

或者：

```bash
python start_project.py --target voice --voice-input text --voice-room R1203 --voice-bed B1
```

在文本输入模式下依次输入：

```text
心率检测
昨晚睡眠情况
睡姿识别
鼾声分析
R1203B1情况怎么样
```

通过标准：

- 已认证 staff session 下：
  - 心率回答应使用 `modalities.vitals.heart_bpm`。
  - 睡眠回答应使用 `modalities.sleep`。
  - 睡姿回答应使用 `modalities.posture`。
  - 鼾声回答应使用 `modalities.vitals` 或 `modalities.sleep` 中的鼾声字段。
- 未认证 session 下：
  - voice 应提示“当前还没有完成身份认证”或类似权限提示。
  - 不应返回患者姓名、记忆、心率、睡眠等隐私数据。

注意：

- Linux/RK3588 上当前如果没有配置 Piper TTS，voice 可能只打印回复文本，TTS 会失败并 fallback 到打印。这不影响上下文链路测试。
- 如果 RKLLM 模型不存在，普通聊天会输出兜底回复；先验证意图类查询和权限裁剪即可。

## 15. 摄像头 camera 模式测试

### 15.1 摄像头可用性检查

```bash
v4l2-ctl --list-devices
python - <<'PY'
import cv2
cap = cv2.VideoCapture(0)
print("opened =", cap.isOpened())
if cap.isOpened():
    ok, frame = cap.read()
    print("read =", ok, "shape =", None if frame is None else frame.shape)
cap.release()
PY
```

通过标准：

- `opened = True`。
- `read = True`。
- frame shape 类似 `(480, 640, 3)`。

### 15.2 模型文件检查

```bash
ls -lh vision/models/
```

必须存在：

```text
face_detection_yunet_2023mar.onnx
emotion_mamba.onnx
```

### 15.3 启动 camera vision

保持 gateway 运行，终端 C：

```bash
source .venv/bin/activate
export PROJECT2_DB_FILE="$PWD/data/rk3588_test.db"
export GATEWAY_BASE="http://127.0.0.1:8765"
export VISION_SOURCE="camera"
export VISION_CAMERA_INDEX="0"
export VISION_INTERVAL_S="1.0"
python vision/vision_worker.py
```

通过标准：

- 日志显示 camera 模式已启用。
- 没有人脸时不会崩溃。
- 有人脸时能上报 emotion。

检查 emotion：

```bash
curl -s 'http://127.0.0.1:8765/api/v2/emotion/latest?room=R1203&bed=B1'
```

通过标准：

- `face_present` 在有人脸时为 `true`。
- `label` 为情绪标签。
- `confidence` 为 0 到 1 的数字。

## 16. 人脸注册与真实身份识别测试

### 16.1 使用管理页面注册

推荐先用管理页：

```text
http://<RK3588_IP>:8765/admin
```

流程：

1. 创建工作人员 `sub_staff_test`，或使用已有工作人员。
2. 在创建人员时上传一张正脸照片；或在凭据区域为该人员补录 `face` 凭据。
3. 保存后 gateway 会自动向量化并写入 SQLite。

检查 gallery：

```bash
curl -s 'http://127.0.0.1:8765/api/v3/identity/gallery?type=face'
```

通过标准：

- 返回中能看到 `sub_staff_test` 的 active face credential。
- `template` 中包含 embedding/vector 相关字段。

注意：

- `identity/gallery` 现在按“本机视觉服务接口”管理，只应在 RK3588 本机用 `127.0.0.1` 检查。
- 不要从远程电脑导出 gallery 模板；人脸 embedding 属于敏感生物特征数据。

### 16.2 使用 API 注册

如果要用命令行上传图片：

这同样建议在 RK3588 本机执行，或在已登录的管理页面上传。

```bash
python - <<'PY' > /tmp/face_payload.json
import base64, json
image_path = "staff_face.jpg"
with open(image_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")
payload = {
    "subject_id": "sub_staff_test",
    "type": "face",
    "provider": "rk3588_test_upload",
    "image_b64": "data:image/jpeg;base64," + b64
}
print(json.dumps(payload, ensure_ascii=False))
PY

curl -s -b "$ADMIN_COOKIE" -X POST http://127.0.0.1:8765/api/v3/credentials/enroll \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/face_payload.json
```

通过标准：

- 返回 `ok: true`。
- 返回 credential 的 `type` 为 `face`。

如果失败并提示 `cv2` 或 face detector 相关错误，优先检查 OpenCV contrib 和模型文件。

### 16.3 真实识别

启动 camera vision 后，让注册人员站在摄像头前：

```bash
curl -s -b "$ADMIN_COOKIE" http://127.0.0.1:8765/api/v3/session/current
```

通过标准：

- `identity_state` 为 `recognized`。
- `actor_subject_id` 为注册人员 subject。
- `auth_methods` 包含 `face`。
- `assurance_level` 通常为 `medium` 或更高。

如果识别不稳定：

- 光线太暗时先改善光照。
- 换更正、更清晰的人脸注册图。
- 临时降低阈值测试：

```bash
export FACE_MATCH_RECOGNIZED_THRESHOLD="0.78"
export FACE_MATCH_CANDIDATE_THRESHOLD="0.68"
```

真实部署时不要盲目降低阈值，避免误识别。

## 17. RKLLM 和普通聊天测试

### 17.1 检查 RKLLM 文件

```bash
ls -lh rkllm_py/librkllmrt.so
ls -lh /path/to/Qwen3-1.7B_W8A8_RK3588.rkllm
```

设置路径：

```bash
export RKLLM_PROJECT_DIR="$PWD/rkllm_py"
export RKLLM_SO_PATH="$PWD/rkllm_py/librkllmrt.so"
export RKLLM_MODEL_PATH="/path/to/Qwen3-1.7B_W8A8_RK3588.rkllm"
```

### 17.2 启动 voice

```bash
python start_project.py --target voice --voice-input text --voice-room R1203 --voice-bed B1
```

输入：

```text
她昨晚休息得怎么样，今天要怎么关心她？
```

通过标准：

- 如果 RKLLM 正常，回复应自然结合 gateway 的授权上下文。
- 如果当前 session 未认证，回复应避免患者隐私数据。
- 如果 RKLLM 不可用，会打印导入失败、so 不存在或模型不存在，并使用兜底回复。

## 18. 麦克风模式测试

确认音频设备：

```bash
arecord -l
```

启动：

```bash
python start_project.py --target voice --voice-input mic --voice-room R1203 --voice-bed B1
```

通过标准：

- ASR 模型加载成功。
- 说“心率检测”等短口令可以识别。
- 如果没有 TTS，至少终端能打印回复。

常见问题：

- `webrtcvad` 导入失败：重新安装 `webrtcvad` 或检查 Python 版本。
- `sounddevice` / PortAudio 错误：安装 `portaudio19-dev`，检查设备权限。
- ASR 太慢：先改用 `VOICE_INPUT_MODE=text` 验证主链路。

## 19. ESP32 + 巴法云测试入口

ESP32 详细配置见：

```text
esp32/NVS_CONFIG.md
```

### 19.1 串口配置

两套固件使用统一命令：

```text
CFG?
CFGSET ssid=HospitalWiFi
CFGSET password=your_password
CFGSET uid=your_bemfa_uid
CFGSET room=R1203
CFGSET bed=B1
CFGSET device_id=esp32-r1203-b1-radar-001
REBOOT
```

### 19.2 topic 预期

`R1203-B1` 会自动拼接：

```text
r1203b1radar
r1203b1env
r1203b1audio
r1203b1tof1
r1203b1tof2
r1203b1mlx1
r1203b1mlx2
```

### 19.3 Gateway 设置巴法云 UID

在 RK3588 上启动 gateway 前设置：

```bash
export BEMFA_UID="your_bemfa_uid"
python start_project.py --target gateway
```

通过标准：

- gateway 不再提示 `BEMFA_UID 未设置`。
- ESP32 串口显示 WiFi/MQTT 连接成功。
- gateway dashboard 中对应床位的 `radar/env/audio/tof/mlx` 数据逐步变为 online。
- API 能读到数据：

```bash
curl -s 'http://127.0.0.1:8765/api/v2/latest?room=R1203&bed=B1'
```

## 20. 全量联调建议

全量测试时建议分多个终端运行，便于看日志。

终端 A：gateway

```bash
source .venv/bin/activate
export PROJECT2_DB_FILE="$PWD/data/project2.db"
export BEMFA_UID="your_bemfa_uid"
python start_project.py --target gateway
```

终端 B：vision

```bash
source .venv/bin/activate
export GATEWAY_BASE="http://127.0.0.1:8765"
export VISION_SOURCE="camera"
export VISION_CAMERA_INDEX="0"
python vision/vision_worker.py
```

终端 C：posture worker

```bash
source .venv/bin/activate
export GATEWAY_BASE="http://127.0.0.1:8765"
python posture/posture_worker.py
```

终端 D：voice

```bash
source .venv/bin/activate
export GATEWAY_BASE="http://127.0.0.1:8765"
export VOICE_INPUT_MODE="text"
python voice/voice_assistant_integrated.py
```

也可以使用一键启动：

```bash
python start_project.py \
  --target all \
  --voice-input text \
  --with-posture \
  --with-vision \
  --vision-source camera \
  --vision-camera-index 0 \
  --voice-room R1203 \
  --voice-bed B1
```

注意：全量联调时如果 voice 是 `text` 模式，交互输入可能和一键启动日志混在一起。排查问题时优先使用多终端方式。

## 21. 验收清单

基础软件：

- [ ] `python -m py_compile ...` 通过。
- [ ] `pip install -r requirements.txt` 成功，或已记录 ARM64 替代安装方式。
- [ ] `cv2` 可导入。
- [ ] `onnxruntime` 可导入。
- [ ] gateway `/health` 返回 200。
- [ ] `/admin` 页面可打开。

SQLite 管理：

- [ ] 首次访问 `/admin` 可创建超级管理员。
- [ ] 退出后再次访问 `/admin` 需要登录。
- [ ] 可创建 staff。
- [ ] 可创建 patient。
- [ ] 可绑定 patient 到 `R1203-B1`。
- [ ] 可写入 subject memory。
- [ ] 可创建 recognized session。
- [ ] 远程浏览器未登录时不能直接访问管理类 API。

权限上下文：

- [ ] 未认证时 `/api/v3/context/chat` 返回 `policy.allowed=false`。
- [ ] 未认证时不返回患者详情。
- [ ] staff 认证后可查看目标患者上下文。
- [ ] patient 认证后只能查看自己的上下文。
- [ ] unknown 或无权限角色不能查看患者数据。

传感器上下文：

- [ ] radar 模拟数据进入 `modalities.vitals`。
- [ ] sleep 模拟数据进入 `modalities.sleep`。
- [ ] posture 模拟数据进入 `modalities.posture`。
- [ ] memory 摘要进入 `modalities.memory`。
- [ ] voice 的心率/睡眠/睡姿/鼾声回复来自 v3 context。

Vision：

- [ ] mock emotion 可写入 session。
- [ ] mock identity 可让 session 变为 recognized。
- [ ] camera 可打开。
- [ ] 有人脸时 emotion 可更新。
- [ ] 上传人脸照片可生成 face credential。
- [ ] face gallery 只在 RK3588 本机 `127.0.0.1` 用于 vision 调试，不从远程导出模板。
- [ ] 注册人员站到摄像头前可被识别为对应 subject。

Voice：

- [ ] text 模式可运行。
- [ ] 未认证时不会返回患者隐私数据。
- [ ] 认证后意图问答可读取授权上下文。
- [ ] RKLLM 模型可加载，或已确认 fallback 行为。
- [ ] mic 模式可录音和识别。
- [ ] TTS 可播放，或已确认终端打印 fallback 可接受。

ESP32 / 巴法云：

- [ ] ESP32 串口 `CFG?` 可查看配置。
- [ ] `CFGSET` 可写入 WiFi、UID、room、bed。
- [ ] `REBOOT` 后设备自动连接 WiFi。
- [ ] 设备自动连接巴法云。
- [ ] topic 与 `room+bed+kind` 一致。
- [ ] gateway 能收到对应床位数据。
- [ ] dashboard 设备状态 online。

## 22. 常见故障和处理

### 22.1 gateway 启动但没有巴法云数据

检查：

```bash
echo "$BEMFA_UID"
curl -s 'http://127.0.0.1:8765/api/v2/latest?room=R1203&bed=B1'
```

处理：

- 确认 gateway 启动前设置了 `BEMFA_UID`。
- 确认 ESP32 的 NVS 中 `uid/room/bed` 正确。
- 确认 topic 拼接是否为小写，例如 `r1203b1radar`。
- 先用 API 注入模拟数据，确认 gateway 本身没问题。

### 22.2 `/api/v3/context/chat` 一直 `not_authenticated`

检查当前 session：

```bash
curl -s -b "$ADMIN_COOKIE" http://127.0.0.1:8765/api/v3/session/current
```

处理：

- 确认 `identity_state` 为 `recognized`。
- 确认 `assurance_level` 不是 `none`。
- 用 `/api/v3/sessions` 手动创建测试 session。
- 如果从远程电脑测试，先确认已经登录管理页；更推荐在 RK3588 本机用 `127.0.0.1` 执行调试命令。
- 如果靠 vision 更新 session，检查 `VISION_MOCK_SUBJECT_ID` 或 face gallery。

### 22.3 已认证但仍 `not_authorized_for_target`

处理：

- staff/admin 理论上可以看所有目标。
- patient 只能看自己的 `subject_id`。
- 检查当前 actor 的 `role`。
- 检查目标床位是否绑定到了另一个 patient。

### 22.4 上传人脸照片失败

常见原因：

- `cv2` 未安装。
- OpenCV 不是 contrib 版本，缺 `FaceDetectorYN`。
- `vision/models/face_detection_yunet_2023mar.onnx` 不存在。
- 照片中没有清晰正脸。

先跑：

```bash
python - <<'PY'
import cv2
print(cv2.__version__, hasattr(cv2, "FaceDetectorYN"))
PY
```

### 22.5 camera 打不开

检查：

```bash
v4l2-ctl --list-devices
ls -l /dev/video*
```

处理：

- 调整 `VISION_CAMERA_INDEX`。
- 确认没有其他进程占用摄像头。
- 先用 OpenCV 最小脚本读一帧。

### 22.6 voice 启动但 RKLLM 不可用

日志通常会提示：

- `导入失败`
- `未找到 so`
- `未找到模型`

处理：

- 设置 `RKLLM_PROJECT_DIR`。
- 设置 `RKLLM_SO_PATH`。
- 设置 `RKLLM_MODEL_PATH`。
- 先使用意图类问题验证 gateway context，不要把 RKLLM 作为第一阻塞项。

### 22.7 Linux 上没有 TTS 声音

当前代码优先使用硬编码 Piper 模型路径，否则会尝试 Windows SAPI；在 Linux/RK3588 上可能只打印文本。

处理：

- 先接受打印 fallback，验证主链路。
- 后续再配置 Piper 模型和 `PIPER_MODEL/PIPER_EXE` 相关逻辑。

### 22.8 依赖在 ARM64 上安装失败

处理顺序：

1. 先不测 camera：用 `VISION_SOURCE=mock`。
2. 先不测 mic：用 `VOICE_INPUT_MODE=text`。
3. 先不测 RKLLM：允许 fallback。
4. 单独解决 `opencv-contrib-python` 和 `onnxruntime` 的 ARM64 安装。

## 23. 建议记录的测试日志

每次板端测试建议记录：

```text
日期：
RK3588 系统版本：
Python 版本：
项目路径：
数据库文件：
是否设置 BEMFA_UID：
摄像头设备：
OpenCV 版本：
ONNXRuntime 版本：
RKLLM 模型路径：
测试床位：
测试 staff subject_id：
测试 patient subject_id：
通过项：
失败项：
关键日志：
下一步：
```

## 24. 最小通过标准

如果时间有限，至少完成下面几项就可以说明主架构跑通：

1. gateway 启动，`/health` 正常。
2. 首次访问 `/admin` 能创建超级管理员，之后可登录管理页。
3. `/admin` 能创建 staff、patient，并绑定床位。
4. 未认证时 `/api/v3/context/chat` 不返回患者隐私。
5. staff 认证后 `/api/v3/context/chat` 返回目标患者上下文。
6. vision mock 能更新当前 session。
7. voice text 模式查询心率/睡眠/睡姿时走 v3 context。
8. camera 模式能读到人脸情绪。
9. 上传人脸照片后，camera 模式能识别当前工作人员。

完成这些后，再接 ESP32 和巴法云做真实数据闭环。
