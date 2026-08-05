# V4 Seed、提示词与可见边界

## 1. 边界（不变且为设计一部分）

```text
modeltest/
├── workspace/     # 候选唯一可见
└── evaluator/     # 不可见；评测控制面
```

候选可见：

- `workspace/ONBOARDING_TODO.md`
- `workspace/reference/`
- `workspace/tests/public/`
- `workspace/tools/`（含 debug probe、ESP 构建入口）
- `workspace/project2_task/`

候选不可见：

- `evaluator/**`、`docs/v4/**`（评测设计）、`archives/**`、hidden、scoring、broken 生成逻辑细节

**实施注意**：若仓库整包发给模型，应用脚本或目录拷贝保证只暴露 workspace；文档中写明标准投放方式。

## 2. Seed 策略

### 2.1 基底

- 以 **当前 V2 broken seed**（`evaluator/broken_backup/project2_broken_seed`）为起点。  
- **不要**整树替换为 archives 里的 V3.1 workspace。  
- 新 git tag：`project2-v4-broken-seed`。  
- `make_broken_project.py` 重置逻辑保持；基线 tag 名更新。

### 2.2 手术式注入（相对 V2）

| 注入 | 目的 | 注意 |
|------|------|------|
| 旧版 `care_events` 样例库 | F6 可发现 | 放在 `project2_task/data/` 时，**public/probe 默认用 TEMP 干净库**，避免 public 必红 |
| ESP `b64_buf[256]` 诱饵 | F8-07 | 靠近 TODO，真实 ToF 载荷远大于 256 |
| voice/助手仍依赖 ambient | F4 | 收紧 context 后暴露集成问题 |
| Wi-Fi/MQTT 仍剥离/不完整 | F8/F9 | 与 V2 一致 |
| admin/auth/context/sleep/care 残缺 | F2/F3/F5/F7 | 与 V2 一致，可按 V4 项微调 |

### 2.3 public 健康标准

重置后、零修改时：

- `run_public_tests.py`：**通过**  
- `run_debug_probe.py`：**暴露症状**（允许 warning/失败项打印，不要求 exit 0）  
- hidden：**大量预期失败**  
- esp static：**部分失败**  

与 V1 分析一致：broken seed 必须是「能跑的半成品」，不是废墟。

### 2.4 脏库双轨

```text
A. 候选探索：seed 内 data/legacy_sample.db 为旧 schema（非默认 DB 路径，供候选手动打开探索）
B. 自动化 public：强制 TEMP 干净 DB（现有 configure_env 模式，不读 data/legacy_sample.db）
C. hidden F6：测试内自建旧表 fixture（不依赖 seed 文件也可）
```

**推荐**：A + B + C 同时——A 增加真实感；B 保 public；C 保判定稳定。

**路径隔离约束**：脏库必须放在 `data/legacy_sample.db` 而非 `data/project2.db`（默认 DB 路径）。V3.1 曾将脏库直接放在 `data/project2.db`，若 public test 的 `configure_env` 未严格隔离默认路径，可能导致 public 必红。V4 必须避免此问题——public 的 TEMP 干净 DB 与 seed 脏库在文件系统层面隔离。

## 3. ONBOARDING_TODO.md（V4 文案原则）

### 3.1 保留

- 团队 PR 自检闭环语气  
- 必须先跑 public + probe  
- ESP 必做 + 构建脚本  
- 终写 `PULL_REQUEST_TEMPLATE.md`  
- 禁止删功能、改测试、硬编码过关  
- Sprint 结果导向目标（鉴权、隐私、sleep、care_event、兼容、ESP、文档）

### 3.2 删除或改写（防剧透）

| 避免 | 改为 |
|------|------|
| 「敏感 target 必须显式 session_id」 | 「无可靠会话时不得带出患者明细；会话语义需自查」 |
| 「ALTER TABLE 补 ts」 | 「历史库升级后偶发启动失败或时间错乱」 |
| 「voice 要先 current session」 | 不在主列表剧透；靠 probe warning |
| 逐步根因清单 | 症状列表 |

### 3.3 Known issues 示例（症状级）

- 管理页可开，但部分管理 API 在无/假 Cookie 时仍可能被本机访问。  
- 部分 v3 session 状态、过期、主体语义不可靠。  
- care_event 有雏形，schema/路由/授权/归一化需核查。  
- 睡眠 CSV 无 room/bed 时归属易错；混合导出文件需当心。  
- ESP32-S3 USB 在，Wi-Fi/MQTT/NVS/topic/base64 与协议契约不完整。  
- 历史 SQLite 可能缺列，不能只测空库。  
- 收紧权限后，本地语音/助手联调路径可能出现「取不到护理上下文」类警告（若 probe 打出）。

### 3.4 报告文件

- **保留** `project2_task/PULL_REQUEST_TEMPLATE.md`（兼容 V2 语料与习惯）。  
- 模板强制分区：  
  1. 初始诊断（命令+摘要）  
  2. 修改说明  
  3. 最终验证  
  4. ESP 构建证据  
  5. 风险与未验证  
  6. （可选）机器可读 YAML 尾块  

不强制改名为 `answer.md`（V3.1 做法），避免无谓迁移成本。

## 4. Debug Probe V4

### 4.1 仍硬暴露的症状

- 管理 API 鉴权  
- session/context 异常  
- care_event 路由/归一化  
- 其它 V2 已有有价值失败  

### 4.2 新增 warning-only

```text
[probe:Warning] Voice/assistant path: sensitive context denied without session_id;
if local assistant relies on ambient session, sync may break. Consider fetching
/api/v3/session/current before /api/v3/context/chat.
```

- **不要**把 voice 失败写成 probe 总失败（避免模型为过 probe 恢复 ambient）。  
- 文案给方向但保留推理空间；hidden 才严格判 F4。

### 4.3 可选：旧库探测

若检测到 seed 脏库路径：打印 migration 相关 traceback/warning。  
不得让 public 依赖该库。

### 4.4 Evaluator 副本

继续：`evaluator/tools/run_debug_probe.py` 与 workspace 同步策略——评分只用 evaluator 副本。

## 5. Reference 文档

保留并轻微校准：

- `api_contracts.md`  
- `espidf_protocol_contract.md`  
- `architecture_notes.md`  
- sample payloads/CSV  

原则：

- 契约描述 **行为与格式**，少写「唯一正确函数名」。  
- reason 枚举可放契约附录，并注明 **实现必须 deny；字符串精度单独评分**。

### 5.1 api_contracts.md 去剧透（实施时必须改写，PR-C 范围内，MiniMax-M3 B2）

当前 `reference/api_contracts.md` 第 49 行直接剧透了 ambient fallback 的完整解法：

> 面向指定患者的敏感上下文必须携带显式有效 `session_id`。不能因为系统里存在最近一次 current session，就在缺少 `session_id` 的请求中自动放行患者数据。

这句话有三重剧透：直接告诉模型 ambient fallback 不合法、直接命名 `session_id` 参数、命名 "current session" 机制。V4 的设计意图是让模型自己推理出会话语义，而不是从契约里读到答案。

**改写为**（彻底去剧透，MiniMax-M3 B2）：

> 敏感上下文请求需满足授权条件；授权由会话、actor、target 三者关系决定；具体拒绝情形与契约见上节 `/api/v3/sessions` 与 `/api/v3/identity/gallery` 的失败响应。

该改写不指向任何具体参数名或机制，模型需要自行推理：哪些字段组合满足"会话 + actor + target"三者关系、过期/无 actor/跨患者时如何拒绝。hidden test `test_sensitive_target_context_requires_explicit_session` 做严格行为判定。

**V2 历史样本回归验证（PR-C 必做，验收标准）**：

改写后必须用 V2 历史样本验证去剧透是否生效：

| 样本 | V2 F3e 状态 | V4 改写后期望 |
|------|------------|---------------|
| GLM-5.2 (95) | 过 | 仍过 |
| Grok-4.5 (96) | 过 | 仍过 |
| doubao-seed-2.0-code (86) | 过 | 仍过 |
| Kimi K2.7 Code (82) | 漏 | 仍漏 |
| LongCat-2.0 (82) | 漏 | 仍漏 |
| Composer 2.5 (82) | 漏 | 仍漏 |
| DeepSeek V4 Flash (82) | 漏 | 仍漏 |

**回归失败条件**（任一触发即回滚文案）：

- V2 过的样本改写后反而挂 → 新文案有"反暗示"问题（如反向写明不要做什么），需回滚
- V2 漏的样本改写后反而过 → 新文案信息不足，模型不再受契约影响，需加深描述
- 任一行的隐藏测试行为发生不可解释变化 → 立即冻结 PR-C 实施

## 6. 历史噪声文件

`esp32/sketch_jan22a.ino`：

| 选项 | 效果 |
|------|------|
| **保留（默认）** | 真实仓库噪声；可能泄露 topic 构造线索 |
| 移出可见区 | 提高 ESP 纯推理难度 |

V4 默认 **保留**，在 review 中标注「可能提供线索」。若交叉审核要求加难 ESP，实施阶段可移到 `archives/noise/`。

## 7. 投放给候选的标准包

```text
handoff/
  ONBOARDING_TODO.md
  reference/
  tests/
  tools/
  project2_task/
```

另附用户级任务提示（可与现 `新建 文本文档.txt` 同源），要点：

- 只依赖可见内容  
- 先诊断再改  
- 禁止改测试过关  
- 写 PR  
- **不要** subagent 刷题（若你的实验协议需要）  

V4 设计不强制某一家 harness 的系统提示，但 **实验记录必须写 harness 名**。

## 8. 与 V2 提示差异清单（实施 diff 清单）

1. ONBOARDING 去剧透句  
2. Known issues 加混合 CSV / 旧库 / voice warning 症状  
3. PR 模板分区强化  
4. probe 加 voice warning  
5. seed：脏库样例（`data/legacy_sample.db`，非默认路径）+ ESP 小缓冲诱饵 + voice ambient 依赖  
6. `reference/api_contracts.md` 第 49 行去剧透（ambient fallback 解法）  
7. tag 与 make_broken 基线名  

---

下一篇：[05_EVALUATOR_PIPELINE.md](./05_EVALUATOR_PIPELINE.md)
