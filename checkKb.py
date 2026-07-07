import os
from google import genai
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("--- FILE LIST ON GEMINI KNOWLEDGE BASE ---")
files = client.files.list()
for f in files:
    print(f"Display name: {f.display_name} | State: {f.state} | ID: {f.name}")
print("-------------------------------------------")