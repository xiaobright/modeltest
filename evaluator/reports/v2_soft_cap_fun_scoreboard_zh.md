# Project2 V2 软上限娱乐榜

更新时间：2026-07-09

这份是专门给“斗蛐蛐”看的娱乐榜，不替代正式榜，也不替代单模型评测记录。正式榜负责严肃判定“这东西能不能接收”；娱乐榜负责回答另一个更朴素的问题：

> 如果不把一个高危 bug 直接变成天花板，而是当作重大扣分项和发布阻断项，谁的实际工程完成度更强？

本榜没有重新跑模型，也没有重新跑测试。所有分数都来自已经存档的 review、hidden/static 结果、编译证据和人工评语。换句话说，这是“基于现有战报的重新排位”，不是一次新的正式评测。

## 玩法说明

正式榜里，`sensitive context fallback` 这类问题会直接把很多模型卡在 82。这个规则很适合判断发布风险，因为隐私边界没修好确实不能上线。

但拿来排娱乐榜就有点憋屈：有的模型其他地方做得很完整，只是撞了这个高危点；有的模型同样 82，但旧库迁移、ESP、报告都更乱。整数分一压，强弱就挤成一团。

所以娱乐榜采用“软上限”：

- 大多数高危 bug 不再直接封顶，而是保留原始扣分，并标记为发布阻断。
- 真正影响评测可信度的问题仍然硬压，比如 public 测试失败、固件真实编译失败还声称成功、报告明显甩锅、核心鉴权大面积绕过。
- 分数不是严格数学重算，而是基于既有 subtotal 和人工记录做的娱乐排位。
- 这份榜只看完成度和交付形状，不统一考虑价格、渠道福利、额度、速度。

## 阻断标签

- **S**：敏感上下文/会话授权问题，隐私边界没收住。
- **M-crash**：旧数据库迁移会直接崩。
- **M-fidelity**：旧数据能活，但时间戳、排序或语义不完整。
- **E-build**：ESP-IDF 真实构建失败，或构建证据不可信。
- **E-contract**：固件能做/能编，但协议、依赖或静态契约不够干净。
- **P-report**：报告不够准，漏写验证，或者有过度自信。
- **F-public**：公开测试失败，而且失败点在自己碰过的业务逻辑里。

## 娱乐榜单

| 名次 | 模型 | 渠道 | 正式分 | 娱乐分 | 档位 | 主要标签 | 赛后锐评 |
|---:|---|---|---:|---:|---|---|---|
| 1 | GPT-5.5 | Codex | 96 | 96.0 | S 级 | 小 reason-code 瑕疵 | 第一还是第一，收尾能力明显领先，基本属于把题打穿了。 |
| 2 | Grok-4.5 | 当前工作区渠道 | 96 | 95.7 | S 级 | 小 reason-code、报告格式小扣 | 这次不是 4.3 那种梦游局了，33/34 hidden、8/8 ESP static、真实编译两次过，马斯克这回至少在这题上没白吹。 |
| 3 | GLM-5.2 | Opencode/API | 95 | 95.0 | S 级 | 小 reason-code、E-contract | 国产满血最强样本，backend 收得非常干净，离第一梯队只差最后几颗螺丝。 |
| 4 | GLM-5.2 | 火山引擎 / Opencode | 89 | 88.9 | A 级 | M-crash、E-contract、P-report | 强是真的强，32/34 hidden、7/8 ESP static，但旧库迁移一脚踩空，离满血 95 差的就是这口气。 |
| 4 | GPT-5.4 | Codex | 88 | 88.3 | A 级 | M-crash、E-contract | 没有 5.5 那种终局清扫能力，但主体很稳，顶级守门员。 |
| 5 | Kimi K2.7 Code | Opencode/API | 82 | 88.0 | A 级 | S、M-fidelity | 娱乐榜最大翻身仗。正式榜被 82 卡住，但固件、构建、主线修复都很硬。 |
| 6 | GLM-5.2 | WorkBuddy | 88 | 87.8 | A 级 | M-crash、E-contract、P-report | 渠道版依然强，但明显没打出 API 那个 95 的满血状态，也略低于火山/Opencode 这一局。 |
| 7 | doubao-seed-2.0-code | Opencode/API | 86 | 86.0 | A- 级 | M-crash、E-contract | 这轮提升很猛，backend 打得漂亮，ESP 形状拖了后腿。 |
| 8 | GLM-5.1 | Qoder | 82 | 86.0 | A- 级 | S、P-report/工具干预 | 正式榜憋在 82，娱乐榜给它松绑。final-code 很能打，但 Qoder 过程实在折磨。 |
| 9 | Mimo v2.5 Pro | Opencode/API | 82 | 85.0 | B+ 级 | S、M-fidelity、P-report | 效率型选手，跑得快、覆盖广，输在高阶隐私边界和迁移细节。 |
| 10 | LongCat-2.0 | 当前测试渠道 | 82 | 84.5 | B+ 级 | S、E-contract、P-report | 后端主线、旧库迁移和真实构建都挺稳；但隐私门没关严，ESP 契约少几颗钉子。 |
| 11 | DeepSeek V4 Flash | Opencode/API | 82 | 84.0 | B+ 级 | S、M-crash | Flash 反杀 Pro 的代表场。固件和真实 build 很漂亮，旧库迁移崩得有点痛。 |
| 12 | Minimax M3 | WorkBuddy / medium thinking | 82 | 84.0 | B+ 级 | S、M-fidelity、E-contract、reason-code 噪声 | 数字冷，实际不丑。很多失败是 reason 字符串太花，旧库从崩溃变成保真问题，能打但没打穿。 |
| 13 | Composer 2.5 | grok-cli | 82 | 83.5 | B 级 | S、M-crash、E-contract、P-report | 跑得是真快，ESP 也不是糊弄；但隐私门和旧库迁移没收住，属于很顺手但没破墙。 |
| 14 | GLM-5.1 | WorkBuddy | 82 | 83.0 | B 级 | S、M-crash、E-contract | 工具体验比 Qoder 好很多，但最终代码没 Qoder 那版干净。 |
| 15 | Minimax M3 | Opencode/API | 82 | 83.0 | B 级 | S、M-crash、E-contract、P-report | 报告和过程很像样，代码收口差一口气，迁移和 ESP 形状比较伤。 |
| 15 | Gemini 3.1 Pro | Antigravity | 80 | 80.0 | B- 级 | S、M-fidelity/schema、E-contract | 很稳的中上游，能做大面，但细边界和迁移没进 82+ 区。 |
| 16 | Kimi K2.6 | Qoder | 80 | 80.0 | B- 级 | S、E-contract/process、工具压缩问题 | 能力不弱，但 Qoder 的状态保持把观感拉低了。 |
| 17 | Gemini 3.5 Flash | Antigravity | 79 | 79.0 | C+ 级 | S、M-fidelity、care_event API gap、P-report | 固件好看，backend 细活差点意思。 |
| 18 | Kimi K2.6 | WorkBuddy / medium thinking | 78 | 78.5 | C+ 级 | S、M-crash、care_event gap、E-contract、P-report | 便宜是真便宜，但这局代码没打赢 Qoder 版 K2.6，属于性价比赢、榜单输。 |
| 19 | DeepSeek V4 Pro | Opencode/API | 78 | 78.0 | C+ 级 | S、M-crash、E-contract | 后端有实力，但这轮不如 Flash 利索，ESP 和迁移都没收住。 |
| 20 | Qwen3.7 Max | Qoder | 74 | 74.0 | C 级 | S、M-crash、sleep/care gap、E-contract | 很努力，但错过的核心点太多，阿里自家工具也没给它兜住。 |
| 21 | Mimo v2.5 Flash | Opencode/API | 72 | 72.0 | C- 级 | S、M-crash/missing、E-build、P-report | public/debug 看着不错，真实编译和报告可信度把分压下来了。 |
| 22 | Minimax M2.5 | Opencode/API | 66 | 66.0 | D 级 | F-public、S、E-build、P-report | 典型刷分脸：hidden/static 不难看，但 public、编译、报告一起掉链子。 |

## 82 档解冻之后发生了什么

正式榜里最拥挤的是 82 分附近。软上限一放开，这一档立刻分成几层：

- **Kimi K2.7 Code：82 -> 88**  
  最大受益者。它不是“只有 82 的水平”，而是被敏感 context cap 压住了。ESP static 8/8，真实 ESP-IDF build 通过，admin/auth 和 sleep 都完整，整体完成度很强。

- **GLM-5.1 Qoder：82 -> 86**  
  final-code 很漂亮，旧库迁移和 ESP static 都保住了。正式榜被隐私边界封顶，娱乐榜里能看出它其实比很多 82 更扎实。

- **Mimo v2.5 Pro：82 -> 85**  
  速度、上下文控制、工程覆盖都很好。它没有 GLM-5.1 Qoder 那么完整的迁移保真，但整体很干练。

- **LongCat-2.0：82 -> 84.5**  
  新来的美团选手不是来凑数的：public/debug、旧库迁移、Windows ESP-IDF 构建都过了。问题是 sensitive context 这个门没关严，ESP static 又只到 5/8，所以娱乐榜能抬一截，但正式榜不能放它出 82 笼子。

- **DeepSeek V4 Flash：82 -> 84**  
  固件和真实 build 很强，但旧 DB migration 是崩溃级问题，所以娱乐榜也不能给太高。

- **GLM-5.1 WorkBuddy / Minimax M3：82 -> 83-84**  
  都有广度，也都有硬伤。WorkBuddy 的过程更舒服，Minimax 的报告更像样，但最终代码都被 migration 和 context 拉住。

## GLM-5.2 三个样本怎么读

GLM-5.2 现在有三个 V2 样本：

- **Opencode/API：95**  
  目前最强非 GPT 样本，backend 基本全收，旧库迁移也过了。这个更像模型本体上限。

- **火山引擎 / Opencode：89**  
  public/debug 全过，hidden 32/34，ESP static 7/8，真实 Windows ESP-IDF v6.0.1 构建你已确认通过。它比 WorkBuddy 版更像一个强渠道样本，但旧 DB migration 还是启动崩溃，所以被卡在 89。

- **WorkBuddy：88**  
  也很强，但 ESP static 6/8，旧 DB migration 同样崩。它的意义更多是工具/渠道对照：好用、便宜、更新快，但不能替代满血 API 能力基准。

一句话：GLM-5.2 的上限看 95，渠道稳定性看 88-89。它不是弱，是不同渠道打出来的收口细节不一样。

## 渠道小结

**Qoder**：  
GLM-5.1 的最终代码其实不错，说明模型不是不能打。但 Qoder 的压缩和状态保持问题太明显，之前出现过忘工作区、忘脚本、忘 ESP-IDF 环境这类情况。它适合拿免费额度测，但不适合作为“模型满血能力”的唯一证据。

**WorkBuddy**：  
GLM-5.1 过程比 Qoder 顺很多，压缩后还能继续写 PR，体验明显更稳。问题是 GLM-5.2 WorkBuddy 到 88，而 API 到 95，说明这个渠道未必是满血模型表现，更像是“好用、便宜、更新快，但能力基准要打折看”。Kimi K2.6 WorkBuddy 约 500 积分、0.7x，折算基准用量约 714，确实省；但代码结果弱于 Qoder K2.6。Minimax M3 WorkBuddy 约 900 积分、0.25x，折算基准用量约 3600，属于“单价便宜但跑得太铺开”，总价反而不低。

**Opencode/API / Opencode 渠道**：  
更适合作为能力基准，变量少一些，但钱包疼。GLM-5.2 API 的 95、火山/Opencode 的 89、Kimi K2.7 API 的 82/88 娱乐分，都更适合看模型本体或渠道的实际上限。

**Codex**：  
GPT 两个样本仍然是最强对照。5.5 明显强于 5.4；5.4 也够强，但迁移收口差了一截。

## 这份榜该怎么看

如果你问“哪个结果最能放心接收”，看正式榜。  
如果你问“哪个模型实际打出了更多有效工作”，看这份娱乐榜。  
如果你问“哪个模型最值得继续花钱测”，优先看娱乐榜前几名和渠道备注。

这份榜最大的结论是：

- 82 档不是一群完全一样的模型，而是被同一个高危隐私 bug 挤扁了。
- Kimi K2.7、GLM-5.1 Qoder、Mimo Pro、DeepSeek Flash 的实际完成度差距是存在的。
- GLM-5.2 的渠道差异也是真实存在的：95、89、88 三个样本说明满血上限和工具/渠道结果不能混看。
- WorkBuddy 可以作为实用渠道，但暂时不能替代 API 满血基准。
- Qoder 对第三方模型有明显工具拖累，尤其是长任务压缩后的连续性。
- GPT-5.5 和 GLM-5.2 API 仍然是这轮 V2 里最像“能打完还能收拾战场”的两个结果。

最后一句娱乐判词：

> 正式榜管上线，娱乐榜管嘴硬。  
> 82 分不是终点，只是很多模型撞在同一堵墙上留下的形状。
