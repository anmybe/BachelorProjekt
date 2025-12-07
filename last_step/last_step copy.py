import json
import pandas as pd
import google.generativeai as genai
import os
from pathlib import Path
import time


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_JSON = BASE_DIR / "last_step" / "final_biomarker_compendium5.json"
OUTPUT_CSV = "biomarker_summary3.csv"

MODEL = "gemini-2.5-flash"  # free model

# SET YOUR GEMINI API KEY DIRECTLY
genai.configure(api_key="AIzaSyCoTjmHS7ugwRiVG4j_fvuBG8HpdS6QG8Y")


# ---------------------------------------------------
# LLM REQUEST (WITH IMPROVED PROMPT & ROBUST PARSING)
# ---------------------------------------------------

def query_gemini(biomarker_name, findings):
    prompt = f"""
    You are a sports medicine and exercise physiology expert.  
    You must analyze the biomarker strictly in the context of:

    - exercise physiology  
    - training load monitoring  
    - recovery and adaptation  
    - overtraining / underrecovery  
    - metabolic flexibility  
    - inflammation in athletes  
    - performance diagnostics  
    - muscle damage and repair  
    - cardiovascular and endocrine adaptation  

    Ignore general medical or disease-related relevance unless it directly influences athletic performance or training capacity.

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

    3. Summarize all observed effects concisely.

    4. Summarize clinical implications ONLY through a sports-science lens:
    - How does this biomarker inform training?
    - How useful is it for monitoring adaptation, stress, performance, or recovery?

    5. Rate the SPORTS relevance (1–10) using:

    10 = Core biomarker in sports physiology (lactate, VO2max-related, CK, HRV, cortisol, testosterone)  
        8–9 = Strong recovery/training-load markers used in elite sports  
        6–7 = Moderately useful indirect markers (creatinine, urea, general inflammation markers)  
        3–5 = Weak relevance to training decisions  
        1–2 = No practical use for sports diagnostics (oncology markers, cancer miRNA, PRS for disease)

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

    rows = []

    for biomarker in data:
        name = biomarker["biomarker_name"]
        findings = biomarker["findings_by_activity"]

        llm_output = query_gemini(name, findings)
        time.sleep(7)  # prevent 429 rate limit errors

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
    df.to_csv(OUTPUT_CSV, index=False)
    print("CSV created:", OUTPUT_CSV)


if __name__ == "__main__":
    main()
