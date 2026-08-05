import pandas as pd
from pathlib import Path

IN_FILE = r"F:\AIsleep\sleep_integration_project\05_outputs\fusion_eeg_final_conf.csv"
OUT_FILE = r"F:\AIsleep\sleep_integration_project\05_outputs\sleep_quality_per_record.csv"

EPOCH_SEC = 30
MIN_TOTAL_HOURS = 6.0
MIN_SLEEP_HOURS = 4.0

df = pd.read_csv(IN_FILE)

if "record" not in df.columns:
    raise ValueError("当前文件没有 record 列，无法按记录分组统计。")

results = []

def duration_score(hours):
    # 参考型评分：不足4小时不评分；4小时以上逐步给分；7小时及以上满分
    if hours >= 7.0:
        return 60.0
    elif 6.0 <= hours < 7.0:
        return 50.0 + (hours - 6.0) * 10.0
    elif 5.0 <= hours < 6.0:
        return 35.0 + (hours - 5.0) * 15.0
    elif 4.0 <= hours < 5.0:
        return 20.0 + (hours - 4.0) * 15.0
    else:
        return None

def ratio_score(actual, target, tol, weight):
    diff = abs(actual - target)
    if diff >= tol:
        return 0.0
    return weight * (1.0 - diff / tol)

for rec, g in df.groupby("record"):
    stage = g["Final_stage"].astype(str)

    n_total = len(g)
    total_h = n_total * EPOCH_SEC / 3600.0

    n_w = (stage == "W").sum()
    n_1 = (stage == "1").sum()
    n_2 = (stage == "2").sum()
    n_n3 = (stage == "N3").sum()
    n_rem = (stage == "R").sum()

    n_sleep = n_1 + n_2 + n_n3 + n_rem
    sleep_h = n_sleep * EPOCH_SEC / 3600.0

    if n_sleep > 0:
        p1 = n_1 / n_sleep
        p2 = n_2 / n_sleep
        p3 = n_n3 / n_sleep
        pr = n_rem / n_sleep
    else:
        p1 = p2 = p3 = pr = 0.0

    score_valid = int((total_h >= MIN_TOTAL_HOURS) and (sleep_h >= MIN_SLEEP_HOURS))

    if score_valid == 1:
        d_score = duration_score(sleep_h)

        # 结构评分：参考成人常见结构分布
        s1 = ratio_score(p1, 0.05, 0.05, 5.0)
        s2 = ratio_score(p2, 0.45, 0.20, 12.0)
        s3 = ratio_score(p3, 0.25, 0.15, 11.5)
        sr = ratio_score(pr, 0.25, 0.15, 11.5)

        s_score = s1 + s2 + s3 + sr
        total_score = round((d_score if d_score is not None else 0.0) + s_score, 1)

        if total_score >= 85:
            grade = "优秀"
        elif total_score >= 70:
            grade = "良好"
        elif total_score >= 55:
            grade = "一般"
        else:
            grade = "较差"
    else:
        d_score = None
        s_score = None
        total_score = None
        grade = "数据不足，暂不评分"

    results.append({
        "record": rec,
        "total_h": round(total_h, 2),
        "sleep_h": round(sleep_h, 2),
        "W_epochs": n_w,
        "N1_epochs": n_1,
        "N2_epochs": n_2,
        "N3_epochs": n_n3,
        "REM_epochs": n_rem,
        "N1_ratio_in_sleep": round(p1, 4),
        "N2_ratio_in_sleep": round(p2, 4),
        "N3_ratio_in_sleep": round(p3, 4),
        "REM_ratio_in_sleep": round(pr, 4),
        "score_valid": score_valid,
        "duration_score": d_score,
        "structure_score": s_score,
        "total_score": total_score,
        "grade": grade
    })

out = pd.DataFrame(results)
Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

print("[OK] per-record analysis done")
print(out.head(10))
