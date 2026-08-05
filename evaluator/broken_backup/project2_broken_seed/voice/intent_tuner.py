# -*- coding: utf-8 -*-
from collections import defaultdict
from pypinyin import lazy_pinyin
from rapidfuzz import fuzz
import re

INTENTS = {
    "HEART_RATE": {
        "phrases": ["心率检测", "测心率", "查看心率", "心跳检测", "测心跳", "看看心跳", "测脉搏"],
        "keywords": ["心率", "心跳", "脉搏", "心律"],
        "regex": r"(心(率|跳)|脉搏)",
        "th": 68,
    },
    "SLEEP_SUMMARY": {
        "phrases": ["昨晚睡眠情况", "睡眠报告", "昨夜睡眠报告", "睡眠质量", "昨晚睡得怎么样", "昨晚的睡眠统计"],
        "keywords": ["昨晚", "昨夜", "睡眠", "报告", "质量", "统计"],
        "regex": r"(昨(晚|夜).*(睡|眠)|睡眠.*(报告|质量|统计))",
        "th": 70,
    },
    "LEAVE_BED": {
        "phrases": ["离床提醒", "离床检测", "下床提醒", "有没有下床", "落床报警"],
        "keywords": ["离床", "下床", "落床", "报警", "提醒", "记录"],
        "regex": r"((离|下|落)床|报警|提醒)",
        "th": 68,
    },
    "POSTURE": {
        "phrases": ["睡姿识别", "姿势检测", "体位识别", "看看睡姿", "仰卧还是侧卧", "有没有翻身"],
        "keywords": ["睡姿", "姿势", "体位", "仰卧", "侧卧", "俯卧", "趴", "翻身"],
        "regex": r"(睡姿|体位|仰卧|侧卧|俯卧|翻身|姿势)",
        "th": 70,
    },
    "SNORE": {
        "phrases": ["鼾声分析", "鼾声检测", "打呼情况", "打呼严重吗", "呼吸暂停", "鼾声疾病识别"],
        "keywords": ["鼾", "打呼", "呼吸暂停", "鼾声", "打鼾"],
        "regex": r"(鼾|打呼|打鼾|呼吸暂停)",
        "th": 70,
    },
}
PHRASE_PINYIN = {k: [" ".join(lazy_pinyin(p)) for p in v["phrases"]] for k,v in INTENTS.items()}

def score_intent(text: str):
    q_py = " ".join(lazy_pinyin(text))
    fuzzy_scores = {k: max(fuzz.token_set_ratio(q_py, py) for py in pys) for k, pys in PHRASE_PINYIN.items()}
    kw_scores = {}
    for k, cfg in INTENTS.items():
        hits = sum(1 for w in cfg["keywords"] if w in text)
        kw_scores[k] = min(hits * 15, 45)
    re_scores = {k: (25 if re.search(v["regex"], text) else 0) for k, v in INTENTS.items()}
    final = {k: 0.6*fuzzy_scores[k] + 0.3*kw_scores[k] + 0.1*re_scores[k] for k in INTENTS.keys()}
    best = max(final, key=final.get); return best, final[best]

# —— 标注样本（同你之前那份，可继续增删）——
SAMPLES = [
    ("心率检测", "HEART_RATE"), ("查一下心率", "HEART_RATE"), ("看看心跳", "HEART_RATE"),
    ("测心跳", "HEART_RATE"), ("心率多少", "HEART_RATE"), ("心跳多少", "HEART_RATE"),
    ("帮我看心率", "HEART_RATE"), ("测一下心率", "HEART_RATE"), ("心律检测", "HEART_RATE"),
    ("心跳快不快", "HEART_RATE"), ("测测脉搏", "HEART_RATE"),

    ("昨晚睡眠情况", "SLEEP_SUMMARY"), ("昨晚睡得咋样", "SLEEP_SUMMARY"),
    ("昨夜睡眠报告", "SLEEP_SUMMARY"), ("看看昨天睡觉情况", "SLEEP_SUMMARY"),
    ("昨晚睡得好吗", "SLEEP_SUMMARY"), ("睡眠质量", "SLEEP_SUMMARY"),
    ("把昨晚总结一下", "SLEEP_SUMMARY"), ("昨晚的睡眠统计", "SLEEP_SUMMARY"),

    ("离床提醒", "LEAVE_BED"), ("离床检测", "LEAVE_BED"), ("下床了没", "LEAVE_BED"),
    ("落床报警", "LEAVE_BED"), ("看看有没有下床", "LEAVE_BED"), ("我刚下床", "LEAVE_BED"),
    ("离床记录", "LEAVE_BED"), ("有没有离床", "LEAVE_BED"),

    ("睡姿识别", "POSTURE"), ("我现在什么睡姿", "POSTURE"), ("仰卧还是侧卧", "POSTURE"),
    ("姿势检测", "POSTURE"), ("趴着吗", "POSTURE"), ("翻身没有", "POSTURE"),
    ("体位识别", "POSTURE"), ("看看睡姿", "POSTURE"),

    ("鼾声分析", "SNORE"), ("打呼严重吗", "SNORE"), ("我昨晚打鼾没", "SNORE"),
    ("有没有呼吸暂停", "SNORE"), ("鼾声检测", "SNORE"), ("打呼情况", "SNORE"),
    ("鼾声疾病识别", "SNORE"), ("看看打鼾", "SNORE"),

    ("今天天气不错", "CHAT"), ("放一首音乐", "CHAT"), ("讲个笑话", "CHAT"),
]

def evaluate():
    # 用各意图的独立阈值进行决策
    labels = list(INTENTS.keys()) + ["CHAT"]
    m = {l: {"tp":0,"fp":0,"fn":0} for l in labels}
    details = []
    for text, gold in SAMPLES:
        pred_k, s = score_intent(text)
        th = INTENTS[pred_k]["th"]
        pred = pred_k if s >= th else "CHAT"
        details.append((text, gold, pred, s, th))
        if pred == gold:
            m[gold]["tp"] += 1
        else:
            m[pred]["fp"] += 1
            m[gold]["fn"] += 1

    def prf(v):
        tp, fp, fn = v["tp"], v["fp"], v["fn"]
        P = tp/(tp+fp) if (tp+fp) else 0.0
        R = tp/(tp+fn) if (tp+fn) else 0.0
        F = 2*P*R/(P+R) if (P+R) else 0.0
        return P,R,F

    # per-class
    print("=== 每类 P/R/F1 ===")
    for k in labels:
        P,R,F = prf(m[k]); print(f"{k:14s}  P={P:.3f} R={R:.3f} F1={F:.3f}")

    # micro
    TP=sum(v["tp"] for v in m.values()); FP=sum(v["fp"] for v in m.values()); FN=sum(v["fn"] for v in m.values())
    P=TP/(TP+FP) if (TP+FP) else 0.0; R=TP/(TP+FN) if (TP+FN) else 0.0; F=2*P*R/(P+R) if (P+R) else 0.0
    print("\nMicro  P=%.3f R=%.3f F1=%.3f" % (P,R,F))

    print("\n=== 逐样本 ===")
    for text, gold, pred, s, th in details:
        mark = "✅" if gold==pred else "❌"
        print(f"{mark}  {text: <12} -> {pred:12s} (score={s:.1f}, th={th})  [gold={gold}]")

if __name__ == "__main__":
    evaluate()
