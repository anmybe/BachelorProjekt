# ============================================
# Stage C – Overlap-Split + Semantic Chunking (Gemini, seriell, JSON pro Paper)
# ============================================

import json
import re
import time
import datetime
from pathlib import Path
from tqdm import tqdm
from google import genai
from google.genai.errors import APIError
from dotenv import load_dotenv
import os

# --- .env laden, um API-Schlüssel zu erhalten ---
load_dotenv()


# === EINSTELLUNGEN ===
BASE_DIR = Path.home() / "BachelorProjekt" / "paper_pipeline" / "intermediary_results"
INPUT_FILE = BASE_DIR / "stageB_metadata3.json"
TEXT_DIR = BASE_DIR / "fulltext" / "fulltext_raw3"
CHUNK_DIR = BASE_DIR / "chunks_gemini_semantic_serial3"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = BASE_DIR / "stageC_metadata_gemini_semantic_serial3.json"
LOG_PATH = BASE_DIR / "gemini_request_log3.txt"

# --- GEMINI KONFIGURATION ---

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# WICHTIG: Flash 2.5 für Geschwindigkeit, Pro 2.5 als Fallback für bessere Performance bei komplexen Aufgaben
MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-flash"
client = genai.Client(api_key=GEMINI_API_KEY)

# Kosten (Geschätzt pro 1k Tokens, Stand Q4 2025)
# Gemini 2.5 Flash (Input/Output)
COST_PER_1K_IN_FLASH = 0.00035 
COST_PER_1K_OUT_FLASH = 0.0007
# Gemini 2.5 Pro (Input/Output)
COST_PER_1K_IN_PRO = 0.0035
COST_PER_1K_OUT_PRO = 0.007
# -------------------------------

MAX_CHARS = 15000 # Erhöht für Gemini Flash 2.5
OVERLAP = 1000
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
    """Zerteilt Text in überlappende Segmente (einfache Zeichenbasis)."""
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


def get_cost(model_name: str, in_toks: int, out_toks: int) -> float:
    """Berechnet die Kosten basierend auf dem Modell und Token-Verbrauch."""
    model_name = model_name.lower()
    if "flash" in model_name:
        cost = (in_toks / 1000 * COST_PER_1K_IN_FLASH) + (out_toks / 1000 * COST_PER_1K_OUT_FLASH)
    elif "pro" in model_name:
        cost = (in_toks / 1000 * COST_PER_1K_IN_PRO) + (out_toks / 1000 * COST_PER_1K_OUT_PRO)
    else:
        # Fallback für unbekannte Modelle
        cost = (in_toks + out_toks) / 1000 * 0.005
    return cost


def gemini_chunk(segment: str, paper_id: str, segment_id: int, current_model: str = MODEL):
    """Ruft Gemini auf, um Text in sinnvolle Abschnitte zu teilen."""
    
    # Prompt mit SEMANTISCHER ANFORDERUNG
    prompt_template = """
You are an expert biomedical text segmenter. You MUST follow every rule EXACTLY as written.
No creativity, no improvements, no optimization. ZERO EXCEPTIONS.

Your task:
Split the input text into highly coherent, semantically-focused CHUNKS of 300–600 words.

Semantic Rules (MUST FOLLOW):
A. Cohesion: Chunks MUST group paragraphs that discuss the same specific sub-topic (e.g., all discussion of IGF-1 findings, or all description of training protocols).
B. Hierarchy: If possible, do not split across major document sections (e.g., Introduction, Methods, Results, Discussion).
C. Size Priority: Semantic cohesion is more important than size. If keeping a topic coherent slightly exceeds 600 words, prioritize the coherence.

Technical Rules (MUST FOLLOW):
1. NEVER rewrite, modify, shorten, expand, or reorder any text.
2. NEVER split inside a sentence.
3. NEVER split inside a paragraph. Splitting ONLY allowed BETWEEN paragraphs.
4. If a paragraph exceeds 600 words, it becomes its own chunk.
5. Overlap rule:
   - Each chunk (except chunk 1) MUST start with the LAST FULL SENTENCE of the previous chunk.
   - Overlap MUST be EXACTLY ONE COMPLETE SENTENCE.
6. NEVER duplicate paragraphs.
7. NEVER add new text.
8. Chunk IDs MUST be strictly increasing: 1, 2, 3, ... (Note: This is corrected by the Python script after all segments are processed).
9. If input < 600 words → return exactly one chunk.
10. If input text ends mid-sentence because of truncation, DO NOT attempt to fix it.

Output MUST be valid JSON ONLY:
{
  "chunks": [
    {"id": 1, "text": "..."},
    {"id": 2, "text": "..."}
  ]
}

Input text:
<<<TEXT>>>
"""
    prompt = prompt_template.replace("<<<TEXT>>>", segment)
    model_name = current_model

    for attempt in range(3):
        try:
            print(f"\n🟢 [{paper_id}–Seg {segment_id}] Modell: {model_name}, Zeichen: {len(segment)}")
            start = time.time()
            
            # Gemini API Aufruf
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config={"response_mime_type": "application/json"},
                # Setze das Timeout
                request_options={"timeout": 60.0} 
            )
            
            duration = time.time() - start
            log_request(model_name)
            print(f"⏱️ Antwortdauer: {duration:.1f}s")
            
            # Tokenverbrauch und Kosten
            usage = response.usage_metadata
            in_toks = usage.prompt_token_count
            out_toks = usage.candidates_token_count
            cost = get_cost(model_name, in_toks, out_toks)

            output_text = response.text
            parsed = safe_parse_json(output_text)
            
            if not parsed:
                print("⚠️ JSON-Parsing fehlgeschlagen – Rohchunk verwendet.")
                return [{"id": 1, "text": segment.strip()}], in_toks, out_toks, cost

            chunks = parsed.get("chunks", parsed)
            print(f"✅ {len(chunks)} Chunks erkannt.")
            time.sleep(1) # Kurze Pause zwischen API-Aufrufen
            return chunks, in_toks, out_toks, cost

        except APIError as e:
            msg = str(e).lower()
            print(f"⚠️ Versuch {attempt+1} fehlgeschlagen (APIError): {e}")

            # Behandlung von Rate Limit / Timeout
            if "rate limit" in msg or "429" in msg or "quota" in msg:
                print(f"🚧 Rate Limit/Quota erreicht – Wechsel zu {FALLBACK_MODEL}")
                # Setze Modell für nächsten Versuch
                current_model = FALLBACK_MODEL
                model_name = FALLBACK_MODEL
                wait_time = 30 * (2 ** attempt)
                print(f"⏳ Warte {wait_time}s...")
                time.sleep(wait_time)
                continue

            if "timeout" in msg or "504" in msg or "500" in msg:
                print("⏳ Timeout/Serverfehler – Segmentgröße halbiert und neuer Versuch ...")
                # Reduziere die Segmentgröße, falls das Modell damit Probleme hat
                segment = segment[:int(len(segment) * 0.75)] # Reduzierung auf 75%
                wait_time = 10 * (2 ** attempt)
                print(f"⏳ Warte {wait_time}s...")
                time.sleep(wait_time)
                continue

            # Standard-Backoff für andere Fehler
            time.sleep(5 * (2 ** attempt))

        except Exception as e:
            print(f"⚠️ Versuch {attempt+1} fehlgeschlagen (Unbekannter Fehler): {e}")
            time.sleep(5 * (2 ** attempt))


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

    # Korrekte Pfadkonstruktion (geht davon aus, dass die pmcid auch der Dateiname ist)
    text_filename = f"{paper_id}.txt"
    path = TEXT_DIR / text_filename 
    
    if not path.exists():
        print(f"⚠️ Datei fehlt: {path}")
        continue

    text = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not text:
        continue

    segments = split_with_overlap(text)
    print(f"➡️ {len(segments)} Segmente à ~{MAX_CHARS} Zeichen, Overlap {OVERLAP}.")

    all_chunks = []
    # Setze das Modell für jedes neue Paper auf das Hauptmodell zurück
    current_model_for_chunking = MODEL 

    for i, seg in enumerate(tqdm(segments, desc=f"{paper_id} Segmente"), start=1):
        chunks, in_toks, out_toks, cost = gemini_chunk(seg, paper_id, i, current_model_for_chunking)
        total_in += in_toks
        total_out += out_toks
        total_cost += cost
        all_chunks.extend(chunks)

        # Logik, um das Hauptmodell beizubehalten, es sei denn, der Fallback wurde verwendet
        # (Dies ist hier weniger kritisch, da Gemini eine robustere Quota-Behandlung hat)

    # KORREKTUR DER CHUNK-ID-NUMMERIERUNG FÜR DAS GESAMTE PAPER
    if all_chunks:
        current_id = 1
        for chunk in all_chunks:
            chunk['id'] = current_id
            current_id += 1
        print(f"✅ Chunk-IDs korrigiert, {current_id - 1} fortlaufende Chunks erstellt.")


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