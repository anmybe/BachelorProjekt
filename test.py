# ============================================
# Stage C – XML → Text-Chunks + Metadaten (robust)
# ============================================

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from tqdm import tqdm

# ==== EINSTELLUNGEN ====
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_FILE = BASE_DIR / "stageB_metadata.json"
XML_DIR = BASE_DIR / "xml_raw"
CHUNK_DIR = BASE_DIR / "chunks"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = BASE_DIR / "stageC_metadata.json"

# ==== HILFSFUNKTIONEN ====
def clean_text(text: str) -> str:
    """Einfaches Preprocessing: Leerzeichen normalisieren, Referenzen entfernen"""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[[0-9,\- ]+\]', '', text)
    return text.strip()

def extract_sections(xml_text: str) -> dict:
    """Extrahiert strukturierte Abschnitte aus JATS-XML mit Keyword-Heuristik und Body-Fallback."""
    soup = BeautifulSoup(xml_text, "xml")

    def clean(txt):
        return re.sub(r'\s+', ' ', txt).strip()

    sections = {
        "title": "",
        "abstract": "",
        "introduction": "",
        "methods": "",
        "results": "",
        "discussion": "",
        "full_body": "",
    }

    # Titel
    title_tag = soup.find("article-title")
    if title_tag:
        sections["title"] = clean(title_tag.get_text())

    # Abstract
    abstract_tag = soup.find("abstract")
    if abstract_tag:
        sections["abstract"] = clean(abstract_tag.get_text())

    # Keywords zur Erkennung der Hauptabschnitte
    methods_kw = ["method", "material", "design", "procedure", "participant", "data collection", "analysis"]
    results_kw = ["result", "finding", "observation", "outcome"]
    discussion_kw = ["discussion", "conclusion", "interpretation", "implication", "summary"]
    intro_kw = ["introduction", "background", "rationale"]

    # Alle <sec>-Tags durchlaufen
    for sec in soup.find_all("sec"):
        sec_title_tag = sec.find("title")
        sec_title = sec_title_tag.get_text().lower().strip() if sec_title_tag else ""
        sec_type = (sec.get("sec-type") or "").lower()
        content = clean(sec.get_text())

        # Zuordnung nach Titel oder sec-type
        if any(k in sec_title for k in intro_kw):
            sections["introduction"] += " " + content
        elif any(k in sec_title for k in methods_kw) or "method" in sec_type:
            sections["methods"] += " " + content
        elif any(k in sec_title for k in results_kw) or "result" in sec_type:
            sections["results"] += " " + content
        elif any(k in sec_title for k in discussion_kw) or any(k in sec_type for k in ["discussion", "conclusion"]):
            sections["discussion"] += " " + content

    # === BODY-FALLBACK ===
    body = soup.find("body")
    if body:
        # Unerwünschte Teile entfernen
        for tag in body.find_all([
            "ref-list", "ack", "funding-group", "conflict", "supplementary-material",
            "data-availability", "author-contributions", "app-group"
        ]):
            tag.decompose()

        sections["full_body"] = clean(body.get_text())

    # Endreinigung
    for key in sections:
        sections[key] = clean_text(sections[key])

    return sections


# ==== PIPELINE AUSFÜHRUNG ====
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    papers = json.load(f)

meta_out = []
for p in tqdm(papers):
    xml_path = Path(p["xml_file"])
    if not xml_path.exists():
        continue

    xml_text = xml_path.read_text(encoding="utf-8", errors="ignore")
    sections = extract_sections(xml_text)

    paper_id = xml_path.stem
    chunks = []

    # Speichere nur befüllte Abschnitte
    for name, content in sections.items():
        if not content:
            continue
        chunk_path = CHUNK_DIR / f"{paper_id}_{name}.txt"
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(content)
        chunks.append({"section": name, "chunk_file": str(chunk_path)})

    meta_out.append({
        "pmid": p.get("pmid"),
        "doi": p.get("doi"),
        "pmcid": p.get("pmcid"),
        "chunks": chunks
    })

# ==== SPEICHERN ====
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(meta_out, f, indent=2, ensure_ascii=False)

print(f"✅ Stage C abgeschlossen – {len(meta_out)} Papers verarbeitet")
print(f"📦 Chunks gespeichert unter: {CHUNK_DIR}")
print(f"📜 Metadaten: {OUT_PATH}")
