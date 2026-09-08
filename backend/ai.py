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
- Sound like a warm, reassuring person, the way a caring Indian nurse or
  health worker would talk to someone they know — calm, gentle, a little
  personal, never robotic or alarming.
- Do not open with scary-sounding warnings or long lists of dangerous
  possibilities unless the situation is genuinely an emergency. Most
  common symptoms are not emergencies, so don't make the patient more
  anxious than they already are — reassure first, then guide.
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

# Separate vision-capable model for analyzing uploaded
# medical report photos (prescriptions, lab results, etc.)
VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "qwen/qwen3.6-27b"
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
# SAFETY NET: STRIP ANY LEAKED REASONING
# ==========================================

def strip_reasoning_leftovers(text):
    """
    Some reasoning-capable models can occasionally leak their internal
    <think>...</think> chain-of-thought into the visible reply even when
    reasoning is turned off. This removes any such block as a safety net
    so the patient never sees raw model reasoning.
    """

    if not text:
        return text

    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # In case of an unclosed <think> tag (truncated output),
    # cut everything from that point onward.
    cleaned = re.sub(
        r"<think>.*$",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE
    )

    return cleaned.strip()


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
            return strip_reasoning_leftovers(text.strip())

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


# ==========================================
# ANALYZE UPLOADED MEDICAL REPORT PHOTO
# ==========================================

def analyze_report_image(image_data_url, patient_note=""):
    """
    Takes a base64 data-url of a photo (previous medical report,
    prescription, lab result, etc.) and returns a short, confident,
    plain-language explanation of what it shows.
    """

    instructions = (
        "You are a knowledgeable health assistant looking at a photo of a "
        "patient's previous medical report, prescription, or lab result. "
        "Read it and explain what it shows in confident, plain, everyday "
        "language - like a knowledgeable friend summarizing it for them, "
        "not like a transcription exercise.\n\n"
        "Cover: what type of document this is, the diagnosis or condition "
        "named, key medicines and what they're generally used for, and any "
        "test values that stand out as high/low. Then briefly say what the "
        "patient should keep in mind or ask their doctor about.\n\n"
        "Rules:\n"
        "- Do not think out loud, do not narrate your reading process, and "
        "do not show uncertainty word-by-word (no 'maybe this, maybe "
        "that'). Read it once, then answer directly and confidently.\n"
        "- If one specific word or phrase is genuinely illegible, skip "
        "it silently or mention it in a single short clause - never spend "
        "more than one sentence guessing about it.\n"
        "- No headers, no markdown, no bullet lists, no asterisks - just "
        "clear flowing paragraphs, 4-8 sentences total.\n"
        "- You are not a doctor and cannot give a final diagnosis; if "
        "something looks concerning, say so plainly and suggest showing "
        "it to a doctor.\n"
        "- If the image is unclear or is not a medical document at all, "
        "say that honestly in one line instead of guessing."
    )

    if patient_note:
        instructions += f"\n\nThe patient also added this note: {patient_note}"

    try:

        print(f"Analyzing report image using: {VISION_MODEL}")

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instructions},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url}
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.4,
            reasoning_effort="none",
            reasoning_format="hidden"
        )

        if not response or not response.choices:
            raise Exception("Empty response analyzing image")

        text = response.choices[0].message.content

        if text:
            return strip_reasoning_leftovers(text.strip())

        raise Exception("Model returned an empty analysis")

    except Exception as error:

        print("===================================")
        print("IMAGE ANALYSIS ERROR")
        print(f"Model: {VISION_MODEL}")
        print(f"Error: {error}")
        print("===================================")

        if is_quota_error(error):
            raise Exception("GROQ_QUOTA_EXCEEDED")

        raise Exception(
            friendly_error_message(error)

        )