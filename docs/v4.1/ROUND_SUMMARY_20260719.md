# Project2 评测轮次总结（终稿 · 2026-07-18～19）

**目的：** V4.1b 锚点轮次收口；换会话 / 压缩上下文后直接读本文件 + 现行榜。  
**现行主线：** **V4.1b**（`project2-v4.1b`）  
**日期：** 2026-07-18 起尺与归档 → 07-19 补全多跑、下沿、Kimi K3  
**状态：** **本轮正式锚点已闭环，V4.1b 作为正式稳定基线**（缺 Composer 2.5：无可用渠道；Claude 未测：成本放弃）

**最终解释与远期决策：** [`FINAL_ASSESSMENT_20260719.md`](./FINAL_ASSESSMENT_20260719.md)

**前一草稿：** [`ROUND_SUMMARY_20260718.md`](./ROUND_SUMMARY_20260718.md)（中途快照，数字以本终稿与 scoreboard 为准）

---

## 0. 一句话

> 冻结 V4.0 → V4.1a（F6 不连坐）→ V4.1b（ambient 不连坐 F5）→ live 主空间锚满。  
> **主列顶端 sol worst 98**；DeepSeek 灰度 n=2 **worst 96、~$0.12/枪** 仍是 CPI 王。  
> 榜跨 **98 → 73**；**single-obs 会骗人**（luna 96→90，DeepSeek 99→96）。  
> Composer 无渠道；Claude 不测；Kimi K3 **92 / $6 / 48min** 中上偏贵慢。

---

## 1. 版本与运维（终态）

| 版本 | 含义 | 正式成绩 |
|------|------|----------|
| **V4.0** | Ability/Ship、F1–F12、Gold 100 | **冻结** `archives/v4_round_final_20260718/` — **禁止重算** |
| **V4.1a** | F6 独立 fixture；multi-run | 历史 `v4.1_scoreboard.md` |
| **V4.1b** | ambient 只扣 F3-05；F5-05 仅授权 care | **现行** `evaluator/reports/v4.1b_scoreboard.md` |

**运维默认**

- 投放：live `workspace/project2_task` + `make_broken_project.py` 重置  
- handoff：**日常不用**  
- multi-run：主列 Ability = **worst** formal；附录 best/worst/range  
- 效率副榜：`evaluator/reports/v4.1_efficiency_board.md`（**不进 Ability**）  
- K3 费用细账：`evaluator/reports/kimi_k3_cost_ledger.md`

**Gold：** `20260718_162420` → **100/A**

---

## 2. 终榜（Main Ability = worst）

| 名次 | 模型 | n | Main | Ship | Class | 费用/时（代表） |
|:--:|------|:-:|-----:|------|-------|----------------|
| 1 | **GPT-5.6-sol** Codex high | 2 | **98** | 98–99 | B+–A | ~$8.18 / ~25min |
| 2 | **DeepSeek-V4-Pro** OC 灰度 | 2 | **96** | 96–99 | B+–A | **~$0.12** / ~32min |
| 3 | GPT-5.6-terra high | 2 | **94** | 94 | B+ | ~$2.04 / ~13min |
| 3 | Kimi-K2.7-Code WB | 1 | **94** | **88** | B+ | —（M-crash） |
| 5 | **Kimi-K3** OC+Go max | 1 | **92** | 92 | B+ | **$6.13**/48min；**非官方订阅**（Go 量化存疑，不重测） |
| 6 | GLM-5.2 WB xhigh | 1 | **91** | 91 | B+ | — |
| 7 | GPT-5.6-luna high | 2 | **90** | 90–96 | B+ | ~$1.93 / ~22min |
| 7 | Grok-4.5 grok-cli | 2 | **90** | 65–88 | D–B+ | **≈$2.81** n=2（~$1.2–1.6/枪）；**很快** |
| 7 | Doubao Evolving-0714 OC | 1 | **90** | 90 | B+ | 同 0714；**≈¥13.04/~$1.81**（OC token 标价） |
| 10 | **Qwen-3.8-Max-Preview** Qoder | **2** | **87** | 87–87 | **B+** | **worst**；双枪同失分锁 87；vs 3.7 **+6**；列表¥21.26/一折¥2.12 |
| 10 | **Gemini-3.5-Flash** AG | **2** | **87** | 87–88 | **B+** | **worst**；crash 双枪；voice 满；vs V4 93 约 −5～−6 |
| 12 | HY-3 WB | 1 | **86** | 86 | B+ | — |
| 13 | **Mimo-v2.5-Pro** OC | 1 | **83** | 83 | **B** | crash+隐私+voice0；**$0.15**（≈DS 价） |
| 14 | **LongCat-2.0** OC | **2** | **82.5** | 72–94 | B–B+ | **worst**；best 94；range 11.5；≈V2 档 |
| 15 | **Gemini-3.1-Pro** AG | 1 | **82** | **60** | **D** | **明文密码**；ESP 满；费用未透明 |
| 16 | Qwen-3.7-Max Qoder | 1 | **81** | 81 | B | — |
| 17 | Minimax-M2.7 Qoder | 1 | **73** | **60** | **D** | ~¥3.55 |

完整索引与 review 路径见 `evaluator/reports/v4.1b_scoreboard.md`。

---

## 3. 主题结论

### 3.1 尺子是否达成目标

| 目标 | 结果 |
|------|------|
| 打破 F6 全家 0 双峰 | **是**。可 F6=5～10；K3/terra/Doubao 等可满 10 |
| 打破 ambient 软墙 82 扎堆 | **是**。ambient 只 −5；F5 可仍 12；顶端 98–99 |
| 拉开差距 | **是**。主列 **98→73**，中间 94/92/91/90 可辨 |
| multi-run 防运气 | **有效**。sol 99→98；DeepSeek 99→96；**luna 96→90**；terra **两枪锁 94** |

### 3.2 GPT-5.6 全家 @ Codex high（n=2 齐）

| 产品 | Main | range | 标价≈sol | 代表枪 | 模式 |
|------|-----:|-------|----------|--------|------|
| **sol** | **98** | 98–99 | 100% | $8.18 / 25min | 细节抖动（tof1）；sole 顶端 |
| **terra** | **94** | 94–94 | **50%** | $2.04 / **13min** | **ambient 稳定短板**；轻预算 |
| **luna** | **90** | **90–96** | **~20%** | $1.93 / **22min** | **方差最大**；单价低、用量大 |

- UI 都叫 high，**思考预算明显不同**：sol 最重 → luna 中重 → terra 最轻。  
- Ability worst：**sol > terra > luna**（不是单价或时长排序）。  
- **多想 ≠ 更稳**（luna 比 terra 烧得久，worst 更差）。

### 3.3 DeepSeek-V4-Pro 灰度

| 项 | 值 |
|----|-----|
| run1 | **99/A** 仅 F12 |
| run2 | **96/B+** backfill + wifi_ssid + F12 |
| Main | **96** worst |
| 费用 | 两枪各 ~**$0.12**；墙钟约 32min/枪 |
| cache 观察 | ctx 可 **200k+**，miss 仅 **~3k+** → 贵价 miss 极少（疑正式/灰度 cache 计量或命中异常；勿当全冷启动外推） |
| 相对 V4.0 | 同 harness **82→96～99** 质变（勿只归因尺子） |
| 叙事 | **能力近顶 + CPI 断层第一**；比 sol 略低分、便宜约 **70×** |
| **preview 对照** | Ability **78** / Ship **72**；费用 **$0.14**；钱同档、分差 **~18** |

### 3.4 Kimi 线

| 样本 | Ability | Ship | 要点 |
|------|--------:|-----:|------|
| K2.7-Code WB | **94** | **88** | 隐私/voice 满；**M-crash** |
| **K3** sub max | **92** | **92** | **F6=10**；**ambient** + ESP−2；single-obs |
| K3 费用 | — | — | 实付 **$6.13**；去换号缓存税 **~$5.63**；**48min** |
| K3 过程 | — | — | 旧订 $3.8 坠机 → 换号 miss $0.55 → 续完；**4×/双倍只动限额** |

- 相对 hype（Sol/Fable 级）：**中上分、旗舰价、偏慢** → 情绪上「挺拉」，技术上 **非崩盘**。  
- 相对 DeepSeek：**钱约 ×50、分更低**。  
- 相对 K2.7：迁移更好、隐私更差，总分略低。

### 3.5 中游与下沿

| 模型 | 要点 |
|------|------|
| GLM-5.2 xhigh | **91**；无 M-crash；高于 V4 中思考 81 |
| Grok-4.5 n=2 | Ability **90–91**；run1 **spoof→Ship 65/D**；run2 恢复；本地 cost **≈$1.19+$1.62**；API≈6–7min/枪，**体感快**；Harness 已开源 [xai-org/grok-build](https://github.com/xai-org/grok-build) |
| **LongCat-2.0** OC | n=2 **82.5** worst（best **94**，range **11.5**）；run2 voice0+编不过 Ship72；vs V2 **82** 贴脸；run1 神枪非平台；尺子去掉 82 墙会暴露上限也暴露方差 |
| Doubao Evolving-0714 | **90**；**同 0714 权重**非周更；F6 满、voice 0、ambient；OC token **25.3万新入+879.8万命中+3.2万出** → 标价 **¥13.04 / ~$1.81**（额度未扣仍记标价） |
| **Qwen-3.8-Max-Preview** | **87** worst n=2 @ qoder（run1/run2 皆 87，失分同构）；vs **3.7 81 +6**；隔日未见抬分；列表 **¥21.26** / 一折 **¥2.12** |
| HY-3 | **86**；ambient+no-actor；F6=5 |
| **Mimo-v2.5-Pro** OC | **83/B**；**$0.15**（≈DeepSeek 价）；no-actor+ambient+voice0+**M-crash**；ESP/auth 满；**同价非 CPI** |
| **Gemini-3.5-Flash** AG | **87** worst n=2（best 88）；**M-crash 双枪复现**；voice 满、无明文；vs 3.1-Pro 信任质变；vs V4 93 约 −5～−6；费用未记 |
| **Gemini-3.1-Pro** AG | **82/60/D**；**明文密码**（与 V4 同型）；ESP 满；Ability 低于 V4 的 90；费用未透明 |
| Qwen-3.7-Max | **81/B**；voice 0 + ESP 契约碎；V4 76→81 |
| **M2.7** | **73/60/D**；**明文密码**；~¥3.55；**下沿有效**；CPI 负对照 |

### 3.6 常见失败模式（终态归纳）

| 模式 | 谁 | 影响 |
|------|-----|------|
| **ambient** | terra×2、K3、GLM、Grok、HY、Qwen、luna 低分枪… | −5 + B+；terra **可复现** |
| **F6 crash** | K2.7、Grok、HY… | −3 + Ship≤88 |
| **F6 backfill only** | luna、DeepSeek run2、GLM… | −2 |
| **F12 reason** | 几乎所有强模型 | −1 不进 S-* |
| **ESP 碎扣** | tof1 / wifi_ssid / mqtt REQUIRES / lwip | −1～−2 |
| **明文密码** | M2.7 | Ship 60 / D |
| **session spoof** | Grok run1 | Ship 65 / D |

### 3.7 渠道与未测

| 项 | 状态 |
|----|------|
| **Composer 2.5** | Grok Build **无模型可选**；历史曾误标 Cursor；**本轮无法补测** |
| **Grok Build OSS** | [xai-org/grok-build](https://github.com/xai-org/grok-build) 已公开 Rust 源码（Apache-2.0） |
| **Claude / Fable** | 操作者判断 **测不起**；信息增益有限（已有 sol 美系顶） |
| Qoder 偶发中断 | Kimi 改 WB、Qwen 完成；不并渠道 n |
| 默认 harness 多样性 | Codex / OpenCode / WB / qoder / grok-cli / kimi-sub |

---

## 4. 效率副榜（摘要，不进 Ability）

| 角色 | 模型 | Ability | $/枪 | min |
|------|------|--------:|-----:|----:|
| CPI 王 | DeepSeek gray | 96 | **0.12** | ~32 |
| 常态地板 | DeepSeek preview | 78 | **0.14** | — |
| **快且不贵** | **Grok** | **90**w | **~1.2–1.6**（n=2≈$2.8） | API≈6–7 |
| 按量中游 | **Doubao** | **90** | **~1.81**（¥13.04） | — |
| 列表中游 | **Qwen-3.8-Max-P** | **87** | **~2.95**（¥21.26；一折 **0.29**） | ~21 |
| 便宜近顶 | terra | 94 | 2.04 | ~13 |
| 晃 | luna | 90 | 1.93 | ~22 |
| 中上贵慢 | K3 | 92 | 6.13（5.63） | **48** |
| 顶端贵 | sol | 98 | 8.18 | ~25 |
| 负对照 | M2.7 | 73/D | ¥3.55 | — |

**标价链（操作者）：** luna ≈ terra×40% ≈ **sol×20%**；terra ≈ **sol×50%**。  
总费 luna≈terra 而时长更长 → high 档 **预算不同**。  
**Grok：** 本地会话 `costUsdTicks` 可还原美元；卖点是 **速度 + harness**，不是压 DeepSeek 的 CPI。  
**Grok Build 开源：** [github.com/xai-org/grok-build](https://github.com/xai-org/grok-build)（Apache-2.0；不接受外部贡献）。

---

## 5. 本轮未做 / 刻意不做

| 状态 | 事项 |
|------|------|
| **缺渠道** | Composer 2.5 |
| **成本放弃** | Claude 系 |
| **不主动补跑** | K3 n=2、DeepSeek 正式路由、Composer/Claude 均只在出现真实选型需求时再测 |
| **禁止** | 用 4.1b 重算 V4.0/4.1a 正式分 |
| **远期** | V5 / PlanExec 独立项目（文档已有，未并入本榜） |

---

## 6. 记忆锚点

| 锚 | 数字 |
|----|------|
| Gold | **100/A** |
| 主列顶端 | **sol 98** worst（best 99） |
| CPI 王 | DeepSeek **96** · **$0.12** |
| 5.6 梯度（worst） | sol 98 > terra 94 > luna 90 |
| ambient 可复现 | terra **94–94** |
| 方差警示 | luna **90–96**；DeepSeek **96–99** |
| K3 | **92** · **$6.13** · 48min |
| 下沿 | M2.7 **73/60/D** |
| V4.0 中游墙 | 常 81–82 → 4.1b 已拉开 |

---

## 7. 关键路径

| 用途 | 路径 |
|------|------|
| **本终稿** | `docs/v4.1/ROUND_SUMMARY_20260719.md` |
| 现行榜 | `evaluator/reports/v4.1b_scoreboard.md` |
| 效率副榜 | `evaluator/reports/v4.1_efficiency_board.md` |
| K3 费用 | `evaluator/reports/kimi_k3_cost_ledger.md` |
| 评审全集 | `evaluator/reviews/v4.1b_*.md` |
| V4.0 冻结 | `archives/v4_round_final_20260718/` |
| 候选/评审提示 | `CANDIDATE_PROMPT.md` · `REVIEWER_PROMPT.md` |

### 日常命令

```powershell
python evaluator\make_broken_project.py
# 模型只改 workspace\project2_task
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CH --harness H `
  --require-meta --include-espidf-build `
  --run-group-id GROUP --run-index N --thinking-level LEVEL
```

---

## 8. 给下一会话

1. 读 **本文件** + `v4.1b_scoreboard.md`  
2. 规则锁定 **V4.1b**；不重算历史正式分  
3. 本轮锚点 **已闭环**；新模型再开新行，不必重跑全家  
4. 无主动补洞或全家重跑计划；新样本必须先有真实选型需求  

## 9. 收口后的使用决策

- Ability >=95 且无严重 Ship blocker，已足以覆盖当前日常开发。
- Ability >=90 的模型可承担实现工作，最终是否可交付取决于 Ship 与失败 family。
- 本轮主要证明 V4.1b 的评分去级联和多跑观测有效，不证明所有模型跨版本升级。
- V4.1b 不再继续迭代；V5 保持远期，不以区分 96/98/99 为近期需求。
- `worst-of-n` 是保守观测下界；n=1 与 n=2 排名不能解释成同等稳定性证据。

---

*终稿写于 2026-07-19。V4.1b 锚点轮次正式收口。*
