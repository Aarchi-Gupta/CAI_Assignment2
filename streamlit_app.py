__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
# import import_ipynb
# import Basic_RAG as model
from basic_rag import ask_local_llm, retrieve_similar_chunks

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
    # bot_response = "This is a hardcoded response from the bot."
    retrieved_chunks_DB = retrieve_similar_chunks(user_input)
    bot_response = ask_local_llm(user_input, retrieved_chunks_DB)

    # Add the bot's response to the chat history
    st.session_state.messages.append({"role": "bot", "content": bot_response})

    # Rerun the script to reflect the updated messages
    st.rerun()
