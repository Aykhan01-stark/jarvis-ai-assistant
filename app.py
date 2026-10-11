import io
import os
import streamlit as st
from google import genai
from gtts import gTTS
from PIL import Image
from duckduckgo_search import DDGS

# ---------------------------------------------------------
# 1. TƏNZİMLƏMƏLƏR VƏ API SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Jarvis AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Jarvis - Virtual Süni İntellekt Köməkçisi")

API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    API_KEY = st.sidebar.text_input("Gemini API Key girin:", type="password")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    st.warning("Davam etmək üçün Gemini API açarını daxil edin.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------
# 2. YARDIMÇI FUNKSİYALAR
# ---------------------------------------------------------
def text_to_speech(text: str):
    """Mətni audioya çevirir və Streamlit-də oxudur."""
    try:
        tts = gTTS(text=text, lang="az")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3")
    except Exception as e:
        st.error(f"Səs oxuma xətası: {e}")

def web_search(query: str) -> str:
    """İnternetdə axtarış edib nəticə qaytarır."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            search_data = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            return search_data
    except Exception as e:
        return f"Axtarışda xəta: {e}"

# ---------------------------------------------------------
# 3. İNTERFEYS VƏ İDARƏETMƏ PANELİ
# ---------------------------------------------------------
st.sidebar.header("⚙️ Jarvis İdarəetmə Paneli")

mode = st.sidebar.selectbox(
    "Rejim Seçin:",
    ["Söhbət & Kodlaşdırma", "Şəkil Analizi (Multimodal)", "Veb Axtarış"]
)

enable_voice = st.sidebar.checkbox("Səsli Cavab Aktiv Olsun", value=False)

if st.sidebar.button("🗑️ Tarixçəni Sıfırla"):
    st.session_state.messages = []
    st.rerun()

# ---------------------------------------------------------
# 4. ƏSAS MƏNTİQ
# ---------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- REJİM 1: SÖHBƏT VƏ KODLAŞDIRMA ---
if mode == "Söhbət & Kodlaşdırma":
    prompt = st.chat_input("Jarvis-ə sual verin və ya kod istəyin...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            reply = response.text
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

            if enable_voice:
                text_to_speech(reply)

# --- REJİM 2: ŞƏKİL ANALİZİ ---
elif mode == "Şəkil Analizi (Multimodal)":
    uploaded_file = st.file_uploader("Bir şəkil yükləyin:", type=["png", "jpg", "jpeg", "webp"])
    image_prompt = st.text_input("Şəkil haqqında nə öyrənmək istəyirsiniz?", "Bu şəkildə nə təsvir olunub?")

    if uploaded_file and st.button("Şəkli Analiz Et"):
        image = Image.open(uploaded_file)
        st.image(image, caption="Yüklənən Şəkil", use_column_width=True)

        with st.spinner("Şəkil analiz edilir..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, image_prompt]
            )
            st.markdown("### Jarvis-in Analizi:")
            st.write(response.text)
            
            if enable_voice:
                text_to_speech(response.text)

# --- REJİM 3: VEB AXTARIŞ ---
elif mode == "Veb Axtarış":
    search_query = st.text_input("İnternetdə axtarmaq istədiyiniz mövzu:")
    if search_query and st.button("Axtar və İzah Et"):
        with st.spinner("İnternetdən məlumatlar toplanır..."):
            web_data = web_search(search_query)
            
            prompt = f"Aşağıdakı veb axtarış nəticələrinə əsasən sualı cavablandır:\n\nSual: {search_query}\n\nMəlumatlar:\n{web_data}"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            st.markdown("### Axtarış Nəticələrinə Əsasən Cavab:")
            st.write(response.text)
            
            if enable_voice:
                text_to_speech(response.text)
