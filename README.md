# AI Health Assistant

A simple web-based health assistant that lets a patient chat about their symptoms, upload a photo of a medical report, and get a plain-language summary or a downloadable health report at the end of the conversation. Built as our submission for Smart India Hackathon (SIH) — internal round.

## Why we built this

Most people don't understand their prescriptions or lab reports properly, and they either ignore small symptoms or panic and rush to a doctor for things that could've been clarified in two minutes. We wanted something in between — a chat-based assistant that talks like a knowledgeable friend, not a medical pamphlet, and that can also read a report photo and explain it in normal language.

## What it actually does

- **Chat with the assistant** — describe how you're feeling, and it responds conversationally, asking one relevant follow-up at a time instead of dumping a checklist on you.
- **Upload a report photo** — snap or upload an image of a prescription/lab report, and the assistant reads and explains it.
- **Patient profile & history** — every patient gets an ID, and past conversations are saved so the assistant has context instead of starting from zero each time.
- **Emergency detection** — the backend checks each message for signs that this might be a genuine emergency and flags it separately from a normal reply.
- **Health summary & report generation** — at the end of a conversation, it can pull out the key symptoms/details discussed and generate a proper health report.

## Tech stack

| Layer | What we used |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript — hosted on GitHub Pages |
| Backend | Python (Flask) — hosted on Render |
| AI | Groq API (OpenAI-compatible SDK, pointed at Groq's endpoint) |
| Database | SQLite for storing patients, conversations, and messages |

We used Groq mainly because it's fast — response times matter a lot in a chat UI, and Groq's inference speed made the conversation actually feel like a conversation instead of a loading spinner.

## Project structure

```
AI assistance/
├── index.html           # main frontend page
├── script.js             # chat UI logic, API calls to backend
├── style.css              # styling
├── backend/
│   ├── server.py          # Flask app, all API routes
│   ├── ai.py               # Groq client, system prompt, AI response logic
│   ├── database.py         # SQLite setup and queries
│   ├── report.py            # health report generation
│   └── requirements.txt
└── database/
    └── healthcare.db        # local SQLite DB
```

## How the backend is organized

`server.py` is the entry point — it exposes routes for creating/fetching a patient, chatting (`/chat`), chatting with an uploaded report image (`/chat-image`), starting a new conversation, fetching history, and generating a summary/report. It doesn't talk to Groq directly — it calls into `ai.py`, which owns the system prompt, the client setup, and all the AI-facing logic (normal replies, emergency checks, extracting health info, and analyzing report images).

We kept the AI logic separate from the Flask routes on purpose, so the routes stay readable and we can change how we talk to the model without touching the API layer.

## Running it locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
# add your GROQ_API_KEY in a .env file
python server.py
```

**Frontend**
Just open `index.html` in a browser, or serve it with any static server. Update the backend URL in `script.js` if you're not running the backend locally.

## A note on AI assistance

We used AI tools during development for help with debugging, understanding certain libraries, and getting a starting structure for some parts of the code — the way most student developers use tools like this to learn faster. Every part of the logic here has been gone through, understood, and in several places rewritten by us so we can explain and defend how it works. We're not claiming zero AI involvement in the *process* of learning and building, but the understanding and the final implementation are ours.

## Team

_Add your team name and member names here._

## Disclaimer

This is a hackathon prototype and **not a substitute for professional medical advice**. The assistant is meant to help people understand symptoms and reports better, not to diagnose or replace a doctor.
