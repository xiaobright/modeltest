# V4 高耦合上限题候选池

**状态**：建议稿，暂不纳入 V4.0 主分。  
**目的**：收集交叉审核意见后，再决定是否把 1–2 个高耦合题作为 V4.0 加分/tie-breaker 或 V4.1 正式 family。

## 1. 为什么需要 capstone

当前 V2/V4 主线能较好区分 70–90 分段，但 95+ 模型的剩余卡点多是细节、reason、报告或单点迁移问题。若要测试模型上限，需要引入真实工程中的跨模块耦合：

- 数据从传感器进入 gateway 后，是否能正确映射到床位和患者。
- 权限、安全、历史状态和上下文摘要是否保持一致。
- 部分故障、重试、迁移或配置变化时，系统能否安全降级。
- 模型是否能在不重写整仓、不删功能的前提下完成端到端闭环。

## 2. 出题原则

- **作为上限题，不作为大锤**：capstone 失败不应自动把模型打到固定低分，除非发生真实隐私泄漏、public 回归、篡改测试或报告造假。
- **拆成可部分得分子项**：每题 8–12 分，拆成 4–6 个行为 oracle。
- **避免隐藏实现偏好**：测输入/输出/DB/API 状态，不要求特定函数名、文件名或模块拆分。
- **public 给症状，hidden 判闭环**：公开材料只暗示业务问题，不给完整链路答案。
- **优先低硬件依赖**：可用 fake payload、temp DB、fake session 和本地 HTTP/函数调用完成，不要求真机。

## 3. 候选 A：Sensor → Gateway → care_event → Context → Voice 闭环

### 场景

ESP 模拟上传一条 ToF/MLX 异常 payload。Gateway 解析 room/bed，写入 sensor latest，并按规则生成或关联 `care_event`。随后授权 v3 context 和 voice/RK3588 助手能读到这条事件；未授权、跨患者或无显式 session 时不得泄漏。

### 耦合模块

ESP 协议、gateway ingest、bed mapping、sensor_store、care_events、DB、context policy、voice bridge。

### 行为 oracle

| 子项 | 建议分 | 判定 |
|------|------:|------|
| Payload ingest | 2 | fake ToF/MLX payload 能按协议进入 gateway，room/bed 归一化正确 |
| Sensor latest | 2 | latest/status API 能看到正确床位的最新状态，不污染其它床 |
| care_event linkage | 2 | 异常 payload 生成或关联 care_event，limit/order 正确 |
| Authorized context | 2 | 合法显式 session 可在 context 中看到对应护理事件 |
| Unauthorized zero leak | 2 | 无 session/跨患者/ambient-only 不泄漏事件、患者名或偏好 |
| Voice bridge | 1–2 | voice 路径带显式 session 读取同一上下文，不恢复 ambient fallback |

### 价值

这是最强的上限题：能测模型是否把固件协议、后端状态、护理事件、会话隐私和助手调用收成一个闭环，而不是分别补 marker。

### 风险

链路长，容易连坐。若纳入主分，建议作为独立 capstone family，且每个子项独立给分。

## 4. 候选 B：Patient Bed Transfer / 换床历史保真

### 场景

患者从 `R1203/B1` 转到 `R1204/B2`。历史 sleep、care_event、sensor 事件仍属于历史床位；当前 context 使用新床位；旧床位不能被另一个患者的 session 读出历史敏感数据。

### 耦合模块

bed_config、subjects、sleep_importer、care_events、sensor_store、context authorization、DB migration。

### 行为 oracle

| 子项 | 建议分 | 判定 |
|------|------:|------|
| Transfer model | 2 | 能表达当前床位与历史床位，不用当前床位覆盖所有历史 |
| Historical sleep | 2 | 换床前 sleep 仍归历史床位/患者，换床后写入新床位 |
| Historical care_event | 2 | 事件按发生时床位保真，context 按患者权限汇总 |
| Cross-patient isolation | 2 | 新入住旧床位的患者不能读前一位患者历史 |
| API compatibility | 1–2 | legacy latest/context 不崩，排序和 limit 保持 |

### 价值

真实护理/病房系统很常见，能测“当前状态 vs 历史事实”的系统建模能力。强模型如果只做简单 room/bed 覆盖，会在这里暴露。

### 风险

需要先明确项目是否接受 transfer 数据模型。如果现有真实项目没有该概念，可作为 V4.1 题，不宜仓促塞进 V4.0。

## 5. 候选 C：Offline Retry + Idempotency / 离线重放幂等

### 场景

网络中断后，同一批 sensor/sleep/care payload 被重放两次。系统不能重复生成事件；但可更新 latest、保留排序、记录重试来源，并且报告不能声称真机联网已验证。

### 耦合模块

ESP payload id/hash、gateway ingest、sleep_importer、care_events、DB unique/index、API latest/context、process reporting。

### 行为 oracle

| 子项 | 建议分 | 判定 |
|------|------:|------|
| Stable idempotency key | 2 | 同一 payload 重放不重复插入 |
| Latest update | 2 | latest/status 仍反映最新数据 |
| care_event dedupe | 2 | 同一异常不重复生成多条护理事件 |
| Ordering | 1–2 | 新旧 payload 混合后排序稳定 |
| Report honesty | 1 | 报告区分模拟重放与真实 MQTT 连通 |

### 价值

能测分布式系统味道：重试、去重、排序、报告诚实。比单纯 CSV 幂等更复杂。

### 风险

需要给清楚 dedupe 契约，否则可能变成猜题。建议 V4.1 或作为 optional capstone。

## 6. 候选 D：Privacy-safe Summary Under Partial Failure / 故障降级隐私摘要

### 场景

同一次 context 请求中：sleep 数据可用，care_event 表是旧 schema，sensor latest 缺失或损坏，voice 有合法 session。系统应返回可用的安全摘要和 degraded flags，不 500、不用 ambient fallback、不泄漏未授权数据。

### 耦合模块

DB migration、context builder、care_event、sleep_importer、sensor_store、auth/session、voice bridge、error handling。

### 行为 oracle

| 子项 | 建议分 | 判定 |
|------|------:|------|
| No 500 | 2 | 局部表/数据损坏不导致 context 整体崩溃 |
| Safe degradation | 2 | 返回 degraded flags 或空结构，不编造数据 |
| Authorized useful summary | 2 | 合法 session 仍能看到可用 sleep/非损坏部分 |
| Unauthorized zero leak | 2 | 未授权路径仍零泄漏 |
| Migration interaction | 1–2 | 旧 care_event schema 自动升级或隔离失败 |

### 价值

非常适合区分 96+：它测的不是 happy path，而是部分失败下的系统设计和隐私边界。

### 风险

要避免把异常处理写成“吞掉所有错误”。Oracle 应要求 degraded 可见、日志/状态可解释。

## 7. 候选 E：Multi-Actor Audit Trail / 多角色审计链

### 场景

admin 创建 care_event，staff 查看并追加 note，patient 只能看到自己的摘要，voice worker 只读授权上下文。所有写操作进入 audit log；登出或过期 session 后不能继续写。

### 耦合模块

admin auth、session、care_event、audit DB、context、API regression、process reporting。

### 行为 oracle

| 子项 | 建议分 | 判定 |
|------|------:|------|
| Write auth | 2 | admin/staff/patient 写权限符合角色边界 |
| Audit rows | 2 | 写操作记录 actor、target、action、time |
| Read isolation | 2 | patient 只读自己的摘要，不读其它患者 |
| Session invalidation | 2 | logout/expired 后不可继续写 |
| Regression | 1–2 | 旧 care_event API 不崩 |

### 价值

能测写路径权限，而不只是 context read path。也能抓“只保护 GET，不保护 POST”的实现。

### 风险

可能需要新增 audit 表，实施成本高。适合 V4.1。

## 8. 候选 F：Config Rotation / 配置轮换不硬编码

### 场景

Bemfa UID、room/bed、admin/session TTL、CSV import policy 在运行中变化。新 payload 使用新配置，历史数据不被重写，旧 session 按 TTL 失效。

### 耦合模块

config、NVS/ESP docs、gateway APIs、session、sensor/care/sleep、reporting。

### 行为 oracle

| 子项 | 建议分 | 判定 |
|------|------:|------|
| Runtime config read | 2 | 不硬编码 room/bed/uid/test IDs |
| Historical stability | 2 | 配置变更不重写历史 sleep/care/sensor |
| New data routing | 2 | 新 payload 按新配置进入正确床位 |
| Session TTL | 2 | TTL 变化后旧 session 行为符合契约 |
| Docs/report | 1 | 文档和报告说明配置来源与未验证硬件 |

### 价值

强力抓硬编码和一次性全局状态污染。

### 风险

范围较散，容易变成多个小题拼盘。若采用，应收窄到 room/bed + session TTL 两条线。

## 9. 推荐取舍

### V4.0 若只选一个

选 **候选 D：故障降级隐私摘要**。

理由：

- 不需要硬件。
- 与现有 F3/F6/F5/F7 自然相连。
- 能测上限，又不会强迫大规模新增业务模型。
- 对 96 档模型更有区分度：happy path 已经能做，partial failure 下的安全降级更难。

### V4.0 若选两个

选：

1. **候选 D：故障降级隐私摘要**
2. **候选 A：Sensor → Gateway → care_event → Context → Voice 闭环**

其中 A 可以先做 fake payload + gateway/context/voice 的纯软件链路，不要求真实 MQTT 或真机。

### V4.1 优先

1. Patient Bed Transfer / 换床历史保真。
2. Offline Retry + Idempotency / 离线重放幂等。
3. Multi-Actor Audit Trail / 多角色审计链。

这些更像新增业务模型或持久化契约，适合等 V4.0 稳定后再加。

## 10. 交叉审核问题

请其它 AI / 人类审核时明确回答：

| 问题 | 选择 |
|------|------|
| V4.0 是否需要 capstone？ | 不需要 / 需要 1 个 / 需要 2 个 |
| 若需要，首选哪个？ | A/B/C/D/E/F |
| 是否作为正式 100 分内 family？ | 是 / 否，作为 tie-breaker / 否，作为 V4.1 |
| 是否接受新增业务概念（如 bed transfer、audit log）？ | 是 / 否 |
| 是否会导致测试成本过高？ | 是 / 否 |

## 11. 当前建议

本阶段只把 capstone 放入候选池，不立即修改 F1–F12 的 100 分结构。等至少两轮外部交叉审核后，再决定是否：

1. 作为 V4.0 tie-breaker。
2. 从 F12/static/redundant context 中挪 8–10 分给 capstone。
3. 延后到 V4.1。
