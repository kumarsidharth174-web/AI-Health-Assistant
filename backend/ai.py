from google import genai
import os
import re
import json
import time
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")


client = genai.Client(api_key=api_key)


SYSTEM_PROMPT = """
You are an AI Healthcare Assistant.

Your role is to help patients understand their health concerns
and organize the information they provide.

IMPORTANT:

- You are not a doctor.
- Do not claim to diagnose a disease.
- Give general health information.
- Ask useful follow-up questions.
- Use simple and calm language.
- Pay attention to symptoms, duration, severity,
  temperature, medicines and medical history.
- Never invent patient information.
- If symptoms may represent an emergency,
  clearly recommend urgent medical care.
- Do not prescribe dangerous or restricted medicines.
- Remember the conversation context.
- The patient may write in Hindi, English or Hinglish
  (mixed Hindi-English). Reply in the same style/language
  the patient is using, in a warm and simple tone.
"""


# Current, supported Gemini models.
# If the first fails, the next is tried automatically.
MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash"
]


# ==========================================
# EMERGENCY KEYWORD DETECTION (runs locally, no API needed)
# ==========================================

EMERGENCY_PATTERNS = [
    r"chest pain", r"seene mein dard", r"sine mein dard",
    r"can'?t breathe", r"cannot breathe", r"difficulty breathing",
    r"saans nahi", r"saans lene mein takleef",
    r"unconscious", r"passed out", r"behosh",
    r"severe bleeding", r"bleeding a lot", r"bahut khoon",
    r"heart attack", r"dil ka daura",
    r"stroke", r"paralysis", "lakwa",
    r"seizure", r"fits", r"mirgi",
    r"suicide", r"kill myself", r"khudkushi",
    r"severe burn", r"poisoning", r"zeher",
    r"choking", r"gala ghut"
]

EMERGENCY_REGEX = re.compile("|".join(EMERGENCY_PATTERNS), re.IGNORECASE)


def check_emergency(text):
    """Return True if the message contains wording that could
    indicate a medical emergency."""

    if not text:
        return False

    return bool(EMERGENCY_REGEX.search(text))


# ==========================================
# FRIENDLY ERROR MESSAGES
# ==========================================

def friendly_error_message(error_text):

    text = str(error_text).lower()

    if "429" in text or "resource_exhausted" in text or "quota" in text:
        return (
            "The AI assistant is receiving too many requests right now "
            "(usage limit reached). Please wait a minute and try again."
        )

    if "404" in text or "not_found" in text or ("model" in text and "not found" in text):
        return "The AI model is temporarily unavailable. Please try again in a moment."

    if "503" in text or "unavailable" in text:
        return "The AI service is busy right now. Please try again shortly."

    if "api key" in text or "permission_denied" in text or "unauthenticated" in text or "401" in text or "403" in text:
        return (
            "The AI service could not be reached because of a "
            "configuration problem. Please check the server's API key."
        )

    if "timeout" in text or "connection" in text or "network" in text:
        return (
            "Could not reach the AI service due to a network issue. "
            "Please check your internet connection and try again."
        )

    return "The AI assistant could not process that right now. Please try again in a few seconds."


# ==========================================
# CHAT RESPONSE (WITH CONVERSATION MEMORY)
# ==========================================

def get_ai_response(user_message, previous_messages=None):

    if previous_messages is None:
        previous_messages = []

    conversation = ""

    for message in previous_messages:
        conversation += f"{message['sender']}: {message['message']}\n"

    prompt = f"""
{SYSTEM_PROMPT}

Previous patient conversation:

{conversation}

Latest patient message:

Patient: {user_message}

Respond naturally to the latest message.
Use the previous conversation when relevant.
"""

    last_error = None

    for model in MODELS:

        for attempt in range(2):

            try:
                print(f"Trying {model}, attempt {attempt + 1}")

                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                if response.text:
                    return response.text

            except Exception as error:
                last_error = error
                print(f"AI ERROR: {model}")
                print(str(error))
                time.sleep(1)

    raise Exception(str(last_error))


# ==========================================
# HEALTH INFORMATION EXTRACTION
# ==========================================

def extract_health_info(messages):

    default = {
        "symptoms": "Not provided",
        "duration": "Not provided",
        "temperature": "Not provided",
        "severity": "Not provided",
        "medicines": "Not provided",
        "history": "Not provided"
    }

    if not messages:
        return default

    conversation = ""

    for message in messages:
        conversation += f"{message['sender']}: {message['message']}\n"

    prompt = f"""
Read this patient conversation and extract ONLY information the
patient actually stated. Do not guess or invent anything.

If a field was not mentioned, use exactly: "Not provided"

Respond with ONLY valid JSON (no markdown, no extra text) in this
exact shape:

{{
  "symptoms": "...",
  "duration": "...",
  "temperature": "...",
  "severity": "...",
  "medicines": "...",
  "history": "..."
}}

Conversation:

{conversation}
"""

    for model in MODELS:

        try:
            response = client.models.generate_content(model=model, contents=prompt)

            raw_text = response.text.strip()
            raw_text = re.sub(r"^```json|^```|```$", "", raw_text, flags=re.MULTILINE).strip()

            data = json.loads(raw_text)

            for key in default:
                if key not in data or not data[key]:
                    data[key] = "Not provided"

            return data

        except Exception as error:
            print(f"EXTRACTION ERROR ({model}): {error}")
            continue

    return default