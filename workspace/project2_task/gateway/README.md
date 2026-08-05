# Gateway 模块说明

`gateway/` 是项目的本地网关层，负责把传感器、视觉、姿态、睡眠算法和语音助手连接起来。现在已经按职责拆分，后续改动时优先把代码放到对应模块，避免重新堆回 `gateway.py`。

## 模块职责

```text
gateway/
├── gateway.py          # HTTP 路由、页面服务、启动入口、Bemfa 订阅主循环
├── config.py           # 环境变量、路径、运行参数
├── db.py               # SQLite 连接、建表、床位配置同步
├── auth.py             # 超级管理员账号、登录、Cookie 会话
├── subjects.py         # 人员、床位绑定、记忆、凭据、身份匹配、会话
├── sensor_store.py     # 普通传感器/睡眠/姿态/情绪历史缓存
├── esp_store.py        # ESP32 ToF/MLX 数据包与完整帧组聚合
├── sleep_importer.py   # 睡眠 CSV 导入和无房床字段归属策略
├── utils.py            # 通用类型转换、时间、JSON、ID 工具
├── bed_config.py       # 床位拓扑和 Bemfa topic 命名
├── dashboard.html      # 实时看板
└── admin.html          # 管理台
```

## 放代码的原则

- 新增环境变量或路径：放 `config.py`。
- 新增表、索引、数据库连接策略：放 `db.py`。
- 管理员登录、登出、HTTP 管理会话：放 `auth.py`。
- 人员、患者、床位绑定、凭据、身份匹配、护理记忆：放 `subjects.py`。
- 雷达、环境、音频、睡眠、姿态、情绪这类时序数据缓存：放 `sensor_store.py`。
- ESP32 二进制帧、完整四路姿态 set 组包：放 `esp_store.py`。
- 睡眠算法 CSV 文件读取、导入、归属规则：放 `sleep_importer.py`。
- 只和 HTTP 路由或启动流程有关的 glue code：留在 `gateway.py`。

## 管理员初始化

首次访问 `/admin` 或 `/dashboard` 时，如果还没有超级管理员账户，会显示初始化页面。初始化后，管理页和管理类 API 需要登录访问。

当前保留本机服务接口例外，便于单护士站联调：本机进程仍可调用采集、视觉、身份 gallery 和对话上下文接口。远程浏览器需要通过管理员登录。

## 睡眠 CSV 归属策略

睡眠 CSV 如果带 `room/bed` 字段，会写入对应床位。如果没有房床字段，默认只导入第一个配置床位，避免同一报告广播到所有床位。

可用环境变量调整：

```text
SLEEP_IMPORT_DEFAULT_ROOM=R1203
SLEEP_IMPORT_DEFAULT_BED=B1
SLEEP_IMPORT_UNSCOPED_POLICY=first   # first / skip / all
```

生产环境建议使用 `skip` 或明确设置 `SLEEP_IMPORT_DEFAULT_ROOM/BED`。
