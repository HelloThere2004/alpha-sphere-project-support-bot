import os
import json
import requests
import re
import inspect
from markdownify import markdownify as md
from google import genai
from google.genai import types

API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
STATE_FILE = "sync_state.json"

api_key = os.environ.get("API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def load_state():
    """Load the local synchronization state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    """Save the updated synchronization state locally."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

def generate_slug(title):
    """Generate a URL-friendly slug from the article title."""
    slug = re.sub(r'[^a-zA-Z0-9\-]', '-', title.lower())
    return re.sub(r'\-+', '-', slug).strip('-')

def main():
    """Local execution entry point."""
    print("Starting Local Scrape & Sync process...")
    if not api_key:
        print("Error: API_KEY environment variable is missing.")
        exit(1)

    print("Fetching existing files from Gemini for cleanup mapping...")
    try:
        existing_files = {f.display_name: f.name for f in client.files.list()}
    except Exception as e:
        print(f"Warning: Could not fetch existing files. {e}")
        existing_files = {}

    state = load_state()
    new_state = {}
    
    response = requests.get(API_URL, params={"per_page": 100})
    if response.status_code != 200:
        print(f"Zendesk API connection failed with status code: {response.status_code}")
        exit(1)
        
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
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_content)
            
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
                upload_kwargs["path"] = filename
            elif "file" in valid_params:
                upload_kwargs["file"] = filename
            else:
                for p in valid_params:
                    if p not in ["self", "config"]:
                        upload_kwargs[p] = filename
                        break
                        
            uploaded_file = client.files.upload(**upload_kwargs)
            print(f"Synced to Gemini: {filename} (State: {uploaded_file.state})")
        except Exception as e:
            print(f"Error uploading file {filename} to Gemini: {e}")
            
        if os.path.exists(filename):
            os.remove(filename)

    save_state(new_state)
    
    print("\n--- DAILY JOB SUMMARY ---")
    print(f"Added:    {stats['added']}")
    print(f"Updated:  {stats['updated']}")
    print(f"Skipped:  {stats['skipped']}")
    print("----------------------------\n")
    
    exit(0)

if __name__ == "__main__":
    main()