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
    raise ValueError("GROQ_API_KEY not found in environment variables")

print(
    f"GROQ_API_KEY loaded, "
    f"length={len(api_key)}, "
    f"starts_with={api_key[:6]}***"
)


# ==========================================
# GROQ CLIENT
# (Groq's API is OpenAI-compatible, so we reuse
#  the OpenAI SDK and just point it at Groq's URL)
# ==========================================

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    timeout=20.0
)


# ==========================================
# SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """
You are an AI Healthcare Assistant having a real conversation with a patient.
Talk like a caring, knowledgeable person texting back — not like a medical
pamphlet or a doctor writing a report.

STRICT STYLE RULES:

- Keep replies SHORT. 3-6 sentences for a normal message. Only go longer if
  the situation is genuinely an emergency and safety info must be given.
- Do NOT use markdown formatting: no headers (##), no bold (**text**), no
  tables, no bullet-point lists, no emojis. Just write in plain flowing
  sentences and short paragraphs, like a normal chat message.
- Ask ONE follow-up question at a time, not a numbered list of five
  questions. Pick the single most useful thing to ask next.
- Don't repeat generic disclaimers or the same safety checklist every
  message — say it once if truly relevant, not every turn.
- Sound natural and human, like a knowledgeable friend, not a form or an
  encyclopedia entry.

CONTENT RULES:

- You are not a doctor and cannot diagnose. Give general health guidance.
- Pay attention to symptoms, duration, severity, temperature, medicines,
  and medical history the patient has already shared — don't ask again
  for things they already told you.
- Never invent patient information.
- If symptoms sound like a real emergency, say so plainly and clearly and
  tell them to seek urgent care — briefly, not with a big table.
- Do not prescribe dangerous or restricted medicines.
- Remember the conversation context.
- The patient may write in Hindi, English or Hinglish (mixed). Reply in
  the same language/style they are using — if they write in Hinglish,
  reply in Hinglish, not formal Hindi or English.
"""


# ==========================================
# MODEL
# ==========================================

# Use one model only.
# This prevents unnecessary API calls when quota is exhausted.

MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)


# ==========================================
# EMERGENCY KEYWORD DETECTION
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
    """
    Return True if the message contains wording
    that could indicate a medical emergency.
    """

    if not text:
        return False

    return bool(EMERGENCY_REGEX.search(text))


# ==========================================
# FRIENDLY ERROR MESSAGES
# ==========================================

def friendly_error_message(error_text):

    text = str(error_text).lower()

    # OpenAI quota / rate limit
    if (
        "429" in text
        or "resource_exhausted" in text
        or "quota" in text
        or "rate limit" in text
        or "insufficient_quota" in text
    ):
        return (
            "The AI assistant has reached its current usage limit. "
            "Please wait a little while and try again."
        )

    # Model not found
    if (
        "404" in text
        or "not_found" in text
        or "model not found" in text
        or "does not exist" in text
    ):
        return (
            "The AI model is temporarily unavailable. "
            "Please try again later."
        )

    # Service unavailable
    if (
        "503" in text
        or "service unavailable" in text
        or "temporarily unavailable" in text
    ):
        return (
            "The AI service is busy right now. "
            "Please try again shortly."
        )

    # API key / permission
    if (
        "api key" in text
        or "permission_denied" in text
        or "unauthenticated" in text
        or "incorrect api key" in text
        or "401" in text
        or "403" in text
    ):
        return (
            "The AI service could not be accessed because "
            "of an API configuration problem."
        )

    # Timeout
    if (
        "timeout" in text
        or "timed out" in text
    ):
        return (
            "The AI service took too long to respond. "
            "Please try again."
        )

    # Network
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
# CHECK QUOTA ERROR
# ==========================================

def is_quota_error(error):

    text = str(error).lower()

    return (
        "429" in text
        or "resource_exhausted" in text
        or "quota" in text
        or "rate limit" in text
        or "insufficient_quota" in text
    )


# ==========================================
# CHAT RESPONSE
# ==========================================

def get_ai_response(user_message, previous_messages=None):

    if previous_messages is None:
        previous_messages = []

    # Safety: make sure user message is not empty
    user_message = str(user_message or "").strip()

    if not user_message:
        return "Please tell me what health problem you are experiencing."

    # ======================================
    # BUILD CONVERSATION AS CHAT MESSAGES
    # ======================================

    chat_messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    for message in previous_messages:

        sender = message.get("sender", "patient")
        text = message.get("message", "")

        role = "assistant" if sender == "ai" else "user"

        chat_messages.append({
            "role": role,
            "content": text
        })

    chat_messages.append({
        "role": "user",
        "content": user_message
    })

    # ======================================
    # ONLY ONE API REQUEST
    # ======================================

    try:

        print(f"Calling OpenAI model: {MODEL}")

        response = client.chat.completions.create(
            model=MODEL,
            messages=chat_messages,
            max_tokens=280,
            temperature=0.6
        )

        if not response or not response.choices:
            raise Exception("Empty response from OpenAI")

        text = response.choices[0].message.content

        if text:
            return text.strip()

        raise Exception("OpenAI returned an empty response")

    except Exception as error:

        print("===================================")
        print("AI ERROR")
        print(f"Model: {MODEL}")
        print(f"Error: {error}")
        print("===================================")

        # IMPORTANT:
        # If quota is exhausted, immediately stop.
        # Do NOT try another model.
        if is_quota_error(error):
            raise Exception(
                "OPENAI_QUOTA_EXCEEDED"
            )

        raise Exception(
            friendly_error_message(error)
        )


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

    # ======================================
    # BUILD CONVERSATION
    # ======================================

    conversation_parts = []

    for message in messages:

        sender = message.get("sender", "user")
        text = message.get("message", "")

        conversation_parts.append(
            f"{sender}: {text}"
        )

    conversation = "\n".join(conversation_parts)

    # ======================================
    # EXTRACTION PROMPT
    # ======================================

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

    # ======================================
    # ONE EXTRACTION REQUEST
    # ======================================

    try:

        print(f"Extracting health information using: {MODEL}")

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        if not response or not response.choices:
            return default

        raw_text = response.choices[0].message.content

        if not raw_text:
            return default

        raw_text = raw_text.strip()

        # Remove markdown JSON fences (safety net)
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

        # ==================================
        # ENSURE ALL REQUIRED FIELDS EXIST
        # ==================================

        for key in default:

            if key not in data:
                data[key] = "Not provided"

            elif not data[key]:
                data[key] = "Not provided"

        return data

    except Exception as error:

        print("===================================")
        print("HEALTH EXTRACTION ERROR")
        print(error)
        print("===================================")

        # If quota is exhausted, don't retry.
        # Returning default keeps the server alive.

        return default
