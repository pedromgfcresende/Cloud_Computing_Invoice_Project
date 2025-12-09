import streamlit as st
import boto3
import pandas as pd
import io
import time


AWS_ACCESS_KEY = ""  
AWS_SECRET_KEY = ""  
BUCKET_NAME = "" 
REGION = "eu-central-1"                

# --- 2. CONFIGURATION ---
# Use the bucket name found in your lambda.py logic if needed, 
# or the one you created manually.

CSV_KEY = 'financial_report.csv'

# --- 3. CONNECT TO AWS ---
# We create the connection using the keys above. No installation required.
s3 = boto3.client(
    's3',
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

st.set_page_config(page_title="AI Accountant Live", layout="wide")
st.title("🤖 AI Accountant: Live Processing")
st.markdown("---")

# Split layout into two columns
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Upload Invoice")
    uploaded_file = st.file_uploader("Choose an image (JPG/PNG)", type=['jpg', 'jpeg', 'png'])

    if uploaded_file is not None:
        # Display the image
        st.image(uploaded_file, caption='Preview', use_column_width=True)
        
        if st.button("Process Invoice"):
            with st.spinner('Uploading to S3 to trigger Lambda...'):
                # Upload to S3
                # We rename the file to ensure uniqueness or keep original
                file_key = uploaded_file.name
                s3.upload_fileobj(uploaded_file, BUCKET_NAME, file_key)
                st.success(f"✅ Uploaded {file_key}! The AI is analyzing it now...")
                st.info("Wait approx 10-15 seconds for GPT-4 & Lambda to finish, then click Refresh.")

with col2:
    st.subheader("2. Financial Report (Live S3 Data)")
    
    if st.button("🔄 Refresh Data"):
        try:
            # Download CSV from S3
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=CSV_KEY)
            df = pd.read_csv(obj['Body'])
            
            # Sort by ProcessedAt if available to show newest first
            if 'ProcessedAt' in df.columns:
                df = df.sort_values(by='ProcessedAt', ascending=False)
            
            # Display highly visual table
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Total": st.column_config.NumberColumn(format="$%.2f"),
                    "VAT": st.column_config.NumberColumn(format="$%.2f"),
                    "ProcessedAt": st.column_config.DatetimeColumn(format="D MMM YYYY, h:mm a")
                }
            )
            
            # Show Metrics
            if not df.empty and 'Total' in df.columns:
                total_spend = df['Total'].sum()
                st.metric(label="Total Spend in Report", value=f"${total_spend:,.2f}")
                
        except s3.exceptions.NoSuchKey:
            st.warning("No CSV report found in S3 yet.")
        except Exception as e:
            st.error(f"Error reading S3: {e}")

st.markdown("---")
st.caption("Architecture: Streamlit -> S3 -> Lambda -> Rekognition + GPT-4o -> S3 CSV")