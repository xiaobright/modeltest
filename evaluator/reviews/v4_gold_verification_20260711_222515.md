# V4 Gold Verification

## Meta

- result_id: `20260711_222515`
- project: `archives/v4_gold/project2_task`
- git commit: `6da2be71869b43b87f402c5d0fd7ed7513eebe27`
- model/channel/harness: `gpt-5.6-sol-gold / gold / local`
- evidence_source: `result_local_artifact`

## Automatic Evidence

| Check | Result |
|---|---|
| public | pass |
| debug probe | pass |
| hidden | 45/45 |
| ESP static | 9/9 |
| ESP-IDF v6.0.1 build | pass |
| build evidence gate | pass |
| F9 | `real_pass` |
| F11 | `heuristic`（已填写报告，不是 placeholder） |
| Ability / Ship | 100 / 100 |
| Class | A |
| behavior blockers | `[]` |
| meta complete | true |

## Build Artifact

- file: `evaluator/results/20260711_222515/espidf_build_artifacts/stdpro.bin`
- size: `980944` bytes
- SHA256: `b22c89e82c7b0159dec28c0571ad954ece2f1b89c346faa7ce2ad7ce8f219959`
- manifest: `evaluator/results/20260711_222515/espidf_build_evidence.json`
- log: `evaluator/results/20260711_222515/espidf_build.log`

记录的大小和 SHA256 已与归档文件重新计算比对一致。scorer 验证 log/bin
均位于本次 result、文件大小一致且 SHA256 匹配；仅有 build 退出码 0 不足以获得 F9 满分。

F11 同时验证独立占位行与实质报告内容，报告中描述“已移除 placeholder/待填写”
不会再被误判为未填写模板。

构建在 Windows 原生 EIM ESP-IDF v6.0.1 环境完成；未执行 flash、monitor
或真实硬件联网测试。

## Verdict

Gold gate 通过。该 result 直接评测归档 Gold 树，是 F9/F11 最终边界修复后的
V4.0 冻结依据。
