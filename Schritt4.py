import json
import os
from collections import defaultdict
from typing import Dict, Any, List, Optional

# --- CONFIGURATION (Laden aus der Umgebung) ---
# Laden der Ordnernamen aus der .env Datei
from dotenv import load_dotenv
load_dotenv()

# Der Input-Ordner, der die Original-Phase-1-Analysen enthaelt (z.B. semantic_serial_results3)
PHASE1_INPUT_FOLDER = "semantic_serial_results_threads_neues_schema"
# Die Input-Datei von Phase 3 (mit standardisierten Namen)
PHASE3_INPUT_FILE = "standardized_biomarkers3.json"
# Die finale Output-Datei
OUTPUT_FILE = "final_biomarker_details_aggregated.json"

# --- CORE LOGIC ---

def load_index_file(filepath: str) -> List[Dict[str, Any]]:
    """Lädt die standardisierte Biomarker-Liste aus Phase 3."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Index-Datei '{filepath}' nicht gefunden. Bitte Phase 3 zuerst ausführen.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Index-Datei '{filepath}' enthaelt ungueltiges JSON.")
        return []

def load_document_cache(source_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Laedt alle Phase-1-Dokumente in einen Cache zur schnellen Suche.
    Schluessel ist die document_source_id.
    """
    cache = {}
    if not os.path.isdir(source_dir):
        print(f"Error: Quellordner '{source_dir}' (Phase 1 Ergebnisse) nicht gefunden.")
        return cache
        
    for filename in os.listdir(source_dir):
        if filename.endswith('_analysis.json'):
            doc_id = filename.split('_analysis.json')[0]
            file_path = os.path.join(source_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Die Phase-1-Dateien enthalten ein Array mit genau einem Analyse-Objekt
                    data = json.load(f)[0] 
                    cache[doc_id] = data
            except (json.JSONDecodeError, IndexError, AttributeError):
                print(f"Warning: Dokument {filename} konnte nicht in den Cache geladen werden.")
                
    print(f"Dokumenten-Cache geladen: {len(cache)} Dokumente verfügbar.")
    return cache

def aggregate_biomarker_details(standardized_index: List[Dict[str, Any]], doc_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregiert alle Detail-Informationen (extracted_data) unter dem standardisierten Namen.
    """
    final_aggregated_data = []

    for standard_entry in standardized_index:
        standard_name = standard_entry['standard_name']
        source_entries = standard_entry['source_entries']
        
        aggregated_findings = []
        
        # 1. Sammle alle Original-Fundstellen (Paare aus Originalname und ID)
        for entry in source_entries:
            original_name = entry['original_name']
            doc_id = entry['document_source_id']
            
            source_document = doc_cache.get(doc_id)
            if not source_document:
                # Dokument nicht im Cache (z.B. Datei fehlt)
                continue

            extracted_data = source_document.get('extracted_data', {})
            
            # --- WICHTIGE LOGIK: Finden des spezifischen Eintrags ---
            
            # Die detaillierten Effekte (core_effect_and_quantification) muessen nach dem
            # original_name des Biomarkers gefiltert werden, um den Kontext zu sichern.
            core_effects = extracted_data.get('core_effect_and_quantification', [])
            
            # Finde alle Core Effects, die dem Originalnamen entsprechen
            matching_core_effects = [
                effect for effect in core_effects 
                if effect.get('biomarker_name', '').strip() == original_name.strip()
            ]

            # Füge den Fund zum Aggregat hinzu
            aggregated_findings.append({
                "original_name": original_name,
                "document_source_id": doc_id,
                # Fuege die gesamten Extraktionsdetails des DOKUMENTS hinzu. 
                # (Da die anderen Felder (Mechanism, Implication) Dokument-weit sind, 
                # fuegen wir den vollen Block fuer diesen Kontext hinzu)
                "document_context_data": extracted_data,
                "matched_core_effects": matching_core_effects 
            })


        # 2. Bauen des finalen Eintrags
        if aggregated_findings:
            final_aggregated_data.append({
                "standard_name": standard_name,
                "total_unique_sources": len(set(f['document_source_id'] for f in aggregated_findings)),
                # Behaelt die detaillierten Findings, die nun den vollen Dokument-Kontext enthalten.
                "aggregated_source_findings": aggregated_findings 
            })
            
    return final_aggregated_data


def main():
    print("--- PHASE 4: DETAIL-AGGREGATION UND PROVENIENZ ---")
    
    # 1. Index-Datei laden (Output von Phase 3)
    standardized_index = load_index_file(PHASE3_INPUT_FILE)
    if not standardized_index:
        print("Pipeline gestoppt: Konnte Index-Datei nicht laden.")
        return

    # 2. Original-Dokumente laden (Cache der Phase-1-Ergebnisse)
    doc_cache = load_document_cache(PHASE1_INPUT_FOLDER)
    if not doc_cache:
        print("Pipeline gestoppt: Konnte keine Quelldokumente laden.")
        # Erlaubt, mit der Warnung weiterzumachen, falls der Cache leer ist, aber der Index nicht.
        # return 
    
    # 3. Aggregation durchfuehren
    print(f"Starte Aggregation von {len(standardized_index)} standardisierten Biomarkern...")
    final_data = aggregate_biomarker_details(standardized_index, doc_cache)
    
    # 4. Speichern der konsolidierten Ergebnisse
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_data, f, indent=2)
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Detail-Aggregation abgeschlossen.")
    print(f"  Gesamtzahl der eindeutigen Biomarker (Standardisiert): {len(final_data)}")
    print(f"  Ergebnisse gespeichert in '{OUTPUT_FILE}'")
    print("=========================================================\n")


if __name__ == "__main__":
    main()