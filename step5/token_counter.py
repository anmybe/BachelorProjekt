import json
import csv
from pathlib import Path

# ---------------------------------------------------
# CONFIG – same directory as script
# ---------------------------------------------------
BASE_DIR = Path(__file__).parent
INPUT_JSON = BASE_DIR / "result_step4.json"
OUTPUT_CSV = BASE_DIR / "biomarker_summary_step4.csv"

CHARS_PER_TOKEN = 3.5

# ---------------------------------------------------
# TOKEN UTILS
# ---------------------------------------------------
def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    outputs = list(reader)

# ---------------------------------------------------
# FIXED PROMPT (Stage 5)
# ---------------------------------------------------
FIXED_PROMPT = """
You are a sports medicine and exercise physiology expert.
Your analysis MUST stay strictly within the domain of:

- exercise physiology
- training load monitoring
- recovery and adaptation
- overtraining / underrecovery
- metabolic flexibility
- inflammation in athletes
- performance diagnostics
- muscle damage and repair
- cardiovascular and endocrine adaptation

Ignore all disease-related or non-athletic findings unless they directly affect training, recovery, or performance.
If a study has NO athletic context, explicitly state this and avoid speculation.
"""

fixed_prompt_tokens = estimate_tokens(FIXED_PROMPT)

# ---------------------------------------------------
# INPUT TOKENS (Stage 5)
# ---------------------------------------------------
input_tokens_total = 0
api_calls = 0

for biomarker in data:
    name = biomarker.get("standard_name", "")
    findings = biomarker.get("aggregated_source_findings_DEBUG", [])

    dynamic_part = name + json.dumps(findings, indent=2, ensure_ascii=False)

    input_tokens_total += fixed_prompt_tokens
    input_tokens_total += estimate_tokens(dynamic_part)
    api_calls += 1

# ---------------------------------------------------
# OUTPUT TOKENS (Stage 5)
# ---------------------------------------------------
output_tokens_total = 0

for row in outputs:
    output_text = json.dumps({
        "activity_context_summary": row.get("Activity Context Summary", ""),
        "effect_summary": row.get("Effect Summary", ""),
        "sport_specific_implication_summary": row.get("Sport Implications", ""),
        "relevance_score_sport": row.get("Relevance for Sports (1–10)", ""),
        "biomarker_groups": row.get("Biomarker Groups", "")
    }, ensure_ascii=False)

    output_tokens_total += estimate_tokens(output_text)

# ---------------------------------------------------
# METRICS
# ---------------------------------------------------
processed_units = len(outputs)
total_tokens = input_tokens_total + output_tokens_total
avg_tokens_per_unit = int(total_tokens / processed_units) if processed_units else 0

# ---------------------------------------------------
# OUTPUT – SAME FORMAT
# ---------------------------------------------------
print("\nStage 5 – Interpretation / Summarization")
print("---------------------------------------")
print(f"Processed Units     {processed_units} Biomarkers")
print(f"API Calls           {api_calls}")
print(f"Input Tokens        {input_tokens_total:,}")
print(f"Output Tokens       {output_tokens_total:,}")
print(f"Total Tokens        {total_tokens:,}")
print(f"Avg. Tokens/Unit    {avg_tokens_per_unit}")
