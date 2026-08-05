# Architecture Notes

Project2 当前是一个多模块本地 gateway。修复时优先保持职责边界。

- `gateway/gateway.py`：HTTP 路由、页面服务、启动 glue、Bemfa 订阅。
- `gateway/auth.py`：管理员账号、密码哈希、HTTP Cookie 会话。
- `gateway/db.py`：SQLite schema 和连接工具。
- `gateway/subjects.py`：人员、床位绑定、记忆、凭据、身份匹配、会话。
- `gateway/sensor_store.py`：普通传感器/睡眠/姿态/情绪缓存。
- `gateway/esp_store.py`：ESP32 ToF/MLX 数据包与完整 set 聚合。
- `gateway/sleep_importer.py`：睡眠 CSV 导入和无房床字段归属策略。
- 新增 care event 推荐放 `gateway/care_events.py`。

新增功能时请避免：

- 把认证逻辑散落在多个无关模块。
- 让 `gateway.py` 大幅膨胀。
- 为测试硬编码固定 subject、room、bed。
- 直接写真实 `data/project2.db`。

## DB Migration

`CREATE TABLE IF NOT EXISTS` 只能处理全新库，不能升级旧表。修改 schema 时请显式检查 `PRAGMA table_info(...)`，对缺失列执行 `ALTER TABLE ... ADD COLUMN ...`，并为旧数据填充合理默认值。

本任务重点关注 `care_events` 旧表迁移：旧表可能只有 `event_id/subject_id/room/bed/kind/title/content/created_ts/updated_ts`，修复后必须补齐 `severity/source/created_by/ts`，且旧行不能丢失。
