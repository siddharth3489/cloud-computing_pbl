# ----------------------------------------------------
# EduStream — Final Backend (CORS FIXED 100%)
# ----------------------------------------------------

import os
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth
import requests


# ----------------------------------------------------
# Firebase Admin Init
# ----------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "serviceAccountKey_cloud.json")

cred = credentials.Certificate(KEY_PATH)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

FIREBASE_API_KEY = "AIzaSyBO6BuxZEf44GiTcr1mtlo446sBQ00P3oc"


# ----------------------------------------------------
# Flask + CORS
# ----------------------------------------------------
app = Flask(__name__)

# This alone is NOT enough → but we keep it.
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# This IS the important part — ensures headers ALWAYS return.
@app.after_request
def apply_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


# Handle preflight OPTIONS for ANY route
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    response = make_response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response, 200


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------
def error(msg, code=400):
    return jsonify({"success": False, "error": msg}), code

def log(context, e):
    print(f"\n🔥 ERROR in {context}")
    print(e)
    traceback.print_exc()
    print("\n")


# ----------------------------------------------------
# Routes
# ----------------------------------------------------
@app.route("/")
def home():
    return {"message": "EduStream API Running 🚀"}


# ------------------ REGISTER -----------------------
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        name = data.get("name", "")
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return error("Email and password required")

        user = auth.create_user(email=email, password=password, display_name=name)

        db.collection("users").document(user.uid).set({
            "uid": user.uid,
            "email": email,
            "name": name,
            "createdAt": datetime.utcnow().isoformat()
        })

        return {"success": True, "uid": user.uid}

    except Exception as e:
        log("REGISTER", e)
        return error("Registration failed", 500)


# ------------------- LOGIN -------------------------
@app.route("/login", methods=["POST"])
def login():
    try:
        d = request.json
        email, password = d["email"], d["password"]

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

        res = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        })

        if res.status_code != 200:
            return error("Invalid login", 401)

        data = res.json()

        return {
            "success": True,
            "uid": data["localId"],
            "idToken": data["idToken"]
        }

    except Exception as e:
        log("LOGIN", e)
        return error("Login error", 500)


# ------------------- VIDEOS ------------------------
@app.route("/videos", methods=["GET"])
def videos():
    try:
        docs = db.collection("videos").stream()
        arr = []
        for d in docs:
            v = d.to_dict()
            v["id"] = d.id
            arr.append(v)
        return {"success": True, "videos": arr}

    except Exception as e:
        log("VIDEOS", e)
        return error("Could not load videos", 500)


# ------------------- DOWNLOAD LOG ------------------
@app.route("/download", methods=["POST"])
def download():
    try:
        d = request.json
        db.collection("downloads").add({
            "uid": d["uid"],
            "lectureId": d["lectureId"],
            "title": d.get("title", ""),
            "src": d.get("src", ""),
            "createdAt": datetime.utcnow().isoformat(),
        })
        return {"success": True}

    except Exception as e:
        log("DOWNLOAD", e)
        return error("Failed to record download", 500)


@app.route("/downloads", methods=["GET"])
def downloads():
    try:
        uid = request.args.get("uid")
        docs = db.collection("downloads").where("uid", "==", uid).stream()
        arr = []
        for d in docs:
            x = d.to_dict()
            x["id"] = d.id
            arr.append(x)
        return {"success": True, "downloads": arr}

    except Exception as e:
        log("GET DOWNLOADS", e)
        return error("Failed to fetch", 500)


# ----------------------------------------------------
# Run
# ----------------------------------------------------
if __name__ == "__main__":
    print("🔥 EduStream Backend Running on http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=True)
