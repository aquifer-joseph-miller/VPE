import streamlit as st
import openai
from assistants import ASSISTANT_MAP

# ✅ Secure version: API key from secrets (no hardcoding)
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Custom CSS styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: rgba(27, 85, 153, 0.6); /* #1B5599 with 60% opacity */
        color: white;
    }
    h1, h2, h3, h4, h5, h6, .st-emotion-cache-10trblm {
        color: white; /* Ensure title and headings are white */
    }
    .st-emotion-cache-16idsys p {
        color: white; /* Ensure chat messages are white */
    }
    .stTextInput > div > div > input {
        color: white; /* Input text color */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Your existing app code continues below
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
