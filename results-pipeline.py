import json
import requests
import os
import anthropic
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


# --- SYSTEM INSTRUCTIONS AND PROMPTS ---

# 1. System Instruction for CHUNK ANALYSIS (Phase 1a) - NOW USED AS PROMPT PREFIX
CHUNK_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a highly specialized Scientific Data Extractor. Your task is to analyze the provided article chunk "
    "and extract ALL relevant data points for the five required categories. Your response MUST ONLY be a single JSON object "
    "that strictly conforms to the provided JSON Schema (the 'extracted_data' block). DO NOT attempt to summarize the whole document; "
    "focus only on the specific facts present in the text provided.\n\n"
)

# 2. The original full SYSTEM INSTRUCTION (Used for the final SYNTHESIS step) - NOW USED AS PROMPT PREFIX
SYSTEM_INSTRUCTION_PREFIX = (
    "INSTRUCTIONS: You are a Scientific Review Assistant. Your task is to review the structured data provided below. "
    "You MUST respond ONLY with a single JSON object that strictly conforms to the provided full document JSON Schema. "
    "Extract and synthesize the requested information, focusing on specific biomarker names and the physical activity context.\n\n"
)

# 3. Query Builder for CHUNK ANALYSIS (FIXED to include instructions)
def build_chunk_analysis_query(document_id: str, chunk_content: str) -> str:
    """Builds the user prompt for analyzing a single chunk, including the system instructions."""
    
    integrated_query = """
    Analyze the provided content related to the article: **{doc_id}**. 
    Focus on extracting precise data points and relationships to fulfill the following requirements.

    1. Core Effect & Quantification (Biomarker Identity): Identify all primary **biomarkers** that showed a statistically **significant change** (up or down) in response to the study's **physical intervention/condition**. List the **biomarker name**, the **activity/disease context** (e.g., HIPE, P2, Primary Biliary Cirrhosis, Heavy Labor), and quantify the **magnitude of this change** (e.g., logFC=1.27, ~51% reduction, p=0.017, AUC=0.905).

    2. Molecular Mechanism & Activity Type (Relationship): Describe the authors' proposed **molecular mechanism** or **causal relationship** that links the **activity/disease type** (e.g., endurance, autoimmune destruction) to the resulting change in the **biomarker** (e.g., Leptin level influencing T-cell proliferation, or TOC correlating with hsCRP).

    3. Dose/Intensity and Sport/Workload Specificity (Comparison): Analyze whether the study identified a **dose-response** effect or **specificity** related to the type of **sport/workload/disease stage**. Specifically, compare the difference in effect (or lack thereof) between **high** vs. **low** intensity, the inclusion of **heat stress**, or the **physique athlete diet** vs. **control** groups, or **disease phases** on the **biomarkers**.

    4. Clinical Implication & Relevant Population (Health Context): What **clinical or health risk implications** did the authors associate with the observed **biomarker pattern** for the **study population** (e.g., patients with PBC, manual laborers)? Classify the finding as either a **protective anti-inflammatory benefit** or an **adverse risk/diagnostic utility** (e.g., autoimmunity, infection, superior diagnostic marker).

    5. Biomarker Reliability & Future Focus (Assay Utility): Evaluate the authors' assessment of the **sensitivity or reliability** of the key **biomarkers** (e.g., EndoCAb utility in EIGS). Which **alternative biomarkers** (e.g., Ig free light chains) or **functional assays** did the authors recommend for future research?

    Provided Article Content CHUNK:
    ---
    {content}
    ---
    """
    return CHUNK_INSTRUCTION_PREFIX + integrated_query.format(doc_id=document_id, content=chunk_content)

# 4. Query Builder for SYNTHESIS (FIXED to include instructions)
def build_synthesis_query(document_id: str, title: str, chunk_results: list) -> str:
    """Builds the user prompt for the final synthesis API call, including the system instructions."""
    
    formatted_results = "\n\n---\n\n".join([json.dumps(res, indent=2) for res in chunk_results])
    
    synthesis_query = f"""
    You are performing the final synthesis for the document: **{title}** (ID: {document_id}).
    
    Below is a collection of structured JSON objects, each extracted from a single chunk of the source paper. 
    Your task is to review all the individual JSON extractions and synthesize them into a single, cohesive, 
    and non-redundant final JSON object that strictly adheres to the requested full document schema.
    
    Rules for Synthesis:
    1. **Merge Arrays:** For 'core_effect_and_quantification' and 'recommended_alternatives', combine all unique findings from all chunks into a single array. Remove exact duplicates.
    2. **Synthesize Objects:** For the other three categories (Mechanism, Dose/Specificity, Clinical Implication, Reliability), read across all chunks and write a single, comprehensive, and non-redundant summary text for each field.
    3. **Ensure Completeness:** The final JSON object MUST adhere to the original document schema.
    
    Structured Data from Chunks:
    ---
    {formatted_results}
    ---
    """
    return SYSTEM_INSTRUCTION_PREFIX + synthesis_query

# --- CHUNK LOADER FUNCTION (Unchanged) ---

""" def load_document_chunks() -> Dict[str, Dict[str, Any]]:
    ""
    Loads a single JSON file per document ID, extracts metadata and returns the list of chunks.
    ""
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

    return documents_to_process """

def load_document_chunks() -> Dict[str, Dict[str, Any]]:
    """
    Loads a single JSON file per document ID, extracts metadata and returns the list of chunks.
    """
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


# --- API CALL IMPLEMENTATIONS ---

def mock_call_gemini_api(document_id: str, chunk_content: str = None) -> Dict[str, Any]:
    """
    Simulates the LLM's structured JSON response for local testing.
    This function is designed to return the CHUNK-level schema (extracted_data).
    """
    print(f"--- MOCKING API RESPONSE for {document_id} ---")
    
    # MOCK data must match the CHUNK_RESPONSE_SCHEMA (the 'extracted_data' block)
    mock_extracted_data = {
        "core_effect_and_quantification": [
            {
                "biomarker_name": "Mock_Neutrophils",
                "activity_context": "Mock_Intense Training",
                "direction_of_change": "Increase",
                "magnitude_quantification": "30% increase (p<0.01)"
            }
        ],
        "molecular_mechanism_and_relationship": {
            "activity_type_context": "Mock_Physique Sports",
            "mechanism_description": "Mock_Suppression mediated by low leptin levels causing T-cell inhibition.",
            "related_biomarkers": ["Mock_Leptin", "Mock_T-cells"]
        },
        "dose_intensity_and_specificity": {
            "dose_comparison_summary": "Mock_Effect more pronounced in 12hr vs 8hr shifts.",
            "specificity_finding": "Mock_Specific to myeloid lineage."
        },
        "clinical_implication_and_population": {
            "target_population": "Mock_Manual Laborers",
            "health_implication": "Mock_Early development of oxidative stress imbalance.",
            "risk_classification": "Adverse"
        },
        "biomarker_reliability_and_future_focus": {
            "reliability_assessment": "Mock_Low sensitivity in controlled lab settings.",
            "recommended_alternatives": ["Mock_Ig free light chains", "Mock_Functional assays"]
        }
    }
    return mock_extracted_data

def call_gemini_api_internal(document_id: str, user_query: str, system_instruction: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Internal function to handle the actual API call logic with retries."""
    
    # Constructing the payload 
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        # 🚨 FIX: Using the correct field name 'generationConfig' (reverted from previous error)
        "generationConfig": { 
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
        # NOTE: systemInstruction is omitted here because the instructions are now in user_query
    }
    
    max_retries = 5
    retry_delay = 1
    
    """ for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, 
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))
            response.raise_for_status() # Raises HTTPError for 4XX/5XX errors
            
            result = response.json()
            # Extract text from the nested response structure
            json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if json_text:
                return json.loads(json_text)
            else:
                print(f"Warning: Model returned empty content for {document_id}. Attempt {attempt + 1}")
        
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            # Capture the full response text if available for better debugging
            if hasattr(response, 'text'):
                 print(f"Detailed 400 Error: {response.text}")

            print(f"Error for {document_id} on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            sleep(retry_delay)
            retry_delay *= 2
        
    return {"error": f"Failed to process {document_id} after {max_retries} attempts."} """

    for attempt in range(max_retries):
        try:
            # 1. API Call with the Anthropic SDK
            response = ANTHROPIC_CLIENT.messages.create(
                model=MODELS["CLAUDE"],
                max_tokens=4096, # Generous token limit for complex extraction/synthesis
                messages=[
                    # The instructions and schema are already built into the user_query (system instruction prefix)
                    {"role": "user", "content": user_query} 
                ]
            )
            
            # 2. Extract and Parse the JSON from the response text
            # The model is instructed to wrap the JSON in <json>...</json> tags.
            json_text = response.content[0].text
            
            # Find the JSON content wrapped in <json> tags
            start_tag = "<json>"
            end_tag = "</json>"
            
            if start_tag in json_text and end_tag in json_text:
                json_start = json_text.find(start_tag) + len(start_tag)
                json_end = json_text.find(end_tag)
                
                # Sanitize and extract the JSON content
                extracted_json_str = json_text[json_start:json_end].strip()
                
                # Load and return the JSON object
                return json.loads(extracted_json_str)
            else:
                # Fallback: Try to parse the entire response if the tags are missing
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    print(f"Warning: Claude response for {document_id} on attempt {attempt + 1} did not contain valid JSON in <json> tags or as a direct response. Received text:\n{json_text[:200]}...")
            
        except APIError as e:
            # Handle specific Anthropic API errors (rate limits, invalid key, etc.)
            print(f"Claude API Error for {document_id} on attempt {attempt + 1}: {e}")
            if e.status_code == 429: # Too Many Requests (Rate Limit)
                print(f"Rate limit hit. Waiting for {retry_delay} seconds...")
            elif e.status_code == 400: # Bad Request (e.g., input too long)
                 # We don't retry 400 errors as they are likely permanent with the current input
                 return {"error": f"Bad Request (400) from Claude API: {e}"}
            else:
                 pass # Retry other transient errors

        except Exception as e:
            print(f"General Error for {document_id} on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            sleep(retry_delay)
            retry_delay *= 1.5 # Exponential backoff
            
    return {"error": f"Failed to process {document_id} after {max_retries} attempts with Claude API."}


def analyze_chunk(document_id: str, chunk_content: str) -> Dict[str, Any]:
    """
    Phase 1a: Calls the API to analyze a single chunk.
    """
    if MOCK_MODE:
        return mock_call_gemini_api(document_id, chunk_content)

    # Sanitize the chunk content to remove invalid characters
    sanitized_content = chunk_content.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        
    # The prompt now includes the system instructions
    user_query = build_chunk_analysis_query(document_id, sanitized_content)
    
    return call_gemini_api_internal(
        document_id=document_id,
        user_query=user_query,
        system_instruction=None, # System instruction is now included in user_query
        response_schema=CHUNK_RESPONSE_SCHEMA 
    )

def synthesize_results(doc_id: str, title: str, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Phase 1b: Calls the API to synthesize all chunk results into the final document schema."""
    
    if MOCK_MODE:
        print("--- MOCKING SYNTHESIS RESPONSE ---")
        return {
            "title": title,
            "document_source_id": doc_id,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "extracted_data": mock_call_gemini_api(doc_id)
        }

    # The prompt now includes the system instructions
    user_query = build_synthesis_query(doc_id, title, chunk_results)
    
    return call_gemini_api_internal(
        document_id=doc_id,
        user_query=user_query,
        system_instruction=None, # System instruction is now included in user_query
        response_schema=RESPONSE_SCHEMA 
    )


# --- ORCHESTRATION ---

def process_document(doc_id: str, doc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrates the chunk analysis (1a) and final synthesis (1b) for one document."""
    
    all_chunk_results = []
    
    # PHASE 1a: ITERATIVE CHUNK ANALYSIS
    print(f"    -> Starting Chunk Analysis ({len(doc_data['all_chunks'])} chunks)...")
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
    
    if not os.path.exists(OUTPUT_DIR_PHASE1):
        os.makedirs(OUTPUT_DIR_PHASE1)
        print(f"Created output directory: '{OUTPUT_DIR_PHASE1}'")

    documents_to_process = load_document_chunks()
    if not documents_to_process:
        print("No documents were loaded or found. Exiting.")
        return

    success_count = 0
    
    for doc_id, data in documents_to_process.items():
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
        else:
            print(f"Failed analysis for {doc_id}: {analysis_result.get('error', 'Unknown Error during processing.')}")

    print(f"\nPipeline Phase 1 completed. Successfully processed {success_count} documents.")


if __name__ == "__main__":
    main()