import streamlit as st
import openai
from assistants import ASSISTANT_MAP
from feedback_assistants import FEEDBACK_ASSISTANTS
import time

# Configuration
MIN_MESSAGES_FOR_FEEDBACK = 5
POLLING_INTERVAL = 1  # seconds

class VPEApp:
    def __init__(self):
        self.setup_openai()
        self.init_session_state()
    
    def setup_openai(self):
        """Initialize OpenAI client with API key from secrets."""
        try:
            openai.api_key = st.secrets["OPENAI_API_KEY"]
        except KeyError:
            st.error("OpenAI API key not found in secrets. Please configure OPENAI_API_KEY.")
            st.stop()
    
    def init_session_state(self):
        """Initialize session state variables."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = self.create_thread()
        if "selected_actor" not in st.session_state:
            st.session_state.selected_actor = None
    
    def create_thread(self):
        """Create a new OpenAI thread and return its ID."""
        try:
            thread = openai.beta.threads.create()
            return thread.id
        except Exception as e:
            st.error(f"Failed to create thread: {e}")
            st.stop()
    
    def reset_conversation_if_needed(self, current_actor):
        """Reset conversation if actor has changed."""
        if st.session_state.selected_actor != current_actor:
            st.session_state.selected_actor = current_actor
            st.session_state.messages = []
            st.session_state.thread_id = self.create_thread()
    
    def get_patient_name(self, actor_name):
        """Extract patient name from actor selection."""
        # Split by '(' and take the first part, then strip whitespace
        return actor_name.split('(')[0].strip()
    
    def get_feedback_assistant_key(self, actor_name):
        """Generate feedback assistant key from actor name."""
        patient_name = self.get_patient_name(actor_name)
        feedback_key = f"{patient_name} Feedback"
        
        # Fallback to a default if the specific feedback assistant doesn't exist
        if feedback_key not in FEEDBACK_ASSISTANTS:
            # Use the first available feedback assistant as fallback
            available_keys = list(FEEDBACK_ASSISTANTS.keys())
            if available_keys:
                st.warning(f"Feedback assistant for '{patient_name}' not found. Using default feedback assistant.")
                return available_keys[0]
            else:
                st.error("No feedback assistants available.")
                st.stop()
        
        return feedback_key
    
    def get_transcript(self, thread_id):
        """Retrieve and format conversation transcript."""
        try:
            messages = openai.beta.threads.messages.list(
                thread_id=thread_id,
                limit=100
            )
            
            transcript = ""
            # Reverse to get chronological order (oldest first)
            for msg in reversed(messages.data):
                role_label = "STUDENT" if msg.role == "user" else "PATIENT"
                content = msg.content[0].text.value
                transcript += f"{role_label}: {content}\n\n"
            
            return transcript
        except Exception as e:
            st.error(f"Failed to retrieve transcript: {e}")
            return ""
    
    def wait_for_run_completion(self, thread_id, run_id, timeout=60):
        """Wait for OpenAI run to complete with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                run_status = openai.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run_status.status == "completed":
                    return True
                elif run_status.status in ("failed", "cancelled", "expired"):
                    st.error(f"Run failed with status: {run_status.status}")
                    return False
                
                time.sleep(POLLING_INTERVAL)
            except Exception as e:
                st.error(f"Error checking run status: {e}")
                return False
        
        st.error("Request timed out. Please try again.")
        return False
    
    def send_message_to_patient(self, prompt, assistant_id):
        """Send message to virtual patient and get response."""
        try:
            # Add user message to thread
            openai.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=prompt,
            )
            
            # Start run
            run = openai.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,
                assistant_id=assistant_id,
            )
            
            # Wait for completion
            with st.spinner("Waiting for response..."):
                if not self.wait_for_run_completion(st.session_state.thread_id, run.id):
                    return None
            
            # Get latest response
            messages = openai.beta.threads.messages.list(
                thread_id=st.session_state.thread_id,
                limit=1
            )
            
            if messages.data:
                return messages.data[0].content[0].text.value
            else:
                st.error("No response received from virtual patient.")
                return None
                
        except Exception as e:
            st.error(f"Failed to send message: {e}")
            return None
    
    def generate_feedback(self, selected_actor):
        """Generate feedback for the conversation."""
        feedback_assistant_key = self.get_feedback_assistant_key(selected_actor)
        patient_name = self.get_patient_name(selected_actor)
        assistant_id = FEEDBACK_ASSISTANTS[feedback_assistant_key]
        
        # Get transcript
        transcript = self.get_transcript(st.session_state.thread_id)
        if not transcript:
            st.error("Failed to retrieve conversation transcript.")
            return
        
        try:
            # Create new thread for feedback
            feedback_thread = openai.beta.threads.create()
            
            # Prepare feedback prompt
            feedback_prompt = f"""
You are an expert clinical skills rater. Use the five-domain assessment framework.

Transcript of the student's chat with virtual standardized patient {patient_name}:

{transcript}
"""
            
            # Send transcript to feedback assistant
            openai.beta.threads.messages.create(
                thread_id=feedback_thread.id,
                role="user",
                content=feedback_prompt
            )
            
            # Start feedback generation
            feedback_run = openai.beta.threads.runs.create(
                thread_id=feedback_thread.id,
                assistant_id=assistant_id,
            )
            
            # Wait for feedback completion
            with st.spinner("Generating comprehensive feedback..."):
                if not self.wait_for_run_completion(feedback_thread.id, feedback_run.id):
                    return
            
            # Get feedback
            feedback_messages = openai.beta.threads.messages.list(
                thread_id=feedback_thread.id,
                limit=1
            )
            
            if feedback_messages.data and feedback_messages.data[0].role == "assistant":
                feedback_text = feedback_messages.data[0].content[0].text.value
                
                # Display feedback
                st.subheader("📋 Comprehensive Feedback")
                st.markdown(f"*Feedback from {patient_name} encounter*")
                st.markdown(feedback_text)
            else:
                st.error("No feedback generated. Please try again.")
                
        except Exception as e:
            st.error(f"Failed to generate feedback: {e}")
    
    def display_chat_history(self):
        """Display existing chat messages."""
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).markdown(msg["content"])
    
    def get_user_message_count(self):
        """Count user messages in the current conversation."""
        return sum(1 for msg in st.session_state.messages if msg["role"] == "user")
    
    def run(self):
        """Main application loop."""
        st.title("Virtual Patient Encounters (VPE)")
        
        # Sidebar: Actor selection
        if not ASSISTANT_MAP:
            st.error("No virtual patients available. Please check your assistant configuration.")
            st.stop()
        
        selected_actor = st.sidebar.selectbox(
            "Choose a Virtual Patient Encounter",
            list(ASSISTANT_MAP.keys())
        )
        
        assistant_id = ASSISTANT_MAP[selected_actor]
        
        # Reset conversation if actor changed
        self.reset_conversation_if_needed(selected_actor)
        
        # Display chat history
        self.display_chat_history()
        
        # Chat input
        if prompt := st.chat_input("Start chatting with the virtual patient..."):
            # Add user message to display
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").markdown(prompt)
            
            # Get response from virtual patient
            response = self.send_message_to_patient(prompt, assistant_id)
            
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.chat_message("assistant").markdown(response)
        
        # Feedback section
        user_count = self.get_user_message_count()
        
        if user_count >= MIN_MESSAGES_FOR_FEEDBACK:
            st.markdown("---")
            st.subheader("🧠 Ready to end the interview and get feedback?")
            
            if st.button("Generate Feedback!"):
                self.generate_feedback(selected_actor)

# Run the application
if __name__ == "__main__":
    app = VPEApp()
    app.run()