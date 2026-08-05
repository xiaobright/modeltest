from pathlib import Path
import numpy as np
import pandas as pd
import wfdb
from scipy.signal import welch

LABEL_FILE = Path(r"F:\AIsleep\sleep_integration_project\04_scripts\labels_all_epochs.csv")
BASE_DIR = Path(r"F:\AIsleep\radar_slpdb\mit-bih-polysomnographic-database-1.0.0")
OUT_FILE = Path(r"F:\AIsleep\sleep_integration_project\02_pipeline\features\br_features.csv")

RESP_PRIORITY = [
    "Resp (chest)",
    "Resp (abdominal)",
    "Resp (abdomen)",
    "Resp (nasal)",
    "Resp (sum)",
]

def choose_resp_channel(sig_names):
    for name in RESP_PRIORITY:
        if name in sig_names:
            return sig_names.index(name), name
    return None, None

def estimate_br(seg, fs):
    seg = np.asarray(seg, dtype=float)
    seg = seg[np.isfinite(seg)]

    if len(seg) < fs * 5:
        return np.nan, np.nan

    seg = seg - np.mean(seg)

    # 用整段做频谱，提升分辨率
    nperseg = len(seg)
    if nperseg < 64:
        return np.nan, np.nan

    f, p = welch(seg, fs=fs, nperseg=nperseg)

    # 放宽一点频带，避免漏掉
    band = (f >= 0.03) & (f <= 1.0)   # 约 1.8 ~ 60 bpm
    if band.sum() < 2:
        return np.nan, np.nan

    f_band = f[band]
    p_band = p[band]

    if np.all(~np.isfinite(p_band)) or np.nansum(p_band) <= 0:
        return np.nan, np.nan

    peak_idx = np.nanargmax(p_band)
    peak_hz = f_band[peak_idx]
    br_mean = float(peak_hz * 60.0)

    weights = p_band / (np.nansum(p_band) + 1e-12)
    mean_hz = np.nansum(f_band * weights)
    std_hz = np.sqrt(np.nansum(weights * (f_band - mean_hz) ** 2))
    br_std = float(std_hz * 60.0)

    return br_mean, br_std

labels = pd.read_csv(LABEL_FILE)
rows = []

for record_name, g in labels.groupby("record"):
    print(f"[INFO] processing {record_name}")
    rec = wfdb.rdrecord(str(BASE_DIR / record_name))
    fs = rec.fs
    sig_names = rec.sig_name

    idx, channel_name = choose_resp_channel(sig_names)
    if idx is None:
        print(f"[WARN] {record_name}: no respiration channel found.")
        for _, row in g.iterrows():
            rows.append({
                "record": row["record"],
                "start_s": row["start_s"],
                "end_s": row["end_s"],
                "resp_channel": None,
                "BR_mean": np.nan,
                "BR_std": np.nan,
            })
        continue

    signal = rec.p_signal[:, idx]

    for _, row in g.iterrows():
        start_s = float(row["start_s"])
        end_s = float(row["end_s"])
        start_i = max(0, int(round(start_s * fs)))
        end_i = min(len(signal), int(round(end_s * fs)))
        seg = signal[start_i:end_i]

        br_mean, br_std = estimate_br(seg, fs)

        rows.append({
            "record": row["record"],
            "start_s": start_s,
            "end_s": end_s,
            "resp_channel": channel_name,
            "BR_mean": br_mean,
            "BR_std": br_std,
        })

out = pd.DataFrame(rows)
out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

print(f"[OK] wrote {OUT_FILE} rows={len(out)}")
print(out.head())
print(out[['BR_mean','BR_std']].isna().mean())
print(out['resp_channel'].value_counts(dropna=False))
