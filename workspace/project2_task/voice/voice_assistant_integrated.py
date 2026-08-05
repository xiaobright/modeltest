# -*- coding: utf-8 -*-
"""
集成版：语音→识别→意图 or LLM→播报（合并：情感对话 + 天气联网 + 强化意图）
- 指令口令优先：拼音模糊 + 关键词 + 正则 + 高分直通（短口令友好）
- 情感对话：离线“情绪规则”加持（安抚+可执行建议），LLM 只润色
- 天气：优先 QWeather（有 KEY），否则 Open-Meteo；记住城市
- TTS：优先 Piper(.onnx)，找不到则自动 SAPI 中文
"""

import os, re, sys, time, queue, wave, tempfile, subprocess, json, random
from typing import Optional, Tuple
import numpy as np
import requests
from faster_whisper import WhisperModel
from pypinyin import lazy_pinyin
from rapidfuzz import fuzz

try:
    import webrtcvad

    VAD_BACKEND_OK = True
    VAD_BACKEND_ERROR = ""
except Exception as _vad_exc:  # noqa: BLE001
    webrtcvad = None
    VAD_BACKEND_OK = False
    VAD_BACKEND_ERROR = str(_vad_exc)

try:
    import sounddevice as sd
    import soundfile as sf

    AUDIO_BACKEND_OK = True
    AUDIO_BACKEND_ERROR = ""
except Exception as _audio_exc:  # noqa: BLE001
    sd = None
    sf = None
    AUDIO_BACKEND_OK = False
    AUDIO_BACKEND_ERROR = str(_audio_exc)

# ============ 基础配置 ============
SR = 16000
CH = 1
FRAME_MS = 20
ASR_MODEL_SIZE = "small"   # PC 建议 small；板子不够可改 tiny
ASR_COMPUTE = "int8"       # 不行可用 "int8_float16"/"float32"

# 本地 RKLLM（阶段2：模型常驻内存，整段阻塞式问答）
VOICE_DIR = os.path.dirname(__file__)
RKLLM_PROJECT_DIR = os.path.abspath(os.getenv("RKLLM_PROJECT_DIR", os.path.join(VOICE_DIR, "..", "rkllm_py")))
RKLLM_SO_PATH = os.path.abspath(os.getenv("RKLLM_SO_PATH", os.path.join(RKLLM_PROJECT_DIR, "librkllmrt.so")))
RKLLM_MODEL_DIR = os.path.abspath(os.getenv("RKLLM_MODEL_DIR", os.path.join(VOICE_DIR, "..", "..", "model")))
RKLLM_MODEL_PATH = os.path.abspath(os.getenv("RKLLM_MODEL_PATH", os.path.join(RKLLM_MODEL_DIR, "Qwen3-1.7B_W8A8_RK3588.rkllm")))
RKLLM_MAX_NEW_TOKENS = int(os.getenv("RKLLM_MAX_NEW_TOKENS", "256"))
RKLLM_MAX_CONTEXT_LEN = int(os.getenv("RKLLM_MAX_CONTEXT_LEN", "4096"))
RKLLM_MAX_CHAT_TURNS = int(os.getenv("RKLLM_MAX_CHAT_TURNS", "6"))
VOICE_INPUT_MODE = os.getenv("VOICE_INPUT_MODE", "mic").strip().lower()

# 房间/床位绑定
VOICE_ROOM = os.getenv("VOICE_ROOM", "R1203")
VOICE_BED = os.getenv("VOICE_BED", "B1")
VOICE_SESSION_ID = os.getenv("VOICE_SESSION_ID", "").strip()
VOICE_TARGET_SUBJECT_ID = os.getenv("VOICE_TARGET_SUBJECT_ID", "").strip()

# 网关授权上下文（gateway 负责 session、权限和数据裁剪）
GATEWAY_BASE = os.getenv("GATEWAY_BASE", "http://127.0.0.1:8765").rstrip("/")
GATEWAY_CHAT_CONTEXT_URL = os.getenv("GATEWAY_CHAT_CONTEXT_URL", f"{GATEWAY_BASE}/api/v3/context/chat")
GATEWAY_TIMEOUT_S = float(os.getenv("GATEWAY_TIMEOUT_S", "1.5"))
GATEWAY_CONTEXT_ENABLED = os.getenv("GATEWAY_CONTEXT_ENABLED", "1") not in ("0", "false", "False")

# Piper（若文件存在则优先用）
PIPER_MODEL = r"C:\voices\zh_cn\zh_CN-huayan-medium.onnx"
PIPER_EXE = "piper"
USE_PIPER = os.path.isfile(PIPER_MODEL)

if RKLLM_PROJECT_DIR not in sys.path:
    sys.path.insert(0, RKLLM_PROJECT_DIR)

try:
    from rkllm_sdk.client import LLMConfig, RKLLMClient, SamplingConfig

    RKLLM_IMPORT_ERROR = ""
except Exception as _rkllm_import_exc:  # noqa: BLE001
    RKLLMClient = None
    LLMConfig = None
    SamplingConfig = None
    RKLLM_IMPORT_ERROR = str(_rkllm_import_exc)

# ============ 天气配置与偏好文件 ============
QWEATHER_KEY = os.getenv("QWEATHER_KEY")  # 无则为 None
PREF_FILE = os.path.join(VOICE_DIR, "user_prefs.json")

# ============ 轻量情绪规则（离线） ============
EMO_LEX = {
    "anxious": ["担心", "焦虑", "紧张", "害怕", "不安", "心慌", "慌"],
    "sad":     ["难过", "伤心", "沮丧", "没劲", "想哭", "低落"],
    "pain":    ["疼", "痛", "难受", "痉挛", "抽筋", "头晕", "胸闷", "胸痛", "呼吸困难"],
    "confused":["听不懂", "不会", "怎么弄", "怎么用", "看不明白", "不明白"],
}
def detect_mood(text: str) -> str:
    for k, words in EMO_LEX.items():
        if any(w in text for w in words):
            return k
    return "neutral"

# ============ 小工具 ============
def beep():
    if not AUDIO_BACKEND_OK:
        return
    tone = np.sin(2*np.pi*np.arange(int(0.12*SR))*880/SR).astype(np.float32)
    sd.play(tone, SR); sd.wait()

def record_once(max_s=7, tail_ms=700):
    """VAD 端点：静音 tail_ms 后自动结束，返回 PCM16 bytes"""
    if not VAD_BACKEND_OK:
        raise RuntimeError(f"VAD backend unavailable: {VAD_BACKEND_ERROR}")
    if not AUDIO_BACKEND_OK:
        raise RuntimeError(f"audio backend unavailable: {AUDIO_BACKEND_ERROR}")
    vad = webrtcvad.Vad(2)
    block = int(SR*(FRAME_MS/1000.0))
    q = queue.Queue()
    def cb(indata, frames, t, status):
        if status: print(status, file=sys.stderr)
        q.put(bytes(indata))
    pcm=b""; voiced=False; silent=0
    with sd.InputStream(samplerate=SR, channels=CH, dtype='int16',
                        blocksize=block, callback=cb):
        start=time.time()
        while time.time()-start < max_s:
            chunk=q.get(); pcm+=chunk
            step=int(SR*0.01)*2  # 10ms * 2字节
            for i in range(0, len(chunk), step):
                fr=chunk[i:i+step]
                if len(fr)<step: break
                if vad.is_speech(fr, SR):
                    voiced=True; silent=0
                else:
                    silent+=10
                if voiced and silent>=tail_ms:
                    return pcm
    return pcm

# —— 偏好存取（城市等） ——
def _load_prefs():
    try:
        if os.path.isfile(PREF_FILE):
            with open(PREF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_prefs(d):
    try:
        with open(PREF_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# —— 热词归一（繁体/口误） ——
def normalize_hotwords(text: str) -> str:
    rep = {
        "心律": "心率",
        "下床": "离床",
        "落床": "离床",
        "打呼噜": "打呼",
        "打呼嚕": "打呼",
        "打鼾": "打呼",        # 统一关键词
        "昨夜": "昨晚",
        "托夫": "TOF",
        "红外阵列": "红外",
        "檢測": "检测", "睡覺": "睡觉", "體位": "体位", "訊號": "信号",
        "離床": "离床", "鼾聲": "鼾声", "哼聲": "鼾声", "哼声": "鼾声",
        "韓盛": "鼾声", "韓生": "鼾声",
        "心跳率": "心率",
    }
    for k, v in rep.items():
        text = text.replace(k, v)
    return text

def asr_from_pcm(pcm: bytes, asr):
    """PCM16 → 临时wav → faster-whisper"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path=f.name
    w=wave.open(wav_path,"wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm); w.close()

    # beam + 多温度 + VAD 过滤 + 不依赖历史文本 + 词汇引导
    segs, _ = asr.transcribe(
        wav_path,
        language="zh",
        beam_size=5,
        temperature=[0.0, 0.2, 0.4],
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        condition_on_previous_text=False,
        word_timestamps=False,
        initial_prompt="心率、心跳、脉搏、睡眠、昨晚、离床、落床、下床、睡姿、体位、仰卧、侧卧、俯卧、鼾声、打呼、呼吸暂停。"
    )
    os.remove(wav_path)
    text = "".join(s.text for s in segs).strip()
    return normalize_hotwords(text)

# ============ TTS ============
def tts_piper(text: str):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out=f.name
    cmd = f'echo {json.dumps(text)} | "{PIPER_EXE}" -m "{PIPER_MODEL}" -f "{out}"'
    subprocess.run(cmd, shell=True, check=True)
    if AUDIO_BACKEND_OK:
        data, sr = sf.read(out, dtype="float32")
        sd.play(data, sr)
        sd.wait()
    else:
        # Linux fallback when PortAudio is missing.
        subprocess.run(["aplay", out], check=False)
    os.remove(out)

def tts_sapi(text: str, voice_hint="zh-CN", rate=0, volume=100):
    import win32com.client as wincl
    spk = wincl.Dispatch("SAPI.SpVoice")
    try:
        token_cat = wincl.Dispatch("SAPI.SpObjectTokenCategory")
        token_cat.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices", False)
        for token in token_cat.EnumerateTokens():
            desc = token.GetDescription(); low = desc.lower()
            if ("chinese" in low) or ("zh" in low) or (voice_hint.lower() in low):
                spk.Voice = token; break
    except Exception:
        pass
    spk.Rate = rate; spk.Volume = volume
    spk.Speak(text)

def speak(text: str):
    try:
        if USE_PIPER and os.path.isfile(PIPER_MODEL):
            tts_piper(text)
        else:
            tts_sapi(text, voice_hint="zh-CN", rate=0, volume=100)
    except Exception as e:
        print("[TTS失败→打印] ", text, "|", e)

# ============ 多策略意图识别（拼音模糊 + 关键词 + 正则 + 高分直通） ============
KW_UNIT = 25     # 每命中1个关键词 +25 分
KW_CAP  = 50     # 关键词最高加分
RE_HIT  = 35     # 命中正则 +35
W_FUZZ, W_KW, W_RE = 0.50, 0.35, 0.15
FUZZY_PASS = 88  # 模糊得分高于该值直接命中

INTENTS = {
    "HEART_RATE": {
        "phrases": ["心率检测", "测心率", "查看心率", "心跳检测", "测心跳", "看看心跳", "测脉搏", "心跳", "心率"],
        "keywords": ["心率", "心跳", "脉搏", "心律"],
        "regex": r"(心(率|跳)|脉搏)",
        "th": 50,
    },
    "SLEEP_SUMMARY": {
        "phrases": ["昨晚睡眠情况", "睡眠报告", "昨夜睡眠报告", "睡眠质量", "昨晚睡得怎么样", "昨晚的睡眠统计", "睡眠", "昨晚"],
        "keywords": ["昨晚", "昨夜", "睡眠", "报告", "质量", "统计"],
        "regex": r"(昨(晚|夜).*(睡|眠)|睡眠.*(报告|质量|统计)|睡眠)",
        "th": 55,
    },
    "LEAVE_BED": {
        "phrases": ["离床提醒", "离床检测", "下床提醒", "有没有下床", "落床报警", "离床", "下床", "落床"],
        "keywords": ["离床", "下床", "落床", "报警", "提醒", "记录"],
        "regex": r"((离|下|落)床|报警|提醒)",
        "th": 55,
    },
    "POSTURE": {
        "phrases": ["睡姿识别", "姿势检测", "体位识别", "看看睡姿", "仰卧还是侧卧", "有没有翻身", "睡姿", "姿势", "体位"],
        "keywords": ["睡姿", "姿势", "体位", "仰卧", "侧卧", "俯卧", "趴", "翻身"],
        "regex": r"(睡姿|体位|仰卧|侧卧|俯卧|翻身|姿势)",
        "th": 55,
    },
    "SNORE": {
        "phrases": ["鼾声分析", "鼾声检测", "打呼情况", "打呼严重吗", "呼吸暂停", "鼾声疾病识别", "鼾声", "打鼾", "打呼"],
        "keywords": ["鼾", "打呼", "呼吸暂停", "鼾声", "打鼾"],
        "regex": r"(鼾|打呼|打鼾|呼吸暂停)",
        "th": 50,
    },
}
PHRASE_PINYIN = {k: [" ".join(lazy_pinyin(p)) for p in v["phrases"]] for k, v in INTENTS.items()}
def _kw_hits(text: str, kws): return sum(1 for w in kws if w in text)

def score_intent_all(text: str):
    res = {}
    if not text:
        for k, cfg in INTENTS.items():
            res[k] = {"fuzzy":0.0, "kw":0, "re":0, "final":0.0, "th":cfg["th"], "kw_hits":0, "re_hit":0}
        return res
    q_py = " ".join(lazy_pinyin(text))
    for k, py_list in PHRASE_PINYIN.items():
        res.setdefault(k, {})
        res[k]["fuzzy"] = max(fuzz.token_set_ratio(q_py, py) for py in py_list)
    for k, cfg in INTENTS.items():
        hits = _kw_hits(text, cfg["keywords"])
        res[k]["kw_hits"] = hits
        res[k]["kw"] = min(hits * KW_UNIT, KW_CAP)
        hit = 1 if re.search(cfg["regex"], text) else 0
        res[k]["re_hit"] = hit
        res[k]["re"] = RE_HIT if hit else 0
        res[k]["final"] = W_FUZZ*res[k]["fuzzy"] + W_KW*res[k]["kw"] + W_RE*res[k]["re"]
        res[k]["th"] = cfg["th"]
    return res

def decide_intent(text: str):
    scores = score_intent_all(text)
    short_utt = len(text) <= 4
    regex_hits = [(k, v) for k, v in scores.items() if v["re_hit"] == 1]
    if regex_hits and (short_utt or max(v["kw_hits"] for _, v in regex_hits) >= 1):
        regex_hits.sort(key=lambda kv: (kv[1]["kw_hits"], kv[1]["final"]), reverse=True)
        k, v = regex_hits[0]
        top_all = sorted(scores.items(), key=lambda kv: kv[1]["final"], reverse=True)[:3]
        return k, v["final"], v["th"], top_all, scores
    top_fuzzy = sorted(scores.items(), key=lambda kv: kv[1]["fuzzy"], reverse=True)[0]
    if top_fuzzy[1]["fuzzy"] >= FUZZY_PASS:
        top_all = sorted(scores.items(), key=lambda kv: kv[1]["final"], reverse=True)[:3]
        return top_fuzzy[0], top_fuzzy[1]["final"], scores[top_fuzzy[0]]["th"], top_all, scores
    top = sorted(scores.items(), key=lambda kv: kv[1]["final"], reverse=True)
    best_intent, best_detail = top[0]
    chosen = best_intent if best_detail["final"] >= best_detail["th"] else "CHAT"
    return chosen, best_detail["final"], best_detail["th"], top[:3], scores

def parse_intent(text: str):
    final_intent, _, _, _, _ = decide_intent(text)
    return final_intent

# ============ 网关授权上下文 ============
def _as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _as_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def build_gateway_context_params(room=None, bed=None, target_subject_id=None, session_id=None):
    params = {}
    sid = (session_id if session_id is not None else VOICE_SESSION_ID).strip()
    subject_id = (target_subject_id if target_subject_id is not None else VOICE_TARGET_SUBJECT_ID).strip()
    if sid:
        params["session_id"] = sid
    if subject_id:
        params["target_subject_id"] = subject_id
    else:
        params["target_room"] = room or VOICE_ROOM
        params["target_bed"] = bed or VOICE_BED
    return params


def context_policy(ctx: dict) -> dict:
    return ctx.get("policy", {}) if isinstance(ctx, dict) else {}


def context_allowed(ctx: dict) -> bool:
    return bool(context_policy(ctx).get("allowed"))


def context_modalities(ctx: dict) -> dict:
    return ctx.get("modalities", {}) if isinstance(ctx, dict) else {}


def context_target_label(ctx: dict) -> str:
    target = ctx.get("target", {}) if isinstance(ctx, dict) else {}
    room = str(target.get("room") or VOICE_ROOM)
    bed = str(target.get("bed") or VOICE_BED)
    patient = target.get("patient", {}) if isinstance(target.get("patient"), dict) else {}
    name = str(patient.get("name") or "").strip()
    if name and context_allowed(ctx):
        return f"{name}（{room}-{bed}）"
    return f"{room}-{bed}"


def gateway_denied_reply(ctx: dict) -> str:
    policy = context_policy(ctx)
    reason = str(policy.get("reason") or "unknown")
    if reason == "not_authenticated":
        return "当前还没有完成身份认证，我不能读取患者或床位隐私数据。请先在护士站完成识别，或使用后续接入的指纹等认证方式。"
    if reason == "not_authorized_for_target":
        return "当前身份没有这个目标的查询权限，我不能返回对应患者或床位数据。"
    return "当前网关没有授权这次查询，我不能返回患者或床位数据。"


def fetch_authorized_gateway_context(room=None, bed=None) -> Tuple[Optional[dict], Optional[str]]:
    ctx = fetch_gateway_chat_context(room=room, bed=bed)
    if not isinstance(ctx, dict):
        return None, "暂时无法从网关获取已授权的上下文，请确认 gateway 和当前会话正常。"
    if not context_allowed(ctx):
        return None, gateway_denied_reply(ctx)
    return ctx, None


def get_vitals_context(ctx: dict) -> dict:
    mods = context_modalities(ctx)
    vitals = mods.get("vitals", {})
    if isinstance(vitals, dict) and vitals:
        return vitals
    sleep = mods.get("sleep", {})
    return sleep if isinstance(sleep, dict) else {}


def get_sleep_context(ctx: dict) -> dict:
    sleep = context_modalities(ctx).get("sleep", {})
    return sleep if isinstance(sleep, dict) else {}


def get_posture_context(ctx: dict) -> dict:
    posture = context_modalities(ctx).get("posture", {})
    return posture if isinstance(posture, dict) else {}


def get_heart_rate_from_gateway(room=None, bed=None):
    ctx, err = fetch_authorized_gateway_context(room=room, bed=bed)
    if err:
        return None
    heart_bpm = _as_float(get_vitals_context(ctx).get("heart_bpm"), 0.0)
    return heart_bpm if heart_bpm > 0 else None

# ============ 天气：城市解析 & 查询 ============
def _qweather_lookup_city(city: str):
    """和风城市查询，返回 (name, lat, lon) 或 None"""
    if not QWEATHER_KEY: return None
    try:
        url = "https://geoapi.qweather.com/v2/city/lookup"
        params = {"key": QWEATHER_KEY, "location": city}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("code") == "200" and data.get("location"):
            loc = data["location"][0]
            name = loc["name"]
            lat = float(loc["lat"]); lon = float(loc["lon"])
            return name, lat, lon
    except Exception:
        pass
    return None

def _openmeteo_lookup_city(city: str):
    """Open-Meteo geocoding，返回 (name, lat, lon) 或 None"""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        r = requests.get(url, params={"name": city, "count": 1, "language": "zh"}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("results"):
            g = data["results"][0]
            name = g.get("name")
            lat = float(g["latitude"]); lon = float(g["longitude"])
            return name, lat, lon
    except Exception:
        pass
    return None

def resolve_city(city: str):
    """优先QWeather解析；失败则Open-Meteo"""
    city = city.strip()
    if not city: return None
    res = _qweather_lookup_city(city)
    if res: return res
    return _openmeteo_lookup_city(city)

def _qweather_now(lat, lon):
    """和风实时天气，返回中文一句话"""
    if not QWEATHER_KEY: return None
    try:
        url = "https://devapi.qweather.com/v7/weather/now"
        params = {"key": QWEATHER_KEY, "location": f"{lon:.4f},{lat:.4f}", "lang": "zh"}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        j = r.json()
        if j.get("code") == "200":
            now = j["now"]
            txt = now["text"]
            temp = now["temp"]
            hum = now["humidity"]
            wind = now["windDir"]
            return f"{txt}，{temp}度，湿度{hum}%，{wind}。"
    except Exception:
        pass
    return None

def _openmeteo_now(lat, lon):
    """Open-Meteo 实时天气（以温度/体感为主）"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat, "longitude": lon,
            "current": ["temperature_2m","apparent_temperature","relative_humidity_2m","is_day"]
        }
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        cur = r.json().get("current")
        if cur:
            t = cur.get("temperature_2m")
            ta = cur.get("apparent_temperature")
            rh = cur.get("relative_humidity_2m")
            is_day = cur.get("is_day")
            day = "白天" if is_day else "夜间"
            return f"{day}，气温{t}℃，体感{ta}℃，湿度{rh}%。"
    except Exception:
        pass
    return None

def get_weather_sentence(city_hint: str = None) -> str:
    """
    返回一句中文天气话术。
    - 有城市记忆就用记忆；没有就用用户给的 city_hint；再没有就返回空。
    """
    prefs = _load_prefs()
    name = None; lat = lon = None
    if "weather_city" in prefs:
        name = prefs["weather_city"]["name"]
        lat = prefs["weather_city"]["lat"]
        lon = prefs["weather_city"]["lon"]
    elif city_hint:
        res = resolve_city(city_hint)
        if res:
            name, lat, lon = res
            prefs["weather_city"] = {"name": name, "lat": lat, "lon": lon}
            _save_prefs(prefs)
        else:
            return ""

    if name is None:
        return ""

    sent = _qweather_now(lat, lon) if QWEATHER_KEY else None
    if not sent:
        sent = _openmeteo_now(lat, lon)
    if not sent:
        return ""
    return f"{name}当前{sent}"


def fetch_gateway_chat_context(room=None, bed=None, target_subject_id=None, session_id=None) -> Optional[dict]:
    if not GATEWAY_CONTEXT_ENABLED:
        return None
    try:
        params = build_gateway_context_params(
            room=room,
            bed=bed,
            target_subject_id=target_subject_id,
            session_id=session_id,
        )
        r = requests.get(GATEWAY_CHAT_CONTEXT_URL, params=params, timeout=GATEWAY_TIMEOUT_S)
        r.raise_for_status()
        obj = r.json()
        if isinstance(obj, dict):
            return obj
    except Exception as e:  # noqa: BLE001
        print(f"[GATEWAY统一上下文获取失败] {e}")
    return None


def build_sleep_summary_from_context(ctx: dict) -> Optional[str]:
    if not isinstance(ctx, dict):
        return None

    sleep = get_sleep_context(ctx)
    vitals = get_vitals_context(ctx)
    sleep_h = _as_float(sleep.get("sleep_h"), 0.0)
    score = _as_float(sleep.get("sleep_score"), 0.0)
    stage = str(sleep.get("sleep_stage", "W") or "W")
    grade = str(sleep.get("sleep_grade", "数据不足，暂不评分") or "数据不足，暂不评分")
    snore_level = _as_int(sleep.get("snore_level"), 0)
    heart_bpm = _as_float(vitals.get("heart_bpm", sleep.get("heart_bpm")), 0.0)

    # 当前阶段网关在无数据时会返回 0，这里用 0 值作为“数据不足”判断。
    if sleep_h <= 0.0 and score <= 0.0:
        return None

    return (
        f"睡眠报告更新：当前分期{stage}，累计睡眠约{sleep_h:.2f}小时，"
        f"综合评分{score:.1f}分，等级{grade}。"
        f"鼾声等级{snore_level}，当前心率约{heart_bpm:.0f}次每分钟。"
    )


def build_prompt_text_from_chat_context(ctx: dict) -> str:
    if not isinstance(ctx, dict):
        return ""

    parts = []
    policy = context_policy(ctx)
    if not bool(policy.get("allowed")):
        parts.append(gateway_denied_reply(ctx))

    brief = str(ctx.get("brief", "") or "").strip()
    if brief:
        parts.append(brief)

    prompt_hints = ctx.get("prompt_hints") or []
    if isinstance(prompt_hints, list):
        hints = [str(x).strip() for x in prompt_hints if str(x).strip()]
        if hints:
            parts.append("对话提示：" + "；".join(hints[:3]))

    return "\n".join(parts).strip()


def build_heart_rate_reply_from_context(ctx: dict) -> str:
    label = context_target_label(ctx)
    vitals = get_vitals_context(ctx)
    heart_bpm = _as_float(vitals.get("heart_bpm"), 0.0)
    if heart_bpm > 0:
        return f"{label}: 当前心率 {heart_bpm:.0f} 次每分钟。刚活动后略快属正常；若静息仍持续偏快，请记录时间段观察。"
    return f"已获得{label}的授权上下文，但暂时没有可用心率数据，请稍后再试。"


def build_leave_bed_reply_from_context(ctx: dict) -> str:
    label = context_target_label(ctx)
    vitals = get_vitals_context(ctx)
    turning = _as_int(vitals.get("turning"), 0)
    motion = _as_float(vitals.get("motion"), 0.0)
    if turning > 0:
        return f"{label}: 检测到近期翻身或明显体动事件。当前上下文还没有独立离床判定，建议结合现场情况确认。"
    if motion > 0:
        return f"{label}: 当前未见明确离床事件，体动指数约 {motion:.2f}。"
    return f"{label}: 当前上下文未提示离床或明显体动。"


def build_posture_reply_from_context(ctx: dict) -> str:
    label = context_target_label(ctx)
    posture = get_posture_context(ctx)
    class_name = str(posture.get("posture_class") or "").strip()
    confidence = _as_float(posture.get("posture_confidence"), 0.0)
    if class_name and class_name != "未知":
        return f"{label}: 当前姿势为{class_name}，置信度约{confidence * 100:.0f}%。"
    return f"已获得{label}的授权上下文，但暂时没有可用睡姿数据。"


def build_snore_reply_from_context(ctx: dict) -> str:
    label = context_target_label(ctx)
    sleep = get_sleep_context(ctx)
    vitals = get_vitals_context(ctx)
    snore_level = _as_int(vitals.get("snore_level", sleep.get("snore_level")), 0)
    snore_count = _as_int(vitals.get("snore_count_1min", sleep.get("snore_count_1min")), 0)
    if snore_level > 0 or snore_count > 0:
        return f"{label}: 鼾声等级{snore_level}，1分钟{snore_count}次。"
    return f"{label}: 鼾声强度偏低，当前上下文未见呼吸暂停特征。"

# ============ 业务处理 ============
WEATHER_PAT = re.compile(r"(天气|氣象|下雨|雨|温度|冷不冷|热不热|幾度|几度)")

def handle_intent(intent: str, text: str):
    if intent=="HEART_RATE":
        ctx, err = fetch_authorized_gateway_context()
        reply = err or build_heart_rate_reply_from_context(ctx)
    elif intent=="SLEEP_SUMMARY":
        ctx, err = fetch_authorized_gateway_context()
        if err:
            reply = err
        else:
            sleep_reply = build_sleep_summary_from_context(ctx)
            reply = f"{context_target_label(ctx)}: {sleep_reply}" if sleep_reply else f"已获得{context_target_label(ctx)}的授权上下文，但暂时没有可用睡眠报告。"
    elif intent=="LEAVE_BED":
        ctx, err = fetch_authorized_gateway_context()
        reply = err or build_leave_bed_reply_from_context(ctx)
    elif intent=="POSTURE":
        ctx, err = fetch_authorized_gateway_context()
        reply = err or build_posture_reply_from_context(ctx)
    elif intent=="SNORE":
        ctx, err = fetch_authorized_gateway_context()
        reply = err or build_snore_reply_from_context(ctx)
    else:
        # 联网天气：记忆城市优先，问句里若带城市会尝试解析&记住
        if WEATHER_PAT.search(text):
            m = re.search(r"(北京|上海|广州|深圳|杭州|成都|重庆|南京|武汉|西安|天津|苏州|长沙|合肥|郑州|青岛|大连|厦门|福州|沈阳|宁波|无锡|佛山|昆明|石家庄|济南|太原|南昌|南宁|哈尔滨|长春)", text)
            city_hint = m.group(1) if m else None
            sent = get_weather_sentence(city_hint)
            if not sent and not city_hint:
                reply = "要查询天气，请告诉我你所在的城市，例如“北京天气”。"
            elif not sent and city_hint:
                reply = f"我试着查询{city_hint}的天气失败了，请换个城市或稍后再试。"
            else:
                reply = sent
        else:
            reply = chat_lm(text)  # 普通情感对话
    speak(reply)
    return reply

# ============ LLM 情感对话 ============
SYSTEM_PROMPT_BASE = (
    "你是面向老年护理的中文语音助手，语气温和、有同理心。"
    "禁止输出<think>等思考标签。"
    "回答控制在2-3句，优先给出可执行建议。"
)

CHAT_ENGINE = None


def strip_think_text(t: str) -> str:
    t = re.sub(r"(?is)<think>.*?</think>", "", t)
    t = re.sub(r"(?is)<think>.*?$", "", t)
    t = re.sub(r"(?is)\[/?(think|reflection|reasoning)\]", "", t)
    t = re.sub(r"(?is)</?reflection>|</?reasoning>", "", t)
    return t.strip()


def mood_instruction(user_text: str) -> str:
    mood = detect_mood(user_text or "")
    return {
        "neutral": "语气平和；给出清晰建议。",
        "anxious": "用户略显焦虑；先安抚1句，再给两个可执行的步骤。",
        "sad": "用户略显低落；先肯定与支持，再给简单建议。",
        "pain": "用户可能有不适；先关心，再给安全建议；必要时提示就医。",
        "confused": "用户困惑；用更慢、更简单的话解释步骤。",
    }[mood]


class LocalRKLLMChat:
    def __init__(self):
        self.client = None
        self.session = None
        self.ready = False

    def start(self) -> bool:
        if RKLLMClient is None:
            print(f"[RKLLM不可用] 导入失败: {RKLLM_IMPORT_ERROR}")
            return False
        if not os.path.isfile(RKLLM_SO_PATH):
            print(f"[RKLLM不可用] 未找到 so: {RKLLM_SO_PATH}")
            return False
        if not os.path.isfile(RKLLM_MODEL_PATH):
            print(f"[RKLLM不可用] 未找到模型: {RKLLM_MODEL_PATH}")
            return False

        try:
            cfg = LLMConfig(
                model_path=RKLLM_MODEL_PATH,
                max_new_tokens=RKLLM_MAX_NEW_TOKENS,
                max_context_len=RKLLM_MAX_CONTEXT_LEN,
                sampling=SamplingConfig(
                    top_k=1,
                    top_p=0.95,
                    temperature=0.6,
                    repeat_penalty=1.1,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                ),
                skip_special_token=True,
                base_domain_id=0,
                embed_flash=1,
            )
            self.client = RKLLMClient(RKLLM_SO_PATH, cfg)
            self.session = self.client.create_session(session_id="voice-main", keep_history=False)
            self.session.add_message("system", SYSTEM_PROMPT_BASE)
            self.ready = True
            return True
        except Exception as e:  # noqa: BLE001
            self.ready = False
            print(f"[RKLLM初始化失败] {e}")
            return False

    def stop(self) -> None:
        if self.client is None:
            return
        try:
            self.client.destroy()
        except Exception:
            pass
        self.client = None
        self.session = None
        self.ready = False

    def _trim_history(self) -> None:
        if self.session is None:
            return
        system_msgs = [m for m in self.session.messages if m.role == "system"]
        other_msgs = [m for m in self.session.messages if m.role != "system"]
        other_msgs = other_msgs[-(RKLLM_MAX_CHAT_TURNS * 2):]
        self.session.messages = (system_msgs[:1] + other_msgs) if system_msgs else other_msgs

    def chat(self, user_text: str, gateway_ctx_text: str = "") -> Optional[str]:
        if not self.ready or self.session is None:
            return None

        extra_hint = mood_instruction(user_text)
        prompt = f"{user_text}\n\n请遵循回复风格：{extra_hint}"
        if gateway_ctx_text:
            prompt += f"\n\n网关已授权上下文（已经过权限裁剪，不要编造未提供的数据）：{gateway_ctx_text}"
        try:
            result = self.session.generate(prompt)
            reply = strip_think_text(result.text)
            if not reply:
                reply = "我在的，请再说一次你的需求。"
            if len(reply) > 240:
                reply = reply[:240] + "……"
            self._trim_history()
            return reply
        except Exception as e:  # noqa: BLE001
            print(f"[RKLLM推理失败] {e}")
            return None


def chat_lm(user_text: str) -> str:
    ctx = fetch_gateway_chat_context()
    gateway_hint = build_prompt_text_from_chat_context(ctx) if isinstance(ctx, dict) else ""

    if CHAT_ENGINE is not None and CHAT_ENGINE.ready:
        reply = CHAT_ENGINE.chat(user_text, gateway_ctx_text=gateway_hint)
        if reply:
            return reply
    return "我在的，有什么需要我帮忙的吗？"

# ============ 主程序 ============
if __name__=="__main__":
    if VOICE_INPUT_MODE not in ("mic", "text"):
        print(f"[WARN] VOICE_INPUT_MODE={VOICE_INPUT_MODE} 无效，已回退为 mic")
        VOICE_INPUT_MODE = "mic"

    ASR = None
    if VOICE_INPUT_MODE == "mic":
        if not VAD_BACKEND_OK:
            raise RuntimeError(
                "mic mode requires webrtcvad backend, but it is unavailable: "
                f"{VAD_BACKEND_ERROR}"
            )
        if not AUDIO_BACKEND_OK:
            raise RuntimeError(
                "mic mode requires sounddevice/PortAudio, but audio backend is unavailable: "
                f"{AUDIO_BACKEND_ERROR}"
            )
        print("加载 ASR 模型中……")
        ASR = WhisperModel(ASR_MODEL_SIZE, compute_type=ASR_COMPUTE)

    print("加载本地大模型中……")
    CHAT_ENGINE = LocalRKLLMChat()
    if CHAT_ENGINE.start():
        print("本地大模型已常驻内存，等待输入。")
    else:
        print("本地大模型初始化失败，将使用兜底回复。")

    if VOICE_INPUT_MODE == "mic":
        beep()
        print(f"当前房间/床位: {VOICE_ROOM}-{VOICE_BED}")
        print("请说话（示例：心率检测 / 昨晚睡眠情况 / 离床提醒 / 睡姿识别 / 鼾声分析 / 北京天气）。")
    else:
        if not AUDIO_BACKEND_OK:
            print(f"[WARN] 音频后端不可用，将继续文本交互，TTS将尝试使用aplay回退: {AUDIO_BACKEND_ERROR}")
        print(f"当前房间/床位: {VOICE_ROOM}-{VOICE_BED}")
        print("文本输入模式已启用：在终端直接输入文本替代 ASR，输入 exit 可退出。")

    try:
        while True:
            if VOICE_INPUT_MODE == "text":
                text = input("\nuser(text)> ").strip()
                if text.lower() in ("exit", "quit"):
                    break
                if not text:
                    continue
                print("你说：", text)
            else:
                pcm = record_once()
                if len(pcm) < 2000:
                    print("没听清，再来一次～")
                    continue
                print("识别中…")
                text = asr_from_pcm(pcm, ASR)
                print("你说：", text or "(空)")
                if not text:
                    continue
            intent = parse_intent(text)
            print("意图：", intent)
            handle_intent(intent, text)
    finally:
        if CHAT_ENGINE is not None:
            CHAT_ENGINE.stop()
