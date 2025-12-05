# ============================================
# Stage B – PMCIDs → Volltext (bereinigt) herunterladen
# ============================================

import time
import json
import requests
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup

# ==== EINSTELLUNGEN ====
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_FILE = BASE_DIR / "stageA_metadata3.json"
TXT_DIR = BASE_DIR / "fulltext_raw3"
TXT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = BASE_DIR / "stageB_metadata3.json"

# ==== PMCID → Volltext extrahieren ====
def get_fulltext(pmcid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "xml")
        for tag in soup(["ref-list", "table-wrap", "fig", "graphic"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return text
    except Exception:
        return None

# ==== Pipeline ====
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    papers = json.load(f)

downloaded, missing = 0, 0
meta_out = []

for p in tqdm(papers):
    pmcid = p.get("pmcid")
    if not pmcid:
        continue
    fulltext = get_fulltext(pmcid)
    if fulltext:
        out_file = TXT_DIR / f"{pmcid}.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(fulltext)
        downloaded += 1
        meta_out.append({
            "pmid": p["pmid"],
            "doi": p["doi"],
            "pmcid": pmcid,
            "text_file": str(out_file)
        })
    else:
        missing += 1
    time.sleep(0.2)

print(f"\n✅ {downloaded} Volltexte erfolgreich gespeichert, {missing} fehlgeschlagen.")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(meta_out, f, indent=2, ensure_ascii=False)
print(f"📦 Stage B abgeschlossen → {OUT_PATH}")
