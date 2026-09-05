from google import genai
import os
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:

    raise ValueError(
        "GEMINI_API_KEY not found"
    )


client = genai.Client(
    api_key=api_key
)


def generate_health_report(messages):

    conversation = ""


    for message in messages:

        sender = message["sender"]

        text = message["message"]

        conversation += (
            f"{sender}: {text}\n"
        )


    prompt = f"""
You are analyzing a patient's conversation
for an educational healthcare report.

Do NOT diagnose the patient.

Create a clear report with these sections:

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

Conversation:

{conversation}
"""


    models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash"
    ]


    last_error = None


    for model in models:

        try:

            response = client.models.generate_content(

                model=model,

                contents=prompt

            )

            return response.text


        except Exception as error:

            last_error = error

            print(
                f"REPORT ERROR {model}: {error}"
            )


    raise Exception(
        f"Report generation failed: {last_error}"
    )