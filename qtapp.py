import streamlit as st
import requests
from deep_translator import GoogleTranslator
import whisper
import os
import difflib

# --- ページ設定 & デザイン ---
st.set_page_config(page_title="AGENTIA for QTnet", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    header {visibility: hidden;}
    
    /* ページ全体のロゴを強制的に中央へ */
    .stImage {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* コンテナの幅調整 */
    .main .block-container { max-width: 1100px; padding-top: 2rem; }
    
    .section-title {
        font-size: 0.9rem;
        font-weight: bold;
        color: #666;
        margin-bottom: 1rem;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    
    /* ストックカード内のスクロール設定 */
    .stock-card {
        padding: 12px;
        border: 1px solid #f0f0f0;
        border-radius: 4px;
        margin-bottom: 12px;
        background-color: #fafafa;
    }
    
    .scrollable-text {
        font-size: 0.85rem;
        color: #444;
        line-height: 1.5;
        max-height: 150px; 
        overflow-y: auto;
        padding-right: 5px;
        margin-bottom: 10px;
        white-space: pre-wrap;
    }
    
    .scrollable-text::-webkit-scrollbar { width: 4px; }
    .scrollable-text::-webkit-scrollbar-thumb { background: #ddd; border-radius: 10px; }
    
    .quality-badge { font-size: 0.8rem; padding: 2px 8px; border-radius: 12px; font-weight: bold; }
    .pass { background-color: #e6fffa; color: #234e52; border: 1px solid #b2f5ea; }
    .fail { background-color: #fff5f5; color: #822727; border: 1px solid #feb2b2; }
    
    .stButton>button { 
        width: 100%;
        background-color: #1a202c;
        color: white;
        border: none;
        height: 3rem;
    }
    .stButton>button:hover { background-color: #2d3748; color: white; border: none; }
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

# --- レイアウト開始 ---

# 1. ロゴ配置 (カラム作成前に行うことで全体の中央を確保)
if os.path.exists("logo.png"):
    # st.columnsでダミーの余白を作って中央に寄せる確実な方法
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        st.image("logo.png", use_container_width=True)
else:
    st.markdown("<h2 style='text-align: center; color: #333;'>AGENTIA</h2>", unsafe_allow_html=True)

# 縦の余白
st.write("##")

# 2. 2カラム構成 (ここから生成とストック)
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-title">AUDIO GENERATION</div>', unsafe_allow_html=True)
    # 高さを300に設定
    text_input = st.text_area("本文", placeholder="音声化したい内容を入力...", height=300, label_visibility="collapsed")
    
    c1, c2 = st.columns(2)
    with c1:
        lang_option = st.selectbox("出力言語", ["日本語", "英語", "中国語", "スペイン語", "韓国語"])
    with c2:
        voice_style = st.selectbox("音声モデル", ["男性", "女性"])

    if st.button("音声を生成・検品"):
        api_key = st.secrets.get("FISH_AUDIO_API_KEY")
        if not api_key:
            st.error("APIキーが必要です。")
        elif text_input:
            with st.spinner('Generating...'):
                try:
                    lang_map = {"日本語": "ja", "英語": "en", "中国語": "zh-CN", "スペイン語": "es", "韓国語": "ko"}
                    VOICE_MODELS = {
                        "男性": "b8580c330cd74c2bbb7785815f1756d3",
                        "女性": "8c674440f29d49189c4d526a95c8bec3"
                    }
                    translated = GoogleTranslator(source='ja', target=lang_map[lang_option]).translate(text_input)
                    
                    res = requests.post(
                        "https://api.fish.audio/v1/tts",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"text": translated, "format": "wav", "reference_id": VOICE_MODELS[voice_style]}
                    )
                    
                    if res.status_code == 200:
                        audio_data = res.content
                        analysis = analyze_audio(audio_data, translated)
                        
                        new_item = {
                            "audio": audio_data,
                            "full_text": text_input, 
                            "lang": lang_option,
                            "acc": analysis['accuracy']
                        }
                        st.session_state.audio_stock.insert(0, new_item)
                        if len(st.session_state.audio_stock) > 5:
                            st.session_state.audio_stock.pop()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

with col_right:
    st.markdown('<div class="section-title">RECENT STOCK</div>', unsafe_allow_html=True)
    
    if not st.session_state.audio_stock:
        st.caption("履歴はありません")
    
    for i, item in enumerate(st.session_state.audio_stock):
        with st.container():
            acc_class = "pass" if item['acc'] > 80 else "fail"
            st.markdown(f"""
            <div class="stock-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.75rem; color: #999;">{item['lang']}</span>
                    <span class="quality-badge {acc_class}">{item['acc']:.1f}%</span>
                </div>
                <div class="scrollable-text">{item['full_text']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            aud_col, dl_col = st.columns([4, 1])
            with aud_col:
                st.audio(item['audio'])
            with dl_col:
                st.download_button("DL", item['audio'], f"voice_{i}.wav", "audio/wav", key=f"dl_{i}")
            st.write("") 

st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
st.caption("© 2026 Powered by FEIDIAS Inc.")