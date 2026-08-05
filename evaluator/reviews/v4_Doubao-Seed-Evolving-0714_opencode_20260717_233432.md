# V4 Review: Doubao-Seed-Evolving-0714 @ OpenCode

## Meta
- result_id: `20260717_233432`
- harness: OpenCode
- tool_interference: **no**

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **37 / 45**（3 fail + 5 error）
  - `S-ambient`
  - `M-crash`：F6 全 5 项 error
  - `V4-F12-04` reason-only
- esp static: **9 / 9**（全过）
- esp build: **real_pass**
- draft Ability / Ship / Class: **82.0 / 82.0 / B**

## Family

| Family | Final | 缺口 |
|--------|------:|------|
| F1 | 8 | |
| F2 | 12 | |
| F3 | 11 | ambient −5 |
| F4 | 4 | |
| F5 | 10 | context −2（ambient 连带） |
| F6 | 0 | **全 error，migration crash** |
| F7 | 8 | |
| F8 | 8 | static 满分 |
| F9 | 6 | real_pass |
| F10 | 8 | |
| F11 | 4 | PR 充实 |
| F12 | 3 | reason 精度 |

**Ability：** 8+12+11+4+10+0+8+8+6+8+4+3 = **82**

## 与前代 Doubao-Seed-2.0-Code 对比

| 维度 | 2.0-Code（81/B） | Evolving-0714（82/B） | 变化 |
|:---|---:|:---:|:----:|
| F8 ESP static | 7/8 | **8/8** | ✅ +1 |
| F6 migration | 8/10 | 0/10 | ❌ 随机波动 |
| no-actor | ❌ 放行 | ❌ 放行 | 一致 |
| voice | ❌ 未改 | ❌ 未改 | 一致 |
| **Ability** | **81** | **82** | **+1** |

基本上和前代在同一水平线，F8 好了 1 分但 F6 没跑通。属于"每周更新迭代"但没有显著提升能力项覆盖面的样本。esp static 全过值得肯定。

## Final
- **Ability: 82 / 100**
- **Ship: 82 / 100**
- **Class: B**
- **Blockers:** `S-ambient`, `M-crash`, `M-fidelity`
- **Semantic-only:** `V4-F12-04`
