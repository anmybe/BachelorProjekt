import json
import os
from collections import defaultdict
from typing import Dict, Any, List, Tuple

# --- CONFIGURATION (Keep folder names) ---

# Input folder with analyzed JSONs from Phase 1 (Thread Output)
INPUT_FOLDER = "stage3/stage3_Results" 
# Output file for the cleaned list
OUTPUT_FILE = "biomarker-name-list(4-1).json"

# --- PURE PYTHON STANDARDIZATION ---

def get_standard_name_from_original(original_name: str) -> str:
    """
    This function implements the rule-based or database-based
    standardization to assign each original name to a single, consistent
    standard name.
    
    SINCE AI IS EXPLICITLY EXCLUDED, THIS MAPPING MUST BE DONE
    MANUALLY OR VIA A STATIC LOOKUP TABLE.
    
    The standard name should always be the longest, scientifically correct name.
    """
    
    # Example mapping based on provided data (Partial list!)
    MAPPING = {
        # MicroRNA Examples
        "miR-4539": "microRNA-4539",
        "miR-6132": "microRNA-6132",
        "miR-122–5p": "microRNA-122-5p",
        "miR-125b-5p": "microRNA-125b-5p",
        "miR-146a-5p": "microRNA-146a-5p",
        "miR-365a-3p": "microRNA-365a-3p",
        "miR-375": "microRNA-375",
        "miR-130a-3p": "microRNA-130a-3p",
        "miR-155–5p": "microRNA-155-5p",
        
        # Protein/Antigen Examples
        "percentage of γ-H2AX positive cells": "Phosphorylated Histone H2AX",
        "γ-H2AX foci": "Phosphorylated Histone H2AX",
        "γ-H2AX foci per cell": "Phosphorylated Histone H2AX",
        "53BP1 foci": "TP53 Binding Protein 1",
        "53BP1 levels": "TP53 Binding Protein 1",
        "CA19-9": "Carbohydrate Antigen 19-9",
        "THBS2": "Thrombospondin 2",
        "Anti-p53 antibody in combination with serum concentrations of CEA and CA19-9": "Anti-p53 Antibody",
        "CEA": "Carcinoembryonic Antigen", # Must be assigned here as it often appears combined with CA19-9
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
        
        # Cell Marker / Cluster of Differentiation Examples
        "CD72": "Cluster of Differentiation 72",
        "CD59": "Cluster of Differentiation 59",
        "CD3+": "Cluster of Differentiation 3",
        "CD20+": "Cluster of Differentiation 20",
        "CD68+": "Cluster of Differentiation 68",
        # Important: Specific cell types MUST be mapped to the base biomarker
        "CD226+ B cells": "Cluster of Differentiation 226", 
        "CD226+ CD4+ T cells": "Cluster of Differentiation 226",
        # ... further CD226 entries if present
        
        # Panel Examples (these are harder to map statically)
        "Signature of 8 long noncoding RNAs": "Long Noncoding RNA Panel",
        "Five other miRNAs": "Unspecified microRNAs",
        "17-protein panel": "Protein Panel",
        "26-protein panel": "Protein Panel",
        "4-protein panel": "Protein Panel",
        "Protein and miRNA biomarker panels (combined)": "Protein and microRNA Panel",
        "Six serum proteins": "Serum Protein Panel",
    }

    # First try to find an exact match
    name_to_check = original_name.strip()
    if name_to_check in MAPPING:
        return MAPPING[name_to_check]

    # SECOND STRATEGY (Substring mapping, only for abbreviations/CDs)
    # If the name contains a known abbreviation (e.g. CD226+ B cells)
    for original_key, standard_value in MAPPING.items():
        if original_name.startswith(original_key) and original_key.startswith("CD"):
            return standard_value

    # THIRD STRATEGY (Default return if mapping missing)
    # Here we must decide whether to return the name (no standardization)
    # or use a placeholder.
    # For safe fusion we return the original name untouched
    # and must fuse manually later.
    return original_name # ATTENTION: Does NOT standardize this entry!


def load_all_biomarkers_for_clustering(directory_path: str) -> List[Dict[str, str]]:
    """
    Loads all biomarker names and IDs from all JSON files into a flat list
    (Your corrected version).
    """
    if not os.path.isdir(directory_path):
        print(f"Error: The input directory '{directory_path}' was not found.")
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
                    # Adjustment: Use 'analyzed_biomarkers'
                    biomarkers = extracted_data.get('analyzed_biomarkers', [])
                    
                    for entry in biomarkers:
                        biomarker_name = entry.get('biomarker_name')
                        if biomarker_name:
                            all_biomarkers.append({
                                "original_name": biomarker_name,
                                "document_source_id": doc_id
                            })
                            
            except (json.JSONDecodeError, IndexError, AttributeError) as e:
                print(f"  - Error: File {filename} could not be parsed: {e}")
            
    print(f"\nLoaded biomarker entries for standardization: {len(all_biomarkers)}")
    return all_biomarkers


def fuse_and_standardize_results_pure_python(raw_entries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Performs standardization and fusion in one step without LLM,
    based on the pure Python mapping logic.
    """
    # fused_map uses standard_name as key.
    fused_map = defaultdict(lambda: {
        'source_entries': set() # Stores tuples (original_name, document_source_id)
    })

    for entry in raw_entries:
        original_name = entry.get('original_name')
        doc_id = entry.get('document_source_id')
        
        # 1. Standardization: Here the original name is mapped
        standard_name = get_standard_name_from_original(original_name)

        if standard_name and original_name and doc_id:
            # Add pair (OriginalName, ID) as tuple (Set prevents duplicates)
            fused_map[standard_name]['source_entries'].add((original_name, doc_id))

    # 2. Conversion of map to final array schema
    final_list = []
    for standard_name, data in fused_map.items():
        # Convert set of tuples to list of dictionaries,
        # sorted by original_name for consistency.
        source_entries_list = sorted([
            {"original_name": on, "document_source_id": did}
            for on, did in data['source_entries']
        ], key=lambda x: (x['original_name'], x['document_source_id']))
        
        final_list.append({
            "standard_name": standard_name,
            "source_entries": source_entries_list
        })
        
    # Sort final list by standard_name
    return sorted(final_list, key=lambda x: x['standard_name'])


def main_pure_python():
    print("--- PHASE 3: BIOMARKER STANDARDIZATION AND CLUSTERING (PURE PYTHON) ---")
    
    # 1. Load data (flat list of all biomarker entries)
    all_raw_biomarkers = load_all_biomarkers_for_clustering(INPUT_FOLDER)
    if not all_raw_biomarkers:
        print("Pipeline stopped: No biomarkers found for standardization.")
        return

    # 2. Standardization and Fusion in Python
    print("\nStarting pure Python standardization and fusion...")
    final_fused_list = fuse_and_standardize_results_pure_python(all_raw_biomarkers)

    # 3. Save consolidated results
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_fused_list, f, indent=2, ensure_ascii=False) # ensure_ascii=False for special characters
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Biomarker Standardization & Fusion completed.")
    print(f"  Total number of unique biomarkers (after fusion): {len(final_fused_list)}")
    print(f"  Results saved in '{OUTPUT_FILE}'")
    print("=========================================================\n")


if __name__ == "__main__":
    main_pure_python()