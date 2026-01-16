import csv
import json
import os
import random

# ---------------- CONFIG ----------------
BASE_DIR = "step5"

CSV_FILE = os.path.join(BASE_DIR, "biomarker_summary_step4.csv")
JSON_FILE = os.path.join(BASE_DIR, "result_step4.json")
OUTPUT_DIR = os.path.join("validation", "biomarker_validation", "samples")

MIN_RELEVANCE = 6
SAMPLES_PER_GROUP = 3
MAX_SAMPLES = 20

TARGET_GROUPS = [
    "inflammatory_changes",
    "metabolic",
    "glycemic",
    "cardio_risk",
    "endocrine_response",
    "cell_damage",
    "muscle_damage",
]
# ----------------------------------------

# optional reproduzierbar
# random.seed(42)

# ---------------- LOAD JSON ----------------
with open(JSON_FILE, "r", encoding="utf-8") as f:
    biomarker_json = json.load(f)

json_lookup = {
    b["standard_name"].lower(): b
    for b in biomarker_json
}

# ---------------- LOAD CSV ----------------
grouped_rows = {g: [] for g in TARGET_GROUPS}

with open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        relevance = float(row["Relevance for Sports (1–10)"])
        if relevance < MIN_RELEVANCE:
            continue

        group = row["Biomarker Groups"].strip().lower()
        if group in grouped_rows:
            grouped_rows[group].append(row)

# ---------------- PROCESS ----------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

sample_counter = 1

for group in TARGET_GROUPS:
    rows = grouped_rows[group]
    if not rows:
        continue

    selected = random.sample(
        rows, min(SAMPLES_PER_GROUP, len(rows))
    )

    for row in selected:
        if sample_counter > MAX_SAMPLES:
            break

        sample_dir = os.path.join(
            OUTPUT_DIR, f"sample_{sample_counter:03d}"
        )
        os.makedirs(sample_dir, exist_ok=True)

        biomarker_name = row["Biomarker"]
        biomarker_key = biomarker_name.lower()

        # --- JSON ---
        if biomarker_key in json_lookup:
            with open(
                os.path.join(sample_dir, "biomarker.json"),
                "w",
                encoding="utf-8"
            ) as jf:
                json.dump(
                    json_lookup[biomarker_key],
                    jf,
                    indent=2,
                    ensure_ascii=False
                )

        # --- TXT ---
        with open(
            os.path.join(sample_dir, "biomarker_profile.txt"),
            "w",
            encoding="utf-8"
        ) as tf:
            tf.write("BIOMARKER PROFILE\n")
            tf.write("=" * 30 + "\n\n")

            tf.write("Biomarker\n---------\n")
            tf.write(f"{row['Biomarker']}\n\n")

            tf.write("Biomarker Group\n---------------\n")
            tf.write(f"{row['Biomarker Groups']}\n\n")

            tf.write("Relevance for Sports\n--------------------\n")
            tf.write(f"{row['Relevance for Sports (1–10)']} / 10\n\n")

            tf.write("Activity Context\n----------------\n")
            tf.write(f"{row['Activity Context Summary']}\n\n")

            tf.write("Effect Summary\n--------------\n")
            tf.write(f"{row['Effect Summary']}\n\n")

            tf.write("Sport Implications\n------------------\n")
            tf.write(f"{row['Sport Implications']}\n\n")

            tf.write("Document References\n-------------------\n")
            tf.write(f"{row['Document IDs']}\n\n")

            tf.write("Occurrences in Dataset\n---------------------\n")
            tf.write(f"{row['Occurrences in Dataset']}\n")

        sample_counter += 1

print(f"Done. Created {sample_counter - 1} samples.")
