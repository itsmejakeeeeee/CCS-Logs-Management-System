import os
import requests
import mysql.connector
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration from Environment Variables
ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "2026")
ROOT_KEY = os.getenv("ROOT_KEY", "998877")
GSHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")

# XAMPP Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ccs_logs_db'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/verify', methods=['POST'])
def verify_access():
    data = request.json
    role = data.get('role')
    key = data.get('key')
    
    if role == 'admin' and key == ADMIN_PASSCODE:
        return jsonify({"success": True})
    elif role == 'super' and key == ROOT_KEY:
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Invalid Passcode"}), 401

@app.route('/api/logs', methods=['GET', 'POST'])
def handle_logs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.json
        action = data.get('action')

        if action == 'archive':
            cursor.execute("UPDATE logs SET is_archived = 1 WHERE timestamp = %s", (data['timestamp'],))
        elif action == 'delete':
            cursor.execute("DELETE FROM logs WHERE timestamp = %s", (data['timestamp'],))
        else:
            # New Log Entry - Save to XAMPP
            cursor.execute("""
                INSERT INTO logs (taskType, name, log_date, courseSection, purpose)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['taskType'], data['name'], data['date'], data['courseSection'], data['purpose']))
            
            # Sync to Google Sheets Backup
            if GSHEET_URL:
                try:
                    requests.post(GSHEET_URL, json=data, timeout=5)
                except Exception as e:
                    print(f"Google Sheets Sync Failed: {e}")

        conn.commit()
        conn.close()
        return jsonify({"status": "success"})

    # GET Request: Fetch all logs from XAMPP
    cursor.execute("SELECT * FROM logs WHERE is_archived = 0 ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    cursor.execute("SELECT * FROM logs WHERE is_archived = 1 ORDER BY timestamp DESC")
    archives = cursor.fetchall()
    
    # Format dates for JSON
    for entry in logs + archives:
        entry['timestamp'] = entry['timestamp'].isoformat()
    
    conn.close()
    return jsonify({"logs": logs, "archives": archives})

if __name__ == '__main__':
    app.run(debug=True, port=5000)