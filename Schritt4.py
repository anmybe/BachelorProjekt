import json
import os
import re
from collections import defaultdict
from typing import Dict, Any, List, Optional

# --- CONFIGURATION (Laden aus der Umgebung) ---
# Laden der Ordnernamen aus der .env Datei
from dotenv import load_dotenv
load_dotenv()

# Der Input-Ordner, der die Original-Phase-1-Analysen enthaelt (z.B. semantic_serial_results3)
PHASE1_INPUT_FOLDER = "semantic_serial_results_threads_final"
# Die Input-Datei von Phase 3 (mit standardisierten Namen)
PHASE3_INPUT_FILE = "ki(step3)_standardized_biomarkers_final.json"
# Die finale Output-Datei
OUTPUT_FILE = "result_step4.json"

# --- HELPER FUNCTION: NAME NORMALIZATION ---

def normalize_name_for_comparison(name: str) -> str:
    """Konvertiert den Namen in Kleinbuchstaben und entfernt ALLE 
    überflüssigen Whitespace-Zeichen (inkl. \n, \t, \r, \b) 
    für den robusten Vergleich."""
    # Wird für das interne Matching verwendet.
    # Dies ist der entscheidende Fix für die Sonderzeichen/Whitespace-Probleme
    cleaned_name = re.sub(r'\s+', '', name) 
    return cleaned_name.lower()

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
            # doc_id ist der Teil vor "_analysis.json"
            doc_id = filename.replace('_analysis.json', '') 
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

def extract_and_consolidate_details(standard_name: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Diese Funktion dient der manuellen/regelbasierten Synthese der Biomarker-Details.
    """
    
    # PLACEEHOLDER Logic (Beibehalten, da keine KI verwendet werden soll)
    # Beachte: Der standard_name sollte hier bereits sauber sein, da er aus Phase 3 kommt.
    if len(findings) == 1:
        return {
            "overall_biomarker_summary": f"Manuelle Synthese: {standard_name} wurde in {findings[0]['document_source_id']} gefunden. Die tatsächliche Zusammenfassung muss manuell hinzugefügt werden.",
            "mechanisms_consensus": "Manuelle Synthese: Hier wuerde die konsolidierte Mechanismus-Zusammenfassung stehen.",
            "reliability_consensus": "Manuelle Synthese: Hier wuerde die konsolidierte Zuverlaessigkeits-Zusammenfassung stehen."
        }
    
    return {
        "overall_biomarker_summary": f"Automatischer Platzhalter fuer {standard_name}: Gefunden in {len(findings)} Quellen. Manuelle Synthese erforderlich.",
        "mechanisms_consensus": f"Details zu den Mechanismen sind in den 'aggregated_source_findings_DEBUG' enthalten.",
        "reliability_consensus": "Manuelle Aggregation der Zuverlaessigkeit ueber mehrere Studien noetig."
    }


def aggregate_biomarker_details(standardized_index: List[Dict[str, Any]], doc_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregiert alle Detail-Informationen (analyzed_biomarkers) unter dem standardisierten Namen
    und fuegt die Summary-Felder hinzu.
    """
    final_aggregated_data = []
    total_matched_findings = 0 # Zaehler fuer Debugging

    for standard_entry in standardized_index:
        standard_name = standard_entry['standard_name']
        source_entries = standard_entry['source_entries']
        
        aggregated_findings = []
        unique_finding_keys: Set[Tuple[str, str]] = set()

        for entry in source_entries:
            original_name = entry['original_name']
            doc_id = entry['document_source_id']
            
            key = (original_name, doc_id)
            if key in unique_finding_keys:
                continue
            unique_finding_keys.add(key)
            
            source_document = doc_cache.get(doc_id)
            if not source_document:
                continue

            extracted_data = source_document.get('extracted_data', {})
            
            # NEU: Normalisiere den Originalnamen FÜR DEN VERGLEICH
            normalized_original_name = normalize_name_for_comparison(original_name)
            
            # Wir suchen im Array 'analyzed_biomarkers'
            analyzed_biomarkers = extracted_data.get('analyzed_biomarkers', [])
            
            # Finde ALLE Biomarker-Details, die dem Originalnamen entsprechen
            matching_biomarker_details = [
                detail for detail in analyzed_biomarkers 
                # HIER DER FIX: Normalisierter Vergleich
                if normalize_name_for_comparison(detail.get('biomarker_name', '')) == normalized_original_name
            ]

            if matching_biomarker_details:
                total_matched_findings += 1 # Debugging-Zaehler erhoehen
                
                # Füge den Fund zum Aggregat hinzu
                aggregated_findings.append({
                    "original_name": original_name,
                    "document_source_id": doc_id,
                    "document_context_data": {
                        "document_summary": extracted_data.get('document_summary'),
                        "treatment_details": extracted_data.get('treatment_details'),
                    },
                    "matched_biomarker_details": matching_biomarker_details 
                })


        # 2. Bauen des finalen Eintrags
        if aggregated_findings:
            
            # Erstelle die Summary-Felder
            biomarker_summary = extract_and_consolidate_details(standard_name, aggregated_findings)
            
            final_aggregated_data.append({
                "standard_name": standard_name,
                "source_entries": source_entries, 
                "biomarker_summary": biomarker_summary,
                "metadata": {
                    "total_documents_contributed": len(set(f['document_source_id'] for f in aggregated_findings)),
                    "api_calls_for_synthesis": 0 
                },
                "aggregated_source_findings_DEBUG": aggregated_findings 
            })
            
    print(f"DEBUG: Gesamtanzahl der erfolgreich gematchten Originalnamen: {total_matched_findings}")
    return final_aggregated_data


def main():
    print("--- PHASE 4: DETAIL-AGGREGATION UND SYNTHESE-VORBEREITUNG (Pure Python) ---")
    
    # 1. Index-Datei laden (Output von Phase 3)
    standardized_index = load_index_file(PHASE3_INPUT_FILE)
    if not standardized_index:
        print("Pipeline gestoppt: Konnte Index-Datei nicht laden.")
        return

    # 2. Original-Dokumente laden (Cache der Phase-1-Ergebnisse)
    doc_cache = load_document_cache(PHASE1_INPUT_FOLDER)
    if not doc_cache:
        print("Pipeline gestoppt: Konnte keine Quelldokumente laden.")
        return 
    
    # 3. Aggregation durchfuehren
    print(f"Starte Aggregation von {len(standardized_index)} standardisierten Biomarkern...")
    final_data = aggregate_biomarker_details(standardized_index, doc_cache)
    
    # 4. Speichern der konsolidierten Ergebnisse
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Detail-Aggregation abgeschlossen.")
    print(f"  Gesamtzahl der eindeutigen Biomarker (Standardisiert): {len(final_data)}")
    print(f"  Ergebnisse gespeichert in '{OUTPUT_FILE}'")
    print("=========================================================\n")


if __name__ == "__main__":
    main()