# DeepSeek Harness 实验 preset

> 独立发布与后续维护位于
> [`xiaobright/dsh-anchored-standard`](https://github.com/xiaobright/dsh-anchored-standard)。
> 本目录保留 2026-08-14 Project2 98/99 双跑使用的冻结快照，便于证据复算。

## anchored-standard

这是 Project2 98/99 分双跑使用的两阶段 preset，针对 DeepSeek Harness 提交
[`47f9438`](https://github.com/deepseek-ai/deepseek-harness/tree/47f943859bef60e4160492346772ded9b24f765a)
编写和验证：

1. 第一次模型请求保持 Minimal 的完整 system prompt，只暴露当前平台 shell 和 `read`；
2. 会话出现第一个持久 `tool/call` 后，后续请求恢复 Standard 的完整工具目录；
3. 阶段由 session event 推导，重载会话不会丢失，也不会跨 session 共享状态。

Windows 首次目录为 `pwsh/read`，Linux 为 `bash/read`。本次 98/99 分实测使用 Windows、
DeepSeek V4 Pro、`reasoningEffort=max`；它不是官方 preset，也不保证在其他 Harness 版本或
其他任务上得到相同提升。

### 安装

把 `anchored-standard/` 整个目录放到用户 preset 目录：

```text
C:\Users\<用户名>\.dsh\.agent-presets\anchored-standard
```

完整重启 DeepSeek Harness，新建空 session，并选择
`两阶段锚定标准模式（实验）`。不要在已有 session 中途切换 preset。

导出的 JSONL 应出现两次 `request/header`：第一次只有两个工具，第二次为完整 Standard
目录。如果首段 reasoning 已经持续使用 Standard 风格，应停止昂贵长测并先检查 preset
是否加载成功。

### 来源与许可

`agent.cordis.yml` 基于 DeepSeek Harness 的 Standard preset 修改，`tool-bootstrap.mjs`
为本项目新增。DeepSeek Harness 使用 MIT License，许可文本见
[`LICENSE.deepseek-harness`](./LICENSE.deepseek-harness)。

## minimal-full

`minimal-full/` 是本轮 full-task 消融 preset。它与 `anchored-standard` 保持相同的
Minimal complete persona、runtime-context suppression 和 Standard capability roster，唯一的
模型可见目标差异是移除 `tool-bootstrap`：从第一次模型请求起即暴露同平台完整 Standard
工具目录。正式运行前必须通过 request/header 快照验证；若首请求除工具目录外还有差异，
该消融不进入付费阶段。

该 preset 由 [@NineThoughts0521](https://github.com/NineThoughts0521) 用于 2026-08-15 独立复现；实现、schema gate 与 full-task 结果见 [`../../experiments/deepseek-v4-pro-anchoring/`](../../experiments/deepseek-v4-pro-anchoring/README.md)。这些 runs 不并入维护者原有 formal `n`。
