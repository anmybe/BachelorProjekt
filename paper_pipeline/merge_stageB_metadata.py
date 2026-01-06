import json
import os

def merge_metadata_files():
    base_dir = "paper_pipeline/intermediary_results"
    files_to_merge = [
        "stageB_metadata.json",
        "stageB_metadata2.json",
        "stageB_metadata3.json"
    ]
    
    merged_data = []
    seen_pmids = set()
    
    print("Starting merge process...")
    
    for filename in files_to_merge:
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}")
            continue
            
        print(f"Processing {filename}...")
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            count_new = 0
            for item in data:
                pmid = item.get('pmid')
                if pmid and pmid not in seen_pmids:
                    seen_pmids.add(pmid)
                    merged_data.append(item)
                    count_new += 1
            print(f"  Added {count_new} new items from {filename}")
            
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from {filepath}")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    output_file = os.path.join(base_dir, "stageB_metadata_merged.json")
    print(f"Writing merged data to {output_file}...")
    
    try:
        with open(output_file, 'w') as f:
            json.dump(merged_data, f, indent=2)
        print(f"Successfully merged {len(merged_data)} unique items.")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    merge_metadata_files()
