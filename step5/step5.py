import json
import csv
import google.generativeai as genai
import os
from pathlib import Path
import time
from dotenv import load_dotenv

load_dotenv()



# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
BASE_DIR = Path.home() / "Programming" / "BachelorProjekt"
INPUT_JSON = BASE_DIR / "step5" / "result_step4.json"
OUTPUT_CSV = "biomarker_summary_step4.csv"

MODEL = "gemini-2.5-flash"  # free model

# SET YOUR GEMINI API KEY DIRECTLY
# SET YOUR GEMINI API KEY FROM ENV
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))



# ---------------------------------------------------
# LLM REQUEST (WITH IMPROVED PROMPT & ROBUST PARSING)
# ---------------------------------------------------

def query_gemini(biomarker_name, findings):
    prompt = f"""
    You are a sports medicine and exercise physiology expert.  
    Your analysis MUST stay strictly within the domain of:

    - exercise physiology  
    - training load monitoring  
    - recovery and adaptation  
    - overtraining / underrecovery  
    - metabolic flexibility  
    - inflammation in athletes  
    - performance diagnostics  
    - muscle damage and repair  
    - cardiovascular and endocrine adaptation  

    Ignore all disease-related or non-athletic findings unless they directly affect training, recovery, or performance.  
    If a study has NO athletic context, explicitly state this and avoid speculation.

    ----------------------------------------
    DATA
    ----------------------------------------
    Biomarker: {biomarker_name}

    Findings:
    {json.dumps(findings, indent=2)}

    ----------------------------------------
    TASKS
    ----------------------------------------

    1. Extract ALL document IDs from the findings.  
    - The output MUST ALWAYS contain the field "document_ids".  
    - It MUST ALWAYS be a list of strings.

    2. Summarize all activity contexts (athlete population, intervention, training state).  
    If none exist → state "No athlete or exercise context reported."

    3. Summarize all observed effects concisely.  
    Do NOT include mechanistic speculation beyond what is in the findings.

    4. Summarize implications ONLY through a sports-science lens:
    - Does this biomarker help understand training stress, adaptation, performance, or recovery?
    - If the findings do NOT support athletic interpretation → clearly state that.

    5. Rate SPORTS relevance (1–10) using the provided scale.
    If findings are non-athletic → give a low but justified score.

    ----------------------------------------
    BIOMARKER GROUP CLASSIFICATION
    ----------------------------------------

    Assign the biomarker to one or more of these groups:

    1. "inflammatory_changes"
    2. "metabolic"
    3. "glycemic"
    4. "cardio_risk"
    5. "endocrine_response"
    6. "cell_damage"
    7. "muscle_damage"

    Rules:
    - Choose ONLY based on physiological function of the biomarker itself.
    - A biomarker can belong to multiple groups.
    - If uncertain → leave empty.
    - Do NOT invent new groups.

    ----------------------------------------
    OUTPUT FORMAT (STRICT JSON)
    ----------------------------------------

    Return ONLY a JSON object:

    {{
    "biomarker": "{biomarker_name}",
    "document_ids": [...],
    "activity_context_summary": "...",
    "effect_summary": "...",
    "sport_specific_implication_summary": "...",
    "relevance_score_sport": number,
    "biomarker_groups": [...]
    }}
    """


    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(prompt)

    # Extract correct text content
    try:
        raw = response.candidates[0].content.parts[0].text
    except Exception as e:
        print("ERROR: Gemini returned no text. Full response:")
        print(response)
        raise e

    # Clean up JSON fences
    raw = raw.strip().replace("```json", "").replace("```", "").replace("`", "")

    # Parse JSON robustly
    try:
        output = json.loads(raw)
    except Exception as e:
        print("\nERROR: JSON parsing failed. RAW OUTPUT:\n")
        print(raw)
        raise e

    return output




# ---------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------

def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- FAULT TOLERANCE: CHECK EXISTING PROGRESS ---
    processed_biomarkers = set()
    output_file = BASE_DIR / "step5" / OUTPUT_CSV

    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                # Assuming "Biomarker" is the first column (index 0)
                for row in reader:
                    if row:
                        processed_biomarkers.add(row[0])
        print(f"Resuming... Found {len(processed_biomarkers)} already processed biomarkers.")
    else:
        # Create file and write header if it doesn't exist
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Biomarker", "Document IDs", "Activity Context Summary", 
                "Effect Summary", "Sport Implications", "Relevance for Sports (1–10)", 
                "Biomarker Groups", "Occurrences in Dataset"
            ])
        print(f"Created new output file: {OUTPUT_CSV}")

    total_biomarkers = len(data)
    
    # Open file in APPEND mode for continuous writing
    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for i, biomarker in enumerate(data):
            # Adjusted fields for result_step4.json structure
            name = biomarker.get("standard_name", "Unknown")

            if name in processed_biomarkers:
                print(f"Skipping {i+1}/{total_biomarkers}: {name} (Already processed)")
                continue

            findings = biomarker.get("aggregated_source_findings_DEBUG", [])

            try:
                llm_output = query_gemini(name, findings)
            except Exception as e:
                print(f"Failed to process {name}: {e}")
                continue
            
            # time.sleep(7)  # Removed rate limiting for paid key

            occurrence_count = len(findings)

            row = [
                llm_output.get("biomarker", ""),
                ", ".join(llm_output.get("document_ids", [])),
                llm_output.get("activity_context_summary", ""),
                llm_output.get("effect_summary", ""),
                llm_output.get("sport_specific_implication_summary", ""),
                llm_output.get("relevance_score_sport", ""),
                ", ".join(llm_output.get("biomarker_groups", [])),
                occurrence_count
            ]

            writer.writerow(row)
            # Flush immediately to ensure data is saved to disk
            f.flush()
            print(f"Processed {i+1}/{total_biomarkers}: {name}")

    print("Processing complete.")


if __name__ == "__main__":
    main()
