# Project2 V5 远期设计方向

**状态：** 远期方案 / 想法台账，未立项，暂停实施  
**首次记录：** 2026-07-12  
**最近整理：** 2026-07-19  
**当前正式基准：** V4.1b formal stable baseline；V4.0 frozen archive / V4.1a 历史锚点  
**结论来源：** V4/V4.1b 正式成绩、V2 对照、multi-run、成本记录、操作者过程观察；2026-07-14 对  
`myproject/project`、`project2`、`project3` 与 live bug 知识库的真实缺陷考古

> V5 不是近期开发计划。V4.1b 已足以承担当前模型评测；在预算、时间和新增样本不足时，
> 不启动题库、评分器或 broken seed 改造。
>
> **2026-07-18：** V4.0 已完整归档于 `archives/v4_round_final_20260718/`。V4.1a 仅处理
> F6 级联观测与 multi-run 协议，**不**把新鲜度 / session 抢占 / QEMU / HIL 提前塞进主榜。
>
> **2026-07-19：** V4.1b 锚点闭环并成为正式稳定基线。当前经验是 Ability >=95 且
> 无严重 Ship blocker 已足以覆盖日常开发，Ability >=90 已可承担实现工作。现在没有
> 区分 96/98/99 的实际需求；顶部拥挤、最后一分或免费模型福利都不构成 V5 立项理由。

本文是可持续追加的 living memo，不是 frozen spec、实施 handoff 或排期承诺。后续发现
新的真实 bug、环境问题、硬件方案或成本证据时，先补入本文，等真正立项后再收敛成
可执行设计。当前想法允许演化，但不应无记录地被后来的结论覆盖。

## 1. 为什么暂不启动

V4.1b 已完成本轮核心目标：拆除 V2 的 82 分硬墙，建立 Ability/Ship 双轨，修复 F6 与
ambient 级联，并用更可信的迁移、隐私、multi-run 和真实 build 证据解释模型。继续改版
的即时收益已经低于实施和复测成本。

V4.1b 的最终使用判断是：95 分以上且无严重 Ship blocker 的模型对当前日常项目已没有
实质能力焦虑；90 分以上的模型也可堪使用，只需按失败 family 做终审。当前没有业务
负载要求进一步区分顶部模型，因此 V5 的价值必须来自未来真实问题，而不是排行榜分辨率。

本轮还显示：高思考预算会显著增加时间和费用，但未稳定转化为更高工程完成度。

| 单次观测 | high | xhigh | 边际结果 |
|---|---:|---:|---|
| GPT-5.6-sol | 98 / 13 min / $3.49 | 99 / 24 min / $7.25 | +1 分，时间 +85%，成本 +108% |
| GPT-5.6-luna | 98 / 18 min / $1.29 | 99 / 24 min / $2.11 | +1 分，时间 +33%，成本 +64% |
| GPT-5.6-terra | 97 / 15 min / $2.01 | 95 / 24 min / $4.00 | -2 分，时间和成本均增加 |

这些是单次运行，不足以证明稳定规律，但足以否定“预算越高必然越好”的默认假设。
在拿不到原始思维链的前提下，只能把额外消耗描述为未转化为可观察成果的推理、搜索
或执行路径方差，不能直接断言模型在内部完全空转。

## 2. V5 要解决的问题

V5 家族若在远期重启，只聚焦三个 V4.1b 尚未充分回答、且已在真实开发中产生实际损失
的问题：

1. **新工作负载能力**：现有高分模型是否在真正跨模块、高耦合、带故障和历史状态的
   工程闭环中出现了 V4.1b 无法预测的失败。没有真实失败证据时，不为了顶部排序造题。
2. **代理执行效率**：更多思考预算带来的时间和 token 是否转化为有效编辑、验证覆盖和
   更高成功率，而不是重复表述、延迟工具调用、无状态变化回合或过度修补。
3. **嵌入式真实闭环**：模型能否跨 C/C++、Python、工具链、协议和设备状态定位根因，
   同时避免把测试台自身的随机故障误算成模型能力。

V5 不以重新拉开中游或顶部模型为目标，也不因 95–99 拥挤而推翻 V4.1b 已验证有效的
主骨架。高耦合场景首先服务于真实开发风险覆盖，区分度只是校准结果，不是立项目的。

## 3. 建议结构：V4.1b 基线 + V5 / V5 HIL

V4.1b 收口后，原先设想的 V5 标准层已无独立问题可回答：日常软件模型选型、Ability/
Ship 解释和 90/95 档位判断均可继续由 V4.1b 承担。远期命名因此由三级收敛为两级：
原 **V5 Pro** 提升为 **V5**，原 **V5 Pro Max** 改称 **V5 HIL**。

| 层级 | 核心问题 | 主要环境 | 运行对象 |
|---|---|---|---|
| **V4.1b** | 当前日常模型能否可靠完成项目改造 | Python/host tests + ESP build | 日常选型基线与按需新增样本 |
| **V5** | 能否解决跨语言、高耦合嵌入式闭环 | C/C++ + Python + 协议回放 + QEMU | 少量有明确研究价值的模型 |
| **V5 HIL** | V5 提交能否在真实设备上完成验证、诊断和恢复 | 固定 ESP32 HIL 测试台 | 少量 V5 候选 |

V5 不再被预设为 V4.1b 的常规换代或规模化新主榜，而是有真实盲区证据后才启动的
高耦合 capstone。V5 HIL 不是更大的另一套题库，而是复用同一提交的真机认证/调试
profile。两者的区别主要是证据等级，不是营销式难度后缀。旧结果保持冻结，不跨版本
回填或重算。

### 3.1 保留 V4.1b 主标尺

- 保留 Ability/Ship/Class 双视图和行为 blocker。
- 保留 V4.1b 的 F1–F12、Gold、证据链和冻结结果作为回归基线。
- 不把 V5 新题临时塞入 V4.1b 的 100 分，也不重算历史正式成绩。
- 冻结后发现 evaluator bug 时另发修订说明或升版本，不静默改写正式结果。

### 3.2 V5：独立高耦合 Capstone

若真实开发证明有必要，先用一个独立 capstone 研究高耦合闭环，不与 V4.1b Ability
相加，也不做十几个零散新题。候选方向包括：

1. **故障降级隐私摘要**：旧 schema、缺损 sensor、可用 sleep 和合法 voice session
   同时存在时，系统可用但零泄漏，并明确报告 degraded 状态。
2. **端到端护理闭环**：fake sensor payload 经 gateway、bed mapping、care_event、context
   到 voice；授权路径可见，ambient、无 actor 和跨患者路径零泄漏。
3. **离线重放幂等**：重复 payload 不重复写事件，latest、排序、历史保真和报告证据一致。

详细候选及 oracle 见
[`v4/archive/original_design/CAPSTONE_ITEM_IDEAS.md`](./v4/archive/original_design/CAPSTONE_ITEM_IDEAS.md)。

每个 capstone 必须按行为拆分部分得分，避免一个早期失败连坐整条链；hidden test 只验证
可观察状态，不锁定函数名、模块边界或具体实现方式。

### 3.3 真实项目素材来源

本机另一个真实原型分支 `E:\Desktop\myproject\project` 可作为 V5 素材库。它在现有
评测壳之外增加了双 ESP 节点、端侧睡姿推理、TCP 二进制协议、数据新鲜度、板端
ASR/RKLLM/TTS、视觉弱提示和 companion 事件投递。

优先复用真实缺陷，不重新虚构题目：

| 来源提交/模块 | 可提炼的 V5 场景 | 主要耦合 |
|---|---|---|
| `b35cef1^ -> b35cef1` | **数据新鲜度真值链**：设备停止更新后，不得把旧心率、睡姿或鼾声重新盖新时间戳并播报成当前状态 | Arduino 固件 -> TCP ingest/store -> context -> voice |
| `b35cef1^ -> b35cef1` | **不可信传感器流安全**：超长/截断 UART 帧不得越界；单路 MLX 失败不得发布未初始化数据或刷新 freshness | UART parser -> driver -> shared state -> inference gate |
| `b35cef1^ -> b35cef1` | **流式输出隐私状态机**：`<think>` 等标签跨任意 chunk 边界时均不得进入 TTS | RKLLM stream -> filter state -> sentence pipeline -> audio sink |
| `b35cef1^ -> b35cef1` | **投递真实性**：socket write、设备确认和 companion cooldown 不能把失败伪装成成功 | gateway downlink -> connection lifecycle -> event retry/cooldown |
| `2585213^ -> 2585213` | **干净构建可复现**：无 `build/`、无 managed cache、无网络时仍可由锁定源码构建 | manifest -> vendored component -> ESP-IDF 6.0.1 build |

首选 capstone 仍是“数据新鲜度真值链”。它来自真实问题，跨设备、网关和最终用户话术，
同时包含时间、失败状态和信息真实性；价值在于覆盖真实风险，而不是保证拉开高分模型。

**2026-07-14 补记（残余缺口仍开放）：** `b35cef1` 已修 Arduino 用新 `ts` 重盖旧
心率、store clamp/prune-on-read 与部分 voice 空字典防护，但 live 仍有：
`build_voice_sleep_context` 在雷达/环境/音频非空时易标 `live` 而未强制 `vitals_valid`
与模态 TTL；posture 上下文无 emotion 级 freshness；voice 在字段存在时仍可能把
“鼾声 0 / 未离床”说成当前事实。V5 应把这些**残余**与 `b35cef1^` 可注入缺陷
一并设计进 oracle，而不是假设 `b35cef1` 后链路已完美。

这些提交只能作为出题证据和 Gold 参考，不能直接把整个分支及完整修复 diff 交给被测
模型。制作 seed 时应裁掉无关大模块，并重新检查许可证、路径、凭据和答案泄漏。

### 3.4 V5：QEMU 的位置

QEMU 用于填补 host test 与真机之间的系统级空白，而不是替代真机。Espressif QEMU
当前可覆盖 ESP32-S3 CPU、UART、flash、PSRAM、eFuse、部分 timer/watchdog、硬件加密
和虚拟 OpenCores Ethernet；不覆盖真实 Wi-Fi、I2C、RMT、GP SPI、I2S、USB 和 GPIO
matrix。因此它适合验证：

- 固件 boot、FreeRTOS task、panic/backtrace、栈/堆和 watchdog；
- flash image、分区、UART 坏帧注入、协议编码和 GDB 定位；
- 通过 OpenEth 或 host bridge 验证 TCP 状态机；
- 在 fake sensor adapter 下运行正式 parser、freshness、推理门控和上报逻辑。

QEMU 专用适配只能替换最底层硬件接口，不得复制另一套业务逻辑。MLX90640 的 I2C、
WS2812 的 RMT、真实 Wi-Fi 和传感器电气/噪声问题仍需 V5 HIL 验证。

参考：[`ESP-IDF QEMU 指南`](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/tools/qemu.html)、
[`Espressif QEMU 支持表`](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md)、
[`ESP32-S3 QEMU 说明`](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/esp32s3/README.md)。

### 3.5 V5 HIL：环境与实机验证

环境配置、依赖诊断、烧录、串口观察和板端调试本身都是嵌入式工程能力。纯 build 在
当前模型中已接近饱和，只保留编译题难以继续拉开上限；但真机每轮成本高、状态混沌，
不适合作为所有 V5 样本的硬门槛。V5 HIL 只对少量有明确验证价值的 V5 提交运行。

| 层级 | 验证 | 建议用途 |
|---|---|---|
| E0 | 从明确的基础环境启动，识别/激活 ESP-IDF，解决项目依赖和离线组件问题 | 环境与工具能力 |
| H0 | 主机侧 parser/protocol/state-machine 测试，fake payload 和 fake clock | 软件回归基础 |
| H1 | 干净 ESP-IDF v6.0.1 build，保存固件、size、SHA256 和日志 | 固件构建能力 |
| H2 | 自动发现指定板卡，执行 flash，抓取含固件版本的启动日志 | 烧录与启动能力 |
| H3 | 串口运行诊断：panic、watchdog、栈/堆、传感器初始化、重连 | C/C++ 板端调试能力 |
| H4 | 板端发送真实或可控注入数据，Gateway 收包，Python 状态与最终 voice/context 一致 | 跨语言端到端能力 |

V5 HIL 应复用 V5 的同一份任务和提交，避免又长出一套不可比较的新题。结果至少
区分：

- **HIL Verified**：V5 提交未经修改，直接通过真机闭环；
- **HIL Debugged**：首次失败，模型根据真机日志和受控重试最终修好；
- **HIL Failed**：测试台健康，但在预算/重试上限内未完成闭环。

Verified 与 Debugged 都有价值，但含义不同：前者证明软件/QEMU 与真机一致，后者测量
真实嵌入式调试和恢复能力，不应压成同一个 pass。

远期固定测试台可包括：

```text
控制主机
|- USB-UART / USB-JTAG：flash、monitor、DTR/RTS
|- 可控 USB Hub 或继电器：单端口断电与恢复
|- ESP32-S3 DUT：被测固件
|- 第二块 ESP32/RP2040：UART/I2C 数据与故障注入
`- Gateway：TCP 收包、状态断言和结果归档
```

测试台对模型提供受控命令，例如 `preflight`、`power-cycle`、`enter-bootloader`、`flash`、
`monitor`、`inject-fault` 和 `assert-gateway`。RST/BOOT/电源控制应使用标准自动下载电路、
晶体管/隔离或可控 Hub，不让模型依赖人工按键。

为了让 HIL 失败仍可公平归因，运行前先由 evaluator 执行与候选无关的 bench preflight：

- 固定板卡、线材、供电、传感器或故障注入器，并记录 USB/串口身份；
- 用已知 Gold 固件完成一次 flash、boot 和最小收包，证明测试台健康；
- 候选运行期间保存命令、串口、网络、固件 hash 和时间线到 result-local 目录；
- 明确区分 `candidate_fail`、`bench_fail` 和 `skipped_env`，bench 自身失败不得伪装成模型失败；
- 给候选有限但真实的重试机会，观察其是否会根据日志形成“修改 -> 重编译 -> 烧录 -> 验证”闭环。

当前盘点时机器未发现串口设备，因此只确认已有 ESP-IDF build 产物，不能把它误记为
实机验证结果。V5 HIL 真正启动前，应先把固定硬件测试台和 preflight 脚本做好。

### 3.6 分语言与集成维度

总分之外单独报告以下维度，避免强 Python 模型用网关得分掩盖薄弱固件，也避免强 C/C++
模型因上层细节被看成整体弱：

- **Firmware C/C++**：内存安全、任务同步、驱动有效性、watchdog、资源预算；
- **Host Python**：协议解析、状态存储、TTL、重试、API 和用户话术；
- **Environment/Tooling**：工具链发现、依赖处理、干净构建、flash/monitor 操作；
- **Hardware Integration**：板端启动、传感器状态、网络重连、上下行协议；
- **End-to-End Closure**：跨 C/C++ 与 Python 的 schema、时间语义、失败状态和最终行为一致。

V5 的能力证据应主要来自 QEMU/End-to-End Closure，V5 HIL 再验证 H2-H4；不能
继续依靠通过反复编译即可收敛的静态 marker 拉分。

## 4. 效率不进入 Ability，单独报告

成本和速度不应污染代码能力分，但应成为正式结果的一等视图。每次运行至少记录：

- model、provider、endpoint product、billing tier、harness、thinking level；
- 新增输入、cached input、输出和 reasoning token；
- 实际成本、零缓存估算、理想缓存估算、总时长；
- 首次工具调用、首次有效编辑、首次有效测试的时间；
- 重复文本回合、无状态变化回合、失败重试和重复读取次数；
- 最终 Ability、Ship、Capstone、public/hidden/build 结果。

建议派生指标：

- 达到 A/B+ 的成功成本，而不只是单次 CPI；
- `high -> xhigh` 每提升 1 分的边际时间和成本；
- 有效工具回合占比、首次有效编辑延迟；
- 同配置多次运行的均值、范围、失败率和成本方差。

不保存或推测原始思维链。执行效率只根据外部可复核事件判断。

## 5. 实验设计与成本控制

V5 应分阶段推进，任一阶段不成立就停止：

1. **素材积累**：只记录真实 bug、日志、修复前后提交和环境，不立即造题。
2. **V5 作者验证**：只做一个高耦合 capstone，用 Gold、broken seed、软件回放和 QEMU
   验证 oracle、归因边界与运行成本。
3. **V5 小样本试测**：一个顶部、一个中游和一个低档样本，确认它确实提供 V4.1b
   无法解释的新信息；不为形成全模型矩阵而扩样。
4. **V5 HIL 预研**：Gold 固件先通过固定测试台，之后只验证少量有研究价值的 V5 提交。
5. **有限转正**：V5 或 HIL 只有能回答独立问题且证据可归因时，才建立结果视图。

预算规则：

- 开工前预设总费用和总工时上限；达到上限即停止，不靠追加样本救设计。
- 优先复用 frozen 提交做离线 replay，不要求所有历史模型重新生成代码。
- 先跑便宜渠道和 high 档验证题目，再决定是否购买 xhigh 样本。
- 不做全模型矩阵；只选择能回答明确假设的最小样本集。
- V5 与 V5 HIL 分开核算预算，不因已经投入 V5 而默认继续投入真机验证。
- V5 HIL 必须设置单模型总时长、build/flash 次数和自动恢复次数上限，禁止无限调板。

## 6. V5 不应该做什么

- 不因 95–99 拥挤而增加更多拼写、marker、报告措辞和单点 hidden 细节。
- 不把时间短或价格低直接奖励进 Ability。
- 不用单次运行宣布 high 必然优于 xhigh，或宣布某渠道必然量化。
- 不要求或依赖不可获得的原始思维链来判定“空转”。
- 不同时加入多个新业务模型，导致无法定位分差来自哪条耦合链。
- 不在 V4 已冻结结果上做跨版本覆盖写入。
- 不把完整视觉、RKLLM、LoRA、两套 ESP 和全部传感器一次性搬入 seed，制造另一个真实项目。
- 不把宿主机偶发不认串口、必须重启等测试台事故包装成高质量环境题。
- 不把 QEMU 通过称为真机通过，也不让 QEMU 专用分支复制正式业务逻辑。

## 7. 重启条件

### 7.1 V5

1. 真实开发中重复出现重要失败，且 V4.1b 分数/Ship/family 无法预测或解释这些失败。
2. 已有一个高耦合 capstone 的行为 oracle、Gold 和 broken seed，并通过等价实现审查。
3. 软件回放和 QEMU 能运行正式核心逻辑，不只验证模拟专用代码。
4. 三个最小校准样本证明它比 V4.1b 顶部细节分提供了新的能力信息。
5. 单轮时间和成本在预设上限内，且不需要形成全模型矩阵。
6. 新场景能回答 V4.1b 无法回答的问题，而不是为了版本号重跑。
7. 能保存完整 token、缓存、成本和外部执行事件数据。
8. 已确定固定重复次数、校准锚点、费用/工时预算和停止条件。
9. 题目价值在不考虑模型排名时仍成立；顶部拥挤或最后一分不足不能单独触发立项。

### 7.2 V5 HIL

1. 固定测试台能自动 preflight、flash、monitor、断电恢复和归档 result-local 证据。
2. Gold 固件可连续重复通过，`candidate_fail` 与 `bench_fail` 有清晰归因。
3. V5 提交可直接进入真机验证，不需要维护另一套任务代码。
4. 已证明真机结果提供 QEMU 无法替代的信息，值得额外人工、设备和时间成本。

## 8. 暂定决策

- **现在：** V4.1b 收工并作为正式稳定基线；95+ 视为当前日常可靠完成档，90+ 视为
  可用执行档，结合 Ship/family 决定审查强度。
- **短期：** 不开发 V5 或 V5 HIL，不新增正式题，不搭建硬件测试台，不启动大规模复测。
- **积累方式：** 遇到真实 bug 时只保存最小证据，不要求立即加工成评测题；2026-07-14
  已完成一轮三仓考古，结果写入 §9.8，**仍不建 seed / 不改 evaluator**。
- **未来顺序：** 先由真实开发证明 V4.1b 存在重要盲区，再判断 V5 capstone 是否有
  必要；不先造一套与 V4.1b 重叠的新主榜。只有 V5 证明真机信息不可替代，才评估
  V5 HIL 测试台。

**2026-07-14 已确认的产品边界（操作者确认，仍属 memo 非 frozen spec）：**

1. **主轴：** 数据新鲜度真值链 + session 显式性（时间/来源真值，而非更多 auth marker）。
2. **场景来源：** V5 高耦合主场景使用 **project 家用线**的最小切片（`b35cef1` /
   `2585213` 及父提交），并按需引用 **project2 医院壳**的 context/session 经验；
   project2 的可规模化 host 题只作独立辅助 fixture，不再组成一套标准 V5 主榜。
3. **已修缺陷可再注入：** sleep 默认 `first`、缺 import 等允许作为 V5 辅助 regression，
   并在题面/registry 标明 `regression` 与修复 commit。
4. **PlanExec 控制面假证据：** 独立 capstone，**不进 V5 Ability 主榜**（见 §9.6）。
5. **project3 双 ESP：** 只记素材与历史固件坑，**不**作为 V5 第一阶段 seed；若未来
   做 V5 后续场景时再单独立项。

一句话概括：

> V4.1b 继续负责日常软件模型选型，V5 只研究有真实依据的高耦合嵌入式闭环，V5 HIL
> 复用同一提交做真机验证和调试；新增证据不值得新增成本时，就停留在上一层。

## 9. 后续想法台账

### 9.1 已收敛方向

- V4.1b 保持正式稳定；远期若立项只使用 V5 / V5 HIL 两级命名。
- V5 不自动替换 V4.1b，而是独立高耦合研究；V5 HIL 是少量提交的真机认证/调试
  profile，不做全模型硬件矩阵。
- 首选真实主线是“数据新鲜度真值链”，核心是不把旧、坏、未确认数据说成当前事实；
  **并列主轴**是 session 必须可显式绑定，禁止全局 current-session 静默抢占。
- V5 主场景默认使用 **project 切片**，project2 提供 context/session 经验和辅助 host
  fixture；project3 双 ESP 仅素材台账。
- 已修真实 bug 允许再注入为 regression 题；未修残余（新鲜度话术、session 抢占）
  优先作开放产品缺陷题。
- PlanExec 控制面缺陷独立 capstone，不进 V5 Ability。
- 环境安装、C/C++、Python、协议和实机调试都是能力，但需要分维度和做故障归因。
- 软件模拟解决规模，QEMU 解决系统级固件问题，真机负责发现模拟器覆盖不到的问题。
- 高思考预算的边际收益必须结合成本、时间和重复运行判断，不能默认 xhigh 最优。
- 95–99 的继续细分不是当前需求；未来新题必须先证明真实工程价值，再谈区分度。

### 9.2 尚未决定

- 从 V4.1b 或真实项目选择 V5 候选时，采用 Ability、Class、指定 family 通过，还是
  按研究问题直接抽样。
- V5 是独立分数、通过级别，还是多维雷达；是否保留统一总分。
- V5 HIL 的 HIL Debugged 是否独立排名，还是只记录认证状态和过程指标。
- 故障注入板优先使用第二块 ESP32、RP2040，还是商业可编程测试设备。
- QEMU adapter 能做到多薄，是否值得为当前固件维护 OpenEth/fake sensor profile。
- 真机测试的最长允许时间、flash 次数、自动恢复次数和人工介入边界。
- V5 辅助 fixture 是否纳入 project2 的 Bemfa 垃圾行 / import 漏导等 wiring 小题，
  还是只保留跨模块题并把 wiring 降为 smoke。
- 双 ESP 融合陈旧标记是否在 V5 后续场景单独立项（第一阶段明确不做）。

### 9.3 V2 -> V4 模型排序反转的启发

V4 出现了有价值的排序反转：V2 中 GLM-5.2 整体较强，Kimi/Composer 表面分偏低；
V4 中 GLM 三个渠道集中在 81-82，而 Kimi K2.7 为 90、Composer 2.5 为 92。

还原后不能简单解释为模型本体此消彼长：

- Kimi K2.7 在 V2 的未封顶完成度本来约 88，正式 82 主要来自 ambient 硬顶；V4 的
  90 大部分是评分恢复表达能力，真实提升约 2 分。
- Composer V2 未封顶约 81-83，V4 迁移、no-actor、voice 和 ESP 均明显改善到 92，
  是较可信的真实运行质量提升样本。
- GLM V4 三渠道都有相同的 ambient（约 7 分，含 care context 连带）和 migration
  crash。把 ambient 加回后为 88-89，恰好接近 V2 非满血渠道；V2 的 95 来自硅基
  流动按量满血 API，V4 没有同 provider/product 的对应样本。
- V4 去除了 `api_contracts` 对 explicit session/current-session 的直接剧透。GLM 在明确
  契约下执行很强，但本轮没有主动推导出隐含 ambient 风险；Kimi/Composer 则更好地
  展示了广覆盖和全仓收口能力。

对 V5 的设计启发：

1. **分开测契约执行与风险发现**：同一能力可设置“明确契约题”和“只给症状的隐含契约
   题”，分别报告，不让一个混合总分掩盖模型画像。
2. **加入信息揭示梯度**：public 只给业务症状，reference 给必要边界但不命名解法；
   记录模型是在读到契约后执行，还是能从日志、调用链和失败状态主动发现根因。
3. **强调跨模块收口**：V5 capstone 应让局部正确仍不足以通过，必须同时闭合 firmware、
   gateway、context/voice 和迁移状态；但各子项仍独立计分，避免新的 hard cap。
4. **固定 provider 校准**：跨版本至少保留少量相同 model + provider + endpoint product +
   billing tier + harness 锚点；OpenCode 只表示 harness，不能替代 provider 身份。
5. **区分上限与渠道稳定性**：同模型应同时记录 best-known full-strength ceiling 和常用
   渠道分布，不能用免费/订阅端点的一次低分覆盖满血 API 上限。
6. **排序反转应视为诊断信号**：若新题改变排名，先检查硬顶、提示泄漏、provider 和
   family 权重，再讨论模型升级或退化；好的新版本可以重排模型，但必须解释重排来自
   哪类能力。

这也支持 V5 使用单一高耦合场景但输出多维画像：模型可能是强契约执行者、强风险
发现者、强全仓收口者，三者不应被默认视为同一种“强”。

### 9.4 真实 bug 最小捕获格式

平时开发仍以解决问题为主，不要求当场做 broken seed。遇到可能有评测价值的问题，只需
尽量留下：

```text
日期 / 一句话症状
hardware | environment | firmware | python | integration
出错命令或关键日志
修复前 commit / patch（能留则留）
修复后 commit
是否依赖真机，能否软件/QEMU 回放
```

后续立项时再从中选择可复现、可归因、区分度高的少数问题。散落在旧对话但回收成本
过高的历史问题默认不强行考古；真实项目负责解决问题，评测项目只把少数好问题加工成
稳定标本。

### 9.5 Migration 级联、权重与重复运行

V4 重跑进一步暴露了单次成绩无法表达稳定性的问题：Grok-4.5 两次均为 82，HY-3
WorkBuddy 与 Composer-2.5 则均由首跑 92 降至重跑 82。后两者除 F6 外的 family 结果
一致，10 分变化全部来自同一个顺序错误：在旧表补齐 `ts` 之前先创建依赖 `ts` 的
索引，导致数据库初始化崩溃。

F6 在 rubric 中已按“不崩溃/数据保留、补列、时间回填、幂等、混排”拆成
`3 + 2 + 2 + 1 + 2`，但五个 hidden test 共享完整初始化入口。单个初始化错误会让后续
语义全部无法观测，实际形成 0/10 或 10/10 双峰。旧数据库升级失败是合理的发布阻断，
但发布严重性不应自动等同于 Ability 中五种能力都被一个根因重复放大。

V5 若重做 migration 评分，应遵守以下规则：

1. **V4 保持冻结**：不事后修改 F6 权重，不用新规则重算历史正式成绩；重复结果另报
   run score、观测区间和关键 family 通过率。
2. **Ability 与 Ship 分工**：Ability 对独立迁移能力分项计分；完整旧库升级 crash 仍标
   `M-crash`，禁止 Class A，并保留严格的 Ship gate。
3. **拆执行前置条件而非只拆分值**：为补列/保留、时间回填、幂等和混排分别构造可独立
   到达的 legacy fixture，避免一个索引顺序错误遮住全部后续能力；同时保留一条完整的
   最老 schema 端到端升级测试。
4. **控制 Ability 权重**：若 migration 仍只覆盖一个表和一个升级入口，建议占 6-8 分；
   释放的分值优先给跨协议、数据新鲜度或跨模块状态一致性。若未来覆盖多版本 schema、
   事务恢复和回滚，再用实证提高权重。
5. **按根因解释级联**：报告既保留真实行为分，也标明多个 error 是否由同一启动根因
   引起，避免把一次局部顺序决策描述成十项独立能力缺失。

重复运行统计不得把两次结果的 10 分极差写成“方差 +/-10”。至少报告 runs、best、
worst、range 和 family pass rate；样本足够时再报告均值、中位数或标准差。一次运行是
`model + provider + harness + trajectory` 的交付样本，不直接等同于模型的稳定水平。

### 9.6 PlanExec 真实缺陷对 V5 的启发

固定规划执行评测框架的首次实现与两轮返修产生了一组真实控制面缺陷：Gold 校准曾进入
正式 handoff 根；scenario 哈希被记录但未在阶段边界验证；`.git` 内部状态污染内容哈希；
snapshot 和 evaluation 可在冻结后被修改；P1 计时从 freeze 而非 review 发布开始；P0
首次达到 B+ 的成本错误包含了未来 P1 费用；calibration 结果曾混入默认 aggregate。

这些问题不是语法错误，基础测试和主流程大多能够运行。共同模式是：

> 系统输出了看似完整的结果，但结果所依赖的来源、时间边界、模式边界或累计口径并不
> 真实。

这与 V5 首选的“数据新鲜度真值链”高度同构：评测器中的 seed/public packet/snapshot/
result，相当于真实项目中的 firmware payload/Gateway store/Context/Voice；两者都要求
来源、版本、时序和失效状态沿全链传递，不能把旧数据、校准数据或未来阶段数据伪装成
当前事实。

对 V5 的具体启发：

1. **模式隔离**：demo、calibration、fake sensor 和回放数据必须带来源并默认不能进入
   production Context/Voice；类似 Gold 不能进入 official handoff。
2. **端到端 provenance**：固件版本、协议版本、device/sequence/sample time、Gateway
   receive time、store schema 和最终话术应可关联；不能只在入口写一个版本字符串。
3. **内容与运行状态分离**：源码/协议内容 hash 不应被构建缓存或 Git 内部状态污染；
   runtime state、commit 和 artifact hash 分开记录。
4. **阶段边界按真实事件计时**：断连、重连、传感器失效、数据过期和恢复必须从实际事件
   发生时计时，不能从后续查询或保存日志时重新起算。
5. **首次成立语义**：某状态在 T0 已失效，不能被 T1 的新包倒灌成 T0 有效；类似 P0
   已达阈值的成本不能包含未来 P1。历史查询与 latest/current 必须分开。
6. **fail closed 与降级并存**：来源或版本不可信时，敏感事实与“当前状态”应 fail closed；
   系统本身可继续运行并报告 degraded，而不是整条链无差别崩溃。
7. **制品和报告同源**：build hash、测试结果、设备状态和最终报告应由结构化证据生成，
   避免代码已更新但 README/状态报告仍保留旧结论。
8. **mutation oracle**：通过篡改 payload/version/timestamp/cache/artifact 验证系统在正确
   边界拒绝，优先考行为不变量，不锁定模块名或唯一实现。

本轮还记录了 warm same-session 返修的实际成本。Luna 首次实现 `$2.28`，第一轮返修
`$2.70`，最终总消耗 `$7.14`，因此第三轮为 `$2.16`；两轮返修合计 `$4.86`，约占 Luna
总成本的 68%。加约 `$2.50` 一次性规划后为 `$9.64`，强审查成本另计。返修沿用重上下文
且中间间隔较长时会掉缓存，这不是应被清洗掉的噪声，而是真实工作流成本。

未来效率报告应增加：

- `repair_context_mode = warm_same_session | compacted_same_session | cold_handoff`；
- 返修开始时累计上下文、cache read/write、是否自动压缩或重建会话；
- P0 implementation、review delivery、P1 repair 分阶段时间和费用；
- 计划 one-off、按运行次数摊销，以及首次达到 B+/A 的累计成本。

正式主对照使用 warm same-session repair；cold handoff 只能作为可选成本实验，不能为了
得到更低价格替代真实开发流程。控制面缺陷本身放入独立 PlanExec capstone，不直接加入
V5 Ability；详细实施见
[`PLANEXEC_CONTROL_PLANE_SCENARIO_HANDOFF.md`](./PLANEXEC_CONTROL_PLANE_SCENARIO_HANDOFF.md)。

### 9.7 追加规则

- 新想法先追加到“尚未决定”或新增日期小节，不直接改成实施承诺。
- 有数据推翻旧判断时，保留旧判断的背景并记录为何改变。
- 真正开工前，另建 frozen design、rubric 和 implementation handoff；本文继续保留为
  决策历史，不直接充当运行契约。

### 9.8 2026-07-14 真实 bug 考古与 V5 题源台账

**状态：** 素材台账；不建 seed、不改 V4 evaluator、不立项施工。  
**方法：** 三仓 git 历史、`审查结果.txt`、`project2/docs/BUG_KNOWLEDGE_BASE.md`、
`ESP_MQTT_OPS.md`、ESP CHANGELOG、V4 ONBOARDING 与 PlanExec 控制面缺陷对照。  
**Gold 参考 commit（仅证据，不整仓投放）：** `project` 的 `b35cef1`、`2585213`；
`project2` 的 `6741d31`、`04ccc6c`、`d5ca482`、`e5f834a`。

#### 9.8.1 分层放题（与 §8 确认边界一致）

| 层 | 种子壳 | 题源重点 |
|---|---|---|
| V4.1b 基线 | project2 | 继续承担日常模型选型；不新增题、不重算历史结果 |
| V5 辅助 fixture | project2 | session 显式绑定、v3 隔离+voice 消费 policy、host 侧 mock 停更 freshness；wiring/regression 仅作辅助证据 |
| V5 capstone | project 切片 + project2 上下文 | **FRESH-1 全链**（优先）；可拆分子 oracle：STREAM-1、DELIV-1、UART-1/MLX-1 |
| V5 固件/QEMU 包 | `b35cef1^` / CHANGELOG 裁剪 | UART 越界、MLX 失败门控、ToF 帧头/meta、栈溢出 |
| V5 HIL | 同一 V5 任务与提交的真机验证 | H2–H4；bench preflight 区分 candidate_fail / bench_fail |
| 独立 | PlanExec | 控制面 provenance；**不进 Ability** |
| 仅素材 | project3 | 双 ESP 融合陈旧、UART0 污染、帧头坑；第一阶段不做 seed |

#### 9.8.2 优先题源（§9.4 最小捕获）

```text
ID: FRESH-1
日期: 2026-07-14 考古 / 原修复约 b35cef1 前后
一句话症状: 设备停更后，网关/语音仍把旧心率等说成“当前”
分类: integration | firmware | python
关键日志/行为: radar 仍周期性上报但 vitals 无效；context 标 live；voice 读出 HR
修复前: b35cef1^（Arduino 无 vitals_valid 仍刷新 ts；store/voice 侧缺口）
修复后: b35cef1 部分修复；live 仍有 sleep/posture/voice 残余（见 §3.3 补记）
真机依赖: 完整链可选真机；host mock 停更 + 过期 ts 可软件回放
V5 用法: 首选 capstone；可拆 host-only 子项作为辅助 fixture
Oracle 草图: 停更/过期后 modalities 不得当 live 当前值；话术无“当前心率=N”；
  online 新鲜样本仍可播报；分项计分避免早期失败连坐
```

```text
ID: SESS-1
日期: 2026-07-14
一句话症状: 后到的人脸/会话抢占全局 current session，省略 session_id 的客户端串身份
分类: python | integration
关键路径: project2 gateway/subjects.get_current_session；context_builder 空 session_id 回落
修复前/后: 开放设计风险（未作为单点产品修复关闭）
真机依赖: 否；双 session fixture 即可
V5 用法: 高价值辅助 fixture；与 V4 ambient 相关但测“抢占”而非仅 ambient 授权
Oracle 草图: sess_A 后写入更新 last_seen 的 sess_B；无 session_id 请求不得静默用错 actor；
  或强制要求显式 session_id 并在响应中可审计
```

```text
ID: PRIV-1
日期: 持续 / e5f834a 加固测试
一句话症状: 未认证或跨患者时若消费端忽略 policy，仍可能播报 sleep/vitals/memory
分类: python | integration
关键路径: context_builder.build_chat_context_v3；voice 必须读 policy.allowed
修复后: v3 拒绝时 modalities 应为空；voice 侧有 deny 路径
真机依赖: 否
V5 用法: 辅助 E2E fixture（builder + consumer）；V4 F3 升级版，强调消费端
Oracle 草图: unauth/cross-patient → allowed=false 且 modalities 空且 TTS prompt 无 PHI；
  staff recognized → 可含 sleep brief
```

```text
ID: SLEEP-1
日期: 修复 6741d31
一句话症状: 无 room/bed 的睡眠 CSV 全部落到第一床
分类: python
关键路径: sleep_importer.row_targets；曾默认 unscoped_policy=first
修复前: first；修复后: skip（project2 config/yaml）
真机依赖: 否
V5 用法: regression 注入允许；标明 regression + 6741d31
Oracle 草图: 无归属行不写任何床；混合文件只写有归属行；大小写 room/bed 映射正确
```

```text
ID: STREAM-1
日期: 审查 P1#4 / b35cef1
一句话症状: <think> 跨 SSE/chunk 边界时思考内容进入 TTS
分类: python
关键路径: project voice/tts 流式过滤；_StreamThinkFilter
修复前: 分 chunk 正则无 inside_think 状态
修复后: b35cef1 状态机
真机依赖: 否；纯字符串切分即可
V5 用法: capstone 子 oracle 或辅助隐私 fixture
Oracle 草图: 任意切分 open/close/属性/大小写；spoken sink 永不含 think 内文
```

```text
ID: UART-1 / MLX-1
日期: 审查 P1#1/#2 / b35cef1
一句话症状: UART 超长帧 memcpy 越界；单路 MLX 失败仍拷未初始化温度并刷新 freshness
分类: firmware
关键路径: project esp32 testpro3 main.cpp 解析与驱动
修复前: b35cef1^；修复后: 长度门控 + per-sensor ok/last-good
真机依赖: 软件/QEMU 帧注入即可
V5 用法: 固件/QEMU 包
Oracle 草图: 超长/截断/错尾不写越界、不标 valid；单路失败不污染另一路 freshness
```

```text
ID: DELIV-1
日期: 审查 P2#9 / b35cef1
一句话症状: socket 写失败仍返回 sent；companion cooldown 先于成功投递
分类: python | integration
关键路径: tcp_ingest writer；companion 事件顺序
修复后: 写错误传播；POST 后再记 memory/cooldown（仍无设备 ACK）
真机依赖: 否（mock writer）
V5 用法: capstone 子 oracle（投递诚实性）
Oracle 草图: writer raise → False 且连接注销；5xx → 无 cooldown；可选 queued/sent/acked 分态
```

```text
ID: BUILD-1
日期: 审查 P1#5 / 2585213
一句话症状: 干净树 + 无网/无 managed cache 时 ESP-IDF 6.0.1 因 led_strip 等失败
分类: environment | firmware
关键路径: 组件 manifest vs 本地 vendored components/led_strip
修复后: 2585213 本地 vendor
真机依赖: 否；只要 IDF 工具链
V5 用法: 环境维 / 严于 V4 F9 的“离线干净构建”
Oracle 草图: 删 build+managed_components 后 idf.py build 成功；依赖不靠 registry 热拉补丁
```

```text
ID: WIRE-1 / WIRE-2
日期: d5ca482 / 04ccc6c
一句话症状: ADMIN_AUTH_ENABLED=False 时 NameError；to_timestr 缺 import time
分类: python
修复后: 已修；可再注入
真机依赖: 否
V5 用法: 辅助 wiring/smoke 或 regression（见 §9.2 是否降权）
Oracle 草图: 关鉴权路径返回 subject；rrhr/to_timestr 不抛
```

```text
ID: BEMFA-1 / PRUNE-1
日期: e5f834a 测试加固 / sensor_store 语义
一句话症状: 垃圾 TCP 行拖垮订阅；过期或未来 ts 导致 latest 空或 prune 卡死
分类: python
真机依赖: 否
V5 用法: 辅助协议/时间语义 fixture；与 FRESH-1 同族
Oracle 草图: 垃圾行 skip；ts=0 prune 后 latest 空；now_ms 写入可见；未来 ts clamp
```

```text
ID: TOF-HDR / TOF-META / STACK-1
日期: project2/project3 ESP CHANGELOG 历史
一句话症状: 错帧头 AA55 导致 frames=0；漏跳 16B meta 全黑；RF 任务栈溢出 panic
分类: firmware
真机依赖: 帧头/meta 可软件回放；栈溢出适合 QEMU/HIL
V5 用法: 固件/QEMU 次优先；STACK-1 偏 V5 HIL
```

#### 9.8.3 明确不进 V5 Ability 或第一阶段 seed

| 项 | 处理 |
|---|---|
| PlanExec Gold 进 handoff、哈希不复核、冻结后可变、计时/成本口径错 | 独立 PlanExec capstone |
| 传感器历史纯内存重启清空 | 设计说明 / Ship 文档题，不作唯一 Ability 大题 |
| v2 无鉴权 chat、loopback worker 放行 | 兼容面说明；可选 Ship |
| project3 双 ESP 全栈 | 仅素材；V5 后续场景再议 |
| 拼写/marker/报告措辞拉开 95–99 | 禁止（见 §6） |

#### 9.8.4 与 V4 的错开摘要

V4 已覆盖：admin、ambient 行为、care_event、migration、sleep 归属、ESP static/build。  
V5 新增量应来自：样本时间 vs 接收时间、停更话术、session 抢占、部分失败 degraded、
不可信传感器流、投递诚实、离线干净构建、（远期）双 ESP 融合陈旧。  
不把 V4 F1–F12 细节题再堆一层。

#### 9.8.5 建议落地顺序（仅备忘，非排期）

1. 保持本台账与 `project2/docs/BUG_KNOWLEDGE_BASE.md` 同步新修 bug。  
2. 立项时：先做 project2 辅助 fixture 与 host freshness 子项。  
3. 再做一条可拆分计分的 FRESH-1 V5 capstone（含残余话术 oracle）。  
4. 固件包与 BUILD-1 仅对顶部模型。  
5. V5 HIL 仅在固定测试台 preflight 稳定后启用。  

### 9.9 2026-07-19 V4.1b 收口后的新增约束

V4.1b 的结果改变了 V5 的优先级，而不是推翻已有题源。当前结论是：V4.1b 已足以
完成日常模型选型，V5 不再承担“把 96、98、99 强行排开”的任务。

#### 9.9.1 保留的经验

1. **独立 fixture 优先于事后解释级联。** F6 拆开后，Ability 能表达局部迁移能力，
   Ship 仍能保留完整旧库升级失败的发布严重性。FRESH-1、session、固件题也必须为
   各子能力提供独立可达 fixture，再补一条端到端闭环。
2. **正向能力与安全失败分开。** V4.1b 将授权 care 与 ambient 泄漏拆开；未来 freshness
   也要分开测新鲜数据可用、陈旧数据拒绝和恢复路径，不能一次失败全家连坐。
3. **Ability 与 Ship 继续双轨。** Kimi 94/88、Grok 90/65、M2.7 73/60 证明总完成度
   与发布风险必须同时保留。
4. **Route 是模型身份的一部分。** DeepSeek gray 96-99 与 preview 78 的差异远大于
   普通模型分差。未来 group key 必须包含 provider、endpoint product、billing tier、
   route/fingerprint、harness、thinking 和信息权限，未知字段不得静默合并。

#### 9.9.2 不沿用到 V5 的做法

1. **Mixed-n worst 不作统一稳定榜。** V4.1b 为历史连续性保留 worst 主列，但 n=1 与
   n=2 混排会奖励少测。未来固定正式重复次数；单次交付 Ability、可靠性/失败率和
   best-known ceiling 分开报告。
2. **顶部微细节不进入核心决胜。** Sol 98 与 99 的差异主要是 `tof1` marker 和 reason。
   exact reason、marker、报告措辞与静态拼写转为 Evidence/Process/contract 辅助维度，
   不用来制造新的顶部排序。
3. **不使用简单 Ability/美元 CPI 作唯一效率结论。** 实付、订阅边际、标价等价、
   warm cache、cold start 和异常路由分列；优先报告首次达到可交付阈值的成本/时间与
   Pareto 前沿。
4. **不因免费额度或新模型发布重跑全矩阵。** 只有真实选型问题或新失败模式才新增
   样本；免费 token 不是评测需求。

#### 9.9.3 未来冻结前校准门

若 V5 终于立项，正式运行前至少完成：

- Gold、broken seed 和等价 mutation 验证；
- 一个顶部、一个中游、一个低档锚点，关键配置使用相同固定 n；
- item 级 cascade/covariance 检查，确认单根因不会重复放大 Ability；
- route/provider 信息完整性检查；
- 运行成本、人工介入、最大墙钟和停止条件；
- 在不知道模型排名的前提下，逐题说明其真实工程价值。

任一项不成立，就继续使用 V4.1b，不为了版本号进入实施。

### 9.10 2026-07-19 超远期开放式 V5 / V5 HIL 方案

**状态：** 仅记录架构想法；不立项、不采购、不画正式 PCB、不搭建测试台。本文节
不是实施 handoff，也不是当前评测契约。后续真正开工时，应根据当时的真实项目和现有
硬件重新收敛，而不是机械照搬本节。

#### 9.10.1 从命题评测转向开放式系统任务

V4.1b 仍然是受控代码题：模型面对明确的 seed、题面、测试出口和评分维度。PlanExec
则是在固定计划下测执行成本与交付能力。若未来真的启动 V5，主场景可以转向更开放的
系统工程任务：

> 给模型一个已经准备好的 Linux/嵌入式开发环境、一个真实系统目标和可用设备，允许
> 模型自行认识拓扑、修改代码、部署、注入故障、观察日志并验证最终行为；评测器只在
> 主机侧观察外部可复核结果。

这不是为了让题目变得模糊，而是把自由度从“实现细节”扩大到“排障路径”。模型可以
自行决定使用 shell、Python、SSH、systemd、串口工具、自己的测试脚本或其他合理方法。
不固定函数名、模块名、目录结构或唯一修复路径，也不把代码静态相似度作为核心评分。

开放式 V5 仍必须固定：

- 任务目标和系统边界；
- 公开可观察的协议、设备和环境信息；
- 外部行为不变量；
- 测试数据的可重复性；
- 墙钟、烧录、重启、安装和功耗预算；
- evaluator 的最终验收出口。

自由发挥只属于实现和调试过程，不属于成功标准。否则评测会从能力测试退化成一次
不可复现的现场演示。

#### 9.10.2 基础环境应预装并可恢复

V5 不把“拿到一块全新开发板后从零安装系统”作为每次模型运行的默认前置条件。现实
中的持续开发通常已经有可用的操作系统、工具链、依赖和设备连接，模型需要解决的是
项目问题和运行故障。

建议提前准备并冻结基础镜像：

- 树莓派 5 的 Linux、SSH、Python、Git、MQTT/TCP 基础服务；
- 规定版本的 ESP-IDF、烧录和串口工具；
- 固定用户、权限、udev 规则和 `/dev/serial/by-id` 设备映射；
- 公开的硬件拓扑、HIL-BUS 和 bench 控制命令；
- 可以修改的 candidate 工作区和依赖层；
- 与个人文件、主机凭据、Gold 和 evaluator 隔离的系统盘或容器。

每轮开始先用 Gold 完成 preflight，证明测试台健康。模型运行造成的系统污染通过
候选容器、独立用户空间或恢复镜像处理；不要求每次把物理测试台重新从空盘安装。
环境安装和依赖诊断仍可作为 V5 的一个维度，但不应成为所有场景的随机前置噪声。

#### 9.10.3 主机评测与树莓派候选环境隔离

推荐的信任边界：

```text
主机 Windows
|- evaluator、hidden scenario、Gold、score model
|- 运行记录、成本记录、冻结快照
|- 主机侧原始观测和最终判分
`- 通过独立 SSH key 控制树莓派

树莓派 5
|- 模型工作区和候选 Gateway
|- 模型可安装的依赖和调试工具
|- ESP32 烧录、串口和公开故障注入
|- candidate 日志
`- 不保存 hidden oracle、Gold 修复和主机凭据
```

SSH 只作为传输和控制通道，evaluator 逻辑不复制到模型工作区，也不把 hidden test
目录挂载到树莓派。主机可以调用树莓派的固定控制接口，但最终行为测试尽量从主机侧
发起并观察网络、设备和用户可见输出。

如果模型拥有树莓派真正的 root 权限，则树莓派上的日志和 bench 服务都不能被视为
可信证据。更稳妥的方案是给模型一个接近 root 的候选容器或独立用户空间，让它能够
安装依赖、管理候选服务、访问公开串口和调试设备，但不能修改 bench controller、
主机评测通道和证据目录。若将来必须给完整 root，则需要由主机或独立控制器直接采集
关键 UART、电源和设备状态。

#### 9.10.4 模型与 evaluator 的控制权限

模型必须能进行真正的自测，否则无法测到自主调试能力；但模型和 evaluator 不应完全
同权。建议采用“同类故障公开、具体组合隐藏”的边界：

| 能力 | 模型 | evaluator |
|---|---:|---:|
| 查看设备、串口、服务和公开日志 | 是 | 是 |
| 编译、烧录、重启候选 Gateway | 是 | 是 |
| RST、BOOT、公开断电恢复 | 是 | 是 |
| 发送正常和自定义传感器数据 | 是 | 是 |
| 注入截断帧、旧数据、断网等典型故障 | 是 | 是 |
| 自己编写额外测试脚本 | 是 | 不限制 |
| 隐藏故障组合和精确时序 | 否 | 是 |
| 读取 Gold、hidden oracle 和预期输出 | 否 | 是 |
| 修改主机评测、bench controller 和原始证据 | 否 | 否 |
| 恢复基础镜像、冻结候选和最终评分 | 否 | 是 |

模型可以主动尝试断网、重启 Gateway、重启 ESP32、发送过期数据、制造坏帧和重复包。
evaluator 再使用公开故障类型的不同组合、边界值和时序进行隐藏验收。隐藏测试不应
突然引入题面未声明的新协议或硬件能力，而应检验公开契约的组合与恢复行为。

#### 9.10.5 固件和仿真端的可见性

模型可以看到自己操作对象的 firmware，尤其是模拟传感器、协议对端和公开 Pico2
注入器。这使它能够理解协议、状态机和时序，也符合真实工程中查看对端固件或测试
fixture 的习惯。

建议分层：

| 对象 | 模型查看源码 | 模型可改写/烧录 | 隐藏评测处理 |
|---|---:|---:|---|
| 候选 DUT 固件 | 是 | 是 | 冻结候选 hash |
| S3 协议对端/模拟器 | 是 | 按任务决定 | hidden 前恢复 reference hash |
| Pico2-M 公开注入器 | 是 | 是 | 可保留模型自定义工具 |
| Pico2-E 主机评测控制器 | 公开协议即可 | 否 | 主机确认 firmware hash |
| hidden 故障序列 | 否 | 否 | 只存在主机运行时 |

隐藏场景不应硬编码在公开 fixture firmware 内。公开固件可以描述通用的“发送帧、拉低
引脚、等待、重启”等能力，主机在运行时下发隐藏时序。正式 hidden 前由主机重新烧录
reference fixture，并检查其 hash，防止模型通过修改模拟器把所有测试伪造成成功。

#### 9.10.6 双 S3、双 Pico2 的通用 HIL 背板

硬件不应从一开始做成某个项目的整机复刻。首选是一个可插拔的低速 HIL backplane，
两块 ESP32-S3 和两块 Pico2 通过排针或适配卡接入；新换 C5、C6、P4 或其他开发板时，
只更换小型 pin-map adapter，不重新设计整张主板。

推荐角色：

```text
ESP32-S3 A：候选 DUT
ESP32-S3 B：协议对端、第二节点、reference 或备用 DUT
Pico2-M：接树莓派，提供模型可用的公开数据/故障注入
Pico2-E：接主机，提供隐藏注入、独立采集和最终恢复
```

主背板建议包含：

- 两路独立的 5V DUT 电源、电子负载开关、过流保护、放电和电流采样；
- 每块 DUT 的 EN、BOOT/GPIO0、手动复位和电源状态；
- 每块 DUT 两路 UART，支持模型侧日志和主机侧独立 RX 监听；
- 两路 I2C，支持可切换上拉、SDA/SCL 断开和 Pico2 模拟传感器；
- 一路基础 SPI 和若干片选/触发线；
- 每块 DUT 至少 8 条带串联保护和测试点的通用 DIO；
- 电压、电流、reset cause、power-good 和逻辑分析仪测试点；
- 两块 Pico2 的可拔插接口、USB 数据口和明确的电源域隔离。

可定义一个项目无关的 `HIL-BUS`，例如包含 `5V_SW`、`3V3_SENSE`、多路 `GND`、
`EN`、`BOOT`、`UART0/1`、`I2C`、`SPI`、`DIO0-DIO7`、`ADC` 和 `TRIG`。具体 ESP GPIO
由适配卡映射，不在主背板上假设 S3、C6 和 P4 的 strapping、USB、flash 或 PSRAM
引脚完全一致。

通用 DIO 不要直接把两个推挽输出硬连在一起。每条线应预留串联电阻、跳线/总线选择、
可选上拉下拉和测试点；EN/BOOT 使用开漏控制。第一版使用跳线、0 欧电阻位和少量
总线开关即可，不需要昂贵的全矩阵 crosspoint。

第一版不加入摄像头、麦克风、真实 MLX 传感器、射频干扰、高压毛刺和复杂高速 SPI
故障。当前最有价值的可控对象是电源、EN/BOOT、UART、I2C、GPIO、reset、数据时间戳
和端到端 Gateway 行为。

#### 9.10.7 开放式 V5 的运行阶段

开放式长任务仍需要边界，而不是无限运行：

1. **Preflight**：主机用 Gold 固件验证树莓派、控制器、供电、串口和最小通信。
2. **Discovery**：模型查看公开拓扑、串口标识、服务和工作区。
3. **Implementation**：模型自由修改 Gateway、固件、fixture 和配置。
4. **Self-test**：模型自行烧录、重启、注入公开故障并观察恢复。
5. **Freeze**：主机保存源码、配置、依赖、固件 hash 和候选快照，停止继续修改。
6. **Hidden black-box evaluation**：主机发数据和故障，只观察外部行为和独立证据。
7. **Optional repair**：若研究返修能力，再把症状级失败包交还模型，并单独记录成本。

黑盒 oracle 主要判断：是否启动、是否通信、是否拒绝坏数据、是否保留合法数据、是否
正确标记 degraded/stale、是否幂等、是否恢复、是否泄漏信息，以及最终用户输出是否
与设备事实一致。代码路径、函数名和具体模块边界不作为核心评分依据。

#### 9.10.8 WSL 的位置与构建策略

WSL 对 ESP-IDF 构建可能有明显速度优势，例如全新构建从数分钟降到约一分钟，因此
适合作为未来的**可选构建 worker**。但当前 Windows EIM 的 ESP-IDF v6.0.1 原生环境
仍是正式基准；在没有做一致性校准前，不把 WSL 和 Windows 构建结果混成同一组。

若未来采用 WSL：

- 源码和构建目录放在 WSL 自己的 ext4 文件系统内，不放在 `/mnt/e` 上做高频编译；
- WSL 使用与 Windows 相同的 ESP-IDF、工具链、组件锁定和环境变量记录；
- WSL 只负责 build，烧录、串口和真机控制交给 Windows 或树莓派；
- 构建产物导出到主机后保存 hash、size、日志和 `build_backend=wsl2`；
- Gold 先分别在 Windows 和 WSL 构建，确认行为、分区、固件和评测出口一致；
- 运行记录区分 cold build、warm build、cache 状态和后端，不把速度差误读成模型能力差。

WSL 不应成为模型必须解决的随机 USB/串口桥接问题。尤其不建议把真机刷写和长期串口
监控依赖 WSL 的 USB 映射；WSL 可以加速编译，设备控制仍保持在已验证的 Windows 或
树莓派路径。

#### 9.10.9 无人值守但有界的自动化

“让模型闷头跑几个小时”可以作为运行方式，但不能是无上限的黑盒等待。控制面至少应
设置：

- 单步编译、烧录、串口监控和安装的超时；
- 单模型总墙钟预算；
- 最大编译、烧录、断电、重启和依赖安装次数；
- 连续无文件变化、无新日志或无状态变化的 watchdog；
- 每个阶段的快照、日志和可恢复 checkpoint；
- 超时后自动停止并保留现场，而不是继续消耗 token 和硬件寿命。

推荐把“有效编辑、有效测试、首次设备通信、首次通过公开场景、最后一次状态变化”
作为外部事件记录。这样可以允许模型长时间自主工作，又能在失控前自动停机，并区分
它是在编译、搜索、重试、等待设备，还是已经没有实际进展。

该方案的目标不是让模型永远运行，而是测量在一个真实但受控的系统中，它能否建立拓扑
认知、找到根因、形成修改-部署-验证闭环。任何一项硬件、权限、时间或证据边界尚未
稳定时，继续使用 V4.1b，不启动 V5 HIL。
