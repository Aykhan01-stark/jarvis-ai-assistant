import io
import os
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import speech_recognition as sr
from PIL import Image
from duckduckgo_search import DDGS

# ---------------------------------------------------------
# 1. TƏNZİMLƏMƏLƏR VƏ APİ SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Jarvis AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Jarvis - Virtual Süni İntellekt Köməkçisi")

# API Açarı təyini (Streamlit secrets və ya Environment variable üçün)
API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    API_KEY = st.sidebar.text_input("Gemini API Key girin:", type="password")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    st.warning("Davam etmək üçün Gemini API açarını daxil edin.")
    st.stop()

# Çat tarixçəsini saxlanması
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------
# 2. YARDIMÇI FUNKSİYALAR (SƏS VƏ AXTARIŞ)
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

def speech_to_text():
    """Mikrofondan səsi dinləyir və mətnə çevirir."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Dinlənilir... Danışın...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio, language="az-AZ")
            return text
        except sr.WaitTimeoutError:
            st.error("Vaxt bitdi, səs eşidilmədi.")
        except sr.UnknownValueError:
            st.error("Səs anlaşılamadı.")
        except Exception as e:
            st.error(f"Xəta baş verdi: {e}")
    return None

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

# Rejim seçimi
mode = st.sidebar.selectbox(
    "Rejim Seçin:",
    ["Söhbət & Kodlaşdırma", "Şəkil Analizi (Multimodal)", "Veb Axtarış"]
)

# Səs cavabı parametri
enable_voice = st.sidebar.checkbox("Səsli Cavab Aktiv Olsun", value=False)

# Səsli daxiletmə düyməsi
if st.sidebar.button("🎤 Səsli Əmr Ver"):
    voice_prompt = speech_to_text()
    if voice_prompt:
        st.sidebar.success(f"Eşidildi: {voice_prompt}")
        st.session_state.messages.append({"role": "user", "content": voice_prompt})

# Tarixçəni təmizləmə
if st.sidebar.button("🗑️ Tarixçəni Sıfırla"):
    st.session_state.messages = []
    st.rerun()

# ---------------------------------------------------------
# 4. ƏSAS MƏNTİQ
# ---------------------------------------------------------

# Əvvəlki mesajları göstər
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- REJİM 1: SÖHBƏT VƏ KODLAŞDIRMA ---
if mode == "Söhbət & Kodlaşdırma":
    prompt = st.chat_input("Jarvis-ə sual verin və ya kod istəyin...")
    
    # Əgər səsli daxiletmədən mesaj gəlibsə və ya klaviaturadan yazılıbsa
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
