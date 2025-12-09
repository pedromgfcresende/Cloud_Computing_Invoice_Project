import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI
import re

application = Flask(__name__)

def get_current_timestamp():
    return datetime.now().isoformat()

def clean_number_string(s):
    """Removes currency symbols and dots for comparison."""
    if isinstance(s, (int, float)):
        return str(s)
    return re.sub(r'[^\d.,]', '', str(s))

def check_numbers_in_rekognition(invoice_data, raw_text):
    """
    Verifies that the numbers extracted by AI actually exist in the raw text 
    from Rekognition.
    """
    if not raw_text:
        return True # Skip check if no raw text provided

    normalized_raw = raw_text.replace('.', '').replace(',', '.')
    
    total_val = invoice_data.get('total')
    if total_val:

        clean_total = clean_number_string(total_val).replace(',', '')
        if clean_total not in normalized_raw:
             if str(total_val) not in raw_text:
                 return False

    vat_val = invoice_data.get('vat')
    if vat_val and float(vat_val) > 0:
        clean_vat = clean_number_string(vat_val).replace(',', '')
        if clean_vat not in normalized_raw:
             if str(vat_val) not in raw_text:
                 return False
                 
    return True

def validate_vat_math(invoice_data):
    """
    Checks if Total / (1 + VAT_rate) * VAT_rate ~= VAT_amount
    """
    try:
        total = float(invoice_data.get('total', 0))
        vat = float(invoice_data.get('vat', 0))
        rate_percent = float(invoice_data.get('vat_rate', 0)) 

        if rate_percent == 0 and vat == 0:
            return True
            
        if rate_percent == 0:
            return False 

        rate_decimal = rate_percent / 100.0
        
        calculated_vat = (total / (1 + rate_decimal)) * rate_decimal
        
   
        if abs(calculated_vat - vat) < 0.05:
            return True
            
        return False
    except Exception:
        return False
    
@application.route("/", methods=["GET"])
def health():
    return "OK", 200

@application.route('/process_invoice', methods=['POST'])
def process_invoice():
    """
    Expects JSON payload:
    {
        "text": "Raw OCR text (optional if image provided)",
        "image": "Base64 encoded image string (optional if text provided)"
    }
    Returns:
    {
        "csv_row": "2024-01-01,Vendor,100.00,20.00,2024-01-01T12:00:00"
    }
    """
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"error": "Server configuration error: Missing OpenAI API Key"}), 500
            
        client = OpenAI(api_key=api_key)
        data = request.get_json()
        raw_text = data.get('text', "")
        image_base64 = data.get('image_base64', None)

        if not raw_text and not image_base64:
            return jsonify({"error": "No text or image provided"}), 400

        messages = [
            {
                "role": "system",
                "content": "You are an automated accountant. Extract vendor, date (YYYY-MM-DD), total amount, vat amount, and vat rate (percentage) from the invoice. Return JSON only."
            }
        ]

        user_content = []
        
        if raw_text:
            user_content.append({"type": "text", "text": f"Analyze this invoice text:\n{raw_text}"})

        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}",
                    "detail": "high"
                }
            })

        user_content.append({
            "type": "text", 
            "text": "Return a JSON object with keys: 'vendor', 'date', 'total', 'vat', 'vat_rate'. Use numbers for amounts. If vat/rate is missing, use 0."
        })

        messages.append({"role": "user", "content": user_content})

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0
        )

        # Parse Response
        result_content = response.choices[0].message.content
        invoice_data = json.loads(result_content)

        # --- VALIDATION STEPS ---
        
        # 1. Rekognition Cross-Check
        rekognition_match = check_numbers_in_rekognition(invoice_data, raw_text)
        
        # 2. VAT Math Check
        vat_math_ok = validate_vat_math(invoice_data)

        if not rekognition_match or not vat_math_ok:
            error_reason = "No match AI vs Rekognition" if not rekognition_match else "VAT math validation failed"
            
            return jsonify({
                "status": "error",
                "data": invoice_data,
                "csv_row": f"ERROR,AI_ERROR - {error_reason},0,0,{get_current_timestamp()}"
            }), 200 
        
        # Prepare CSV Row
        vendor = invoice_data.get('vendor', 'Unknown').replace(',', ' ') 
        date = invoice_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        total = invoice_data.get('total', 0)
        vat = invoice_data.get('vat', 0)
        processed_at = get_current_timestamp()

        # Create the CSV Row
        csv_row = f"{date},{vendor},{total},{vat},{processed_at}"

        return jsonify({
            "status": "success",
            "data": invoice_data,
            "csv_row": csv_row
        }), 200

    except Exception as e:
        print(f"Error processing invoice: {e}")
        return jsonify({"error": str(e)}), 500

