import json
import csv
import random
import os
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "result_step4.json"
INPUT_CSV = BASE_DIR / "biomarker_summary_step4.csv"
LOG_FILE = BASE_DIR / "validation_log.csv"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_data():
    print(f"Loading data from {INPUT_JSON}...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    
    # Create a lookup dictionary for JSON data by standard_name
    json_map = {item.get("standard_name", "Unknown"): item for item in json_data}

    print(f"Loading data from {INPUT_CSV}...")
    csv_data = []
    if INPUT_CSV.exists():
        with open(INPUT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_data.append(row)
    else:
        print(f"Error: Could not find {INPUT_CSV}")
        return None, None

    return json_map, csv_data

def main():
    json_map, csv_data = load_data()
    if not json_map or not csv_data:
        return

    # Filter to ensure we only test items present in both
    valid_items = [row for row in csv_data if row["Biomarker"] in json_map]
    
    if not valid_items:
        print("No matching biomarkers found between JSON and CSV.")
        return

    print(f"\nLoaded {len(valid_items)} matched biomarkers.")
    input("Press Enter to start validation session...")

    session_count = 0
    
    while True:
        clear_screen()
        # Pick a random biomarker
        row = random.choice(valid_items)
        name = row["Biomarker"]
        source_entry = json_map[name]
        findings = source_entry.get("aggregated_source_findings_DEBUG", [])

        print("="*80)
        print(f"BIOMARKER: {name}")
        print("="*80)
        
        print("\n--- RAW SOURCE FINDINGS (Input to AI) ---")
        for i, finding in enumerate(findings):
             # Try to get the snippet from diverse locations in the JSON structure
            context = finding.get('document_context_data', {}).get('document_summary', 'N/A')
            print(f"[{i+1}] {context[:400]}..." if len(context) > 400 else f"[{i+1}] {context}")
            print("-" * 40)

        print("\n" + "="*80)
        print("--- AI GENERATED RESULT ---")
        print(f"CONTEXT SUMMARY:  {row['Activity Context Summary']}")
        print(f"EFFECT SUMMARY:   {row['Effect Summary']}")
        print(f"IMPLICATION:      {row['Sport Implications']}")
        print(f"RELEVANCE SCORE:  {row['Relevance for Sports (1–10)']}")
        print(f"GROUPS:           {row['Biomarker Groups']}")
        print("="*80)

        print("\nHow accurate/useful is this result?")
        print("[1] Bad / Hallucinated")
        print("[2] Poor / Missed Key Info")
        print("[3] Acceptable")
        print("[4] Good")
        print("[5] Excellent")
        print("[s] Skip")
        print("[q] Quit")

        choice = input("\nYour Rating: ").strip().lower()

        if choice == 'q':
            break
        
        if choice == 's':
            continue

        if choice in ['1', '2', '3', '4', '5']:
            # Log the result
            file_exists = LOG_FILE.exists()
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Biomarker", "Rating", "Comment"])
                
                comment = input("Optional comment (press Enter to skip): ")
                writer.writerow([name, choice, comment])
                print("Saved.")
                session_count += 1
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")

    print(f"\nSession ended. You validated {session_count} items.")
    print(f"Results saved to {LOG_FILE}")

if __name__ == "__main__":
    main()
