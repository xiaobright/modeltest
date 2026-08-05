# Codex 上下文交接 2026-07-14

这份文件用于当前长对话压缩后的工作恢复。它不是候选模型可见材料，不得放入
PlanExec candidate handoff。压缩后先读本文件，再以磁盘和用户最新消息为准。

## 1. 压缩后第一件事

1. 读取用户压缩后的最新消息，确认 Luna 是否已经完成 Phase 1 回修。
2. 读取：
   `E:\Desktop\mytests\modeltest-planexec\docs\PHASE1_POSTMORTEM_REPAIR_HANDOFF.md`。
3. 在 `E:\Desktop\mytests\modeltest-planexec` 重新运行只读检查：

```powershell
git status --short
git log -5 --oneline --decorate
git diff --stat
git diff
```

4. 不要假定本文件记录的 00:01 工作树仍是最新状态；Luna 已可能继续修改或提交。
5. 若 Luna 已完成，按 code review 方式先列 findings，再决定是否回修；不要直接相信
   “测试通过”摘要。

## 2. 三个项目的角色

### V4 frozen 主项目

```text
E:\Desktop\mytests\modeltest
```

- 当前 cwd 所在项目。
- 根目录是 non-git source tree。
- V4.0 已冻结，正式 scoreboard、Gold、历史 V2/V4 结果和设计文档都在这里。
- 除非用户明确要求，不修改 V4 frozen 评分、Gold、hidden tests 和历史 evidence。

关键文件：

```text
evaluator\reports\v4_scoreboard.md
evaluator\reports\v4_v2_comparison_final.md
docs\V5_DESIGN_DIRECTION.md
docs\PLAN_GUIDED_EXECUTION_BENCHMARK_HANDOFF.md
docs\PLANEXEC_CONTROL_PLANE_SCENARIO_HANDOFF.md
docs\PLANEXEC_LUNA_P0_REVIEW.md
docs\PLANEXEC_LUNA_P1_REVIEW.md
```

### PlanExec 控制面

```text
E:\Desktop\mytests\modeltest-planexec
```

- 固定专家计划 + 模型执行 + 可选返修的独立测试项目。
- 当前基线 commit：`92b5398 Fix phase timing and cumulative economics`。
- 状态一直是 `implemented / pre-freeze`，不得宣布 frozen。
- 场景：`v4-plan-replay`，候选项目：`project2_task`。
- official candidate handoff 根：
  `E:\Desktop\mytests\modeltest_planexec_handoffs\<run_id>\workspace`。

关键文件：

```text
docs\AI_TEST_OPERATOR_HANDOFF.md
docs\PHASE1_POSTMORTEM_REPAIR_HANDOFF.md
reports\phase-summary-20260713.md
reports\aggregate.md
reports\aggregate.json
```

### 真实项目原型分支

```text
E:\Desktop\myproject\project
```

- 只读题源/真实项目参考，不属于当前回修目标。
- 仍有用户修改，绝不能回滚：

```text
M  esp32/testpro3/dependencies.lock
?? 审查结果.txt
```

## 3. 当前用户决定

用户已经决定下一轮：

- 测一轮成本和精力都高，先把评测控制面修好再测。
- 后续主要测试强模型，弱模型不再大规模铺开。
- 主要看 P0 第一次实现能否达到 95 以上。
- 对第一次已经达到 95/98 且无安全硬伤的模型，不再默认进行同模型返修。
- 同模型 P1 对顶部样本意义很小：GLM/Grok/Composer 都是 0 分收益，Luna还出现
  -2 分回归。
- 现实工作流更倾向于：强模型规划 -> 便宜/顺手模型实现 -> 强模型终审并直接修
  最后细节，而不是反复让原执行模型接收模糊 review packet。
- P1 仍可保留为显式 repairability 诊断，但不进入默认主轨。

主轨拟定 P0 pass：

```text
Ability >= 95
Ship >= 95
F9 == real_pass
无 trust/security hard blocker
无 F-public、T-tamper、E-build/build overclaim
```

`E-contract` 可以让 scorer 的 Class 保持 B+，但满足上述条件仍可视为“P0 首次实现
达标”。不要把 P0 pass、Ability>=95 和 Class A 混为一谈。

## 4. PlanExec Phase 1 六个正式样本

所有样本都是 n=1 single observation。

| run/model | V4 对照 | P0 | P1 | Ship/Class | model cost | P0/P1 measured wall |
|---|---:|---:|---:|---|---:|---:|
| GLM-5.2 | 82 | 98 | 98 | 98/B+ | $3.53+$3.06=$6.59 | 26.0m/22.4m |
| Grok-4.5 r2 | 82 | 98 | 98 | 98/B+ | unknown | 19.3m/7.0m |
| Composer-2.5 | V4 92，重跑82 | 98 | 98 | 98/B+ | unknown | 400.1m/8.8m |
| Qwen-3.7-Max | 76 | 91 | 98 | 98/B+ | $3.37+$1.20=$4.57 | 43.0m/58.6m |
| GPT-5.6 Luna high | 98 | 94.5 | 92.5 | 92.5/B+ | $1.09+$0.36=$1.45 | 20.3m/6.6m |
| DeepSeek V4 Pro | 82 | 83 | 93 | 65/D | $0.11+$0.05=$0.16 | 16.0m/9.2m |

正式 run ID：

```text
glm5-2-max-r1-20260713
grok-4-5-high-r2-20260713
composer-2-5-medium-r1-20260713
qwen-3-7-max-medium-r1-20260713
gpt-5-6-luna-high-r1-20260713
deepseekv4pro-max-r1-20260713
```

另有 `grok-4-5-high-r1-20260713` 因与 GLM P1 共享 ESP build 资源冲突而人工中止，
不应进入正式 aggregate。

## 5. Phase 1 已确认的模型结论

### 固定计划的主效应

- GLM 82 -> P0 98、Grok 82 -> P0 98：两者 V4 卡点主要是规划、隐含风险发现和
  全仓覆盖，不是给定明确任务后的编码能力。
- Composer P0 98：固定计划至少能把它带到顶部，但只有一次样本，不能证明方差已消失。
- Qwen 76 -> P0 91 -> P1 98：目前最能证明“专家计划 + 症状级返修”有效的样本。
- DeepSeek P1 修复完整 migration，Ability +10；但管理员绕过和 voice regression
  未解决，Ship 仍65。便宜不等于可交付。
- 顶部三个模型全部停在 98且漏完全相同两项，说明固定计划已经造成明显 ceiling
  compression。未来主指标应偏向 P0 pass、成本、时间、回归和干预，而不是只排最终分。

### 同模型 P1 的收益

- GLM：P1 $3.06、22.4分钟、0 分收益。
- Grok：P1 7分钟、0 分收益，费用未知。
- Composer：P1 8.8分钟、0 分收益，且新增 `P-report` blocker。
- Luna：P1 6.6分钟/$0.36，Ability -2并引入回归。
- Qwen：P1 +7，属于有价值的中档返修。
- DeepSeek：P1 Ability +10但 Ship +0，不是发布成功。

因此：P0 已达到 95/98 且无严重 blocker 时，默认不再花钱跑同模型 P1。

## 6. ESP-IDF/MQTT 结论和信息边界

Phase 1 正式 evidence：

- GLM、Grok、Composer、Qwen、DeepSeek 的 P0/P1 F9 real build 均通过，F9=6/6。
- Luna P0/P1 build 均失败，return code 1，F9=3.5/6（诚实报告失败）。
- 六个模型都漏 `V4-F8-03` 的直接 MQTT/lwIP 依赖静态项，通常再漏 no-actor exact
  reason，因此顶部集中在 98。
- 旧阶段报告“所有模型编译成功”“最终编译评分均为0”是错误/混淆表述，必须纠正。

用户补充：

- Luna 表示 MQTT 遇到问题；严格不能查看 workspace 外路径，网络搜索又不可用，因此
  没收口 ESP-IDF 6.0 MQTT 变化。
- Grok 和 DeepSeek 在同类限制下，仅靠编译日志推导出 ESP-IDF 6.0 的 MQTT 变化，
  这是有效的闭卷诊断能力差异。
- GLM/Qwen 是否读取本地 SDK、具体边界仍应按 run annotation 确认；不能猜。

未来如果测试 local-SDK-assisted 轨：

```text
只允许只读 E:\esp\v6.0.1\esp-idf
禁止开放整个 E:\esp
尤其禁止 E:\esp\builds
```

原因：`E:\esp\builds` 含其他候选镜像和构建产物，会泄漏答案。不同信息条件必须记录：

```text
workspace_only
workspace_plus_local_sdk
network_enabled
```

但用户当前决定先不补跑 Luna，先修控制面。

## 7. Phase 1 报告/评测器已确认的问题

### Aggregate schema 漂移

`final_report.json` 当前使用：

```text
economics.operational
economics.cost_to_b_plus
economics.cost_to_a
```

`evaluator/aggregate_runs.py` 仍读旧字段：

```text
economics.total
economics.threshold_costs
```

所以 aggregate 成本全是 null。actual/estimate 还被错误地要求同时完整，导致有 actual、
无 estimate 时也不能得到 operational actual。

### Ability 阈值与 Class 混淆

aggregate 的 `p0_a_probability` 实际只计算 `Ability >= 95`，不是 `Class == A`。
应拆成：

```text
ability_ge_95_rate
class_a_rate
p0_pass_rate
```

V4 scoreboard 曾把部分 `98 + E-contract` 人工列为 A；canonical scorer 实际映射 B+。
Ability 可跨版本比较，Class 暂时不能直接对照。

### ESP build 隔离

旧路径共享：

```text
E:\esp\builds\modeltest\project2_task
```

不同 run/stage 共享 candidate mirror、CMakeCache 和 Ninja state，已经触发并发冲突，
也存在增量污染风险。新目标：

```text
E:\esp\builds\modeltest-planexec\<run_id>\<stage>\project2_task
```

仅允许共享 ccache；不删除旧 build 目录。

### Intervention 缺失

阶段报告记录 Qwen 网络、本地 SDK、MSYSTEM、超时/重跑等事件，但所有 finalized
manifest 的 `human_interventions` 仍为空。需要新 CLI 和 information regime；旧 manifest
不得回写，只能用 versioned posthoc annotations 纠正派生报告。

### Regression attribution 漏项

当前只比较正分 item earned。Composer P1 新增零分辅助项 `P-report` blocker，但
`introduced_regression_item_ids` 为空，阶段报告错误写成“无 regression”。新 final report
需比较 introduced/resolved behavior blockers 和 semantic failures。

### 时间不可比

- Composer P0 400分钟包含长时间人工闲置。
- Qwen evaluator P1 包含外部工具超时后的数小时空档。
- measured wall、operator wall、active model time 必须分开，不能猜 active time。

### Candidate workspace 根 Git

现有 `prepare_run.py` 只给 `workspace\project2_task` 保留内层 Git，workspace 根 Git
由操作员手工建。用户要求 official candidate 打开的 workspace 根本身就是边界仓库，
避免工具向上发现控制仓库。

目标是 official external handoff 自动建立外层单提交 Git，保留内层项目 Git。calibration
workspace 位于控制仓库内部，不投放候选，不能套 official ancestor-Git 拒绝规则。

## 8. 已写给 Luna 的回修交接

完整要求在：

```text
E:\Desktop\mytests\modeltest-planexec\docs\PHASE1_POSTMORTEM_REPAIR_HANDOFF.md
```

实施顺序：

1. P0-only 状态机/final report；
2. official workspace 根 Git 自动化；
3. ESP build root 按 run/stage 隔离；
4. economics/aggregate schema；
5. intervention/information regime；
6. blocker regression attribution；
7. 时间展示；
8. corrected Phase 1 报告和操作文档；
9. unittest、synthetic、一次 Gold真实 ESP build；
10. 一致性审计和 commit。

重要非目标：

- 不改 V4 scoring/item registry/Gold/hidden semantics；
- 不重跑任何真实模型；
- 不新增 V5题目或实机测试；
- 不删除或移动旧 handoff/run/build/archive；
- 不改真实项目；
- 不宣布 frozen。

验收报告应产生：

```text
reports\phase-summary-20260713-corrected.md
reports\phase-summary-20260713-corrected.json
corrected aggregate
```

旧 snapshots/evaluations/control snapshots/finalized manifests/final reports 必须保持不变；
派生报告可重建，但要标注来源。

## 9. 2026-07-14 00:01 的进行中工作树快照

在编写本文件时，PlanExec 工作树是：

```text
M  README.md
M  evaluator/common/paths.py
M  evaluator/common/state.py
?? docs/AI_TEST_OPERATOR_HANDOFF.md
?? docs/PHASE1_POSTMORTEM_REPAIR_HANDOFF.md
```

其中 README 和两个 docs 是本对话写入的用户要求内容。`paths.py`、`state.py` 是之后
出现的外部/Luna进行中修改，不是本轮 Codex 写入，绝不能回滚。

截至 00:01 已看到的部分实现：

- `paths.py` 新增：

```text
ESP_BUILD_ROOT = E:\esp\builds\modeltest-planexec
stage_build_root(run_id, stage)
```

- `state.py` 新增允许：

```text
p0_evaluated -> finalized
```

这只是进行中快照，尚未审查，也不能据此判断需求完成。尤其需要确认 finalizer 是否
正确生成 P0-only schema、是否保留 fail-closed 状态、是否避免直接 transition 绕过证据
验证。

压缩后必须重新读实时 diff；如果出现用户/Luna新修改，继续在其基础上工作。

### 00:07 追加状态

在本交接写完后的六分钟内，Luna继续推进。2026-07-14 00:07:36 的工作树已经变为：

```text
M  README.md
M  evaluator/aggregate_runs.py
M  evaluator/common/paths.py
M  evaluator/common/state.py
M  evaluator/demo_synthetic.py
M  evaluator/evaluate_stage.py
M  evaluator/finalize_run.py
M  evaluator/freeze_stage.py
M  evaluator/prepare_run.py
?? docs/AI_TEST_OPERATOR_HANDOFF.md
?? docs/PHASE1_POSTMORTEM_REPAIR_HANDOFF.md
?? evaluator/record_intervention.py
?? evaluator/start_phase.py
```

当时 diff 约为 350 insertions / 153 deletions，仍未提交。新增/扩展范围已经覆盖：

- P0-only finalize；
- aggregate；
- build path；
- prepare/workspace；
- explicit phase start；
- intervention CLI；
- synthetic workflow。

这些都只是实时进行中修改，尚未读取完整 diff、运行测试或接受审查。压缩后若 Luna
仍在运行，不要与它并发编辑同一批文件；等待用户确认完成，再做完整 review。

## 10. Luna 完成后的审查清单

按 finding-first code review：

1. 检查 commit、完整 diff、未提交文件；确保 README 和两个 handoff docs 未丢。
2. 确认已有 official/calibration evidence 未被修改、重写或删除。
3. 检查 P0-only：
   - 只能从已验证 `p0_evaluated` finalize；
   - threshold_met 由程序校验；
   - P1 为 null，不复制 P0；
   - below-threshold no-repair 能记录失败；
   - optional P1 仍可显式运行。
4. 检查 P0 pass：Ability、Ship、F9和 hard blockers 全部参与，不能只看 Ability。
5. 检查 ESP build path 对每个 run/stage 唯一，artifact 从同一路径归档；不能共享
   CMake/Ninja candidate state。
6. 检查 economics actual/estimate 独立完整性，aggregate 不再读旧 schema。
7. 检查 `ability_ge_95_rate` 与 `class_a_rate` 分离。
8. 检查 intervention/information regime 进入 final report 和 aggregate grouping。
9. 检查 Composer 新 `P-report` 能作为 blocker regression 被发现。
10. 检查 outer Git 只用于 official external handoff；calibration 不被 ancestor rule 阻断。
11. 检查 corrected report：5个 build pass、Luna fail；四个已知成本正确；两个成本
    unknown 保持 null；n=1无 mean/median。
12. 检查实际 Gold build evidence：独立路径、return code 0、result-local bin/log/hash。
13. 运行或核实 unittest、synthetic；不调用真实模型。
14. 检查状态仍为 implemented/pre-freeze。

如果 Luna已经提交，先 `git show --stat --oneline HEAD` 和 `git show HEAD`；不要因为它说
“单一清晰 commit”就忽略工作树里可能仍有未提交用户文档。

## 11. 早期 PlanExec 构建成本背景

PlanExec 控制面本身是 Luna按固定 handoff 实现：

```text
初次实现：$2.28
第一次返修：$2.70
第三次返修：$2.16
Luna总计：$7.14
两轮返修合计：$4.86（约68%）
专家计划 authoring：约$2.50
计划 + Luna：约$9.64（未含审查者成本）
```

长间隔会掉缓存，使返修更贵；程序即时生成 review 时通常更接近热缓存。这个背景促成
当前 P0-first 决策。

## 12. V4/V5 仍需记住的结论

- V4 Gold=100，broken seed=45.5；V4没有 V3.1 那种区分度退化。
- V4顶部 GPT-5.6 sol/luna xhigh 99，luna high 98；但高思考档多花的钱和时间主要追
  最后一分，high 往往更实际。
- V4中 GLM三个渠道集中81-82；Kimi 90、Composer首跑92。排序反转说明模型画像和
  provider/产品层很重要，不能把 harness 当 provider。
- GLM-5.2 V2的95来自硅基流动满血按量 API；V4 OpenCode Go/免费渠道81-82，不是
  同 provider 对照，不能直接归因模型退化或量化。
- V4 F6 migration 对部分非 GPT-5.6 模型出现约10分方差；远期应拆细，但当前不改。
- V5、V4 Pro/Pro Max、QEMU、真机自动化、RST/BOOT硬件控制都已记录在
  `docs/V5_DESIGN_DIRECTION.md`，近期不施工。
- 独立 control-plane capstone 方案在 `docs/PLANEXEC_CONTROL_PLANE_SCENARIO_HANDOFF.md`，
  已决定延期，不新建昂贵场景。
- 远期真实硬件测试有价值，但环境混沌、串口/RST和调试时间使其不适合当前常规轮次。

## 13. 文件删除和数据安全

任何删除都必须遵守：

1. 先只读盘点；
2. 列出每个拟删除对象的精确绝对路径、内容、删除理由、唯一副本风险；
3. 等用户对这份具体清单明确确认；
4. 只能删除确认清单中的对象；
5. 删除前再次验证绝对路径，删除后核对保留结果。

当前回修没有任何删除需求。不得清理旧 handoff、aborted run、ESP build、archive、
reports 或真实项目用户文件。

## 14. Windows/ESP 环境

ESP-IDF v6.0.1 使用 Windows EIM，不切 WSL：

```text
ESP-IDF：E:\esp\v6.0.1\esp-idf
激活脚本：E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1
工具目录：E:\esp\tools
```

构建必须阻塞等待，shell timeout 给足，不默认后台轮询。标准形式：

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ". 'E:\esp\tools\Microsoft.v6.0.1.PowerShell_profile.ps1'; Set-Location -LiteralPath '<project>'; idf.py build"
```

Conda若需要：

```powershell
& 'D:\ProgramData\anaconda3\condabin\conda.bat' info --envs
& 'D:\ProgramData\anaconda3\condabin\conda.bat' run -n <env> <command>
```

## 15. 当前最近请求的正确落点

用户当前不是要求再设计题目，也不是要求立刻重跑 Luna。当前序列是：

```text
Phase 1结果分析
-> 决定强模型/P0-first
-> 写 Luna回修交接
-> Luna可能正在实现
-> 压缩上下文
-> 等 Luna完成后审查实现
```

压缩后不要被旧的 V5、独立场景或补跑模型请求带偏。最新主任务是保障
`modeltest-planexec` 的 Phase 1 回修正确落地，然后再决定下一轮强模型测试。
