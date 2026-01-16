import os
import json
import csv
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
def load_env():
    load_dotenv()

# Load JSON files from a directory
def load_json_files(directory):
    directory = Path(directory)
    return [json.load(open(file, 'r', encoding='utf-8')) for file in directory.glob("*.json")]

# Load CSV file
def load_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

# Pretty print a block of text
def pretty_print_block(text):
    print("=" * 40)
    print(text)
    print("=" * 40)

# Generate a timestamp
def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Ensure reproducibility
def set_random_seed(seed=42):
    random.seed(seed)