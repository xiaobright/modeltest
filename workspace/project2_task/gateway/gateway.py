import base64
import html
import ipaddress
import json
import os
import socket
import sqlite3
import sys
import threading
import time
import uuid
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from auth import (
    admin_account_exists,
    create_admin_account,
    create_admin_http_session,
    delete_admin_http_session,
    get_admin_http_session,
    login_admin_account,
)
from config import (
    ADMIN_AUTH_ENABLED,
    ADMIN_FILE,
    ADMIN_PASSWORD_MIN_LEN,
    ADMIN_SESSION_COOKIE,
    ADMIN_SESSION_TTL_MS,
    DASHBOARD_FILE,
    EMOTION_CONTEXT_TTL_MS,
    EMOTION_LABELS,
    ESP_ONLINE_TTL_MS,
    ESP_STORE_DEPTH,
    FACE_MATCH_CANDIDATE_THRESHOLD,
    FACE_MATCH_RECOGNIZED_THRESHOLD,
    HTTP_HOST,
    HTTP_PORT,
    LOCATION,
    MAX_JSON_BODY_BYTES,
    POSTURE_CLASS_NAMES,
    SLEEP_IMPORT_ENABLED,
)
from db import DB_FILE, db_connect, init_management_db, row_to_dict
from esp_store import (
    _get_esp_state,
    append_esp_packet,
    build_esp_set_view,
    esp_lock,
    get_esp_status,
    get_latest_esp_set,
)
from sensor_store import (
    HISTORY_MINUTES,
    append_item,
    latest_one,
    list_latest,
    replace_items,
    series,
    source_online,
    to_timestr,
)
import sleep_importer as sleep_importer_module
from subjects import (
    IDENTITY_RUNTIME_ERROR,
    close_assignment,
    create_assignment,
    create_credential,
    create_credential_from_enrollment,
    create_memory,
    create_session_from_observation,
    create_subject,
    get_active_assignment_for_bed,
    get_active_assignment_for_subject,
    get_current_session,
    get_session,
    get_subject,
    list_assignments,
    list_bed_meta,
    list_credentials,
    list_identity_gallery,
    list_memories,
    list_subjects,
    match_identity,
    upsert_session,
)
from utils import (
    as_bool,
    as_float,
    as_int,
    json_loads_default,
    normalize_bed,
    normalize_room,
    now_ms,
    safe_json_loads,
)

from bed_config import (
    ALL_KINDS,
    ALL_TOPICS,
    BEDS,
    BEMFA_HOST,
    BEMFA_TCP_PORT,
    BEMFA_UID,
    POSTURE_STREAMS,
    TOPIC_TO_BED_AND_KIND,
    print_config,
    validate,
)

# BEMFA subscription check
_config_errors = validate()
if _config_errors:
    for err in _config_errors:
        print(f"[GATEWAY] WARNING: {err}")


def load_dashboard_html():
    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return (
            "<html><body><h1>Dashboard Missing</h1>"
            f"<p>Cannot load: {DASHBOARD_FILE}</p>"
            f"<p>Error: {e}</p></body></html>"
        )


def load_admin_html():
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return (
            "<html><body><h1>Admin Missing</h1>"
            f"<p>Cannot load: {ADMIN_FILE}</p>"
            f"<p>Error: {e}</p></body></html>"
        )


def load_admin_auth_html(setup_mode: bool):
    title = "初始化超级管理员" if setup_mode else "管理员登录"
    submit_text = "创建并登录" if setup_mode else "登录"
    endpoint = "/api/v3/admin/setup" if setup_mode else "/api/v3/admin/login"
    display_name_field = """
        <label>
          显示名称
          <input name="display_name" autocomplete="name" placeholder="超级管理员" />
        </label>
    """ if setup_mode else ""
    confirm_field = """
        <label>
          确认密码
          <input name="password_confirm" type="password" autocomplete="new-password" required />
        </label>
    """ if setup_mode else ""
    password_autocomplete = "new-password" if setup_mode else "current-password"
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title} - Project2</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f5f7fb;
      color: #172033;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(420px, calc(100vw - 32px));
      background: #fff;
      border: 1px solid #d8deea;
      border-radius: 8px;
      box-shadow: 0 16px 42px rgba(20, 33, 60, 0.12);
      padding: 28px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    p {{ margin: 0 0 22px; color: #5f6b80; line-height: 1.6; }}
    form {{ display: grid; gap: 14px; }}
    label {{ display: grid; gap: 6px; font-size: 14px; font-weight: 600; }}
    input {{
      height: 42px;
      border: 1px solid #c8d0df;
      border-radius: 6px;
      padding: 0 12px;
      font-size: 15px;
    }}
    button {{
      height: 44px;
      border: 0;
      border-radius: 6px;
      background: #1b6ef3;
      color: #fff;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }}
    .msg {{ min-height: 20px; color: #c03131; font-size: 14px; }}
  </style>
</head>
<body>
  <main>
    <h1>{escaped_title}</h1>
    <p>{"首次进入需要创建超级管理员账户，之后管理页和管理 API 都需要登录。" if setup_mode else "请输入超级管理员账户后继续访问管理台。"}</p>
    <form id="authForm">
      <label>
        用户名
        <input name="username" autocomplete="username" required minlength="3" maxlength="64" />
      </label>
      {display_name_field}
      <label>
        密码
        <input name="password" type="password" autocomplete="{password_autocomplete}" required minlength="{ADMIN_PASSWORD_MIN_LEN}" />
      </label>
      {confirm_field}
      <button type="submit">{submit_text}</button>
      <div id="msg" class="msg"></div>
    </form>
  </main>
  <script>
    const form = document.getElementById('authForm');
    const msg = document.getElementById('msg');
    form.addEventListener('submit', async (event) => {{
      event.preventDefault();
      msg.textContent = '';
      const payload = Object.fromEntries(new FormData(form).entries());
      try {{
        const resp = await fetch('{endpoint}', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        const data = await resp.json().catch(() => ({{}}));
        if (!resp.ok || !data.ok) {{
          msg.textContent = data.error || '操作失败';
          return;
        }}
        window.location.href = '/admin';
      }} catch (err) {{
        msg.textContent = String(err);
      }}
    }});
  </script>
</body>
</html>"""


# =====================
# Data cache (per bed)
# =====================
















# =====================
# SQLite management data
# =====================





















































































# =====================
# Per-bed data access
# =====================















# =====================
# Per-bed ESP data
# =====================















def compute_sleep_score(radar_item, env_item, audio_item):
    score = 80

    motion = float(radar_item.get("motion", 0) or 0)
    turning = int(radar_item.get("turning", 0) or 0)
    score -= min(20, motion * 50)
    if turning == 1:
        score -= 5

    noise_db = float(env_item.get("noise_db", 0) or 0)
    snore_level = int(audio_item.get("snore_level", 0) or 0)
    score -= max(0, (noise_db - 35) * 0.8)
    score -= snore_level * 4

    co2 = float(env_item.get("co2_ppm", 0) or 0)
    if co2 > 1200:
        score -= min(15, (co2 - 1200) / 50)

    return max(0, min(100, int(score)))


def sleep_epoch_zero():
    return {
        "record": "",
        "start_s": 0.0, "end_s": 0.0,
        "BR_mean": 0.0, "BR_std": 0.0,
        "HR_mean": 0.0, "HR_std": 0.0,
        "RMSSD": 0.0, "SDNN": 0.0,
        "EEG_stage": "W", "EEG_conf": 0.0,
        "Sleep_detect": "W", "Sleep_W_prob": 0.0,
        "Final_stage": "W", "RuleApplied": 0,
        "ts": 0,
    }


def sleep_quality_zero():
    return {
        "record": "",
        "total_h": 0.0, "sleep_h": 0.0,
        "W_epochs": 0, "N1_epochs": 0, "N2_epochs": 0, "N3_epochs": 0, "REM_epochs": 0,
        "N1_ratio_in_sleep": 0.0, "N2_ratio_in_sleep": 0.0,
        "N3_ratio_in_sleep": 0.0, "REM_ratio_in_sleep": 0.0,
        "score_valid": 0, "duration_score": 0.0,
        "structure_score": 0.0, "total_score": 0.0,
        "grade": "数据不足，暂不评分",
        "ts": 0,
    }


def posture_zero():
    return {
        "class_idx": -1, "class_name": "未知",
        "confidence": 0.0, "confidence_flag": "none",
        "probabilities": [0.0, 0.0, 0.0],
        "infer_ms": 0.0, "esp_set_id": -1,
        "infer_count": 0, "ts": 0,
    }


def emotion_zero():
    return {
        "label": "未知",
        "confidence": 0.0,
        "confidence_flag": "none",
        "probabilities": {},
        "face_count": 0,
        "face_present": False,
        "source": "unknown",
        "source_state": "idle",
        "backend": "none",
        "camera_index": -1,
        "stable_for_ms": 0,
        "infer_ms": 0.0,
        "infer_count": 0,
        "notes": "",
        "identity_state": "",
        "subject_id": "",
        "ts": 0,
    }


def normalize_sleep_epoch(row: dict, fallback_ts: int):
    z = sleep_epoch_zero()
    out = dict(z)
    out.update({
        "record": str(row.get("record", "") or ""),
        "start_s": as_float(row.get("start_s"), 0.0),
        "end_s": as_float(row.get("end_s"), 0.0),
        "BR_mean": as_float(row.get("BR_mean"), as_float(row.get("breath_bpm"), 0.0)),
        "BR_std": as_float(row.get("BR_std"), 0.0),
        "HR_mean": as_float(row.get("HR_mean"), as_float(row.get("heart_bpm"), 0.0)),
        "HR_std": as_float(row.get("HR_std"), 0.0),
        "RMSSD": as_float(row.get("RMSSD"), 0.0),
        "SDNN": as_float(row.get("SDNN"), 0.0),
        "EEG_stage": str(row.get("EEG_stage", "W") or "W"),
        "EEG_conf": as_float(row.get("EEG_conf"), 0.0),
        "Sleep_detect": str(row.get("Sleep_detect", "W") or "W"),
        "Sleep_W_prob": as_float(row.get("Sleep_W_prob"), 0.0),
        "Final_stage": str(row.get("Final_stage", "W") or "W"),
        "RuleApplied": as_int(row.get("RuleApplied"), 0),
    })
    out["ts"] = as_int(row.get("ts"), fallback_ts)
    return out


def normalize_sleep_quality(row: dict, fallback_ts: int):
    z = sleep_quality_zero()
    out = dict(z)
    out.update({
        "record": str(row.get("record", "") or ""),
        "total_h": as_float(row.get("total_h"), 0.0),
        "sleep_h": as_float(row.get("sleep_h"), 0.0),
        "W_epochs": as_int(row.get("W_epochs"), 0),
        "N1_epochs": as_int(row.get("N1_epochs"), 0),
        "N2_epochs": as_int(row.get("N2_epochs"), 0),
        "N3_epochs": as_int(row.get("N3_epochs"), 0),
        "REM_epochs": as_int(row.get("REM_epochs"), 0),
        "N1_ratio_in_sleep": as_float(row.get("N1_ratio_in_sleep"), 0.0),
        "N2_ratio_in_sleep": as_float(row.get("N2_ratio_in_sleep"), 0.0),
        "N3_ratio_in_sleep": as_float(row.get("N3_ratio_in_sleep"), 0.0),
        "REM_ratio_in_sleep": as_float(row.get("REM_ratio_in_sleep"), 0.0),
        "score_valid": as_int(row.get("score_valid"), 0),
        "duration_score": as_float(row.get("duration_score"), 0.0),
        "structure_score": as_float(row.get("structure_score"), 0.0),
        "total_score": as_float(row.get("total_score"), as_float(row.get("score"), 0.0)),
        "grade": str(row.get("grade", "数据不足，暂不评分") or "数据不足，暂不评分"),
    })
    out["ts"] = as_int(row.get("ts"), fallback_ts)
    return out


def latest_sleep_epoch(room: str, bed: str):
    return normalize_sleep_epoch(latest_one(room, bed, "sleep_epoch") or {}, 0)


def latest_sleep_quality(room: str, bed: str):
    return normalize_sleep_quality(latest_one(room, bed, "sleep_quality") or {}, 0)


def latest_posture(room: str, bed: str):
    raw = latest_one(room, bed, "posture")
    if not raw:
        return posture_zero()
    z = posture_zero()
    out = dict(z)
    out.update({
        "class_idx": as_int(raw.get("class_idx"), -1),
        "class_name": str(raw.get("class_name", "未知") or "未知"),
        "confidence": as_float(raw.get("confidence"), 0.0),
        "confidence_flag": str(raw.get("confidence_flag", "none") or "none"),
        "probabilities": raw.get("probabilities", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0],
        "infer_ms": as_float(raw.get("infer_ms"), 0.0),
        "esp_set_id": as_int(raw.get("esp_set_id"), -1),
        "infer_count": as_int(raw.get("infer_count"), 0),
    })
    out["ts"] = as_int(raw.get("ts"), 0)
    return out


def normalize_emotion_probabilities(raw_probs):
    if isinstance(raw_probs, dict):
        out = {}
        for label in EMOTION_LABELS:
            out[label] = round(as_float(raw_probs.get(label), 0.0), 4)
        return out
    if isinstance(raw_probs, list):
        out = {}
        for idx, label in enumerate(EMOTION_LABELS):
            out[label] = round(as_float(raw_probs[idx] if idx < len(raw_probs) else 0.0, 0.0), 4)
        return out
    return {label: 0.0 for label in EMOTION_LABELS}


def latest_emotion(room: str, bed: str):
    raw = latest_one(room, bed, "emotion")
    if not raw:
        return emotion_zero()
    z = emotion_zero()
    out = dict(z)
    out.update({
        "label": str(raw.get("label", "未知") or "未知"),
        "confidence": as_float(raw.get("confidence"), 0.0),
        "confidence_flag": str(raw.get("confidence_flag", "none") or "none"),
        "probabilities": normalize_emotion_probabilities(raw.get("probabilities")),
        "face_count": max(0, as_int(raw.get("face_count"), 0)),
        "face_present": as_bool(raw.get("face_present"), False),
        "source": str(raw.get("source", "unknown") or "unknown"),
        "source_state": str(raw.get("source_state", "idle") or "idle"),
        "backend": str(raw.get("backend", "none") or "none"),
        "camera_index": as_int(raw.get("camera_index"), -1),
        "stable_for_ms": max(0, as_int(raw.get("stable_for_ms"), 0)),
        "infer_ms": as_float(raw.get("infer_ms"), 0.0),
        "infer_count": max(0, as_int(raw.get("infer_count"), 0)),
        "notes": str(raw.get("notes", "") or ""),
        "identity_state": str(raw.get("identity_state", "") or ""),
        "subject_id": str(raw.get("subject_id", "") or ""),
    })
    out["ts"] = as_int(raw.get("ts"), 0)
    return out


def emotion_is_fresh(emotion: dict):
    ts = as_int(emotion.get("ts"), 0)
    return ts > 0 and (now_ms() - ts) <= EMOTION_CONTEXT_TTL_MS


def build_voice_sleep_context(room: str, bed: str):
    epoch = latest_sleep_epoch(room, bed)
    quality = latest_sleep_quality(room, bed)
    radar = latest_one(room, bed, "radar") or {}
    env = latest_one(room, bed, "env") or {}
    audio = latest_one(room, bed, "audio") or {}

    brief = (
        f"当前睡眠分期{epoch.get('Final_stage', 'W')}，"
        f"睡眠评分{quality.get('total_score', 0):.1f}分，"
        f"等级{quality.get('grade', '数据不足，暂不评分')}。"
    )

    return {
        "room": room, "bed": bed,
        "record": quality.get("record") or epoch.get("record", ""),
        "sleep_stage": epoch.get("Final_stage", "W"),
        "sleep_score": as_float(quality.get("total_score"), 0.0),
        "sleep_grade": quality.get("grade", "数据不足，暂不评分"),
        "sleep_h": as_float(quality.get("sleep_h"), 0.0),
        "snore_level": as_int(audio.get("snore_level"), 0),
        "snore_count_1min": as_int(audio.get("snore_count_1min"), 0),
        "heart_bpm": as_float(radar.get("heart_bpm"), 0.0),
        "breath_bpm": as_float(radar.get("breath_bpm"), 0.0),
        "noise_db": as_float(env.get("noise_db"), 0.0),
        "co2_ppm": as_float(env.get("co2_ppm"), 0.0),
        "brief": brief,
        "ts": now_ms(),
    }


def build_voice_vitals_context(room: str, bed: str):
    radar = latest_one(room, bed, "radar") or {}
    env = latest_one(room, bed, "env") or {}
    audio = latest_one(room, bed, "audio") or {}

    heart_bpm = as_float(radar.get("heart_bpm"), 0.0)
    breath_bpm = as_float(radar.get("breath_bpm"), 0.0)
    motion = as_float(radar.get("motion"), 0.0)
    turning = as_int(radar.get("turning"), 0)
    snore_level = as_int(audio.get("snore_level"), 0)
    snore_count = as_int(audio.get("snore_count_1min"), 0)

    event_hints = []
    if turning > 0:
        event_hints.append("近期有翻身或明显体动")
    elif motion > 0:
        event_hints.append(f"体动指数{motion:.2f}")
    if snore_level > 0 or snore_count > 0:
        event_hints.append(f"鼾声等级{snore_level}，1分钟{snore_count}次")

    brief = (
        f"当前心率约{heart_bpm:.0f}次每分钟，呼吸约{breath_bpm:.0f}次每分钟。"
        if heart_bpm > 0 or breath_bpm > 0
        else "当前生命体征实时数据不足。"
    )
    if event_hints:
        brief += " " + "；".join(event_hints) + "。"

    return {
        "room": room,
        "bed": bed,
        "heart_bpm": heart_bpm,
        "breath_bpm": breath_bpm,
        "motion": motion,
        "turning": turning,
        "snore_level": snore_level,
        "snore_count_1min": snore_count,
        "noise_db": as_float(env.get("noise_db"), 0.0),
        "co2_ppm": as_float(env.get("co2_ppm"), 0.0),
        "radar_ts": as_int(radar.get("ts"), 0),
        "env_ts": as_int(env.get("ts"), 0),
        "audio_ts": as_int(audio.get("ts"), 0),
        "brief": brief,
        "ts": now_ms(),
    }


def build_voice_posture_context(room: str, bed: str):
    p = latest_posture(room, bed)
    if p.get("class_idx", -1) < 0:
        return {}
    brief = (
        f"当前睡姿为{p.get('class_name', '未知')}，"
        f"置信度{p.get('confidence', 0.0) * 100:.0f}%。"
    )
    return {
        "room": room, "bed": bed,
        "posture_class": p.get("class_name", "未知"),
        "posture_confidence": p.get("confidence", 0.0),
        "posture_flag": p.get("confidence_flag", "none"),
        "posture_probs": p.get("probabilities", [0.0, 0.0, 0.0]),
        "posture_infer_ms": p.get("infer_ms", 0.0),
        "brief": brief,
        "ts": p.get("ts", 0),
    }


def build_voice_emotion_context(room: str, bed: str):
    emotion = latest_emotion(room, bed)
    if not emotion.get("face_present") or not emotion_is_fresh(emotion):
        return {}

    label = emotion.get("label", "未知")
    confidence = emotion.get("confidence", 0.0)
    face_count = max(1, as_int(emotion.get("face_count"), 1))
    dialogue_hint = {
        "开心": "用户当前情绪较积极，正常回应并保持自然鼓励即可。",
        "自然": "用户当前情绪平稳，按常规节奏回答即可。",
        "悲伤": "用户当前可能有些低落，先表达理解，再给简单建议。",
        "恐惧": "用户当前可能紧张或不安，先安抚，再给简短可执行步骤。",
        "愤怒": "用户当前可能烦躁，语气保持平稳，少解释，多解决。",
        "厌恶": "用户当前可能有抗拒或不适，先确认不舒服的原因。",
        "蔑视": "用户当前可能不太耐烦，避免对抗，聚焦实际帮助。",
        "惊讶": "用户当前可能刚被信息触发，先确认发生了什么。",
    }.get(label, "根据用户当前状态，保持简洁、温和和有条理。")

    brief = f"当前表情倾向为{label}，置信度{confidence * 100:.0f}%，镜头内约{face_count}张人脸。"
    return {
        "room": room,
        "bed": bed,
        "label": label,
        "confidence": confidence,
        "confidence_flag": emotion.get("confidence_flag", "none"),
        "face_count": face_count,
        "source": emotion.get("source", "unknown"),
        "source_state": emotion.get("source_state", "idle"),
        "backend": emotion.get("backend", "none"),
        "stable_for_ms": emotion.get("stable_for_ms", 0),
        "subject_id": emotion.get("subject_id", ""),
        "identity_state": emotion.get("identity_state", ""),
        "dialogue_hint": dialogue_hint,
        "brief": brief,
        "ts": emotion.get("ts", 0),
    }


def build_chat_context(room: str, bed: str):
    sleep = build_voice_sleep_context(room, bed)
    emotion = build_voice_emotion_context(room, bed)
    posture = build_voice_posture_context(room, bed)

    brief_parts = []
    prompt_hints = []

    if as_float(sleep.get("sleep_h"), 0.0) > 0.0 or as_float(sleep.get("sleep_score"), 0.0) > 0.0:
        brief_parts.append(
            f"最近睡眠摘要：累计睡眠约{as_float(sleep.get('sleep_h'), 0.0):.2f}小时，"
            f"评分{as_float(sleep.get('sleep_score'), 0.0):.1f}分，"
            f"等级{sleep.get('sleep_grade', '数据不足，暂不评分')}。"
        )
        prompt_hints.append("如果用户谈到疲劳、精神状态或昨夜休息情况，可自然结合睡眠摘要给建议。")

    if emotion:
        brief_parts.append(str(emotion.get("brief", "") or ""))
        hint = str(emotion.get("dialogue_hint", "") or "")
        if hint:
            prompt_hints.append(hint)

    return {
        "scene": "awake_dialogue",
        "subject": {
            "room": room,
            "bed": bed,
            "subject_id": "",
            "identity_state": "",
            "role": "",
        },
        "policy": {
            "context_scope": "hospital_default_bed",
            "allow_sleep_summary": True,
            "allow_current_emotion": True,
            "allow_current_posture": False,
        },
        "modalities": {
            "sleep": sleep,
            "emotion": emotion,
            "posture": posture,
        },
        "brief": " ".join(x for x in brief_parts if x).strip(),
        "prompt_hints": prompt_hints,
        "ts": now_ms(),
    }


def _emotion_dialogue_hint(label: str) -> str:
    return {
        "开心": "当前操作者情绪较积极，正常回应并保持自然鼓励即可。",
        "自然": "当前操作者情绪平稳，按常规节奏回答即可。",
        "悲伤": "当前操作者可能有些低落，先表达理解，再给简单建议。",
        "恐惧": "当前操作者可能紧张或不安，先安抚，再给简短可执行步骤。",
        "愤怒": "当前操作者可能烦躁，语气保持平稳，少解释，多解决。",
        "厌恶": "当前操作者可能有抗拒或不适，先确认不舒服的原因。",
        "蔑视": "当前操作者可能不太耐烦，避免对抗，聚焦实际帮助。",
        "惊讶": "当前操作者可能刚被信息触发，先确认发生了什么。",
    }.get(label, "根据当前操作者状态，保持简洁、温和和有条理。")


def actor_can_access_target(actor_subject: dict | None, target_patient_id: str) -> bool:
    if not actor_subject:
        # No actor info = probably an internal worker call, just allow it.
        return True
    role = str(actor_subject.get("role") or "unknown")
    actor_id = str(actor_subject.get("subject_id") or "")
    if role in ("admin", "staff"):
        return True
    if role == "patient" and actor_id and actor_id == target_patient_id:
        return True
    return False


def session_is_authenticated(session: dict | None) -> bool:
    if not session:
        return False
    identity_state = str(session.get("identity_state") or "unknown")
    assurance_level = str(session.get("assurance_level") or "none")
    # Workers / voice loop don't always do face auth, so skip the check here.
    if identity_state in ("unknown", ""):
        return True
    if assurance_level in ("none", ""):
        return False
    return True


def build_memory_summary(subject_id: str, limit: int = 5):
    rows = list_memories(subject_id, limit=limit) if subject_id else []
    if not rows:
        return {"items": [], "brief": ""}
    items = []
    for row in rows:
        items.append({
            "memory_id": row.get("memory_id", ""),
            "kind": row.get("kind", ""),
            "content_compressed": row.get("content_compressed", ""),
            "visibility_scope": row.get("visibility_scope", ""),
            "source": row.get("source", ""),
            "updated_ts": row.get("updated_ts", 0),
        })
    brief = " ".join(str(x.get("content_compressed", "")).strip() for x in items if x.get("content_compressed")).strip()
    return {"items": items, "brief": brief}


def build_chat_context_v3(params: dict):
    session_id = (params.get("session_id") or [""])[0]
    session = get_session(session_id) if session_id else get_current_session()
    actor_subject = get_subject(session.get("actor_subject_id", "")) if session else None

    target_room = normalize_room((params.get("target_room") or params.get("room") or [""])[0])
    target_bed = normalize_bed((params.get("target_bed") or params.get("bed") or [""])[0])
    target_subject_id = str((params.get("target_subject_id") or [""])[0] or "")

    if (not target_room or not target_bed) and target_subject_id:
        active = get_active_assignment_for_subject(target_subject_id)
        if active:
            target_room = active.get("room", "")
            target_bed = active.get("bed", "")

    if not target_room or not target_bed:
        if BEDS:
            target_room, target_bed = BEDS[0]
            target_room = normalize_room(target_room)
            target_bed = normalize_bed(target_bed)
        else:
            target_room, target_bed = "DEFAULT", "DEFAULT"

    assignment = get_active_assignment_for_bed(target_room, target_bed)
    if not target_subject_id and assignment:
        target_subject_id = assignment.get("subject_id", "")
    target_subject = get_subject(target_subject_id) if target_subject_id else None

    authenticated = session_is_authenticated(session)
    allowed = authenticated and actor_can_access_target(actor_subject, target_subject_id)
    actor_role = str((actor_subject or {}).get("role") or (session or {}).get("role") or "unknown")
    actor_emotion = (session or {}).get("emotion", {}) if session else {}
    prompt_hints = []
    brief_parts = []

    if actor_emotion:
        label = str(actor_emotion.get("label", "未知") or "未知")
        conf = as_float(actor_emotion.get("confidence"), 0.0)
        brief_parts.append(f"当前操作者表情倾向为{label}，置信度{conf * 100:.0f}%。")
        prompt_hints.append(_emotion_dialogue_hint(label))

    sleep = {}
    vitals = {}
    posture = {}
    memory = {"items": [], "brief": ""}
    if allowed:
        sleep = build_voice_sleep_context(target_room, target_bed)
        vitals = build_voice_vitals_context(target_room, target_bed)
        posture = build_voice_posture_context(target_room, target_bed)
        if as_float(sleep.get("sleep_h"), 0.0) > 0.0 or as_float(sleep.get("sleep_score"), 0.0) > 0.0:
            brief_parts.append(
                f"目标床位最近睡眠摘要：累计睡眠约{as_float(sleep.get('sleep_h'), 0.0):.2f}小时，"
                f"评分{as_float(sleep.get('sleep_score'), 0.0):.1f}分，"
                f"等级{sleep.get('sleep_grade', '数据不足，暂不评分')}。"
            )
            prompt_hints.append("如果用户谈到目标患者疲劳、精神状态或昨夜休息情况，可自然结合睡眠摘要。")
        if target_subject_id:
            memory = build_memory_summary(target_subject_id)
            if memory.get("brief"):
                brief_parts.append("目标患者记忆摘要：" + memory["brief"])
                prompt_hints.append("结合患者偏好和护理备注时要简短自然，不要暴露无关隐私。")

    target_assignment = assignment if allowed else {}
    target_patient = target_subject if allowed else {}

    return {
        "scene": "nurse_station_dialogue",
        "actor": {
            "subject_id": (actor_subject or {}).get("subject_id", (session or {}).get("actor_subject_id", "")),
            "name": (actor_subject or {}).get("name", ""),
            "role": actor_role,
            "identity_state": (session or {}).get("identity_state", "unknown"),
            "assurance_level": (session or {}).get("assurance_level", "none"),
            "auth_methods": (session or {}).get("auth_methods", []),
            "emotion": actor_emotion,
        },
        "target": {
            "target_type": "bed",
            "room": target_room,
            "bed": target_bed,
            "assignment": target_assignment or {},
            "patient": target_patient or {},
        },
        "policy": {
            "allowed": allowed,
            "context_scope": "subject_assignment",
            "allowed_sections": ["sleep", "vitals", "posture", "memory_summary"] if allowed else [],
            "reason": "role_allowed" if allowed else (
                "not_authenticated" if not authenticated else "not_authorized_for_target"
            ),
        },
        "modalities": {
            "sleep": sleep,
            "vitals": vitals,
            "posture": posture,
            "memory": memory,
        },
        "brief": " ".join(x for x in brief_parts if x).strip(),
        "prompt_hints": prompt_hints,
        "session": session or {},
        "ts": now_ms(),
    }


def build_beds_list():
    result = []
    try:
        bed_rows = list_bed_meta()
    except Exception:
        bed_rows = [{"room": room, "bed": bed, "display_name": f"{room}-{bed}", "enabled": 1} for room, bed in BEDS]
    if not bed_rows:
        bed_rows = [{"room": room, "bed": bed, "display_name": f"{room}-{bed}", "enabled": 1} for room, bed in BEDS]
    for bed_row in bed_rows:
        room = bed_row.get("room", "")
        bed = bed_row.get("bed", "")
        r = latest_one(room, bed, "radar") or {}
        e = latest_one(room, bed, "env") or {}
        a = latest_one(room, bed, "audio") or {}
        state = _get_esp_state(room, bed)
        esp_online = (now_ms() - int(state.get("last_seen_ms", 0))) <= ESP_ONLINE_TTL_MS if state.get("last_seen_ms") else False
        po = latest_posture(room, bed)
        em = latest_emotion(room, bed)
        try:
            assignment = get_active_assignment_for_bed(room, bed)
        except Exception:
            assignment = None
        result.append({
            "room": room,
            "bed": bed,
            "display_name": bed_row.get("display_name", f"{room}-{bed}"),
            "enabled": bool(bed_row.get("enabled", 1)),
            "assignment": assignment or {},
            "status": {
                "radar": source_online(r.get("ts", 0)),
                "env": source_online(e.get("ts", 0)),
                "audio": source_online(a.get("ts", 0)),
                "esp": "online" if esp_online else "offline",
                "emotion": source_online(em.get("ts", 0), ttl_ms=EMOTION_CONTEXT_TTL_MS),
            },
            "posture": {
                "class_name": po.get("class_name", "未知"),
                "confidence": po.get("confidence", 0.0),
            },
            "emotion": {
                "label": em.get("label", "未知"),
                "confidence": em.get("confidence", 0.0),
                "face_present": em.get("face_present", False),
            },
        })
    return result


def import_sleep_outputs_once(force: bool = False):
    return sleep_importer_module.import_sleep_outputs_once(
        force=force,
        beds=BEDS,
        normalize_sleep_epoch=normalize_sleep_epoch,
        normalize_sleep_quality=normalize_sleep_quality,
        replace_items=replace_items,
    )


def run_sleep_output_importer():
    return sleep_importer_module.run_sleep_output_importer(import_sleep_outputs_once)


# =====================
# Bemfa TCP Subscription
# =====================

def parse_cmd2_line(line: str):
    try:
        qs = {}
        for part in line.split("&"):
            key, sep, value = part.partition("=")
            if not sep:
                continue
            qs[unquote(key)] = unquote(value)

        if qs.get("cmd", "") != "2":
            return None, None
        topic = qs.get("topic")
        msg = qs.get("msg")
        if topic is None:
            return None, None
        return topic, msg
    except Exception:
        return None, None


def parse_posture_payload(base64_str: str) -> bytes | None:
    """解码 base64 编码的二进制 payload。"""
    if not base64_str:
        return None
    try:
        data = base64.b64decode(base64_str)
        return data
    except Exception:
        return None


def bemfa_tcp_sub_loop():
    """持久 TCP 连接巴法云，订阅所有床位 topic，接收推送数据写入缓存。"""
    if not BEMFA_UID:
        print("[BEMFA] WARNING: BEMFA_UID not set, subscription skipped")
        return

    while True:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((BEMFA_HOST, BEMFA_TCP_PORT))
            s.settimeout(1.0)

            sub = f"cmd=1&uid={BEMFA_UID}&topic={','.join(ALL_TOPICS)}\r\n"
            s.sendall(sub.encode("utf-8"))
            print(f"[BEMFA] SUB: topics={len(ALL_TOPICS)} host={BEMFA_HOST}:{BEMFA_TCP_PORT}")

            last_ping = time.time()
            buf = b""

            while True:
                if time.time() - last_ping >= 55:
                    s.sendall(b"ping\r\n")
                    last_ping = time.time()

                try:
                    data = s.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    raise RuntimeError("TCP disconnected")

                buf += data
                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    line = raw_line.decode("utf-8", errors="ignore").strip("\r").strip()
                    if not line:
                        continue

                    topic, msg = parse_cmd2_line(line)
                    if not topic:
                        continue
                    if topic not in TOPIC_TO_BED_AND_KIND:
                        continue

                    room, bed, kind = TOPIC_TO_BED_AND_KIND[topic]

                    # Handle ESP posture binary data (tof1/tof2/mlx1/mlx2)
                    if kind in POSTURE_STREAMS:
                        payload_json = safe_json_loads(msg) if msg else None
                        if isinstance(payload_json, dict):
                            b64_data = payload_json.get("payload_b64", "")
                            bin_payload = parse_posture_payload(b64_data)
                            if bin_payload:
                                sensor_type = 0x02 if kind.startswith("tof") else 0x01
                                sensor_id = 0x01 if kind.endswith("1") else 0x02
                                crc = 0  # CRC not verified over cloud relay
                                append_esp_packet(room, bed, sensor_type, sensor_id,
                                                  bin_payload, crc, f"bemfa:{topic}", True)
                                state = _get_esp_state(room, bed)
                                with esp_lock:
                                    state["bytes_rx"] += len(bin_payload)
                        continue

                    # Handle sensor data (radar/env/audio)
                    payload = None
                    if msg and msg != "NULL":
                        payload = safe_json_loads(msg)

                    ts = None
                    if isinstance(payload, dict) and "ts" in payload:
                        try:
                            ts = int(payload["ts"])
                        except Exception:
                            ts = None
                    if ts is None:
                        ts = now_ms()

                    item = {"ts": ts}
                    if isinstance(payload, dict):
                        item.update(payload)
                    else:
                        item["raw"] = msg

                    append_item(room, bed, kind, item)

        except Exception as e:
            print(f"[BEMFA] ERROR: {e!r}, reconnect in 2s...")
            try:
                if s:
                    s.close()
            except Exception:
                pass
            time.sleep(2)


# =====================
# HTTP API Handler
# =====================

BODY_TOO_LARGE = object()


def _get_room_bed(params):
    """从查询参数中提取 room/bed，未指定时返回第一个床位。"""
    room = (params.get("room") or [None])[0]
    bed = (params.get("bed") or [None])[0]
    if room and bed:
        return room, bed
    if BEDS:
        return BEDS[0][0], BEDS[0][1]
    return "default", "default"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body_bytes, content_type="application/json; charset=utf-8", extra_headers=None):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body_bytes)))
        if extra_headers:
            for key, value in extra_headers:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body_bytes)

    def _json(self, obj, code=200, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, body, extra_headers=extra_headers)

    def _html(self, html, code=200):
        self._send(code, html.encode("utf-8"), "text/html; charset=utf-8")

    def _read_json(self):
        length = as_int(self.headers.get("Content-Length"), 0)
        if length <= 0:
            return None
        if length > MAX_JSON_BODY_BYTES:
            return BODY_TOO_LARGE
        raw = self.rfile.read(length)
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def _admin_cookie_token(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            name, sep, value = part.strip().partition("=")
            if sep and name == ADMIN_SESSION_COOKIE:
                return value
        return ""

    def _admin_session(self) -> dict | None:
        if not ADMIN_AUTH_ENABLED:
            return {"username": "disabled", "subject_id": DEFAULT_ADMIN_SUBJECT_ID}
        return get_admin_http_session(self._admin_cookie_token())

    def _is_local_request(self) -> bool:
        host = self.client_address[0] if self.client_address else ""
        try:
            return ipaddress.ip_address(host).is_loopback
        except Exception:
            return host in ("localhost", "127.0.0.1", "::1")

    def _path_allows_local_service(self, path: str) -> bool:
        if path.startswith("/api/v2/"):
            return True
        if path.startswith("/api/esp/"):
            return True
        if path in (
            "/api/v3/context/chat",
            "/api/v3/identity/gallery",
            "/api/v3/identity/match",
            "/api/v3/vision/observation",
        ):
            return True
        return False

    def _authorized_for_api(self, path: str) -> bool:
        if self._admin_session() is not None:
            return True
        if self._is_local_request():
            return True
        return False

    def _deny_auth(self):
        self._json({"error": "admin authentication required"}, code=401)

    def _set_admin_cookie_headers(self, token: str):
        max_age_s = max(60, ADMIN_SESSION_TTL_MS // 1000)
        return [(
            "Set-Cookie",
            f"{ADMIN_SESSION_COOKIE}={token}; Max-Age={max_age_s}; Path=/; HttpOnly; SameSite=Lax",
        )]

    def _clear_admin_cookie_headers(self):
        return [(
            "Set-Cookie",
            f"{ADMIN_SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax",
        )]

    def _handle_admin_auth_get(self):
        session = self._admin_session()
        self._json({
            "ok": True,
            "setup_required": ADMIN_AUTH_ENABLED and not admin_account_exists(),
            "authenticated": bool(session),
            "session": session or {},
            "auth_enabled": ADMIN_AUTH_ENABLED,
            "ts": now_ms(),
        })

    def _handle_admin_setup(self, body):
        if not ADMIN_AUTH_ENABLED:
            self._json({"ok": True, "auth_enabled": False, "ts": now_ms()})
            return
        try:
            account = create_admin_account(body if isinstance(body, dict) else {})
            token, session = create_admin_http_session(account["username"])
            session["subject_id"] = account["subject_id"]
            self._json(
                {"ok": True, "account": account, "session": session, "ts": now_ms()},
                extra_headers=self._set_admin_cookie_headers(token),
            )
        except (ValueError, sqlite3.IntegrityError) as e:
            self._json({"error": str(e)}, code=400)

    def _handle_admin_login(self, body):
        if not ADMIN_AUTH_ENABLED:
            self._json({"ok": True, "auth_enabled": False, "ts": now_ms()})
            return
        try:
            token, session = login_admin_account(body if isinstance(body, dict) else {})
            self._json(
                {"ok": True, "session": session, "ts": now_ms()},
                extra_headers=self._set_admin_cookie_headers(token),
            )
        except ValueError as e:
            self._json({"error": str(e)}, code=401)

    def _handle_admin_logout(self):
        delete_admin_http_session(self._admin_cookie_token())
        self._json({"ok": True, "ts": now_ms()}, extra_headers=self._clear_admin_cookie_headers())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        q = urlparse(self.path)
        params = parse_qs(q.query)

        if q.path == "/" or q.path == "/dashboard":
            if ADMIN_AUTH_ENABLED and not self._admin_session():
                self._html(load_admin_auth_html(setup_mode=not admin_account_exists()))
                return
            self._html(load_dashboard_html())
            return

        if q.path == "/admin":
            if ADMIN_AUTH_ENABLED and not self._admin_session():
                self._html(load_admin_auth_html(setup_mode=not admin_account_exists()))
                return
            self._html(load_admin_html())
            return

        if q.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return

        if q.path == "/health":
            self._json({
                "ok": True,
                "mode": "bemfa",
                "location": LOCATION,
                "beds": len(BEDS),
                "topics": len(ALL_TOPICS),
                "minutes": HISTORY_MINUTES,
            })
            return

        if q.path == "/api/v3/admin/auth":
            self._handle_admin_auth_get()
            return

        if q.path.startswith("/api/") and ADMIN_AUTH_ENABLED and not self._authorized_for_api(q.path):
            self._deny_auth()
            return

        if q.path == "/api/v3/identity/gallery" and ADMIN_AUTH_ENABLED and not self._is_local_request():
            self._json({"error": "identity gallery is local-service only"}, code=403)
            return

        if q.path == "/api/v2/beds":
            self._json({"beds": build_beds_list(), "ts": now_ms()})
            return

        if q.path == "/api/v3/beds":
            self._json({"beds": build_beds_list(), "db": DB_FILE, "ts": now_ms()})
            return

        if q.path == "/api/v3/subjects":
            role = (params.get("role") or [""])[0]
            status = (params.get("status") or [""])[0]
            self._json({"subjects": list_subjects(role=role, status=status), "ts": now_ms()})
            return

        if q.path.startswith("/api/v3/subjects/"):
            subject_id = q.path.rsplit("/", 1)[-1]
            subject = get_subject(subject_id)
            if not subject:
                self._json({"error": "subject not found", "subject_id": subject_id}, code=404)
                return
            subject["active_assignment"] = get_active_assignment_for_subject(subject_id) or {}
            subject["memories"] = list_memories(subject_id, limit=20)
            self._json(subject)
            return

        if q.path == "/api/v3/assignments":
            subject_id = (params.get("subject_id") or [""])[0]
            room_q = (params.get("room") or [""])[0]
            bed_q = (params.get("bed") or [""])[0]
            status = (params.get("status") or [""])[0]
            self._json({
                "assignments": list_assignments(subject_id=subject_id, room=room_q, bed=bed_q, status=status),
                "ts": now_ms(),
            })
            return

        if q.path == "/api/v3/memories":
            subject_id = (params.get("subject_id") or [""])[0]
            limit = as_int((params.get("limit") or ["20"])[0], 20)
            self._json({"memories": list_memories(subject_id, limit=limit), "ts": now_ms()})
            return

        if q.path == "/api/v3/credentials":
            subject_id = (params.get("subject_id") or [""])[0]
            credential_type = (params.get("type") or [""])[0]
            include_template = as_int((params.get("include_template") or ["0"])[0], 0) == 1
            if include_template and ADMIN_AUTH_ENABLED and not self._is_local_request():
                self._json({"error": "credential templates are local-service only"}, code=403)
                return
            self._json({
                "credentials": list_credentials(
                    subject_id=subject_id,
                    credential_type=credential_type,
                    include_template=include_template,
                ),
                "ts": now_ms(),
            })
            return

        if q.path == "/api/v3/identity/gallery":
            credential_type = (params.get("type") or ["face"])[0]
            self._json({
                "type": credential_type,
                "credentials": list_identity_gallery(credential_type),
                "thresholds": {
                    "recognized": FACE_MATCH_RECOGNIZED_THRESHOLD,
                    "candidate": FACE_MATCH_CANDIDATE_THRESHOLD,
                },
                "runtime_error": IDENTITY_RUNTIME_ERROR,
                "ts": now_ms(),
            })
            return

        if q.path == "/api/v3/session/current":
            self._json({"session": get_current_session() or {}, "ts": now_ms()})
            return

        if q.path == "/api/v3/context/chat":
            self._json(build_chat_context_v3(params))
            return

        room, bed = _get_room_bed(params)

        if q.path == "/api/esp/status":
            self._json(get_esp_status(room, bed))
            return

        if q.path == "/api/esp/set/latest":
            include_payload = as_int((params.get("payload") or ["0"])[0], 0) == 1
            one_set = get_latest_esp_set(room, bed, include_payload=include_payload)
            self._json({
                "ok": True,
                "room": room,
                "bed": bed,
                "has_set": bool(one_set),
                "store_depth": ESP_STORE_DEPTH,
                "set": one_set,
                "ts": now_ms(),
            })
            return

        if q.path == "/api/v2/latest":
            r = latest_one(room, bed, "radar") or {"ts": 0}
            e = latest_one(room, bed, "env") or {"ts": 0}
            a = latest_one(room, bed, "audio") or {"ts": 0}
            ep = latest_sleep_epoch(room, bed)
            sq = latest_sleep_quality(room, bed)
            po = latest_posture(room, bed)
            em = latest_emotion(room, bed)

            obj = {
                "room": room,
                "bed": bed,
                "location": LOCATION,
                "status": {
                    "radar": source_online(r.get("ts", 0)),
                    "env": source_online(e.get("ts", 0)),
                    "audio": source_online(a.get("ts", 0)),
                    "emotion": source_online(em.get("ts", 0), ttl_ms=EMOTION_CONTEXT_TTL_MS),
                },
                "radar": r if r.get("ts") else {},
                "env": e if e.get("ts") else {},
                "audio": a if a.get("ts") else {},
                "sleep": {
                    "record": sq.get("record") or ep.get("record", ""),
                    "final_stage": ep.get("Final_stage", "W"),
                    "sleep_score": as_float(sq.get("total_score"), 0.0),
                    "sleep_grade": sq.get("grade", "数据不足，暂不评分"),
                    "sleep_h": as_float(sq.get("sleep_h"), 0.0),
                },
                "posture": {
                    "class_name": po.get("class_name", "未知"),
                    "confidence": po.get("confidence", 0.0),
                    "confidence_flag": po.get("confidence_flag", "none"),
                    "probabilities": po.get("probabilities", [0.0, 0.0, 0.0]),
                    "infer_ms": po.get("infer_ms", 0.0),
                    "infer_count": po.get("infer_count", 0),
                },
                "emotion": {
                    "label": em.get("label", "未知"),
                    "confidence": em.get("confidence", 0.0),
                    "confidence_flag": em.get("confidence_flag", "none"),
                    "probabilities": em.get("probabilities", {}),
                    "face_count": em.get("face_count", 0),
                    "face_present": em.get("face_present", False),
                    "source": em.get("source", "unknown"),
                    "source_state": em.get("source_state", "idle"),
                    "backend": em.get("backend", "none"),
                    "stable_for_ms": em.get("stable_for_ms", 0),
                    "infer_ms": em.get("infer_ms", 0.0),
                    "infer_count": em.get("infer_count", 0),
                    "notes": em.get("notes", ""),
                    "subject_id": em.get("subject_id", ""),
                    "identity_state": em.get("identity_state", ""),
                    "ts": em.get("ts", 0),
                },
                "ts": now_ms(),
            }
            self._json(obj)
            return

        if q.path == "/api/v2/rrhr":
            minutes = int((params.get("minutes") or ["30"])[0])
            step = int((params.get("step") or ["10"])[0])
            s = series(room, bed, "radar", minutes=minutes, step_s=step)
            table = []
            for it in s:
                table.append({
                    "time": to_timestr(int(it["ts"])),
                    "breath_bpm": float(it.get("breath_bpm", 0) or 0),
                    "heart_bpm": float(it.get("heart_bpm", 0) or 0),
                    "motion": float(it.get("motion", 0) or 0),
                    "turning": int(it.get("turning", 0) or 0),
                })
            self._json({"table": table})
            return

        if q.path == "/api/v2/env_latest":
            e = latest_one(room, bed, "env") or {}
            self._json({
                "co2_ppm": float(e.get("co2_ppm", 0) or 0),
                "temp_c": float(e.get("temp_c", 0) or 0),
                "rh": float(e.get("rh", 0) or 0),
                "noise_db": float(e.get("noise_db", 0) or 0),
                "ts": int(e.get("ts", 0) or 0),
            })
            return

        if q.path == "/api/v2/turn_stats":
            minutes = int((params.get("minutes") or ["30"])[0])
            s = series(room, bed, "radar", minutes=minutes, step_s=5)
            turn_cnt = sum(1 for it in s if int(it.get("turning", 0) or 0) == 1)
            motions = [float(it.get("motion", 0) or 0) for it in s]
            motion_avg = sum(motions) / len(motions) if motions else 0.0
            self._json({
                "minutes": minutes,
                "turn_count": turn_cnt,
                "motion_avg": round(motion_avg, 3),
                "ts": now_ms(),
            })
            return

        if q.path == "/api/v2/snore_count_latest":
            a = latest_one(room, bed, "audio") or {}
            self._json({
                "snore_count_1min": int(a.get("snore_count_1min", 0) or 0),
                "snore_level": int(a.get("snore_level", 0) or 0),
                "ts": int(a.get("ts", 0) or 0),
            })
            return

        if q.path == "/api/v2/snore_db_range":
            minutes = int((params.get("minutes") or ["30"])[0])
            bucket_min = int((params.get("bucket") or ["5"])[0])
            env_s = series(room, bed, "env", minutes=minutes, step_s=10)
            if not env_s:
                self._json({"table": []})
                return
            buckets = defaultdict(list)
            for it in env_s:
                ts = int(it["ts"])
                lt = time.localtime(ts / 1000)
                mm = (lt.tm_min // bucket_min) * bucket_min
                key = time.strftime(f"%H:{mm:02d}", lt)
                db = float(it.get("noise_db", 0) or 0)
                buckets[key].append(db)
            table = []
            for k in sorted(buckets.keys()):
                arr = buckets[k]
                table.append({"name": k, "start": round(min(arr), 1), "end": round(max(arr), 1)})
            self._json({"table": table})
            return

        if q.path == "/api/v2/sleep_score_bar":
            minutes = int((params.get("minutes") or ["30"])[0])
            bucket_min = int((params.get("bucket") or ["5"])[0])
            radar_s = series(room, bed, "radar", minutes=minutes, step_s=10)
            env_s = series(room, bed, "env", minutes=minutes, step_s=10)
            audio_s = series(room, bed, "audio", minutes=minutes, step_s=10)
            if not radar_s:
                self._json({"table": []})
                return

            def bucketize(seq):
                m = {}
                for it in seq:
                    ts = int(it["ts"])
                    lt = time.localtime(ts / 1000)
                    mm = (lt.tm_min // bucket_min) * bucket_min
                    key = time.strftime(f"%H:{mm:02d}", lt)
                    if key not in m or int(m[key]["ts"]) < ts:
                        m[key] = it
                return m

            br = bucketize(radar_s)
            be = bucketize(env_s)
            ba = bucketize(audio_s)
            keys = sorted(set(br.keys()) | set(be.keys()) | set(ba.keys()))
            table = []
            for k in keys:
                r = br.get(k, {})
                e = be.get(k, {})
                a = ba.get(k, {})
                score = compute_sleep_score(r, e, a)
                table.append({"time": k, "score": score})
            self._json({"table": table})
            return

        if q.path == "/api/v2/sleep/epoch/latest":
            self._json(latest_sleep_epoch(room, bed))
            return

        if q.path == "/api/v2/sleep/quality/latest":
            self._json(latest_sleep_quality(room, bed))
            return

        if q.path == "/api/v2/sleep/model_input/latest":
            ep = latest_sleep_epoch(room, bed)
            self._json({
                "record": ep.get("record", ""),
                "start_s": as_float(ep.get("start_s"), 0.0),
                "end_s": as_float(ep.get("end_s"), 0.0),
                "BR_mean": as_float(ep.get("BR_mean"), 0.0),
                "BR_std": as_float(ep.get("BR_std"), 0.0),
                "HR_mean": as_float(ep.get("HR_mean"), 0.0),
                "HR_std": as_float(ep.get("HR_std"), 0.0),
                "RMSSD": as_float(ep.get("RMSSD"), 0.0),
                "SDNN": as_float(ep.get("SDNN"), 0.0),
                "EEG_stage": ep.get("EEG_stage", "W"),
                "EEG_conf": as_float(ep.get("EEG_conf"), 0.0),
                "ts": as_int(ep.get("ts"), 0),
            })
            return

        if q.path == "/api/v2/sleep/epoch/list":
            limit = as_int((params.get("limit") or ["120"])[0], 120)
            record = (params.get("record") or [""])[0]
            rows = [normalize_sleep_epoch(x, 0) for x in list_latest(room, bed, "sleep_epoch", limit=limit, record=record)]
            self._json({"table": rows})
            return

        if q.path == "/api/v2/sleep/quality/list":
            limit = as_int((params.get("limit") or ["120"])[0], 120)
            record = (params.get("record") or [""])[0]
            rows = [normalize_sleep_quality(x, 0) for x in list_latest(room, bed, "sleep_quality", limit=limit, record=record)]
            self._json({"table": rows})
            return

        if q.path == "/api/v2/voice/sleep_context":
            self._json(build_voice_sleep_context(room, bed))
            return

        if q.path == "/api/v2/posture/latest":
            self._json(latest_posture(room, bed))
            return

        if q.path == "/api/v2/voice/posture_context":
            self._json(build_voice_posture_context(room, bed))
            return

        if q.path == "/api/v2/emotion/latest":
            self._json(latest_emotion(room, bed))
            return

        if q.path == "/api/v2/voice/emotion_context":
            self._json(build_voice_emotion_context(room, bed))
            return

        if q.path == "/api/v2/emotion/history":
            limit = as_int((params.get("limit") or ["20"])[0], 20)
            rows = list_latest(room, bed, "emotion", limit=limit)
            self._json({"table": rows})
            return

        if q.path == "/api/v2/voice/chat_context":
            self._json(build_chat_context(room, bed))
            return

        if q.path == "/api/v2/posture/history":
            limit = as_int((params.get("limit") or ["20"])[0], 20)
            rows = list_latest(room, bed, "posture", limit=limit)
            self._json({"table": rows})
            return

        if q.path == "/api/v2/sleep/import_now":
            import_sleep_outputs_once(force=True)
            self._json({"ok": True, "msg": "import completed", "ts": now_ms()})
            return

        self._json({"error": "not found", "path": q.path}, code=404)

    def do_POST(self):
        q = urlparse(self.path)
        body = self._read_json()
        if body is BODY_TOO_LARGE:
            self._json({"error": "request body too large", "max_bytes": MAX_JSON_BODY_BYTES}, code=413)
            return
        if body is None:
            self._json({"error": "invalid json"}, code=400)
            return

        # Extract room/bed from POST body or query params
        params = parse_qs(q.query)
        body_obj = body if isinstance(body, dict) else {}

        if q.path == "/api/v3/admin/setup":
            self._handle_admin_setup(body_obj)
            return

        if q.path == "/api/v3/admin/login":
            self._handle_admin_login(body_obj)
            return

        if q.path == "/api/v3/admin/logout":
            self._handle_admin_logout()
            return

        if q.path.startswith("/api/") and ADMIN_AUTH_ENABLED and not self._authorized_for_api(q.path):
            self._deny_auth()
            return

        if q.path == "/api/v3/subjects":
            try:
                self._json({"ok": True, "subject": create_subject(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path == "/api/v3/assignments":
            try:
                self._json({"ok": True, "assignment": create_assignment(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path.startswith("/api/v3/assignments/") and q.path.endswith("/close"):
            assignment_id = q.path.split("/")[-2]
            self._json({"ok": True, "assignment": close_assignment(assignment_id), "ts": now_ms()})
            return

        if q.path == "/api/v3/memories":
            try:
                self._json({"ok": True, "memory": create_memory(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path == "/api/v3/credentials/enroll":
            try:
                self._json({"ok": True, "credential": create_credential_from_enrollment(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path == "/api/v3/credentials":
            try:
                self._json({"ok": True, "credential": create_credential(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path == "/api/v3/identity/match":
            try:
                self._json({"ok": True, "identity": match_identity(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path == "/api/v3/sessions":
            try:
                self._json({"ok": True, "session": upsert_session(body_obj), "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        if q.path == "/api/v3/vision/observation":
            try:
                session = create_session_from_observation(body_obj)
                self._json({"ok": True, "session": session, "ts": now_ms()})
            except (ValueError, sqlite3.IntegrityError) as e:
                self._json({"error": str(e)}, code=400)
            return

        room = str(body_obj.get("room", "") or (params.get("room") or [""])[0])
        bed = str(body_obj.get("bed", "") or (params.get("bed") or [""])[0])
        if not room or not bed:
            if BEDS:
                room, bed = BEDS[0]
            else:
                room, bed = "default", "default"

        if q.path == "/api/v2/ingest":
            if not isinstance(body, dict):
                self._json({"error": "payload must be object for /api/v2/ingest"}, code=400)
                return
            kind = str(body.get("kind", "") or "")
            payload = body.get("payload", body)
            if kind not in ALL_KINDS:
                self._json({"error": "invalid kind", "kinds": list(ALL_KINDS)}, code=400)
                return
            if isinstance(payload, list):
                n = 0
                for x in payload:
                    if isinstance(x, dict):
                        append_item(room, bed, kind, x)
                        n += 1
                self._json({"ok": True, "kind": kind, "room": room, "bed": bed, "ingested": n, "ts": now_ms()})
                return
            if not isinstance(payload, dict):
                self._json({"error": "payload must be object or list"}, code=400)
                return
            append_item(room, bed, kind, payload)
            self._json({"ok": True, "kind": kind, "room": room, "bed": bed, "ingested": 1, "ts": now_ms()})
            return

        if q.path == "/api/v2/ingest/sleep_epoch":
            rows = body if isinstance(body, list) else [body]
            n = 0
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                item = normalize_sleep_epoch(row, now_ms() + i)
                append_item(room, bed, "sleep_epoch", item)
                n += 1
            self._json({"ok": True, "kind": "sleep_epoch", "room": room, "bed": bed, "ingested": n, "ts": now_ms()})
            return

        if q.path == "/api/v2/ingest/sleep_quality":
            rows = body if isinstance(body, list) else [body]
            n = 0
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                item = normalize_sleep_quality(row, now_ms() + i)
                append_item(room, bed, "sleep_quality", item)
                n += 1
            self._json({"ok": True, "kind": "sleep_quality", "room": room, "bed": bed, "ingested": n, "ts": now_ms()})
            return

        if q.path == "/api/v2/ingest/posture":
            row = body if isinstance(body, dict) else (body[0] if isinstance(body, list) and body else None)
            if not isinstance(row, dict):
                self._json({"error": "payload must be object"}, code=400)
                return
            item = dict(posture_zero())
            item.update({
                "class_idx": as_int(row.get("class_idx"), -1),
                "class_name": str(row.get("class_name", "未知") or "未知"),
                "confidence": as_float(row.get("confidence"), 0.0),
                "confidence_flag": str(row.get("confidence_flag", "none") or "none"),
                "probabilities": row.get("probabilities", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0],
                "infer_ms": as_float(row.get("infer_ms"), 0.0),
                "esp_set_id": as_int(row.get("esp_set_id"), -1),
                "infer_count": as_int(row.get("infer_count"), 0),
            })
            item["ts"] = as_int(row.get("ts"), now_ms())
            append_item(room, bed, "posture", item)
            self._json({"ok": True, "kind": "posture", "room": room, "bed": bed, "ingested": 1, "ts": now_ms()})
            return

        if q.path == "/api/v2/ingest/emotion":
            row = body if isinstance(body, dict) else (body[0] if isinstance(body, list) and body else None)
            if not isinstance(row, dict):
                self._json({"error": "payload must be object"}, code=400)
                return
            item = dict(emotion_zero())
            item.update({
                "label": str(row.get("label", "未知") or "未知"),
                "confidence": as_float(row.get("confidence"), 0.0),
                "confidence_flag": str(row.get("confidence_flag", "none") or "none"),
                "probabilities": normalize_emotion_probabilities(row.get("probabilities")),
                "face_count": max(0, as_int(row.get("face_count"), 0)),
                "face_present": as_bool(row.get("face_present"), False),
                "source": str(row.get("source", "unknown") or "unknown"),
                "source_state": str(row.get("source_state", "idle") or "idle"),
                "backend": str(row.get("backend", "none") or "none"),
                "camera_index": as_int(row.get("camera_index"), -1),
                "stable_for_ms": max(0, as_int(row.get("stable_for_ms"), 0)),
                "infer_ms": as_float(row.get("infer_ms"), 0.0),
                "infer_count": max(0, as_int(row.get("infer_count"), 0)),
                "notes": str(row.get("notes", "") or ""),
                "subject_id": str(row.get("subject_id", "") or ""),
                "identity_state": str(row.get("identity_state", "") or ""),
            })
            item["ts"] = as_int(row.get("ts"), now_ms())
            append_item(room, bed, "emotion", item)
            session = None
            identity = row.get("identity") if isinstance(row.get("identity"), dict) else {}
            if identity or item.get("subject_id"):
                if not identity:
                    identity = {
                        "type": "face",
                        "auth_method": "face",
                        "subject_id": item.get("subject_id", ""),
                        "identity_state": item.get("identity_state") or "recognized",
                        "confidence": as_float(row.get("identity_confidence"), item.get("confidence", 0.0)),
                    }
                session = create_session_from_observation({"identity": identity, "emotion": item, "ts": item["ts"]})
            self._json({
                "ok": True,
                "kind": "emotion",
                "room": room,
                "bed": bed,
                "ingested": 1,
                "session": session or {},
                "ts": now_ms(),
            })
            return

        if q.path == "/api/v2/sleep/import_now":
            import_sleep_outputs_once(force=True)
            self._json({"ok": True, "msg": "import completed", "ts": now_ms()})
            return

        self._json({"error": "not found", "path": q.path}, code=404)


# =====================
# Main
# =====================

def main():
    print_config()
    init_management_db()
    errors = validate()
    if errors:
        for err in errors:
            print(f"[GATEWAY] ERROR: {err}")
        if "BEMFA_UID" in " ".join(errors):
            print("[GATEWAY] BEMFA_UID 未设置：将跳过巴法云订阅，但继续启动本地 HTTP/API")

    t = threading.Thread(target=bemfa_tcp_sub_loop, daemon=True)
    t.start()

    if SLEEP_IMPORT_ENABLED:
        ti = threading.Thread(target=run_sleep_output_importer, daemon=True)
        ti.start()

    server = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), Handler)
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/health")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/latest?room=R1203&bed=B1")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/emotion/latest?room=R1203&bed=B1")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/voice/emotion_context?room=R1203&bed=B1")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/voice/chat_context?room=R1203&bed=B1")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/beds")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v3/beds")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v3/subjects")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v3/context/chat?target_room=R1203&target_bed=B1")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/admin")
    server.serve_forever()


if __name__ == "__main__":
    main()

