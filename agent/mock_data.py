"""
Mock data for demo/testing.

This data simulates what would come from a real dental practice's
recall list and scheduling system.
"""

# Patients on the recall list (overdue for appointments)
# Varied by: treatment type, days overdue, reliability, demographics
RECALL_LIST = [
    # --- High priority cleaning patients ---
    {
        "name": "Sarah Kim",
        "phone": "+1-801-555-0101",
        "treatment_needed": "cleaning",
        "days_overdue": 15,
        "reliability_score": 0.95,
    },
    {
        "name": "James Park",
        "phone": "+1-801-555-0102",
        "treatment_needed": "cleaning",
        "days_overdue": 22,
        "reliability_score": 0.85,
    },
    {
        "name": "Emily Rodriguez",
        "phone": "+1-801-555-0103",
        "treatment_needed": "cleaning",
        "days_overdue": 10,
        "reliability_score": 0.90,
    },
    {
        "name": "Michael Thompson",
        "phone": "+1-801-555-0104",
        "treatment_needed": "cleaning",
        "days_overdue": 45,
        "reliability_score": 0.70,
    },
    {
        "name": "David Chen",
        "phone": "+1-801-555-0105",
        "treatment_needed": "cleaning",
        "days_overdue": 5,
        "reliability_score": 0.60,
    },

    # --- Filling patients ---
    {
        "name": "Maria Garcia",
        "phone": "+1-801-555-0106",
        "treatment_needed": "filling",
        "days_overdue": 30,
        "reliability_score": 0.85,
    },
    {
        "name": "Robert Williams",
        "phone": "+1-801-555-0107",
        "treatment_needed": "filling",
        "days_overdue": 60,
        "reliability_score": 0.75,
    },
    {
        "name": "Jennifer Lee",
        "phone": "+1-801-555-0108",
        "treatment_needed": "filling",
        "days_overdue": 14,
        "reliability_score": 0.92,
    },

    # --- Crown patients ---
    {
        "name": "William Johnson",
        "phone": "+1-801-555-0109",
        "treatment_needed": "crown",
        "days_overdue": 25,
        "reliability_score": 0.88,
    },
    {
        "name": "Patricia Brown",
        "phone": "+1-801-555-0110",
        "treatment_needed": "crown",
        "days_overdue": 18,
        "reliability_score": 0.80,
    },

    # --- Root canal patients ---
    {
        "name": "Christopher Martinez",
        "phone": "+1-801-555-0111",
        "treatment_needed": "root_canal",
        "days_overdue": 7,
        "reliability_score": 0.65,
    },
    {
        "name": "Amanda Davis",
        "phone": "+1-801-555-0112",
        "treatment_needed": "root_canal",
        "days_overdue": 35,
        "reliability_score": 0.78,
    },

    # --- Exam patients ---
    {
        "name": "Daniel Wilson",
        "phone": "+1-801-555-0113",
        "treatment_needed": "exam",
        "days_overdue": 90,
        "reliability_score": 0.55,
    },
    {
        "name": "Jessica Taylor",
        "phone": "+1-801-555-0114",
        "treatment_needed": "exam",
        "days_overdue": 120,
        "reliability_score": 0.70,
    },

    # --- Whitening patients ---
    {
        "name": "Andrew Anderson",
        "phone": "+1-801-555-0115",
        "treatment_needed": "whitening",
        "days_overdue": 3,
        "reliability_score": 0.98,
    },
    {
        "name": "Sophia Nguyen",
        "phone": "+1-801-555-0116",
        "treatment_needed": "whitening",
        "days_overdue": 12,
        "reliability_score": 0.82,
    },
]


# --- Demo slots (different scenarios) ---

# Default: cleaning slot at 2 PM (most common)
DEMO_SLOT = {
    "id": "slot_001",
    "time": "2:00 PM",
    "date": "Today",
    "treatment": "cleaning",
    "value": 200,
}

# Alternative slots for testing different scenarios
DEMO_SLOTS = {
    "cleaning": {
        "id": "slot_001",
        "time": "2:00 PM",
        "date": "Today",
        "treatment": "cleaning",
        "value": 200,
    },
    "filling": {
        "id": "slot_002",
        "time": "10:30 AM",
        "date": "Today",
        "treatment": "filling",
        "value": 350,
    },
    "crown": {
        "id": "slot_003",
        "time": "3:30 PM",
        "date": "Today",
        "treatment": "crown",
        "value": 1200,
    },
    "root_canal": {
        "id": "slot_004",
        "time": "9:00 AM",
        "date": "Today",
        "treatment": "root_canal",
        "value": 1500,
    },
    "exam": {
        "id": "slot_005",
        "time": "11:00 AM",
        "date": "Today",
        "treatment": "exam",
        "value": 150,
    },
    "whitening": {
        "id": "slot_006",
        "time": "4:00 PM",
        "date": "Today",
        "treatment": "whitening",
        "value": 400,
    },
}


# --- Helper to get patients by treatment type ---

def get_patients_for_treatment(treatment: str) -> list[dict]:
    """Filter recall list to patients needing a specific treatment."""
    return [p for p in RECALL_LIST if p["treatment_needed"] == treatment]


# --- Stats for demo talking points ---

MOCK_STATS = {
    "total_patients": len(RECALL_LIST),
    "treatments": {
        "cleaning": len(get_patients_for_treatment("cleaning")),
        "filling": len(get_patients_for_treatment("filling")),
        "crown": len(get_patients_for_treatment("crown")),
        "root_canal": len(get_patients_for_treatment("root_canal")),
        "exam": len(get_patients_for_treatment("exam")),
        "whitening": len(get_patients_for_treatment("whitening")),
    },
    "avg_days_overdue": sum(p["days_overdue"] for p in RECALL_LIST) // len(RECALL_LIST),
    "avg_reliability": round(sum(p["reliability_score"] for p in RECALL_LIST) / len(RECALL_LIST), 2),
}
