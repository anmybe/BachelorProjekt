# --------------------------------------------
# KI-gestützte PubMed-Pipeline: Query → Europe PMC TXT
# --------------------------------------------
# Schritte:
# 1. PubMed-Query  →  PMIDs
# 2. PMIDs         →  DOIs
# 3. DOIs          →  Europe PMC PMCID
# 4. PMCID         →  Volltext-XML  →  TXT-Datei
# --------------------------------------------

import os
import time
import json
import requests
import xml.etree.ElementTree as ET
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup

# ==== EINSTELLUNGEN ====
SEARCH_TERM = '(measur* OR determin* OR monitor* OR quantitativ*) AND health* AND blood AND humans[MeSH Terms] AND ("sports medicine" OR "regenerative medicine" OR "athletic performance" OR "exercise physiology" OR training OR athletics OR "sports injury" OR "sports nutrition" OR "musculoskeletal health") AND (biomarker* OR "blood analysis" OR "blood testing" OR "blood parameters")'
MAX_RESULTS = 10000            # API-Limit ggf. erhöhen
SAVE_DIR = Path.home() / "Programming" / "BP" / "pmc_texts"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# ==== 1. PubMed Query -> PMIDs ====
def get_pubmed_ids(query, retmax=100):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": retmax}
    r = requests.get(url, params=params)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return [id_tag.text for id_tag in root.findall(".//Id")]

pmids = get_pubmed_ids(SEARCH_TERM, retmax=MAX_RESULTS)
print(f"✅ {len(pmids)} PMIDs gefunden")

# ==== 2. PMIDs -> DOIs ====
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

# ==== 3. DOI -> PMCID bei Europe PMC ====
def get_pmcid(doi):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": f"DOI:{doi}", "format": "json"}
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return None
        return results[0].get("pmcid")
    except Exception:
        return None

# ==== 4. PMCID -> Volltext-XML -> Text extrahieren ====
def get_fulltext(pmcid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "xml")
    for tag in soup(["ref-list", "table-wrap", "fig", "graphic"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text

# ==== 5. Pipeline ausführen ====
downloaded = 0
no_text = 0
metadata = []

for p in tqdm(papers):
    doi = p["doi"]
    pmcid = get_pmcid(doi)
    if not pmcid:
        no_text += 1
        continue
    text = get_fulltext(pmcid)
    if text:
        out_path = SAVE_DIR / f"{doi.replace('/', '_')}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        downloaded += 1
        metadata.append({"pmid": p["pmid"], "doi": doi, "pmcid": pmcid, "txt_file": str(out_path)})
    else:
        no_text += 1
    time.sleep(0.5)

print(f"\n✅ {downloaded} Volltexte erfolgreich gespeichert, {no_text} ohne Volltext.")
with open(SAVE_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"📦 Metadaten gespeichert: {SAVE_DIR / 'metadata.json'}")
