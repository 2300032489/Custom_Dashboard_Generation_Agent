import os
import io
import re
import pandas as pd
from langdetect import detect, DetectorFactory
from unidecode import unidecode
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
DetectorFactory.seed = 0

# TEMP KEY (hard-coded)
API_KEY = "AIzaSyBFUpR-76--zGRDsDTftSeKxJdGEXqoTAE"
genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.0-flash"

SYSTEM_INSTRUCTIONS = (
    "You are a friendly multilingual AI + Data Analyst chatbot. "
    "If user chats casually respond casually. "
    "If user asks data insights, analyze data. "
    "If user asks sum / average / mean on file, calculate directly. "
    "always be short, clear, simple."
)

def _safe_lang(text: str) -> str:
    try: return detect(text)
    except: return "en"

def _normalize(text: str) -> str:
    text = text or ""
    text = text.replace("\r"," ").replace("\n"," ").strip()
    text = re.sub(r"\s+"," ",text)
    return text

def read_any_file_to_text(filename: str, content: bytes) -> str:
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
        return df.to_csv(index=False)
    if filename.lower().endswith((".xls",".xlsx")):
        df = pd.read_excel(io.BytesIO(content))
        return df.to_csv(index=False)
    return ""

def analyze_text_or_table(user_input_text: str=None, file_name: str=None, file_bytes: bytes=None) -> str:

    # greetings
    greetings = ["hi","hello","hey","hola","namaste","hii","hai"]
    if user_input_text and user_input_text.lower().strip() in greetings:
        return "Hello! 👋 How can I help you today?"

    # if file present
    if file_name and file_bytes:
        doc_text = read_any_file_to_text(file_name, file_bytes)
        user_text = user_input_text or ""

        # ---- direct numeric calculation ----
        try:
            df = None
            if file_name.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif file_name.endswith((".xlsx",".xls")):
                df = pd.read_excel(io.BytesIO(file_bytes))

            if df is not None and user_input_text:
                if any(w in user_input_text.lower() for w in ["sum","total","average","mean"]):
                    numeric_cols = df.select_dtypes(include='number').columns
                    if len(numeric_cols)>0:
                        result={}
                        for c in numeric_cols:
                            result[c] = {
                                "sum": float(df[c].sum()),
                                "mean": float(df[c].mean())
                            }

                        # pretty formatting
                        lines=[]
                        for col, stats in result.items():
                            lines.append(f"- **{col}** → total = {stats['sum']:,} | average = {stats['mean']:,}")

                        numeric_block="**Numeric Summary**\n"+"\n".join(lines)

                        # ask gemini for 1-2 short insights
                        small_prompt=f"""You are a short data analyst.

Here is a numeric summary:

{numeric_block}

Give 2 bullet insights maximum. very short."""

                        model=genai.GenerativeModel(MODEL_NAME)
                        llm_resp=model.generate_content(small_prompt)
                        llm_text=llm_resp.text.strip()
                        return numeric_block+"\n\n**Insights**\n"+llm_text

        except:
            pass

        combined = f"{user_text}\n\n{doc_text}"

    else:
        combined = user_input_text or ""

    normalized=_normalize(combined)

    prompt=f"""{SYSTEM_INSTRUCTIONS}

USER MESSAGE:
{normalized}
"""

    model=genai.GenerativeModel(MODEL_NAME)
    resp=model.generate_content(prompt)
    return resp.text.strip() if resp.text else "No response"
