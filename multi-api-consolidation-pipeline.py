import json
import os
from time import sleep
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv()

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

# --- GLOBAL METRICS TRACKING ---
TOKEN_USAGE = {
    "provider": "",
    "model": "",
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "total_calls": 0,
}

# --- CONFIGURATION (The Switch) ---

# Choose your provider here for consolidation: "GEMINI", "CLAUDE", or "OPENAI"
API_PROVIDER = "GEMINI" 

INPUT_FOLDER = "semantic_serial_results3" # Ordner, der die Ergebnisse aus Phase 1 enthält
OUTPUT_FILE = "final_biomarker_compendium6.json"

# --- API KEYS AND MODEL MAPPING ---
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
ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=API_KEYS["CLAUDE"]) if anthropic else None
OPENAI_CLIENT = OpenAI(api_key=API_KEYS["OPENAI"]) if openai else None

# The base URL structure for the raw Gemini API call
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['GEMINI']}:generateContent?key={API_KEYS['GEMINI']}"


# --- SCHEMA DEFINITION (Final Consolidation Schema) ---

FINAL_BIOMARKER_SCHEMA = {
  "description": "Final consolidated list of all biomarkers, grouped by molecule name, detailing the relationship to different sports/workloads.",
  "type": "array", 
  "items": {
    "type": "object", 
    "properties": {
      "biomarker_name": {
        "type": "string", 
        "description": "The specific name of the biomarker (e.g., IgA, hsCRP, Neutrophils, ACTH)."
      },
      "overall_summary": {
        "type": "string", 
        "description": "A brief summary of the biomarker's role across all analyzed studies (e.g., Primary marker for immunosuppression and stress-induced inflammation)."
      },
      "findings_by_activity": {
        "type": "array", 
        "description": "Detailed findings for this biomarker across different activity contexts.",
        "items": {
          "type": "object", 
          "properties": {
            "source_document_id": {
              "type": "string", 
              "description": "The original document ID where this finding was extracted."
            },
            "activity_context": {
              "type": "string", 
              "description": "The specific sport or workload tested (e.g., Endurance Running P2-EHS, LIPE, Heavy Labor/Slaughterhouse)."
            },
            "effect_and_magnitude": {
              "type": "string", 
              "description": "The direction and magnitude of change (e.g., Increased significantly (p<0.01), logFC=1.27 reduction, No substantial change)."
            },
            "clinical_implication": {
              "type": "string", 
              "description": "The health or performance consequence (e.g., Protective anti-inflammatory benefit, High risk of infection, Low sensitivity biomarker for EIGS)."
            }
          },
          "required": ["source_document_id", "activity_context", "effect_and_magnitude", "clinical_implication"]
        }
      }
    },
    "required": ["biomarker_name", "overall_summary", "findings_by_activity"]
  }
}


# --- API CONSOLIDATION INSTRUCTION ---

SYSTEM_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a Scientific Data Fusion Specialist. Your task is to process a list of structured biomarker analyses "
    "(from multiple documents) and consolidate them into a single, comprehensive, thematic list. "
    "Group all findings by the 'biomarker_name' field. The output MUST strictly conform to the provided JSON Schema (a root ARRAY structure). "
    "You must return the final consolidated structure as a single JSON array.\n\n"
)

def build_consolidation_query(intermediate_data: List[Dict[str, Any]]) -> str:
    """Builds the user prompt for the consolidation task."""
    
    data_for_prompt = json.dumps(intermediate_data, indent=2)
    
    user_query = (
        "Consolidate the following intermediate biomarker data (extracted from multiple scientific articles) "
        "into the final required JSON structure. Group all findings by the unique biomarker name. "
        "The overall_summary should concisely explain the biomarker's general role in physical performance/stress.\n\n"
        "--- INTERMEDIATE DATA ---\n"
        f"{data_for_prompt}"
        "\n--- END OF DATA ---"
    )
    return SYSTEM_INSTRUCTION_PREFIX + user_query


# --- PROVIDER-SPECIFIC API CALLERS ---

def call_gemini_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Handles API call using raw requests for the Gemini API endpoint."""
    global TOKEN_USAGE

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
        
        # --- TOKEN TRACKING (Gemini FIX) ---
        usage_metadata = result.get('usageMetadata', {})
        TOKEN_USAGE['provider'] = "GEMINI"
        TOKEN_USAGE['model'] = MODELS["GEMINI"]
        TOKEN_USAGE['input_tokens'] += usage_metadata.get('promptTokenCount', 0)
        TOKEN_USAGE['output_tokens'] += usage_metadata.get('candidatesTokenCount', 0)
        TOKEN_USAGE['total_tokens'] += usage_metadata.get('totalTokenCount', 0)
        TOKEN_USAGE['total_calls'] += 1
        # -----------------------------------

        if json_text:
            return json.loads(json_text)
        else:
            return {"error": "Gemini API returned empty content."}
    
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP Error: {e}"
        if hasattr(response, 'text'):
            error_msg += f" | Response: {response.text}"
        return {"error": error_msg}
    except json.JSONDecodeError:
        return {"error": "Gemini API returned unparseable JSON."}

def call_claude_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles API call using the Anthropic SDK with tool use.
    
    Note: Uses a wrapper object for ARRAY root schemas to satisfy Claude's 'Input should be object' validation.
    """
    global TOKEN_USAGE
    
    if not ANTHROPIC_CLIENT:
        return {"error": "Anthropic client not initialized. Library missing or key invalid."}
        
    # --- FIX FÜR CLAUDE ARRAY SCHEMA ---
    if response_schema.get("type", "").lower() == "array":
        claude_input_schema = {
            "type": "object",
            "properties": {
                "consolidated_list": response_schema
            },
            "required": ["consolidated_list"]
        }
        tool_name = "consolidate_data"
    else:
        # Dies wird in Phase 2 nicht verwendet, aber für die Vollständigkeit
        claude_input_schema = response_schema
        tool_name = "generic_tool"
    # -----------------------------------

    tool_schema = {
        "name": tool_name,
        "description": "Consolidate multiple structured biomarker findings into a single thematic array.",
        "input_schema": claude_input_schema
    }
    max_tokens = 8192 

    try:
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODELS["CLAUDE"],
            max_tokens=max_tokens, 
            tools=[tool_schema],
            messages=[{"role": "user", "content": user_query}]
        )
        
        # --- TOKEN TRACKING (Claude) ---
        usage = response.usage
        TOKEN_USAGE['provider'] = "CLAUDE"
        TOKEN_USAGE['model'] = MODELS["CLAUDE"]
        TOKEN_USAGE['input_tokens'] += usage.input_tokens
        TOKEN_USAGE['output_tokens'] += usage.output_tokens
        TOKEN_USAGE['total_tokens'] += usage.input_tokens + usage.output_tokens
        TOKEN_USAGE['total_calls'] += 1
        # -------------------------------

        if response.stop_reason == "tool_use":
            tool_calls = [c for c in response.content if c.type == "tool_use"]
            if tool_calls and tool_calls[0].name == tool_schema["name"]:
                
                raw_input = tool_calls[0].input
                
                # Unwrap the result if we used the array wrapper 
                if response_schema.get("type", "").lower() == "array":
                    return raw_input.get("consolidated_list", {"error": "Failed to unwrap Claude ARRAY response."})
                else:
                    return raw_input

            else:
                return {"error": "Claude API failed to return expected tool use call."}
        else:
            return {"error": f"Claude API did not return structured tool output. Stop reason: {response.stop_reason}"}

    except (APIError, APIStatusError) as e:
        error_msg = f"Claude API Error ({e.status_code}): {e.response.json().get('error', {}).get('message', 'Unknown API Error')}"
        return {"error": error_msg}
    except Exception as e:
        return {"error": f"General Claude SDK Error: {e}"}

def call_openai_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Handles API call using the OpenAI SDK with function calling (tools)."""
    global TOKEN_USAGE
    
    if not OPENAI_CLIENT:
        return {"error": "OpenAI client not initialized. Library missing or key invalid."}
        
    # --- Schema Sanitization for OpenAI ---
    def sanitize_schema_types(schema):
        # Recursively change uppercase 'OBJECT', 'ARRAY', 'STRING' to lowercase 
        if isinstance(schema, dict):
            new_schema = {}
            for k, v in schema.items():
                if k == 'type' and isinstance(v, str):
                    new_schema[k] = v.lower()
                elif k in ('properties', 'items') and isinstance(v, dict):
                    new_schema[k] = sanitize_schema_types(v)
                elif isinstance(v, dict):
                     new_schema[k] = sanitize_schema_types(v)
                else:
                    new_schema[k] = v
            return new_schema
        elif isinstance(schema, list):
            return [sanitize_schema_types(item) for item in schema]
        return schema

    sanitized_schema = response_schema # Schema ist bereits kleingeschrieben
    
    # OpenAI requires the JSON Schema definition nested under 'parameters'
    tool_schema = {
        "type": "function",
        "function": {
            "name": "consolidate_data",
            "description": "Consolidate multiple structured biomarker findings into a single thematic array.",
            "parameters": sanitized_schema # Pass the full ARRAY schema here
        }
    }

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=MODELS["OPENAI"],
            messages=[{"role": "user", "content": user_query}],
            tools=[tool_schema],
            tool_choice={"type": "function", "function": {"name": "consolidate_data"}}
        )
        
        # --- TOKEN TRACKING (OpenAI) ---
        usage = response.usage
        TOKEN_USAGE['provider'] = "OPENAI"
        TOKEN_USAGE['model'] = MODELS["OPENAI"]
        TOKEN_USAGE['input_tokens'] += usage.prompt_tokens
        TOKEN_USAGE['output_tokens'] += usage.completion_tokens
        TOKEN_USAGE['total_tokens'] += usage.total_tokens
        TOKEN_USAGE['total_calls'] += 1
        # -------------------------------
        
        # Parse the structured tool call
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "consolidate_data":
                return json.loads(tool_call.function.arguments)
        
        return {"error": "OpenAI API failed to return structured function call."}
    
    except OpenAI_APIError as e:
        error_msg = f"OpenAI API Error ({e.status_code}): {e.message}"
        return {"error": error_msg}
    except Exception as e:
        return {"error": f"General OpenAI SDK Error: {e}"}

# --- UNIFIED API CALL HANDLER (Unchanged) ---

def call_llm_api_internal(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Routes the API call to the selected provider with exponential backoff.
    """
    provider_map = {
        "GEMINI": call_gemini_api,
        "CLAUDE": call_claude_api,
        "OPENAI": call_openai_api,
    }
    
    if API_PROVIDER not in provider_map:
        return {"error": f"Invalid API_PROVIDER selected: {API_PROVIDER}"}
        
    api_caller = provider_map[API_PROVIDER]
    
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            result = api_caller(document_id, user_query, response_schema)
            
            if "error" not in result:
                return result
            
            # Log specific errors from the provider's wrapper function
            print(f"Error from {API_PROVIDER} on attempt {attempt + 1}: {result['error']}")
            
        except Exception as e:
            # Catch unexpected errors outside the provider wrapper
            print(f"Unhandled pipeline error on attempt {attempt + 1}: {e}")
            
        if attempt < max_retries - 1:
            sleep(retry_delay)
            retry_delay *= 2
        
    return {"error": f"Failed to process {document_id} after {max_retries} attempts with {API_PROVIDER}."}


# --- PHASE 2 CORE LOGIC (Unchanged) ---

def load_all_intermediate_data(directory_path: str) -> List[Dict[str, Any]] | None:
    """
    Loads and combines all JSON files from the specified folder into a single list.
    """
    if not os.path.isdir(directory_path):
        print(f"Error: Das Eingabeverzeichnis '{directory_path}' wurde nicht gefunden.")
        return None

    all_results = []
    print(f"Suche nach JSON-Dateien in '{directory_path}'...")
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        all_results.extend(data)
                    elif isinstance(data, dict):
                        all_results.append(data)
                    
                    print(f"  + Datei geladen: {filename}")
            except json.JSONDecodeError:
                print(f"  - Fehler: Datei {filename} enthält ungültiges JSON und wird ignoriert.")
            except Exception as e:
                print(f"  - Fehler beim Lesen von {filename}: {e}")

    if not all_results:
        print("Keine gültigen JSON-Ergebnisse gefunden.")
        return None
        
    print(f"\nGesamtzahl der geladenen Dokumentenanalysen: {len(all_results)}")
    return all_results


def consolidate_data(intermediate_data: List[Dict[str, Any]]):
    """Sends the extracted data to the selected LLM for fusion and structuring."""
    
    # 1. Erstelle den Prompt
    user_query = build_consolidation_query(intermediate_data)
    
    print(f"Sende Konsolidierungsanfrage an {API_PROVIDER}...")

    # 2. Führe die LLM-Anfrage durch
    consolidation_id = f"CONSOLIDATION_TASK_{datetime.now().strftime('%Y%m%d')}"
    
    final_compendium = call_llm_api_internal(
        document_id=consolidation_id,
        user_query=user_query,
        response_schema=FINAL_BIOMARKER_SCHEMA
    )
    
    return final_compendium

def main():
    """Main function for the consolidation pipeline (Phase 2)."""
    
    # 1. Lade die Ergebnisse aller JSON-Dateien aus dem Ordner
    intermediate_data = load_all_intermediate_data(INPUT_FOLDER)
    if not intermediate_data:
        return
        
    # 2. Führe die Konsolidierung durch (API-Aufruf)
    final_compendium = consolidate_data(intermediate_data)
    
    # 3. Speichere das Endergebnis
    if isinstance(final_compendium, list):
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            json.dump(final_compendium, f, indent=2)
        print(f"\n✅ SUCCESS: Final compendium (all biomarkers grouped) saved to '{OUTPUT_FILE}'.")
        print(f"   Total unique biomarkers extracted: {len(final_compendium)}")
    else:
        print(f"\n❌ FAILURE: Final data structure could not be generated. Error: {final_compendium.get('error', 'Unknown error.')}")

    # 4. Gebe die Token-Nutzung aus
    print("\n--- TOKEN USAGE SUMMARY ---")
    print(f"Provider: {TOKEN_USAGE['provider']} ({TOKEN_USAGE['model']})")
    print(f"Input Tokens (Prompt/Data): {TOKEN_USAGE['input_tokens']}")
    print(f"Output Tokens (Response): {TOKEN_USAGE['output_tokens']}")
    print(f"Total Tokens Used: {TOKEN_USAGE['total_tokens']}")
    print("---------------------------\n")

if __name__ == "__main__":
    main()