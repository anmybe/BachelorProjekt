import argparse
import openai
import csv
import os
from pathlib import Path
import sys
import pandas as pd
import json
sys.path.append(str(Path(__file__).resolve().parent.parent))
from legacy_code.utils import load_env, load_json_files, pretty_print_block, timestamp, set_random_seed
import random

def validate_papers(samples_per_group):
    print("[INFO] Starting paper validation process...")
    load_env()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Load biomarker summary CSV
    biomarker_summary_path = Path("step5/biomarker_summary_step4.csv")
    biomarker_data = pd.read_csv(biomarker_summary_path)

    # Group by biomarker groups and sample paper IDs
    sampled_paper_ids = []
    for group, group_data in biomarker_data.groupby("Biomarker Groups"):
        group_paper_ids = group_data["Document IDs"].dropna().str.split(", ").explode().unique()
        sampled_paper_ids.extend(random.sample(list(group_paper_ids), min(samples_per_group, len(group_paper_ids))))

    print(f"[INFO] Sampled paper IDs: {sampled_paper_ids}")

    # Load summaries and full texts
    summaries_dir = Path("Schritt1_Results")
    fulltexts_dir = Path("step1-2/intermediary_results/fulltext/fulltext_raw")

    # Map PMIDs to PMCIDs and file paths
    paper_id_map = {}
    with open("step1-2/paper_links/paper_id_links_correct_path.json", "r", encoding="utf-8") as f:
        paper_links = json.load(f)
        for entry in paper_links:
            pmid = entry.get("pmid")
            pmcid = entry.get("pmcid")
            text_file = entry.get("text_file")
            if pmid and pmcid and text_file:
                paper_id_map[pmid] = {
                    "pmcid": pmcid,
                    "text_file": text_file
                }

    # Test mapping for a random paper ID
    random_pmid = random.choice(list(paper_id_map.keys())) if paper_id_map else None
    if random_pmid:
        test_mapping = paper_id_map[random_pmid]
        print("[DEBUG] Testing mapping for random paper ID:", random_pmid)
        print("[DEBUG] Corresponding mapping:", test_mapping)

        # Check if the file exists
        test_file_path = Path(test_mapping["text_file"])
        if test_file_path.exists():
            print("[DEBUG] Test file exists:", test_file_path)
        else:
            print("[DEBUG] Test file does NOT exist:", test_file_path)

    print("[DEBUG] Paper ID Map:", paper_id_map)
    print("[DEBUG] Summaries Directory:", summaries_dir)
    print("[DEBUG] Fulltexts Directory:", fulltexts_dir)
    print("[DEBUG] Total entries in Paper ID Map:", len(paper_id_map))
    print("[DEBUG] Summaries Directory Path:", summaries_dir)
    print("[DEBUG] Fulltexts Directory Path:", fulltexts_dir)

    # Removed detailed debug comments for each paper to avoid flooding the terminal
    summaries = {}
    for file in summaries_dir.glob("*_analysis.json"):
        pmid = file.stem.split("_")[0]
        if pmid in paper_id_map:
            summaries[paper_id_map[pmid]["pmcid"]] = file.read_text(encoding="utf-8")

    fulltexts = {}
    for file in fulltexts_dir.glob("PMC*.txt"):
        pmcid = file.stem
        if any(pmcid == data["pmcid"] for data in paper_id_map.values()):
            fulltexts[pmcid] = file.read_text(encoding="utf-8")

    print("[DEBUG] Total Summaries Loaded:", len(summaries))
    print("[DEBUG] Total Fulltexts Loaded:", len(fulltexts))

    print("[DEBUG] Loaded Summaries:", summaries.keys())
    print("[DEBUG] Loaded Fulltexts:", fulltexts.keys())

    output_file = Path("validation/results/paper_validation_log.csv")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["paper_id", "category", "model_verdict", "timestamp", "user_comment"])
        writer.writeheader()

        for idx, paper_id in enumerate(sampled_paper_ids, start=1):
            print(f"[INFO] Validating paper {idx}/{len(sampled_paper_ids)}...")
            summary = summaries.get(paper_id, "")
            fulltext = fulltexts.get(paper_id, "")

            if not summary or not fulltext:
                print(f"[WARNING] Missing data for paper ID {paper_id}. Skipping.")
                continue

            prompt = f"""
            Your task is to validate whether an AI-generated summary is faithful to the original scientific text.

            You will receive:
            1. The original text snippet from a scientific paper.
            2. The AI-generated summary of that snippet.

            Evaluate the summary for:
            - correctness,
            - absence of hallucinations,
            - fidelity to the original content,
            - correct direction of effects.

            Respond ONLY with one of:
            "excellent"
            "good"
            "acceptable"
            "poor"
            "hallucinated"

            Original Text:
            {fulltext}

            AI-Generated Summary:
            {summary}
            """

            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=50
            )

            model_verdict = response.choices[0].text.strip()
            print(f"[INFO] Model verdict for paper {paper_id}: {model_verdict}")

            writer.writerow({
                "paper_id": paper_id,
                "category": biomarker_data.loc[biomarker_data["Document IDs"].str.contains(paper_id, na=False), "Biomarker Groups"].iloc[0],
                "model_verdict": model_verdict,
                "timestamp": timestamp(),
                "user_comment": ""
            })

    print(f"[INFO] Validation complete. Results saved to {output_file}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate paper-level summaries.")
    parser.add_argument("--samples_per_group", type=int, default=5, help="Number of papers to sample per biomarker group.")
    args = parser.parse_args()

    validate_papers(args.samples_per_group)