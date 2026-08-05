# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

请记录修改前运行的命令和关键结果：

- `python tests\run_public_tests.py project2_task`
- `python tools\run_debug_probe.py project2_task`

## 修改的文件列表

待填写。

## 架构调整与模块设计

待填写。

## 安全边界及鉴权设计

待填写。

## 睡眠 CSV 无 room/bed 时的特殊处理

待填写。

## care_event 实现细节

待填写。

## ESP32-S3 固件接口对齐说明

待填写。

## 本地测试与编译验证结果

请记录修复后运行的命令和结果，至少包括：

- `python tests\run_public_tests.py project2_task`
- `python tools\run_debug_probe.py project2_task`
- `python tools\run_espidf_build.py project2_task` 编译结果或失败位置说明

## 未验证的残留技术债与风险

待填写。
