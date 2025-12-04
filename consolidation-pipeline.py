import json
import requests
import os
from time import sleep

# --- CONFIGURATION ---
INPUT_FOLDER = "semantic_serial_results"
OUTPUT_FILE = "final_biomarker_compendium.json"
API_KEY = "AIzaSyBJ71KAiR9A791vIIp3P7ty_9GpTL011dk"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"

FINAL_BIOMARKER_SCHEMA = {
  "description": "Final consolidated list of all biomarkers, grouped by molecule name, detailing the relationship to different sports/workloads.",
  "type": "ARRAY",
  "items": {
    "type": "OBJECT",
    "properties": {
      "biomarker_name": {
        "type": "STRING",
        "description": "The specific name of the biomarker (e.g., IgA, hsCRP, Neutrophils, ACTH)."
      },
      "overall_summary": {
        "type": "STRING",
        "description": "A brief summary of the biomarker's role across all analyzed studies (e.g., Primary marker for immunosuppression and stress-induced inflammation)."
      },
      "findings_by_activity": {
        "type": "ARRAY",
        "description": "Detailed findings for this biomarker across different activity contexts.",
        "items": {
          "type": "OBJECT",
          "properties": {
            "source_document_id": {
              "type": "STRING",
              "description": "The original document ID where this finding was extracted."
            },
            "activity_context": {
              "type": "STRING",
              "description": "The specific sport or workload tested (e.g., Endurance Running P2-EHS, LIPE, Heavy Labor/Slaughterhouse)."
            },
            "effect_and_magnitude": {
              "type": "STRING",
              "description": "The direction and magnitude of change (e.g., Increased significantly (p<0.01), logFC=1.27 reduction, No substantial change)."
            },
            "clinical_implication": {
              "type": "STRING",
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

# --- API FUSION LOGIC ---

def load_all_intermediate_data(directory_path):
    """
    Lädt und kombiniert alle JSON-Dateien aus dem angegebenen Ordner in ein einziges Array.
    Erwartet, dass jede JSON-Datei ein Array oder ein Objekt (mit einem Ergebnis) ist.
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
                    
                    # Die Ergebnisse aus Phase 1 sind typischerweise ein Array von Objekten
                    # ODER (falls die Datei nur ein Dokument enthielt) ein einzelnes Objekt.
                    if isinstance(data, list):
                        all_results.extend(data)
                    elif isinstance(data, dict):
                        # Füge ein einzelnes Ergebnis-Objekt als Array-Element hinzu
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


def consolidate_data(intermediate_data):
    """Sends the extracted data to the LLM for fusion and structuring."""
    
    # 1. Bereite die Daten für den Prompt vor
    data_for_prompt = json.dumps(intermediate_data, indent=2)
    
    SYSTEM_INSTRUCTION = (
        "You are a Scientific Data Fusion Specialist. Your task is to process a list of structured biomarker analyses "
        "(from multiple documents) and consolidate them into a single, comprehensive, thematic list. "
        "Group all findings by the 'biomarker_name' field. The output MUST strictly conform to the provided JSON Schema."
    )
    
    user_query = (
        "Consolidate the following intermediate biomarker data (extracted from multiple scientific articles) "
        "into the final required JSON structure. Group all findings by the unique biomarker name. "
        "The overall_summary should concisely explain the biomarker's general role in physical performance/stress.\n\n"
        "--- INTERMEDIATE DATA ---\n"
        f"{data_for_prompt}"
        "\n--- END OF DATA ---"
    )
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": FINAL_BIOMARKER_SCHEMA
        }
    }
    
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            print(f"Sending consolidation request (Attempt {attempt + 1})...")
            response = requests.post(API_URL, 
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if json_text:
                return json.loads(json_text)
        
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"API Error during consolidation: {e}")

        if attempt < max_retries - 1:
            sleep(retry_delay)
            retry_delay *= 2
        
    return {"error": "Failed to consolidate data after multiple attempts."}

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
        print("\n❌ FAILURE: Final data structure could not be generated.")

if __name__ == "__main__":
    main()