# V4 Review: GPT-5.4 @ Codex (xhigh)

## Meta
- result_id: `20260712_211059`
- harness: Codex (xhigh thinking)
- tool_interference: **no**
- duration: **~15 min**（花费待确认）
- 操作者备注: V2 历史分 88/hidden 32/34/static 6/8；验证"降智"

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **42 / 45**（3 fail）
  - `S-ambient`：环境 session 未关（F3e −5）
  - F5 care context 连带
  - `V4-F12-04` reason-only
  - **无** S-no-actor / S-plaintext-admin / M-crash
- esp static: **8 / 9**（1 failed：`lwip` 缺 CMake REQUIRES）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **91.0 / 91.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 11 | **11** | 仅 F3e ambient −5；**no_actor 正确** |
| F4 | 4 | **4** | voice 正确 |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 10 | **10** | 迁移满分 |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | `lwip` 缺 REQUIRES（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+11+4+10+10+8+7+6+8+4+3 = **91**

## Final scores
- **Ability:** **91 / 100**
- **Ship:** **91 / 100**
- **Class:** **B+**
- **Blockers (behavior only):** `S-ambient`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5**
- security: **8.3**
- migration: **10.0**
- esp_deploy: **9.3**
- process_truth: **10.0**

## Findings

### 做得好的
1. **Auth/voice/no_actor/migration/sleep 全部正确**。
2. **42/45 hidden，零安全泄漏**。
3. **仅 ambient + lwip 两个小缺口**。

### 主要缺口
1. **`S-ambient`（F3e −5）**。
2. **`E-contract`（F8-03）**：`lwip` 缺 REQUIRES。
3. **F12-04 reason**。

### V2→V4 对照 & GPT 系降智分析

| 模型 | V2 历史 | V4 实测 | 耗时 | 花费 | 结论 |
|:---|:------:|:------:|:---:|:---:|:----|
| GPT-5.6-sol | — | **99** | 24 min | $7.25 | 5.6 系列旗舰 |
| GPT-5.5 | 96 | **92** | 23 min | **$9.06** | 分数略降，花费反升→**磨洋工证据** |
| **GPT-5.4** | **88** | **91** | **15 min** | **?** | **分数反升，耗时更短** |

有意思的是：
- **5.5 确实有降智迹象**：V2 亚军（96），V4 拿 92，且花了全场最贵的 $9.06 和 23 分钟——"磨洋工"模式明显。
- **5.4 反而没降**：V2 88 → V4 91，还升了 3 分，而且只用了 15 分钟，比 5.5 快了 8 分钟。说明 5.4 在这个任务上更高效。

两个模型在同一问题上表现不同，可能说明"降智"不是全局性退化，而是特定能力维度的方差变大——5.5 在某些细节上反复纠结（ambient 没关掉 + 多花 token），5.4 反而直来直去完成了。

### 与 GPT-5.5 对比

| 项目 | 5.5（92） | 5.4（91） |
|:---|---:|:---:|
| F8 static | ✅ 8/8 | ❌ 7/8（lwip） |
| 其余 family | 完全相同 | 完全相同 |
| 耗时 | 23 min | **15 min** |
| 花费 | $9.06 | ? |

两模型能力几乎一致，仅差在一个 ESP REQUIRES 细节上。

## Recommendation
- **revise**（补 ambient + lwip）
- 一句话：GPT-5.4 @ Codex xhigh 是 **「91 分 B+，与 5.5 仅差一个 lwip 细节，V2→V4 未降智反而略升」** 的样本。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] V2→V4 退化验证
- [x] GPT 系降智对比
