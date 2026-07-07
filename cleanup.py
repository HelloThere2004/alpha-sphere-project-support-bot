import os
from google import genai
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Beginning Gemini Knowledge Base cleanup...")
try:
    # Get the list of all existing files
    files = client.files.list()
    count = 0
    for f in files:
        print(f"Deleting: {f.display_name} (ID: {f.name})")
        client.files.delete(name=f.name)
        count += 1
    print(f"Successfully cleaned up {count} files on Gemini!")
except Exception as e:
    print(f"Error: {e}")