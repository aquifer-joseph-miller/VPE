import streamlit as st
import openai
from assistants import ASSISTANT_MAP
from feedback_assistants import FEEDBACK_ASSISTANTS
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import tempfile
import os
import wave
import numpy as np
import threading
import time

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

# Initialize session state for audio recording
if "audio_buffer" not in st.session_state:
    st.session_state.audio_buffer = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "audio_recorded" not in st.session_state:
    st.session_state.audio_recorded = False

def audio_frame_callback(frame):
    """Callback to capture audio frames during recording."""
    if st.session_state.is_recording:
        # Convert frame to numpy array and store
        audio_array = frame.to_ndarray()
        st.session_state.audio_buffer.append(audio_array.flatten())
    return frame

def save_recorded_audio():
    """Convert recorded audio buffer to WAV file."""
    if not st.session_state.audio_buffer:
        return None
    
    try:
        # Concatenate all audio frames
        audio_data = np.concatenate(st.session_state.audio_buffer)
        
        # Normalize audio (convert to 16-bit PCM)
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(48000)  # 48kHz
            wav_file.writeframes(audio_data.tobytes())
        
        return temp_file.name
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return None

def transcribe_audio_file(file_path):
    """Transcribe audio file using OpenAI Whisper."""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript.strip()
    except Exception as e:
        raise e

def process_user_message(prompt):
    """Process a user message through the OpenAI Assistant."""
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

# Chat input section
st.markdown("### 💬 Send a message")

# Text input
if prompt := st.chat_input("Type your message or use voice recording below..."):
    process_user_message(prompt)

# Voice recording section
st.markdown("### 🎤 Voice Recording")

# WebRTC streamer for audio capture
webrtc_ctx = webrtc_streamer(
    key="audio-recorder",
    mode=WebRtcMode.SENDONLY,
    audio_receiver_size=1024,
    media_stream_constraints={
        "video": False,
        "audio": {
            "echoCancellation": True,
            "noiseSuppression": True,
            "autoGainControl": True,
            "sampleRate": 48000,
        }
    },
    audio_frame_callback=audio_frame_callback,
    rtc_configuration=RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    ),
)

# Recording controls
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🔴 Start Recording", disabled=st.session_state.is_recording):
        if webrtc_ctx.state.playing:
            st.session_state.is_recording = True
            st.session_state.audio_buffer = []
            st.session_state.audio_recorded = False
            st.rerun()
        else:
            st.error("Please allow microphone access first by clicking the play button above.")

with col2:
    if st.button("⏹️ Stop Recording", disabled=not st.session_state.is_recording):
        st.session_state.is_recording = False
        st.session_state.audio_recorded = True
        st.rerun()

with col3:
    if st.session_state.is_recording:
        st.error("🔴 Recording... Click 'Stop Recording' when finished")
    elif st.session_state.audio_recorded and st.session_state.audio_buffer:
        st.success("✅ Audio recorded! Click 'Transcribe & Send' below")
    elif webrtc_ctx.state.playing:
        st.info("🎤 Ready to record. Click 'Start Recording'")
    else:
        st.warning("⚠️ Click the play button above to enable microphone")

# Transcription button
if st.session_state.audio_recorded and st.session_state.audio_buffer:
    if st.button("🎯 Transcribe & Send Message"):
        with st.spinner("🎯 Transcribing your message..."):
            try:
                # Save recorded audio to file
                audio_file_path = save_recorded_audio()
                
                if audio_file_path:
                    # Transcribe the audio
                    transcribed_text = transcribe_audio_file(audio_file_path)
                    
                    # Clean up the temporary file
                    os.unlink(audio_file_path)
                    
                    if transcribed_text:
                        st.success(f"🎙️ **Transcribed:** *{transcribed_text}*")
                        
                        # Process the message
                        process_user_message(transcribed_text)
                        
                        # Reset recording state
                        st.session_state.audio_buffer = []
                        st.session_state.audio_recorded = False
                        st.rerun()
                    else:
                        st.warning("⚠️ No speech detected. Please try recording again.")
                else:
                    st.error("❌ Could not process the recording. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Transcription failed: {str(e)}")
                st.info("💡 **Tips for better recording:**\n"
                       "• Speak clearly and loudly\n"
                       "• Ensure quiet environment\n"
                       "• Record for at least 2-3 seconds\n"
                       "• Check your microphone permissions")

# Instructions
with st.expander("ℹ️ How to use voice recording"):
    st.markdown("""
    **Step-by-step:**
    
    1. **Enable microphone** - Click the ▶️ play button in the WebRTC box above
    2. **Allow permissions** - Your browser will ask for microphone access
    3. **Start recording** - Click the 🔴 "Start Recording" button
    4. **Speak your message** - Talk clearly into your microphone
    5. **Stop recording** - Click ⏹️ "Stop Recording" when finished
    6. **Send message** - Click 🎯 "Transcribe & Send Message"
    
    **Tips:**
    - Speak in a quiet environment
    - Hold the microphone close to your mouth
    - Speak clearly and at normal pace
    - Wait a moment after clicking start before speaking
    """)

# ✅ Only show button if there's a user message in the history
user_message_count = sum(1 for msg in st.session_state.messages if msg["role"] == "user")

if user_message_count >= 5:
    st.markdown("---")
    st.subheader("🧠 Ready to reflect?")
    
    if st.button("Get Feedback on This Interaction"):
        transcript = get_transcript_as_text(st.session_state.thread_id)
        # Create new thread for feedback
        feedback_thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread_id=feedback_thread.id,
            role="user",
            content=f"""
Below is a transcript of a simulated patient encounter. The STUDENT is a medical learner. The PATIENT is Mr. Aiken, a virtual patient powered by AI.
Please provide constructive feedback **only on the STUDENT's performance**, including their tone, communication style, question quality, and clinical reasoning. Do not critique the patient responses.

Transcript:
{transcript}
"""
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
        
        # 🎨 Feedback icon + title
        col1, col2 = st.columns([1, 8])
        with col1:
            st.image("https://imgur.com/BVSjFOh.png", width=40)
        with col2:
            st.subheader("Leslie's Feedback")
        
        # 📝 Feedback content
        st.markdown(feedback_text)