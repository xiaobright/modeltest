"""
床位配置模块 — 集中管理房间/床位拓扑、Topic 命名、巴法云连接参数
被 gateway / posture_worker / voice_assistant 等模块引用
"""

import json
import os

# =====================
# 巴法云连接参数
# =====================
BEMFA_HOST = os.getenv("BEMFA_HOST", "bemfa.com")
BEMFA_TCP_PORT = int(os.getenv("BEMFA_TCP_PORT", "8344"))
BEMFA_UID = os.getenv("BEMFA_UID", "")

# =====================
# 床位定义
# =====================
# 可通过环境变量 BEDS_CONFIG 传入 JSON 格式覆盖
# 格式: {"beds": [["R1203", "B1"], ["R1203", "B2"], ["R1204", "B1"]]}
_default_beds = [
    ("R1203", "B1"),
    ("R1203", "B2"),
    ("R1204", "B1"),
]

_raw_env = os.getenv("BEDS_CONFIG", "")
if _raw_env:
    try:
        parsed = json.loads(_raw_env)
        if isinstance(parsed, dict) and isinstance(parsed.get("beds"), list):
            BEDS = [tuple(item) for item in parsed["beds"] if len(item) == 2]
        else:
            BEDS = _default_beds
    except Exception:
        BEDS = _default_beds
else:
    BEDS = _default_beds

# =====================
# 数据种类定义
# =====================
# 传感器数据（通过巴法云 topic 订阅）
SENSOR_KINDS = ("radar", "env", "audio")

# 姿态数据（ESP32 ToF+MLX 四通道，通过巴法云 topic 订阅）
POSTURE_STREAMS = ("tof1", "tof2", "mlx1", "mlx2")

# 网关内部使用（非 topic 订阅，由 worker/sleep/vision 模块写入）
INTERNAL_KINDS = ("sleep_epoch", "sleep_quality", "posture", "emotion")

# 所有数据种类
ALL_KINDS = SENSOR_KINDS + POSTURE_STREAMS + INTERNAL_KINDS

# =====================
# Topic 命名
# =====================

def topics_for(room: str, bed: str) -> dict[str, str]:
    """返回单个床位的所有巴法云 topic 映射 {kind: topic}"""
    prefix = f"{room.lower()}{bed.lower()}"
    topics = {}
    for kind in SENSOR_KINDS:
        topics[kind] = f"{prefix}{kind}"
    for stream in POSTURE_STREAMS:
        topics[stream] = f"{prefix}{stream}"
    return topics


def build_topic_registry():
    """构建全局 topic → (room, bed, kind) 映射表"""
    all_topics = []
    registry = {}  # topic -> (room, bed, kind)
    for room, bed in BEDS:
        t = topics_for(room, bed)
        for kind, topic in t.items():
            all_topics.append(topic)
            registry[topic] = (room, bed, kind)
    return all_topics, registry


ALL_TOPICS, TOPIC_TO_BED_AND_KIND = build_topic_registry()


def print_config():
    """打印当前床位配置摘要（启动时调用）"""
    print("[BED-CONFIG] 巴法云连接:")
    print(f"  host={BEMFA_HOST}  port={BEMFA_TCP_PORT}  uid={'***' if BEMFA_UID else '(未设置)'}")
    print(f"[BED-CONFIG] 床位数量: {len(BEDS)}")
    for room, bed in BEDS:
        t = topics_for(room, bed)
        print(f"  {room}-{bed}: radar={t['radar']}  env={t['env']}  audio={t['audio']}")
        print(f"             tof1={t['tof1']}  tof2={t['tof2']}  mlx1={t['mlx1']}  mlx2={t['mlx2']}")
    print(f"[BED-CONFIG] 订阅 topic 总数: {len(ALL_TOPICS)}")


def validate() -> list[str]:
    """验证配置有效性，返回错误列表"""
    errors = []
    if not BEMFA_UID:
        errors.append("BEMFA_UID 未设置（环境变量 BEMFA_UID）")
    if not BEDS:
        errors.append("BEDS 配置为空")
    for room, bed in BEDS:
        if not room or not bed:
            errors.append(f"无效床位: room={room}, bed={bed}")
    return errors
