import json
import os

def generate_links():
    # Try both possible paths
    paths = [
        "paper_pipeline/intermediary_results/stageB_metadata_merged.json",
        "paper_pipeline/paper_links/stageB_metadata_merged.json"
    ]
    
    metadata_path = None
    for p in paths:
        if os.path.exists(p):
            metadata_path = p
            break
            
    if not metadata_path:
        print(f"Error: Metadata file not found in {paths}")
        return

    print(f"Reading metadata from {metadata_path}")
    output_path = "paper_viewer/src/paper_links.json"
    
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
