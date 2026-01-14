import json
import random
from pathlib import Path
import os
from dotenv import load_dotenv
import csv
from datetime import datetime
from fpdf import FPDF
from openai import OpenAI

# Load environment
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths & config
PAPER_LINKS = Path("step1-2/paper_links/paper_id_links_correct_path.json")
SCHRITT1_DIR = Path("Schritt1_Results")
SAMPLES = 30

OUTPUT_DIR = Path("validation")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

BUNDLE_DIR = OUTPUT_DIR / "bundles"
BUNDLE_DIR.mkdir(exist_ok=True, parents=True)

RESULTS_CSV = OUTPUT_DIR / "results.csv"
SUMMARY_TXT = OUTPUT_DIR / "summary.txt"

PROMPT_TEMPLATE = """
Your task is to validate whether an AI-generated summary is faithful to the original scientific text.

You will receive a single PDF file that contains:
1) the raw full text of a scientific sports/physiology paper,
2) the AI-generated JSON analysis for that same paper.

Evaluate the AI analysis according to:
- correctness,
- absence of hallucinations,
- fidelity to the original content,
- correct direction of effects,
- whether the extracted findings match the source text.

Respond ONLY with one of:
excellent
good
acceptable
poor
hallucinated

Then provide a short 1–2 sentence explanation.
"""

def load_paper_links():
    if not PAPER_LINKS.exists():
        raise FileNotFoundError(f"Missing: {PAPER_LINKS}")
    with open(PAPER_LINKS, "r", encoding="utf-8") as f:
        return json.load(f)

def create_bundle_pdf(pmid, txt_path: Path, json_path: Path):
    bundle_path = BUNDLE_DIR / f"{pmid}_bundle.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    # Header
    pdf.multi_cell(0, 6, f"===== RAW PAPER TEXT (PMID {pmid}) =====\n\n")

    # Insert paper text
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            pdf.multi_cell(0, 5, line)

    pdf.add_page()
    pdf.multi_cell(0, 6, "===== JSON ANALYSIS =====\n\n")

    # Insert JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        for line in f:
            pdf.multi_cell(0, 5, line)

    pdf.output(str(bundle_path))
    return bundle_path

def upload_file(path: Path):
    with open(path, "rb") as f:
        uploaded = client.files.create(
            file=f,
            purpose="assistants"
        )
    return uploaded.id

def validate_pair(pmid, txt_path: Path, json_path: Path):
    bundle_pdf = create_bundle_pdf(pmid, txt_path, json_path)
    bundle_id = upload_file(bundle_pdf)

    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": PROMPT_TEMPLATE
                    },
                    {
                        "type": "input_file",
                        "file_id": bundle_id
                    }
                ]
            }
        ]
    )

    return response.output_text.strip()

def write_results_header():
    if not RESULTS_CSV.exists():
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["pmid", "verdict", "explanation", "timestamp"])

def append_result(pmid, verdict, explanation):
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([pmid, verdict, explanation, datetime.now().isoformat()])

def compute_statistics():
    counts = {k: 0 for k in ["excellent", "good", "acceptable", "poor", "hallucinated"]}
    total = 0

    if RESULTS_CSV.exists():
        with open(RESULTS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                verdict = row["verdict"].strip().lower()
                if verdict in counts:
                    counts[verdict] += 1
                    total += 1

    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write(f"Validation Summary ({total} samples)\n\n")
        for k, v in counts.items():
            pct = (v / total * 100) if total > 0 else 0
            f.write(f"{k}: {v} ({pct:.1f}%)\n")

    print("[INFO] Summary written:", SUMMARY_TXT)

def main():
    print("[INFO] Loading paper links...")
    paper_links = load_paper_links()
    if not paper_links:
        print("[ERROR] No entries found.")
        return

    sample_count = min(SAMPLES, len(paper_links))
    selected = random.sample(paper_links, sample_count)

    write_results_header()

    for i, entry in enumerate(selected, start=1):
        pmid = entry.get("pmid")
        text_file = entry.get("text_file")

        print(f"\n[INFO] Validating {i}/{sample_count} — PMID {pmid}")

        if not text_file:
            print("[ERROR] Missing text_file.")
            continue

        txt_path = Path(text_file)
        if not txt_path.exists():
            print("[ERROR] Missing TXT:", txt_path)
            continue

        json_path = SCHRITT1_DIR / f"{pmid}_analysis.json"
        if not json_path.exists():
            print("[ERROR] Missing JSON:", json_path)
            continue

        try:
            full_output = validate_pair(pmid, txt_path, json_path)

            if "\n" in full_output:
                verdict, explanation = full_output.split("\n", 1)
            else:
                verdict = full_output
                explanation = ""

            print("[RESULT]", verdict)
            append_result(pmid, verdict, explanation)

        except Exception as e:
            print("[ERROR] Failed:", e)

    compute_statistics()
    print("[INFO] Done.")

if __name__ == "__main__":
    main()
