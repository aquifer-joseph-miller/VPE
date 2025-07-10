import streamlit as st
import openai
from assistants import ASSISTANT_MAP
from feedback_assistants import FEEDBACK_ASSISTANTS

# Keep this helper function unchanged
def get_transcript_as_text(thread_id):
    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    transcript = ""
    for msg in reversed(messages.data):  # chronological order
        if msg.role == "user":
            role_label = "STUDENT"
        elif msg.role == "assistant":
            role_label = "PATIENT"
        else:
            role_label = msg.role.upper()
        content = msg.content[0].text.value
        transcript += f"{role_label}: {content}\n\n"
    return transcript

# Helper function to map patient encounters to main feedback assistants
def get_feedback_assistant_key(actor_name):
    """
    Maps the selected VPE actor to the appropriate main feedback assistant key.
    """
    feedback_mapping = {
        "Mr. Aiken (Standard)": "Mr. Aiken Feedback",
        "Mr. Aiken (Challenging)": "Mr. Aiken Feedback",
        "Mr. Smith (Standard)": "Mr. Smith Feedback",
        "Mr. Smith (Challenging)": "Mr. Smith Feedback",
        "Mrs. Kelly (Standard)": "Mrs. Kelly Feedback",
    }
    
    return feedback_mapping.get(actor_name, "Mr. Aiken Feedback")  # Default fallback

# Helper function to get patient name for feedback context
def get_patient_name(actor_name):
    """Extract the patient name from the actor selection for feedback context."""
    if "Mr. Aiken" in actor_name:
        return "Mr. Aiken"
    elif "Mr. Smith" in actor_name:
        return "Mr. Smith"
    elif "Mrs. Kelly" in actor_name:
        return "Mrs. Kelly"
    else:
        return "the patient"  # Generic fallback

# Secure API key handling
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Virtual Patient Encounters (VPE)")

# Sidebar: Select Actor
actor = st.sidebar.selectbox("Choose a Virtual Patient Encounter", list(ASSISTANT_MAP.keys()))
assistant_id = ASSISTANT_MAP[actor]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    thread = openai.beta.threads.create()
    st.session_state.thread_id = thread.id

# Store the selected actor in session state to maintain consistency
if "selected_actor" not in st.session_state:
    st.session_state.selected_actor = actor

# Update selected actor if user changes selection (this will reset the conversation)
if st.session_state.selected_actor != actor:
    st.session_state.selected_actor = actor
    st.session_state.messages = []
    thread = openai.beta.threads.create()
    st.session_state.thread_id = thread.id

# Display prior chat messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Start chatting with the virtual patient..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)
    
    # Send message to OpenAI Assistant
    openai.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
    )
    
    run = openai.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id,
    )
    
    # Wait for assistant to finish
    with st.spinner("Waiting for response..."):
        while True:
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
    
    # Get the latest response
    messages = openai.beta.threads.messages.list(thread_id=st.session_state.thread_id)
    latest = messages.data[0].content[0].text.value
    st.session_state.messages.append({"role": "assistant", "content": latest})
    st.chat_message("assistant").markdown(latest)

# Only show button if there's a user message in the history
# Count how many user messages exist
user_message_count = sum(1 for msg in st.session_state.messages if msg["role"] == "user")

if user_message_count >= 5:
    st.markdown("---")
    st.subheader("🧠 Ready to end the interview and get feedback?")
    
    if st.button("Generate Feedback!"):
        # Get the appropriate feedback assistant for the selected actor
        feedback_assistant_key = get_feedback_assistant_key(st.session_state.selected_actor)
        patient_name = get_patient_name(st.session_state.selected_actor)
        
        # DEBUG LOGGING
        st.write("### 🔍 DEBUG INFORMATION")
        st.write(f"**Selected Actor:** {st.session_state.selected_actor}")
        st.write(f"**Feedback Assistant Key:** {feedback_assistant_key}")
        st.write(f"**Patient Name:** {patient_name}")
        
        # Check if the feedback assistant exists
        if feedback_assistant_key not in FEEDBACK_ASSISTANTS:
            st.error(f"Feedback assistant '{feedback_assistant_key}' not found. Please check your feedback_assistants configuration.")
            st.stop()
        
        assistant_id_to_use = FEEDBACK_ASSISTANTS[feedback_assistant_key]
        st.write(f"**Assistant ID being used:** {assistant_id_to_use}")
        
        # Display all available assistants for verification
        st.write("**All Available Feedback Assistants:**")
        for key, value in FEEDBACK_ASSISTANTS.items():
            if key == feedback_assistant_key:
                st.write(f"→ **{key}**: {value} ← USING THIS ONE")
            else:
                st.write(f"   {key}: {value}")
        
        transcript = get_transcript_as_text(st.session_state.thread_id)
        
        # Show transcript preview for debugging
        st.write("**Transcript Preview (first 500 chars):**")
        st.text(transcript[:500] + "..." if len(transcript) > 500 else transcript)
        
        # Generate Overall Feedback
        # Create new thread for feedback
        feedback_thread = openai.beta.threads.create()
        
        # FORCED FORMAT MESSAGE
        user_message_content = f"""
Below is a transcript of a student's chat with virtual standardized patient {patient_name}. 

CRITICAL REQUIREMENT: You MUST respond using the exact structured format specified in your system instructions. Your response MUST start with:

### PERFORMANCE SUMMARY
**Domain 1 - Breadth:** [Green ✅ OR Yellow ⚠️ OR Red ❌]
**Domain 2 - Depth:** [Green ✅ OR Yellow ⚠️ OR Red ❌]
**Domain 3 - Clinical Relevance:** [Green ✅ OR Yellow ⚠️ OR Red ❌]
**Domain 4 - Questioning Technique:** [Green ✅ OR Yellow ⚠️ OR Red ❌]
**Domain 5 - Patient Interaction:** [Green ✅ OR Yellow ⚠️ OR Red ❌]

Do NOT provide narrative feedback. Follow the structured domain analysis format exactly as specified in your instructions.

Transcript:
{transcript}
"""
        
        st.write("**User Message Being Sent:**")
        st.text_area("Message Preview", user_message_content, height=200)
        
        # Overall feedback prompt
        openai.beta.threads.messages.create(
            thread_id=feedback_thread.id,
            role="user",
            content=user_message_content
        )
        
        # Use the main feedback assistant
        feedback_run = openai.beta.threads.runs.create(
            thread_id=feedback_thread.id,
            assistant_id=assistant_id_to_use,
        )
        
        st.write(f"**Run Created with ID:** {feedback_run.id}")
        
        with st.spinner("Generating comprehensive feedback..."):
            while True:
                feedback_status = openai.beta.threads.runs.retrieve(
                    thread_id=feedback_thread.id,
                    run_id=feedback_run.id
                )
                if feedback_status.status == "completed":
                    break
                elif feedback_status.status in ["failed", "cancelled", "expired"]:
                    st.error(f"Feedback generation failed with status: {feedback_status.status}")
                    if hasattr(feedback_status, 'last_error') and feedback_status.last_error:
                        st.error(f"Error details: {feedback_status.last_error}")
                    st.stop()
        
        st.write(f"**Run Status:** {feedback_status.status}")
        
        feedback_messages = openai.beta.threads.messages.list(thread_id=feedback_thread.id)
        feedback_text = feedback_messages.data[0].content[0].text.value
        
        # Show raw response for debugging
        st.write("**Raw Response (first 1000 chars):**")
        st.text_area("Raw Response Preview", feedback_text[:1000] + "..." if len(feedback_text) > 1000 else feedback_text, height=200)
        
        # Display Overall Feedback Section
        st.subheader("📋 Comprehensive Feedback")
        st.markdown(f"*Feedback from {patient_name} encounter*")
        st.markdown(feedback_text)