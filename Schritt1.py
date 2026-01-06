import json
import os
from time import sleep
from datetime import datetime
from typing import Dict, Any, List, Tuple
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

MOCK_MODE = False
CHUNK_FOLDER = "chunks_gemini_semantic_serial(Hälfte2)"
OUTPUT_DIR_PHASE1 = "Schritt1_Results"


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


# --- SCHEMA DEFINITION & SANITIZATION (Unveraendert) ---

def _sanitize_schema_types(schema: Dict | List | str) -> Dict | List | str:
    """Recursively converts all JSON Schema type definitions to lowercase strings."""
    if isinstance(schema, dict):
        new_schema = {}
        for k, v in schema.items():
            if k == 'type' and isinstance(v, str):
                new_schema[k] = v.lower()
            elif k in ('properties', 'items') and isinstance(v, dict):
                new_schema[k] = _sanitize_schema_types(v)
            elif isinstance(v, dict) or isinstance(v, list):
                 new_schema[k] = _sanitize_schema_types(v)
            else:
                new_schema[k] = v
        return new_schema
    elif isinstance(schema, list):
        return [_sanitize_schema_types(item) for item in schema]
    return schema


# 1. Base Schema (using original definition format)
DRAFT_RESPONSE_SCHEMA = {
  "type": "OBJECT",
  "properties": {
    "title": {
      "type": "STRING",
      "description": "The concise, one-sentence title of the scientific document. If the source title is very long, summarize its essence into one sentence (e.g., 'Predicting anaemia from standard blood testing in developing countries.')."
    },
    "document_source_id": {
      "type": "STRING",
      "description": "The unique ID of the source document (e.g., PMID, DOI)."
    },
    "analysis_date": {
      "type": "STRING",
      "description": "The date when the data analysis was performed."
    },
    "extracted_data": {
      "type": "OBJECT",
      "properties": {
        "document_summary": {
          "type": "STRING",
          "description": "A concise summary of the study's aim and main findings (e.g., 'Investigation of molecular changes following CITT ablation of 4T1 breast carcinoma in mouse models.')."
        },
        "treatment_details": {
          "type": "OBJECT",
          "properties": {
            "therapy_type": {
              "type": "STRING",
              "description": "The specific therapeutic method investigated in the document (e.g., CITT, Radiotherapy, Exercise)."
            },
            "dose_specificity": {
              "type": "STRING",
              "description": "Details regarding the intensity, duration, or specifics of the dose, including any lack of dose comparisons (e.g., 'Partial ablation at 80-90°C; no dose-response comparisons reported.')."
            }
          },
          "required": [
            "therapy_type",
            "dose_specificity"
          ]
        },
        "analyzed_biomarkers": {
          "type": "ARRAY",
          "description": "A list of detailed objects, where each object fully describes an individual biomarker, its effect, and context.",
          "items": {
            "type": "OBJECT",
            "properties": {
              "biomarker_name": {
                    "type": "STRING",
                    "description": "The molecular marker's name (e.g., Cxcl12, CK, Cortisol)."
                },
              "measured_tissue_or_fluid": {
                "type": "STRING",
                "description": "The tissue or body fluid where the marker was quantified (e.g., Blood Serum, Muscle Biopsy, Saliva)."
              },
              "activity_type": {
                "type": "STRING",
                "description": "The type of measurement (e.g., Gene Transcript, Protein Level, Hormone Concentration)."
              },
              "measured_effect": {
                "type": "OBJECT",
                "properties": {
                  "direction_of_change": {
                    "type": "STRING",
                    "description": "The direction of the change after treatment or activity (e.g., higher, lower, unchanged)."
                  },
                  "magnitude_quantification": {
                    "type": "STRING",
                    "description": "The precise quantitative/statistical data, including reference range/normal limits if cited (e.g., 'Normal range 90±10; decreased to 60±7', '2 to 2.5-fold higher (P<0.05)')."
                  }
                },
                "required": [
                  "direction_of_change",
                  "magnitude_quantification"
                ]
              },
              "core_biological_function": {
                "type": "STRING",
                "description": "The fundamental biological role of the biomarker (e.g., mediates inflammation, tissue repair, energy metabolism regulation). This explains WHAT the biomarker does."
              },
              "relevant_activity_context": {
                "type": "STRING",
                "description": "The specific type of activity or condition linked to the change (e.g., Endurance running, High-intensity Interval Training (HIIT), Post-surgical recovery, 4T1 Carcinoma Ablation). This explains the specific WHEN/WHERE."
              },
              "performance_or_health_indicator": {
                "type": "STRING",
                "description": "The derived significance for performance, regeneration, or health status (e.g., 'Indicates muscle damage level', 'Predicts overtraining risk', 'Associated with heightened bone metastasis risk')."
              },
            },
            "required": [
              "biomarker_name",
              "measured_tissue_or_fluid",
              "activity_type",
              "measured_effect",
              "core_biological_function",
              "relevant_activity_context",
              "performance_or_health_indicator",
            ]
          }
        }
      },
      "required": [
        "document_summary",
        "treatment_details",
        "analyzed_biomarkers"
      ]
    }
  },
  "required": [
    "title",
    "document_source_id",
    "analysis_date",
    "extracted_data"
  ]
}

# 2. Final Sanitized Schema Definitions (Used throughout the pipeline)
RESPONSE_SCHEMA = _sanitize_schema_types(DRAFT_RESPONSE_SCHEMA)
CHUNK_RESPONSE_SCHEMA = RESPONSE_SCHEMA["properties"]["extracted_data"]


# --- CORE QUERY BUILDERS (AKTUALISIERT) ---

CHUNK_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a highly specialized Scientific Data Extractor. Analyze the provided article chunk "
    "and extract ALL relevant data points for the new, detailed structure using the provided JSON tool/schema. "
    "Your output MUST strictly conform to the schema defined in the tool call. DO NOT summarize the whole document; "
    "focus only on the specific facts present in the text provided.\n\n"
)

SYSTEM_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a Scientific Review Assistant. Review the collection of structured JSON results from the chunks below. "
    "Synthesize them into a single, cohesive, and non-redundant final JSON object using the provided tool/schema. "
    "Merge the 'analyzed_biomarkers' arrays and write comprehensive summaries for the 'document_summary' and 'treatment_details' objects.\n\n"
)

def build_chunk_analysis_query(document_id: str, chunk_content: str) -> str:
    """
    Builds the user prompt for analyzing a single chunk, explicitly detailing 
    all new required fields in the schema.
    """
        
    integrated_query = f"""
    Document ID: **{document_id}**. 
    
    Extraction Requirements:
    
    A. DOCUMENT OVERVIEW:
    1. Document Summary: Concisely summarize the study's primary aim and the main conclusion.
    2. Treatment Details: Identify the therapeutic/activity method (e.g., CITT, HIIT, Radiotherapy) and provide specifics on the dose, intensity, and duration. Report any dose-response observations.

    B. BIOMARKER DETAILS (For EVERY significant marker found):
    For each biomarker, you MUST find and report the following contextual information exactly matching the detailed schema fields:
    1. Biomarker Name
    2. Measured Tissue/Fluid 
    3. Activity Type (Measurement type)
    4. Measured Effect - Direction 
    5. Measured Effect - Quantification (Precise data/stats, including cited normal limits).
    6. Core Biological Function 
    7. Relevant Activity Context 
    8. Performance/Health Indicator 

    Provided Article Content CHUNK:
    ---
    {chunk_content}
    ---
    """
    return CHUNK_INSTRUCTION_PREFIX + integrated_query

def build_synthesis_query(document_id: str, title: str, chunk_results: list) -> str:
    """
    Builds the user prompt for the final synthesis API call, including instructions,
    and explicitly instructs the LLM to clean the noisy input title.
    """
    
    formatted_results = "\n\n---\n\n".join([json.dumps(res, indent=2) for res in chunk_results])
    
    synthesis_query = f"""
    Raw Input Title (MUST BE CLEANED): **{title}**
    Document ID: {document_id}

    **FINAL SYNTHESIS TASK:** Based on the following extracted chunks and the *Raw Input Title*, create the final, complete JSON structure.
    
    1. **Title Field Synthesis (CRITICAL):** Synthesize the 'title' field by **aggressively cleaning the Raw Input Title** to remove all metadata (journal, authors, affiliations, URLs, dates) and ensure the final 'title' is concise (**MAXIMUM ONE SENTENCE**) and captures the document's central topic.
    2. **Data Synthesis:** Merge the 'analyzed_biomarkers' arrays and write comprehensive summaries for 'document_summary' and 'treatment_details'.
    
    Structured Data from Chunks (to be synthesized):
    ---
    {formatted_results}
    ---
    
    Please use the provided output schema to synthesize this data according to the merging rules in the instructions.
    """
    return SYSTEM_INSTRUCTION_PREFIX + synthesis_query


# --- PROVIDER-SPECIFIC API CALLERS (Hinzufuegen der usage-Uebergabe) ---

def call_gemini_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Handles API call using raw requests for the Gemini API endpoint."""
    usage_metadata = {}

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
        
        # --- TOKEN TRACKING (Gemini) ---
        usage_metadata = result.get('usageMetadata', {})
        
        if json_text:
            return json.loads(json_text), usage_metadata
        else:
            return {"error": "Gemini API returned empty content."}, usage_metadata
    
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP Error: {e}"
        if hasattr(response, 'text'):
            error_msg += f" | Response: {response.text}"
        return {"error": error_msg}, usage_metadata
    except json.JSONDecodeError:
        return {"error": "Gemini API returned unparseable JSON."}, usage_metadata

def call_claude_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Handles API call using the Anthropic SDK with tool use."""
    usage_metadata = {}

    if not ANTHROPIC_CLIENT:
        return {"error": "Anthropic client not initialized. Library missing or key invalid."}, usage_metadata
        
    if response_schema.get("type", "").lower() == "object":
        claude_input_schema = response_schema
        tool_name = "extract_scientific_data"
    elif response_schema.get("type", "").lower() == "array":
        claude_input_schema = {
            "type": "object",
            "properties": {
                "data_array": response_schema
            },
            "required": ["data_array"]
        }
        tool_name = "consolidate_data"
    else:
        claude_input_schema = response_schema
        tool_name = "generic_tool"

    tool_schema = {
        "name": tool_name,
        "description": "Extract and synthesize scientific data from the provided text according to the specific criteria.",
        "input_schema": claude_input_schema
    }
    max_tokens = 4096

    try:
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODELS["CLAUDE"],
            max_tokens=max_tokens, 
            tools=[tool_schema],
            messages=[{"role": "user", "content": user_query}]
        )
        
        # --- TOKEN TRACKING (Claude) ---
        usage = response.usage
        usage_metadata = {
            'input_tokens': usage.input_tokens, 
            'output_tokens': usage.output_tokens,
            'total_tokens': usage.input_tokens + usage.output_tokens
        }
        # -------------------------------

        if response.stop_reason == "tool_use":
            tool_calls = [c for c in response.content if c.type == "tool_use"]
            if tool_calls and tool_calls[0].name == tool_schema["name"]:
                raw_input = tool_calls[0].input
                
                if response_schema.get("type", "").lower() == "array":
                    return raw_input.get("data_array", {"error": "Failed to unwrap Claude ARRAY response."}), usage_metadata
                else:
                    return raw_input, usage_metadata

            else:
                return {"error": "Claude API failed to return expected tool use call."}, usage_metadata
        else:
            return {"error": f"Claude API did not return structured tool output. Stop reason: {response.stop_reason}"}, usage_metadata

    except (APIError, APIStatusError) as e:
        error_msg = f"Claude API Error ({e.status_code}): {e.response.json().get('error', {}).get('message', 'Unknown API Error')}"
        return {"error": error_msg}, usage_metadata
    except Exception as e:
        return {"error": f"General Claude SDK Error: {e}"}, usage_metadata

def call_openai_api(document_id: str, user_query: str, response_schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Handles API call using the OpenAI SDK with function calling (tools)."""
    usage_metadata = {}

    if not OPENAI_CLIENT:
        return {"error": "OpenAI client not initialized. Library missing or key invalid."}, usage_metadata
        
    sanitized_schema = response_schema
    
    if response_schema.get("type", "").lower() == "array":
        tool_name = "consolidate_data"
    else:
        tool_name = "extract_scientific_data"
    
    tool_schema = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": "Consolidate or extract scientific data according to the criteria.",
            "parameters": sanitized_schema 
        }
    }

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=MODELS["OPENAI"],
            messages=[{"role": "user", "content": user_query}],
            tools=[tool_schema],
            tool_choice={"type": "function", "function": {"name": tool_name}}
        )
        
        # --- TOKEN TRACKING (OpenAI) ---
        usage = response.usage
        usage_metadata = {
            'input_tokens': usage.prompt_tokens, 
            'output_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens
        }
        # -------------------------------
        
        # Parse the structured tool call
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == tool_name:
                return json.loads(tool_call.function.arguments), usage_metadata
        
        return {"error": "OpenAI API failed to return structured function call."}, usage_metadata
    
    except OpenAI_APIError as e:
        error_msg = f"OpenAI API Error ({e.status_code}): {e.message}"
        return {"error": error_msg}, usage_metadata
    except Exception as e:
        return {"error": f"General OpenAI SDK Error: {e}"}, usage_metadata

# --- UNIFIED API CALL HANDLER ---

def call_llm_api_internal(document_id: str, user_query: str, response_schema: Dict[str, Any], usage_tracker: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Routes the API call to the selected provider with exponential backoff and tracks usage.
    Gibt Ergebnis und Usage-Metriken (fuer diesen EINEN Call) zurueck.
    """
    provider_map = {
        "GEMINI": call_gemini_api,
        "CLAUDE": call_claude_api,
        "OPENAI": call_openai_api,
    }
    
    if API_PROVIDER not in provider_map:
        return {"error": f"Invalid API_PROVIDER selected: {API_PROVIDER}"}, {}
        
    api_caller = provider_map[API_PROVIDER]
    
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        
        # API-Caller gibt Result und usage_metadata zurueck
        result, usage_metadata = api_caller(document_id, user_query, response_schema)
        
        if "error" not in result:
            # Token zur Gesamt-Document-Nutzung addieren
            usage_tracker['input_tokens'] += usage_metadata.get('input_tokens', 0)
            usage_tracker['output_tokens'] += usage_metadata.get('output_tokens', 0)
            usage_tracker['total_tokens'] += usage_metadata.get('total_tokens', 0)
            usage_tracker['total_calls'] += 1
            usage_tracker['provider'] = API_PROVIDER
            usage_tracker['model'] = MODELS[API_PROVIDER]

            return result, usage_tracker
        
        # Log specific errors from the provider's wrapper function
        print(f"Error from {API_PROVIDER} on attempt {attempt + 1}: {result['error']}")

        if attempt < max_retries - 1:
            sleep(retry_delay)
            retry_delay *= 2
        
    return {"error": f"Failed to process {document_id} after {max_retries} attempts with {API_PROVIDER}."}, usage_tracker


# --- GENERALIZED PIPELINE FUNCTIONS ---

def load_document_chunks() -> Dict[str, Dict[str, Any]]:
    """Loads a single JSON file per document ID, extracts metadata and returns the list of chunks."""
    if not os.path.isdir(CHUNK_FOLDER):
        print(f"Error: Directory '{CHUNK_FOLDER}' not found. Please create it and place your files inside.")
        return {}

    all_files = os.listdir(CHUNK_FOLDER)
    documents_to_process = {}

    for filename in all_files:
        if filename.endswith('.json'):
            file_path = os.path.join(CHUNK_FOLDER, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)

                # Extract key metadata
                doc_id = doc_data.get('pmid') or doc_data.get('pmcid') or doc_data.get('doi') or filename.split('_')[0]
                
                chunks_list = doc_data.get('chunks', [])
                
                # Get the title (or default)
                first_chunk_text = chunks_list[0].get('text', '') if chunks_list else ''
                title = first_chunk_text.split('\n')[0].strip() or f"Document {doc_id} (Title not extracted)"

                if not chunks_list:
                    print(f"Warning: Skipping {filename}. Contains no 'chunks'.")
                    continue

                documents_to_process[doc_id] = {
                    'title': title,
                    'all_chunks': chunks_list # Store the list of chunk objects
                }
                
            except json.JSONDecodeError:
                print(f"Warning: Skipping {filename}. Not a valid JSON file.")
            except Exception as e:
                print(f"Warning: Could not read or process {filename}. Error: {e}")

    return documents_to_process

def analyze_chunk(document_id: str, chunk_content: str, usage_tracker: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Phase 1a: Calls the unified API to analyze a single chunk."""
    if MOCK_MODE:
        return {"error": "Mocking not fully implemented."}, usage_tracker

    # Sanitize the chunk content
    sanitized_content = chunk_content.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        
    user_query = build_chunk_analysis_query(document_id, sanitized_content)
    
    # Der innere Aufruf gibt das Resultat und die akkumulierten Usage-Metriken zurueck
    return call_llm_api_internal(
        document_id=document_id,
        user_query=user_query,
        response_schema=CHUNK_RESPONSE_SCHEMA,
        usage_tracker=usage_tracker
    )

def synthesize_results(doc_id: str, title: str, chunk_results: List[Dict[str, Any]], usage_tracker: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Phase 1b: Calls the unified API to synthesize all chunk results into the final document schema."""
    
    if MOCK_MODE:
        return {"error": "Mocking not fully implemented."}, usage_tracker

    user_query = build_synthesis_query(doc_id, title, chunk_results)
    
    # Der innere Aufruf gibt das Resultat und die akkumulierten Usage-Metriken zurueck
    return call_llm_api_internal(
        document_id=doc_id,
        user_query=user_query,
        response_schema=RESPONSE_SCHEMA,
        usage_tracker=usage_tracker
    )


# --- ORCHESTRATION & MAIN (Parallelisiert) ---

def process_document(doc_id: str, doc_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Hauptverarbeitungsfunktion fuer ein Dokument, die parallelisiert wird.
    Gibt die Dokumenten-ID, das Analyse-Resultat und die Token-Metriken zurueck.
    """
    
    # Lokaler Tracker, der die Usage fuer dieses EINE Dokument akkumuliert
    local_usage_tracker = {
        "provider": "", "model": "", "input_tokens": 0, "output_tokens": 0,
        "total_tokens": 0, "total_calls": 0
    }
    
    all_chunk_results = []
    
    # PHASE 1a: ITERATIVE CHUNK ANALYSIS
    print(f"    -> Starting Chunk Analysis for {doc_id} ({len(doc_data['all_chunks'])} chunks) using {API_PROVIDER}...")
    for i, chunk in enumerate(doc_data['all_chunks']):
        chunk_content = chunk.get('text', '')
        
        if not chunk_content.strip():
             # print(f"    -> Warning: Chunk {i+1} is empty, skipping.")
             continue

        # WICHTIG: analyze_chunk aktualisiert local_usage_tracker durch Referenz
        chunk_result, local_usage_tracker = analyze_chunk(doc_id, chunk_content, local_usage_tracker)
        
        if "error" in chunk_result:
            print(f"    -> FAILED on Chunk {i+1} for {doc_id}. Stopping analysis.")
            return doc_id, chunk_result, local_usage_tracker
            
        all_chunk_results.append(chunk_result)
        sleep(0.1) # Reduzierte Pause, da threadsicher

    if not all_chunk_results:
        return doc_id, {"error": "No non-empty chunks were successfully processed."}, local_usage_tracker
        
    # PHASE 1b: FINAL SYNTHESIS
    print(f"    -> Synthesizing final document result for {doc_id}...")
    final_analysis, local_usage_tracker = synthesize_results(doc_id, doc_data['title'], all_chunk_results, local_usage_tracker) 
    
    if "error" in final_analysis:
        print(f"    -> FAILED Synthesis for {doc_id}: {final_analysis['error']}")
    
    return doc_id, final_analysis, local_usage_tracker

def main():
    """Main function to iterate over documents and process chunks in parallel."""
    
    # Globaler Tracker zur Akkumulation aller Tokens
    TOTAL_TOKEN_USAGE = {
        "input_tokens": 0, "output_tokens": 0,
        "total_tokens": 0, "total_calls": 0
    }
    
    if API_PROVIDER not in MODELS:
        print(f"Configuration Error: Invalid API_PROVIDER '{API_PROVIDER}' selected.")
        return

    if not os.path.exists(OUTPUT_DIR_PHASE1):
        os.makedirs(OUTPUT_DIR_PHASE1)
        print(f"Created output directory: '{OUTPUT_DIR_PHASE1}'")

    documents_to_process = load_document_chunks()
    if not documents_to_process:
        print("No documents were loaded or found. Exiting.")
        return

    success_count = 0
    
    # --- PARALLELE VERARBEITUNG START ---
    MAX_WORKERS = 8
    
    print(f"\nStarting parallel analysis of {len(documents_to_process)} documents using {API_PROVIDER} (Max Workers: {MAX_WORKERS}).")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Erstelle Future-Objekte
        futures = {
            executor.submit(process_document, doc_id, data): doc_id 
            for doc_id, data in documents_to_process.items()
        }

        # Verarbeite die Ergebnisse, sobald sie fertig sind (as_completed)
        for future in concurrent.futures.as_completed(futures):
            doc_id = futures[future]
            
            try:
                # Hole die Ergebnisse und die lokale Usage
                doc_id, analysis_result, doc_usage = future.result()
            except Exception as e:
                print(f"\nCRITICAL ERROR PROCESSING {doc_id}: {e}")
                continue
            
            # Token-Nutzung zur Gesamt-Statistik addieren
            TOTAL_TOKEN_USAGE['input_tokens'] += doc_usage['input_tokens']
            TOTAL_TOKEN_USAGE['output_tokens'] += doc_usage['output_tokens']
            TOTAL_TOKEN_USAGE['total_tokens'] += doc_usage['total_tokens']
            TOTAL_TOKEN_USAGE['total_calls'] += doc_usage['total_calls']

            if "error" not in analysis_result and analysis_result.get('extracted_data'):
                
                analysis_result['document_source_id'] = doc_id
                analysis_result['analysis_date'] = datetime.now().strftime("%Y-%m-%d")
                analysis_result['title'] = documents_to_process[doc_id]['title']
                
                output_filename = os.path.join(OUTPUT_DIR_PHASE1, f"{doc_id}_analysis.json")
                with open(output_filename, "w", encoding='utf-8') as f:
                    json.dump([analysis_result], f, indent=2) 
                
                print(f"\n✅ Successfully analyzed and saved {doc_id} to '{output_filename}'.")
                success_count += 1
                
                # Token-Nutzung für dieses Dokument ausgeben
                print("--- TOKEN USAGE SUMMARY FOR DOCUMENT ---")
                print(f"Provider: {doc_usage['provider']} ({doc_usage['model']})")
                print(f"Total API Calls: {doc_usage['total_calls']}")
                print(f"Input Tokens (Prompt/Data): {doc_usage['input_tokens']}")
                print(f"Output Tokens (Response): {doc_usage['output_tokens']}")
                print(f"Total Tokens Used: {doc_usage['total_tokens']}")
                print("----------------------------------------")
                
            else:
                print(f"\n❌ Failed analysis for {doc_id}: {analysis_result.get('error', 'Unknown Error during processing.')}")

    # --- ENDE DER PARALLELEN VERARBEITUNG ---
    
    print(f"\nPipeline Phase 1 completed. Successfully processed {success_count} documents.")

    # Gesamte Token-Nutzung ausgeben
    print("\n\n=============== OVERALL COST SUMMARY ===============")
    print(f"Total Documents Processed Successfully: {success_count}")
    print(f"Provider: {API_PROVIDER} ({MODELS[API_PROVIDER]})")
    print(f"TOTAL API Calls: {TOTAL_TOKEN_USAGE['total_calls']}")
    print(f"TOTAL Input Tokens: {TOTAL_TOKEN_USAGE['input_tokens']}")
    print(f"TOTAL Output Tokens: {TOTAL_TOKEN_USAGE['output_tokens']}")
    print(f"GRAND TOTAL Tokens Used: {TOTAL_TOKEN_USAGE['total_tokens']}")
    print("====================================================\n")


if __name__ == "__main__":
    main()