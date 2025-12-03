import requests
import base64
import json
# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
# 1. Point to LOCALHOST for local testing
BEANSTALK_URL = "http://127.0.0.1:5000"
ENDPOINT = f"{BEANSTALK_URL}/process_invoice"

# Path to a test image on your computer (optional)
# If you don't have one, set this to None
IMAGE_PATH = "invoice_sample.jpg" 

# Mock OCR text (simulating what AWS Rekognition would have found)
# This is used for the validation logic we added.
MOCK_RAW_TEXT = """
INVOICE #1001
Date: 2024-01-15
Vendor: Tech Corp Inc.
Item 1: Server hosting ... 500.00
Item 2: Support .......... 100.00
Subtotal: 600.00
VAT (20%): 120.00
TOTAL: 720.00
"""

def run_test():
    print(f"Testing service at: {ENDPOINT}")

    
    payload = {
        "text": MOCK_RAW_TEXT
    }

    # Load and encode image if it exists
    if IMAGE_PATH:
        try:
            with open(IMAGE_PATH, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                payload["image_base64"] = b64_string
                print(f"Loaded image: {IMAGE_PATH}")
        except FileNotFoundError:
            print("Image file not found, sending text only.")

    try:
        # Send POST request
        response = requests.post(ENDPOINT, json=payload)
        
        # Check status
        if response.status_code == 200:
            print("\n✅ SUCCESS!")
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\n❌ FAILED with status {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"\n❌ Connection Error: {e}")

if __name__ == "__main__":
    run_test()