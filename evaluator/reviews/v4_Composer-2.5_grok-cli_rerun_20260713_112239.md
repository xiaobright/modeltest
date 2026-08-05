# V4 Review: Composer-2.5 @ grok-cli（重跑）

## Meta
- result_id: `20260713_112239`
- harness: grok-cli
- tool_interference: **no**
- 操作者备注: 首跑 `20260711_182425`（92/B+）→ 重跑验证

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **37 / 45**（3 fail + 5 error）
  - `S-ambient`
  - **`M-crash`**：F6 全 5 项 error
  - `V4-F12-04` reason-only
- esp static: **9 / 9**
- esp build: **real_pass**
- draft Ability / Ship / Class: **82.0 / 82.0 / B**

## 重跑对比

| 项目 | 首跑（07-11, 92/B+） | 重跑（07-13, 82/B） | 变化 |
|:---|---:|:---:|:----:|
| F6 migration | **10/10** ✅ | **0/10** ❌ | **−10** |
| 其余 family | 全一致 | 全一致 | 0 |
| **Ability** | **92** | **82** | **−10** |

## 三模型重跑汇总

| 模型 | 首跑 | 重跑 | 方差 | F6 首跑 | F6 重跑 |
|:---|:---:|:---:|:----:|:-------:|:-------:|
| Grok-4.5 | **82** | **82** | ±0 | 0/10 | 0/10 |
| HY-3 @ WorkBuddy | **92** | **82** | **±10** | 10/10 | 0/10 |
| Composer-2.5 | **92** | **82** | **±10** | 10/10 | 0/10 |

**规律很明显了：首跑 92 的俩（HY-3、Composer）重跑都掉到 82，首跑 82 的 Grok 则稳在 82。** 区别全在 F6 迁移——92 分那次 migration 顺序碰巧写对了，重跑时回到了和其他模型一样的 crash。F6=10 更像是随机事件而非模型能力，80% 的模型在这个问题上都是 F6=0。

## 结论
- **Composer-2.5 的真实水平 ~82/B**，92 是超常发挥
- 目前唯一能稳定跑通 F6 的只有 GPT-5.6 系列
