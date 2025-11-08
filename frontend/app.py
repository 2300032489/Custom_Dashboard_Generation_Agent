# frontend/app.py  (HOME PAGE)
import streamlit as st
from streamlit_lottie import st_lottie
import json

st.set_page_config(page_title="Analytix Adda", layout="wide")

# ---- LOAD LOTTIE ----
with open("animation.json","r", encoding="utf-8") as f:
    anim = json.load(f)

# ---- CENTER TITLE ----
st.markdown("<h1 style='text-align:center; font-size:48px;'>ANALYTIX ADDA</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# animation
st_lottie(anim, height=320, key="home_anim")

# slogans
slogans = [
    "Transform Data → Discover Patterns → Predict Future",
    "Your AI Partner for Business Intelligence",
    "Ask. Analyse. Understand. Decide.",
    "Turn Raw Data into Smart Decisions"
]

js_code = f"""
<script>
var slogans = {slogans};
var i = 0;
function rotate() {{
  var el = document.getElementById('slogan');
  if (!el) return;
  el.innerHTML = slogans[i];
  i=(i+1)%slogans.length;
}}
setInterval(rotate,2000);
rotate();
</script>
"""

st.markdown("""
<div style='text-align:center; font-size:26px; margin-top:25px; font-weight:600;' id='slogan'></div>
""", unsafe_allow_html=True)

st.markdown(js_code, unsafe_allow_html=True)

# about section
st.markdown("""
<br><br>
<div style='text-align:center; font-size:20px; color:#444; line-height:1.6;'>
Welcome to <b>Analytix Adda</b>.<br>
Upload your data → Ask anything in your language → Get instant insights.<br>
Forecast, summarise, detect patterns, get business suggestions… all in one place.
<br><br>
Use the left sidebar → open <b>📊 DASHBOARD</b> to start!
</div>
""", unsafe_allow_html=True)
