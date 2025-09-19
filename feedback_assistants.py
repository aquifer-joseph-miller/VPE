# feedback_assistants.py

FEEDBACK_ASSISTANTS = {
    # Main feedback assistants (organized by patient name)
    "Mr. Aiken Feedback": "asst_DeDFNDKqaeoNaBC68j5QaBH3",
    "Mrs. Kelly Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    
    # Using consistent naming 
    "Albert Smitherman Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Jessica Morales Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Amanda Waters Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Barbara Turner Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Anna Pine Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Lori Johnson Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7", 
    "Dolores Russell Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Allison Killpatrick Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Erica Patterson Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
}

# Helper function to get feedback assistant ID
def get_feedback_assistant_id(patient_name):
    """
    Get feedback assistant ID by patient name.
    
    Args:
        patient_name (str): The name of the patient
        
    Returns:
        str: The feedback assistant ID, or None if not found
    """
    feedback_key = f"{patient_name} Feedback"
    return FEEDBACK_ASSISTANTS.get(feedback_key)

# Get all available feedback assistants
def get_available_feedback_assistants():
    """
    Get a list of all available feedback assistant names.
    
    Returns:
        list: List of feedback assistant keys
    """
    return list(FEEDBACK_ASSISTANTS.keys())