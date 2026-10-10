import csv
import random

# Same constants and weights as backend/services/fraud_scoring.py
LOWBALL, OVERBID, FAST_RELEASE, NEW_HOURS, LARGE, RAPID_COUNT = 0.30, 1.50, 300, 24, 50000, 5
TIERS = [(75, "CRITICAL"), (50, "HIGH"), (25, "MEDIUM"), (0, "LOW")]


def tier(score):
    return next(name for limit, name in TIERS if score >= limit)


def score_preventive(c):
    s = 0
    if c["ratio"] < LOWBALL: s += 30
    if c["ratio"] > OVERBID: s += 15
    if c["age_h"] < NEW_HOURS: s += 20
    if c["recent_bids"] > RAPID_COUNT: s += 20
    if c["amount"] >= LARGE: s += 10
    return s


def score_audit(c):
    s = 0
    if c["ratio"] < LOWBALL: s += 30
    if c["ratio"] > OVERBID: s += 15
    if c["release_s"] is not None and 0 <= c["release_s"] < FAST_RELEASE: s += 25
    if c["age_h"] < NEW_HOURS: s += 20
    if c["amount"] >= LARGE: s += 10
    return s


random.seed(24262)
cases = []


def add(label, kind, ratio, budget, age_h, recent, release_s):
    cases.append({"label": label, "kind": kind, "ratio": round(ratio, 2),
                  "amount": round(ratio * budget), "age_h": round(age_h, 1),
                  "recent_bids": recent, "release_s": release_s})


# Legitimate: typical behaviour (40)
for _ in range(40):
    add(0, "legit_typical", random.uniform(0.6, 1.2), random.choice([8000, 15000, 30000, 40000]),
        random.uniform(72, 3000), random.randint(0, 3), random.randint(900, 200000))

# Legitimate but unusual: honest edge cases a rule set may wrongly flag (15)
for _ in range(5):   # honest new freelancer
    add(0, "legit_new_account", random.uniform(0.7, 1.1), 20000, random.uniform(2, 20), random.randint(0, 2), random.randint(1200, 90000))
for _ in range(5):   # honest large contract
    add(0, "legit_large", random.uniform(0.9, 1.1), random.choice([60000, 80000, 100000]), random.uniform(200, 2000), random.randint(0, 2), random.randint(3600, 500000))
for _ in range(3):   # honest cheap bid, e.g. simple task
    add(0, "legit_cheap", random.uniform(0.22, 0.29), 20000, random.uniform(100, 1500), random.randint(0, 3), random.randint(1200, 90000))
for _ in range(2):   # honest very quick job
    add(0, "legit_quick_job", random.uniform(0.8, 1.0), 5000, random.uniform(100, 1500), 1, random.randint(200, 290))

# Fraudulent: strong, multi signal patterns (25)
for _ in range(10):  # lowball plus new account
    add(1, "fraud_lowball_new", random.uniform(0.05, 0.25), 40000, random.uniform(1, 20), random.randint(0, 3), random.randint(60, 250))
for _ in range(8):   # spam bidder with lowballs
    add(1, "fraud_spam_lowball", random.uniform(0.08, 0.28), 30000, random.uniform(1, 100), random.randint(7, 15), random.randint(100, 280))
for _ in range(5):   # large, new account, quick release
    add(1, "fraud_large_new_fast", random.uniform(0.9, 1.1), random.choice([60000, 90000]), random.uniform(1, 20), random.randint(0, 2), random.randint(30, 250))
for _ in range(2):   # overbid, new, large, spam
    add(1, "fraud_overbid_combo", random.uniform(1.6, 2.2), 40000, random.uniform(1, 20), random.randint(6, 12), random.randint(60, 250))

# Fraudulent but subtle: single weak signal, hard to catch (10)
for _ in range(4):
    add(1, "fraud_subtle_fast_release", random.uniform(0.8, 1.0), 20000, random.uniform(100, 2000), 1, random.randint(30, 280))
for _ in range(3):
    add(1, "fraud_subtle_spam_only", random.uniform(0.7, 1.1), 20000, random.uniform(100, 2000), random.randint(6, 9), random.randint(1000, 90000))
for _ in range(3):
    add(1, "fraud_subtle_new_only", random.uniform(0.7, 1.1), 20000, random.uniform(2, 20), 1, random.randint(1000, 90000))

for c in cases:
    c["score_pre"] = score_preventive(c)
    c["score_audit"] = score_audit(c)


def metrics(key, threshold):
    tp = sum(1 for c in cases if c["label"] == 1 and c[key] >= threshold)
    fn = sum(1 for c in cases if c["label"] == 1 and c[key] < threshold)
    fp = sum(1 for c in cases if c["label"] == 0 and c[key] >= threshold)
    tn = sum(1 for c in cases if c["label"] == 0 and c[key] < threshold)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(cases)
    return tp, fp, tn, fn, prec, rec, f1, acc


print(f"Cases: {len(cases)} ({sum(c['label'] for c in cases)} fraud, {sum(1 - c['label'] for c in cases)} legitimate)")
rows = []
for name, key in [("Preventive (bid acceptance)", "score_pre"), ("Audit (contract)", "score_audit")]:
    print(f"\n{name}")
    print("Thr  TP  FP  TN  FN  Prec   Rec    F1     Acc")
    for t in (25, 50, 75):
        tp, fp, tn, fn, p, r, f, a = metrics(key, t)
        print(f"{t:>3} {tp:>3} {fp:>3} {tn:>3} {fn:>3}  {p:.2f}   {r:.2f}   {f:.2f}   {a:.2f}")
        rows.append([name, t, tp, fp, tn, fn, round(p, 3), round(r, 3), round(f, 3), round(a, 3)])
    print("Tier counts (legit / fraud):")
    for _, tname in TIERS:
        l = sum(1 for c in cases if c["label"] == 0 and tier(c[key]) == tname)
        fr = sum(1 for c in cases if c["label"] == 1 and tier(c[key]) == tname)
        print(f"  {tname:<9} {l:>3} / {fr:>3}")

with open("fraud_eval_summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["scorer", "threshold", "TP", "FP", "TN", "FN", "precision", "recall", "f1", "accuracy"])
    w.writerows(rows)
with open("fraud_eval_cases.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(cases[0].keys()))
    w.writeheader()
    w.writerows(cases)
print("\nSaved fraud_eval_summary.csv and fraud_eval_cases.csv")
