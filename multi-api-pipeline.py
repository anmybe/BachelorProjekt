import json
import os
from time import sleep
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv()

# --- LLM API IMPORTS ---
# requests is used for the raw Gemini API endpoint
import requests 

# Anthropic and OpenAI SDKs are used for those providers
try:
    import anthropic
    from anthropic import APIError, APIStatusError # Import specific Anthropic errors
except ImportError:
    anthropic = None
    APIError = type('APIError', (Exception,), {})
    APIStatusError = type('APIStatusError', (Exception,), {})

try:
    from openai import OpenAI
    openai = True  # Flag to indicate successful import
except ImportError:
    openai = None
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None 
# --- END IMPORTS ---

# --- GLOBAL METRICS TRACKING ---
def initialize_token_usage():
    global TOKEN_USAGE
    TOKEN_USAGE = {
        "provider": "",
        "model": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "total_calls": 0,
    }

initialize_token_usage()

# --- CONFIGURATION (The Switch) ---

# Choose your provider here: "GEMINI", "CLAUDE", or "OPENAI"
API_PROVIDER = "GEMINI" 

MOCK_MODE = False
CHUNK_FOLDER = "chunks_gemini_semantic_serial3"
OUTPUT_DIR_PHASE1 = "semantic_serial_results4"

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
# Initialize SDK clients only if the provider is selected and the library is imported

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=API_KEYS["CLAUDE"]) if anthropic else None
OPENAI_CLIENT = OpenAI(api_key=API_KEYS["OPENAI"]) if OpenAI else None

# The base URL structure for the raw Gemini API call
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['GEMINI']}:generateContent?key={API_KEYS['GEMINI']}"


# --- SCHEMA DEFINITIONS (Unchanged) ---
# ... (RESPONSE_SCHEMA and CHUNK_RESPONSE_SCHEMA remain the same) ...

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "document_source_id": {"type": "STRING"},
        "analysis_date": {"type": "STRING"},
        "extracted_data": {
            "type": "OBJECT",
            "properties": {
                "core_effect_and_quantification": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "biomarker_name": {"type": "STRING"},
                            "activity_context": {"type": "STRING"},
                            "direction_of_change": {"type": "STRING"},
                            "magnitude_quantification": {"type": "STRING"}
                        },
                        "required": ["biomarker_name", "activity_context", "direction_of_change", "magnitude_quantification"]
                    }
                },
                "molecular_mechanism_and_relationship": {
                    "type": "OBJECT",
                    "properties": {
                        "activity_type_context": {"type": "STRING"},
                        "mechanism_description": {"type": "STRING"},
                        "related_biomarkers": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": ["activity_type_context", "mechanism_description", "related_biomarkers"]
                },
                "dose_intensity_and_specificity": {
                    "type": "OBJECT",
                    "properties": {
                        "dose_comparison_summary": {"type": "STRING"},
                        "specificity_finding": {"type": "STRING"}
                    },
                    "required": ["dose_comparison_summary", "specificity_finding"]
                },
                "clinical_implication_and_population": {
                    "type": "OBJECT",
                    "properties": {
                        "target_population": {"type": "STRING"},
                        "health_implication": {"type": "STRING"},
                        "risk_classification": {"type": "STRING"}
                    },
                    "required": ["target_population", "health_implication", "risk_classification"]
                },
                "biomarker_reliability_and_future_focus": {
                    "type": "OBJECT",
                    "properties": {
                        "reliability_assessment": {"type": "STRING"},
                        "recommended_alternatives": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": ["reliability_assessment", "recommended_alternatives"]
                }
            },
            "required": ["core_effect_and_quantification", "molecular_mechanism_and_relationship", "dose_intensity_and_specificity", "clinical_implication_and_population", "biomarker_reliability_and_future_focus"]
        }
    },
    "required": ["title", "document_source_id", "analysis_date", "extracted_data"]
}

CHUNK_RESPONSE_SCHEMA = RESPONSE_SCHEMA["properties"]["extracted_data"]


# --- PROMPT INSTRUCTIONS (Unchanged) ---

CHUNK_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a highly specialized Scientific Data Extractor. Analyze the provided article chunk "
    "and extract ALL relevant data points for the five required categories using the provided JSON tool/schema. "
    "Your output MUST strictly conform to the schema defined in the tool call. DO NOT summarize the whole document; "
    "focus only on the specific facts present in the text provided.\n\n"
)

SYSTEM_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a Scientific Review Assistant. Review the collection of structured JSON results from the chunks below. "
    "Synthesize them into a single, cohesive, and non-redundant final JSON object using the provided tool/schema. "
    "Merge array fields and write comprehensive summaries for object fields.\n\n"
)


# --- CORE QUERY BUILDERS (Unchanged) ---

def build_chunk_analysis_query(document_id: str, chunk_content: str) -> str:
    """Builds the user prompt for analyzing a single chunk, including instructions."""
    integrated_query = f"""
    Document ID: **{document_id}**. 
    
    Extraction Requirements:
    1. Core Effect & Quantification: Identify all primary **biomarkers** that showed a **significant change**. List the **biomarker name**, the **activity/disease context**, the **direction of change**, and the **magnitude/quantification** (e.g., logFC, p-value, AUC, percentage).
    2. Molecular Mechanism & Relationship: Describe the authors' proposed **molecular mechanism** linking the **activity/disease type** to the **biomarker** change. List **related biomarkers**.
    3. Dose/Intensity and Specificity: Analyze any **dose-response** effect, comparison between **high vs. low intensity/stage**, or **specificity** finding.
    4. Clinical Implication & Population: Note the **target population**, the **health implication**, and classify the finding (e.g., **protective benefit, adverse risk, diagnostic utility**).
    5. Biomarker Reliability & Future Focus: Evaluate the **sensitivity/reliability** and list any **recommended alternative biomarkers/assays**.

    Provided Article Content CHUNK:
    ---
    {chunk_content}
    ---
    """
    return CHUNK_INSTRUCTION_PREFIX + integrated_query

def build_synthesis_query(document_id: str, title: str, chunk_results: list) -> str:
    """Builds the user prompt for the final synthesis API call, including instructions."""
    
    formatted_results = "\n\n---\n\n".join([json.dumps(res, indent=2) for res in chunk_results])
    
    synthesis_query = f"""
    Document: **{title}** (ID: {document_id}).
    
    Structured Data from Chunks (to be synthesized):
    ---
    {formatted_results}
    ---
    
    Please use the provided output schema to synthesize this data according to the merging rules in the instructions.
    """
    return SYSTEM_INSTRUCTION_PREFIX + synthesis_query


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
        
        # --- TOKEN TRACKING (Gemini) ---
        usage_metadata = result.get('usageMetadata', {})
        TOKEN_USAGE['provider'] = "GEMINI"
        TOKEN_USAGE['model'] = MODELS["GEMINI"]
        TOKEN_USAGE['input_tokens'] += usage_metadata.get('promptTokenCount', 0)
        TOKEN_USAGE['output_tokens'] += usage_metadata.get('candidatesTokenCount', 0)
        TOKEN_USAGE['total_tokens'] += usage_metadata.get('totalTokenCount', 0)
        TOKEN_USAGE['total_calls'] += 1
        # -------------------------------

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
    
    Note: Schema handling is simplified as global schema is already lowercased.
    """
    global TOKEN_USAGE
    
    if not ANTHROPIC_CLIENT:
        return {"error": "Anthropic client not initialized. Library missing or key invalid."}
        
    # --- FIX FOR CLAUDE OBJECT/ARRAY ROOT SCHEMA ---
    # The SDK expects the tool's input_schema to be an OBJECT.
    if response_schema.get("type", "").lower() == "object":
        # Objects are passed directly
        claude_input_schema = response_schema
        tool_name = "extract_scientific_data"
    elif response_schema.get("type", "").lower() == "array":
        # Arrays must be wrapped in a pseudo-OBJECT for the tool parameter.
        claude_input_schema = {
            "type": "object",
            "properties": {
                "data_array": response_schema
            },
            "required": ["data_array"]
        }
        tool_name = "consolidate_data" # Name change for synthesis tool
    else:
        claude_input_schema = response_schema
        tool_name = "generic_tool"
    # ------------------------------------------

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
                
                # Unwrap the result if we used the array wrapper (for ARRAY schemas)
                if response_schema.get("type", "").lower() == "array":
                    # The result is { "data_array": [...] } -> extract the array
                    return raw_input.get("data_array", {"error": "Failed to unwrap Claude ARRAY response."})
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
        
    # Schema types are already lowercase thanks to global sanitization
    sanitized_schema = response_schema
    
    # Check if this is the consolidation step (ARRAY) or the chunk analysis (OBJECT)
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
            if tool_call.function.name == tool_name:
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


# --- GENERALIZED PIPELINE FUNCTIONS (Unchanged) ---

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

def analyze_chunk(document_id: str, chunk_content: str) -> Dict[str, Any]:
    """Phase 1a: Calls the unified API to analyze a single chunk."""
    if MOCK_MODE:
        # Use a generalized mock call
        return {"error": "Mocking is not fully implemented for cross-API chunk analysis yet."}

    # Sanitize the chunk content
    sanitized_content = chunk_content.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        
    user_query = build_chunk_analysis_query(document_id, sanitized_content)
    
    return call_llm_api_internal(
        document_id=document_id,
        user_query=user_query,
        response_schema=CHUNK_RESPONSE_SCHEMA 
    )

def synthesize_results(doc_id: str, title: str, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Phase 1b: Calls the unified API to synthesize all chunk results into the final document schema."""
    
    if MOCK_MODE:
        return {"error": "Mocking is not fully implemented for cross-API synthesis yet."}

    user_query = build_synthesis_query(doc_id, title, chunk_results)
    
    return call_llm_api_internal(
        document_id=doc_id,
        user_query=user_query,
        response_schema=RESPONSE_SCHEMA 
    )


# --- ORCHESTRATION & MAIN (Token Reporting Fix) ---

def process_document(doc_id: str, doc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrates the chunk analysis (1a) and final synthesis (1b) for one document."""
    
    all_chunk_results = []
    
    # PHASE 1a: ITERATIVE CHUNK ANALYSIS
    print(f"    -> Starting Chunk Analysis ({len(doc_data['all_chunks'])} chunks) using {API_PROVIDER}...")
    for i, chunk in enumerate(doc_data['all_chunks']):
        chunk_content = chunk.get('text', '')
        
        if not chunk_content.strip():
             print(f"    -> Warning: Chunk {i+1} is empty, skipping.")
             continue

        chunk_result = analyze_chunk(doc_id, chunk_content)
        
        if "error" in chunk_result:
            print(f"    -> FAILED on Chunk {i+1}. Stopping for this document.")
            return {"error": f"Failed analysis on chunk {i+1}: {chunk_result['error']}"}
            
        all_chunk_results.append(chunk_result)
        sleep(0.5) # Small delay between chunks
    
    if not all_chunk_results:
        return {"error": "No non-empty chunks were successfully processed."}
        
    # PHASE 1b: FINAL SYNTHESIS
    print("    -> Synthesizing final document result...")
    final_analysis = synthesize_results(doc_id, doc_data['title'], all_chunk_results) 
    
    if "error" in final_analysis:
        print(f"    -> FAILED Synthesis: {final_analysis['error']}")
    
    return final_analysis

def main():
    """Main function to iterate over documents and process chunks."""
    
    global TOKEN_USAGE

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
    
    for doc_id, data in documents_to_process.items():
        # Setzt den Zähler für jedes Dokument zurück
        initialize_token_usage() 

        print(f"\n--- Processing Document ID: {doc_id} (Title: {data['title'][:50]}...) ---")
        
        analysis_result = process_document(doc_id, data)
        
        if "error" not in analysis_result and analysis_result.get('extracted_data'):
            
            analysis_result['document_source_id'] = doc_id
            analysis_result['analysis_date'] = datetime.now().strftime("%Y-%m-%d")
            analysis_result['title'] = data['title']
            
            output_filename = os.path.join(OUTPUT_DIR_PHASE1, f"{doc_id}_analysis.json")
            with open(output_filename, "w", encoding='utf-8') as f:
                json.dump([analysis_result], f, indent=2) 
            
            print(f"Successfully analyzed and saved to '{output_filename}'.")
            success_count += 1
            
            # 🚨 FIX: Token-Nutzung nach erfolgreicher Analyse des Dokuments ausgeben
            print("--- TOKEN USAGE SUMMARY FOR DOCUMENT ---")
            print(f"Provider: {TOKEN_USAGE['provider']} ({TOKEN_USAGE['model']})")
            print(f"Total API Calls: {TOKEN_USAGE['total_calls']}")
            print(f"Input Tokens (Prompt/Data): {TOKEN_USAGE['input_tokens']}")
            print(f"Output Tokens (Response): {TOKEN_USAGE['output_tokens']}")
            print(f"Total Tokens Used: {TOKEN_USAGE['total_tokens']}")
            print("----------------------------------------")
            
        else:
            print(f"Failed analysis for {doc_id}: {analysis_result.get('error', 'Unknown Error during processing.')}")

    print(f"\nPipeline Phase 1 completed. Successfully processed {success_count} documents.")


if __name__ == "__main__":
    main()