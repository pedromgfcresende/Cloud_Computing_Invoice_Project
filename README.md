
# AI-Powered Invoice Processing Pipeline

This project is an automated, serverless invoice processing system. It allows users to upload invoice images, automatically extracts financial data (Vendor, Date, Total, VAT) using GPT-4o and AWS Rekognition, performs math validation, and aggregates the results into a live CSV financial report.

## Project Structure

  * [cite_start]**`application.py`**: A Flask microservice (intended for Elastic Beanstalk) that handles the AI extraction logic, VAT math validation, and data formatting[cite: 1].
  * **`lambda.py`**: An AWS Lambda function that triggers on S3 uploads. It acts as the orchestrator: grabbing text via Rekognition, calling the Flask AI service, and saving results to CSV.
  * **`testing.py`**: A local script to test the Flask endpoint with mock text or images.
  * **`requirements.txt`**: Python dependencies for the Flask environment.

-----

## Architecture Workflow

1.  **User Interface**: The user uploads an invoice image via the **Streamlit Dashboard** (`dashboard.py`).
2.  **Storage Trigger**: The image is saved to an **AWS S3 Bucket**, which triggers the **Lambda Function**.
3.  **OCR**: The Lambda function (`lambda.py`) calls **AWS Rekognition** to extract raw text from the image.
4.  **AI Analysis**: The Lambda sends the image (Base64) and raw text to the **Flask Application** (`application.py`).
5.  **Extraction & Validation**:
      * GPT-4o extracts the Vendor, Date, Total, and VAT.
      * [cite_start]**Cross-Check**: The app verifies that extracted numbers actually exist in the raw Rekognition text[cite: 1].
      * [cite_start]**Math Check**: The app verifies that `Total` matches the `VAT` + `Rate` logic[cite: 1].
6.  **Reporting**: The Lambda appends the validated data to `financial_report.csv` in the S3 bucket.
7.  **Visualization**: The Streamlit dashboard reads the updated CSV from S3 and displays the metrics.

-----

## Prerequisites

  * **Python 3.9+**
  * **AWS Account** with access to S3, Lambda, Rekognition, and Elastic Beanstalk.
  * **OpenAI API Key** (for GPT-4o).

-----

## Configuration & Setup

### 1\. Flask Microservice (Elastic Beanstalk)

This service handles the intelligence.

1.  Ensure `requirements.txt` is present.
2.  Set the environment variable `OPENAI_API_KEY` in your deployment environment (e.g., Elastic Beanstalk configuration).
3.  Deploy `application.py` to AWS Elastic Beanstalk.

### 2\. AWS Lambda (Orchestrator)

This connects S3 to the Flask app.

1.  Create a Lambda function using the code in `lambda.py`.
2.  **Permissions**: Give the Lambda execution role permissions for:
      * `s3:GetObject` & `s3:PutObject`
      * `rekognition:DetectText`
3.  **Environment**: Update the `BEANSTALK_URL` variable in `lambda.py` to point to your deployed Flask app.

### 3\. S3 Bucket

1.  Create a bucket (e.g., `invoice-project-team5`).
2.  Configure an **Event Notification** on this bucket to trigger the Lambda function on `PUT` events (suffix `.jpg`, `.png`).

### 4\. Dashboard (Local or Hosted)

1.  Install dependencies:
    ```bash
    pip install streamlit boto3 pandas
    ```
2.  Open `dashboard.py` and update the `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, and `BUCKET_NAME`.

-----

## Usage

### Running the Dashboard

Start the user interface locally:

```bash
streamlit run dashboard.py
```

1.  **Upload Invoice**: Use the left column to upload a `.jpg` or `.png` invoice.
2.  **Wait**: The file uploads to S3 -\> triggers Lambda -\> calls AI. This takes \~10-15 seconds.
3.  **Refresh**: Click "Refresh Data" in the right column to view the updated financial table.

### Testing the API Locally

You can test the Flask logic without deploying to AWS using `testing.py`.

1.  Run the Flask app locally:
    ```bash
    export OPENAI_API_KEY="sk-..."
    python application.py
    ```
2.  In a separate terminal, run the test script:
    ```bash
    python testing.py
    ```
    *This will send a mock invoice text to your local endpoint and print the JSON result.*

-----

## Validation Features

The system implements strict "Hallucination Guards" in `application.py`:

  * **Rekognition Cross-Check**: If GPT extract a number (e.g., "100.00"), the system ensures that number physically appears in the raw text detected by AWS Rekognition. [cite_start]If not, it flags an error[cite: 1].
  * **VAT Math Logic**: It calculates if `Total / (1 + VAT_Rate) * VAT_Rate` roughly equals the extracted `VAT Amount`. [cite_start]If the math doesn't add up, the invoice is flagged[cite: 1].

-----

### Known Issues / Troubleshooting

  * **CSV Format**: Ensure `financial_report.csv` headers in S3 match what the dashboard expects (`Total`, `VAT`, `ProcessedAt`).
  * **Lambda Timeout**: Ensure your Lambda timeout is set to at least **30 seconds**, as GPT-4o and network requests can take time.