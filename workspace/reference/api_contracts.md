# Public API Contracts

这些是本次工程任务使用的公开接口契约，用于统一 API 行为和文档口径。

## Admin

`POST /api/v3/admin/setup`

```json
{"username": "admin", "password": "StrongPass123", "password_confirm": "StrongPass123"}
```

成功：返回 `ok=true`，并设置管理员 Cookie。密码必须加盐哈希保存。

`POST /api/v3/admin/login`

```json
{"username": "admin", "password": "StrongPass123"}
```

成功：返回 `ok=true`，并设置管理员 Cookie。

`POST /api/v3/admin/logout`

成功后旧 Cookie 失效。

`GET /api/v3/admin/auth`

返回是否需要 setup、是否已认证。

## Subjects And Sessions

管理 API：

```text
GET  /api/v3/subjects
POST /api/v3/subjects
GET  /api/v3/assignments
POST /api/v3/assignments
POST /api/v3/sessions
```

远程未登录用户不能访问管理 API。本机 worker 例外只用于指定服务接口。

## Context

`GET /api/v3/context/chat?session_id=...&target_subject_id=...`

请求敏感患者上下文时，调用方应提供可靠的会话凭证与目标范围。未通过鉴权或授权检查的请求不得返回患者明细、记忆或护理事件内容。实现时请结合现有 session / actor / 过期语义与 gateway 代码自行收敛边界。

未认证示例形态：

```json
{
  "policy": {"allowed": false, "reason": "not_authenticated"},
  "target": {"patient": {}, "assignment": {}},
  "modalities": {"sleep": {}, "vitals": {}, "posture": {}, "memory": {}}
}
```

staff/admin 认证后可查看任意目标患者；patient 只能查看自己。

以下 session 必须视为未认证或不可授权：

- `identity_state=unknown`
- `assurance_level=none` 或空
- `expires_ts` 已过期
- 缺少 `actor_subject_id`

## Care Events

`POST /api/v3/care/events`

需要管理员登录。

`GET /api/v3/care/events?subject_id=sub_patient_test`

需要管理员登录，或通过授权上下文只暴露给允许访问目标患者的 actor。

Context 授权通过后应包含 `modalities.care_events` 或等价字段。

查询参数：

- `subject_id`
- `room` + `bed`
- `limit`：默认最近若干条，返回应按 `ts` 或 `created_ts` 倒序。

room/bed 必须按 gateway 约定规范化。用 lowercase 写入的 `r1203/b1` 也应能被 uppercase 查询 `R1203/B1` 找到。

旧 SQLite 库可能已经存在缺少 `severity/source/created_by/ts` 的 `care_events` 表。初始化逻辑必须迁移旧表并保留旧数据。

## Legacy APIs

这些旧接口必须保持可用：

```text
POST /api/v2/ingest
POST /api/v2/ingest/sleep_quality
GET  /api/v2/latest
GET  /api/v2/voice/chat_context
GET  /api/esp/status
GET  /api/esp/set/latest
```
