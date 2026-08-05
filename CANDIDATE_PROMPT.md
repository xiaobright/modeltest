# V4.1 被测模型提示词（候选 / Candidate）

**用途**：给被测模型粘贴的任务正文（操作侧文件，**不要**放进候选可见区当答案）。  
**默认投放：** live `workspace/`（主空间测完再 `make_broken_project` 重置）。  
**可选：** `prepare_candidate_handoff.py` 生成的外部包（正式隔离时用）。

---

## 投放前检查（默认）

1. `python evaluator\make_broken_project.py` 已重置  
2. 模型 cwd / 可见范围尽量只含 `workspace/`（或直接 `workspace/project2_task`）  
3. **不要**让模型读 `evaluator/`、`docs/`、`archives/`、live `terminals/`、`mcps/`  
4. 测完评测：`python evaluator\run_full_eval.py workspace\project2_task ...`  
5. 下一模型前再重置

---

## 提示词正文（复制以下整段）

```text
你正在接手一个本地护理/睡眠联调工程（Project2），工作区仅限当前可见的 workspace 目录。
里面有真实开发遗留的 bug，也有交接文档要求补完的功能。请把项目修到可提测状态。

【可见范围】
- 只依赖 workspace 内内容：ONBOARDING_TODO.md、reference/、tests/public/、tools/、project2_task/
- 不要读取、搜索或依赖 workspace 之外的目录（不要碰 evaluator、docs、archives 等）

【必须流程】
1. 先阅读 ONBOARDING_TODO.md、reference/、项目 README、已有代码结构
2. 开始改代码前，必须先运行并阅读：
   python tests\run_public_tests.py project2_task
   python tools\run_debug_probe.py project2_task
3. 根据诊断结果修复；改完再跑上述两条；需要时继续迭代
4. ESP32-S3（esp32/testpro4）是必做：按 reference/espidf_protocol_contract.md 修复 Wi-Fi+MQTT/协议/NVS 等
5. 环境支持则运行：
   python tools\run_espidf_build.py project2_task
   （或 tools 下的 Windows 编译脚本）至少跑到明确成功或明确失败点，并如实记录
6. 最后把：初始诊断、修改说明、最终验证、ESP 编译/失败情况、未验证风险
   写入 project2_task/PULL_REQUEST_TEMPLATE.md（不要留「待填写」空模板）

【硬性约束】
- 不要通过删功能、硬编码测试数据、降低安全要求、跳过旧 API、修改 tests/ 或 tools/ 诊断脚本来绕过问题
- 保持模块边界，不要把所有逻辑塞回单一文件
- 管理员密码不可明文；Cookie 只存随机 token；注意 session/context 权限与患者数据零泄漏
- 历史 SQLite 可能缺列，初始化要能迁移并尽量保留旧数据
- 睡眠 CSV 可能混合有/无 room-bed 的行，按行策略处理
- 收紧鉴权后，检查 voice/本地助手是否仍能正确带会话取上下文（不要靠静默 ambient session 漏数据）

【输出】
- 直接开始修改，不要只给建议
- 最终用简短总结：改了什么、验证了什么、还有什么风险
- 不要调用 subagent
```

---

## 锚定 meta 建议

| 模型 | --model | --channel | --harness |
|------|---------|-----------|-----------|
| Grok | Grok-4.5 | grok-cli | grok-cli |
| GPT-5.6-luna | GPT-5.6-luna | codex-high | codex |
| HY-3 | HY-3 | workbuddy | workbuddy |
| GLM-5.2 | glm-5.2 | workbuddy | workbuddy |
| Composer | composer-2.5 | grok-cli | grok-cli |

正式评测命令（默认主空间）：

```powershell
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CHANNEL --harness HARNESS `
  --require-meta --include-espidf-build `
  --run-group-id "NAME_CH_thinking" --run-index 1 `
  --thinking-level high
```
