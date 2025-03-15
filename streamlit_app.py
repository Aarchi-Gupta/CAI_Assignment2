import streamlit as st

# Set the page title
st.set_page_config(page_title="Financial RAG Chatbot Cognizant")

# Add a title to the app
st.title("Financial RAG Chatbot Cognizant")

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a text input for the user message
user_input = st.chat_input("Type your message...")

# If user sends a message
if user_input:
    # Add the user's message to the chat history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Hardcoded bot response
    bot_response = "This is a hardcoded response from the bot."

    # Add the bot's response to the chat history
    st.session_state.messages.append({"role": "bot", "content": bot_response})

    # Rerun the script to reflect the updated messages
    st.rerun()
