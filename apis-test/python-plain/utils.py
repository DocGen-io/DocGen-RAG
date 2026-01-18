import os
import json

def read_json(file_path):
    """Reads a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def write_json(data, file_path):
    """Writes data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def list_files(directory):
    """Lists all files in a directory."""
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
