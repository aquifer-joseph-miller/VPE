import streamlit as st
import openai
from assistants import ASSISTANT_MAP
from feedback_assistants import FEEDBACK_ASSISTANTS

# ✅ Keep this helper function unchanged
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

# Secure API key handling
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Virtual Patient Actors (VPE)")

# Sidebar: Select Actor
actor = st.sidebar.selectbox("Choose an AI Actor", list(ASSISTANT_MAP.keys()))
assistant_id = ASSISTANT_MAP[actor]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    thread = openai.beta.threads.create()
    st.session_state.thread_id = thread.id

# Display prior chat messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Say something to the actor..."):
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

# ✅ Only show button if there's a user message in the history
if st.session_state.messages and any(msg["role"] == "user" for msg in st.session_state.messages):
    st.markdown("---")
    st.subheader("🧠 Ready to reflect?")

    if st.button("Get Feedback on This Interaction"):
        transcript = get_transcript_as_text(st.session_state.thread_id)

        # Create new thread for feedback
        feedback_thread = openai.beta.threads.create()

        openai.beta.threads.messages.create(
            thread_id=feedback_thread.id,
            role="user",
            content=f"Here is the transcript of a student interacting with a virtual patient. Please provide constructive feedback:\n\n{transcript}"
        )

        feedback_run = openai.beta.threads.runs.create(
            thread_id=feedback_thread.id,
            assistant_id=FEEDBACK_ASSISTANTS["Mr. Aiken Feedback"],
        )

        with st.spinner("Generating feedback..."):
            while True:
                feedback_status = openai.beta.threads.runs.retrieve(
                    thread_id=feedback_thread.id,
                    run_id=feedback_run.id
                )
                if feedback_status.status == "completed":
                    break

        feedback_messages = openai.beta.threads.messages.list(thread_id=feedback_thread.id)
        feedback_text = feedback_messages.data[0].content[0].text.value

# Show Feedback Coach icon next to the heading
col1, col2 = st.columns([1, 8])
with col1:
    st.image("https://drive.google.com/uc?id=1FOLTw9RLgJLe8jCnBnbYFVWi2m6dUL7Z", width=40)
with col2:
    st.subheader("Feedback from Coach")

# Feedback content
st.markdown(feedback_text)