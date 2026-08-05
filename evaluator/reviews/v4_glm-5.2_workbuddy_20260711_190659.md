# V4 Review: GLM-5.2 @ WorkBuddy

## Meta
- result_id: `20260711_190659`
- harness: WorkBuddy
- tool_interference: **yes**（见下；**不改变** Ability 代码分，但解释 ESP 耗时与 F9 证据路径）
- evidence_source: **`v4_rerun`**
- 操作者备注: 候选侧安全沙箱曾拦截 bulk delete / Bash↔PS 交叉调用；开启完全权限后才稳定完成 ESP 编译。代码本体与 harness 摩擦应分开叙事。

### tool_interference 摘要（WorkBuddy 自述 + 终端旁证）
1. **safe-delete 钩子**：`Remove-Item` / `idf.py fullclean` 删 build 数千文件触发 `[SAFE_DELETE_BULK_CONFIRM_REQUIRED]`，中断编译；`set-target→fullclean` 路径反复踩坑。
2. **idf.py → cmake 子进程 PATH**：激活脚本 PATH 有 Ninja，但 `idf.py` 经 `subprocess` 调 cmake 时找不到 Ninja；最终绕过 `idf.py`，用 `cmake -G Ninja` + `cmake --build`。
3. **Bash↔PowerShell 交叉调用禁令**：官方 `run_espidf_build.py`（内部 spawn PS）在 sandbox 下难跑通；需关安全限制 / 拆工具链。
4. **代码侧实际编译错误仅两轮**（`ESP_EVENT_ANY_ID` cast、`p` 作用域、`esp_netif.h`、`device_config` 缺 FreeRTOS 头）— 与环境搏斗时间远大于修代码时间。

→ 效率差主要是 **channel/harness 摩擦**，不是「没放编译脚本」。脚本在 `workspace/tools/run_espidf_build.py`。

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **37 / 45**（failed 3 + migration **5× error**）
  - `S-ambient`：`test_sensitive_target_context_requires_explicit_session_behavior`（`allowed=True`）
  - care context 集成连带失败
  - F12-04 reason-only：`not_authenticated` ≠ `not_authorized_for_target`
  - **F6 全灭**：`sqlite3.OperationalError: no such column: ts`（init 阶段，**M-crash**）
- esp static: **8 / 9**；失败 `test_mqtt_dependencies_added` → **`lwip` missing from CMake REQUIRES**（`E-contract`）
- esp build: 机器 `skipped_env`；**人工 real_pass**：PR 详述 cmake 直编成功 + bin 路径/尺寸；操作者确认完全权限下可编过
- draft Ability / Ship / Class（机器）: **74.5 / 74.5 / B**（F9=3, F11=0.5 低估）

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 契约过 |
| F2 | 12 | **12** | auth 8/8 |
| F3 | 11 | **11** | 仅 F3e −5；其余 behavior 过 |
| F4 | 4 | **4** | voice bridge 过 |
| F5 | 10 | **10** | CRUD 过；context −2（ambient 连带） |
| F6 | 0 | **0** | 旧库 init 即炸：`CREATE INDEX ... (ts)` 在 `_migrate_care_events` **之前**执行，旧表无 `ts` → OperationalError。迁移函数本身写了但**跑不到** |
| F7 | 8 | **8** | sleep 含 mixed 全过 |
| F8 | 7 | **7** | 缺 `lwip` REQUIRES（−1）；其余 static 过 |
| F9 | 3 | **6** | 真编成功有产物与诚实路径说明（绕过 idf.py）；**非** overclaim |
| F10 | 8 | **8** | 回归过 |
| F11 | 0.5 | **4** | PR 极充实；机器 placeholder 误判（模板引导语） |
| F12 | 3 | **3** | 仅 no_actor reason |

**Ability：** 8+12+11+4+10+0+8+7+6+8+4+3 = **81**

## Final scores
- **Ability:** **81 / 100**
- **Ship:** **81 / 100**（`M-crash` 门槛 ≤88，未触顶；无信任 hard cap）
- **Class:** **B**（Ability&lt;85 且存在 `S-ambient` + `M-crash` + `E-contract`）
- **Blockers (behavior only):** `S-ambient`, `M-crash`, `M-fidelity`（F6 连带）, `E-contract`
- **Semantic-only:** `V4-F12-04` no_actor reason

## Dimensions（0–10）
- final_code: **8.5**
- security: **7.0**（ambient 未关）
- migration: **0**
- esp_deploy: **8.5**（static 差一点 + 真编过；harness 折腾另计）
- process_truth: **9.5**（PR 诚实写了 idf/Ninja 绕过）
- efficiency: **低（工具链）** — 与代码能力解耦；建议渠道备注，不进 Ability

## Findings

### 做得好的
1. **Admin / sleep / voice / 回归** 完整，public+probe 干净。
2. **ESP 模块化**（protocol / device_config / mqtt_payload / network_backhaul）完整，最终能出 bin。
3. **PR 质量高**：初诊、根因、绕过编译路径、bin 尺寸、风险清单清楚；未谎称 `idf.py` 一键成功。
4. **no_actor 行为已 deny**，仅 reason 枚举差一分。
5. 在极差 harness 摩擦下仍交付可评测固件与网关主线。

### 主要缺口
1. **`M-crash`（硬伤）**：`db.py` 在旧 `care_events` 上先建 `INDEX (…, ts)`，迁移函数在后 → 旧库启动即 `no such column: ts`。F6=0。
2. **`S-ambient`**：`build_chat_context_v3` 仍 `get_current_session()` fallback（与 Composer 同款）。
3. **F8 `lwip`**：CMake `REQUIRES` 有 wifi/netif/event/mqtt/mbedtls，缺 `lwip` 静态项。
4. **care context** 随 ambient 挂（−2）。
5. **效率/体验**：时间主要耗在 WorkBuddy 安全钩子与 PATH，不是「不会修代码」——但 **Ability 只量交付物**。

### PR/报告是否诚实
**是。** 明确写了 idf.py/Ninja 环境问题与 cmake 直编路径；未把 harness 失败甩锅成「代码已满分」。与 terminal 多次编译尝试一致。

## Recommendation
- **revise**
  - 必改：迁移顺序（先 migrate 再 index，或 index 用条件创建）
  - 必改：关掉 ambient session fallback
  - 建议：CMake 补 `lwip`
- 一句话：GLM-5.2@WorkBuddy 是 **「主线不弱、迁移踩雷、隐私 ambient 未破、ESP 被 harness 拖累」** 的 B 档样本；相对同模型 Opencode/API 历史高分，本 channel 迁移失败把 Ability 从 ~88–95 叙事拉到 **81**。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格泄漏
- [x] 未用 82 墙压 Ship（Ship=Ability=81）
- [x] channel/harness 与 tool_interference 写明


