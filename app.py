import streamlit as st
import openai
import exifread
import os
import re
from geopy.geocoders import Nominatim
from io import BytesIO

# OpenAI ve coğrafi konumlandırma ayarları
openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="replabalor_app")

def parse_questions(response_text):
    """GPT yanıtındaki soruları çıkar"""
    return re.findall(r'\* (.*?)(?:\n|$)', response_text)

def generate_questions(prompt, context=[]):
    """GPT ile soru listesi oluştur"""
    messages = [
        {"role": "system", "content": "Sadece madde işaretli sorular üret"},
        *context,
        {"role": "user", "content": prompt}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
        max_tokens=200
    )
    return parse_questions(response.choices[0].message['content'])

def get_location_from_exif(uploaded_file):
    """Fotoğrafın EXIF verisinden konumu çıkar"""
    try:
        img_bytes = uploaded_file.getvalue()
        tags = exifread.process_file(BytesIO(img_bytes))
        
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef', 'N')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef', 'E')

        if all([gps_latitude, gps_longitude]):
            # Derece, Dakika, Saniye'yi ondalık dereceye çevir
            def dms_to_decimal(dms, ref):
                degrees = dms.values[0].num / dms.values[0].den
                minutes = dms.values[1].num / dms.values[1].den
                seconds = dms.values[2].num / dms.values[2].den
                decimal = degrees + (minutes / 60) + (seconds / 3600)
                return decimal if ref in ['N', 'E'] else -decimal
            
            lat = dms_to_decimal(gps_latitude, str(gps_latitude_ref))
            lon = dms_to_decimal(gps_longitude, str(gps_longitude_ref))
            
            return f"{lat:.6f}, {lon:.6f}"
        return None
        
    except Exception as e:
        st.error(f"EXIF okuma hatası: {str(e)}")
        return None

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "questions" not in st.session_state:
    st.session_state.questions = []

# Arayüz
st.title("RELABALOR - Butonlu Etkileşim")
uploaded_file = st.file_uploader("Fotoğraf Yükle", type=["jpg", "jpeg", "png"])

# Fotoğraf yüklendiğinde
if uploaded_file and not st.session_state.messages:
    latlon = get_location_from_exif(uploaded_file)
    if latlon:
        location = geolocator.reverse(latlon, language="tr")
        context = f"Konum: {location.raw.get('address', {}).get('city', 'Bilinmeyen')}"
        
        # İlk soruları oluştur
        st.session_state.questions = generate_questions(
            f"Şu konum için 3 turistik soru üret: {context}. Yanıt verme, sadece soruları sırala."
        )
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"**{context}**\n\nLütfen bir soru seçin:"
        })

# Mesajları göster
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Butonlar için container
button_container = st.container()

# Buton etkileşimi
if st.session_state.questions:
    with button_container:
        cols = st.columns(2)
        for i, q in enumerate(st.session_state.questions):
            if cols[i%2].button(q, key=f"btn_{i}"):
                # Seçilen soruyu ekle
                st.session_state.messages.append({"role": "user", "content": q})
                
                # GPT'den cevap al
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": q}],
                    temperature=0.7,
                    max_tokens=500
                )
                answer = response.choices[0].message['content']
                
                # Takip sorularını oluştur
                new_questions = generate_questions(
                    f"Bu cevap için 2 takip sorusu üret: {answer}. Yanıt verme, sadece soruları sırala."
                )
                
                # Güncellemeleri kaydet
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"{answer}\n\n**Yeni Sorular:**"
                })
                st.session_state.questions = new_questions
                st.rerun()

# Kullanıcı yazı giremesin diye inputu gizle
st.markdown("""
<style>
    .stChatInput {visibility: hidden; height: 0;}
</style>
""", unsafe_allow_html=True)