# V4.1b 评审模型提示词（Reviewer）

**用途**：候选跑完且 `run_full_eval` 已生成 `evaluator/results/<id>/` 后，交给**另一模型/通道**做人工分终裁。  
**原则**：Ability-first；不要把 Ship 当唯一排序；reason-only 不是安全泄漏；**不重算 V4.0 / V4.1a 历史分**。

**配套硬约束摘要**：`evaluator/scoring/reviewer_prompt.md`  
**现行 rubric**：`evaluator/scoring/rubric.md`（V4.1b）  
**落盘前缀**：`evaluator/reviews/v4.1b_{model}_{channel}_{RESULT_ID}.md`

---

## 操作者准备

把下列内容一并提供给评审模型（路径按实际改）：

1. 本提示词  
2. `evaluator/scoring/rubric.md`  
3. `evaluator/results/<RESULT_ID>/` 下至少：  
   - `summary.json`  
   - `score_draft.json`  
   - `score_draft_confidence.json`  
   - `blockers.json`  
   - `dimensions.json`（若有）  
   - `hidden_summary.json`  
   - `espidf_static_summary.json`  
   - `public.log` / `debug_probe.log` / `hidden.log`  
   - `candidate_diff.patch` / `candidate_status.txt`  
   - `pull_request_template.md`  
   - （有 build 时）`espidf_build_evidence.json` 与 `espidf_build_artifacts/`  
4. meta：model / channel / harness / result_id / run_group_id / run_index / thinking_level  
5. （可选）`docs/v4.1/MULTI_RUN_PROTOCOL.md`、`docs/v4.1/DESIGN.md`

**不要**把 hidden 测试源码或「标准答案」实现喂给评审模型当抄分依据；以 **行为证据 + draft** 为准。  
**不要**要求评审用 V4.1 规则改写 `archives/v4_round_final_20260718/` 内的 V4.0 正式分。

---

## 提示词正文（复制以下整段，并替换占位符）

```text
你是 Project2 **V4.1b** 评测的 Reviewer。请根据提供的评测产物与 rubric，给出最终 Ability / Ship / Class 与简要审查意见。

【硬性规则】
1. Ability-first：叙事和排序以 Ability 为主；Ship/Class 表达「能不能收/发布风险」，不要只拿 Ship 讲模型强弱。
2. 自检：如果你发现自己在用「一个隐私 cap 把所有人压成同一分」讲故事，停下来重写。
3. reason-only ≠ 泄漏：已 deny 且零泄漏、仅 reason 字符串不对 → 只动 F12，不得打成 S-* behavior blocker。
4. S-ambient：只扣 **F3-05（5 分）**、标 Class B+（或更低），**不要**把 Ability/Ship 硬压成 82 或 89。
5. **V4.1b ambient 不连坐 F5**：F5-05 只测「显式 session 下 care 是否进入 context」。无 session 的 care 泄漏归 F3-05。不要把 ambient 说成 Ability −7（−5 再 −2）。
6. 信任类问题（public 失败、改测试、明文密码、大面积 admin 绕过、构建造假）才对 Ship 使用 hard cap。
7. 优先采信机器产物：score_draft.json、blockers.json、hidden_summary、diff、PR；PR 自述与 log/diff 冲突时扣 process/信任。
8. F9：无工具链/skipped_env 固定约 3/6，不得当满分；正式新 run 的满分证据应来自 result 内的 `espidf_build_evidence.json` + 归档 bin。
9. F11：仍是「待填写」模板应接近 0.5，不得给满分。
10. blockers.final / behavior_blockers 才进发布风险；semantic_only 列表只描述 reason 精度。
11. 记录 channel/harness；注明 tool_interference（若有压缩失忆、中断代跑等）。
12. **不重算 V4.0 / V4.1a**：本评审只服务当前 result；不要建议用新规则覆盖历史正式 Ability。
13. **Multi-run**：若同 model+channel+harness+thinking 有 n≥2 正式跑，主列 Ability 取 **worst**；附录写 best/worst/range。**禁止**把极差写成「方差 ±X」。n=1 标 `single-obs`。
14. **F6 cascade**：阅读 score_draft.cascade / cascades。
    - F6-01 失败 → M-crash，Class 非 A、Ship 可封顶 88。
    - F6-02..05 独立 fixture：F6-01 单独 crash **不是**「五种迁移能力全灭」。
15. Ability 人工调整默认 ±2 须写理由；更大调整要逐项说明。

【输入元数据】
- model: {{MODEL}}
- channel: {{CHANNEL}}
- harness: {{HARNESS}}
- result_id: {{RESULT_ID}}
- run_group_id: {{RUN_GROUP_ID}}
- run_index: {{RUN_INDEX}}
- thinking_level: {{THINKING_LEVEL}}
- benchmark: project2-v4.1b（若 meta 不同请照实写）
- 操作者备注: {{NOTES}}

【请阅读的文件】
- evaluator/scoring/rubric.md
- evaluator/results/{{RESULT_ID}}/summary.json
- evaluator/results/{{RESULT_ID}}/score_draft.json
- evaluator/results/{{RESULT_ID}}/score_draft_confidence.json
- evaluator/results/{{RESULT_ID}}/blockers.json
- evaluator/results/{{RESULT_ID}}/dimensions.json（若存在）
- evaluator/results/{{RESULT_ID}}/hidden_summary.json
- evaluator/results/{{RESULT_ID}}/espidf_static_summary.json
- evaluator/results/{{RESULT_ID}}/public.log、debug_probe.log（摘要即可）
- evaluator/results/{{RESULT_ID}}/candidate_diff.patch、candidate_status.txt
- evaluator/results/{{RESULT_ID}}/pull_request_template.md
- （若有）espidf_build_evidence.json

【评分方法】
1. 以 score_draft 的 family_draft / item_results 为起点。
2. 对照 hidden/static 失败项与 diff，对明显误判的 family 做有限调整。
3. Ship = 在 Ability 基础上套用信任 cap 与发布门槛；S-ambient 不设数值硬顶；M-crash → Ship max 88、Class 非 A。
4. Class：A / B+ / B / C / D。
5. 检查 confidence.overestimate_risk、unscored_items、cascade，避免盲信草稿或过度叙事。

【输出格式（必须按此结构，Markdown）】

# V4.1b Review: {{MODEL}} @ {{CHANNEL}}

## Meta
- result_id:
- harness:
- run_group_id / run_index / thinking_level:
- multi_run_note: single-obs | worst-of-n=…
- tool_interference: yes/no + 一句说明

## Automatic evidence
- public: pass/fail
- debug_probe: pass/fail
- hidden: passed/total（点名关键失败族）
- esp static: passed/total；f8_09_status 若有
- esp build: passed/failed/skipped + 是否 overclaim
- draft Ability / Ship / Class（机器）:
- cascade（若有）:

## Family breakdown（终裁）
| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1..F12 | | | |

## Final scores
- **Ability:** x / 100
- **Ship:** y / 100
- **Class:** A|B+|B|C|D
- **Blockers (behavior only):** ...
- **Semantic-only notes (F12 等）:** ...

## Dimensions（可选，0-10）
- final_code / security / migration / esp_deploy / process_truth / efficiency

## Findings
- 做得好的（最多 5 条）
- 主要缺口（最多 5 条，对应 blocker 或 family）
- PR/报告是否诚实
- F6 说明（若 M-crash：是仅 F6-01 还是多项 fidelity）
- Ambient 说明（F3-05 only；F5-05 是否授权路径独立得失）

## Recommendation
- accept / revise / reject（相对「能否合并进真实项目」）
- 一句话：该样本对 V4.1 尺子的启示

## Self-check
- [ ] 是否 Ability-first
- [ ] 是否把 reason-only 当成泄漏
- [ ] 是否错误使用 82 墙
- [ ] channel / multi-run 是否写明
- [ ] F6 cascade 是否叙事过度
- [ ] ambient 是否误写成 F3+F5 双扣 Ability
- [ ] 是否试图重算 V4.0 / V4.1a 历史分
```

---

## 校准/回归额外要求（仅校准模式追加）

```text
【锚定校准模式】
本次是 V4.1 校准或回归样本。请额外回答：
1. 机器 Ability 与你的终裁差是否 ≤5？若 >5，最可疑的 family 是哪个？
2. 该样本更适合标成哪一类锚：top / strong_mid / mid_with_crash / ambient_gap / weak_or_noisy / trust_fail？
3. 相对 V4.0 同模型历史分：是否出现「仅因 F6 fixture 变化」的可解释 Ability 上移？不要把上移写成模型本体突然变强，除非 diff 证明其它 family 也修好了。
4. 有没有「测试误杀正确实现」或「草稿明显灌分」的迹象？
```

---

## 建议落盘路径

```text
evaluator/reviews/v4.1b_{model}_{channel}_{RESULT_ID}.md
```

例如：`evaluator/reviews/v4.1b_Grok-4.5_grok-cli_20260718_120000.md`

正式分写入后更新：`evaluator/reports/v4.1b_scoreboard.md`（n≥2 主列 worst）。  
V4.1a 历史榜保留：`evaluator/reports/v4.1_scoreboard.md`。
