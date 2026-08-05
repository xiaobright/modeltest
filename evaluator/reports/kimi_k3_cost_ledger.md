# Kimi K3 费用台账（Project2 V4.1b，非正式 Ability）

**模型：** Kimi-K3 · channel `kimi-sub` · harness `kimi` · thinking **max**  
**result_id：** `20260719_124011`  
**状态：** **已封口**  
**更新：** 2026-07-19

---

## 计价口径

| 概念 | 含义 |
|------|------|
| **显示美元价** | **真实账单**（累加 = 实付） |
| **订阅 4× / 双倍额度** | 只动 **限额消耗**，不改美元显示价 |
| **缓存** | miss/hit 改变单次调用美元价 |

---

## 分项与总价

| # | 阶段 | 美元 | 备注 |
|---|------|-----:|------|
| 1 | 旧订阅第一段（quota 坠机） | 3.80 | 未完成 |
| 2 | 换号续跑 · 首调 **cache miss** | 0.55 | 换号丢缓存 |
| 2′ | 对照：若 cache **命中** | *(0.055)* | ≈ miss 的 1/10；不计实付 |
| 3 | 续跑至完成（含 2 之后全部） | 1.78 | 由总账反推：6.13 − 3.80 − 0.55 |
| **Σ 实付** | **整枪真实总价** | **6.13** | 操作者账单 |
| **缓存税** | miss − hit | **0.495 ≈ 0.50** | 0.55 − 0.055 |
| **Σ′ 去换号缓存税** | 假设首调命中 | **≈ 5.63** | 6.13 − 0.50（或 6.13 − 0.55 + 0.055） |

**墙钟：** 合计约 **48 min**（含坠机/换号/续跑整段 agent 时间）。

```text
total_usd_actual          = 6.13
total_usd_cache_adjusted  = 5.63   # exclude account-switch cache miss tax
wall_min                  = 48
cache_miss_first_call     = 0.55   # hit counterfactual 0.055
quota_multiplier          = limits only, not USD
```

---

## CPI 对照（同基准完整/近完整枪）

| 模型 | Ability 主列 | 费用 | 墙钟 | 相对 K3 |
|------|-------------:|-----:|-----:|---------|
| DeepSeek-V4-Pro | **96** worst | ~$0.12 | ~32 min | 更强主列 · **贵约 1/50** |
| GPT-5.6-terra high | **94** | ~$2.04 | ~13 min | 略高 Ability · 更便宜更快 |
| GPT-5.6-luna high | **90** worst | ~$1.93 | ~22 min | 更低 Ability · 更便宜 |
| GPT-5.6-sol high | **98** | ~$8.18 | ~25 min | 更高 Ability · 更贵；K3 实付 **低于 sol** |
| Kimi-K2.7-Code WB | **94**/88 | — | — | Ability 更高；K3 **无 M-crash** 但 **有 ambient** |
| **Kimi-K3** | **92** | **$6.13**（调 $5.63） | **48 min** | 本枪 |

**结论（效率叙事）：**  
- 实付 **$6.13** 未超过 sol high $8.18，但 **远高于** terra/luna/DeepSeek。  
- 去换号缓存税 **~$5.63** 仍是中上价位；**48 min** 偏慢。  
- 相对 DeepSeek：**钱 ×50、时更长、分还低** → CPI 不占优。  
- 限额层 4×/双倍是另一套账，**不进美元 Σ**。
