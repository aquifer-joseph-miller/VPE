import streamlit as st
import openai
from assistants import ASSISTANT_MAP
from feedback_assistants import FEEDBACK_ASSISTANTS

def get_transcript_as_text(thread_id):
    # grab more history at once
    messages = openai.beta.threads.messages.list(
        thread_id=thread_id,
        limit=100      # bump this up if your conversation is longer
    )
    transcript = ""
    # messages.data is newest‑first, so reverse it for chronological order
    for msg in reversed(messages.data):
        if msg.role == "user":
            role_label = "STUDENT"
        elif msg.role == "assistant":
            role_label = "PATIENT"
        else:
            role_label = msg.role.upper()
        content = msg.content[0].text.value
        transcript += f"{role_label}: {content}\n\n"
    return transcript

def get_feedback_assistant_key(actor_name):
    """
    Maps the selected VPE actor to the appropriate main feedback assistant key.
    """
    feedback_mapping = {
        "Mr. Aiken (Standard)": "Mr. Aiken Feedback",
        "Mr. Aiken (Challenging)": "Mr. Aiken Feedback",
        "Mr. Smith (Standard)":  "Mr. Smith Feedback",
        "Mr. Smith (Challenging)": "Mr. Smith Feedback",
        "Mrs. Kelly (Standard)":  "Mrs. Kelly Feedback",
    }
    return feedback_mapping.get(actor_name, "Mr. Aiken Feedback")

def get_patient_name(actor_name):
    """Extract the patient name from the actor selection for feedback context."""
    if "Mr. Aiken" in actor_name:
        return "Mr. Aiken"
    elif "Mr. Smith" in actor_name:
        return "Mr. Smith"
    elif "Mrs. Kelly" in actor_name:
        return "Mrs. Kelly"
    else:
        return "the patient"

# Secure API key handling
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Virtual Patient Encounters (VPE)")

# Sidebar: Select Actor
actor = st.sidebar.selectbox(
    "Choose a Virtual Patient Encounter",
    list(ASSISTANT_MAP.keys())
)
assistant_id = ASSISTANT_MAP[actor]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    thread = openai.beta.threads.create()
    st.session_state.thread_id = thread.id
if "selected_actor" not in st.session_state:
    st.session_state.selected_actor = actor

# Reset conversation if actor changes
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

# Only show feedback button after at least 5 user turns
user_message_count = sum(1 for msg in st.session_state.messages if msg["role"] == "user")

if user_message_count >= 5:
    st.markdown("---")
    st.subheader("🧠 Ready to end the interview and get feedback?")

    if st.button("Generate Feedback!"):
        feedback_assistant_key = get_feedback_assistant_key(st.session_state.selected_actor)
        patient_name = get_patient_name(st.session_state.selected_actor)

        if feedback_assistant_key not in FEEDBACK_ASSISTANTS:
            st.error(f"Feedback assistant '{feedback_assistant_key}' not found.")
            st.stop()

        assistant_id_to_use = FEEDBACK_ASSISTANTS[feedback_assistant_key]
        transcript = get_transcript_as_text(st.session_state.thread_id)

        # Create new thread for feedback
        feedback_thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread_id=feedback_thread.id,
            role="system",
            content="You are an expert clinical skills rater. Use the five-domain assessment framework."
        )
        openai.beta.threads.messages.create(
            thread_id=feedback_thread.id,
            role="user",
            content=f"""
Below is a transcript of a student's chat with virtual standardized patient {patient_name}.
Please evaluate the student's performance using the five-domain assessment framework.

Transcript:
{transcript}
"""
        )

        feedback_run = openai.beta.threads.runs.create(
            thread_id=feedback_thread.id,
            assistant_id=assistant_id_to_use,
        )

        with st.spinner("Generating comprehensive feedback..."):
            while True:
                feedback_status = openai.beta.threads.runs.retrieve(
                    thread_id=feedback_thread.id,
                    run_id=feedback_run.id
                )
                if feedback_status.status == "completed":
                    break
                elif feedback_status.status in ["failed", "cancelled", "expired"]:
                    st.error("Feedback generation failed. Please try again.")
                    st.stop()

        # Fetch the full feedback reply
        feedback_messages = openai.beta.threads.messages.list(
            thread_id=feedback_thread.id,
            limit=100
        )
        assistant_replies = [
            m for m in feedback_messages.data
            if m.role == "assistant"
        ]
        if not assistant_replies:
            st.error("No assistant reply found in feedback thread.")
            st.stop()
        feedback_text = assistant_replies[-1].content[0].text.value

        # Display Overall Feedback
        st.subheader("📋 Comprehensive Feedback")
        st.markdown(f"*Feedback from {patient_name} encounter*")
        st.markdown(feedback_text)
