import streamlit as st
import requests
from deep_translator import GoogleTranslator
import whisper
import os
import difflib

# --- ページ設定 & デザイン ---
st.set_page_config(page_title="AGENTIA for QTnetβ", layout="wide")

st.markdown("""
    <style>
    /* 全体背景とフォント */
    .stApp { background-color: #ffffff; }
    header {visibility: hidden;}
    
    /* コンテナ調整 */
    .main .block-container { max-width: 1100px; padding-top: 1rem; }
    
    /* センターロゴ用 */
    .logo-container { display: flex; justify-content: center; margin-bottom: 2rem; }
    
    /* セクションの枠組み */
    .section-title {
        font-size: 0.9rem;
        font-weight: bold;
        color: #666;
        margin-bottom: 1rem;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    
    /* ストックカード：さらにミニマルに */
    .stock-card {
        padding: 12px;
        border: 1px solid #f0f0f0;
        border-radius: 4px;
        margin-bottom: 8px;
        background-color: #fafafa;
    }
    
    /* バッジ */
    .quality-badge { font-size: 0.8rem; padding: 2px 8px; border-radius: 12px; }
    .pass { background-color: #e6fffa; color: #234e52; border: 1px solid #b2f5ea; }
    .fail { background-color: #fff5f5; color: #822727; border: 1px solid #feb2b2; }
    
    /* ボタン */
    .stButton>button { 
        width: 100%;
        background-color: #1a202c;
        color: white;
        border: none;
        transition: 0.2s;
    }
    .stButton>button:hover { background-color: #2d3748; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if "audio_stock" not in st.session_state:
    st.session_state.audio_stock = []

@st.cache_resource
def load_whisper():
    return whisper.load_model("base")

def analyze_audio(audio_bytes, target_text):
    temp_file = "temp_audio.wav"
    with open(temp_file, "wb") as f:
        f.write(audio_bytes)
    try:
        model = load_whisper()
        result = model.transcribe(temp_file)
        transcribed_text = result["text"].strip()
        match_score = difflib.SequenceMatcher(None, target_text.lower(), transcribed_text.lower()).ratio()
        return {"transcribed": transcribed_text, "accuracy": match_score * 100}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# --- レイアウト ---

# 1. ロゴ（センター配置）
if os.path.exists("logo.png"):
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.image("logo.png", width=280)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown("<h1 style='text-align: center;'>AGENTIA</h1>", unsafe_allow_html=True)

# 2. 2カラム構成
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-title">AUDIO GENERATION</div>', unsafe_allow_html=True)
    text_input = st.text_area("本文", placeholder="テキストを入力...", height=180, label_visibility="collapsed")
    
    c1, c2 = st.columns(2)
    with c1:
        lang_option = st.selectbox("言語", ["日本語", "英語", "中国語", "スペイン語", "韓国語"])
    with c2:
        voice_style = st.selectbox("モデル", ["男性", "女性"])

    if st.button("生成を実行"):
        api_key = st.secrets.get("FISH_AUDIO_API_KEY")
        if not api_key:
            st.error("APIキーが設定されていません。")
        elif text_input:
            with st.spinner('Processing...'):
                try:
                    lang_map = {"日本語": "ja", "英語": "en", "中国語": "zh-CN", "スペイン語": "es", "韓国語": "ko"}
                    VOICE_MODELS = {
                        "男性": "b8580c330cd74c2bbb7785815f175