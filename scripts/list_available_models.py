import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment")
    exit(1)

genai.configure(api_key=api_key)

print("Listing available models...")
try:
    models = genai.list_models()
    found_embedding = False
    for m in models:
        if 'embedContent' in m.supported_generation_methods:
            print(f"Name: {m.name}")
            print(f"Display Name: {m.displayName}")
            print(f"Description: {m.description}")
            print("-" * 20)
            found_embedding = True
    
    if not found_embedding:
        print("No models found with 'embedContent' capability.")

except Exception as e:
    print(f"Error listing models: {e}")
