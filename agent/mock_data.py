"""
Mock data for demo/testing.

This data simulates what would come from a real dental practice's
recall list and scheduling system.
"""

# Patients on the recall list (overdue for appointments)
RECALL_LIST = [
    {
        "name": "Sarah Kim",
        "phone": "+1-801-555-0101",
        "treatment_needed": "cleaning",
        "days_overdue": 15,
        "reliability_score": 0.9,
    },
    {
        "name": "James Park",
        "phone": "+1-801-555-0102",
        "treatment_needed": "cleaning",
        "days_overdue": 8,
        "reliability_score": 0.7,
    },
    {
        "name": "Maria Garcia",
        "phone": "+1-801-555-0103",
        "treatment_needed": "filling",
        "days_overdue": 30,
        "reliability_score": 0.85,
    },
    {
        "name": "David Chen",
        "phone": "+1-801-555-0104",
        "treatment_needed": "cleaning",
        "days_overdue": 5,
        "reliability_score": 0.6,
    },
]

# The slot that needs to be filled
DEMO_SLOT = {
    "id": "slot_001",
    "time": "2:00 PM",
    "date": "Today",
    "treatment": "cleaning",
    "value": 200,
}
