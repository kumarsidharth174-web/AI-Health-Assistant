import sqlite3
import os
from datetime import datetime


DATABASE_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "database"
)

os.makedirs(DATABASE_FOLDER, exist_ok=True)

DATABASE_PATH = os.path.join(
    DATABASE_FOLDER,
    "healthcare.db"
)


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            title TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            summary TEXT,
            symptoms TEXT,
            recommendations TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# CREATE PATIENT
# ==========================================

def create_patient(name="Guest Patient", age=None, gender=None, phone=None):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO patients (name, age, gender, phone, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (name, age, gender, phone, datetime.now().isoformat()))

    patient_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return patient_id


# ==========================================
# UPDATE PATIENT PROFILE
# ==========================================

def update_patient(patient_id, name=None, age=None, gender=None, phone=None):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE patients
        SET
            name = COALESCE(?, name),
            age = COALESCE(?, age),
            gender = COALESCE(?, gender),
            phone = COALESCE(?, phone)
        WHERE id = ?
    """, (name, age, gender, phone, patient_id))

    connection.commit()
    connection.close()


# ==========================================
# CREATE CONVERSATION
# ==========================================

def create_conversation(patient_id, title="Health Consultation"):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO conversations (patient_id, title, created_at)
        VALUES (?, ?, ?)
    """, (patient_id, title, datetime.now().isoformat()))

    conversation_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return conversation_id


# ==========================================
# SAVE MESSAGE
# ==========================================

def save_message(conversation_id, sender, message):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO messages (conversation_id, sender, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, sender, message, datetime.now().isoformat()))

    connection.commit()
    connection.close()


# ==========================================
# GET CONVERSATION MESSAGES
# ==========================================

def get_conversation(conversation_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT sender, message, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (conversation_id,))

    messages = cursor.fetchall()
    connection.close()

    return [dict(row) for row in messages]


# ==========================================
# GET PATIENT
# ==========================================

def get_patient(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = cursor.fetchone()
    connection.close()

    return dict(patient) if patient else None


# ==========================================
# GET ALL CONVERSATIONS FOR A PATIENT (HISTORY LIST)
# ==========================================

def get_patient_conversations(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, title, created_at
        FROM conversations
        WHERE patient_id = ?
        ORDER BY id DESC
    """, (patient_id,))

    conversations = cursor.fetchall()
    connection.close()

    return [dict(row) for row in conversations]


# ==========================================
# GET PATIENT REPORT DATA (ALL MESSAGES, ALL CONVERSATIONS)
# ==========================================

def get_patient_messages(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT m.sender, m.message, m.created_at
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.patient_id = ?
        ORDER BY m.id ASC
    """, (patient_id,))

    messages = cursor.fetchall()
    connection.close()

    return [dict(row) for row in messages]


# ==========================================
# SAVE REPORT
# ==========================================

def save_report(patient_id, summary, symptoms, recommendations):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO reports (patient_id, summary, symptoms, recommendations, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (patient_id, summary, symptoms, recommendations, datetime.now().isoformat()))

    connection.commit()
    report_id = cursor.lastrowid
    connection.close()

    return report_id


# Start database (creates tables if they do not exist yet,
# never deletes existing data)
initialize_database()