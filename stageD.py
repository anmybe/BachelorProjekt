# ============================================
# Stage D – LLM-Analyse der Chunks mit Gemini API
# ============================================

import os
import json
import time
from pathlib import Path
from tqdm import tqdm
import google.generativeai as genai

# ==== EINSTELLUNGEN ====
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_FILE = BASE_DIR / "stageC_metadata.json"
CHUNK_DIR = BASE_DIR / "chunks"
OUT_DIR = BASE_DIR / "results_stageD"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = BASE_DIR / "stageD_metadata.json"

MODEL_NAME = "models/gemini-2.5-flash"      # du kannst auch "gemini-1.5-flash" testen (billiger/schneller)
MAX_RETRIES = 3 

# ==== API KEY LADEN ====
genai.configure(api_key="AIzaSyCoTjmHS7ugwRiVG4j_fvuBG8HpdS6QG8Y")

# ==== PROMPT-VORLAGE ====
PROMPT_TEMPLATE = """You are an expert biomedical text analyst specialized in sports physiology and exercise immunology.

From the following scientific text, decide if it is relevant to sports or exercise physiology.
If relevant, extract the following fields:
- exercise_types: type, duration, environmental conditions
- biomarkers: biochemical or immunological markers studied
- observed_effects: pre- vs post-exercise differences
- statistical_significance: p-values or qualitative statements
- sex_differences: if reported
- evidence_strength: strong, moderate, weak, or non-significant

Return ONLY valid JSON in the exact structure below.
Do NOT include explanations, comments, or text outside the JSON.

[
  {{
    "relevance": "",
    "exercise_types": [],
    "biomarkers": [],
    "observed_effects": {{}},
    "statistical_significance": {{}},
    "sex_differences": "",
    "evidence_strength": ""
  }}
]
Text:
\"\"\"{text}\"\"\"
"""

# ==== FUNKTION FÜR GEMINI-AUFRUF ====
def analyze_text_with_gemini(text: str):
    model = genai.GenerativeModel(MODEL_NAME)
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(PROMPT_TEMPLATE.format(text=text[:20000]))
            content = response.text.strip()

            # Validierungslogik
            if not content.startswith("["):
                raise ValueError("Invalid JSON response")
            return json.loads(content)
        except Exception as e:
            print(f"⚠️ Fehler (Versuch {attempt+1}): {e}")
            time.sleep(5)
    return None


# ==== PIPELINE ====
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    papers = json.load(f)

results = []
for p in tqdm(papers):
    paper_id = p.get("pmcid") or p.get("doi") or p.get("pmid")
    paper_results = []

    for chunk in p["chunks"]:
        chunk_path = Path(chunk["chunk_file"])
        text = chunk_path.read_text(encoding="utf-8", errors="ignore")
        res = analyze_text_with_gemini(text)
        if res:
            out_file = OUT_DIR / f"{chunk_path.stem}_result.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2, ensure_ascii=False)
            paper_results.append({"section": chunk["section"], "result_file": str(out_file)})

    results.append({
        "pmid": p.get("pmid"),
        "doi": p.get("doi"),
        "pmcid": p.get("pmcid"),
        "results": paper_results
    })

# ==== SPEICHERN ====
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"✅ Stage D abgeschlossen – {len(results)} Papers verarbeitet")
print(f"📦 Ergebnisse gespeichert unter: {OUT_DIR}")
print(f"📜 Metadaten: {OUT_PATH}")
