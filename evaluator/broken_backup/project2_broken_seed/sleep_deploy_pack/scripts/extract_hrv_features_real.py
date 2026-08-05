from pathlib import Path
import numpy as np
import pandas as pd
import wfdb
from scipy.signal import find_peaks

LABEL_FILE = Path(r"F:\AIsleep\sleep_integration_project\04_scripts\labels_all_epochs.csv")
BASE_DIR = Path(r"F:\AIsleep\radar_slpdb\mit-bih-polysomnographic-database-1.0.0")
OUT_FILE = Path(r"F:\AIsleep\sleep_integration_project\02_pipeline\features\hrv_features.csv")

def estimate_hrv(seg, fs):
    seg = np.asarray(seg, dtype=float)
    seg = seg[np.isfinite(seg)]

    if len(seg) < fs * 5:
        return np.nan, np.nan, np.nan, np.nan

    seg = seg - np.mean(seg)
    std = np.std(seg)
    if std < 1e-8:
        return np.nan, np.nan, np.nan, np.nan

    min_distance = int(0.25 * fs)
    height = 0.5 * std

    peaks, _ = find_peaks(seg, distance=min_distance, height=height)

    if len(peaks) < 3:
        peaks, _ = find_peaks(-seg, distance=min_distance, height=height)

    if len(peaks) < 3:
        return np.nan, np.nan, np.nan, np.nan

    rr = np.diff(peaks) / fs
    rr = rr[(rr > 0.3) & (rr < 2.0)]

    if len(rr) < 2:
        return np.nan, np.nan, np.nan, np.nan

    hr = 60.0 / rr
    hr_mean = float(np.mean(hr))
    hr_std = float(np.std(hr, ddof=1)) if len(hr) >= 2 else np.nan
    sdnn = float(np.std(rr, ddof=1) * 1000.0) if len(rr) >= 2 else np.nan

    diff_rr = np.diff(rr)
    rmssd = float(np.sqrt(np.mean(diff_rr ** 2)) * 1000.0) if len(diff_rr) >= 1 else np.nan

    return hr_mean, hr_std, rmssd, sdnn

labels = pd.read_csv(LABEL_FILE)
rows = []

for record_name, g in labels.groupby("record"):
    print(f"[INFO] processing {record_name}")

    rec = wfdb.rdrecord(str(BASE_DIR / record_name))
    fs = rec.fs
    sig_names = rec.sig_name

    if "ECG" not in sig_names:
        print(f"[WARN] {record_name}: no ECG")
        for _, row in g.iterrows():
            rows.append({
                "record": row["record"],
                "start_s": row["start_s"],
                "end_s": row["end_s"],
                "HR_mean": np.nan,
                "HR_std": np.nan,
                "RMSSD": np.nan,
                "SDNN": np.nan,
            })
        continue

    ecg = rec.p_signal[:, sig_names.index("ECG")]

    for _, row in g.iterrows():
        start_s = float(row["start_s"])
        end_s = float(row["end_s"])
        start_i = max(0, int(round(start_s * fs)))
        end_i = min(len(ecg), int(round(end_s * fs)))

        seg = ecg[start_i:end_i]
        hr_mean, hr_std, rmssd, sdnn = estimate_hrv(seg, fs)

        rows.append({
            "record": row["record"],
            "start_s": start_s,
            "end_s": end_s,
            "HR_mean": hr_mean,
            "HR_std": hr_std,
            "RMSSD": rmssd,
            "SDNN": sdnn,
        })

out = pd.DataFrame(rows)
out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

print(f"[OK] wrote {OUT_FILE} rows={len(out)}")
print(out.head())
print(out[['HR_mean','HR_std','RMSSD','SDNN']].isna().mean())
