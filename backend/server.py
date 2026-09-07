from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import os

import database
import ai
import report


# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)


# ==========================================
# HOME / HEALTH CHECK
# ==========================================

@app.route("/", methods=["GET"])
def home():

    print("GET / received")

    return "AI Healthcare Assistant Backend is Running!"


# ==========================================
# CREATE PATIENT
# ==========================================

@app.route("/patient", methods=["POST"])
def create_patient():

    try:

        print("POST /patient received")

        data = request.get_json(
            silent=True
        ) or {}

        name = data.get(
            "name"
        ) or "Guest Patient"

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
            "patient": database.get_patient(
                patient_id
            )
        })

    except Exception:

        print("\n========== PATIENT ERROR ==========")
        traceback.print_exc()
        print("===================================\n")

        return jsonify({
            "error": "Could not create patient profile."
        }), 500


# ==========================================
# GET PATIENT
# ==========================================

@app.route(
    "/patient/<int:patient_id>",
    methods=["GET"]
)
def get_patient(patient_id):

    try:

        patient = database.get_patient(
            patient_id
        )

        if not patient:

            return jsonify({
                "error": "Patient not found."
            }), 404

        return jsonify({
            "patient": patient
        })

    except Exception:

        print("\n========== GET PATIENT ERROR ==========")
        traceback.print_exc()
        print("=======================================\n")

        return jsonify({
            "error": "Could not load patient."
        }), 500


# ==========================================
# UPDATE PATIENT
# ==========================================

@app.route(
    "/patient/<int:patient_id>",
    methods=["PUT"]
)
def update_patient(patient_id):

    try:

        data = request.get_json(
            silent=True
        ) or {}

        database.update_patient(
            patient_id,
            name=data.get("name"),
            age=data.get("age"),
            gender=data.get("gender"),
            phone=data.get("phone")
        )

        return jsonify({
            "patient": database.get_patient(
                patient_id
            )
        })

    except Exception:

        print("\n========== UPDATE PATIENT ERROR ==========")
        traceback.print_exc()
        print("==========================================\n")

        return jsonify({
            "error": "Could not update patient."
        }), 500


# ==========================================
# CHAT
# ==========================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    print("\n")
    print("==========================================")
    print("========== CHAT REQUEST RECEIVED =========")
    print("==========================================")

    try:

        # ----------------------------------
        # READ REQUEST
        # ----------------------------------

        data = request.get_json(
            silent=True
        ) or {}

        print("Request JSON received")

        user_message = (
            data.get("message")
            or ""
        ).strip()

        patient_id = data.get(
            "patient_id"
        )

        conversation_id = data.get(
            "conversation_id"
        )

        print(
            "Message:",
            user_message
        )

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Conversation ID:",
            conversation_id
        )

        # ----------------------------------
        # VALIDATE MESSAGE
        # ----------------------------------

        if not user_message:

            print("ERROR: Empty message")

            return jsonify({
                "reply": "Please enter a message."
            }), 400

        # ----------------------------------
        # CREATE GUEST PATIENT
        # ----------------------------------

        if not patient_id:

            print(
                "Creating guest patient..."
            )

            patient_id = (
                database.create_patient()
            )

            print(
                "Guest patient created:",
                patient_id
            )

        # ----------------------------------
        # CREATE CONVERSATION
        # ----------------------------------

        if not conversation_id:

            title = user_message[:40]

            if len(user_message) > 40:
                title += "..."

            print(
                "Creating conversation..."
            )

            conversation_id = (
                database.create_conversation(
                    patient_id,
                    title=title
                )
            )

            print(
                "Conversation created:",
                conversation_id
            )

        # ----------------------------------
        # LOAD PREVIOUS MESSAGES
        # ----------------------------------

        print(
            "Loading previous messages..."
        )

        previous_messages = (
            database.get_conversation(
                conversation_id
            )
        )

        print(
            "Previous messages:",
            len(previous_messages)
            if previous_messages
            else 0
        )

        # ----------------------------------
        # SAVE USER MESSAGE
        # ----------------------------------

        print(
            "Saving user message..."
        )

        database.save_message(
            conversation_id,
            "patient",
            user_message
        )

        # ----------------------------------
        # CALL GROQ
        # ----------------------------------

        print(
            "Calling Groq AI..."
        )

        reply = ai.get_ai_response(
            user_message,
            previous_messages
        )

        print(
            "Groq reply received."
        )

        # ----------------------------------
        # SAVE AI RESPONSE
        # ----------------------------------

        print(
            "Saving AI response..."
        )

        database.save_message(
            conversation_id,
            "ai",
            reply
        )

        # ----------------------------------
        # EMERGENCY CHECK
        # ----------------------------------

        emergency = ai.check_emergency(
            user_message
        )

        print(
            "Emergency:",
            emergency
        )

        print(
            "========== CHAT SUCCESS ==========\n"
        )

        return jsonify({

            "reply": reply,

            "patient_id": patient_id,

            "conversation_id": conversation_id,

            "emergency": emergency

        })

    except Exception as error:

        print("\n")
        print("==========================================")
        print("============ CHAT ERROR ==================")
        print("==========================================")

        print(
            "ERROR TYPE:",
            type(error).__name__
        )

        print(
            "ERROR:",
            str(error)
        )

        traceback.print_exc()

        print(
            "=========================================="
        )
        print(
            "==========================================\n"
        )

        return jsonify({

            "reply": ai.friendly_error_message(
                error
            ),

            "error": str(error)

        }), 503


# ==========================================
# NEW CHAT
# ==========================================

@app.route(
    "/new-chat",
    methods=["POST"]
)
def new_chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        patient_id = data.get(
            "patient_id"
        )

        if not patient_id:

            return jsonify({
                "error": "patient_id is required."
            }), 400

        title = data.get(
            "title",
            "New Consultation"
        )

        conversation_id = (
            database.create_conversation(
                patient_id,
                title=title
            )
        )

        return jsonify({
            "conversation_id": conversation_id
        })

    except Exception:

        print("\n========== NEW CHAT ERROR ==========")
        traceback.print_exc()
        print("====================================\n")

        return jsonify({
            "error": "Could not start a new chat."
        }), 500


# ==========================================
# HISTORY
# ==========================================

@app.route(
    "/history/<int:patient_id>",
    methods=["GET"]
)
def history(patient_id):

    try:

        conversations = (
            database.get_patient_conversations(
                patient_id
            )
        )

        return jsonify({
            "conversations": conversations
        })

    except Exception:

        print("\n========== HISTORY ERROR ==========")
        traceback.print_exc()
        print("===================================\n")

        return jsonify({
            "error": "Could not load history."
        }), 500


# ==========================================
# CONVERSATION
# ==========================================

@app.route(
    "/conversation/<int:conversation_id>",
    methods=["GET"]
)
def conversation(conversation_id):

    try:

        messages = (
            database.get_conversation(
                conversation_id
            )
        )

        return jsonify({
            "messages": messages
        })

    except Exception:

        print("\n========== CONVERSATION ERROR ==========")
        traceback.print_exc()
        print("========================================\n")

        return jsonify({
            "error": "Could not load conversation."
        }), 500


# ==========================================
# SUMMARY
# ==========================================

@app.route(
    "/summary",
    methods=["POST"]
)
def summary():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        patient_id = data.get(
            "patient_id"
        )

        if not patient_id:

            return jsonify({
                "error": "patient_id is required."
            }), 400

        messages = (
            database.get_patient_messages(
                patient_id
            )
        )

        info = ai.extract_health_info(
            messages
        )

        return jsonify({
            "summary": info
        })

    except Exception as error:

        print("\n========== SUMMARY ERROR ==========")
        traceback.print_exc()
        print("===================================\n")

        return jsonify({
            "error": ai.friendly_error_message(
                error
            )
        }), 503


# ==========================================
# REPORT
# ==========================================

@app.route(
    "/report",
    methods=["POST"]
)
def generate_report():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        patient_id = data.get(
            "patient_id"
        )

        if not patient_id:

            return jsonify({
                "error": "Please have a conversation first."
            }), 400

        messages = (
            database.get_patient_messages(
                patient_id
            )
        )

        if not messages:

            return jsonify({
                "error": "No conversation found yet for this patient."
            }), 400

        report_text = (
            report.generate_health_report(
                messages
            )
        )

        database.save_report(
            patient_id=patient_id,
            summary=report_text,
            symptoms="",
            recommendations=""
        )

        return jsonify({
            "report": report_text
        })

    except Exception as error:

        print("\n========== REPORT ERROR ==========")
        traceback.print_exc()
        print("==================================\n")

        return jsonify({
            "error": ai.friendly_error_message(
                error
            )
        }), 503


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    print("")
    print("==========================================")
    print("       AI HEALTHCARE ASSISTANT")
    print("==========================================")
    print("AI Healthcare Backend Started")
    print("==========================================")
    print("")

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )