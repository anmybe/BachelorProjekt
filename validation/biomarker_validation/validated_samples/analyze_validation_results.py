import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ------------------------------------------------------------
# CONFIG — scan the folder where this script is located
# ------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR
OUTPUT_DIR = SCRIPT_DIR / "stats"
OUTPUT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# LOAD ALL JSON FILES
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

print(f"[INFO] Loaded {len(df)} biomarker summaries.")

# ------------------------------------------------------------
# SAVE RAW TABLE
# ------------------------------------------------------------
df.to_csv(OUTPUT_DIR / "all_results.csv", index=False)
print("[INFO] Saved all_results.csv")

# ------------------------------------------------------------
# SUMMARY STATISTICS
# ------------------------------------------------------------
numeric_cols = [
    "factual_accuracy_score",
    "coverage_score",
    "hallucination_score",
    "direction_accuracy_score",
    "group_validity_score",
    "relevance_score_validity",
    "context_accuracy_score",
    "sport_implication_score"
]

stats = df[numeric_cols].mean().round(2)
stats["count"] = len(df)

stats.to_csv(OUTPUT_DIR / "overall_stats.csv")
print("[INFO] Saved overall_stats.csv")

# ------------------------------------------------------------
# RATING DISTRIBUTION
# ------------------------------------------------------------
rating_counts = df["overall_alignment"].value_counts().reindex(
    ["excellent", "good", "acceptable", "poor", "hallucinated"], fill_value=0
)

plt.figure(figsize=(8,4))
plt.bar(rating_counts.index, rating_counts.values)
plt.title("Overall Rating Distribution")
plt.xlabel("Rating")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "rating_distribution.png")
plt.close()
print("[INFO] Saved rating_distribution.png")

# ------------------------------------------------------------
# HISTOGRAMS FOR ALL SCORES
# ------------------------------------------------------------
for col in numeric_cols:
    plt.figure(figsize=(8,4))
    df[col].hist(bins=10)
    plt.title(f"{col.replace('_', ' ').title()} Distribution")
    plt.xlabel("Score")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{col}_hist.png")
    plt.close()

print("[INFO] Saved score histograms.")

# ------------------------------------------------------------
# OPTIONAL: CORRELATION HEATMAP
# ------------------------------------------------------------
plt.figure(figsize=(10, 7))
sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="viridis")
plt.title("Correlation Heatmap of Validation Scores")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "correlation_heatmap.png")
plt.close()

print("[INFO] Saved correlation_heatmap.png")

print("\n[DONE] All statistics and graphics generated in the 'stats' folder.")
