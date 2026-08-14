# DeepSeek V4 trigger probe

这是 2026-08-14 V4 Pro / Flash 轨迹触发实验的脱敏复现工具。完整结论见
[`../../docs/v4.1/DEEPSEEK_V4_TRIGGER_MECHANISM_EXPERIMENTS_20260814.md`](../../docs/v4.1/DEEPSEEK_V4_TRIGGER_MECHANISM_EXPERIMENTS_20260814.md)。

## 发布内容

- `src/classifier.mjs`：保守的轨迹词法分类器；
- `src/cli.mjs`：Chat Completions 单轮和两阶段工具晋升探针；
- `evidence/manifest.json`：私有原始证据的 SHA-256；
- `evidence/experiment_matrix.json`：不含 reasoning 原文的派生矩阵。

原始日志没有公开，因为其中含完整 reasoning、system prompt、工具结果和本地路径。哈希只
用于证明本地原始文件与公开派生结果的对应关系，不能让第三方从哈希恢复内容。

## 使用

需要 Node.js 22+。默认命令只打印请求摘要，不联网：

```powershell
Copy-Item .env.example .env
node --env-file=.env src/cli.mjs
npm test
```

真实请求是显式 opt-in，可能产生费用：

```powershell
node --env-file=.env src/cli.mjs --run --model deepseek-v4-flash
```

用自备的 OpenAI function-tool 数组测试工具目录，或在第二轮晋升目录：

```powershell
node --env-file=.env src/cli.mjs --tools .\my-tools.json
node --env-file=.env src/cli.mjs --run --promote-tools .\my-standard-tools.json
```

`--promote-tools` 使用合成工具结果，只用于检查下一轮轨迹是否保持，不执行真实 agent loop。
真实工程分数必须用完整 harness 和可审计评测复验。

## 判读边界

分类器只识别 `We need`、`Let me`、单独赞许词等表面模式。`ambiguous` 是有意的保守标签；
不得用本工具声称识别了隐藏路由、checkpoint 或模型身份。Flash 探针结果也不得直接外推 Pro。
