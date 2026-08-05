import pandas as pd
import joblib
from pathlib import Path

# ===== 模型路径 =====
EEG_MODEL = r"F:\AIsleep\radar_slpdb\scripts\baseline_eeg_N3merge\rf_eeg_c4a1_N3merge.joblib"
SLEEP_MODEL = r"F:\AIsleep\sleep_integration_project\03_models\sleep_stage\sleep_stage_rf_2class.joblib"

# ===== 数据路径 =====
EEG_FEATURE = r"F:\AIsleep\radar_slpdb\scripts\baseline_eeg_N3merge\features_eeg_c4a1_N3merge.csv"
BRHRV_DATA = r"F:\AIsleep\sleep_integration_project\02_pipeline\features\dataset_stage_2class.csv"

OUT_FILE = r"F:\AIsleep\sleep_integration_project\05_outputs\fusion_eeg_final_conf.csv"

# ===== 参数 =====
SLEEP_W_PROB_THR = 0.65
EEG_CONF_THR = 0.75

# ===== 读取 =====
df_eeg = pd.read_csv(EEG_FEATURE)
df_phy = pd.read_csv(BRHRV_DATA)

# ===== 加载模型 =====
eeg_model = joblib.load(EEG_MODEL)
sleep_model = joblib.load(SLEEP_MODEL)

# ===== EEG预测 =====
X_eeg = df_eeg.values
eeg_pred = eeg_model.predict(X_eeg)
eeg_proba = eeg_model.predict_proba(X_eeg)
eeg_conf = eeg_proba.max(axis=1)

# ===== 生理预测 =====
feature_cols = ["BR_mean","BR_std","HR_mean","HR_std","RMSSD","SDNN"]
X_phy = df_phy[feature_cols]
sleep_pred = sleep_model.predict(X_phy)
sleep_proba = sleep_model.predict_proba(X_phy)
sleep_classes = list(sleep_model.named_steps["rf"].classes_)
w_idx = sleep_classes.index("W")
sleep_w_prob = sleep_proba[:, w_idx]

# ===== 对齐长度 =====
n = min(len(eeg_pred), len(sleep_pred), len(df_phy))

# ===== 融合 =====
final_pred = []
rule_applied = []

for i in range(n):
    eeg_stage = str(eeg_pred[i])
    eeg_c = float(eeg_conf[i])
    phy_w = float(sleep_w_prob[i])

    if (phy_w >= SLEEP_W_PROB_THR) and (eeg_stage in ["W", "1"]) and (eeg_c < EEG_CONF_THR):
        final_pred.append("W")
        rule_applied.append(1)
    else:
        final_pred.append(eeg_stage)
        rule_applied.append(0)

# ===== 输出：保留 record / start_s / end_s =====
keep_cols = []
for c in ["record", "start_s", "end_s", "stage", "label_2class"]:
    if c in df_phy.columns:
        keep_cols.append(c)

df_out = df_phy.loc[:n-1, keep_cols].copy()
df_out["EEG_stage"] = eeg_pred[:n]
df_out["EEG_conf"] = eeg_conf[:n]
df_out["Sleep_detect"] = sleep_pred[:n]
df_out["Sleep_W_prob"] = sleep_w_prob[:n]
df_out["Final_stage"] = final_pred
df_out["RuleApplied"] = rule_applied

Path(OUT_FILE).parent.mkdir(parents=True, exist_ok=True)
df_out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

print("[OK] fusion done")
print(df_out.head())
print()
print("columns:")
print(df_out.columns.tolist())
