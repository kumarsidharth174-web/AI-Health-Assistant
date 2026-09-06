from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback

import database
import ai
import report


app = Flask(__name__)
CORS(app)


# ==========================================
# HOME (health check)
# ==========================================

@app.route("/")
def home():
    return "AI Healthcare Assistant Backend is Running!"


# ==========================================
# CREATE / GET PATIENT PROFILE
# ==========================================
# Called once when the patient first opens the app
# (profile setup form), or to load the saved profile.

@app.route("/patient", methods=["POST"])
def create_patient():

    try:
        data = request.get_json() or {}

        name = data.get("name") or "Guest Patient"
        age = data.get("age")
        gender = data.get("gender")
        phone = data.get("phone")

        patient_id = database.create_patient(
            name=name,
            age=age,
            gender=gender,
            phone=phone
        )

        return jsonify({
            "patient_id": patient_id,
            "patient": database.get_patient(patient_id)
        })

    except Exception:
        print("\n===== /patient ERROR =====")
        traceback.print_exc()
        return jsonify({"error": "Could not create patient profile."}), 500


@app.route("/patient/<int:patient_id>", methods=["GET"])
def get_patient(patient_id):

    try:
        patient = database.get_patient(patient_id)

        if not patient:
            return jsonify({"error": "Patient not found."}), 404

        return jsonify({"patient": patient})

    except Exception:
        print("\n===== /patient GET ERROR =====")
        traceback.print_exc()
        return jsonify({"error": "Could not load patient."}), 500


@app.route("/patient/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):

    try:
        data = request.get_json() or {}

        database.update_patient(
            patient_id,
            name=data.get("name"),
            age=data.get("age"),
            gender=data.get("gender"),
            phone=data.get("phone")
        )

        return jsonify({"patient": database.get_patient(patient_id)})

    except Exception:
        print("\n===== /patient PUT ERROR =====")
        traceback.print_exc()
        return jsonify({"error": "Could not update patient."}), 500


# ==========================================
# CHAT (with memory + database saving)
# ==========================================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json()

        if not data:
            return jsonify({"reply": "Please send a message."}), 400

        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"reply": "Please enter a message."}), 400

        if ai.client is None:
            return jsonify({
                "reply": "Gemini API key is missing. Please check your .env file."
            }), 500

        patient_id = data.get("patient_id")
        conversation_id = data.get("conversation_id")

        # Make sure we have a patient (create a guest one if needed)
        if not patient_id:
            patient_id = database.create_patient()

        # Make sure we have a conversation to save messages into
        if not conversation_id:
            title = user_message[:40] + ("..." if len(user_message) > 40 else "")
            conversation_id = database.create_conversation(patient_id, title=title)

        # Load previous messages in THIS conversation for context
        previous_messages = database.get_conversation(conversation_id)

        # Save the patient's new message
        database.save_message(conversation_id, "patient", user_message)

        print("\n--------------------------------")
        print("USER:", user_message)
        print("--------------------------------")

        # Ask Gemini for a reply, using conversation memory
        reply = ai.get_ai_response(user_message, previous_messages)

        # Save AI reply
        database.save_message(conversation_id, "ai", reply)

        print("AI:", reply)

        emergency = ai.check_emergency(user_message)

        return jsonify({
            "reply": reply,
            "patient_id": patient_id,
            "conversation_id": conversation_id,
            "emergency": emergency
        })

    except Exception as error:

        print("\n========== /chat ERROR ==========")
        traceback.print_exc()
        print("==================================\n")

        friendly = ai.friendly_error_message(error)

        return jsonify({"reply": friendly}), 503


# ==========================================
# START A NEW CHAT (keeps old one in the database)
# ==========================================

@app.route("/new-chat", methods=["POST"])
def new_chat():

    try:
        data = request.get_json() or {}

        patient_id = data.get("patient_id")

        if not patient_id:
            return jsonify({"error": "patient_id is required."}), 400

        title = data.get("title") or "New Consultation"

        conversation_id = database.create_conversation(patient_id, title=title)

        return jsonify({"conversation_id": conversation_id})

    except Exception:
        print("\n===== /new-chat ERROR =====")
        traceback.print_exc()
        return jsonify({"error": "Could not start a new chat."}), 500


# ==========================================
# PATIENT HISTORY (list of past conversations)
# ==========================================

@app.route("/history/<int:patient_id>", methods=["GET"])
def history(patient_id):

    try:
        conversations = database.get_patient_conversations(patient_id)
        return jsonify({"conversations": conversations})

    except Exception:
        print("\n===== /history ERROR =====")
        traceback.print_exc()
        return jsonify({"error": "Could not load history."}), 500


# ==========================================
# OPEN A SPECIFIC PAST CONVERSATION
# ==========================================

@app.route("/conversation/<int:conversation_id>", methods=["GET"])
def conversation(conversation_id):

    try:
        messages = database.get_conversation(conversation_id)
        return jsonify({"messages": messages})

    except Exception:
        print("\n===== /conversation ERROR =====")
        traceback.print_exc()
        return jsonify({"error": "Could not load conversation."}), 500


# ==========================================
# PATIENT HEALTH SUMMARY (symptoms/duration/etc cards)
# ==========================================

@app.route("/summary", methods=["POST"])
def summary():

    try:
        data = request.get_json() or {}

        patient_id = data.get("patient_id")

        if not patient_id:
            return jsonify({"error": "patient_id is required."}), 400

        messages = database.get_patient_messages(patient_id)

        info = ai.extract_health_info(messages)

        return jsonify({"summary": info})

    except Exception as error:
        print("\n===== /summary ERROR =====")
        traceback.print_exc()
        return jsonify({"error": ai.friendly_error_message(error)}), 503


# ==========================================
# GENERATE HEALTH REPORT
# ==========================================

@app.route("/report", methods=["POST"])
def generate_report():

    try:
        data = request.get_json() or {}

        patient_id = data.get("patient_id")

        if not patient_id:
            return jsonify({"error": "Please have a conversation first."}), 400

        messages = database.get_patient_messages(patient_id)

        if not messages:
            return jsonify({"error": "No conversation found yet for this patient."}), 400

        report_text = report.generate_health_report(messages)

        # Save a copy of the report in the database
        database.save_report(
            patient_id=patient_id,
            summary=report_text,
            symptoms="",
            recommendations=""
        )

        return jsonify({"report": report_text})

    except Exception as error:

        print("\n========== /report ERROR ==========")
        traceback.print_exc()
        print("====================================\n")

        return jsonify({"error": ai.friendly_error_message(error)}), 503


# ==========================================
# RUN SERVER
# ==========================================
# IMPORTANT for Render (or any cloud host):
# - host must be "0.0.0.0" (not 127.0.0.1), so it's reachable
#   from outside the container.
# - port must come from the PORT environment variable that
#   Render sets automatically — not a hardcoded number.

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    print("\n======================================")
    print("      AI HEALTHCARE ASSISTANT")
    print("======================================")
    print(f"Server starting on port: {port}")
    print("======================================\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )