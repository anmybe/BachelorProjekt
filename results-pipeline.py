import json
import requests
import os
from time import sleep
from datetime import datetime

# --- CONFIGURATION ---
# IMPORTANT: Set MOCK_MODE = True for local testing (no API key needed).
MOCK_MODE = False

# Folder where your chunked text files reside
CHUNK_FOLDER = "xml_chunks"
OUTPUT_DIR_PHASE1 = "phase1_results" 
API_KEY = "AIzaSyBJ71KAiR9A791vIIp3P7ty_9GpTL011dk"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"

# The structured output schema definition (required for both real API and mocking structure validation)
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


# The actual prompt based on your final combined query
SYSTEM_INSTRUCTION = (
    "You are a Scientific Review Assistant. Your task is to analyze the provided article chunks "
    "(Abstract, Methods, Results, and Discussion sections) related to sports medicine and biomarker relationships. "
    "You MUST respond ONLY with a single JSON object that strictly conforms to the provided JSON Schema. "
    "Extract and synthesize the requested information, focusing on specific biomarker names and the physical activity context."
)

def build_user_query(document_id: str, chunk_content: str) -> str:
    """Builds the comprehensive user prompt based on the five integrated queries."""
    
    integrated_query = """
    Analyze the provided content related to the article: {doc_id}. 
    Focus on extracting precise data points and relationships to fulfill the following requirements.

    1. Core Effect & Quantification (Biomarker Identity): Identify all primary **biomarkers** that showed a statistically **significant change** (up or down) in response to the study's **physical intervention**. List the **biomarker name**, the **physical activity context** (e.g., HIPE, P2, Heavy Labor), and quantify the **magnitude of this change** (e.g., logFC=1.27, ~51% reduction, p=0.017, >250 MMU/ml).

    2. Molecular Mechanism & Activity Type (Relationship): Describe the authors' proposed **molecular mechanism** or **causal relationship** that links the **activity type** (e.g., endurance, heavy labor) to the resulting change in the **biomarker** (e.g., Leptin level influencing T-cell proliferation, or TOC correlating with hsCRP).

    3. Dose/Intensity and Sport/Workload Specificity (Comparison): Analyze whether the study identified a **dose-response** effect or **specificity** related to the type of **sport/workload**. Specifically, compare the difference in effect (or lack thereof) between **high** vs. **low** intensity, the inclusion of **heat stress**, or the **physique athlete diet** vs. **control** groups on the **biomarkers**.

    4. Clinical Implication & Relevant Population (Health Context): What **clinical or health risk implications** did the authors associate with the observed **biomarker pattern** for the **study population**? Classify the finding as either a **protective anti-inflammatory benefit** or an **adverse risk** (e.g., autoimmunity, infection).

    5. Biomarker Reliability & Future Focus (Assay Utility): Evaluate the authors' assessment of the **sensitivity or reliability** of the key **biomarkers** (e.g., EndoCAb utility in EIGS). Which **alternative biomarkers** (e.g., Ig free light chains) or **functional assays** did the authors recommend for future research?

    Provided Article Chunks (Abstract, Methods, Results, and Discussion):
    ---
    {content}
    ---
    """
    return integrated_query.format(doc_id=document_id, content=chunk_content)

# --- CHUNK LOADER FUNCTION ---

def load_and_combine_chunks():
    """
    Loads and combines 'results' and 'discussion' chunks from the specified folder.
    Groups files by their Document ID (e.g., 'PMC7617100').
    """
    if not os.path.isdir(CHUNK_FOLDER):
        print(f"Error: Directory '{CHUNK_FOLDER}' not found. Please create it and place your files inside.")
        return {}

    all_files = os.listdir(CHUNK_FOLDER)
    doc_chunks = {}

    # 1. Group files by Document ID
    for filename in all_files:
        if filename.endswith('.txt'):
            parts = filename.split('_')
            
            if len(parts) >= 2:
                doc_id = parts[0]
                section = parts[-1].replace('.txt', '').lower()
                
                if doc_id not in doc_chunks:
                    doc_chunks[doc_id] = {
                        'title': None, 
                        'abstract': None, 
                        'methods': None, 
                        'results': None, 
                        'discussion': None, 
                    }

                if 'results' in section:
                    doc_chunks[doc_id]['results'] = filename
                elif 'discussion' in section:
                    doc_chunks[doc_id]['discussion'] = filename
                elif 'title' in section:
                    doc_chunks[doc_id]['title'] = filename
                elif 'abstract' in section:
                    doc_chunks[doc_id]['abstract'] = filename
                elif 'methods' in section:
                    doc_chunks[doc_id]['methods'] = filename


    final_chunks = {}
    
    # 2. Combine all available sections for each document
    for doc_id, files in doc_chunks.items():
        if files['results'] and files['discussion']:
            try:
                # Load Title
                title_content = f"Document ID: {doc_id}"
                if files['title']:
                     with open(os.path.join(CHUNK_FOLDER, files['title']), 'r', encoding='utf-8') as f:
                        # Liest nur die erste Zeile oder entfernt unnötigen Whitespace
                        title_content = f.read().strip().split('\n')[0] 
                
                # Load content from all sections
                content_parts = {}
                sections_to_load = ['abstract', 'methods', 'results', 'discussion']
                
                for section in sections_to_load:
                    filename = files.get(section)
                    content = f"[No {section.upper()} content available]"
                    if filename:
                        with open(os.path.join(CHUNK_FOLDER, filename), 'r', encoding='utf-8') as f:
                            content = f.read()
                    content_parts[section] = content

                # Combine all sections with clear delimiters
                combined_content = (
                    f"--- ABSTRACT SECTION ---\n{content_parts['abstract']}\n\n"
                    f"--- METHODS SECTION ---\n{content_parts['methods']}\n\n"
                    f"--- RESULTS SECTION ---\n{content_parts['results']}\n\n"
                    f"--- DISCUSSION SECTION ---\n{content_parts['discussion']}"
                )
                
                final_chunks[doc_id] = {
                    'title': title_content,
                    'content': combined_content
                }
                
            except Exception as e:
                print(f"Warning: Could not read or combine files for {doc_id}. Error: {e}")
        else:
             print(f"Skipping {doc_id}: Missing core 'results' or 'discussion' file.")

    return final_chunks

# --- MOCK & REAL API CALL FUNCTIONS ---

def mock_call_gemini_api(document_id: str, chunk_content: str):
    """
    Simulates the LLM's structured JSON response for local testing.
    This uses a fixed mock structure for immediate pipeline testing.
    """
    print(f"--- MOCKING API RESPONSE for {document_id} ---")
    
    mock_data = {
        "title": f"MOCK ANALYSIS: {document_id}",
        "document_source_id": document_id,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "extracted_data": {
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
    }
    return mock_data

def call_gemini_api(document_id: str, chunk_content: str):
    """Calls the Gemini API to analyze the chunk content and return structured JSON (Real API Call)."""
    
    user_query = build_user_query(document_id, chunk_content)
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA
        }
    }
    
    # Implement exponential backoff for robustness
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, 
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if json_text:
                return json.loads(json_text)
            else:
                print(f"Warning: Model returned empty content for {document_id}. Attempt {attempt + 1}")
        
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Error for {document_id} on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            sleep(retry_delay)
            retry_delay *= 2
        
    return {"error": f"Failed to process {document_id} after {max_retries} attempts."}


def main():
    """Main function to iterate over documents and process chunks."""
    
    # NEU: Sicherstellen, dass der Ausgabeordner existiert
    if not os.path.exists(OUTPUT_DIR_PHASE1):
        os.makedirs(OUTPUT_DIR_PHASE1)
        print(f"Created output directory: '{OUTPUT_DIR_PHASE1}'")

    # Use the new loader function to get the data structure
    simulated_chunks = load_and_combine_chunks()
    if not simulated_chunks:
        print("No documents were loaded or found. Exiting.")
        return

    # Select the appropriate processing function
    process_func = mock_call_gemini_api if MOCK_MODE else call_gemini_api 

    success_count = 0
    
    for doc_id, data in simulated_chunks.items():
        print(f"\n--- Processing Document ID: {doc_id} (Title: {data['title']}) ---")
        
        # NOTE: Pass the combined content to the API or mock function
        analysis_result = process_func(doc_id, data['content'])
        
        if "error" not in analysis_result:
            # Füllen der dynamischen Felder
            analysis_result['document_source_id'] = doc_id
            analysis_result['analysis_date'] = datetime.now().strftime("%Y-%m-%d")
            analysis_result['title'] = data['title']
            
            # SPEICHERN PRO DOKUMENT IN DEN NEUEN ORNDER
            output_filename = os.path.join(OUTPUT_DIR_PHASE1, f"{doc_id}_analysis.json")
            with open(output_filename, "w", encoding='utf-8') as f:
                # Speichert das Ergebnis als Array, da Phase 2 ein Array erwartet
                json.dump([analysis_result], f, indent=2) 
            
            print(f"Successfully analyzed and saved to '{output_filename}'.")
            success_count += 1
        else:
            print(f"Failed analysis for {doc_id}: {analysis_result['error']}")

    print(f"\nPhase 1 completed. Successfully processed {success_count} documents.")


if __name__ == "__main__":
    main()