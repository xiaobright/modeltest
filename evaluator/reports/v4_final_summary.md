# Project2 V4 评测总结报告

> **已由更完整的正式分析替代：** `evaluator/reports/v4_v2_comparison_final.md`。
> 本文件保留 2026-07-12 首版汇总，内部“降智”“Pareto 最优”等措辞不再作为最终结论。

**日期：** 2026-07-12  
**测试规模：** 18 个独立模型身份，25 次运行  
**测试轮次：** 11 轮重置  

---

## 一、总榜（Ability 降序）

| 名次 | 模型 | 渠道/强度 | Ability | Ship | Class | 主缺口 |
|:--:|:---|:---|:------:|:----:|:-----:|:-------|
| 1 | GPT-5.6-sol | Codex xhigh | **99** | 99 | A | 仅 F12 reason |
| 1 | GPT-5.6-luna | Codex xhigh | **99** | 99 | A | 仅 F12 reason |
| 3 | GPT-5.6-sol | Codex high | **98** | 98 | A | topic 标记 |
| 3 | GPT-5.6-luna | Codex high | **98** | 98 | A | topic 标记 |
| 5 | GPT-5.6-terra | Codex high | **97** | 97 | A | mqtt REQUIRES + topic |
| 6 | GPT-5.6-terra | Codex xhigh | **95** | 95 | A | voice 未改 |
| 7 | Gemini-3.5-Flash | Antigravity | **93** | 93 | B+ | no-actor 放行 |
| 8 | GPT-5.5 | Codex xhigh | **92** | 92 | B+ | ambient |
| 8 | HY-3 | WorkBuddy | **92** | 92 | B+ | ambient |
| 8 | Composer-2.5 | grok-cli | **92** | 92 | B+ | ambient |
| 11 | GPT-5.4 | Codex xhigh | **91** | 91 | B+ | ambient + lwip |
| 11 | GPT-5.6-sol | Codex medium | **91** | 91 | B+ | ambient + mqtt |
| 13 | Kimi-K2.7-Code | Qoder | **90** | 90 | B+ | ambient + ts 回填 |
| 13 | Gemini-3.1-Pro | Antigravity | **90** | **60** | **D** | 明文密码 |
| 15 | HY-3 | OpenCode | **86.5** | 86.5 | B+ | ambient + PR + ESP |
| 16 | Minimax-M3 | WorkBuddy | **84** | 84 | B | ambient + regression |
| 17 | Grok-4.5 | grok-cli | **82** | 82 | B | ambient + migration crash |
| 17 | DeepSeek-V4-Pro | OpenCode | **82** | 82 | B | ambient + migration + voice |
| 17 | GLM-5.2 | OpenCode | **82** | 82 | B | ambient + migration crash |
| 17 | GLM-5.2 | WorkBuddy | **81** | 81 | B | ambient + migration crash |
| 17 | GLM-5.2 | Qoder | **81** | 81 | B | ambient + migration crash |
| 17 | LongCat-2.0 | OpenCode | **81** | 81 | B | no-actor 放行 + voice |
| 17 | Doubao-Seed-2.0-Code | OpenCode | **81** | 81 | B | no-actor 放行 + voice |
| 24 | Qwen-3.7-Max | Qoder | **76** | 76 | B | ambient + migration crash + voice |
| 25 | Minimax-M2.7 | Qoder | **61** | **60** | **D** | 明文密码 + cookie 绕过 |

---

## 二、关于"降智"的量化结论

通过 GPT-5.4 / 5.5 / 5.6 同条件（xhigh）对比：

| 模型 | V2 历史 | V4 实测 | 耗时 | 花费 | CPI | 结论 |
|:---|:------:|:------:|:---:|:---:|:---:|:----|
| GPT-5.6-sol | — | **99** | 24 min | $7.25 | 13.7 | 当前旗舰 |
| GPT-5.6-luna | — | **99** | 24 min | $2.11 | 46.9 | 同分半价 |
| GPT-5.5 | 96 | **92** | 23 min | **$9.06** | 10.2 | ⚠️ **降智：分数降、花费反升** |
| GPT-5.4 | 88 | **91** | 15 min | $2.50 | 36.4 | ✅ **未降智：分数反升、更高效** |

**结论：GPT-5.5 确实有降智迹象（磨洋工：花最多钱拿中档分），但这不是 GPT 全系列的全局退化。** 5.4 在 V4 上反而比 V2 表现更好。降智更可能是 5.5 特定版本的效率问题。

---

## 三、思考强度 vs 性价比（GPT-5.6-sol 梯度）

| 强度 | 耗时 | 花费 | Ability | 相比上一档 | CPI |
|:---:|:---:|:---:|:------:|:---------|:---:|
| medium | 8 min | $2.32 | **91** | — | 39.2 |
| high | 13 min | $3.49 | **98** | +$1.17 +5 min → **+7 分** ✅ | 28.1 |
| xhigh | 24 min | $7.25 | **99** | +$3.76 +11 min → **+1 分** ❌ | 13.7 |

**High 是 Pareto 最优档位**——多花 5 分钟和 $1.17 就能从 91 冲到 98，再往上追最后 1 分要花 3 倍钱。

---

## 四、终极推荐

| 用途 | 建议 | 花费 | Ability | 理由 |
|:---|:----|:---:|:------:|:-----|
| **日常首选 🥇** | **luna high** | **$1.29** | **98** | CPI 76.0，全场最能打 |
| 性价比备选 🥈 | terra high | $2.01 | 97 | 与 luna 差距极小 |
| 要满分 🥉 | luna xhigh | $2.11 | 99 | 最便宜的满分方案 |
| 预算充足 | sol high | $3.49 | 98 | 速度最快（13 min） |
| 钱多烧的 | sol xhigh | $7.25 | 99 | 追最后 1 分 |

**一句话：日常无脑选 luna high，18 分钟 $1.29 拿 98 分。**

---

## 五、渠道差异总结

| 渠道 | 代表模型 | 特点 |
|:----|:--------|:-----|
| **Codex** | GPT-5.6 系列 | 最强，有环境记忆，ESL 表现稳定 |
| **WorkBuddy** | HY-3, GLM-5.2 | 有 memory 机制辅助，第二次跑通常更好 |
| **OpenCode** | HY-3, LongCat, Doubao | 无记忆，模型全靠自身，方差较大 |
| **Qoder** | Kimi K2.7, GLM-5.2, Qwen | 混合表现，ESP 编译常被 PATH 干扰 |
| **Antigravity** | Gemini 系列 | Gemini 3.5 Flash 表现意外好，Pro 有硬伤 |

---

## 六、常见失败模式排名

| 模式 | 受影响模型数 | 典例 |
|:----|:----------:|:----|
| S-ambient（环境 session 未关） | **15/18** | 几乎所有模型 |
| F12 reason 精度不足 | **15/18** | 几乎所有模型 |
| E-contract（ESP 依赖缺失） | **10/18** | lwip/mqtt/esp_event 漏加 |
| M-crash/M-fidelity（迁移问题） | **6/18** | GLM-5.2×3, Grok, Qwen |
| S-no-actor（无 actor 放行） | **5/18** | LongCat, Doubao, Gemini×2, Qwen |
| F4=0（voice 未改） | **5/18** | terra xhigh, LongCat, Doubao, Qwen |
| S-plaintext-admin（明文密码） | **2/18** | M2.7, Gemini Pro → Class D |

---

## 七、文件索引

| 文件 | 内容 |
|:----|:-----|
| `evaluator/reports/v4_scoreboard.md` | 完整成绩榜 |
| `evaluator/reports/gpt5.6_cost_analysis.md` | GPT 系列性价比分析 |
| `evaluator/reviews/v4_*.md` | 单模型评审（18 份） |
