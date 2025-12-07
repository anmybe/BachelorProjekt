# ============================================
# Stage A – Query → PMIDs → DOIs → PMCIDs
# ============================================

import time
import json
import requests
import xml.etree.ElementTree as ET
from tqdm import tqdm
from pathlib import Path
from dotenv import load_dotenv

# ==== EINSTELLUNGEN ====
SEARCH_TERM = '(measur* OR determin* OR monitor* OR quantitativ*) AND health* AND blood AND humans[MeSH Terms] AND ("sports medicine" OR "regenerative medicine" OR "athletic performance" OR "exercise physiology" OR training OR athletics OR "sports injury" OR "sports nutrition" OR "musculoskeletal health") AND (biomarker* OR "blood analysis" OR "blood testing" OR "blood parameters") AND (overtraining OR"muscle damage" OR inflamation OR regenerat* OR recovery OR "anabolic response")'
MAX_RESULTS = 1000
SAVE_DIR = Path.home() / "BachelorProjekt" / "paper_pipeline" / "intermediary_results"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = SAVE_DIR / "stageA_metadata3.json"

# ==== 1️⃣ PubMed Query → PMIDs ====
def get_pubmed_ids(query, retmax=100):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": retmax}
    r = requests.get(url, params=params)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return [id_tag.text for id_tag in root.findall(".//Id")]

pmids = get_pubmed_ids(SEARCH_TERM, retmax=MAX_RESULTS)
print(f"✅ {len(pmids)} PMIDs gefunden")

# ==== 2️⃣ PMIDs → DOIs ====
def get_dois(pmids):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    all_dois = []
    for i in tqdm(range(0, len(pmids), 100)):
        batch = pmids[i:i+100]
        params = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
        r = requests.get(url, params=params)
        r.raise_for_status()
        xml = ET.fromstring(r.text)
        for art in xml.findall(".//PubmedArticle"):
            pmid = art.findtext(".//PMID")
            doi = art.findtext(".//ArticleId[@IdType='doi']")
            if doi:
                all_dois.append({"pmid": pmid, "doi": doi})
        time.sleep(0.3)
    return all_dois

papers = get_dois(pmids)
print(f"✅ {len(papers)} DOIs gefunden")

# ==== 3️⃣ DOI → PMCID (Europe PMC) ====
def get_pmcid(doi):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": f"DOI:{doi}", "format": "json"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return None
        return results[0].get("pmcid")
    except Exception:
        return None

for p in tqdm(papers):
    pmcid = get_pmcid(p["doi"])
    p["pmcid"] = pmcid
    time.sleep(0.2)

# ==== 4️⃣ Ergebnisse speichern ====
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

found = len([p for p in papers if p["pmcid"]])
print(f"✅ {found} PMCIDs gefunden und gespeichert → {OUT_PATH}")
