import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

# ------------------------------------------------------------
# CONFIG — ALWAYS USE SCRIPT DIRECTORY
# ------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR
OUTPUT_DIR = SCRIPT_DIR / "stats"
OUTPUT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# ISSUE CATEGORY FUNCTION
# ------------------------------------------------------------
def categorize_issue(issue: str) -> str:
    issue_l = issue.lower()

    if any(k in issue_l for k in ["over", "generaliz", "extrapol", "benefit", "framed", "stronger"]):
        return "overinterpretation"
    if any(k in issue_l for k in ["not measured", "invented", "implied", "qualitative", "presented as outcomes"]):
        return "hallucinated_data"
    if any(k in issue_l for k in ["direction", "increase", "decrease", "ambig"]):
        return "direction_mismatch"
    if any(k in issue_l for k in ["review", "observ", "design", "protocol", "causal", "heterogeneous", "policy"]):
        return "study_design_error"
    if any(k in issue_l for k in ["limitation", "sample size", "conflicting", "not emphasized", "exploratory"]):
        return "missing_limitations"
    if any(k in issue_l for k in ["cutoff", "terminology", "correlation", "detail", "figure"]):
        return "technical_error"
    if any(k in issue_l for k in ["redund", "non-", "beyond", "other studies", "prominently"]):
        return "noise_or_redundancy"

    return "other"

# ------------------------------------------------------------
# LOAD JSON FILES
# ------------------------------------------------------------
def load_jsons():
    rows = []
    for file in DATA_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["source_file"] = file.name
                rows.append(data)
        except:
            pass
    return pd.DataFrame(rows)

df = load_jsons()
if df.empty:
    raise ValueError(f"No JSON validation files found in: {DATA_DIR}")

print(f"[INFO] Loaded {len(df)} validation results.")

# ------------------------------------------------------------
# SUMMARY STATISTICS
# ------------------------------------------------------------
stats = {
    "count": len(df),
    "mean_fidelity": df["fidelity_score"].mean(),
    "mean_hallucination": df["hallucination_score"].mean(),
    "mean_direction_accuracy": df["direction_accuracy_score"].mean(),
    "mean_completeness": df["completeness_score"].mean(),
    "excellent_rate": (df["overall_rating"] == "excellent").mean(),
    "hallucinated_rate": (df["overall_rating"] == "hallucinated").mean()
}

pd.DataFrame([stats]).to_csv(OUTPUT_DIR / "overall_stats.csv", index=False)
print("[INFO] Saved overall_stats.csv")

# ------------------------------------------------------------
# ISSUE CLUSTERING
# ------------------------------------------------------------
all_issues = []
for issues in df["issues"]:
    if isinstance(issues, list):
        all_issues.extend(issues)

# basic issue counts
issue_counts = Counter(all_issues)
issue_df = (
    pd.DataFrame(issue_counts.items(), columns=["issue", "count"])
    .sort_values("count", ascending=False)
)

# ------------------------------------------------------------
# CATEGORIZE ISSUES
# ------------------------------------------------------------
issue_df["category"] = issue_df["issue"].apply(categorize_issue)
issue_df.to_csv(OUTPUT_DIR / "issue_clusters.csv", index=False)

print("[INFO] Saved issue_clusters.csv with categories.")

# ------------------------------------------------------------
# CATEGORY COUNTS
# ------------------------------------------------------------
category_counts = issue_df["category"].value_counts().reset_index()
category_counts.columns = ["category", "count"]
category_counts.to_csv(OUTPUT_DIR / "issue_categories.csv", index=False)

print("[INFO] Saved issue_categories.csv")

# ------------------------------------------------------------
# SCORE HISTOGRAMS
# ------------------------------------------------------------
plots = [
    ("fidelity_score", "fidelity_hist.png"),
    ("hallucination_score", "hallucination_hist.png"),
    ("direction_accuracy_score", "direction_accuracy_hist.png"),
    ("completeness_score", "completeness_hist.png")
]

for col, filename in plots:
    plt.figure(figsize=(8, 4))
    df[col].hist(bins=10)
    plt.title(col.replace("_", " ").title())
    plt.xlabel("Score")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename)
    plt.close()

print("[INFO] Saved score histograms.")

# ------------------------------------------------------------
# PLOT ISSUE CATEGORIES
# ------------------------------------------------------------
plt.figure(figsize=(10, 5))
plt.bar(category_counts["category"], category_counts["count"])
plt.xticks(rotation=70, ha="right")
plt.title("Issue Categories")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "issues_by_category.png")
plt.close()

print("[INFO] Saved issues_by_category.png")
print("[DONE] All statistics generated in:", OUTPUT_DIR)
