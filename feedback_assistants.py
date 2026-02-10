# feedback_assistants.py

FEEDBACK_ASSISTANTS = {
    # Main feedback assistants (organized by patient name)
    "Mr. Aiken Feedback": "asst_DeDFNDKqaeoNaBC68j5QaBH3",
    "Mrs. Kelly Feedback": "asst_VDMoRCzxDWfqiJnx4rGkOlE7",
    "Albert Smitherman Feedback": "asst_trOKTbhafy3dEWgU7X53zfsv",
    "Mrs. Ada Street Feedback": "asst_P3RDnVT2LEmLnpB90P0bVkgP",
    "Betsy Pearce Feedback": "asst_SnVg0HQT347M1UiZjV57kRn8",
    "Jessica Morales Feedback": "asst_mYV3rAu4QzniUKTPwpetjsZy",
    "Amanda Waters Feedback": "asst_0qnP7dAL045D07pAdyI7fMwq",
    "Barbara Turner Feedback": "asst_RpoQyL8MuMcAFLgaMUyOZHuk",
    "Anna Pine Feedback": "asst_hccHydZdIkL5p79jykuv1JkV",
    "Lori Johnson Feedback": "asst_kyRrhplReh3wRFKSILLiizCy", 
    "Dolores Russell Feedback": "asst_9VEOfHVWK7tUVu8qff68dJgu",
    "Allison Killpatrick Feedback": "asst_iDhvobUsS7mrx4eQsc9FgNnN",
    "Erica Patterson Feedback": "asst_9KtP5WjAJ7vmextH0iKuUEB0",
    "Mrs. Miller Feedback": "asst_J2yNXKyAVxZ9yhxVD1o4roNh",
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