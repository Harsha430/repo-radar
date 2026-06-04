import os
from dotenv import load_dotenv
from groq import Groq

# Load from .env
load_dotenv()

groq_key = os.getenv("GROQ_API_KEY")

print(f"Loaded Groq Key: {groq_key[:8]}...{groq_key[-4:]}" if groq_key else "NO KEY FOUND IN .ENV")

try:
    print("Sending test request to Groq API...")
    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say 'Groq is working perfectly!'"}
        ]
    )
    print("\nSUCCESS! Response from Groq:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"\nFAILED: {e}")
