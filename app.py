import streamlit as st
import openai
from assistants import ASSISTANT_MAP
from feedback_assistants import FEEDBACK_ASSISTANTS
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import tempfile
import os
import wave
import numpy as np

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
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "text"  # "text" or "voice"

def audio_frame_callback(frame):
    """Callback to capture audio frames during recording."""
    if st.session_state.is_recording:
        audio_array = frame.to_ndarray()
        st.session_state.audio_buffer.append(audio_array.flatten())
    return frame

def save_recorded_audio():
    """Convert recorded audio buffer to WAV file."""
    if not st.session_state.audio_buffer:
        return None
    
    try:
        audio_data = np.concatenate(st.session_state.audio_buffer)
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        audio_data = (audio_data * 32767).astype(np.int16)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(48000)
            wav_file.writeframes(audio_data.tobytes())
        
        return temp_file.name
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return None

def transcribe_and_send():
    """Transcribe recorded audio and automatically send as message."""
    st.write(f"🔍 Debug: Audio buffer length: {len(st.session_state.audio_buffer)}")
    
    if not st.session_state.audio_buffer:
        st.warning("No audio recorded. Make sure to click START first, then Record.")
        return
    
    with st.spinner("🎯 Processing your message..."):
        try:
            st.write("🔍 Debug: Starting audio processing...")
            
            # Save audio to file
            audio_file_path = save_recorded_audio()
            st.write(f"🔍 Debug: Audio file created: {audio_file_path is not None}")
            
            if audio_file_path:
                # Transcribe using OpenAI Whisper
                st.write("🔍 Debug: Sending to OpenAI Whisper...")
                with open(audio_file_path, "rb") as audio_file:
                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                
                # Clean up temp file
                os.unlink(audio_file_path)
                
                transcribed_text = transcript.strip()
                st.write(f"🔍 Debug: Transcribed text: '{transcribed_text}'")
                
                if transcribed_text:
                    # Automatically send the transcribed message
                    process_user_message(transcribed_text)
                    
                    # Reset recording state
                    st.session_state.audio_buffer = []
                    st.session_state.is_recording = False
                else:
                    st.warning("No speech detected. Please try again.")
            else:
                st.error("Could not process recording.")
                
        except Exception as e:
            st.error(f"Transcription failed: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

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

# Input mode selection
st.markdown("### 💬 Choose input method:")
col1, col2 = st.columns(2)

with col1:
    if st.button("💬 Text Chat", use_container_width=True, 
                 type="primary" if st.session_state.input_mode == "text" else "secondary"):
        st.session_state.input_mode = "text"
        st.rerun()

with col2:
    if st.button("🎤 Voice Chat", use_container_width=True,
                 type="primary" if st.session_state.input_mode == "voice" else "secondary"):
        st.session_state.input_mode = "voice"
        st.rerun()

# Show current mode
if st.session_state.input_mode == "text":
    st.info("📝 **Text Chat Mode** - Type your message below")
    
    # Text input
    if prompt := st.chat_input("Say something to the actor..."):
        process_user_message(prompt)

else:  # voice mode
    st.info("🎙️ **Voice Chat Mode** - Record your message")
    
    # WebRTC for voice input (only show in voice mode)
    webrtc_ctx = webrtc_streamer(
        key="voice-recorder",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={
            "video": False,
            "audio": {
                "echoCancellation": True,
                "noiseSuppression": True,
                "autoGainControl": True,
            }
        },
        audio_frame_callback=audio_frame_callback,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
    )
    
    # Voice recording controls
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔴 Record", disabled=st.session_state.is_recording or not webrtc_ctx.state.playing):
            st.session_state.is_recording = True
            st.session_state.audio_buffer = []
            st.rerun()
    
    with col2:
        if st.button("⏹️ Stop", disabled=not st.session_state.is_recording):
            st.session_state.is_recording = False
            # Automatically transcribe and send when stopping
            transcribe_and_send()
            st.rerun()
    
    with col3:
        if not webrtc_ctx.state.playing:
            st.warning("⚠️ Click ▶️ above to enable microphone")
        elif st.session_state.is_recording:
            st.error("🔴 Recording... Click 'Stop' when finished")
        else:
            st.success("✅ Ready to record")

# ✅ Only show feedback button if there's a user message in the history
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