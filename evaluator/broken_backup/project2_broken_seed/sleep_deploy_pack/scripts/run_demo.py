from pathlib import Path
import pandas as pd

# ========= 相对路径 =========
BASE = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE / "examples" / "fusion_eeg_final_conf.csv"
OUT_SCORE = BASE / "examples" / "sleep_quality_per_record.csv"

print("[INFO] loading data from:", INPUT_FILE)

df = pd.read_csv(INPUT_FILE)

results = []

for rec, g in df.groupby("record"):
    total_epochs = len(g)
    sleep_epochs = len(g[g["Final_stage"] != "W"])

    sleep_h = sleep_epochs * 30 / 3600.0

    if sleep_epochs == 0:
        continue

    def ratio(stage):
        return len(g[g["Final_stage"] == stage]) / sleep_epochs

    p1 = ratio("1")
    p2 = ratio("2")
    p3 = ratio("N3")
    pr = ratio("R")

    def duration_score(h):
        if h >= 7:
            return 60
        if h >= 6:
            return 50
        if h >= 5:
            return 40
        if h >= 4:
            return 30
        return 20

    def ratio_score(p, ideal, tol, max_score):
        return max(0, max_score * (1 - abs(p - ideal) / tol))

    d_score = duration_score(sleep_h)

    s_score = (
        ratio_score(p1, 0.05, 0.05, 5) +
        ratio_score(p2, 0.50, 0.20, 12) +
        ratio_score(p3, 0.20, 0.15, 11.5) +
        ratio_score(pr, 0.20, 0.15, 11.5)
    )

    total = round(d_score + s_score, 1)

    if total >= 85:
        grade = "优秀"
    elif total >= 70:
        grade = "良好"
    elif total >= 55:
        grade = "一般"
    else:
        grade = "较差"

    results.append({
        "record": rec,
        "sleep_h": round(sleep_h, 2),
        "N1": round(p1, 3),
        "N2": round(p2, 3),
        "N3": round(p3, 3),
        "REM": round(pr, 3),
        "score": total,
        "grade": grade
    })

out = pd.DataFrame(results)
out.to_csv(OUT_SCORE, index=False, encoding="utf-8-sig")

print("[OK] done")
print("[OK] saved to:", OUT_SCORE)
print(out.head())
