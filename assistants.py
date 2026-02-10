# assistants.py

ASSISTANT_MAP = {
   
    # Geriatrics
    "Mr. Aiken (Geriatrics 15)": "asst_QvmAr0EQSkJbTz1egONsWRBy",
    "Albert Smitherman (Geriatrics 16)": "asst_kAbDyyAv4noyXhEUTIVultmv",
    "Mrs. Ada Street (Geriatrics 3)": "asst_8yBlHaT60YdtsPjjrgliijud",
    
    # Pediatrics
    "Mrs. Kelly (Pediatrics 12)": "asst_YFt8DwxTNaNIb167RidYEvQR",
    "Jessica Morales (Pediatrics 09)": "asst_KJHLtj7XmArrsaiNOUA225i3",
    
    # Family Medicine
    "Amanda Waters (Family Medicine 05)": "asst_HsHZ5S1NHLJiEgyMV5cCakiX",
    
    # Internal Medicine
    "Barbara Turner (Internal Medicine 09)": "asst_rULWJq6yptdIKcdZ0jc4Toxt",
    
    # Neurology
    "Anna Pine (Neurology 11)": "asst_fJKBggzYCVeAkVdw1pxLq20c",
    
    # Gynecology
    "Lori Johnson (Gynecology 02)": "asst_AACL3cOVfAs5q6FLrGbNhhii",
    "Dolores Russell (Gynecology 03)": "asst_VKdsqSCQ20QUGZvRvIqjEYZQ",
    
    # Psychiatry
    "Allison Killpatrick (Psychiatry 05)": "asst_pXcWTnltp76KLKw6KyaAGCjw",
    
    # Palliative Care
    "Erica Patterson (Palliative Care 06)": "asst_jKKOCPvspxa9g2qo8GCVvswu",

    # High Value Care
    "Mrs. Miller (High Value Care 04)": "asst_pWDA8oyZfpvRGWyYDoWhakj1",
}

# Helper function to get assistant by name or ID
def get_assistant_id(actor_name):
    """
    Get assistant ID by actor name.
    
    Args:
        actor_name (str): The name of the virtual patient actor
        
    Returns:
        str: The assistant ID, or None if not found
    """
    return ASSISTANT_MAP.get(actor_name)
