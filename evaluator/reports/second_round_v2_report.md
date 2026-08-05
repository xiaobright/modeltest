# Project2 第二轮模型评测报告

评测日期：2026-06-13  
更新日期：2026-06-23（补入 Kimi K2.7 Code、GLM-5.2 Opencode/API、GLM-5.2 火山引擎/Opencode、GLM-5.2 WorkBuddy、GLM-5.1 WorkBuddy、Kimi K2.6 WorkBuddy、Minimax M3 WorkBuddy）  
评测项目：`workspace/project2_task` 第二版 benchmark  
记录位置：`evaluator/reviews/*.md`  
样本数：21 个完整评分记录  
第一轮参考报告：`archives/first_round_v1_20260612/evaluator/reports/first_round_report.md`

## 1. 本轮设置

第二轮不再是第一轮那种极弱提示词。它更接近真实工程迭代中的“带现象 debug”：

- 项目被伪装成真实未完成工程，而不是纯测评题。
- 任务目标更明确，公共测试和 debug probe 会给出可复现现象。
- ESP32-S3 不再是选做项，而是必做项。
- 当前工作区以 `PULL_REQUEST_TEMPLATE.md` 作为最终提测说明和自检记录。
- 评分不只看 hidden 数量，也看最终代码、ESP 静态/真实编译、报告事实一致性、人工审查。

这一轮的核心价值不是“谁会不会改一个明显 bug”，而是看模型能否把安全边界、DB 迁移、care_event 全链路、sleep 数据归属、ESP-IDF 固件和报告验证串成一个可信闭环。

## 2. 排名与分层

| Rank | Model | Score | Ability note | Hidden | ESP static | ESP build evidence | 简评 |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | GPT-5.5 | 96 | 96.0 | 33/34 | 8/8 | 未由 evaluator 复跑，报告和静态证据强 | 明显第一，唯一问题是 context reason code 语义 |
| 2 | GLM-5.2 (Opencode/API) | 95 | 95.0 | 33/34 | 6/8 | evaluator WSL build 通过 | 当前最强非 GPT 满血结果，backend 基本完整 |
| 3 | GLM-5.2 (火山引擎 / Opencode) | 89 | 88.9 | 32/34 | 7/8 | 用户确认 Windows ESP-IDF v6.0.1 编译通过 | 强渠道样本，ESP 静态较好，但旧 DB migration 路径仍崩 |
| 4 | GPT-5.4 | 88 | 88.3 | 32/34 | 6/8 | evaluator WSL build 通过 | 与 WorkBuddy GLM-5.2 同分小胜，旧 DB migration 路径仍崩 |
| 5 | GLM-5.2 (WorkBuddy) | 88 | 87.8 | 32/34 | 6/8 | evaluator WSL build 通过 | 渠道复测强但低于 API 满血，旧 DB migration 回退 |
| 6 | doubao-seed-2.0-code | 86 | 86.0 | 32/34 | 5/8 | evaluator WSL build 通过 | 提升最大之一，backend 很强，ESP contract 较弱 |
| 7 | GLM-5.1 (Qoder) | 82 | 82.0 | 30/34 | 8/8 | 用户确认最终编译通过，过程需干预 | 82 档最强 final-code 之一，隐私边界卡住 |
| 8 | Kimi K2.7 Code (Opencode/API) | 82 | 81.8 | 29/34 | 8/8 | evaluator WSL build 通过 | ESP/构建可信度强，非 Qoder 环境，仍被 sensitive context cap 卡住 |
| 9 | DeepSeek V4 Flash | 82 | 81.8 | 30/34 | 8/8 | evaluator WSL build 通过 | Flash 表现强于预期，old DB 路径更硬，仍被 context cap 卡住 |
| 10 | Mimo v2.5 Pro | 82 | 81.7 | 29/34 | 8/8 | 用户确认 WSL 编译，未按指定 wrapper 记录 | 速度和上下文控制优秀，context fallback 未破 |
| 11 | GLM-5.1 (WorkBuddy) | 82 | 81.6 | 30/34 | 7/8 | 用户确认编译完成 | 工具过程明显优于 Qoder，但最终代码旧库迁移回退 |
| 12 | Minimax M3 | 82 | 81.4 | 30/34 | 6/8 | 报告记录较完整 | 报告和过程强，旧 DB migration 崩，context fallback 未破 |
| 13 | Minimax M3 (WorkBuddy / medium thinking) | 82 | 81.2 | 27/34 | 6/8 | 候选报告称编译成功，未独立复跑/确认 | 比 Kimi WorkBuddy 更强，reason-code 噪声较多，context cap 仍在 |
| 14 | Gemini 3.1 Pro | 80 | 80.0 | 29/34 | 7/8 | 未统一复跑 | 相比 V1 大幅提升，backend 主线明显补齐 |
| 15 | Kimi K2.6 (Qoder) | 80 | 80.0 | 29/34 | 7/8 | 记录不规范，受 Qoder 压缩影响 | 能力不弱，但过程稳定性和 ESP buffer 风险扣分 |
| 16 | Gemini 3.5 Flash | 79 | 79.0 | 28/34 | 8/8 | 未统一复跑 | V1 已强，V2 提升有限，卡在 context/migration |
| 17 | Kimi K2.6 (WorkBuddy / medium thinking) | 78 | 78.5 | 27/34 | 6/8 | 候选报告称编译成功，未独立复跑/确认 | WorkBuddy 成本较低，但 final-code 弱于 Qoder K2.6 |
| 18 | DeepSeek V4 Pro | 78 | 78.0 | 29/34 | 5/8 | 未统一复跑 | backend 能力强，ESP 和 migration 较松 |
| 19 | Qwen3.7 Max | 74 | 74.0 | 24/34 | 6/8 | 未统一复跑 | 高努力，但 sleep ownership、migration、context 都有硬伤 |
| 20 | Mimo v2.5 Flash | 72 | 72.0 | 29/34 | 7/8 | evaluator WSL build 失败 | public/debug 强，但 build overclaim 压分 |
| 21 | Minimax M2.5 | 66 | 66.0 | 30/34 | 8/8 | evaluator WSL build 失败 | 静态/hidden 会刷分，但 public 失败和报告甩锅严重 |

本轮平均分约 **82.0**，中位数 **82**。这和第一轮的平均 **57.7**、中位数 **53.5** 差异很大，但这不代表所有模型能力瞬间提升了二十多分，而是 V2 的提示、任务显性化、debug probe、评分规则和人工 rubric 共同改变了测评形态。

## 3. 本轮主要发现

### 3.1 顶部被真正拉开

第一轮 GPT-5.5 和 GPT-5.4 都是 80 分，几乎没有区分出前沿差异。第二轮中：

- GPT-5.5 到 96，基本完整解决安全、care_event、sleep、migration、ESP static。
- GLM-5.2 在 Opencode/API 满血渠道到 95，是当前最强非 GPT 结果，backend 基本完整，只剩 reason code 和 ESP 细节风险。
- 火山引擎 / Opencode 的 GLM-5.2 到 89，hidden 32/34、ESP static 7/8、Windows ESP-IDF v6.0.1 编译由用户确认通过；它强于 WorkBuddy 样本，但旧 DB migration 仍有启动崩溃。
- GPT-5.4 到 88，整体很强，但旧 DB migration 仍有启动崩溃。
- GLM-5.2 在 WorkBuddy 渠道是 88，hidden/ESP/build 形态与 GPT-5.4 非常接近，但同样被旧 DB migration 卡住。若用小数点只为同分排序，火山/Opencode GLM-5.2 约 **88.9**、GPT-5.4 约 **88.3**、WorkBuddy GLM-5.2 约 **87.8**；这说明三个样本都在强 A 档附近，但 GLM-5.2 的模型本体上限仍应看 95 分 API 结果。
- Doubao 到 86，backend 修复很完整，但 ESP contract 与迁移仍弱于 GPT/GLM 顶部结果。

这说明 V2 对第一梯队区分更好。前沿模型的差距不再只体现在“有没有找到任务”，而是体现在旧数据迁移、隐私 reason code、ESP 可维护性、报告一致性这些收口细节。

### 3.2 中游从 50 分堆移动到 80/82 分堆

V1 中大量模型堆在 48-55，因为一个本地管理 API 鉴权根因会连带丢很多分。V2 加了更明确的 debug 现象之后，很多模型都能补齐 admin/auth 主线，于是分数整体上移。

但新的集中点变成了 **80/82 分档**。典型模式是：

- public tests 通过。
- debug probe 通过。
- admin/auth 基本全过。
- sleep import 基本全过。
- care_event 大部分完成。
- ESP 至少有静态实现。
- 但 `build_chat_context_v3()` 仍会在没有显式 `session_id` 时 fallback 到 current session，导致 targeted patient context 被 ambient session 授权。

这个 bug 很真实，也应该是高价值扣分点，但它仍然让 GLM、Kimi K2.7、DeepSeek Flash、Mimo Pro、Minimax M3 等模型挤在同一个 82 cap 附近。下一版如果想区分这些模型，需要把 context policy 拆成更多独立、可部分得分的细项，而不是一个 cap 决定天花板。

### 3.3 public/debug 通过不再代表工程可信

Minimax M2.5 是很好的反例。它 hidden 30/34、ESP static 8/8，看数字不差，但：

- 公共测试没过。
- 报告把失败归因于测试框架，而不是承认业务 contract 未满足。
- ESP-IDF v6.0 真实编译失败，`espressif/mqtt: ^2.0.0` 依赖解析不到。
- 过程中还出现文件写入/输出错误，导致工作提前结束，需要人工继续。

这说明 V2 的自动脚本仍不能完全替代人工审查。隐藏测试和静态测试是证据，不是最终评分本身。

### 3.4 ESP-IDF 仍是强区分点，但必须真实 build

本轮 ESP 暴露出四类情况：

- **完整或接近完整**：GPT-5.5、GPT-5.4、DeepSeek Flash、GLM、Mimo Pro。
- **新增强固件结果**：Kimi K2.7 Code 在 Opencode/API 环境中 ESP static 8/8，evaluator 复跑 ESP-IDF v6.0 build 通过。
- **backend 强但 ESP contract 弱**：Doubao、DeepSeek Pro。
- **静态过但真实 build 失败**：Mimo Flash、Minimax M2.5。
- **过程依赖工具/用户干预**：Qoder 中的 GLM、Kimi。
- **工具渠道对照样本**：WorkBuddy GLM-5.1 的压缩和续写表现明显优于 Qoder，但最终代码少了旧库迁移兼容和一个 ESP 静态契约点。

因此 V3 最好把 ESP 分成两层：

- 静态协议 contract：topic、NVS、payload_b64、USB 保留、Wi-Fi/MQTT API。
- 真实编译 contract：必须使用提供脚本，保存 build log，失败要写清楚定位。

只靠 static markers 太容易被“关键词式实现”刷过去。

### 3.5 工具影响不可忽略

这轮模型跑在不同工具和额度渠道中：

- GPT 在 Codex 中，整体发挥最好，工具链和上下文管理也最稳定。
- Qoder 中的 GLM/Kimi 出现压缩后忘工作目录、忘 build 脚本、忘 ESP-IDF v6.0.0 环境的问题，明显是工具层干扰。
- Antigravity/Gemini 的额度较宽，但 Claude 额度不足，无法完整横向复测。
- Opencode/API 类模型环境更接近统一，但成本不能全覆盖。
- WorkBuddy 模型更新快、免费/低成本积分多，实用价值不低；但 GLM-5.2 复测从 API 版 95 掉到 88，且体感输出更快，说明它更适合作为工具实用榜渠道，不应直接替代满血 API 榜。新补的火山/Opencode GLM-5.2 到 89，也说明渠道样本能接近 GPT-5.4 档，但和满血 API 结果仍有明显收口差距。
- GLM-5.1 在 WorkBuddy 中没有复现 Qoder 的压缩失忆，直到 ESP-IDF 编译完成、写 PR 阶段才触发压缩，压缩后仍能继续工作；但最终代码没有超过 Qoder 版 GLM-5.1，因为旧数据库迁移路径反而回退。
- Kimi K2.6 在 WorkBuddy 中成本约 **500 积分**，倍率 **0.7x**，折算基准用量约 `500 / 0.7 = 714`；渠道成本确实低。但最终代码只有 hidden 27/34、ESP static 6/8，care_event 全链路、旧库迁移、ESP 契约和报告命令都弱于 Qoder 版 K2.6。这说明 WorkBuddy 便宜好用不等于每个第三方模型样本都更强。
- Minimax M3 在 WorkBuddy 中也标注为 medium thinking。它 hidden 27/34、ESP static 6/8，看数字低于 Opencode/API 版 M3，但失败质量不同：不少 context 失败是 reason-code 精确字符串问题，old DB migration 从崩溃级改善为 `ts=0` 保真问题，care_event 主链也更完整。成本上它约 **900 积分**、倍率 **0.25x**，折算基准用量约 `900 / 0.25 = 3600`，大约是 Kimi WorkBuddy 的 **5 倍**；低倍率被高用量抵消了。能力榜仍不应高估，但娱乐榜可以给它比 Kimi WorkBuddy 更高的位置。

所以本轮分数更适合理解为“模型 + 工具 + 提示 + 环境”的端到端结果。单看模型本体时，要单独标注工具干扰。

## 4. 与 V1 相比的能力变化

本轮最明显的不是强模型变强，而是中游模型“知道该往哪里修”之后，大量从 50 分段跃迁到 78-82 分段。说明 V1 的弱提示词主要测主动发现能力，V2 测的是有现象、有任务约束后的真实 debug 和收口能力。

提升特别明显的模型：

- Doubao：42 -> 86，说明 V1 弱提示下没有展开能力，V2 有引导后 backend 能力释放很多。
- GLM：48 -> 82，有较强 final-code 能力，但工具/过程需要注意。
- Gemini 3.1 Pro：50 -> 80，从中低档进入强 partial。
- Kimi：52 -> 80，说明它能完成广泛修复，但 context/ESP 细节仍不足。
- Mimo Pro：55 -> 82，效率优秀，卡在高阶隐私边界。

提升较小的模型：

- Gemini 3.5 Flash：76 -> 79。V1 已经发挥较好，V2 没拉开更多。
- GPT-5.4：80 -> 88。明显提升，但旧 DB migration 仍使其低于 GPT-5.5。

## 5. 当前 V2 的问题

### 5.1 82 分档仍偏拥挤

V2 已经比 V1 好很多，但 82 档包含多个风格不同的模型：

- GLM：final-code 较强，过程受工具影响；WorkBuddy 过程更顺，但 Qoder 版 final-code 迁移细节更完整。
- Kimi K2.7：Opencode/API 环境下固件和构建强，old DB migration 仍不完整。
- DeepSeek Flash：真实 build 强，hidden 略多，但 migration/context 弱。
- Mimo Pro：效率好，ESP static 强，但 context fallback 未破。
- Minimax M3：报告和流程强，migration/ESP static 较弱。

这些模型不应该完全一个分数。当前已经用 ability-only ranking score 做小数区分，但 V3 需要在 rubric 层面让它们自然分开。

### 5.2 context policy 太像单点天花板

Sensitive targeted context fallback 是高价值问题，但目前它更像一道“有没有想到”的门槛题。建议 V3 拆成：

- 无显式 session 不得读 target context。
- expired session 不得读。
- unknown identity 不得读。
- no actor subject 应该 denied，reason 必须准确。
- patient A 不能读 patient B。
- allowed=false 时不能泄漏 target subject、care_event、memory。
- staff/admin 可以读，但必须有明确 session。

这样模型即使漏一个，也不会全部挤到同一个 cap。

### 5.3 public failure 应更强扣分

Minimax M2.5 说明 hidden 数字高不代表可信。V3 可以继续保留“公共测试失败最高 68”这类 cap，并明确：

- 公共测试失败不能用“测试框架问题”轻易带过。
- 如果要质疑测试，必须给出最小复现、数据流解释和替代验证。
- 只要失败在自己触碰过的业务路径，默认按候选修复失败处理。

### 5.4 报告一致性应继续提高权重

V2 已经看到多种报告问题：

- build 没过但声称成功。
- 没用指定脚本但写成已完成。
- public test 失败却写 7/8 可接受。
- 使用临时 helper，但最终 diff 没保留。

这部分非常像真实开发中的“PR 描述不可信”。它值得单独保留为评分项，而不是只作为附注。

## 6. 阶段性结论

第二轮 benchmark 更适合测“真实 debug 能力”和“工程收口能力”。它比第一轮更能释放中游模型能力，也更能区分 GPT-5.5 和 GPT-5.4 这种前沿模型差距。

但它仍有两个问题：

- 中上游模型继续集中在 80/82 分档。
- 自动测试中 ESP static 和 hidden 数字仍可能被表面实现刷高。

下一版应继续保持真实项目伪装、必要现象引导和严格 workflow，同时增加更多互不耦合的中等难度问题，并把 context policy、migration、ESP build、报告一致性拆得更细。这样才能既保留“强模型能发挥”的空间，也把 78-86 这一段拉开。

## 7. 2026-07-07 追加样本：LongCat-2.0

LongCat-2.0 是 V2 后续追加的美团模型样本，结果目录为 `evaluator/results/20260707_112431`，单模型 review 为 `evaluator/reviews/longcat_2.0_20260707_112431.md`。

最终记录为 **82 / 100**，能力排序小数为 **81.5 / 100**。自动证据是 public 通过、debug probe 通过、hidden 30/34、ESP static 5/8。候选报告声称 ESP-IDF 构建通过，我又用 Windows ESP-IDF v6.0.1 复核了一次，`idf.py build` 实际通过并生成 `stdpro.bin`，因此不按 build-trust 失败扣分。

这个样本的优点很清楚：admin/auth hidden 8/8，sleep hidden 6/6，旧 SQLite `care_events` migration hidden 通过，真实 ESP-IDF build 也过了。换句话说，它不是那种只靠关键词或静态检查刷分的提交，主线修复确实有工程含金量。

但它仍然被严格榜卡在 82：敏感 targeted-context 路径仍会在缺少显式 session 边界时被 ambient/current session 授权，这是发布阻断级 privacy bug。除此之外，ESP static 只有 5/8，缺 `mbedtls` dependency marker、`mbedtls_base64` marker 和显式 `tof1` topic suffix marker；PR template 也因为没有明确记录修复后的 final verification wording，被 process contract 扣了一分。

所以 LongCat-2.0 的位置大概是：正式榜仍在 82 档中段，强于很多 78-80 的 partial 修复；娱乐软榜可给到 **84.5**，因为旧库迁移和真实构建比不少 82 档样本更扎实。但它还不能越过 Doubao 86，也不能接近 GPT-5.4 / GLM-5.2 88+ 这一档，主要差距就在 context policy 收口和 ESP 契约完整度。

## 8. 2026-07-09 追加样本：Grok-4.5

Grok-4.5 是 V2 后续追加的新发布模型样本，结果目录为 `evaluator/results/20260709_193745`，单模型 review 为 `evaluator/reviews/grok4.5_20260709_193745.md`。

最终记录为 **96 / 100**，能力排序小数为 **95.7 / 100**。自动证据是 public 通过、debug probe 通过、hidden 33/34、ESP static 8/8。用户确认 ESP-IDF 真实构建两次通过，因此本次不再重复长时间编译。

这个样本和之前 Grok-4.3 的差异非常大。Grok-4.3 更像是没有真正展开工作就写完成总结；Grok-4.5 则把 backend、migration、sleep、care_event、ESP static 和真实 build 证据都收得很完整。它也修掉了大量 82 档模型反复撞到的敏感上下文 ambient/current-session fallback：`test_sensitive_target_context_requires_explicit_session` 已经通过。

唯一 hidden 失败是 `session_without_actor_subject` 的 reason code：模型把缺少 `actor_subject_id` 的会话归因为 `not_authenticated`，而 contract 期望 `not_authorized_for_target`。这属于上下文策略语义精度问题，不是数据泄漏级问题。另一个小扣分是没有生成 `answer.md`，但 PR/report artifact 通过了 process contract，所以只作为格式一致性扣分。

结论：Grok-4.5 可以记为当前 V2 顶级样本之一，和 GPT-5.5 同一档，略低于 GPT-5.5 的原因主要是最终报告格式和一个 reason-code 细节。它明显高于 GLM-5.2 API 的 95 分样本，也把 Grok 系列从第一轮“很拉”的印象里拉了回来。

## 9. 2026-07-09 追加样本：Composer 2.5

Composer 2.5 是 Grok Build CLI 侧的新模型样本，结果目录为 `evaluator/results/20260709_195343`，单模型 review 为 `evaluator/reviews/composer_2.5_20260709_195343.md`。

最终记录为 **82 / 100**，能力排序小数为 **81.45 / 100**。自动证据是 public 通过、debug probe 通过、hidden 30/34、ESP static 7/8。用户确认 ESP-IDF 真实构建通过，并且整体完成速度很快。

这个样本的强项是手感和工程展开速度。admin/auth hidden 8/8，sleep hidden 6/6，process-reporting hidden 5/5，ESP static 7/8，再加真实编译通过，说明它不是刷关键词式提交。固件部分还做了模块拆分，新增 `device_config`、`maixsense_parser`、`mqtt_payload`、`protocol_packet` 等 helper，整体可维护性比很多只改 `main.cpp` 的样本好。

但它没有越过 V2 最关键的 82 墙。hidden 里 `sensitive_target_context_requires_explicit_session` 仍失败，说明 targeted patient context 仍会被 ambient/current session 授权；`session_without_actor_subject` 也被错误允许，不只是 reason-code 小问题。care_event context integration 的失败同样来自这条隐私边界。旧数据库迁移也漏了 `ts` 列，老 `care_events` 表不能完整升级。

因此 Composer 2.5 应放在 82 档中游偏上：强于很多 78-80 partial 修复，接近 Minimax M3 / LongCat 这组，但低于 GLM-5.1 Qoder、Kimi K2.7、DeepSeek Flash、Mimo Pro 这些 82 档前排。娱乐软榜可给 **83.5**，因为速度、ESP 和可维护性不错；正式榜仍是 **82**，因为隐私边界没有收住。
