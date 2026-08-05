# V4 Review: GLM-5.2 @ Qoder

## Meta
- result_id: `20260711_204201`
- harness: Qoder / QoderWork
- tool_interference: **yes** — ESP-IDF `idf.py` 拒跑：`MSys/Mingw is no longer supported`  
  根因：Bash 工具实为 Git Bash，PATH 混入 MinGW（`Git\mingw64`、`Espressif\tools\git\mingw64` 等）；`run_espidf_build.py` → PowerShell 继承污染 PATH + `MSYSTEM`。  
  候选用临时 `run_espidf_temp.ps1`（清 MSYSTEM + 过滤 PATH 中 msys/mingw/usr）绕过并成功出 bin。**不扣 Ability**；F9 按产物满分。
- evidence_source: **`v4_rerun`**
- 操作者备注: 本轮最后一样本（同模型 WorkBuddy 渠道对照）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **36 / 45**（fail 4 + err 5）
  - `S-ambient` + care context 连带
  - F12 reason-only
  - **F6 全 error**：`no such column: ts`（INDEX 在 migrate 前）
  - process：`claims device_config` 但无对应改动文件 → `P-report`
- esp static: **9 / 9**
- esp build: 机器 `skipped_env`；**人工 real_pass**（`stdpro.bin` 984160 bytes，mtime 2026-07-11 20:33，与 PR 一致）
- draft Ability / Ship / Class（机器）: **75.5 / 75.5 / B**（F9=3、F11=0.5 低估）

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | F1-05 0 分项失败记 `P-report`，主分项仍过 |
| F2 | 12 | **12** | 哈希/token_hash 鉴权全过（明显强于 M2.7） |
| F3 | 11 | **11** | 仅 F3e −5；no_actor 行为 deny |
| F4 | 4 | **4** | `fetch_current_session_id` 过 |
| F5 | 10 | **10** | context −2（ambient） |
| F6 | 0 | **0** | 旧表：`CREATE INDEX (... ts)` 在 `_migrate_*` 之前 → M-crash（与同模型 WB 同源） |
| F7 | 8 | **8** | `beds[0]` 已修，含 mixed |
| F8 | 8 | **8** | static 满分 + mqtt yml + lwip |
| F9 | 3 | **6** | 真编成功；PATH 摩擦记 tool_interference |
| F10 | 8 | **8** | |
| F11 | 0.5 | **3** | PR 充实且诚实写 MSys 绕过；**−1**：声称 `device_config` 辅助文件但 diff 仅有 `network_backhaul` |
| F12 | 3 | **3** | no_actor reason |

**Ability：** 8+12+11+4+10+0+8+8+6+8+3+3 = **81**

## Final scores
- **Ability:** **81 / 100**
- **Ship:** **81 / 100**（`M-crash` ≤88 未触顶；`P-report` 未到信任 hard-cap 72 级）
- **Class:** **B**
- **Blockers (behavior only):** `S-ambient`, `M-crash`, `M-fidelity`, `P-report`
- **Semantic-only:** `V4-F12-04`

## Dimensions（0–10）
- final_code: **8.0**
- security: **7.0**（鉴权满分；ambient 未关）
- migration: **0**
- esp_deploy: **10**（static+bin；harness 折腾另计）
- process_truth: **7.5**（MSys 诚实；device_config 文件名虚报）
- efficiency: **低（工具链）** — PATH 污染，与代码能力解耦

## Findings

### 做得好的
1. **Auth 满分** — 明文密码/任意 session 类 trust 坑收干净（对照 M2.7@Qoder D 档）。
2. **Sleep + Voice + ESP static/build** 全过；模块化（network_backhaul）可用。
3. public/probe 干净；PR 对 **Qoder Git Bash → MinGW PATH → idf.py 拒跑** 诊断完整可复现。
4. 同模型跨 channel：与 WorkBuddy 同 Ability 带，本 channel 多拿 F4/F7/F8 干净分。

### 主要缺口
1. **`M-crash`**：`db.py` INDEX(ts) 先于 migrate — 与 GLM-5.2@WorkBuddy **同一类 bug**。
2. **`S-ambient`**：`get_current_session()` fallback 仍在。
3. **`P-report`**：PR 提到 `device_config`，实际未提交对应 helper 文件（用 `network_backhaul` + main 内结构）。
4. F12 reason 精度。

### PR/报告是否诚实
**大体是。** 编译成功、MSys 绕过路径与 bin 吻合；device_config 命名与仓库不一致记轻量 P-report，非假 build。

## Recommendation
- **revise**（可合并前必修迁移顺序 + ambient；更正 PR 文件名）
- 一句话：GLM-5.2@Qoder = **强鉴权/ESP、迁移与 ambient 双雷** 的 B 档；Ability **81** 与同模型 WorkBuddy **并列**，channel 摩擦不同但代码 cap 同在 M-crash+ambient。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] channel=Qoder + tool_interference 写明


