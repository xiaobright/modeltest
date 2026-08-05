# -*- coding: utf-8 -*-
# 最小语音环路：说“心率检测”→ 识别 → 意图 → 播报
# 默认用 Windows 自带语音（SAPI）播报；想用 Piper，把 USE_PIPER=True 并填 PIPER_MODEL 路径即可。

import os, sys, time, queue, wave, re, tempfile, subprocess, json
import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

# ===== 配置 =====
SR = 16000           # 统一采样率
CH = 1               # 单声道
FRAME_MS = 20        # VAD帧长 10/20/30ms 之一
ASR_MODEL_SIZE = "tiny"      # tiny 或 base，先用 tiny 更稳
ASR_COMPUTE = "int8"         # CPU上更快；如遇问题可改为 "int8_float16" 或 "float32"

# 语音播报：默认用 SAPI；若你已下载 Piper 中文音色，把 USE_PIPER=True，并设置 PIPER_MODEL 路径
USE_PIPER = False
PIPER_EXE = "piper"
PIPER_MODEL = r"C:\voices\zh_cn\zh_CN-huayan-medium.onnx"  # 换成你的 .onnx 完整路径（准备好后再启用）

# ===== 简易意图（先规则，后续可接 LLM）=====
def parse_intent(text: str):
    if re.search(r"(心率|心跳).*(检测|查询|多少)?", text):
        return "HEART_RATE"
    return "CHAT"

# ===== 播报实现 =====
def tts_sapi(text: str):
    import win32com.client as wincl
    wincl.Dispatch("SAPI.SpVoice").Speak(text)

def tts_piper(text: str):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_out = f.name
    # 用 echo + 管道喂给 piper 生成 wav
    cmd = f'echo {json.dumps(text)} | "{PIPER_EXE}" -m "{PIPER_MODEL}" -f "{wav_out}"'
    subprocess.run(cmd, shell=True, check=True)
    import soundfile as sf
    data, sr = sf.read(wav_out, dtype="float32")
    sd.play(data, sr); sd.wait()
    os.remove(wav_out)

def speak(text: str):
    try:
        if USE_PIPER:
            tts_piper(text)
        else:
            tts_sapi(text)
    except Exception as e:
        print("[TTS失败，改为打印] ", text)

# ===== 录音 + VAD 端点检测 =====
def record_once(max_s=6, tail_ms=600):
    """返回一段说话的 PCM16 字节；静音 tail_ms 毫秒后自动收尾"""
    vad = webrtcvad.Vad(2)  # 0-3，数值越大越“严格”
    block = int(SR * (FRAME_MS/1000.0))
    q = queue.Queue()

    def cb(indata, frames, t, status):
        if status:
            print(status, file=sys.stderr)
        q.put(bytes(indata))

    pcm = b""; voiced = False; silent = 0
    with sd.InputStream(samplerate=SR, channels=CH, dtype='int16',
                        blocksize=block, callback=cb):
        start = time.time()
        while time.time() - start < max_s:
            chunk = q.get()
            pcm += chunk
            # webrtcvad 需要固定 10/20/30ms 子帧，这里用 10ms
            step = int(SR * 0.01) * 2  # 10ms * 2字节
            for i in range(0, len(chunk), step):
                fr = chunk[i:i+step]
                if len(fr) < step: break
                is_speech = vad.is_speech(fr, SR)
                if is_speech:
                    voiced = True; silent = 0
                else:
                    silent += 10
                if voiced and silent >= tail_ms:
                    return pcm
    return pcm

# ===== ASR：Whisper 推理 =====
def asr_from_pcm(pcm: bytes) -> str:
    # 写到临时 wav 再丢给 faster-whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm); w.close()

    segs, _ = ASR_MODEL.transcribe(path, language="zh")
    os.remove(path)
    return "".join(s.text for s in segs).strip()

# ===== 业务处理 =====
def handle_intent(intent: str, text: str):
    if intent == "HEART_RATE":
        bpm = 78  # 先占位；以后改成读你设备/云端的实时心率
        reply = f"当前心率 {bpm} 次每分钟。"
    else:
        reply = "好的，我在。"
    speak(reply)
    return reply

# ===== 主程序 =====
if __name__ == "__main__":
    print("加载 ASR 模型中…（第一次会稍慢）")
    ASR_MODEL = WhisperModel(ASR_MODEL_SIZE, compute_type=ASR_COMPUTE)

    # 提示音
    beep = np.sin(2*np.pi*np.arange(int(0.15*SR))*880/SR).astype(np.float32)
    sd.play(beep, SR); sd.wait()
    print("请说话（示例：心率检测）。说完停顿一下自动结束。")

    while True:
        pcm = record_once()
        if len(pcm) < 2000:
            print("没听清，再来一次～"); continue
        print("识别中…")
        text = asr_from_pcm(pcm)
        print("你说：", text or "(空)")
        if not text:
            continue
        intent = parse_intent(text)
        print("意图：", intent)
        handle_intent(intent, text)
