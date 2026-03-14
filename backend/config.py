"""
Firebase and environment configuration.
Loads env vars and initializes the Firebase Admin SDK.
"""

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent / ".env")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Firebase init — only initialize once
_cred_path = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path(__file__).parent / "serviceAccountKey.json"),
)

if not firebase_admin._apps:
    cred = credentials.Certificate(_cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
session_ref = db.collection("sessions").document("current")
