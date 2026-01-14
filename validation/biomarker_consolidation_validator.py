import argparse
import openai
import csv
import os
from pathlib import Path
from validation.utils import load_env, load_json_files, load_csv, pretty_print_block, timestamp, set_random_seed

def validate_biomarker_consolidation(samples_per_category):
    load_env()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    json_dir = Path("data/papers")
    csv_file = Path("data/biomarker_summary_step4.csv")
    output_file = Path("output/consolidation_validation_log.csv")
    output_file.parent.mkdir(exist_ok=True)

    papers = load_json_files(json_dir)
    biomarker_data = load_csv(csv_file)

    categories = [
        "exercise physiology",
        "training load monitoring",
        "recovery and adaptation",
        "overtraining / underrecovery",
        "metabolic flexibility",
        "inflammation in athletes",
        "performance diagnostics",
        "muscle damage and repair",
        "cardiovascular and endocrine adaptation"
    ]

    set_random_seed()
    sampled_biomarkers = {}

    for category in categories:
        category_biomarkers = [b for b in biomarker_data if b.get("category") == category]
        if category_biomarkers:
            sampled_biomarkers[category] = random.sample(category_biomarkers, min(samples_per_category, len(category_biomarkers)))

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["biomarker", "category", "model_verdict", "number_of_source_papers", "timestamp", "user_comment"])
        writer.writeheader()

        for category, biomarkers in sampled_biomarkers.items():
            for biomarker in biomarkers:
                biomarker_name = biomarker.get("Biomarker", "unknown")
                document_ids = biomarker.get("Document IDs", "").split(", ")

                evidence_snippets = [
                    paper.get("document_summary", "")
                    for paper in papers
                    if paper.get("paper_id") in document_ids
                ]

                prompt = f"""
                You are evaluating whether a consolidated biomarker summary is consistent with its underlying evidence.

                You will receive:
                1) A list of original evidence snippets from the referenced papers.
                2) The consolidated biomarker summary (effect + context).

                Evaluate:
                - correctness,
                - consistency with evidence,
                - absence of contradictions or invented details,
                - whether typical physiological mechanisms are preserved.

                Respond ONLY with:
                "excellent"
                "good"
                "acceptable"
                "poor"
                "inconsistent"

                Evidence Snippets:
                {evidence_snippets}

                Consolidated Summary:
                {biomarker.get('Effect Summary', '') + ' ' + biomarker.get('Activity Context Summary', '')}
                """

                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=50
                )

                model_verdict = response.choices[0].text.strip()

                writer.writerow({
                    "biomarker": biomarker_name,
                    "category": category,
                    "model_verdict": model_verdict,
                    "number_of_source_papers": len(evidence_snippets),
                    "timestamp": timestamp(),
                    "user_comment": ""
                })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate biomarker consolidation summaries.")
    parser.add_argument("--samples_per_category", type=int, default=1, help="Number of biomarkers to sample per category.")
    args = parser.parse_args()

    validate_biomarker_consolidation(args.samples_per_category)