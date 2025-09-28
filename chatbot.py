import streamlit as st
from huggingface_hub import InferenceClient
import time
import os

st.set_page_config(page_title="Chatbot")

ss = st.session_state #save session

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

client = InferenceClient(model=MODEL_ID, token=HF_TOKEN)

#to store the chat
if "messages" not in ss:
    ss.messages = []

#to load the messages
for role , msg in ss.messages:
    if role == "user":
        st.chat_message("user").write(msg)
    else:
        st.chat_message("AI").write(msg)

#to save message and user send message
user_input = st.chat_input("Enter your message:")
if user_input:
    st.chat_message("user").write(user_input)
    ss.messages.append(("user", user_input))

    #AI REPLAY
    aiReplay = st.chat_message("AI").empty()
    reply_text = ""

    # FOR MAKE IT WORD BY WORD (STREAMING)
    REPLAY = client.chat_completion(
        model=MODEL_ID,
        messages=[{"role": "user", "content": user_input}],
        stream=True,
        max_tokens=128, # max tokens in one response
    )

    # display word by word
    for chunks in REPLAY:
        chunk = chunks.choices[0].delta.get("content", "")
        reply_text += chunk
        aiReplay.write(reply_text)
        time.sleep(0.02) #to make word gen slower

    ss.messages.append(("assistant", reply_text))