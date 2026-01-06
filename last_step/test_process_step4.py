import json
import pandas as pd
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
INPUT_JSON = BASE_DIR / "last_step" / "result_step4.json"
OUTPUT_CSV = "test_biomarker_summary.csv"

MODEL = "gemini-2.5-flash"  # free model

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

    {
    "biomarker": "{biomarker_name}",
    "document_ids": [...],
    "activity_context_summary": "...",
    "effect_summary": "...",
    "sport_specific_implication_summary": "...",
    "relevance_score_sport": number,
    "biomarker_groups": [...]
    }
    """

    """


    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(prompt)

    # Extract correct text content
    try:
        if not response.candidates:
             print("ERROR: No candidates returned from Gemini.")
             print(response)
             return {}
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
    if not os.path.exists(INPUT_JSON):
        print(f"Error: Input file not found at {INPUT_JSON}")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    # TEST MODE: Only process the first biomarker
    print("Running in TEST MODE: Processing only the first biomarker...")
    for biomarker in data[:1]:
        # Adjusted fields for result_step4.json structure
        name = biomarker.get("standard_name", "Unknown")
        findings = biomarker.get("aggregated_source_findings_DEBUG", [])

        print(f"Processing: {name}")
        llm_output = query_gemini(name, findings)
        
        occurrence_count = len(findings)

        

        row = {
            "Biomarker": llm_output.get("biomarker", ""),
            "Document IDs": ", ".join(llm_output.get("document_ids", [])),
            "Activity Context Summary": llm_output.get("activity_context_summary", ""),
            "Effect Summary": llm_output.get("effect_summary", ""),
            "Sport Implications": llm_output.get("sport_specific_implication_summary", ""),
            "Relevance for Sports (1–10)": llm_output.get("relevance_score_sport", ""),
            "Biomarker Groups": ", ".join(llm_output.get("biomarker_groups", [])),
            "Occurrences in Dataset": occurrence_count
        }


        rows.append(row)

    df = pd.DataFrame(rows)
    # Print the result to console for immediate visibility
    print("\n--- TEST RESULT ---")
    print(df.to_string())
    print("-------------------\n")
    
    df.to_csv(OUTPUT_CSV, index=False)
    print("CSV created:", OUTPUT_CSV)


if __name__ == "__main__":
    main()
