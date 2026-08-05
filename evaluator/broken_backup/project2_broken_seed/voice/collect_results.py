# -*- coding: utf-8 -*-
"""
把 eval_asr_aishell.py 的 JSON 输出汇总为 CSV
建议你的单次结果重定向保存为:
  C:\rkvoice_demo\results\<dataset>_<model>.json
例如:
  aishell1_small.json / aishell1_tiny.json / thchs30_small.json ...
"""
import json, csv, glob, os

IN_DIR  = r"C:\rkvoice_demo\results"
OUT_CSV = r"C:\rkvoice_demo\results\summary.csv"

rows = []
for fp in glob.glob(os.path.join(IN_DIR, "*.json")):
    base = os.path.basename(fp)
    name = os.path.splitext(base)[0]
    try:
        with open(fp,"r",encoding="utf-8") as f:
            obj = json.load(f)
        rows.append([name, obj.get("CER"), obj.get("AVG_RTF")])
    except Exception as e:
        print("skip", fp, e)

os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
with open(OUT_CSV,"w",encoding="utf-8",newline="") as f:
    wt = csv.writer(f)
    wt.writerow(["exp_name","CER","AVG_RTF"])
    wt.writerows(rows)

print("OK ->", OUT_CSV)
