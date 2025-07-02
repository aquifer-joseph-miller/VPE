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

# Helper function to map patient encounters to feedback assistants
def get_feedback_assistant_key(actor_name):
    """
    Maps the selected VPE actor to the appropriate feedback assistant key.
    Modify this mapping based on your FEEDBACK_ASSISTANTS dictionary structure.
    """
    feedback_mapping = {
        "Mr. Aiken (Standard)": "Mr. Aiken Feedback",
        "Mr. Aiken (Challenging)": "Mr. Aiken Feedback",  # Same feedback assistant for both versions
        "Mr. Smith (Standard)": "Mr. Smith Feedback",
        "Mr. Smith (Challenging)": "Mr. Smith Feedback",  # Same feedback assistant for both versions
        "Mrs. Kelly (Standard)": "Mrs. Kelly Feedback",
    }
    
    return feedback_mapping.get(actor_name, "Mr. Aiken Feedback")  # Default fallback

# Helper function to map patient encounters to breadth feedback assistants
def get_breadth_feedback_assistant_key(actor_name):
    """
    Maps the selected VPE actor to the appropriate breadth feedback assistant key.
    """
    breadth_feedback_mapping = {
        "Mr. Aiken (Standard)": "Mr. Aiken Feedback - Breadth",
        "Mr. Aiken (Challenging)": "Mr. Aiken Feedback - Breadth",  # Same breadth feedback assistant for both versions
        "Mr. Smith (Standard)": "Mr. Smith Feedback - Breadth",
        "Mr. Smith (Challenging)": "Mr. Smith Feedback - Breadth",  # Same breadth feedback assistant for both versions
        "Mrs. Kelly (Standard)": "Mrs. Kelly Feedback - Breadth",
    }
    
    return breadth_feedback_mapping.get(actor_name, "Mr. Aiken Feedback - Breadth")  # Default fallback

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
        # Get the appropriate feedback assistants for the selected actor
        feedback_assistant_key = get_feedback_assistant_key(st.session_state.selected_actor)
        breadth_feedback_assistant_key = get_breadth_feedback_assistant_key(st.session_state.selected_actor)
        patient_name = get_patient_name(st.session_state.selected_actor)
        
        # Check if all feedback assistants exist
        if feedback_assistant_key not in FEEDBACK_ASSISTANTS:
            st.error(f"Feedback assistant '{feedback_assistant_key}' not found. Please check your feedback_assistants configuration.")
            st.stop()
            
        if breadth_feedback_assistant_key not in FEEDBACK_ASSISTANTS:
            st.error(f"Breadth feedback assistant '{breadth_feedback_assistant_key}' not found. Please check your feedback_assistants configuration.")
            st.stop()
            
        if "Depth Feedback" not in FEEDBACK_ASSISTANTS:
            st.error(f"Depth feedback assistant 'Depth Feedback' not found. Please check your feedback_assistants configuration.")
            st.stop()

        transcript = get_transcript_as_text(st.session_state.thread_id)

        # Generate Overall Feedback
        # Create new thread for overall feedback
        feedback_thread = openai.beta.threads.create()

        # Updated feedback prompt to be more dynamic
        openai.beta.threads.messages.create(
            thread_id=feedback_thread.id,
            role="user",
            content=f"""
Below is a transcript of a simulated patient encounter. The STUDENT is a medical learner. The PATIENT is {patient_name}, a virtual patient powered by AI.

Please provide constructive feedback **only on the STUDENT's performance**, including their tone, communication style, question quality, and clinical reasoning. Do not critique the patient responses.

Transcript:
{transcript}
"""
        )

        # Use the dynamically selected feedback assistant
        feedback_run = openai.beta.threads.runs.create(
            thread_id=feedback_thread.id,
            assistant_id=FEEDBACK_ASSISTANTS[feedback_assistant_key],
        )

        with st.spinner("Generating overall feedback..."):
            while True:
                feedback_status = openai.beta.threads.runs.retrieve(
                    thread_id=feedback_thread.id,
                    run_id=feedback_run.id
                )
                if feedback_status.status == "completed":
                    break

        feedback_messages = openai.beta.threads.messages.list(thread_id=feedback_thread.id)
        overall_feedback_text = feedback_messages.data[0].content[0].text.value

        # Display Overall Feedback
        # 🎨 Feedback icon + title (could also be made dynamic based on patient)
        col1, col2 = st.columns([1, 8])
        with col1:
            st.image("https://imgur.com/BVSjFOh.png", width=40)
        with col2:
            st.subheader("Feedback on exploration of all relevant problem areas")

        # 📝 Feedback content
        st.markdown(overall_feedback_text)

        # Generate Breadth Feedback
        # Create new thread for breadth feedback
        breadth_feedback_thread = openai.beta.threads.create()

        # Breadth-specific feedback prompt
        openai.beta.threads.messages.create(
            thread_id=breadth_feedback_thread.id,
            role="user",
            content=f"""
Below is a transcript of a simulated patient encounter. The STUDENT is a medical learner. The PATIENT is {patient_name}, a virtual patient powered by AI.

Please provide constructive feedback **only on the STUDENT's performance** specifically focused on breadth of data gathering - the extent of exploration to find all relevant problem areas in the patient's situation. Do not critique the patient responses.

Transcript:
{transcript}
"""
        )

        # Use the breadth feedback assistant
        breadth_feedback_run = openai.beta.threads.runs.create(
            thread_id=breadth_feedback_thread.id,
            assistant_id=FEEDBACK_ASSISTANTS[breadth_feedback_assistant_key],
        )

        with st.spinner("Generating breadth feedback..."):
            while True:
                breadth_feedback_status = openai.beta.threads.runs.retrieve(
                    thread_id=breadth_feedback_thread.id,
                    run_id=breadth_feedback_run.id
                )
                if breadth_feedback_status.status == "completed":
                    break

        breadth_feedback_messages = openai.beta.threads.messages.list(thread_id=breadth_feedback_thread.id)
        breadth_feedback_text = breadth_feedback_messages.data[0].content[0].text.value

        # Display Breadth Feedback Section
        st.markdown("---")
        st.subheader("📊 Breadth (Data Gathering)")
        st.markdown("*The extent of exploration to find all relevant problem areas in the patient's situation*")
        st.markdown(breadth_feedback_text)

        # Generate Depth Feedback
        # Create new thread for depth feedback
        depth_feedback_thread = openai.beta.threads.create()

        # Depth-specific feedback prompt
        openai.beta.threads.messages.create(
            thread_id=depth_feedback_thread.id,
            role="user",
            content=f"""
Below is a transcript of a simulated patient encounter. The STUDENT is a medical learner. The PATIENT is {patient_name}, a virtual patient powered by AI.

Please provide constructive feedback **only on the STUDENT's performance** specifically focused on depth and appropriateness in following up symptoms. Do not critique the patient responses.

Transcript:
{transcript}
"""
        )

        # Use the depth feedback assistant
        depth_feedback_run = openai.beta.threads.runs.create(
            thread_id=depth_feedback_thread.id,
            assistant_id=FEEDBACK_ASSISTANTS["Depth Feedback"],
        )

        with st.spinner("Generating depth feedback..."):
            while True:
                depth_feedback_status = openai.beta.threads.runs.retrieve(
                    thread_id=depth_feedback_thread.id,
                    run_id=depth_feedback_run.id
                )
                if depth_feedback_status.status == "completed":
                    break

        depth_feedback_messages = openai.beta.threads.messages.list(thread_id=depth_feedback_thread.id)
        depth_feedback_text = depth_feedback_messages.data[0].content[0].text.value

        # Display Depth Feedback Section
        st.markdown("---")
        st.subheader("🔍 Depth")
        st.markdown("*Depth and appropriateness in following up symptoms*")
        st.markdown(depth_feedback_text)