import os
import json
import requests
import re
import boto3
import inspect
from botocore.exceptions import ClientError
from markdownify import markdownify as md
from google import genai
from google.genai import types

API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
STATE_FILE_KEY = "sync_state.json"
S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME", "my-optibot-state-bucket")

s3_client = boto3.client("s3")
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
client = genai.Client(api_key=api_key)

def load_state_from_s3():
    """Load the synchronization state from AWS S3."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=STATE_FILE_KEY)
        state_data = response['Body'].read().decode('utf-8')
        return json.loads(state_data)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print("State file not found on S3. Initializing a new sync session.")
            return {}
        else:
            print(f"Error connecting to S3: {e}")
            raise e

def save_state_to_s3(state):
    """Save the updated synchronization state back to AWS S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=STATE_FILE_KEY,
            Body=json.dumps(state, indent=4),
            ContentType="application/json"
        )
        print("Successfully saved sync state to S3.")
    except Exception as e:
        print(f"Failed to save state to S3: {e}")

def generate_slug(title):
    """Generate a URL-friendly slug from the article title."""
    slug = re.sub(r'[^a-zA-Z0-9\-]', '-', title.lower())
    return re.sub(r'\-+', '-', slug).strip('-')

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    print("Starting Scrape & Sync process via AWS Lambda...")
    
    # Fetch file list once from Gemini to optimize API calls (Fix N+1)
    print("Fetching existing files from Gemini for cleanup mapping...")
    try:
        existing_files = {f.display_name: f.name for f in client.files.list()}
    except Exception as e:
        print(f"Warning: Could not fetch existing files. {e}")
        existing_files = {}
    
    state = load_state_from_s3()
    new_state = {}
    
    response = requests.get(API_URL, params={"per_page": 100})
    if response.status_code != 200:
        print(f"Zendesk API connection failed with status code: {response.status_code}")
        return {"statusCode": 500, "body": "Zendesk API connection failed"}
        
    articles = response.json().get("articles", [])
    stats = {"added": 0, "updated": 0, "skipped": 0}
    
    for article in articles:
        art_id = str(article.get("id"))
        updated_at = article.get("updated_at")
        title = article.get("title", "Untitled")
        html_body = article.get("body", "")
        url = article.get("html_url", "")
        
        if not html_body:
            continue
            
        new_state[art_id] = updated_at
        slug = generate_slug(title)
        filename = f"{slug}.md"
        
        is_modified = False
        if art_id in state:
            if state[art_id] == updated_at:
                stats["skipped"] += 1
                continue
            else:
                stats["updated"] += 1
                is_modified = True
                print(f"[UPDATED] {title}")
        else:
            stats["added"] += 1
            print(f"[NEW] {title}")
            
        clean_md = md(html_body, heading_style="ATX", strip=['script', 'style'])
        final_content = f"# {title}\n\n**Article URL:** {url}\n\n---\n\n{clean_md}"
        
        temp_filepath = f"/tmp/{filename}"
        with open(temp_filepath, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        # Optimized old file cleanup logic
        if is_modified and filename in existing_files:
            print(f"Cleaning up older version of {filename} on Gemini.")
            try:
                client.files.delete(name=existing_files[filename])
            except Exception as e:
                print(f"Failed to delete old file {filename}: {e}")
            
        try:
            sig = inspect.signature(client.files.upload)
            valid_params = sig.parameters.keys()
            
            upload_kwargs = {
                "config": types.UploadFileConfig(
                    display_name=filename,
                    mime_type="text/plain"
                )
            }
            
            if "path" in valid_params:
                upload_kwargs["path"] = temp_filepath
            elif "file" in valid_params:
                upload_kwargs["file"] = temp_filepath
            else:
                for p in valid_params:
                    if p not in ["self", "config"]:
                        upload_kwargs[p] = temp_filepath
                        break
                        
            uploaded_file = client.files.upload(**upload_kwargs)
            print(f"Synced to Gemini: {filename} (State: {uploaded_file.state})")
        except Exception as e:
            print(f"Error uploading file {filename} to Gemini: {e}")
            
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

    save_state_to_s3(new_state)
    
    print("\n--- DAILY JOB SUMMARY ---")
    print(f"Added:    {stats['added']}")
    print(f"Updated:  {stats['updated']}")
    print(f"Skipped:  {stats['skipped']}")
    print("----------------------------\n")
    
    return {
        "statusCode": 200,
        "body": json.dumps(f"Sync completed. Added: {stats['added']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}")
    }