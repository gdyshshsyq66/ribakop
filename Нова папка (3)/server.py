from flask import Flask, request, send_from_directory, jsonify
import json
import os
import random
import string
from datetime import datetime, timezone, timedelta

app = Flask(__name__, static_folder='.')

ADMIN_PASSWORD = "1234"   # change if needed
admin_token = None

STATUSES_FILE = "statuses.json"

# Ensure statuses.json exists
if not os.path.exists(STATUSES_FILE):
    with open(STATUSES_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def load_statuses():
    with open(STATUSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_statuses(data):
    with open(STATUSES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def filter_last_4h(launches):
    out = []
    try:
        for ts in launches:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - dt <= timedelta(hours=4):
                out.append(ts)
    except Exception:
        pass
    return out

# LOGIN
@app.post("/login")
def login():
    global admin_token
    pw = request.json.get("password", "")
    if pw == ADMIN_PASSWORD:
        admin_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        return jsonify(ok=True, token=admin_token)
    return jsonify(ok=False)

# GET STATUSES
@app.get("/status/get")
def get_status():
    data = load_statuses()
    result = {}
    for name, info in data.items():
        entry = {}
        entry['status'] = info.get('status', 'Немає')
        launches = info.get('launches', [])
        # ensure list
        if not isinstance(launches, list):
            launches = []
        entry['launches'] = launches
        entry['launches4h'] = filter_last_4h(launches)
        entry['lastLaunch'] = launches[-1] if launches else None
        result[name] = entry
    return jsonify(result)

# SET STATUS
@app.post("/status/set")
def set_status():
    global admin_token
    data = request.json or {}
    token = data.get("token")
    name = data.get("name")
    status = data.get("status")

    if token != admin_token:
        return jsonify(error="forbidden"), 403

    statuses = load_statuses()
    if name not in statuses or not isinstance(statuses[name], dict):
        statuses[name] = {}

    statuses[name]['status'] = status

    # If status is not "Немає", record a new launch timestamp
    if status != "Немає":
        launches = statuses[name].get('launches', [])
        if not isinstance(launches, list):
            launches = []
        launches.append(now_iso())
        # optionally keep only recent N entries (e.g., last 100)
        if len(launches) > 200:
            launches = launches[-200:]
        statuses[name]['launches'] = launches

    save_statuses(statuses)
    return jsonify(ok=True)

# Serve static files (HTML, assets)
@app.route("/<path:path>")
def serve_file(path):
    return send_from_directory('.', path)

@app.route("/")
def index():
    # default to dashboard_full.html
    return send_from_directory('.', "dashboard_full.html")

if __name__ == "__main__":
    print("✔ Python сервер працює на http://localhost:3000")
    app.run(host="0.0.0.0", port=3000, debug=True)
