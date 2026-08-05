# V4 Review: Gemini-3.1-Pro @ Antigravity

## Meta
- result_id: `20260712_200908`
- harness: Antigravity
- tool_interference: **no**
- 操作者备注: V2 历史分 80；V4 表现 Ability 不错但有 trust 硬伤

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **39 / 45**（6 fail）
  - **`S-plaintext-admin`**：密码明文返回 + setup 自动创建 session→**信任硬伤**
  - **`S-no-actor`**：no_actor session 放行
  - `P-report`：PR 声称 `mqtt_payload` 但无对应文件
  - `M-fidelity`：migration 缺 `ts` 列
  - `E-contract`：`esp_event` 缺 CMake REQUIRES
  - `V4-F12-04` reason-only
- esp static: **8 / 9**（1 failed：`esp_event` 缺 REQUIRES）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **90.0 / 60.0 / D**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 过（F1-05 0pt false claim 标记 P-report 但不扣分） |
| F2 | 8 | **8** | **密码明文返回（−2）+ setup 后自动认证（−2）——S-plaintext-admin** |
| F3 | 14 | **14** | no_actor 放行（−2, S-no-actor）；**ambient 正确关闭**（好！） |
| F4 | 4 | **4** | voice 正确接入 session API |
| F5 | 12 | **12** | care 全链过 |
| F6 | 8 | **8** | migration 缺 `ts` 列（−2, M-fidelity） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | `esp_event` 缺 REQUIRES（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实（虽有 false claim） |
| F12 | 3 | **3** | `role_allowed` ≠ `not_authorized_for_target` |

**Ability：** 8+8+14+4+12+8+8+7+6+8+4+3 = **90**

**Ship cap 触发：** 明文密码 → **max 60**（rubric 规则）

## Final scores
- **Ability:** **90 / 100**
- **Ship:** **60 / 100**（明文密码 hard cap）
- **Class:** **D**（信任/鉴权不可接受）
- **Blockers (behavior only):** `S-plaintext-admin`, `S-no-actor`, `P-report`, `M-fidelity`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.1**
- security: **3.5** — auth 有明文密码硬伤，但 voice/ambient 正确
- migration: **8.0**
- esp_deploy: **9.3**
- process_truth: **5.0** — PR 声称不存在的 `mqtt_payload` 文件

## Findings

### 做得好的
1. **Ambient 正确关闭（F3 no S-ambient）**：隐私边界意识好。
2. **Voice 正确接入（F4=4）**。
3. **ESP build + 大部分 static 过**。
4. **Migration / Sleep / Regression 基本正常**。

### 主要缺口
1. **`S-plaintext-admin`（信任硬伤）**：密码明文返回、setup 后自动创建已认证 session——这属于基本安全常识缺失，触发行 Ship 60 cap。
2. **`S-no-actor`（行为泄漏）**：no_actor session 被放行。
3. **P-report**：PR 声称存在 `mqtt_payload` 但实际 diff 无此文件。
4. **F6 migration 缺 ts 列**。
5. **F8 `esp_event` 缺 REQUIRES**。

### 与 Minimax M2.7 同档

Gemini 3.1 Pro 是继 M2.7 之后第二个因 **信任硬伤** 被打到 Class D 的模型。Ability 虽有 90，但 Ship cap 直接压到 60——与 V2 历史分 80 相比，V4 的信任检测更严格地暴露了问题。

## Recommendation
- **reject**
  - 必改：密码哈希存储（PBKDF2/argon2）
  - 必改：setup 后不自动创建已认证 session
  - 必改：no_actor session 拒绝
  - 建议：补 `esp_event` REQUIRES、修 migration ts
- 一句话：Gemini-3.1-Pro @ Antigravity 是 **「Ability 90 但明文密码信任硬伤触 Ships 60 cap → Class D」** 的样本；安全基础不过关，与 M2.7 同档。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] Ship hard cap 正确使用（明文密码→60）
- [x] 未用 82 墙
- [x] channel 写明
