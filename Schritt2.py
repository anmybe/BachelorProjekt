import json
import os
from collections import defaultdict
from typing import Dict, Any, List, Tuple

# --- CONFIGURATION (Behalte Ordnernamen) ---

# Input-Ordner mit den analysierten JSONs aus Phase 1 (Thread-Output)
INPUT_FOLDER = "semantic_serial_results_threads_final" 
# Output-Datei fuer die bereinigte Liste
OUTPUT_FILE = "standardized_biomarkers_final.json"

# --- REINE PYTHON STANDARDISIERUNG ---

def get_standard_name_from_original(original_name: str) -> str:
    """
    Diese Funktion implementiert die Regelwerk- oder Datenbank-basierte
    Standardisierung, um jeden Originalnamen einem einzigen, konsistenten
    Standardnamen zuzuordnen.
    
    DA DIE VERWENDUNG VON KI EXPLIZIT AUSGESCHLOSSEN IST, MUSS DIESES
    MAPPING MANUELL ODER ÜBER EINE STATISCHE NACHSCHLAGETABELLE ERFOLGEN.
    
    Der Standardname sollte immer der längste, wissenschaftlich korrekte Name sein.
    """
    
    # Beispiel-Mapping basierend auf den von dir gelieferten Daten (Teilliste!)
    MAPPING = {
        # MicroRNA Beispiele
        "miR-4539": "microRNA-4539",
        "miR-6132": "microRNA-6132",
        "miR-122–5p": "microRNA-122-5p",
        "miR-125b-5p": "microRNA-125b-5p",
        "miR-146a-5p": "microRNA-146a-5p",
        "miR-365a-3p": "microRNA-365a-3p",
        "miR-375": "microRNA-375",
        "miR-130a-3p": "microRNA-130a-3p",
        "miR-155–5p": "microRNA-155-5p",
        
        # Protein/Antigen Beispiele
        "percentage of γ-H2AX positive cells": "Phosphorylated Histone H2AX",
        "γ-H2AX foci": "Phosphorylated Histone H2AX",
        "γ-H2AX foci per cell": "Phosphorylated Histone H2AX",
        "53BP1 foci": "TP53 Binding Protein 1",
        "53BP1 levels": "TP53 Binding Protein 1",
        "CA19-9": "Carbohydrate Antigen 19-9",
        "THBS2": "Thrombospondin 2",
        "Anti-p53 antibody in combination with serum concentrations of CEA and CA19-9": "Anti-p53 Antibody",
        "CEA": "Carcinoembryonic Antigen", # Muss hier zugeordnet werden, da es oft mit CA19-9 in Kombination kommt
        "C3c": "Complement Component 3c",
        "C5b-9": "Complement Component 5b-9",
        "IgM": "Immunoglobulin M",
        "IgG": "Immunoglobulin G",
        "PIIBNP": "Procollagen Type II N-terminal Propeptide",
        "PIIBNP (hsPRO-C2)": "Procollagen Type II N-terminal Propeptide",
        "PIIANP": "Procollagen Type II A N-terminal Propeptide",
        "C2M": "Collagen Type II Degradation Marker C2M",
        "PINP": "Procollagen Type I N-terminal Propeptide",
        "PIICP": "Procollagen Type II C-terminal Propeptide",
        
        # Zell-Marker / Cluster of Differentiation Beispiele
        "CD72": "Cluster of Differentiation 72",
        "CD59": "Cluster of Differentiation 59",
        "CD3+": "Cluster of Differentiation 3",
        "CD20+": "Cluster of Differentiation 20",
        "CD68+": "Cluster of Differentiation 68",
        # Wichtig: Spezifische Zelltypen MÜSSEN auf den Basis-Biomarker gemappt werden
        "CD226+ B cells": "Cluster of Differentiation 226", 
        "CD226+ CD4+ T cells": "Cluster of Differentiation 226",
        # ... weitere CD226 Einträge, falls vorhanden
        
        # Panel Beispiele (diese sind schwerer statisch zu mappen)
        "Signature of 8 long noncoding RNAs": "Long Noncoding RNA Panel",
        "Five other miRNAs": "Unspecified microRNAs",
        "17-protein panel": "Protein Panel",
        "26-protein panel": "Protein Panel",
        "4-protein panel": "Protein Panel",
        "Protein and miRNA biomarker panels (combined)": "Protein and microRNA Panel",
        "Six serum proteins": "Serum Protein Panel",
    }

    # Zuerst versuchen, eine exakte Übereinstimmung zu finden
    name_to_check = original_name.strip()
    if name_to_check in MAPPING:
        return MAPPING[name_to_check]

    # ZWEITE STRATEGIE (Teilstring-Mapping, nur bei Abkürzungen/CDs)
    # Wenn der Name eine bekannte Abkürzung enthält (z.B. CD226+ B cells)
    for original_key, standard_value in MAPPING.items():
        if original_name.startswith(original_key) and original_key.startswith("CD"):
            return standard_value

    # DRITTE STRATEGIE (Standard-Rückgabe bei fehlendem Mapping)
    # Hier muss entschieden werden, ob man den Namen zurückgibt (keine Standardisierung)
    # oder ob man einen Platzhalter verwendet.
    # Für eine sichere Fusion geben wir den Originalnamen unberührt zurück
    # und müssen später manuell fusionieren.
    return original_name # ACHTUNG: Standardisiert diesen Eintrag NICHT!


def load_all_biomarkers_for_clustering(directory_path: str) -> List[Dict[str, str]]:
    """
    Lädt alle Biomarker-Namen und IDs aus allen JSON-Dateien in eine flache Liste
    (Deine korrigierte Version).
    """
    if not os.path.isdir(directory_path):
        print(f"Error: Das Eingabeverzeichnis '{directory_path}' wurde nicht gefunden.")
        return []

    all_biomarkers = []
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    doc_data = data[0]
                    doc_id = doc_data.get('document_source_id', 'UNKNOWN_ID')
                    
                    extracted_data = doc_data.get('extracted_data', {})
                    # Anpassung: Verwenden von 'analyzed_biomarkers'
                    biomarkers = extracted_data.get('analyzed_biomarkers', [])
                    
                    for entry in biomarkers:
                        biomarker_name = entry.get('biomarker_name')
                        if biomarker_name:
                            all_biomarkers.append({
                                "original_name": biomarker_name,
                                "document_source_id": doc_id
                            })
                            
            except (json.JSONDecodeError, IndexError, AttributeError) as e:
                print(f"  - Fehler: Datei {filename} konnte nicht geparst werden: {e}")
            
    print(f"\nGeladene Biomarker-Einträge zur Standardisierung: {len(all_biomarkers)}")
    return all_biomarkers


def fuse_and_standardize_results_pure_python(raw_entries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Führt die Standardisierung und die Fusion in einem Schritt ohne LLM durch,
    basierend auf der reinen Python-Mapping-Logik.
    """
    # fused_map verwendet den standard_name als Schlüssel.
    fused_map = defaultdict(lambda: {
        'source_entries': set() # Speichert Tupel (original_name, document_source_id)
    })

    for entry in raw_entries:
        original_name = entry.get('original_name')
        doc_id = entry.get('document_source_id')
        
        # 1. Standardisierung: Hier wird der Originalname gemappt
        standard_name = get_standard_name_from_original(original_name)

        if standard_name and original_name and doc_id:
            # Füge das Paar (Originalname, ID) als Tupel hinzu (Set verhindert Duplikate)
            fused_map[standard_name]['source_entries'].add((original_name, doc_id))

    # 2. Konvertierung des Maps in das finale Array-Schema
    final_list = []
    for standard_name, data in fused_map.items():
        # Konvertiere das Set von Tupeln in eine Liste von Dictionaries,
        # sortiert nach dem original_name für Konsistenz.
        source_entries_list = sorted([
            {"original_name": on, "document_source_id": did}
            for on, did in data['source_entries']
        ], key=lambda x: (x['original_name'], x['document_source_id']))
        
        final_list.append({
            "standard_name": standard_name,
            "source_entries": source_entries_list
        })
        
    # Sortiere die finale Liste nach standard_name
    return sorted(final_list, key=lambda x: x['standard_name'])


def main_pure_python():
    print("--- PHASE 3: BIOMARKER STANDARDIZATION AND CLUSTERING (PURE PYTHON) ---")
    
    # 1. Daten laden (flache Liste aller Biomarker-Einträge)
    all_raw_biomarkers = load_all_biomarkers_for_clustering(INPUT_FOLDER)
    if not all_raw_biomarkers:
        print("Pipeline gestoppt: Keine Biomarker zum Standardisieren gefunden.")
        return

    # 2. Standardisierung und Fusion in Python
    print("\nStarte reine Python Standardisierung und Fusion...")
    final_fused_list = fuse_and_standardize_results_pure_python(all_raw_biomarkers)

    # 3. Speichern der konsolidierten Ergebnisse
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_fused_list, f, indent=2, ensure_ascii=False) # ensure_ascii=False für Umlaute/Sonderzeichen
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Biomarker Standardization & Fusion abgeschlossen.")
    print(f"  Gesamtzahl der eindeutigen Biomarker (nach Fusion): {len(final_fused_list)}")
    print(f"  Ergebnisse gespeichert in '{OUTPUT_FILE}'")
    print("=========================================================\n")


if __name__ == "__main__":
    main_pure_python()