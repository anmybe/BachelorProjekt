import json
import os

def generate_links():
    # This is where merge_stageB_metadata.py outputs the file
    metadata_path = "step1-2/intermediary_results/stageB_metadata_merged.json"
    
    if not os.path.exists(metadata_path):
        print(f"Error: Metadata file not found at {metadata_path}")
        return

    print(f"Reading metadata from {metadata_path}")
    output_path = "paper_viewer/src/paper_id_links.json"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(metadata_path, 'r') as f:
            data = json.load(f)
            
        links = {}
        for item in data:
            pmid = item.get('pmid')
            doi = item.get('doi')
            if pmid and doi:
                links[pmid] = doi
                
        with open(output_path, 'w') as f:
            json.dump(links, f, indent=2)
            
        print(f"Generated {output_path} with {len(links)} entries.")
        
    except Exception as e:
        print(f"Error generating links: {e}")

if __name__ == "__main__":
    generate_links()
