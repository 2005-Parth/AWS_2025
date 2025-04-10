import streamlit as st
import boto3
from botocore.exceptions import ClientError
import os
import tempfile
import shutil

# Set page config
st.set_page_config(page_title="AWS Workshop - IAM User Creator", layout="centered")

# Initialize session state
if 'success_message' not in st.session_state:
    st.session_state.success_message = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

# App title and description
st.title("AWS Workshop - IAM User Creator")
st.markdown("This tool creates IAM users for workshop participants.")

# Function to get AWS credentials
def get_aws_credentials():
    if hasattr(st, 'secrets') and 'aws' in st.secrets:
        return {
            'aws_access_key_id': st.secrets.aws.aws_access_key_id,
            'aws_secret_access_key': st.secrets.aws.aws_secret_access_key,
            'region_name': st.secrets.aws.get('region_name', 'ap-south-1')
        }
    elif all(key in os.environ for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']):
        return {
            'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
            'region_name': os.environ.get('AWS_REGION', 'us-east-1')
        }
    return None

# Function to create password
def create_password(username):
    return f"{username}@encode2025"

# Function to create IAM user
def create_iam_user(username, group_name="AWS_Participants"):
    try:
        aws_credentials = get_aws_credentials()
        if not aws_credentials:
            return {"success": False, "error": "AWS credentials not found."}
        
        iam = boto3.client('iam', 
                         aws_access_key_id=aws_credentials['aws_access_key_id'],
                         aws_secret_access_key=aws_credentials['aws_secret_access_key'],
                         region_name=aws_credentials['region_name'])
        
        response = iam.create_user(UserName=username)
        password = create_password(username)
        
        iam.create_login_profile(UserName=username, Password=password, PasswordResetRequired=False)
        iam.add_user_to_group(GroupName=group_name, UserName=username)
        
        return {
            "success": True,
            "username": username,
            "password": password,
            "arn": response['User']['Arn'],
            "console_url": "https://console.aws.amazon.com/"
        }
    except ClientError as e:
        return {"success": False, "error": str(e)}

# Function to create credentials text
def create_credentials_text(username, password, arn):
    return f"""AWS WORKSHOP CREDENTIALS
------------------------
Username: {username}
Password: {password}
ARN: {arn}
Console URL: https://console.aws.amazon.com/
"""

# Function to create and return a temporary file
def create_temp_file(content, filename):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path, temp_dir

# User input form
with st.form("user_form"):
    username = st.text_input("Enter Username")
    submitted = st.form_submit_button("Create IAM User")
    
    if submitted:
        if not username:
            st.session_state.error_message = "Username cannot be empty!"
            st.session_state.success_message = None
        else:
            result = create_iam_user(username)
            if result["success"]:
                st.session_state.success_message = f"User '{username}' created!"
                st.session_state.error_message = None
                st.session_state.result = result
            else:
                st.session_state.error_message = f"Error: {result['error']}"
                st.session_state.success_message = None

# Display results
if st.session_state.success_message:
    st.success(st.session_state.success_message)
    if 'result' in st.session_state:
        result = st.session_state.result
        
        st.write("### User Details")
        st.write(f"Username: {result['username']}")
        st.write(f"Password: {result['password']}")
        st.write(f"ARN: {result['arn']}")
        st.write(f"Console URL: {result['console_url']}")
        
        credentials_text = create_credentials_text(result['username'], result['password'], result['arn'])
        
        # Create temporary file
        filename = f"{result['username']}_credentials.txt"
        try:
            file_path, temp_dir = create_temp_file(credentials_text, filename)
            
            # Provide file for download
            with open(file_path, 'rb') as f:
                st.download_button(
                    label="Download Credentials",
                    data=f,
                    file_name=filename,
                    mime="text/plain",
                    key=f"download_{result['username']}"
                )
            
            # Clean up temporary directory after download
            def cleanup():
                shutil.rmtree(temp_dir)
            
            st.write("### Alternative: Copy Text")
            st.code(credentials_text, language="text")
            
            # Cleanup warning
            st.warning("Please download the file now. The temporary file will be deleted after this session.")
            
        except Exception as e:
            st.error(f"Error creating temporary file: {str(e)}")
            st.code(credentials_text, language="text")  # Fallback to showing text
    

if st.session_state.error_message:
    st.error(st.session_state.error_message)

st.markdown("---")