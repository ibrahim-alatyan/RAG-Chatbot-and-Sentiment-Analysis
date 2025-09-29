import os
import time
import streamlit as st
from groq import Groq
import pandas as pd
import sqlite3

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖")
st.title("🤖 RAG Chatbot")

st.subheader("HELLO! Im here to help you and answer you question about your table 🤖")


st.markdown("""
<style>
.stTabs [role="tablist"] {
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return sqlite3.connect("amazon.db", check_same_thread=False)

conn = get_conn()

chatbotTab , tableTab = st.tabs(["chatbot","Table"])

ss = st.session_state


with chatbotTab:
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

    # to store chat
    if "messages" not in ss:
        ss.messages = []
    
    chat_area = st.container()

    # display past messages
    with chat_area:
        for role, msg in ss.messages:
            if role == "user":
                st.chat_message("user").write(msg)
            else:
                st.chat_message("ai").write(msg)

    st.markdown("<div style='min-height:40vh'></div>", unsafe_allow_html=True)

    # user input
    user_input = st.chat_input("Enter your message")
    if user_input:
        with chat_area:
            st.chat_message("user").write(user_input)
        ss.messages.append(("user", user_input))

        with chat_area:
            ai_box = st.chat_message("ai").empty()

        reply_text = ""

        # build full chat history for model
        chat_messages = [{"role": "system", "content": "You are a helpful assistant."}]
        for role, msg in ss.messages:
            role_mapped = "user" if role == "user" else "assistant"
            chat_messages.append({"role": role_mapped, "content": msg})


        if "df_table" in ss and ss.df_table is not None and not ss.df_table.empty:
            preview_csv = ss.df_table.head(3).to_csv(index=False) #I BUT 3 ROWS BECUSE I DONT HAVE TOKEN :)               
            chat_messages.append({                                                  
                "role": "user",
                "content": f"Here is a preview of my table (first 30 rows, CSV):\n{preview_csv}\nUse only this data to answer factual questions."
            })  

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
                ai_box.write(reply_text)
                time.sleep(0.01)

        ss.messages.append(("ai", reply_text))

with tableTab:
    st.markdown("🤖 You can see table ,and sentiment analysis")
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
        conn
    )

    df_sql = pd.read_sql_query(f"SELECT * FROM amazon_review;", conn)
    st.dataframe(df_sql, use_container_width=True) 

    ss.df_table = df_sql #STORE TABLE IN SESSION