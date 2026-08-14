# modeltest — LLM 工程维护能力自测套件 (V4.1b · frozen)

> A personal, self-hosted evaluation harness that measures how well LLMs perform
> real-world engineering maintenance on a multi-module Python + ESP32 firmware
> project. Frozen at V4.1b on 2026-07-23. **Not a public benchmark.**

这是 Project2 的本地开发、提测自检与自动化校验套件。它把「本地开发工作区」和
「自动化提测/自检控制区」分开,方便做本地代码重置、测试校验、自检日志收集和
PR 一致性预审。

## Status

- **当前正式稳定基线:V4.1b**,已于 2026-07-23 正式冻结。不再迭代、不开发 V5。
  详见 [`PROJECT_FROZEN.md`](./PROJECT_FROZEN.md)。
- 冻结的是题面、测试与计分规则；模型、渠道和 harness 的实测台账仍会追加。
  最新一轮记录截至 2026-08-14。
- 这是一个**个人项目**,不是面向社区的公开 benchmark;Ability 阈值与结论只对本
  题面、本工具环境有效,**不构成跨项目通用认证**。
- V5 两次尝试均失败,工作区与归档见独立 repo **`modeltest-v5`**。
- 9 轮历史评测快照(V1–V4.1b、PlanExec、V5 specialty/formal)体积较大且高度
  重复,不进 git 仓库,以压缩包形式放在 **GitHub Releases**。

## DeepSeek V4 专项报告（2026-08-14）

> **核心发现：** V4 Pro 在官方 DSH minimal + max 下两跑 **99/96**，但在相同
> WSL/max 环境的 standard 和 PTC 只有 **91/92**；V4 Flash 更换 scaffold 后思维链
> 风格明显变化，Ability 仍为 **92**。证据更支持“Pro 具备高上限但强依赖 RL 对齐
> scaffold”，而不是 Linux、官方 harness 或 `run_code` 本身带来增益。

- **完整 harness 分析：**
  [`DeepSeek V4 Pro 正式版：harness 对照分析`](./docs/v4.1/DEEPSEEK_V4_PRO_HARNESS_ANALYSIS_20260814.md)
- **思维链风格与 PTC：**
  [`DeepSeek V4 Pro：轨迹风格与 PTC 对照分析`](./docs/v4.1/DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md)
- **完整成绩与单次评审：**
  [`V4.1b 成绩榜`](./evaluator/reports/v4.1b_scoreboard.md)
- **可复算聚合证据：**
  [`轨迹统计脚本、哈希清单与 CSV/JSON`](./evaluator/trajectory_evidence/README.md)

原始 session/OpenCode 导出包含完整 reasoning、system prompt、绝对路径和本地环境信息，
因此只在私有证据目录保留；公开仓库提供源文件 SHA-256、复算脚本和不含原文的聚合统计。

## Directory Layout

```text
modeltest/
├── workspace/          # 候选工作区:被测工程副本 + 公开说明 + public tests
│   ├── project2_task/  #   待完善的本地项目代码(默认就在这里测模型)
│   ├── ONBOARDING_TODO.md
│   ├── reference/      #   公开参考材料
│   ├── tests/public/   #   公开单元测试
│   └── tools/          #   本地自检脚本(run_debug_probe / run_espidf_build)
├── evaluator/          # 自动化提测控制区:hidden tests / scoring / results
│   ├── run_full_eval.py        # 主评测入口
│   ├── make_broken_project.py  # 重置 broken seed
│   ├── scoring/                # 评分逻辑(已 SHA-256 冻结)
│   ├── tests/hidden/           # 隐藏测试(候选不应读)
│   ├── results/                # 每次跑分的证据链
│   ├── reviews/                # 每个模型的评审 .md
│   └── reports/                # scoreboard / freeze_manifest 等
├── docs/               # 设计文档、轮次总结、最终评估
├── README.md  PROJECT_FROZEN.md  CANDIDATE_PROMPT.md  REVIEWER_PROMPT.md
└── requirements.txt    # evaluator 依赖(候选工程依赖见 workspace/project2_task/)
```

- 模型工作区应限定在 `workspace/` 或 `project2_task/`,**不要**把整个 `modeltest`
  根(含 `evaluator/`、`docs/`)当可读范围。
- `evaluator/tests/hidden/`、`evaluator/scoring/`、`evaluator/results/` 只给内部
  校验使用,候选不应读。

## Quick Start

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install -r workspace/project2_task/requirements.txt   # 候选工程与 hidden tests 需要
```

### 2. 重置 broken seed

```powershell
python evaluator\make_broken_project.py
```

`make_broken_project.py` 默认从 `evaluator/broken_backup/project2_broken_seed/`
重置 `workspace/project2_task/`。如需从一个完整工程重新生成损坏版种子:

```powershell
python evaluator\make_broken_project.py --source C:\path\to\completed_project2
```

生成种子时会排除评测目录、`.git/`、缓存、构建目录和本地数据库。

### 3. 让模型只改 `workspace\project2_task`

把 `CANDIDATE_PROMPT.md` 正文交给模型,cwd 最好设在 `project2_task` 或 `workspace`。

### 4. 评测

```powershell
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CHANNEL --harness HARNESS `
  --require-meta --include-espidf-build `
  --run-group-id GROUP --run-index 1 --thinking-level high
```

下一模型前再执行 `make_broken_project.py`。

## Core Development Scope

提测核心检查主要考察:

- 管理员初始化、登录、Cookie 会话和管理 API 鉴权。
- v3 授权上下文的权限裁剪,避免未认证或越权泄露患者数据。
- 睡眠 CSV 多床位归属策略。
- 跨模块新增 `care_event`:DB、API、授权上下文和文档。
- v2/v3 API、worker 调用路径、ESP set 接口的回归兼容。
- ESP32-S3 `esp32/testpro4` Wi-Fi + MQTT 巴法云回传、协议打包、NVS 配置和
  ESP-IDF 静态契约。
- `project2_task/PULL_REQUEST_TEMPLATE.md` 中开发人员对自己完成工作的说明,需和
  实际 diff、测试日志一致。

RK3588 推理、摄像头、真实传感器、烧录和真实 Wi-Fi/MQTT 连通不在自动化中直接验证
(需要硬件环境)。ESP32-S3 固件修复本身是必做项,`run_full_eval.py` 默认运行
ESP-IDF 静态契约检查;Windows EIM ESP-IDF 编译作为可用环境下的额外验证。

## ESP-IDF Build Test (optional)

ESP-IDF 构建验证是**可选项**。脚本通过环境变量定位你的 ESP-IDF 安装,不再硬编码
任何本机路径:

| 环境变量 | 用途 | 默认 |
|---|---|---|
| `ESP_IDF_ACTIVATION_SCRIPT` | ESP-IDF PowerShell 激活脚本路径 | 空(必须设置) |
| `ESP_IDF_BUILD_ROOT` | 构建镜像根目录 | 系统 temp |
| `ESP_IDF_TOOLS_PATH` | IDF 工具目录(ninja/ccache/cmake) | 空 |
| `ESP_IDF_TARGET` | 目标芯片 | `esp32s3` |
| `ESP_IDF_BUILD_JOBS` | 并行编译任务数 | CPU 核数 |

```powershell
$env:ESP_IDF_ACTIVATION_SCRIPT = "C:\path\to\your\idf_profile.ps1"
python .\evaluator\run_espidf_build.py .\workspace\project2_task

# 等价 PowerShell 入口:
powershell -ExecutionPolicy Bypass -File .\evaluator\run_espidf_windows_build.ps1 `
  -ProjectDir .\workspace\project2_task `
  -Target esp32s3
```

约定:

- 不使用 Docker 或 WSL,直接使用 Windows EIM 安装的 ESP-IDF v6.0.x。
- 脚本会复制 `esp32/testpro4` 后再运行 `idf.py -B build set-target esp32s3` 和
  `idf.py -B build build`,避免污染候选源码树。
- 正式 `run_full_eval --include-espidf-build` 会把 build log、bin、大小与 SHA256
  固化到本次 result 目录。
- 只编译,不 flash,不 monitor,不验证 ToF 上电时序、真实 USB 枚举、Wi-Fi/MQTT 连通
  或真实 I2C 读数。

## Optional: 外部 handoff(正式隔离投放)

需要「模型绝对看不到 evaluator」或要留一份可归档投放包时,再用:

```powershell
python evaluator\prepare_candidate_handoff.py
# 把脚本打印的 candidate_workspace 作为模型根目录
# 评测打印的 candidate_project
```

脚本在评测目录外创建带时间戳目录,只复制 `ONBOARDING_TODO.md`、`reference/`、
`tests/`、`tools/`、`project2_task/`,不复制 evaluator。日常单人锚点不推荐默认使用
(占盘、多一步路径)。

## Results & Reports

- 现行成绩榜:[`evaluator/reports/v4.1b_scoreboard.md`](./evaluator/reports/v4.1b_scoreboard.md)
- DeepSeek V4 Pro 正式版与 harness 对照分析:
  [`docs/v4.1/DEEPSEEK_V4_PRO_HARNESS_ANALYSIS_20260814.md`](./docs/v4.1/DEEPSEEK_V4_PRO_HARNESS_ANALYSIS_20260814.md)
- DeepSeek V4 轨迹风格、PTC 与可复算统计:
  [`docs/v4.1/DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md`](./docs/v4.1/DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md)
- 最终评估与使用阈值:[`docs/v4.1/FINAL_ASSESSMENT_20260719.md`](./docs/v4.1/FINAL_ASSESSMENT_20260719.md)
- 轮次事实终稿:[`docs/v4.1/ROUND_SUMMARY_20260719.md`](./docs/v4.1/ROUND_SUMMARY_20260719.md)
- 评分面冻结哈希:[`evaluator/reports/v4.1b_freeze_manifest.md`](./evaluator/reports/v4.1b_freeze_manifest.md)
- 全部报告清单:[`evaluator/reports/README.md`](./evaluator/reports/README.md)

## Disclaimer

本项目是个人为「在真实渠道、成本与可用额度约束下,为自己的开发/选型提供一份参考
台账」而做的自测套件,并非面向社区的公开 benchmark。90 / 95 是**本项目、本题面、
本工具环境**下的经验阈值,不具跨项目可比性。harness/渠道差异是选型现实的一部分,
已在报告中全部标注。代码与文档按「现状」公开,不提供任何担保。
