import json
import os
import re
from collections import defaultdict
from typing import Dict, Any, List, Optional, Set, Tuple

# --- CONFIGURATION (Load from environment) ---
# Load folder names from .env file
from dotenv import load_dotenv
load_dotenv()

# Input folder containing original Phase 1 analyses
PHASE1_INPUT_FOLDER = "stage3_Results"
# Input file from Phase 3 (with standardized names)
PHASE3_INPUT_FILE = "biomarker-list-standardized(4-2).json"
# Final output file
OUTPUT_FILE = "consolidated-list(4-3).json"

# --- HELPER FUNCTION: NAME NORMALIZATION ---

def normalize_name_for_comparison(name: str) -> str:
    """Converts name to lowercase and removes ALL
    superfluous whitespace characters (incl. \n, \t, \r, \b)
    for robust comparison."""
    # Used for internal matching.
    # This is the crucial fix for special char/whitespace problems
    cleaned_name = re.sub(r'\s+', '', name) 
    return cleaned_name.lower()

# --- CORE LOGIC ---

def load_index_file(filepath: str) -> List[Dict[str, Any]]:
    """Loads standardized biomarker list from Phase 3."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Index file '{filepath}' not found. Please run Phase 3 first.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Index file '{filepath}' contains invalid JSON.")
        return []

def load_document_cache(source_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads all Phase 1 documents into a cache for fast search.
    Key is the document_source_id.
    """
    cache = {}
    if not os.path.isdir(source_dir):
        print(f"Error: Source folder '{source_dir}' (Phase 1 Results) not found.")
        return cache
        
    for filename in os.listdir(source_dir):
        if filename.endswith('_analysis.json'):
            # doc_id is part before "_analysis.json"
            doc_id = filename.replace('_analysis.json', '') 
            file_path = os.path.join(source_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Phase 1 files contain array with exactly one analysis object
                    data = json.load(f)[0] 
                    cache[doc_id] = data
            except (json.JSONDecodeError, IndexError, AttributeError):
                print(f"Warning: Document {filename} could not be loaded into cache.")
                
    print(f"Document cache loaded: {len(cache)} documents available.")
    return cache

def extract_and_consolidate_details(standard_name: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    This function serves manual/rule-based synthesis of biomarker details.
    """
    
    # PLACEHOLDER Logic (Keep, as no AI should be used)
    # Note: standard_name should be clean here, as it comes from Phase 3.
    if len(findings) == 1:
        return {
            "overall_biomarker_summary": f"Manual Synthesis: {standard_name} was found in {findings[0]['document_source_id']}. The actual summary must be added manually.",
            "mechanisms_consensus": "Manual Synthesis: Here would be the consolidated mechanism summary.",
            "reliability_consensus": "Manual Synthesis: Here would be the consolidated reliability summary."
        }
    
    return {
        "overall_biomarker_summary": f"Automatic placeholder for {standard_name}: Found in {len(findings)} sources. Manual synthesis required.",
        "mechanisms_consensus": f"Details on mechanisms are in 'aggregated_source_findings_DEBUG'.",
        "reliability_consensus": "Manual aggregation of reliability across multiple studies needed."
    }


def aggregate_biomarker_details(standardized_index: List[Dict[str, Any]], doc_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregates all detail info (analyzed_biomarkers) under standardized name
    and adds summary fields.
    """
    final_aggregated_data = []
    total_matched_findings = 0 # Counter for debugging

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
            
            # NEW: Normalize original name FOR COMPARISON
            normalized_original_name = normalize_name_for_comparison(original_name)
            
            # We search in array 'analyzed_biomarkers'
            analyzed_biomarkers = extracted_data.get('analyzed_biomarkers', [])
            
            # Find ALL biomarker details matching original name
            matching_biomarker_details = [
                detail for detail in analyzed_biomarkers 
                # HERE THE FIX: Normalized comparison
                if normalize_name_for_comparison(detail.get('biomarker_name', '')) == normalized_original_name
            ]

            if matching_biomarker_details:
                total_matched_findings += 1 # Increase debugging counter
                
                # Add finding to aggregate
                aggregated_findings.append({
                    "original_name": original_name,
                    "document_source_id": doc_id,
                    "document_context_data": {
                        "document_summary": extracted_data.get('document_summary'),
                        "treatment_details": extracted_data.get('treatment_details'),
                    },
                    "matched_biomarker_details": matching_biomarker_details 
                })


        # 2. Build final entry
        if aggregated_findings:
            
            # Create summary fields
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
            
    print(f"DEBUG: Total number of successfully matched original names: {total_matched_findings}")
    return final_aggregated_data


def main():
    print("--- PHASE 4: DETAIL AGGREGATION AND SYNTHESIS PREPARATION (Pure Python) ---")
    
    # 1. Load Index File (Output of Phase 3)
    standardized_index = load_index_file(PHASE3_INPUT_FILE)
    if not standardized_index:
        print("Pipeline stopped: Could not load index file.")
        return

    # 2. Load Original Documents (Cache of Phase 1 Results)
    doc_cache = load_document_cache(PHASE1_INPUT_FOLDER)
    if not doc_cache:
        print("Pipeline stopped: Could not load source documents.")
        return 
    
    # 3. Perform Aggregation
    print(f"Starting aggregation of {len(standardized_index)} standardized biomarkers...")
    final_data = aggregate_biomarker_details(standardized_index, doc_cache)
    
    # 4. Save consolidated results
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Detail Aggregation completed.")
    print(f"  Total number of unique biomarkers (Standardized): {len(final_data)}")
    print(f"  Results saved in '{OUTPUT_FILE}'")
    print("=========================================================\n")


if __name__ == "__main__":
    main()