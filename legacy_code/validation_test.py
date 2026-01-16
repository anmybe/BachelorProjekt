import json
import random
from pathlib import Path

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

if __name__ == "__main__":
    test_mapping()