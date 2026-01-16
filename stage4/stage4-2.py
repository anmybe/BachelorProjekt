import json
import os
from time import sleep
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from collections import defaultdict

# --- CONFIGURATION ---

# --- Python-DotEnv Import ---
from dotenv import load_dotenv
load_dotenv()
# --- END Python-DotEnv Import ---

# --- LLM API IMPORTS ---
import requests 

try:
    import anthropic
    from anthropic import APIError, APIStatusError
except ImportError:
    anthropic = None
    APIError = type('APIError', (Exception,), {})
    APIStatusError = type('APIStatusError', (Exception,), {})

try:
    import openai
    from openai import OpenAI
    from openai import APIError as OpenAI_APIError
except ImportError:
    openai = None
    OpenAI_APIError = type('OpenAI_APIError', (Exception,), {})
# --- END IMPORTS ---


# --- CONFIGURATION (The Switch) ---

# Choose your provider here: "GEMINI", "CLAUDE", or "OPENAI"
API_PROVIDER = "GEMINI" 

MOCK_MODE = False
INPUT_FILE_STEP2 = "biomarker-name-list(4-1).json"
OUTPUT_FILE_STEP3 = "biomarker-list-standardized(4-2).json"

MAX_WORKERS = 4 # Number of concurrent API requests
BATCH_SIZE = 150

# --- API KEYS AND MODEL MAPPING (Load from environment variables) ---

API_KEYS = {
    "GEMINI": os.environ.get("GEMINI_API_KEY"),
    "CLAUDE": os.environ.get("CLAUDE_API_KEY"),
    "OPENAI": os.environ.get("OPENAI_API_KEY"),
}

# Provider-specific model selections
MODELS = {
    "GEMINI": "gemini-2.5-flash", # Using the specific preview name for the raw API
    "CLAUDE": "claude-opus-4-5",                 # Best structured output
    "OPENAI": "gpt-4.1"                   # Best structured output
}

# --- GLOBAL CLIENT INITIALIZATION ---
# Initialize SDK clients only if the provider is selected and the library is imported

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=API_KEYS["CLAUDE"]) if anthropic else None
OPENAI_CLIENT = OpenAI(api_key=API_KEYS["OPENAI"]) if OpenAI else None

# The base URL structure for the raw Gemini API call
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['GEMINI']}:generateContent?key={API_KEYS['GEMINI']}"

# --- SCHEMA DEFINITION (Clustering Output) ---

# Schema for API output: We return the list of clusters.
STANDARDIZATION_SCHEMA = {
  "type": "array",
  "description": "Consolidated list of biomarker entries, ensuring identical or synonymous biomarkers are grouped and assigned a consensus standard name.",
  "items": {
    "type": "object",
    "properties": {
      "standard_name": {
        "type": "string",
        "description": "The newly assigned, unified, and scientifically recognized name for the group of synonyms/variants (e.g., 'Cathelicidin Antimicrobial Peptide' for 'LL-37' and 'LL37')."
      },
      "original_name": {
        "type": "string",
        "description": "The exact original biomarker name from the input list (e.g., 'LL-37')."
      },
      "document_source_id": {
        "type": "string",
        "description": "The source document ID associated with this original name."
      }
    },
    "required": ["standard_name", "original_name", "document_source_id"]
  }
}

# --- API CALL IMPLEMENTATION ---

class BatchUsageTracker:
    # ... (Class implementation as in your original code, omitted for brevity)
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.total_calls = 0
    def add_usage(self, usage: Dict[str, Any]):
        self.input_tokens += usage.get('promptTokenCount', 0)
        self.output_tokens += usage.get('candidatesTokenCount', 0)
        self.total_tokens += usage.get('totalTokenCount', 0)
        self.total_calls += 1
    def to_dict(self):
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens, "total_tokens": self.total_tokens, "total_calls": self.total_calls}

def _call_gemini_api_simple(user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Gemini Call with Raw Requests."""
    usage_data = {}
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": response_schema}
    }
    try:
        response = requests.post(GEMINI_API_URL, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
        
        # Token counting
        usage_metadata = result.get('usageMetadata', {})
        
        # Add usage metadata
        return json.loads(json_text), usage_metadata
    except Exception as e:
        return {"error": f"Gemini Error: {e}"}, usage_data

def call_llm_api_internal(user_query: str, response_schema: Dict[str, Any], usage_tracker: BatchUsageTracker) -> Tuple[Dict[str, Any], BatchUsageTracker]:
    """Routes the API call and performs exponential backoff."""
    
    for attempt in range(3):
        result, usage_metadata = _call_gemini_api_simple(user_query, response_schema)
        
        if "error" not in result:
            usage_tracker.add_usage(usage_metadata)
            return result, usage_tracker
        
        print(f"!!! Error from GEMINI on Batch Call (Attempt {attempt + 1}): {result['error']}")
        sleep(1.0 + attempt * 2) 

    return {"error": f"Failed after multiple attempts with GEMINI: {result['error']}"}, usage_tracker

# --- FUSION LOGIC (Step 3) ---

def load_and_prepare_input(filepath: str) -> List[Dict[str, Any]]:
    """
    Loads fused groups from Step 2 and sorts them by their
    current 'standard_name' (which is still the original name).
    
    The output is a list of objects sent directly in batches to the AI.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{filepath}' not found.")
        return []

    # 1. Sort list by current 'standard_name' (Original Name)
    # This is the crucial step for consistency.
    data.sort(key=lambda x: x['standard_name'])
            
    print(f"Loaded biomarker groups (from Step 2): {len(data)}")
    print("Groups successfully sorted by 'standard_name'.")
    
    return data

def cluster_and_standardize_batch(batch: List[Dict[str, Any]], batch_id: int, total_usage: BatchUsageTracker) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Sends a batch of fused biomarker GROUPS to the LLM API.
    
    The AI must fuse groups based on their 'standard_name'.
    """
    
    # 1. Convert groups to flat list of entries the AI can fuse
    # We must revert the format the AI expects in the response.
    flat_list_for_ki = []
    for group in batch:
        current_name = group['standard_name']
        for entry in group['source_entries']:
             flat_list_for_ki.append({
                "original_name": current_name,
                "document_source_id": entry['document_source_id']
            })
    
    # 2. AI Prompt with new instruction
    prompt_instruction = (
        "TASK: You are a scientific nomenclature expert. Given a list of biomarker entries, your task is to standardize and cluster them. "
        "Each 'original_name' in the list currently represents a unique finding from Step 2, but multiple 'original_name' entries may be synonyms (e.g., 'LL-37' and 'LL37'). "
        "You must assign a single, scientifically authoritative 'standard_name' for all synonym groups. "
        "Example: If 'LL-37' and 'LL37' appear in the input, the output entries for both must have the 'standard_name' set to 'Cathelicidin Antimicrobial Peptide'. "
        "Ensure all 'document_source_id' and 'original_name' pairs are preserved and returned, grouped under the new 'standard_name'. "
        "Output the result as an array of objects strictly following the provided schema. "
        "Do not alter 'document_source_id' or 'original_name'.\n\n"
        "Input Biomarker Entries (Current Groupings):\n"
        f"{json.dumps(flat_list_for_ki, indent=2)}"
    )

    # The tracker is returned in thread context, usage is accumulated in main.
    result, total_usage = call_llm_api_internal(prompt_instruction, STANDARDIZATION_SCHEMA, total_usage)
    
    if "error" in result:
        print(f"!!! ERROR in Batch {batch_id}: {result.get('error')}")
        return [], total_usage.to_dict()
    
    if isinstance(result, list):
        print(f"-> Batch {batch_id} (Groups: {len(batch)}) successfully standardized.")
        return result, total_usage.to_dict()
    else:
        print(f"!!! ERROR: Batch {batch_id} returned invalid array: {result}")
        return [], total_usage.to_dict()


def fuse_standardized_results_step3(standardized_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # ... (Fusion logic remains identical as it works with flat AI output)
    fused_map = defaultdict(lambda: {
        'source_entries': set() 
    })

    for entry in standardized_results:
        standard_name = entry.get('standard_name')
        original_name = entry.get('original_name')
        doc_id = entry.get('document_source_id')

        if standard_name and original_name and doc_id:
            # Add pair (OriginalName, ID) as tuple (Set prevents duplicates from AI response)
            fused_map[standard_name]['source_entries'].add((original_name, doc_id))

    # Conversion of map to final array schema
    final_list = []
    for standard_name, data in fused_map.items():
        source_entries_list = sorted([
            {"original_name": on, "document_source_id": did}
            for on, did in data['source_entries']
        ], key=lambda x: (x['original_name'], x['document_source_id']))
        
        final_list.append({
            "standard_name": standard_name,
            "source_entries": source_entries_list
        })
        
    return sorted(final_list, key=lambda x: x['standard_name'])


def main_step3():
    print("--- STEP 3: AI-BASED BIOMARKER STANDARDIZATION ---")
    
    # 1. Load Data (Loads groups to be sorted)
    all_raw_groups = load_and_prepare_input(INPUT_FILE_STEP2)
    if not all_raw_groups:
        print("Pipeline stopped: No biomarkers found for standardization.")
        return

    # 2. Split data into batches (Now BATCH_SIZE counts number of groups)
    batches = [
        all_raw_groups[i:i + BATCH_SIZE]
        for i in range(0, len(all_raw_groups), BATCH_SIZE)
    ]
    
    # ... (Rest of main_step3 function remains same)
    standardized_results_batches = []
    total_usage = BatchUsageTracker()
    successful_batches = 0
    
    # --- 3. PARALLEL PROCESSING OF BATCHES (Standardization) ---
    print(f"Split into {len(batches)} batches. Starting parallel processing with {MAX_WORKERS} threads.")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            # Important: total_usage must be treated as thread-safe tracker
            executor.submit(cluster_and_standardize_batch, batch, i + 1, total_usage): i + 1
            for i, batch in enumerate(batches)
        }
        
        for future in concurrent.futures.as_completed(futures):
            standardized_batch, usage_dict = future.result()
            
            standardized_results_batches.extend(standardized_batch)
            
            if standardized_batch:
                successful_batches += 1
                
    # --- 4. PYTHON-BASED FUSION (Final Grouping) ---
    print("\nStarting final Python fusion (Grouping under new standard name)...")
    final_fused_list = fuse_standardized_results_step3(standardized_results_batches)

    # 5. Save consolidated results
    with open(OUTPUT_FILE_STEP3, "w", encoding='utf-8') as f:
        json.dump(final_fused_list, f, indent=2, ensure_ascii=False)
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Step 3 completed.")
    print(f"  Processed batches (API calls): {successful_batches} of {len(batches)}")
    print(f"  Total number of unique standard biomarkers (after fusion): {len(final_fused_list)}")
    print(f"  Results saved in '{OUTPUT_FILE_STEP3}'")
    print("\n--- TOKEN USAGE ---")
    print(f"Total API Calls: {total_usage.total_calls}")
    print(f"Total Tokens Used: {total_usage.total_tokens}")
    print("=========================================================\n")


if __name__ == "__main__":
    # Import 'requests' and 'dotenv' here if not global
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    main_step3()