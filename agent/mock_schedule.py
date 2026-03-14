"""
Mock schedule data for the daily appointment view.

This represents today's schedule with one cancelled slot that
the agent will attempt to fill.

Structure matches what Carter's dashboard expects:
  Collection: schedule
  Document: today
  Field: slots (array of slot objects)
"""

DAILY_SCHEDULE = {
    "slots": [
        {
            "id": "slot_0900",
            "time": "9:00 AM",
            "treatment": "Crown prep",
            "status": "booked",
            "patient_name": "Tom Bradley",
            "value": 400,
        },
        {
            "id": "slot_1000",
            "time": "10:00 AM",
            "treatment": "Cleaning",
            "status": "booked",
            "patient_name": "Lisa Chen",
            "value": 200,
        },
        {
            "id": "slot_1130",
            "time": "11:30 AM",
            "treatment": "X-Ray + Exam",
            "status": "booked",
            "patient_name": "David Nguyen",
            "value": 250,
        },
        {
            "id": "slot_1400",
            "time": "2:00 PM",
            "treatment": "Cleaning",
            "status": "cancelled",
            "patient_name": None,
            "value": 200,
        },
        {
            "id": "slot_1530",
            "time": "3:30 PM",
            "treatment": "Whitening",
            "status": "booked",
            "patient_name": "Emma Wilson",
            "value": 300,
        },
        {
            "id": "slot_1700",
            "time": "5:00 PM",
            "treatment": "Filling",
            "status": "booked",
            "patient_name": "Carlos Reyes",
            "value": 280,
        },
    ]
}

# The slot that's currently being filled (matches DEMO_SLOT)
CANCELLED_SLOT_ID = "slot_1400"
