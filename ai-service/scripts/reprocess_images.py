import os
import requests
import json
from pathlib import Path

# ==============================================================================
# CONFIGURATION: Define which images each model should interpret.
# Dictionary structure: {"Model Name": ["image1.jpg", "image2.jpg"]}
# ==============================================================================
MODEL_IMAGE_MAP = {
    "SmolVLM2-256M-Video (F16 - Same Model)": [
        "579405.jpg"
    ],
    "SmolVLM2-256M-Video (Q8 - FP16 Test)": [
        "579239.jpg"
    ],
    "SmolVLM2-256M-Video (Q8 - Same Model)": [
        "579239.jpg"
    ],
    # Add new unsupported models and images here.
}

# API Settings
API_ENDPOINT = "http://localhost:8200/v1/inference/fall-detection"
DATASET_ROOT = Path(__file__).parent.parent / "tests" / "dataset"

def find_image_path(filename):
    """Recursively searches for an image in the dataset folder."""
    for path in DATASET_ROOT.rglob(filename):
        if path.is_file():
            return path
    return None

def process_image(image_name, target_model):
    """Sends an image to the API and prints the result."""
    print(f"\n[Image: {image_name}]")
    
    image_path = find_image_path(image_name)
    if not image_path:
        print(f"ERROR: Image not found: {image_name}")
        return

    try:
        with open(image_path, "rb") as f:
            files = {"file": (image_path.name, f, "image/jpeg")}
            # Note: The API uses the currently active loaded model.
            # The model label is printed only for informational purposes.
            response = requests.post(API_ENDPOINT, files=files, timeout=300)
            
        if response.status_code == 200:
            result = response.json()
            print(f"STATUS: Success")
            print(f"MODEL RESULT: {result.get('result', 'Unknown')}")
            print(f"MODEL OUTPUT (Raw): {result.get('raw_output', 'No output')}")
            print(f"LATENCY: {result.get('latency_ms', 0)} ms")
        else:
            print(f"ERROR: API returned status {response.status_code}.")
            print(f"DETAIL: {response.text}")

    except Exception as e:
        print(f"UNEXPECTED ERROR: {str(e)}")

def main():
    print("Unprocessed image interpretation script started...")
    print(f"Dataset Root Directory: {DATASET_ROOT}")
    
    if not MODEL_IMAGE_MAP:
        print("No processable entries found in the dictionary. Please update MODEL_IMAGE_MAP.")
        return

    for model_name, images in MODEL_IMAGE_MAP.items():
        print(f"\n{'='*60}")
        print(f"MODEL: {model_name}")
        print(f"{'='*60}")
        for image_name in images:
            process_image(image_name, model_name)

if __name__ == "__main__":
    main()
