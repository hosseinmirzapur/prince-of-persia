import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent" # Example URL, verify with Gemini API docs

def get_gemini_response(prompt):
    """Sends a prompt to the Gemini API and returns the response."""
    if not GEMINI_API_KEY:
        print("کلید API جیمینای یافت نشد.") # Gemini API key not found.
        return None

    headers = {
        "Content-Type": "application/json",
    }

    params = {
        "key": GEMINI_API_KEY
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=data)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"خطا در فراخوانی API جیمینای: {e}") # Error calling Gemini API: {e}
        return None

if __name__ == '__main__':
    # Example usage
    test_prompt = "What is the capital of France?"
    response_data = get_gemini_response(test_prompt)
    if response_data:
        # Basic parsing, adjust based on actual Gemini API response structure
        try:
            print("پاسخ جیمینای:") # Gemini Response:
            for part in response_data['candidates'][0]['content']['parts']:
                print(part['text'])
        except (KeyError, IndexError) as e:
            print(f"پاسخ جیمینای قابل تجزیه نبود: {e}") # Could not parse Gemini response: {e}
            print("پاسخ خام:", response_data) # Raw response:
