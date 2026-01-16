import json
import re
from pathlib import Path

# ===================================================
# CONFIG
# ===================================================

# Basis: Script liegt in step1-2/
BASE_DIR = Path(__file__).parent 
TEXT_DIR = BASE_DIR / "intermediary_results" / "fulltext" / "fulltext_raw3"
CHUNK_DIR = BASE_DIR / "paper_pipeline_results" / "chunks_gemini_semantic_serial3"

CHARS_PER_TOKEN = 3.5
MAX_CHARS = 15000
OVERLAP = 1000

# ===================================================
# SAFETY CHECKS
# ===================================================
assert BASE_DIR.exists(), f"Missing BASE_DIR: {BASE_DIR}"
assert TEXT_DIR.exists(), f"Missing TEXT_DIR: {TEXT_DIR}"
assert CHUNK_DIR.exists(), f"Missing CHUNK_DIR: {CHUNK_DIR}"

# ===================================================
# UTILS
# ===================================================
def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def split_with_overlap(text: str, window=MAX_CHARS, overlap=OVERLAP):
    segments = []
    i = 0
    while i < len(text):
        segments.append(text[i:i + window])
        i += window - overlap
    return segments

# ===================================================
# FIXED PROMPT (Stage C)
# ===================================================
FIXED_PROMPT = (
    "You are an expert biomedical text segmenter. "
    "Split the input text into coherent semantic chunks."
)
FIXED_PROMPT_TOKENS = estimate_tokens(FIXED_PROMPT)

# ===================================================
# COUNTERS
# ===================================================
total_input_tokens = 0
total_output_tokens = 0
api_calls = 0
processed_papers = 0

# ===================================================
# MAIN LOOP — DRIVE FROM CHUNK FILES
# ===================================================
chunk_files = list(CHUNK_DIR.glob("*.json"))

print(f"Found {len(chunk_files)} chunk files")

for chunk_file in chunk_files:
    try:
        chunk_json = json.loads(chunk_file.read_text(encoding="utf-8"))
    except Exception:
        continue

    # Skip non-chunk JSONs
    if "chunks" not in chunk_json:
        continue

    paper_id = chunk_file.stem.replace("_chunks", "")
    txt_path = TEXT_DIR / f"{paper_id}.txt"

    if not txt_path.exists():
        continue

    # ---------------- INPUT SIDE ----------------
    text = clean_text(txt_path.read_text(encoding="utf-8", errors="ignore"))
    if not text:
        continue

    segments = split_with_overlap(text)

    for seg in segments:
        total_input_tokens += FIXED_PROMPT_TOKENS
        total_input_tokens += estimate_tokens(seg)
        api_calls += 1

    # ---------------- OUTPUT SIDE ----------------
    for c in chunk_json["chunks"]:
        total_output_tokens += estimate_tokens(c.get("text", ""))

    processed_papers += 1

# ===================================================
# METRICS
# ===================================================
total_tokens = total_input_tokens + total_output_tokens
avg_tokens_per_call = int(total_tokens / api_calls) if api_calls else 0

# ===================================================
# OUTPUT
# ===================================================
print("\nStage C – Overlap Split + Semantic Chunking")
print("------------------------------------------")
print(f"Processed Units     {processed_papers} Papers")
print(f"API Calls           {api_calls}")
print(f"Input Tokens        {total_input_tokens:,}")
print(f"Output Tokens       {total_output_tokens:,}")
print(f"Total Tokens        {total_tokens:,}")
print(f"Avg. Tokens/Call    {avg_tokens_per_call}")
