"""
Seed / reset Firestore to clean demo state.

Usage:
    python seed.py

Safe to run repeatedly — overwrites sessions/current entirely.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from agent.firestore import init_firestore, reset_session

service_account_path = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "serviceAccountKey.json",
)
init_firestore(service_account_path)
reset_session()
print("Firestore seeded: sessions/current → clean demo state")
