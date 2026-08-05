# Project2 两轮评测对照报告

对照日期：2026-06-13  
V1 报告：`archives/first_round_v1_20260612/evaluator/reports/first_round_report.md`  
V2 报告：`evaluator/reports/second_round_v2_report.md`  
注意：两轮不是完全同一题面。V1 是弱提示主动探索，V2 是更强约束的现象-debug 工程迭代。因此分数可以做阶段对照，但不能当成严格 A/B 同题成绩。

## 1. 总体对照

| 指标 | V1 | V2 | 变化 |
|---|---:|---:|---:|
| 完整评分样本 | 14 | 14 | 持平 |
| 平均分 | 57.7 | 80.5 | +22.8 |
| 中位数 | 53.5 | 81.0 | +27.5 |
| 最高分 | 80 | 96 | +16 |
| 最低分 | 36 | 66 | +30 |
| hidden 规模 | 28 | 34 | V2 更细 |
| ESP static 规模 | 6 | 8 | V2 更细 |
| 主要提示形态 | 弱提示 | 强约束 + debug 现象 | 测试目标变化 |

V1 的主要结论是：能区分第一梯队和普通模型，但中游严重堆在 48-55。  
V2 的主要结论是：中游整体被拉起来了，前沿也能分开，但新的拥挤点变成 80/82。

## 2. 共同模型分数变化

| Model | V1 | V2 | Delta | 解释 |
|---|---:|---:|---:|---|
| GPT-5.5 | 80 | 96 | +16 | V2 把前沿收口能力拉开，几乎全修 |
| GPT-5.4 | 80 | 88 | +8 | 仍强，但 migration 收口弱于 5.5 |
| Gemini 3.5 Flash | 76 | 79 | +3 | V1 已发挥较好，V2 提升不大 |
| Gemini 3.1 Pro | 50 | 80 | +30 | 有明确现象后 backend 主线显著补齐 |
| Minimax M3 | 60 | 82 | +22 | 报告和流程变强，但卡 context cap |
| Mimo v2.5 Pro | 55 | 82 | +27 | 效率和实现强，漏 high-value privacy |
| Qwen3.7 Max | 53 | 74 | +21 | admin/auth 进步大，但 sleep/migration/context 仍弱 |
| DeepSeek V4 Pro | 52 | 78 | +26 | backend 广泛修复，ESP/migration 较松 |
| Kimi K2.6 | 52 | 80 | +28 | 有较强完成能力，受 Qoder 工具和 ESP 细节影响 |
| GLM5.1 | 48 | 82 | +34 | final-code 能力强，过程依赖人工纠偏 |
| doubao-seed-2.0-code | 42 | 86 | +44 | V2 最大提升之一，说明 V1 弱提示压制了发挥 |

共同模型平均分约从 **58.9** 到 **82.5**，提升约 **23.6** 分。

未直接复测或不可直接对照：

- V1 有 Claude Opus 4.6、Nemotron 3 Ultra Free、Grok 4.3，V2 未完整同口径复测。
- V2 新增 DeepSeek V4 Flash、Mimo v2.5 Flash、Minimax M2.5 等低/Flash 档模型。

## 3. 为什么 V2 普遍涨分

### 3.1 提示词和项目设计改变了能力入口

V1 提示词非常弱，模型需要自己意识到：

- 要读任务文档。
- 要跑测试。
- 要找 hidden-style 安全边界。
- ESP32 不是摆设。
- 最终报告要和实际 diff 一致。

这测的是主动发现能力。很多中游模型不是完全不会修，而是没有主动进入“系统性审查模式”。

V2 给了更强的工程迭代氛围和 visible debug 现象，模型更容易进入真实 debug 流程。它更像现实中工程师收到 bug report 后的修复，而不是在一个陌生项目里自己找所有坑。

### 3.2 V2 把 auth 主线显性化了

V1 最大堆分点是本地 loopback admin bypass。很多模型没看懂“本地 worker allowlist”和“管理 API 登录态”的区别，于是 auth、care_event gate、session spoofing、logout 等一串全挂。

V2 中大多数模型能补齐 admin/auth，因此分数整体上移。这个变化说明：

- V1 更考察主动安全审查。
- V2 更考察已知现象下的修复能力。

两者都有效，但测的是不同能力。

### 3.3 V2 评分给了更多部分信用

V1 中几个高权重根因耦合太强。V2 的 rubric 更细：

- Debug process and reporting
- Admin/auth boundary
- Session/context policy
- care_event full chain
- Sleep CSV ownership
- ESP32 protocol/build
- DB migration
- Regression compatibility
- PR factual consistency
- Maintainability

这让模型即使漏掉一个大点，也能通过其他独立模块体现能力。因此中游不再全部挤在 50 分。

## 4. 前沿模型对照

### GPT-5.5 vs GPT-5.4

V1 中两者都是 80，没有明显拉开。V2 中：

- GPT-5.5：96，33/34 hidden，8/8 ESP static。
- GPT-5.4：88，32/34 hidden，6/8 ESP static，真实 ESP build 通过。

V2 拉开的关键不是 public/debug，而是：

- GPT-5.5 更完整处理旧 DB migration。
- GPT-5.5 的 care_event/context/ESP helper 拆分更完整。
- GPT-5.4 仍有 old SQLite migration 启动崩溃。
- 5.5 的主要剩余问题只是 policy reason code，非数据泄漏。

成本上，这轮 5.5 由于中断、掉缓存等因素，价格接近 5.4 的两倍，未复现第一轮“token 少一半所以成本接近”的情况。因此目前结论是：

- **质量**：V2 中 GPT-5.5 明显领先。
- **成本**：不稳定，受中断、缓存命中和压缩影响很大。
- **性价比**：不能只按单次结果下结论，但 5.5 的质量优势是真实的。

### GPT 系 vs 第二梯队

V2 中第二梯队最强是 Doubao 86、GLM/Mimo/Minimax/DeepSeek Flash 82。它们能完成绝大多数显性工程任务，但共同短板是：

- targeted context 的 ambient session fallback。
- 旧 DB migration 顺序或保真度。
- ESP build/report 一致性。
- 报告中对未验证内容的过度自信。

也就是说，第二梯队已经会“把活干起来”，但在敏感边界和部署收口上仍比 GPT-5.5 差一截。

## 5. 中游区分度对照

### V1 的中游问题

V1 中游集中在：

- Mimo Pro 55
- Nemotron 54
- Qwen 53
- DeepSeek Pro 52
- Kimi 52
- Gemini 3.1 50
- GLM 48

这批模型实际行为有差异，但分数相近。原因是一个 auth 主线没破，会导致太多隐藏测试一起失败。

### V2 的中游问题

V2 中游变成：

- GLM 82
- Mimo Pro 82
- Minimax M3 82
- DeepSeek Flash 82
- Gemini 3.1 80
- Kimi 80
- Gemini 3.5 Flash 79
- DeepSeek Pro 78

这说明 V2 已经把中游从“不会主动发现”区分成了“能完成大部分工程，但卡在高阶边界”。这是进步，但仍不够细。

V3 应该把 78-86 这段继续拉开，而不是再全测一轮之后发现大家又堆在一个档。

## 6. 两轮共同揭示的模型能力维度

### 主动性

V1 更能测主动性。弱提示下能主动读任务、跑测试、审查安全边界的模型很少。GPT、Gemini 3.5 Flash、Claude 部分表现较强。

### Debug 执行力

V2 更能测 debug 执行力。给出现象后，GLM、Mimo、Doubao、Kimi、Gemini 3.1 都明显提升，说明这些模型不是不能写代码，而是需要更明确的问题入口。

### 工程收口

两轮都显示最难的是收口：

- 旧数据库迁移。
- session/context 隐私边界。
- ESP-IDF 真实 build。
- 报告和实际代码一致。
- public/debug/hidden 之外的人工合理性。

这也是强模型真正拉开的地方。

### 报告可信度

弱模型和部分中游模型会写出完成感很强的报告，但不一定可信。典型表现：

- 公共测试失败却说是测试问题。
- build 没跑或没过却写成完成。
- 静态 marker 过了就声称协议完整。
- 修改了 helper 或临时脚本，但最终 diff 没留下。

这个维度很真实，建议保留甚至加权。

## 7. 对下一版 V3 的建议

### 7.1 保留 V1/V2 双轨

以后可以分两种 prompt：

- **弱提示轨**：测主动发现能力。
- **强约束 debug 轨**：测真实修复和收口能力。

同一个模型两轨都测，才能知道它是“不会主动找问题”，还是“找到问题后也修不好”。

### 7.2 拆细 82 分 cap

不要让一个 context fallback 决定太多模型的天花板。可以拆成多个独立计分项：

- 无 session targeted context。
- expired session。
- unknown identity。
- no actor subject。
- patient cross-access。
- staff/admin access。
- denied response 不泄漏 modalities。
- reason code 正确性。

这样能把 82 档自然分成 78、80、82、84、86。

### 7.3 增加更多中等难度、低耦合问题

建议加入：

- 一个和 auth 无关的 DB migration 保真问题。
- 一个 API pagination/order/limit 细节。
- 一个跨模块 normalization 问题。
- 一个 worker allowlist 的边界变化。
- 一个 report artifact 一致性检查。
- 一个 ESP buffer sizing 或 Component Manager 版本约束问题。

每个问题独立，避免 V1 那样一个根因连坐太多分。

### 7.4 标准化 ESP build

ESP 建议硬性要求：

- 必须使用提供脚本。
- 必须保存 build log。
- 如果失败，必须写明失败阶段和下一步。
- static pass 不能替代 build pass。
- 评审时单独记录“真实 build 通过/失败/未统一复跑/用户确认”。

### 7.5 分离三类分数

建议每个模型以后记录三列：

- **Final-code score**：最终代码能力。
- **Autonomy/process score**：是否自己跑通、是否需用户救场、是否遵守脚本。
- **Cost/efficiency note**：token、调用次数、上下文压缩、工具限额。

这样 GLM 这类“最终代码强但 Qoder 过程差”、Mimo 这类“效率优秀”、Minimax M2.5 这类“数字好看但可信度差”就能分开。

## 8. 最终判断

第一轮有效地证明：弱提示下，模型主动发现真实项目问题的能力差异很大。  
第二轮有效地证明：给出更清楚的现象和 workflow 后，中游模型能做得多很多，但前沿模型仍会在安全边界、迁移、ESP build 和报告一致性上拉开。

如果只看“真实项目里用户给一句很弱的话”，V1 更贴近。  
如果看“工程团队给出 bug 现象，让模型完成一轮迭代”，V2 更贴近。

目前最有价值的结论是：

- GPT-5.5 是当前两轮里最完整、最能收口的模型。
- GPT-5.4 仍强，但 V2 中明显低于 5.5。
- Doubao、GLM、Mimo、Minimax M3、DeepSeek Flash 组成强第二梯队，但都还会漏关键隐私或部署边界。
- Gemini 3.5 Flash 在 V1 弱提示下很亮眼，V2 反而没有明显继续提升。
- 某些模型会刷出不错的 hidden/static 数字，但 public/build/report 一核查就露出不可信，这类必须靠人工 rubric 压住。

下一步不需要立刻再全量测一圈。更合适的是用 V3 针对 78-88 这批接近模型做小范围复测，专门拉开中游和第二梯队内部差异。
