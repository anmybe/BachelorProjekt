# ============================================
# Stage C – Volltext (.txt) → Semantische Chunks mit Gemini 2.5 Flash (Free API)
# ============================================

import json, re
from pathlib import Path
from tqdm import tqdm
import google.generativeai as genai

# ==== EINSTELLUNGEN ====
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_FILE = BASE_DIR / "stageB_metadata.json"
TEXT_DIR = BASE_DIR / "fulltext_raw"
CHUNK_DIR = BASE_DIR / "chunks_gemini"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = BASE_DIR / "stageC_metadata_gemini.json"

MODEL = "gemini-2.5-flash"   # kostenlos im Free Tier
MAX_TEXT_LEN = 12000
USD_PER_1K_INPUT = 0.0000    # Free Tier → keine Kosten
USD_PER_1K_OUTPUT = 0.0000

# ==== GEMINI CONFIG ====
genai.configure(api_key="")
model = genai.GenerativeModel(MODEL)

# ==== HELFER ====
def clean_text(txt: str) -> str:
    return re.sub(r"\s+", " ", txt).strip()

def gemini_chunk(text: str):
    """Sendet Text an Gemini 2.5 Flash und erhält semantische Chunks als JSON."""
    text = text[:MAX_TEXT_LEN]
    prompt = f"""
You are a scientific text segmenter.
Split the given research article text into semantically coherent chunks
WITHOUT summarizing, paraphrasing, or interpreting.
Keep the original wording exactly as is.

Rules:
- Preserve all sentences unchanged.
- End chunks only at natural semantic boundaries (sections or paragraph ends).
- Each chunk should be about 800–1200 tokens long.
- Return valid JSON in this structure:

{{
  "chunks": [
    {{ "id": 1, "text": "..." }},
    {{ "id": 2, "text": "..." }}
  ]
}}

Text to split:
{text}
"""

    response = model.generate_content(prompt)
    usage = getattr(response, "usage_metadata", None)
    in_tok = getattr(usage, "prompt_token_count", 0)
    out_tok = getattr(usage, "candidates_token_count", 0)
    cost = (in_tok/1000*USD_PER_1K_INPUT) + (out_tok/1000*USD_PER_1K_OUTPUT)

    try:
        data = json.loads(response.text)
        return data.get("chunks", []), in_tok, out_tok, cost
    except Exception:
        return [{"id": 1, "text": response.text.strip()}], in_tok, out_tok, cost


# ==== PIPELINE ====
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    papers = json.load(f)

meta_out, total_cost = [], 0.0

for p in tqdm(papers, desc="Gemini Stage C"):
    path = Path(p.get("text_file", ""))
    if not path.exists():
        print(f"⚠️ Datei fehlt: {path}")
        continue

    fulltext = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not fulltext:
        continue

    chunks, in_tok, out_tok, cost = gemini_chunk(fulltext)
    total_cost += cost

    chunk_meta = []
    for ch in chunks:
        cid = ch.get("id", len(chunk_meta)+1)
        fname = f"{path.stem}_{cid:02d}.txt"
        cpath = CHUNK_DIR / fname
        cpath.write_text(ch["text"], encoding="utf-8")
        chunk_meta.append({"id": cid, "chunk_file": str(cpath)})

    meta_out.append({
        "pmid": p.get("pmid"),
        "doi": p.get("doi"),
        "pmcid": p.get("pmcid"),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "estimated_cost_usd": round(cost,6),
        "chunks": chunk_meta
    })

OUT_PATH.write_text(json.dumps(meta_out, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"✅ Stage C abgeschlossen – {len(meta_out)} Paper verarbeitet")
print(f"📦 Chunks gespeichert unter: {CHUNK_DIR}")
print(f"📜 Metadaten: {OUT_PATH}")
print(f"💰 Geschätzte Gesamtkosten: ${total_cost:.4f}")
