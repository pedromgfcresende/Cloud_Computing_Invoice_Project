import json
import boto3
import os
import io
import csv
import urllib.parse
from datetime import datetime
import base64
import urllib.request



s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')


BEANSTALK_URL = "http://invoiceaiagent-env.eba-sh8rsafh.eu-central-1.elasticbeanstalk.com/" 
ENDPOINT = f"{BEANSTALK_URL}/process_invoice"


# ---- Auxiliar Functions ----

def get_text_from_rekognition(bucket, key):
    """
    Use AWS Rekognition to read raw text from the image.
    This is passed to the AI to validate the numbers it finds.
    """
    response = rekognition_client.detect_text(
        Image={'S3Object': {'Bucket': bucket, 'Name': key}}
    )

    lines = [item['DetectedText'] for item in response['TextDetections'] if item['Type'] == 'LINE']
    text = "\n".join(lines)
    return text

def get_image_base64(bucket, key):
    """
    Download image from S3 and convert to Base64 string for the API.
    """
    file_obj = s3_client.get_object(Bucket=bucket, Key=key)
    file_content = file_obj['Body'].read()
    return base64.b64encode(file_content).decode('utf-8')

def call_beanstalk_service(raw_text, image_base64):
    """
    Send the text and image to your Flask microservice on Elastic Beanstalk.
    """
    payload = {
        "text": raw_text,
        "image_base64": image_base64
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except urllib.error.URLError as e:
        # Return a fallback error row if the service is down
        return {"csv_row": f"ERROR,SERVICE_UNAVAILABLE - {str(e)},0,0,ERROR"}

def update_csv_in_s3(bucket, data):
    """
    Append the new data to a CSV file in S3
    """
    csv_key = 'financial_report.csv'
    existing_lines = []

    try:
        obj = s3_client.get_object(Bucket=bucket, Key=csv_key)
        existing_lines = obj['Body'].read().decode('utf-8').splitlines()
    except:
        existing_lines = ["Date,Vendor,Total,VAT,ProcessedAt"] 

    new_line = f"{data.get('date')},{data.get('vendor')},{data.get('total')},{data.get('vat')},{datetime.now().isoformat()}"
    existing_lines.append(new_line)

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    for line in existing_lines:
        writer.writerow(line.split(','))
        
    s3_client.put_object(Bucket=bucket, Key=csv_key, Body=csv_buffer.getvalue())

def lambda_handler(event, context):
    try:

        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

        if key.endswith('.csv') or key.endswith('.json'):
            return {'statusCode': 200, 'body': 'Skipped'}

        raw_text = get_text_from_rekognition(bucket, key)
        image_base64 = get_image_base64(bucket, key)
        
        # 3. Process with AI (Beanstalk)
        service_response = call_beanstalk_service(raw_text, image_base64)
        csv_row = service_response.get('csv_row')
        
        # 4. Save Result
        if csv_row:
            update_csv_in_s3(bucket, csv_row)

        return {'statusCode': 200, 'body': 'Success'}
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise e
        
