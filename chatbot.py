import os
import time
import streamlit as st
from groq import Groq

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Put it in your environment or .env")

groq_client = Groq(api_key=GROQ_API_KEY)

MODEL_ID = "groq/compound"

st.set_page_config(page_title="Chatbot", page_icon="🤖")
st.title("🤖 Chatbot")

ss = st.session_state

# to store chat
if "messages" not in ss:
    ss.messages = []

# display past messages
for role, msg in ss.messages:
    if role == "user":
        st.chat_message("user").write(msg)
    else:
        st.chat_message("ai").write(msg)

# user input
user_input = st.chat_input("Enter your message")
if user_input:
    st.chat_message("user").write(user_input)
    ss.messages.append(("user", user_input))

    assistant_box = st.chat_message("ai").empty()
    reply_text = ""

    # build full chat history for model
    chat_messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for role, msg in ss.messages:
        role_mapped = "user" if role == "user" else "assistant"
        chat_messages.append({"role": role_mapped, "content": msg})
    chat_messages.append({"role": "user", "content": user_input})

    genReply = groq_client.chat.completions.create(
        model=MODEL_ID,
        messages=chat_messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )

    # to make ai replay message streaming (word by word)
    for chunk in genReply:
        ai_reply = ""
        try:
            ai_reply = chunk.choices[0].delta.content or ""
        except Exception:
            pass

        if ai_reply:
            reply_text += ai_reply
            assistant_box.write(reply_text)
            time.sleep(0.01)

    ss.messages.append(("ai", reply_text))
