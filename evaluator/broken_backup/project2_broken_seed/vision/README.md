# Vision 模块说明

`vision/` 是 `project2` 当前阶段的独立视觉基础模块。它负责护士站摄像头取流、情绪识别、当前操作者人脸身份识别，并把结果上报给 `gateway` 的 session/权限系统。

## 当前职责

- 摄像头 / mock 取流
- 人脸检测
- 情绪识别
- 人脸向量生成与本地 gallery 比对
- 将结果写入 `gateway`

## 当前文件

```text
vision/
├── frame_source.py
├── emotion_runtime.py
├── identity_runtime.py
├── vision_worker.py
├── models/
│   ├── face_detection_yunet_2023mar.onnx
│   └── emotion_mamba.onnx
└── README.md
```

## 当前运行策略

- 默认低频推理，约 `1Hz`
- 当前优先走 `CPU + ONNXRuntime`
- 没有摄像头时默认可用 `mock` 联调
- 情绪结果仍写到 `project2` 默认床位，便于 dashboard 展示
- 身份结果写入 `gateway` session，用于 `/api/v3/context/chat` 权限裁剪
- 当前人脸向量实现是可替换的本地 OpenCV 版本，后续可换成 ArcFace/InsightFace

## 运行方式

### mock

```bash
python vision/vision_worker.py
```

或：

```bash
python start_project.py --target all --with-vision --vision-source mock
```

指定 mock 身份：

```bash
python start_project.py --target all --with-vision --vision-source mock --vision-mock-subject-id sub_admin_default
```

### camera

```bash
python start_project.py --target all --with-vision --vision-source camera --vision-camera-index 0
```

### auto

```bash
python start_project.py --target all --with-vision --vision-source auto
```

## 输出字段

Worker 会向 `/api/v2/ingest/emotion` 推送：

- `label`
- `confidence`
- `confidence_flag`
- `probabilities`
- `face_count`
- `face_present`
- `source`
- `source_state`
- `backend`
- `stable_for_ms`
- `infer_ms`
- `infer_count`
- `notes`
- `subject_id`
- `identity_state`
- `identity`
- `ts`

Worker 同时会向 `/api/v3/vision/observation` 推送：

- `identity`
- `emotion`
- `camera_index`
- `source`
- `ts`

`identity` 的基础字段为：

- `type`
- `auth_method`
- `identity_state`
- `subject_id`
- `confidence`
- `credential_id`
- `assurance_level`

## 人脸注册与扩展认证

管理页 `/admin` 创建人员或补录凭据时，可以上传人脸照片。gateway 会调用 `identity_runtime.py` 生成 face template，并写入 SQLite 的 `credentials.template_json`。

注册接口：

```text
POST /api/v3/credentials/enroll
```

当前 `type=face` 会自动向量化图片；`fingerprint/card/manual` 等后续认证方式复用同一 credential/enroll 结构，先保留 `template/payload` 入口。

## 当前仍不做视觉分床

当前先把下面这条链路跑通：

```text
vision -> gateway session -> permission policy -> unified chat context -> voice
```

所以这一版故意保持简化：

- 不在 `vision` 中做床位归属判断
- 先把视觉结果落到默认床位，便于板端联调

后续你切到 `project2` 新工作区时，再继续做“视觉归床 / 身份识别 / 权限裁剪”会更稳。
