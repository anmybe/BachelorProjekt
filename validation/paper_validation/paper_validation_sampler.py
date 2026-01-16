import json
import random
from pathlib import Path
import os
from dotenv import load_dotenv
import shutil

# Load environment variables from the .env file
load_dotenv()

def test_mapping():
    print("[INFO] Starting mapping test...")

    # Load paper ID links
    paper_id_links_path = Path("step1-2/paper_links/paper_id_links_correct_path.json")
    if not paper_id_links_path.exists():
        print(f"[ERROR] File not found: {paper_id_links_path}")
        return

    with open(paper_id_links_path, "r", encoding="utf-8") as f:
        paper_links = json.load(f)

    # Test mapping for a random file
    if not paper_links:
        print("[ERROR] No data found in paper ID links file.")
        return

    test_entry = random.choice(paper_links)  # Select a random entry
    pmid = test_entry.get("pmid")
    pmcid = test_entry.get("pmcid")
    text_file = test_entry.get("text_file")

    print("[DEBUG] Testing mapping for a random entry:")
    print(f"PMID: {pmid}")
    print(f"PMCID: {pmcid}")
    print(f"Text File Path: {text_file}")

    # Check if the text file exists
    if text_file:
        text_file_path = Path(text_file)
        if text_file_path.exists():
            print(f"[INFO] Text file exists: {text_file_path}")
        else:
            print(f"[ERROR] Text file does NOT exist: {text_file_path}")
    else:
        print("[ERROR] No text file path provided in the entry.")

def copy_to_samples_folder(file_path, destination_folder):
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination_path = destination_folder / file_path.name
    shutil.copy(file_path, destination_path)
    print(f"[INFO] Copied {file_path} to {destination_path}")

def validate_random_paper():
    print("[INFO] Starting validation for 30 random papers...")

    # Load paper ID links
    paper_id_links_path = Path("step1-2/paper_links/paper_id_links_correct_path.json")
    if not paper_id_links_path.exists():
        print(f"[ERROR] File not found: {paper_id_links_path}")
        return

    with open(paper_id_links_path, "r", encoding="utf-8") as f:
        paper_links = json.load(f)

    # Select 30 random entries
    if not paper_links:
        print("[ERROR] No data found in paper ID links file.")
        return

    selected_entries = random.sample(paper_links, min(30, len(paper_links)))

    for i, test_entry in enumerate(selected_entries, start=1):
        pmid = test_entry.get("pmid")
        pmcid = test_entry.get("pmcid")
        text_file = test_entry.get("text_file")

        print(f"[DEBUG] Testing validation for entry {i}:")
        print(f"PMID: {pmid}")
        print(f"PMCID: {pmcid}")
        print(f"Text File Path: {text_file}")

        # Check if the text file exists
        if not text_file:
            print("[ERROR] No text file path provided in the entry.")
            continue

        text_file_path = Path(text_file)
        if not text_file_path.exists():
            print(f"[ERROR] Text file does NOT exist: {text_file_path}")
            continue

        # Locate the correct JSON file in Schritt1_Results
        schritt1_results_dir = Path("Schritt1_Results")
        json_file_name = f"{pmid}_analysis.json"
        json_file_path = schritt1_results_dir / json_file_name

        if not json_file_path.exists():
            print(f"[ERROR] JSON file does NOT exist: {json_file_path}")
            continue

        # Create a subfolder for each pair
        subfolder = Path(f"validation/samples/sample_{i}")
        copy_to_samples_folder(json_file_path, subfolder)
        copy_to_samples_folder(text_file_path, subfolder)

    print("[INFO] Files copied to validation/samples folder with subfolders.")

if __name__ == "__main__":
    test_mapping()
    validate_random_paper()