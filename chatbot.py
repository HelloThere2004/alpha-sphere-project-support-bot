import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""

def query_bot():
    print("Calling assistant...")
    
    print("Scanning uploaded files on Google Cloud...")
    all_files = list(client.files.list())
    uploaded_files = all_files[:40] 
    
    print(f"Successfully retrieved {len(uploaded_files)} files.")
    
    question = "How do I add a YouTube video?"
    print(f"\nUser: {question}")
    
    contents = uploaded_files + [question]
    
    try:
        print("Sending request to gemini-2.5-flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )
        print(f"\nOptiBot:\n{response.text}")
        
    except Exception as e:
        print(f"\nAPI Error: {e}")
        # Fallback to the Pro version if Flash hits a snag
        print("\nRetrying with gemini-2.5-pro model...")
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )
        print(f"\nOptiBot:\n{response.text}")

if __name__ == "__main__":
    query_bot()