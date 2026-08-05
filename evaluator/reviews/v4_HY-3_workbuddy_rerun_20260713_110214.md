# V4 Review: HY-3 @ WorkBuddy（重跑）

## Meta
- result_id: `20260713_110214`
- harness: WorkBuddy
- tool_interference: **no**
- 操作者备注: 首跑 `20260712_113133`（92/B+）→ 重跑验证

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **37 / 45**（3 fail + 5 error）
  - `S-ambient`：环境 session 未关
  - **`M-crash`**：F6 全 5 项 error——旧表 migration crash（首跑无此问题）
  - `V4-F12-04` reason-only
- esp static: **9 / 9**（全过）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **82.0 / 82.0 / B**

## Family breakdown

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 11 | **11** | 仅 F3e ambient −5 |
| F4 | 4 | **4** | voice 正确 |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 0 | **0** | **全 5 项 error：旧表 migration crash（M-crash）** |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 8 | **8** | static 满分 |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+11+4+10+0+8+8+6+8+4+3 = **82**

## Final scores
- **Ability:** **82 / 100**
- **Ship:** **82 / 100**
- **Class:** **B**
- **Blockers:** `S-ambient`, `M-crash`, `M-fidelity`

## 与首跑对比——方差分析

| 项目 | 首跑（07-12, 92/B+） | 重跑（07-13, 82/B） | 变化 |
|:---|---:|:---:|:----|
| F6 migration | **10/10** ✅ | **0/10** ❌ | **−10** |
| F3 ambient | 11/16 | 11/16 | 一致 |
| ESP static | 8/8 | 8/8 | 一致 |
| hidden | 42/45 | 37/45 | 一致（除 F6 外） |
| **Ability** | **92** | **82** | **−10** |

**你的怀疑是对的，HY-3 @ WorkBuddy 确实不稳定。** 两次跑的 F6 migration 结果完全不同——首跑迁移顺序正确（先 migrate 再 INDEX），重跑出现了经典的 INDEX 先于 migrate 的 crash。这是同一个模型对同一个问题的实现方案不稳定的表现。

相比之下，Grok-4.5 两次跑完全一致（82/82），比 HY-3 稳定得多。

## Recommendation
- **revise**（补迁移顺序 + ambient）
- 注意：该模型在该渠道上方差可达 **±10 分**，单次分数仅供参考。
