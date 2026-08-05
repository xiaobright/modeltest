# V4 Review: Gemini-3.5-Flash @ Antigravity

## Meta
- result_id: `20260712_201859`
- harness: Antigravity
- tool_interference: **no**
- 操作者备注: 对比同通道 Gemini-3.1-Pro（90/60/D—明文密码）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **42 / 45**（3 fail）
  - `S-no-actor`：no_actor session 放行
  - `P-report`：PR 缺修复后验证命令记录
  - `V4-F12-04` reason-only
  - **无** S-plaintext-admin / S-ambient / M-crash / trust
- esp static: **7 / 9**（2 failed：`mbedtls` 缺 REQUIRES + topic `tof1` 标记缺失）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **93.0 / 93.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 6 | **6** | F1-01 缺验证命令记录（−2, P-report） |
| F2 | 12 | **12** | **auth 满分**——无明文密码，无自动 session（远优于 Pro） |
| F3 | 14 | **14** | no_actor 放行（−2, S-no-actor）；**ambient 正确关闭** |
| F4 | 4 | **4** | voice 正确 |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | **迁移满分**（优于 Pro 的 8/10） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 6 | **6** | `mbedtls` 缺 REQUIRES（−1）+ topic `tof1` 标记缺失（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实（虽缺验证命令） |
| F12 | 3 | **3** | `role_allowed` ≠ `not_authorized_for_target` |

**Ability：** 6+12+14+4+12+10+8+6+6+8+4+3 = **93**

## Final scores
- **Ability:** **93 / 100**
- **Ship:** **93 / 100**（无 trust cap 触发）
- **Class:** **B+**
- **Blockers (behavior only):** `S-no-actor`, `P-report`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **10.0**
- security: **9.2** — auth 满分，no_actor 是唯一缺口
- migration: **10.0**
- esp_deploy: **8.6**
- process_truth: **7.5**

## Findings

### 做得好的
1. **Auth 满分（F2=12）**：无明文密码、无自动 session——**与 Pro 的明文密码形成鲜明对比**。
2. **Ambient 正确关闭（F3 无 S-ambient）**。
3. **Voice 正确 + Migration 满分 + Sleep 全过**。
4. **无信任硬伤**：Ship=93，未被 cap。

### 主要缺口
1. **`S-no-actor`**：no_actor session 放行（与 Pro 同款）。
2. **`E-contract`（F8 −2）**：mbedtls REQUIRES + topic 标记双缺。
3. **`P-report`（F1-01）**：PR 缺验证命令。
4. **F12-04 reason 精度**。

### Pro vs Flash 同通道对比

| 项目 | Pro（90/D） | Flash（93/B+） |
|:---|---:|:---:|
| F2 auth | **8/12**（明文密码） | **12/12** ✅ |
| F3 ambient | ✅ 关掉 | ✅ 关掉 |
| F3 no_actor | ❌ 放行 | ❌ 放行 |
| F6 migration | 8/10（缺 ts 列） | **10/10** ✅ |
| F8 ESP | 7/9 | 6/9 |
| **Ability** | **90** | **93** |
| **Ship** | **60**（cap） | **93** |
| **Class** | **D** | **B+** |

**讽刺的是：Flash 作为更小更快的模型，在本测试中全面压制了 Pro。** Pro 多出来的参数和推理能力并没有转化为安全意识和代码质量，反而犯了明文密码这种低级错误。

## Recommendation
- **revise**
  - 必改：no_actor session 拒绝
  - 建议：补 `mbedtls` REQUIRES、补 topic 标记、补 PR 验证命令
- 一句话：Gemini-3.5-Flash @ Antigravity 是 **「93 分 B+、auth 满分、迁移满分、无信任硬伤，仅 no_actor + ESP 细节拖后腿」** 的样本；**比同通道 Pro 高出 33 个 Ship 分，令人意外。**

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] 同通道同族对比分析
