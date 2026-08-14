# DeepSeek V4 轨迹证据

本目录保存 2026-08-14 harness 对照分析的本地原始证据和可复算聚合统计，包括
Windows 上两阶段 `anchored-standard` 的 98/99 分双跑验证。

## 目录

- `raw/`：DSH Session JSONL 与 OpenCode JSON 原始导出，仅本地保存，不公开。
- `manifest.json`：样本标签、分数、配置、相对路径与 SHA-256。
- `analyze_trajectory_exports.py`：统一解析 DSH/OpenCode 完成态消息的脚本。
- `derived/trajectory_stats.json`：完整聚合数据。
- `derived/trajectory_stats.csv`：适合表格分析的扁平数据。

## 复算

```powershell
python evaluator\trajectory_evidence\analyze_trajectory_exports.py `
  --manifest evaluator\trajectory_evidence\manifest.json `
  --json-output evaluator\trajectory_evidence\derived\trajectory_stats.json `
  --csv-output evaluator\trajectory_evidence\derived\trajectory_stats.csv
```

统计只读取 DSH 的完成态 `assistant/message`，不重复计算 `reasoning-chunks`、
`text-chunks` 和 `tool-call-chunks`。OpenCode 只读取 assistant message 的
`reasoning`、`text` 与 `tool` parts。输出不包含完整 reasoning 文本。

DSH 样本还记录 `request/header` 中工具目录的变化。`anchored-standard` 首次请求只有
`pwsh/read`，首个工具调用后切换为 25 项 Standard 工具，用于验证轨迹锚定是否能跨工具
目录扩展保持。

PTC 另行统计外层 `run_code`、内层 `tool/code-dispatch`、必填参数错误、程序失败、
子调用分布和 `Promise.all` 使用情况。

## 发布边界

原始日志包含完整 reasoning、绝对路径、system prompt、命令和工具结果，不直接提交到
公开仓库。公开版本只提供本 README、解析脚本、去掉本地路径的 manifest、派生统计和
分析报告。
