"""Check the plotted positions against the numerical records in this package."""
import json
from pathlib import Path
P = Path(__file__).resolve().parent
load = lambda name: json.loads((P / name).read_text(encoding="utf-8"))
f = load("data/figure_data.json")
delivery = load("data/v20_delivery.json")
ratings = load("data/ratings.json")
summary = load("recomputed_summary.json")
grid = {(r["arm"], r["cap"]): r for r in summary["delivery_grid"] if r["cohort"] == "Q24"}
assert len(f["grid"]) == len(grid) == 25
for row in f["grid"]:
    other = grid[row["arm"], row["cap"]]
    assert row["complete"] == other["complete"] and row["n"] == other["n"]
for r in f["paired"]:
    left = {x["question"]: x["complete"] for x in delivery if x["cohort"] == "Q24" and x["cap"] == r["cap"] and x["arm"] == "B1"}
    right = {x["question"]: x["complete"] for x in delivery if x["cohort"] == "Q24" and x["cap"] == r["cap"] and x["arm"] == "B2"}
    assert len(left) == len(right) == 24 and left.keys() == right.keys()
    assert (r["win"],r["loss"],r["tie"]) == (sum(right[k] and not left[k] for k in left),sum(left[k] and not right[k] for k in left),sum(left[k] == right[k] for k in left))
v90 = {(r["question"],r["arm"],r["cap"]):r for r in ratings if r["cohort"] == "v90_final"}
assert len(f["v90"]) == len(v90) == 24
for r in f["v90"]:
    x=v90[r["id"],r["arm"],r["cap"]]
    assert r["correctness"] == x["correctness"] and r["input_support"] == x["support"] and r["core_completion"] == x["core_label_original"]
    assert r["pass"] == (x["core_label_original"] == "是" and x["correctness"] == 2 and x["support"] == 2)
    assert r["mechanical_delivery"] == x["delivery"] and r["pass"] == x["passed"]
print("Figure source checks passed: 25 grid summaries, 5 paired budgets, 24 V90 positions.")
