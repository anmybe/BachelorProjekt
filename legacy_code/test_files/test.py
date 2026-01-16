# ============================================
# Stage C – Testmodus für EIN Paper (Claude 3.5 Sonnet)
# ============================================

import json
import re
import time
import datetime
from pathlib import Path
from tqdm import tqdm
from anthropic import Anthropic
# APIStatusError wurde auf Wunsch entfernt.
# from anthropic.lib.core import APIStatusError 

# === EINSTELLUNGEN ===
BASE_DIR = Path.home() / "BachelorProjekt"

# Paper auswählen
TEST_PMCID = "PMC12616881"
TEST_FILENAME = f"{TEST_PMCID}.txt"

TEXT_PATH = BASE_DIR / "fulltext_raw3" / TEST_FILENAME
CHUNK_DIR = BASE_DIR / "chunks_test_single_claude"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = CHUNK_DIR / f"{TEST_PMCID}_chunks.json"
LOG_PATH = CHUNK_DIR / "claude_test_log.txt"

# Claude API-Key eintragen
# HINWEIS: Key-Maskierung für die Ausgabe beibehalten
CLAUDE_API_KEY = "..."

client = Anthropic(api_key=CLAUDE_API_KEY)

# Fenstergröße: Claude stabil bei 6000–8000 Zeichen
MAX_CHARS = 7000
OVERLAP = 600
REQUEST_COUNT = 0


# ============================================
# HELPER
# ============================================

def log_request():
    """Logfile für jeden API-Aufruf."""
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        # Modellbezeichnung im Log auf das funktionierende Opus umgestellt
        f.write(f"{ts} | Claude Opus 4.5\n")
    print(f"📈 Request #{REQUEST_COUNT} an Claude")


def clean_text(text: str) -> str:
    """Simplify whitespace."""
    # Reduziert Whitespace auf ein einzelnes Leerzeichen, wichtig für sauberes Splitting
    return re.sub(r"\s+", " ", text).strip()


def split_with_overlap(text: str, window: int = MAX_CHARS, overlap: int = OVERLAP):
    """
    Zerteilt Text in überlappende Segmente (einfache Zeichenbasis).
    Die komplexe, linguistische Logik wurde entfernt, um Python-Performance-Probleme
    (zu langes Laden) zu vermeiden. Die Abgrenzung am Satzende muss nun vom LLM
    innerhalb des Segments vorgenommen werden.
    """
    segs, i = [], 0
    while i < len(text):
        segs.append(text[i:i + window])
        i += window - overlap
    return segs


def safe_parse_json(text: str):
    """Extrahiert JSON aus Claude-Output."""
    text = text.strip()
    text = text.replace("```json", "").replace("```", "")

    match = re.search(r'\{[\s\S]*\}', text) or re.search(r'\[[\s\S]*\]', text)
    if not match:
        return None

    candidate = match.group(0)
    try:
        return json.loads(candidate)
    except Exception:
        # Versuch, Listen zu reparieren, falls das LLM mehrere Objekte liefert
        candidate = re.sub(r'}\s*{', '}, {', candidate)
        try:
            return json.loads(candidate)
        except Exception:
            return None


# ============================================
# CLAUDE CHUNKING CALL
# ============================================

def claude_chunk(segment: str, paper_id: str, segment_id: int):
    """Chunking mit Claude 3.5 Sonnet, f-string sicher."""

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
    # Modell auf das funktionierende Opus umgestellt
    MODEL_ID = "claude-opus-4-5"
    
    # 3 Versuche mit exponentiellem Backoff bei Rate Limits
    for attempt in range(3):
        try:
            print(f"\n🟢 [{paper_id}–Seg {segment_id}] Claude, Zeichen: {len(segment)}, Modell: {MODEL_ID}")
            start = time.time()
            
            response = client.messages.create(
                model=MODEL_ID,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
                timeout=60.0  # TIMEOUT AUF 60 SEKUNDEN ERHÖHT
            )
            
            duration = time.time() - start
            log_request()

            output_text = response.content[0].text
            print(f"⏱️ Antwortdauer: {duration:.1f}s")

            parsed = safe_parse_json(output_text)
            if not parsed:
                print("⚠️ JSON-Parsing fehlgeschlagen – Rohchunk verwendet.")
                # Für den Notfall, falls JSON komplett fehlschlägt, aber keine API-Fehler vorliegen
                return [{"id": 1, "text": segment.strip()}]

            chunks = parsed.get("chunks", parsed)
            print(f"✅ {len(chunks)} Chunks erkannt.")
            return chunks

        except Exception as e:
            # WIEDERHERGESTELLT ZUR GENERALISIERTEN FEHLERBEHANDLUNG
            error_message = str(e).lower()
            print(f"⚠️ Versuch {attempt+1} fehlgeschlagen (Allgemeiner Fehler): {e}")
            
            # Bei Timeout/504 (Verarbeitungsproblem) oder 429 (Rate Limit) warten wir länger
            if "timeout" in error_message or "504" in error_message or "429" in error_message or "rate limit" in error_message:
                wait_time = 30 * (2 ** attempt)  # Startet bei 30s
            else:
                wait_time = 5 * (2 ** attempt)
                
            print(f"⏳ Warte {wait_time}s...")
            time.sleep(wait_time)

    print("💤 Alle Versuche fehlgeschlagen – Rohchunk zurückgegeben.")
    return [{"id": 1, "text": segment.strip()}]



# ============================================
# TESTPIPELINE
# ============================================

print("\n" + "=" * 45)
print(f"📘 TEST: Paper {TEST_PMCID}")
print("=" * 45)

if not TEXT_PATH.exists():
    # Dieser Fehler wird nur ausgelöst, wenn die Textdatei auf Ihrem System fehlt
    raise FileNotFoundError(f"Textdatei fehlt: {TEXT_PATH}. Stellen Sie sicher, dass sie unter {TEXT_PATH} existiert.")

raw_text = clean_text(TEXT_PATH.read_text(encoding="utf-8", errors="ignore"))
segments = split_with_overlap(raw_text) # Nutzt jetzt die einfache, zeichenbasierte Funktion

print(f"➡️ {len(segments)} Segmente (~{MAX_CHARS} Zeichen, Overlap {OVERLAP})")

all_chunks = []

for i, seg in enumerate(tqdm(segments, desc="Chunking"), start=1):
    chunks = claude_chunk(seg, TEST_PMCID, i)
    all_chunks.extend(chunks)

# KORREKTUR DER CHUNK-ID-NUMMERIERUNG
if all_chunks:
    current_id = 1
    for chunk in all_chunks:
        chunk['id'] = current_id
        current_id += 1
    print(f"✅ Chunk-IDs korrigiert, {current_id - 1} fortlaufende Chunks erstellt.")


# speichern
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "pmcid": TEST_PMCID,
        "chunks": all_chunks
    }, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print(f"✅ Test abgeschlossen – {len(all_chunks)} Chunks gespeichert")
print(f"💾 Output: {OUT_PATH}")
print(f"📜 Log: {LOG_PATH}")
print("=" * 60)