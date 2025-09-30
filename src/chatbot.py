import os
import time
import streamlit as st
from groq import Groq
import pandas as pd
import sqlite3
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

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

@st.cache_resource
def load_gpt2_model():
    """Load GPT-2 model and tokenizer from Hugging Face"""
    model_name = "openai-community/gpt2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer

conn = get_conn()

# Model selection radio button
model_choice = st.radio(
    "Choose your model:",
    ["Groq API", "GPT-2 Local"],
)

chatbotTab, tableTab = st.tabs(["chatbot", "Table"])

ss = st.session_state

##########################
#### chat bot tab   ######
##########################

with chatbotTab:  
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    # Initialize based on model choice
    if model_choice == "Groq API":
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        if not GROQ_API_KEY:
            st.error("GROQ_API_KEY is not set. Put it in your environment or .env")
            st.stop()
        groq_client = Groq(api_key=GROQ_API_KEY)
        MODEL_ID = "groq/compound"
    else:
        with st.spinner("Loading GPT-2 model... (this may take a moment)"):
            gpt2_model, gpt2_tokenizer = load_gpt2_model()
        st.success("GPT-2 model loaded successfully!")

    # Store chat
    if "messages" not in ss:
        ss.messages = []
    
    chat_area = st.container()

    # Display past messages
    with chat_area:
        for role, msg in ss.messages:
            if role == "user":
                st.chat_message("user").write(msg)
            else:
                st.chat_message("ai").write(msg)

    st.markdown("<div style='min-height:40vh'></div>", unsafe_allow_html=True)

    # User input
    user_input = st.chat_input("Enter your message")
    if user_input:
        with chat_area:
            st.chat_message("user").write(user_input)
        ss.messages.append(("user", user_input))

        with chat_area:
            ai_box = st.chat_message("ai").empty()

        reply_text = ""

        ##############################
        ##### groq api ###############
        ##############################
        
        if model_choice == "Groq API":
            # Groq API logic
            chat_messages = [{"role": "system", "content": "You are a helpful assistant."}]
            for role, msg in ss.messages:
                role_mapped = "user" if role == "user" else "assistant"
                chat_messages.append({"role": role_mapped, "content": msg})

            if "df_table" in ss and ss.df_table is not None and not ss.df_table.empty:
                preview = ss.df_table
                chat_messages.append({
                    "role": "user",
                    "content": f"Here is a preview of my table\n{preview}\nUse only this data to answer factual questions."
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
            
            # make reply streaming
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

        ########################################
        ######### localy gpt2 ##################
        ########################################

        else:
            context = ""
            
            # Add conversation history
            recent_messages = ss.messages[-4:] if len(ss.messages) > 4 else ss.messages
            for role, msg in recent_messages[:-1]:
                context += f"Q: {msg}\nA: " if role == "user" else f"{msg}\n"
            
            # Add current question
            context += f"Q: {user_input}\nA:"

            # Generate with GPT-2
            inputs = gpt2_tokenizer.encode(context, return_tensors="pt", max_length=400, truncation=True)
            
            # Set attention mask
            attention_mask = torch.ones(inputs.shape, dtype=torch.long)
            
            with torch.no_grad():
                outputs = gpt2_model.generate(
                    inputs,
                    attention_mask=attention_mask,
                    max_new_tokens=100,
                    num_return_sequences=1,
                    temperature=0.9,
                    top_k=50,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=gpt2_tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )
            
            full_response = gpt2_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the new response after the prompt
            reply_text = full_response[len(gpt2_tokenizer.decode(inputs[0], skip_special_tokens=True)):].strip()
            
            # Clean up - stop at question mark, period, or newline
            for delimiter in ['\nQ:', '\n\n', '?', '. ']:
                if delimiter in reply_text:
                    reply_text = reply_text.split(delimiter)[0].strip()
                    if delimiter in ['?', '. ']:
                        reply_text += delimiter.strip()
                    break
            
            # Ensure it ends properly
            if reply_text and reply_text[-1] not in ['.', '?', '!']:
                reply_text += '.'
            
            # streaming 
            temp_text = ""
            for char in reply_text:
                temp_text += char
                ai_box.write(temp_text)
                time.sleep(0.01)

        ss.messages.append(("ai", reply_text))

########################
##### table tab ########
########################

with tableTab:
    st.markdown("🤖 You can see table, and sentiment analysis")
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
        conn
    )

    df_sql = pd.read_sql_query(f"SELECT * FROM amazon_review;", conn)
    st.dataframe(df_sql, use_container_width=True)

    ss.df_table = df_sql  # Store table in session