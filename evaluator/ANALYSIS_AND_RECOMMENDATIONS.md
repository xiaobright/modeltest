# Final Assessment Notes

当前设计已经调整为“三条主线必做”：gateway/security/care_event，睡眠 CSV 多床归属，ESP32-S3 固件 Wi-Fi + MQTT 契约修复。`workspace/` 与 `evaluator/` 的边界仍然清楚，候选模型只看公开任务、参考契约、public tests 和 broken project。

## 当前评测口径

- public tests：基础 import/compile/smoke，保证 broken seed 不是跑不起来的坏种子。
- hidden tests：认证边界、上下文授权、睡眠导入、care_event、API 回归，以及 `PULL_REQUEST_TEMPLATE.md` 合同。
- ESP-IDF static：现在是 `run_full_eval.py` 默认必跑步骤，不再是 optional。
- ESP-IDF Windows build：仍作为可用环境下的额外编译验证，不要求 flash、monitor 或真实硬件联通。
- git artifacts：full eval 自动收集 diff/status/log，并复制 `project2_task/PULL_REQUEST_TEMPLATE.md` 到 results。

## 设计评价

难度梯度是合理的：

- 低到中等：public smoke、文档同步、`PULL_REQUEST_TEMPLATE.md` 报告。
- 中等：管理员密码/session 修复、睡眠 CSV 归属、v2/v3 兼容。
- 中高：care_event 跨 DB/API/context/auth 的完整接入。
- 高：ESP32-S3 Wi-Fi + MQTT active implementation，要求协议、CMake、NVS、base64 JSON 和 gateway 契约同时一致。

区分度也更强：只修 Python API 的模型会在 ESP static 和 PR自检 合同上掉分；只补注释或写报告的模型会被 hidden tests、static markers 和 git diff 对照识别；做了大面积重写但破坏旧接口的模型会被 API regression 和 rubric 扣分。

## 仍需人工把关

- `PULL_REQUEST_TEMPLATE.md` 的“是否真实对应 diff 和日志”只能部分自动化，最终仍需要 reviewer 对照结果目录判断。
- ESP-IDF static能抓住依赖、topic/base64/MQTT runtime markers，但不能替代真实 build 或硬件联调。
- `esp32/sketch_jan22a.ino` 仍作为真实历史文件存在，可能提供概念线索；如果你想让 ESP32 题更纯粹，可以后续再把旧 Arduino 草稿移出候选可见区。
