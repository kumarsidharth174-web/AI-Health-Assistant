from google import genai
import os
from dotenv import load_dotenv


load_dotenv()

# Defensive cleanup: removes accidental quotes or spaces that can
# get pasted into Render/host dashboards.
raw_key = os.getenv("GEMINI_API_KEY", "")
api_key = raw_key.strip().strip('"').strip("'")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found")


client = genai.Client(api_key=api_key)


MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash"
]


def generate_health_report(messages):

    conversation = ""

    for message in messages:
        conversation += f"{message['sender']}: {message['message']}\n"

    prompt = f"""
You are analyzing a patient's conversation
for an educational healthcare report.

Do NOT diagnose the patient.
You are not a doctor and this is not medical advice.

Create a clear report with these sections, using these
exact numbered headings:

1. Patient Summary
2. Reported Symptoms
3. Duration
4. Temperature or Vital Information
5. Relevant Information
6. Possible Concerns
7. General Recommendations
8. Emergency Warning
9. Information Missing

Use "Not provided" when information is unavailable.
Do not invent any detail the patient did not mention.
Keep the language simple and calm.

Conversation:

{conversation}
"""

    last_error = None

    for model in MODELS:

        try:
            response = client.models.generate_content(model=model, contents=prompt)

            if response.text:
                return response.text

        except Exception as error:
            last_error = error
            print(f"REPORT ERROR {model}: {error}")

    raise Exception(str(last_error))