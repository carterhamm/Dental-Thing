"""
Mock data for demo/testing.

This data simulates what would come from a real dental practice's
recall list and scheduling system.

Patient fields:
- name: Patient name
- phone: Contact number
- treatment_needed: Type of treatment needed
- cycles_overdue: Number of treatment cycles missed (1 cycle = ~6 months for cleanings)
- reliability_score: 0-1 score based on appointment history
- preferred_time_of_day: "morning" | "afternoon" | "evening" - derived from visit history
- pending_treatment: True if they have unfinished treatment (e.g., started root canal)
"""

# Patients on the recall list (overdue for appointments)
RECALL_LIST = [
    # --- Team + demo (ranked by priority for cleaning slot demo) ---
    {
        "name": "Podium Judge",
        "phone": "+16502658400",
        "treatment_needed": "cleaning",
        "cycles_overdue": 2,
        "reliability_score": 0.98,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
    {
        "name": "Carter Hammond",
        "phone": "+17192136213",
        "dob": "January 25, 2000",
        "treatment_needed": "cleaning",
        "cycles_overdue": 2,
        "reliability_score": 0.95,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
    {
        "name": "Spencer Hammond",
        "phone": "+17195053575",
        "treatment_needed": "cleaning",
        "cycles_overdue": 4,
        "reliability_score": 0.99,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": True,
    },
    {
        "name": "Carter Hammond",
        "phone": "+17192136213",
        "treatment_needed": "cleaning",
        "cycles_overdue": 3,
        "reliability_score": 0.97,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": True,
    },
    {
        "name": "Eddy Kim",
        "phone": "+10000000000",  # TODO: update with Eddy's real number
        "treatment_needed": "cleaning",
        "cycles_overdue": 3,
        "reliability_score": 0.95,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
<<<<<<< HEAD
    # --- Other cleaning patients ---
=======
    {
        "name": "Spencer Hammond",
        "phone": "+17195053575",
        "dob": "May 10, 1998",
        "treatment_needed": "cleaning",
        "cycles_overdue": 2,
        "reliability_score": 0.90,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
    # --- High priority cleaning patients ---
>>>>>>> origin/carter
    {
        "name": "Sarah Kim",
        "phone": "+1-801-555-0101",
        "treatment_needed": "cleaning",
        "cycles_overdue": 1,
        "reliability_score": 0.95,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
    {
        "name": "James Park",
        "phone": "+1-801-555-0102",
        "treatment_needed": "cleaning",
        "cycles_overdue": 1,
        "reliability_score": 0.85,
        "preferred_time_of_day": "morning",
        "pending_treatment": False,
    },
    {
        "name": "Emily Rodriguez",
        "phone": "+1-801-555-0103",
        "treatment_needed": "cleaning",
        "cycles_overdue": 1,
        "reliability_score": 0.90,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
    {
        "name": "Michael Thompson",
        "phone": "+1-801-555-0104",
        "treatment_needed": "cleaning",
        "cycles_overdue": 2,
        "reliability_score": 0.70,
        "preferred_time_of_day": "morning",
        "pending_treatment": False,
    },
    {
        "name": "David Chen",
        "phone": "+1-801-555-0105",
        "treatment_needed": "cleaning",
        "cycles_overdue": 1,
        "reliability_score": 0.60,
        "preferred_time_of_day": "evening",
        "pending_treatment": False,
    },

    # --- Filling patients ---
    {
        "name": "Maria Garcia",
        "phone": "+1-801-555-0106",
        "treatment_needed": "filling",
        "cycles_overdue": 1,
        "reliability_score": 0.85,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": True,  # Started but didn't finish filling
    },
    {
        "name": "Robert Williams",
        "phone": "+1-801-555-0107",
        "treatment_needed": "filling",
        "cycles_overdue": 2,
        "reliability_score": 0.75,
        "preferred_time_of_day": "morning",
        "pending_treatment": False,
    },
    {
        "name": "Jennifer Lee",
        "phone": "+1-801-555-0108",
        "treatment_needed": "filling",
        "cycles_overdue": 1,
        "reliability_score": 0.92,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },

    # --- Crown patients ---
    {
        "name": "William Johnson",
        "phone": "+1-801-555-0109",
        "treatment_needed": "crown",
        "cycles_overdue": 1,
        "reliability_score": 0.88,
        "preferred_time_of_day": "morning",
        "pending_treatment": True,  # Has temp crown, needs permanent
    },
    {
        "name": "Patricia Brown",
        "phone": "+1-801-555-0110",
        "treatment_needed": "crown",
        "cycles_overdue": 1,
        "reliability_score": 0.80,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },

    # --- Root canal patients ---
    {
        "name": "Christopher Martinez",
        "phone": "+1-801-555-0111",
        "treatment_needed": "root_canal",
        "cycles_overdue": 1,
        "reliability_score": 0.65,
        "preferred_time_of_day": "morning",
        "pending_treatment": True,  # Started root canal, needs completion
    },
    {
        "name": "Amanda Davis",
        "phone": "+1-801-555-0112",
        "treatment_needed": "root_canal",
        "cycles_overdue": 2,
        "reliability_score": 0.78,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },

    # --- Exam patients ---
    {
        "name": "Daniel Wilson",
        "phone": "+1-801-555-0113",
        "treatment_needed": "exam",
        "cycles_overdue": 3,
        "reliability_score": 0.55,
        "preferred_time_of_day": "morning",
        "pending_treatment": False,
    },
    {
        "name": "Jessica Taylor",
        "phone": "+1-801-555-0114",
        "treatment_needed": "exam",
        "cycles_overdue": 4,
        "reliability_score": 0.70,
        "preferred_time_of_day": "evening",
        "pending_treatment": False,
    },

    # --- Whitening patients ---
    {
        "name": "Andrew Anderson",
        "phone": "+1-801-555-0115",
        "treatment_needed": "whitening",
        "cycles_overdue": 1,
        "reliability_score": 0.98,
        "preferred_time_of_day": "afternoon",
        "pending_treatment": False,
    },
    {
        "name": "Sophia Nguyen",
        "phone": "+1-801-555-0116",
        "treatment_needed": "whitening",
        "cycles_overdue": 1,
        "reliability_score": 0.82,
        "preferred_time_of_day": "morning",
        "pending_treatment": False,
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
    "avg_cycles_overdue": round(sum(p["cycles_overdue"] for p in RECALL_LIST) / len(RECALL_LIST), 1),
    "avg_reliability": round(sum(p["reliability_score"] for p in RECALL_LIST) / len(RECALL_LIST), 2),
    "pending_treatments": len([p for p in RECALL_LIST if p["pending_treatment"]]),
}
