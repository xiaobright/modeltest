# V4 Review: Grok-4.5 @ grok-cli（重跑）

## Meta
- result_id: `20260713_100918`
- harness: grok-cli
- tool_interference: **no**
- 操作者备注: 首次 `20260711_210538`（82/B）→ 重跑验证稳定性

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **37 / 45**（3 fail + 5 error）
  - `S-ambient`：环境 session 未关
  - **`M-crash`**：F6 全 5 项 error——旧表 migration crash
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
| F6 | 0 | **0** | 全 5 项 error：旧表 migration crash（M-crash） |
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
- **Semantic-only:** `V4-F12-04`

## 与首跑对比

| 项目 | 首跑（07-11） | 重跑（07-13） | 结论 |
|:---|---:|:---:|:----|
| Ability | **82** | **82** | ✅ 完全一致 |
| hidden | 37/45 | **37/45** | ✅ 完全一致 |
| ESP static | 9/9 | **9/9** | ✅ 完全一致 |
| F6 migration | 0/10 | **0/10** | ✅ 完全一致（M-crash 稳定复现） |
| F3 ambient | −5 | −5 | ✅ 一致 |

**结论：Grok-4.5 的 V4 表现非常稳定**，两次跑分完全一致。82/B 是它的真实水平——ambient 没关、migration 全 crash，但 ESP static 满分、auth 和 voice 正确。不是偶然波动。

## Recommendation
- **revise**（补迁移顺序 + ambient）
