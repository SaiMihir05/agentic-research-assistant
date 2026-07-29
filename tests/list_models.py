import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"Loaded API key: {api_key[:10]}...")

genai.configure(api_key=api_key)
try:
    for m in genai.list_models():
        print(f"- {m.name} (supports: {m.supported_generation_methods})")
except Exception as e:
    print(f"Error: {e}")
