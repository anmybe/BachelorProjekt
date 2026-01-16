# ============================================
# Stage C – Overlap-Split + Semantic Chunking (Gemini, seriell, JSON pro Paper)
# ============================================

import json
import re
import time
import datetime
from pathlib import Path
from tqdm import tqdm
import google.generativeai as genai

# === EINSTELLUNGEN ===
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_FILE = BASE_DIR / "stageB_metadata3.json"
TEXT_DIR = BASE_DIR / "fulltext_raw3"
CHUNK_DIR = BASE_DIR / "chunks_gemini_semantic_serial3"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = BASE_DIR / "stageC_metadata_gemini_semantic_serial3.json"
LOG_PATH = BASE_DIR / "gemini_request_log3.txt"

API_KEY = "..."
MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-flash-lite"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)

MAX_CHARS = 20000
OVERLAP = 400
COST_PER_1K_TOKENS = 0.000125
REQUEST_COUNT = 0


# === HELFER ===
def log_request(model_name):
    """Schreibt jeden API-Aufruf ins Logfile."""
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{ts} | {model_name}\n")
    print(f"📈 Request #{REQUEST_COUNT} an {model_name}")


def clean_text(text: str) -> str:
    """Bereinigt Whitespaces."""
    return re.sub(r"\s+", " ", text).strip()


def split_with_overlap(text: str, window: int = MAX_CHARS, overlap: int = OVERLAP):
    """Zerteilt Text in überlappende Segmente."""
    segs, i = [], 0
    while i < len(text):
        segs.append(text[i:i + window])
        i += window - overlap
    return segs


def safe_parse_json(text: str):
    """Versucht, unsauberes JSON aus dem LLM-Output zu rekonstruieren."""
    text = text.strip().replace("```json", "").replace("```", "")
    match = re.search(r'\{[\s\S]*\}', text) or re.search(r'\[[\s\S]*\]', text)
    if not match:
        return None
    candidate = match.group(0)
    try:
        return json.loads(candidate)
    except Exception:
        candidate = re.sub(r'}\s*{', '}, {', candidate)
        try:
            return json.loads(candidate)
        except Exception:
            return None


def gemini_chunk(segment: str, paper_id: str, segment_id: int, model_name: str = MODEL):
    """Ruft Gemini auf, um Text in sinnvolle Abschnitte (1000–2000 Wörter) zu teilen."""
    global model
    prompt = f"""
You are an expert biomedical text segmenter.

Task:
Split the text into CHUNKS of 300–600 words that remain fully semantically coherent.
Use ONLY paragraph boundaries, never cut inside paragraphs.

Hard rules:
1. Never modify, paraphrase, reorder, or delete words.
2. Never cut in the middle of a sentence or a word.
3. Each chunk must contain COMPLETE paragraphs.
4. Chunk size target: 300–600 words. If a paragraph is long, it may form its own chunk.
5. Overlap rule:
   - Each chunk (except chunk 1) begins with the LAST FULL SENTENCE of the previous chunk.
   - The overlap must be EXACTLY that one sentence and nothing more.

6. Never add new text, explanations, or interpretations.
7. Output ONLY valid JSON in this form:
{
  "chunks": [
    {"id": 1, "text": "..."},
    {"id": 2, "text": "..."},
    {"id": 3, "text": "..."}
  ]
}

Text:
{segment}

{segment[:MAX_CHARS]}
"""

    for attempt in range(3):
        try:
            print(f"\n🟢 [{paper_id}–Seg {segment_id}] Modell: {model_name}, Zeichen: {len(segment)}")
            start = time.time()
            response = model.generate_content(prompt, request_options={"timeout": 480})
            duration = time.time() - start
            log_request(model_name)
            print(f"⏱️ Antwortdauer: {duration:.1f}s")

            # Tokenverbrauch
            usage = getattr(response, "usage_metadata", None)
            in_toks = getattr(usage, "prompt_token_count", 0)
            out_toks = getattr(usage, "candidates_token_count", 0)
            cost = (in_toks + out_toks) / 1000 * COST_PER_1K_TOKENS

            parsed = safe_parse_json(response.text)
            if not parsed:
                print("⚠️ JSON-Parsing fehlgeschlagen – Rohchunk verwendet.")
                return [{"id": 1, "text": segment.strip()}], in_toks, out_toks, cost

            chunks = parsed.get("chunks", parsed)
            print(f"✅ {len(chunks)} Chunks erkannt.")
            time.sleep(8)  # Free-tier Throttle
            return chunks, in_toks, out_toks, cost

        except Exception as e:
            msg = str(e)
            print(f"⚠️ Versuch {attempt+1} fehlgeschlagen: {msg}")

            if "429" in msg:
                print(f"🚧 Quota erreicht – Wechsel zu {FALLBACK_MODEL}")
                model = genai.GenerativeModel(FALLBACK_MODEL)
                model_name = FALLBACK_MODEL
                time.sleep(60)
                continue

            if "timeout" in msg.lower() or "504" in msg:
                print("⏳ Timeout – Segmentgröße halbiert und neuer Versuch ...")
                segment = segment[:int(len(segment) * 0.5)]
                time.sleep(10)
                continue

            time.sleep(5)

    print("💤 Alle Versuche fehlgeschlagen – Rohchunk zurückgegeben.")
    return [{"id": 1, "text": segment.strip()}], 0, 0, 0


# === PIPELINE ===
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    papers = json.load(f)

meta_out = []
total_in = total_out = total_cost = 0.0

for p in papers:
    paper_id = p.get("pmcid") or p.get("doi") or "unknown"
    print("\n" + "=" * 45)
    print(f"📘 Paper: {paper_id}")
    print("=" * 45)

    path = Path(p.get("text_file", ""))
    if not path.exists():
        print(f"⚠️ Datei fehlt: {path}")
        continue

    text = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not text:
        continue

    segments = split_with_overlap(text)
    print(f"➡️ {len(segments)} Segmente à ~{MAX_CHARS} Zeichen, Overlap {OVERLAP}.")

    all_chunks = []
    for i, seg in enumerate(tqdm(segments, desc=f"{paper_id} Segmente"), start=1):
        chunks, in_toks, out_toks, cost = gemini_chunk(seg, paper_id, i)
        total_in += in_toks
        total_out += out_toks
        total_cost += cost
        all_chunks.extend(chunks)

    # eine JSON-Datei pro Paper speichern
    paper_json_path = CHUNK_DIR / f"{paper_id}_chunks.json"
    with open(paper_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "pmid": p.get("pmid"),
            "doi": p.get("doi"),
            "pmcid": p.get("pmcid"),
            "chunks": all_chunks
        }, f, ensure_ascii=False, indent=2)

    meta_out.append({
        "pmid": p.get("pmid"),
        "doi": p.get("doi"),
        "pmcid": p.get("pmcid"),
        "chunk_file": str(paper_json_path)
    })

    print(f"✅ {paper_id}: {len(all_chunks)} Chunks gespeichert → {paper_json_path.name}")


# === SPEICHERN DER METADATEN ===
OUT_PATH.write_text(json.dumps(meta_out, indent=2, ensure_ascii=False), encoding="utf-8")

print("\n" + "=" * 60)
print(f"✅ Stage C abgeschlossen – {len(meta_out)} Paper verarbeitet")
print(f"📜 Metadaten-Datei: {OUT_PATH}")
print(f"💾 Log-Datei: {LOG_PATH}")
print(f"💰 Tokens: In {int(total_in):,}, Out {int(total_out):,}, Summe {int(total_in + total_out):,} (~${total_cost:.4f})")
print(f"📈 Gesamtanzahl API-Aufrufe: {REQUEST_COUNT}")
print("=" * 60)
