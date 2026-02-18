import streamlit as st
import requests
from deep_translator import GoogleTranslator
import whisper
import os
import difflib
import io

# --- ページ設定 & デザイン ---
st.set_page_config(page_title="AGENTIA for QTnet β", layout="wide") # 横並びのためにwideに設定

st.markdown("""
    <style>
    header {visibility: hidden;}
    .main .block-container { max-width: 1000px; padding-top: 2rem; }
    .quality-badge { padding: 4px 12px; border-radius: 4px; font-weight: bold; }
    .pass { background-color: #d4edda; color: #155724; }
    .fail { background-color: #f8d7da; color: #721c24; }
    .stButton>button { 
        background-color: #004e92; 
        color: white; 
        border-radius: 6px;
    }
    /* ストックカードのスタイル */
    .stock-card {
        border: 1px solid #ddd;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 (音声ストック用) ---
if "audio_stock" not in st.session_state:
    st.session_state.audio_stock = []

# --- 内部解析関数 ---
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

# --- メインレイアウト ---
col_main, col_stock = st.columns([1.2, 1]) # 左に操作系、右にストック

with col_main:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=300)
    else:
        st.title("音声生成システム")

    text_input = st.text_area("テキスト入力 (日本語)", placeholder="音声化したい内容を入力してください...", height=150)
    
    c1, c2 = st.columns(2)
    with c1:
        lang_option = st.selectbox("出力言語", ["日本語", "英語", "中国語", "スペイン語", "韓国語"])
    with c2:
        # ボイス選択を2つに限定
        voice_style = st.selectbox("音声モデル", ["男性", "女性"])

    VOICE_MODELS = {
        "男性": "b8580c330cd74c2bbb7785815f1756d3",
        "女性": "735434a118054f65897638d4b7380dfc"
    }

    if st.button("音声を生成・検品"):
        api_key = st.secrets.get("FISH_AUDIO_API_KEY")
        if not api_key:
            st.error("Secretsに 'FISH_AUDIO_API_KEY' を設定してください。")
        elif text_input:
            with st.spinner('AI生成中...'):
                try:
                    lang_map = {"日本語": "ja", "英語": "en", "中国語": "zh-CN", "スペイン語": "es", "韓国語": "ko"}
                    translated = GoogleTranslator(source='ja', target=lang_map[lang_option]).translate(text_input)
                    
                    # APIリクエスト (Fish Audio)
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"text": translated, "format": "wav", "reference_id": VOICE_MODELS[voice_style]}
                    res = requests.post("https://api.fish.audio/v1/tts", headers=headers, json=payload)
                    
                    if res.status_code == 200:
                        audio_data = res.content
                        analysis = analyze_audio(audio_data, translated)
                        
                        # ストックに追加 (最大5つ、新しいものを上に)
                        new_item = {
                            "audio": audio_data,
                            "text": text_input[:20] + "...",
                            "lang": lang_option,
                            "acc": analysis['accuracy'],
                            "trans": analysis['transcribed']
                        }
                        st.session_state.audio_stock.insert(0, new_item)
                        if len(st.session_state.audio_stock) > 5:
                            st.session_state.audio_stock.pop()
                            
                        st.success("生成完了！右側のストックに追加されました。")
                    else:
                        st.error(f"APIエラー: {res.status_code}")
                except Exception as e:
                    st.error(f"エラー: {e}")

# --- 右側：音声ストックエリア ---
with col_stock:
    st.subheader("🎵 生成済みストック (最新5件)")
    if not st.session_state.audio_stock:
        st.info("生成された音声がここに表示されます")
    
    for i, item in enumerate(st.session_state.audio_stock):
        with st.container():
            st.markdown(f"""
            <div class="stock-card">
                <small>{item['lang']} | 精度: {item['acc']:.1f}%</small><br>
                <strong>{item['text']}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.audio(item['audio'])
            
            # ダウンロードボタン (キーをユニークにするために i を使用)
            st.download_button(
                label=f"Download WAV #{i+1}",
                data=item['audio'],
                file_name=f"voice_{item['lang']}_{i}.wav",
                mime="audio/wav",
                key=f"dl_{i}"
            )
            st.markdown("---")

st.caption("© 2026 Powered by FEIDIAS Inc.")