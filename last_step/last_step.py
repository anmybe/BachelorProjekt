import json
import pandas as pd
import google.generativeai as genai
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import os
from pathlib import Path
import time


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
BASE_DIR = Path.home() / "BachelorProjekt"
INPUT_JSON = BASE_DIR / "last_step" / "final_biomarker_compendium5.json"
OUTPUT_PDF = "biomarker_summary2.pdf"
OUTPUT_CSV = "biomarker_summary2.csv"

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
    OUTPUT FORMAT (MUST FOLLOW EXACT STRUCTURE)
    ----------------------------------------

    Return ONLY a JSON object:

    {{
    "biomarker": "...",
    "document_ids": [...],
    "activity_context_summary": "...",
    "effect_summary": "...",
    "sport_specific_implication_summary": "...",
    "relevance_score_sport": number
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
# PDF EXPORT
# ---------------------------------------------------

def export_pdf(df, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    elements = []

    table_data = [df.columns.tolist()] + df.values.tolist()

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP")
    ]))

    elements.append(table)
    doc.build(elements)


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

        # Static manual fields
        training_relation = ""
        risk_indicator = ""
        monitoring_relevance = ""
        other = ""

        row = {
            "Biomarker": llm_output.get("biomarker", ""),
            "Document IDs": ", ".join(llm_output.get("document_ids", [])),
            "Activity Context Summary": llm_output.get("activity_context_summary", ""),
            "Effect Summary": llm_output.get("effect_summary", ""),
            "Sport Implications": llm_output.get("sport_specific_implication_summary", ""),
            "Relevance for Sports (1–10)": llm_output.get("relevance_score_sport", ""),
            "Occurrences in Dataset": occurrence_count,
            "Training Relation": training_relation,
            "Risk Indicator": risk_indicator,
            "Monitoring Relevance": monitoring_relevance,
            "Other": other
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    df.to_csv(OUTPUT_CSV, index=False)
    export_pdf(df, OUTPUT_PDF)

    print("CSV created:", OUTPUT_CSV)
    print("PDF created:", OUTPUT_PDF)


if __name__ == "__main__":
    main()
