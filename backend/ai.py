from openai import OpenAI
import os
import re
import json
from dotenv import load_dotenv

# ==========================================
# ENVIRONMENT
# ==========================================

load_dotenv()

raw_key = os.getenv("GROQ_API_KEY", "")
api_key = raw_key.strip().strip('"').strip("'")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY not found in environment variables"
    )

print(
    f"GROQ_API_KEY loaded, "
    f"length={len(api_key)}, "
    f"starts_with={api_key[:6]}***"
)

# ==========================================
# GROQ CLIENT
# ==========================================

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0
)

# ==========================================
# MODEL
# ==========================================

MODEL = "llama-3.3-70b-versatile"

print(f"GROQ MODEL: {MODEL}")

# ==========================================
# SYSTEM PROMPT
# ==========================================

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
- The patient may write in Hindi, English or Hinglish.
- Reply in the same style/language the patient is using.
- Keep the response useful, calm and reasonably short.
"""

# ==========================================
# EMERGENCY DETECTION
# ==========================================

EMERGENCY_PATTERNS = [
    r"chest pain",
    r"seene mein dard",
    r"sine mein dard",
    r"can't breathe",
    r"cannot breathe",
    r"difficulty breathing",
    r"saans nahi",
    r"saans lene mein takleef",
    r"unconscious",
    r"passed out",
    r"behosh",
    r"severe bleeding",
    r"bleeding a lot",
    r"bahut khoon",
    r"heart attack",
    r"dil ka daura",
    r"stroke",
    r"paralysis",
    r"lakwa",
    r"seizure",
    r"fits",
    r"mirgi",
    r"suicide",
    r"kill myself",
    r"khudkushi",
    r"severe burn",
    r"poisoning",
    r"zeher",
    r"choking",
    r"gala ghut"
]

EMERGENCY_REGEX = re.compile(
    "|".join(EMERGENCY_PATTERNS),
    re.IGNORECASE
)


def check_emergency(text):
    if not text:
        return False

    return bool(EMERGENCY_REGEX.search(text))


# ==========================================
# FRIENDLY ERROR
# ==========================================

def friendly_error_message(error):

    text = str(error).lower()

    if (
        "429" in text
        or "quota" in text
        or "rate limit" in text
        or "too many requests" in text
    ):
        return (
            "The AI assistant has reached its current usage limit. "
            "Please wait a little while and try again."
        )

    if (
        "401" in text
        or "403" in text
        or "api key" in text
        or "authentication" in text
        or "unauthorized" in text
    ):
        return (
            "The AI service could not be accessed because "
            "of an API configuration problem."
        )

    if (
        "404" in text
        or "model not found" in text
        or "does not exist" in text
        or "not_found" in text
    ):
        return (
            "The AI model is temporarily unavailable. "
            "Please try again later."
        )

    if (
        "timeout" in text
        or "timed out" in text
    ):
        return (
            "The AI service took too long to respond. "
            "Please try again."
        )

    if (
        "connection" in text
        or "network" in text
    ):
        return (
            "Could not reach the AI service due to a network issue. "
            "Please try again."
        )

    return (
        "The AI assistant could not process that right now. "
        "Please try again in a few seconds."
    )


# ==========================================
# CHAT RESPONSE
# ==========================================

def get_ai_response(user_message, previous_messages=None):

    if previous_messages is None:
        previous_messages = []

    user_message = str(user_message or "").strip()

    if not user_message:
        return (
            "Please tell me what health problem "
            "you are experiencing."
        )

    chat_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # ======================================
    # PREVIOUS CONVERSATION
    # ======================================

    for message in previous_messages:

        sender = message.get("sender", "patient")
        text = message.get("message", "")

        if not text:
            continue

        role = (
            "assistant"
            if sender == "ai"
            else "user"
        )

        chat_messages.append({
            "role": role,
            "content": str(text)
        })

    # ======================================
    # CURRENT USER MESSAGE
    # ======================================

    chat_messages.append({
        "role": "user",
        "content": user_message
    })

    # ======================================
    # GROQ REQUEST
    # ======================================

    try:

        print("\n======================================")
        print("GROQ REQUEST STARTED")
        print(f"MODEL: {MODEL}")
        print(f"MESSAGE: {user_message}")
        print("======================================")

        response = client.chat.completions.create(
            model=MODEL,
            messages=chat_messages,
            temperature=0.4,
            max_tokens=700
        )

        print("GROQ RESPONSE RECEIVED")

        if not response:
            raise Exception(
                "Groq returned an empty response object"
            )

        if not response.choices:
            raise Exception(
                "Groq returned no choices"
            )

        text = response.choices[0].message.content

        if not text:
            raise Exception(
                "Groq returned empty message content"
            )

        print("GROQ REQUEST SUCCESS")
        print("======================================\n")

        return text.strip()

    except Exception as error:

        print("\n======================================")
        print("GROQ API ERROR")
        print("======================================")
        print("ERROR TYPE:", type(error).__name__)
        print("ERROR:", str(error))
        print("======================================\n")

        raise


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

    conversation_parts = []

    for message in messages:

        sender = message.get(
            "sender",
            "patient"
        )

        text = message.get(
            "message",
            ""
        )

        if text:
            conversation_parts.append(
                f"{sender}: {text}"
            )

    conversation = "\n".join(
        conversation_parts
    )

    prompt = f"""
Read this patient conversation and extract ONLY information
the patient actually stated.

Do not guess or invent anything.

If a field was not mentioned, use exactly:

"Not provided"

Respond with ONLY valid JSON.

Required format:

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

    try:

        print(
            f"Extracting health information using {MODEL}"
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=500
        )

        if not response or not response.choices:
            return default

        raw_text = (
            response.choices[0]
            .message.content
        )

        if not raw_text:
            return default

        raw_text = raw_text.strip()

        raw_text = re.sub(
            r"^```json\s*",
            "",
            raw_text,
            flags=re.IGNORECASE
        )

        raw_text = re.sub(
            r"^```\s*",
            "",
            raw_text
        )

        raw_text = re.sub(
            r"\s*```$",
            "",
            raw_text
        )

        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        for key in default:

            if key not in data:
                data[key] = "Not provided"

            elif not data[key]:
                data[key] = "Not provided"

        return data

    except Exception as error:

        print("\n======================================")
        print("HEALTH EXTRACTION ERROR")
        print("======================================")
        print("ERROR:", str(error))
        print("======================================\n")

        return default