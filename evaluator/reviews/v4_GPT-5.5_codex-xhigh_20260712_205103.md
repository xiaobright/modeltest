# V4 Review: GPT-5.5 @ Codex (xhigh)

## Meta
- result_id: `20260712_205103`
- harness: Codex (xhigh thinking)
- tool_interference: **no**
- duration: **~23 min / $9.06**
- 操作者备注: V2 历史分 96/hidden 33/34/static 8/8；本次 V4 验证是否"降智"

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **42 / 45**（3 fail）
  - `S-ambient`：环境 session 未关（F3e −5）
  - F5 care context 连带
  - `V4-F12-04` reason-only
  - **无** S-no-actor / S-plaintext-admin / M-crash / E-contract
- esp static: **9 / 9**（全过）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **92.0 / 92.0 / B+**

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
| F8 | 8 | **8** | **static 满分** |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+11+4+10+10+8+8+6+8+4+3 = **92**

## Final scores
- **Ability:** **92 / 100**
- **Ship:** **92 / 100**
- **Class:** **B+**
- **Blockers (behavior only):** `S-ambient`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5**
- security: **8.3** — auth 满分，ambient 未关
- migration: **10.0**
- esp_deploy: **10.0** — static 满分 + real build
- process_truth: **10.0**

## Findings

### 做得好的
1. **Auth 满分 + Voice 正确 + no_actor 正确**：安全边界扎实。
2. **F6=10 迁移满分** + **F8=8 static 满分**。
3. **无信任硬伤、无 E-contract、无 M-crash**：代码质量可靠。
4. **唯一缺口只有 ambient**——与 HY-3@WorkBuddy（同为 92/B+）一个水平。

### 主要缺口
1. **`S-ambient`（F3e −5）**：同大多数模型共性问题。
2. **F12-04 reason 精度**。

### V2 → V4 对照：降智了吗？

| 维度 | V2 历史 | V4 实测 | 结论 |
|:---|---:|:---:|:----|
| hidden | 33/34 | **42/45** | 题量不同（34→45），通过率 ~97% vs ~93% |
| ESP static | 8/8 | **8/8** | 满分不变 |
| auth/voice/migration | — | 全过 | 无退化 |
| ambient | 未单独计 | **S-ambient** | V4 新增精确检测，非退化 |
| **Ability** | **96**（V2标尺） | **92**（V4标尺） | 标尺不同，实际能力无实质下降 |

**结论：没有观测到明显的"降智"。** 92 分在当前 V4 榜上排第 6，与 HY-3@WorkBuddy 并列。唯一缺口 ambient 是 V4 新增的检测维度，几乎所有模型都栽在这条上。如果只看 V2 也覆盖的能力项（auth/migration/ESP/sleep/voice），GPT-5.5 全部满分或接近满分。

### 与 5.6 系列对比

| 模型 | Ability | F3 ambient | F8 static | F6 migration |
|:---|:------:|:---------:|:--------:|:----------:|
| sol xhigh | **99** | ✅ | ✅ 8/8 | ✅ 10/10 |
| luna xhigh | **99** | ✅ | ✅ 8/8 | ✅ 10/10 |
| terra high | **97** | ✅ | ❌ 6/8 | ✅ 10/10 |
| **GPT-5.5 xhigh** | **92** | ❌ | ✅ 8/8 | ✅ 10/10 |
| sol medium | 91 | ❌ | ❌ 7/8 | ✅ 10/10 |

GPT-5.5 与 5.6 系列的真实差距集中在 **ambient 处理**（−5）上。5.6 的 sol/luna 在 xhigh 下能关掉 ambient，5.5 在同样强度下没关掉。除此之外，auth/migration/ESP static/voice 全部同一水平。

## Recommendation
- **revise**（仅需补 ambient）
- 一句话：GPT-5.5 @ Codex xhigh 是 **「92 分 B+，仅 ambient 缺口，无信任无迁移无 ESP 问题——V2 到 V4 能力未退化」** 的有力样本。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] V2→V4 退化验证
- [x] 与 5.6 系列对比
