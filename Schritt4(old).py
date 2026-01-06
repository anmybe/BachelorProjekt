import json
import os
from time import sleep
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

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

# Input-Ordner mit den analysierten JSONs aus Phase 1 (semantic_serial_results3)
PHASE1_INPUT_FOLDER = os.environ.get("PHASE1_OUTPUT_FOLDER", "semantic_serial_results") 
# Die Input-Datei von Phase 3 (mit standardisierten Namen und ID-Paaren)
PHASE3_INPUT_FILE = "standardized_biomarkers3.json"
# Die finale Output-Datei (mit narrativen Zusammenfassungen)
OUTPUT_FILE = "final_biomarker_details_aggregated.json"
MAX_WORKERS = 6 # Anzahl der gleichzeitigen API-Anfragen

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


# --- TOKEN TRACKING (Lokal pro Biomarker) ---

class BiomarkerUsageTracker:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.total_calls = 0
        self.provider = API_PROVIDER
        self.model = MODELS[API_PROVIDER]
    
    def add_usage(self, usage: Dict[str, Any]):
        self.input_tokens += usage.get('input_tokens', 0)
        self.output_tokens += usage.get('output_tokens', 0)
        self.total_tokens += usage.get('total_tokens', 0)
        self.total_calls += 1
    
    def to_dict(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
        }


# --- SCHEMA DEFINITION (Neuer AI Output) ---

FINAL_BIOMARKER_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_biomarker_summary": {
            "type": "string",
            "description": "A comprehensive, narrative summary (2-4 sentences) consolidating the role, effect, and clinical importance of this specific standardized biomarker across all provided documents."
        },
        "mechanisms_consensus": {
            "type": "string",
            "description": "A consolidated summary of all proposed molecular mechanisms and related biomarkers mentioned in the source documents."
        },
        "reliability_consensus": {
            "type": "string",
            "description": "A consolidated synthesis of reliability assessments, limitations (e.g., population/specificity), and recommended future research/alternatives from the source documents."
        }
    },
    "required": ["overall_biomarker_summary", "mechanisms_consensus", "reliability_consensus"]
}


# --- CORE QUERY BUILDER ---

def build_summary_query(standard_name: str, aggregated_data: str) -> str:
    """Builds the user prompt for the final synthesis task."""
    
    INSTRUCTION = (
        "TASK: You are a Lead Scientific Editor. Your task is to analyze the provided raw structured data, which contains "
        "all findings (core effects, mechanisms, implications, reliability) for a single biomarker across multiple scientific papers. "
        "Synthesize this dense, structured input into three fluent, distinct narrative summaries. "
        "Maintain high scientific precision, use quantitative data if available, and adhere strictly to the JSON schema.\n\n"
    )
    
    user_query = (
        f"SYNTHESIS TARGET: **{standard_name}**\n\n"
        f"--- AGGREGATED STRUCTURED DATA ---\n"
        f"{aggregated_data}\n"
        f"--- END OF DATA ---"
    )
    return INSTRUCTION + user_query


# --- PROVIDER-SPECIFIC API CALLERS (Copied from multi_api_pipeline.py) ---
# NOTE: Diese Funktionen sind identisch zu Phase 1, verwenden jedoch den Tracker.

def call_gemini_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Handles API call using raw requests for the Gemini API endpoint."""
    usage_data = {}
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "generationConfig": { 
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
    }
    
    try:
        response = requests.post(GEMINI_API_URL, 
                                 headers={'Content-Type': 'application/json'},
                                 data=json.dumps(payload))
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

def call_claude_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Handles API call using the Anthropic SDK with tool use."""
    usage_data = {}
    if not ANTHROPIC_CLIENT: return {"error": "Claude Client not ready."}, usage_data
        
    # Schema ist ein OBJECT (FINAL_BIOMARKER_SUMMARY_SCHEMA), wird direkt uebergeben
    claude_input_schema = response_schema
    tool_name = "summarize_biomarker"

    tool_schema = {
        "name": tool_name,
        "description": "Synthesize and summarize biomarker details.",
        "input_schema": claude_input_schema
    }
    max_tokens = 4096

    try:
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODELS["CLAUDE"], max_tokens=max_tokens, tools=[tool_schema], messages=[{"role": "user", "content": user_query}]
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
            return raw_input, usage_data
        return {"error": f"Claude did not use tool. Stop: {response.stop_reason}"}, usage_data
    except Exception as e:
        return {"error": f"Claude SDK Error: {e}"}, usage_data

def call_openai_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """OpenAI Call mit SDK und Function Calling."""
    usage_data = {}
    if not OPENAI_CLIENT: return {"error": "OpenAI Client not ready."}, usage_data
    
    # Schema ist bereits bereinigt (kleingeschrieben)
    tool_schema = {
        "type": "function",
        "function": {"name": "summarize_biomarker", "description": "Synthesize and summarize biomarker details.", "parameters": response_schema}
    }

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=MODELS["OPENAI"], messages=[{"role": "user", "content": user_query}], tools=[tool_schema],
            tool_choice={"type": "function", "function": {"name": "summarize_biomarker"}}
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

def call_llm_api_internal(user_query: str, response_schema: Dict[str, Any], usage_tracker: BiomarkerUsageTracker) -> Tuple[Dict[str, Any], BiomarkerUsageTracker]:
    """
    Routet den API Call, fuehrt Exponential Backoff durch und aktualisiert den Tracker.
    """
    
    provider_map = {
        "GEMINI": call_gemini_api,
        "CLAUDE": call_claude_api,
        "OPENAI": call_openai_api,
    }
    
    if API_PROVIDER not in provider_map:
        return {"error": f"Invalid API_PROVIDER selected: {API_PROVIDER}"}, usage_tracker
        
    api_caller = provider_map[API_PROVIDER]
    
    # Vereinfachtes Retry-Schema
    for attempt in range(3):
        result, usage_metadata = api_caller("consolidation_id", user_query, response_schema)
        
        if "error" not in result:
            usage_tracker.add_usage(usage_metadata)
            return result, usage_tracker
        
        print(f"!!! Error from {API_PROVIDER} on API Call {usage_tracker.total_calls + 1} (Attempt {attempt + 1}): {result['error']}")
        sleep(1.0 + attempt * 2) # Exponential backoff

    return {"error": f"Failed after multiple attempts with {API_PROVIDER}: {result['error']}"}, usage_tracker


# --- DATENLADE-FUNKTIONEN ---

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
                    data = json.load(f)[0] 
                    cache[doc_id] = data
            except (json.JSONDecodeError, IndexError, AttributeError):
                print(f"Warning: Dokument {filename} konnte nicht in den Cache geladen werden.")
                
    print(f"Dokumenten-Cache geladen: {len(cache)} Dokumente verfügbar.")
    return cache

# --- AGGREGATIONS- UND SYNTHESELOGIK ---

def process_biomarker_for_synthesis(standard_entry: Dict[str, Any], doc_cache: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any] | None, Dict[str, Any]]:
    """
    Sammelt alle Daten für einen standardisierten Biomarker, ruft das LLM zur Synthese auf 
    und gibt das Endergebnis zurück.
    """
    tracker = BiomarkerUsageTracker()
    standard_name = standard_entry['standard_name']
    source_entries = standard_entry['source_entries']
    
    raw_aggregated_data = []

    # 1. Sammle alle Raw Extracted Data Blocks (reine Python-Logik)
    for entry in source_entries:
        original_name = entry['original_name']
        doc_id = entry['document_source_id']
        
        source_document = doc_cache.get(doc_id)
        if not source_document:
            continue

        extracted_data = source_document.get('extracted_data', {})
        
        # Finde den spezifischen Core Effect, der dem Originalnamen entspricht
        core_effects = extracted_data.get('core_effect_and_quantification', [])
        
        matching_core_effects = [
            effect for effect in core_effects 
            if effect.get('biomarker_name', '').strip() == original_name.strip()
        ]

        # Fuege den vollen Kontext fuer diesen Fund zum Prompt hinzu
        raw_aggregated_data.append({
            "document_source_id": doc_id,
            "original_name": original_name,
            # Die Dokument-weiten Felder (Mechanismus, Implikation, etc.)
            "context_fields": {
                k: v for k, v in extracted_data.items() if k != 'core_effect_and_quantification'
            },
            "matched_core_effects": matching_core_effects
        })

    if not raw_aggregated_data:
        print(f"Warning: Kein Quelldatensatz für '{standard_name}' gefunden.")
        return None, tracker.to_dict()

    # 2. LLM-Synthese-Call
    aggregated_data_str = json.dumps(raw_aggregated_data, indent=2)
    user_query = build_summary_query(standard_name, aggregated_data_str)
    
    synthesis_result, tracker = call_llm_api_internal(user_query, FINAL_BIOMARKER_SUMMARY_SCHEMA, tracker)
    
    if "error" in synthesis_result:
        print(f"!!! FEHLER bei Synthese von '{standard_name}': {synthesis_result['error']}")
        return None, tracker.to_dict()

    # 3. Finales Ergebnis zusammenstellen
    final_entry = {
        "standard_name": standard_name,
        # Die ursprünglichen Quell-Paare (aus Phase 3 Index) beibehalten
        "source_entries": source_entries, 
        # Die LLM-generierte Zusammenfassung
        "biomarker_summary": synthesis_result,
        "metadata": {
            "total_documents_contributed": len(set(e['document_source_id'] for e in raw_aggregated_data)),
            "api_calls_for_synthesis": tracker.total_calls
        }
    }
    
    return final_entry, tracker.to_dict()


def main():
    
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
    
    # 3. PARALLELE VERARBEITUNG DER BIOMARKER (Synthese)
    
    final_data = []
    total_usage = {
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "total_calls": 0,
        "provider": API_PROVIDER, "model": MODELS[API_PROVIDER]
    }
    
    print(f"\nStarte parallele LLM-Synthese für {len(standardized_index)} Biomarker (Max Workers: {MAX_WORKERS}).")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_biomarker_for_synthesis, entry, doc_cache): entry['standard_name']
            for entry in standardized_index
        }
        
        for future in concurrent.futures.as_completed(futures):
            standard_name = futures[future]
            
            try:
                # result ist Tuple: (final_entry | None, usage_dict)
                final_entry, usage_dict = future.result()
            except Exception as e:
                print(f"\nCRITICAL ERROR PROCESSING Biomarker '{standard_name}': {e}")
                continue
            
            # Akkumulierung der Gesamt-Usage
            total_usage['input_tokens'] += usage_dict['input_tokens']
            total_usage['output_tokens'] += usage_dict['output_tokens']
            total_usage['total_tokens'] += usage_dict['total_tokens']
            total_usage['total_calls'] += usage_dict['total_calls']

            if final_entry:
                final_data.append(final_entry)
                
                # Ausgabe der individuellen Kosten pro Biomarker
                print(f"--> SUCCESS: '{standard_name}' ({usage_dict['total_calls']} calls, {usage_dict['total_tokens']} tokens)")
            
    # 4. Speichern der konsolidierten Ergebnisse
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_data, f, indent=2)
        
    # 5. Abschlussbericht
    print("\n=========================================================")
    print(f"✅ PHASE 4: Detail-Aggregation und Synthese abgeschlossen.")
    print(f"  Biomarker erfolgreich synthetisiert: {len(final_data)} von {len(standardized_index)}")
    print(f"  Ergebnisse gespeichert in '{OUTPUT_FILE}'")
    
    print("\n--- GESAMTE TOKEN-NUTZUNG FÜR PHASE 4 ---")
    print(f"Provider: {total_usage['provider']} ({total_usage['model']})")
    print(f"Total API Calls: {total_usage['total_calls']}")
    print(f"Input Tokens (Prompt/Data): {total_usage['input_tokens']}")
    print(f"Output Tokens (Response): {total_usage['output_tokens']}")
    print(f"Total Tokens Used: {total_usage['total_tokens']}")
    print("=========================================================\n")


if __name__ == "__main__":
    main()