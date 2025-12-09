import json
import os
from time import sleep
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from collections import defaultdict

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

# Input-Ordner mit den analysierten JSONs aus Phase 1 (Thread-Output)
INPUT_FOLDER = os.environ.get("PHASE1_OUTPUT_FOLDER", "semantic_serial_results") 
# Output-Datei fuer die bereinigte Liste
OUTPUT_FILE = "standardized_biomarkers4.json"
MAX_WORKERS = 4 # Anzahl der gleichzeitigen API-Anfragen


# --- API KEYS AND MODEL MAPPING (Laden aus Umgebungsvariablen) ---

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

# Das Schema fuer den API-Output (Schritt 1: Standardisierung pro Batch)
STANDARDIZATION_SCHEMA = {
  "type": "array",
  "description": "Consolidated list of biomarker entries, ensuring identical biomarkers share the same standard name.",
  "items": {
    "type": "object",
    "properties": {
      "biomarker_name": {
        "type": "string",
        "description": "The standardized, scientific consensus name for the biomarker (e.g., Brain-Derived Neurotrophic Factor)."
      },
      "original_name": {
        "type": "string",
        "description": "The name of the biomarker as it appeared in the input data (e.g., Serum BDNF levels)."
      },
      "document_source_id": {
        "type": "string",
        "description": "The source document ID where this finding originated."
      }
    },
    "required": ["standard_name", "original_name", "document_source_id"]
  }
}

# Das Schema fuer den END-OUTPUT (Schritt 2: Fusion in Python)
# NEUES ZIELSCHEMA: Behaelt die Paare (Originalname, ID)
FINAL_FUSION_SCHEMA = {
  "type": "array",
  "description": "Final list of unique biomarkers, with all original names and document ID pairs fused into a single entry per standardized name.",
  "items": {
    "type": "object",
    "properties": {
      "standard_name": {
        "type": "string",
        "description": "The standardized, scientific consensus name for the biomarker."
      },
      "source_entries": {
        "type": "array",
        "description": "Unique original name and document ID pairs found for this biomarker.",
        "items": {
            "type": "object",
            "properties": {
                "original_name": {"type": "string", "description": "The name as extracted from the source document."},
                "document_source_id": {"type": "string", "description": "The source document ID."}
            },
            "required": ["original_name", "document_source_id"]
        }
      }
    },
    "required": ["standard_name", "source_entries"]
  }
}


# --- BATCH USAGE TRACKER (Lokal pro Batch) ---

class BatchUsageTracker:
    """Tracker fuer die Tokens innerhalb eines einzelnen Batches."""
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.total_calls = 0
        self.provider = API_PROVIDER
        self.model = MODELS[API_PROVIDER]
    
    def to_dict(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
        }
        
    def add_usage(self, usage: Dict[str, Any]):
        """Addiert die Usage-Daten eines einzelnen API-Calls."""
        self.input_tokens += usage.get('input_tokens', 0)
        self.output_tokens += usage.get('output_tokens', 0)
        self.total_tokens += usage.get('total_tokens', 0)
        self.total_calls += 1


# --- SIMPLE PROVIDER IMPLEMENTATIONS (Rückgabe von Resultat und Usage) ---

def _call_gemini_api_simple(user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Gemini Call mit Raw Requests."""
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
        
        # Token-Zaehlung
        usage_metadata = result.get('usageMetadata', {})
        usage_data = {
            'input_tokens': usage_metadata.get('promptTokenCount', 0),
            'output_tokens': usage_metadata.get('candidatesTokenCount', 0),
            'total_tokens': usage_metadata.get('totalTokenCount', 0),
        }
        
        return json.loads(json_text), usage_data
    except Exception as e:
        return {"error": f"Gemini Error: {e}"}, usage_data

def _call_claude_api_simple(user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Claude Call mit SDK und Tool Use."""
    usage_data = {}
    if not ANTHROPIC_CLIENT: return {"error": "Claude Client not ready."}, usage_data
    
    # Anpassung fuer Claude Array Schema (Clustering Schema ist ein Array)
    if response_schema.get("type", "").lower() == "array":
        claude_input_schema = {"type": "object", "properties": {"consolidated_list": response_schema}, "required": ["consolidated_list"]}
    else:
        claude_input_schema = response_schema

    tool_schema = {"name": "standardize_biomarkers", "description": "Standardize biomarker names.", "input_schema": claude_input_schema}

    try:
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODELS["CLAUDE"], max_tokens=4096, tools=[tool_schema], messages=[{"role": "user", "content": user_query}]
        )
        
        # Token-Zaehlung
        usage = response.usage
        usage_data = {
            'input_tokens': usage.input_tokens, 
            'output_tokens': usage.output_tokens,
            'total_tokens': usage.input_tokens + usage.output_tokens
        }

        if response.stop_reason == "tool_use":
            raw_input = [c for c in response.content if c.type == "tool_use"][0].input
            if response_schema.get("type", "").lower() == "array":
                 return raw_input.get("consolidated_list", {"error": "Failed to unwrap Claude response."}), usage_data
            return raw_input, usage_data
        return {"error": f"Claude did not use tool. Stop: {response.stop_reason}"}, usage_data
    except Exception as e:
        return {"error": f"Claude SDK Error: {e}"}, usage_data

def _call_openai_api_simple(user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """OpenAI Call mit SDK und Function Calling."""
    usage_data = {}
    if not OPENAI_CLIENT: return {"error": "OpenAI Client not ready."}, usage_data

    # Schema ist bereits bereinigt (kleingeschrieben)
    tool_schema = {
        "type": "function",
        "function": {"name": "standardize_biomarkers", "description": "Standardize biomarker names.", "parameters": response_schema}
    }

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=MODELS["OPENAI"], messages=[{"role": "user", "content": user_query}], tools=[tool_schema],
            tool_choice={"type": "function", "function": {"name": "standardize_biomarkers"}}
        )
        
        # Token-Zaehlung
        usage = response.usage
        usage_data = {
            'input_tokens': usage.prompt_tokens, 
            'output_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens
        }

        if response.choices[0].message.tool_calls:
            args = response.choices[0].message.tool_calls[0].function.arguments
            return json.loads(args), usage_data
        return {"error": "OpenAI did not use function call."}, usage_data
    except Exception as e:
        return {"error": f"OpenAI SDK Error: {e}"}, usage_data


# --- UNIFIED API CALL HANDLER ---

def call_llm_api_internal(user_query: str, response_schema: Dict[str, Any], usage_tracker: BatchUsageTracker) -> Tuple[Dict[str, Any], BatchUsageTracker]:
    """
    Routet den API Call und fuehrt Exponential Backoff durch.
    Aktualisiert den BatchUsageTracker.
    """
    
    provider_map = {
        "GEMINI": _call_gemini_api_simple,
        "CLAUDE": _call_claude_api_simple,
        "OPENAI": _call_openai_api_simple,
    }
    
    if API_PROVIDER not in provider_map:
        return {"error": f"Invalid API_PROVIDER selected: {API_PROVIDER}"}, usage_tracker
        
    api_caller = provider_map[API_PROVIDER]
    
    # Vereinfachtes Retry-Schema
    for attempt in range(3):
        # api_caller gibt (result, usage_metadata) zurueck
        result, usage_metadata = api_caller(user_query, response_schema)
        
        if "error" not in result:
            # Token zur Batch-Usage addieren und Tracker zurueckgeben
            usage_tracker.add_usage(usage_metadata)
            return result, usage_tracker
        
        print(f"!!! Error from {API_PROVIDER} on Batch Call {usage_tracker.total_calls + 1} (Attempt {attempt + 1}): {result['error']}")
        sleep(1.0 + attempt * 2) # Exponential backoff

    return {"error": f"Failed after multiple attempts with {API_PROVIDER}: {result['error']}"}, usage_tracker


# --- DATENLADE- & VORVERARBEITUNGSFUNKTIONEN ---

def load_all_biomarkers_for_clustering(directory_path: str) -> List[Dict[str, str]]:
    """
    Lädt alle Biomarker-Namen und IDs aus allen JSON-Dateien in eine flache Liste.
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
                    
                    # Die Dateien enthalten ein Array, das ein einzelnes Dokument-Analyse-Objekt enthält
                    doc_data = data[0] 
                    doc_id = doc_data.get('document_source_id', 'UNKNOWN_ID')
                    
                    extracted_data = doc_data.get('extracted_data', {})
                    # Wir interessieren uns nur fuer die core_effect_and_quantification
                    core_effects = extracted_data.get('core_effect_and_quantification', [])
                    
                    for entry in core_effects:
                        biomarker_name = entry.get('biomarker_name')
                        if biomarker_name:
                            all_biomarkers.append({
                                "original_name": biomarker_name,
                                "document_source_id": doc_id
                            })
                            
            except (json.JSONDecodeError, IndexError, AttributeError) as e:
                print(f"  - Fehler: Datei {filename} konnte nicht geparst werden: {e}")
            
    print(f"\nGeladene Biomarker-Einträge zur Standardisierung: {len(all_biomarkers)}")
    return all_biomarkers

def cluster_and_standardize_batch(batch: List[Dict[str, str]], batch_id: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Sendet eine Charge von Biomarkern an die LLM API zur Standardisierung.
    Gibt die standardisierten Ergebnisse und die Usage zurueck.
    """
    
    tracker = BatchUsageTracker()
    
    # 1. Prompt erstellen
    prompt_instruction = (
        "TASK: You are a scientific nomenclature expert. Given a list of biomarker entries, you must assign a single, "
        "consensus 'standard_name' for groups of entries that refer to the same molecular entity (despite spelling/synonym variation). "
        "Output the result as an array of objects strictly following the provided schema. "
        "The standard name should be the full, formal name (e.g., 'Brain-Derived Neurotrophic Factor' for 'BDNF' or 'Serum BDNF levels').\n\n"
        "Input Biomarker Entries:\n"
        f"{json.dumps(batch, indent=2)}"
    )

    # 2. API Call (tracked durch den BatchUsageTracker)
    result, tracker = call_llm_api_internal(prompt_instruction, STANDARDIZATION_SCHEMA, tracker)
    
    if "error" in result:
        # Rueckgabe des Fehlers und der akkumulierten Tokens (auch wenn fehlerhaft)
        return [], tracker.to_dict()
    
    # 3. Validierung und Rueckgabe
    if isinstance(result, list):
        print(f"-> Batch {batch_id} (Size: {len(batch)}) erfolgreich standardisiert.")
        return result, tracker.to_dict()
    else:
        print(f"!!! FEHLER: Batch {batch_id} hat ungültiges Array zurueckgegeben.")
        return [], tracker.to_dict()

# --- NEUE FUSIONSLOGIK IN PYTHON (Schritt 2 der Phase 3) ---

def fuse_standardized_results(standardized_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Führt die Standardisierungs-Ergebnisse zusammen, um Dubletten zu eliminieren 
    und Originalnamen/IDs unter dem standardisierten Namen zu konsolidieren.
    """
    # fused_map verwendet den standard_name als Schluessel.
    # Der Wert ist ein Dictionary, das die Liste der Paare speichert.
    fused_map = defaultdict(lambda: {
        'source_entries': set() # Wird Tupel (original_name, document_source_id) speichern
    })

    for entry in standardized_results:
        standard_name = entry.get('standard_name')
        original_name = entry.get('original_name')
        doc_id = entry.get('document_source_id')

        if standard_name and original_name and doc_id:
            # Füge das Paar (Originalname, ID) als Tupel hinzu.
            # Tupel sind hashbar und koennen in einem Set verwendet werden.
            fused_map[standard_name]['source_entries'].add((original_name, doc_id))

    # Konvertierung des Maps in das finale Array-Schema
    final_list = []
    for standard_name, data in fused_map.items():
        # Konvertiere das Set von Tupeln in eine Liste von Dictionaries,
        # sortiert nach dem standard_name für Konsistenz.
        source_entries_list = sorted([
            {"original_name": on, "document_source_id": did}
            for on, did in data['source_entries']
        ], key=lambda x: (x['original_name'], x['document_source_id']))
        
        final_list.append({
            "standard_name": standard_name,
            "source_entries": source_entries_list
        })
        
    return final_list


def main():
    print("--- PHASE 3: BIOMARKER STANDARDIZATION AND CLUSTERING ---")
    
    # 1. Daten laden (flache Liste aller Biomarker-Einträge)
    all_raw_biomarkers = load_all_biomarkers_for_clustering(INPUT_FOLDER)
    if not all_raw_biomarkers:
        print("Pipeline gestoppt: Keine Biomarker zum Standardisieren gefunden.")
        return

    # 2. Daten in Batches aufteilen 
    BATCH_SIZE = 1000 
    batches = [
        all_raw_biomarkers[i:i + BATCH_SIZE]
        for i in range(0, len(all_raw_biomarkers), BATCH_SIZE)
    ]
    
    # Initiale Listen und Tracker
    standardized_results_batches = []
    total_usage = {
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "total_calls": 0,
        "provider": API_PROVIDER, "model": MODELS[API_PROVIDER]
    }
    successful_batches = 0
    
    # --- 3. PARALLELE VERARBEITUNG DER BATCHES (Standardisierung) ---
    print(f"Aufteilung in {len(batches)} Batches. Starte Parallelverarbeitung mit {MAX_WORKERS} Threads.")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(cluster_and_standardize_batch, batch, i + 1): i + 1
            for i, batch in enumerate(batches)
        }
        
        for future in concurrent.futures.as_completed(futures):
            # result ist Tuple: (standardisierte_liste, usage_dict)
            standardized_batch, usage_dict = future.result()
            
            standardized_results_batches.extend(standardized_batch)
            
            # Akkumulierung der Gesamt-Usage
            total_usage['input_tokens'] += usage_dict['input_tokens']
            total_usage['output_tokens'] += usage_dict['output_tokens']
            total_usage['total_tokens'] += usage_dict['total_tokens']
            total_usage['total_calls'] += usage_dict['total_calls']
            
            if standardized_batch:
                successful_batches += 1
                
    # --- 4. PYTHON-BASIERTE FUSION (Eliminierung von Dubletten) ---
    print("\nStarte finale Python-Fusion (Eliminierung von Dubletten und Zusammenführung der IDs)...")
    final_fused_list = fuse_standardized_results(standardized_results_batches)


    # 5. Speichern der konsolidierten Ergebnisse
    # NOTE: Wir verwenden hier das interne FINAL_FUSION_SCHEMA, um die Struktur zu dokumentieren.
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_fused_list, f, indent=2)
        
    print("\n=========================================================")
    print(f"✅ SUCCESS: Biomarker Standardization & Fusion abgeschlossen.")
    print(f"  Verarbeitete Batches (API-Calls): {successful_batches} von {len(batches)}")
    print(f"  Gesamtzahl der eindeutigen Biomarker (nach Fusion): {len(final_fused_list)}")
    print(f"  Ergebnisse gespeichert in '{OUTPUT_FILE}'")
    
    print("\n--- GESAMTE TOKEN-NUTZUNG FÜR PHASE 3 ---")
    print(f"Provider: {total_usage['provider']} ({total_usage['model']})")
    print(f"Total API Calls: {total_usage['total_calls']}")
    print(f"Input Tokens (Prompt/Data): {total_usage['input_tokens']}")
    print(f"Output Tokens (Response): {total_usage['output_tokens']}")
    print(f"Total Tokens Used: {total_usage['total_tokens']}")
    print("=========================================================\n")


if __name__ == "__main__":
    main()