import streamlit as st
import openai
from PIL import Image
import exifread
import os
from geopy.geocoders import Nominatim

# OpenAI ve coğrafi konumlandırma ayarları
openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="replabalor_app")

def get_location_from_exif(image_path):
    """Fotoğrafın EXIF verisinden konumu çıkar"""
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f)
        
    gps_tags = {}
    for tag in tags:
        if tag.startswith('GPS GPSLatitude') or tag.startswith('GPS GPSLongitude'):
            gps_tags[tag] = tags[tag]

    if gps_tags:
        try:
            lat = [float(x.num)/float(x.den) for x in tags['GPS GPSLatitude'].values]
            lon = [float(x.num)/float(x.den) for x in tags['GPS GPSLongitude'].values]
            return f"{sum(lat)/len(lat)}, {sum(lon)/len(lon)}"
        except:
            return None
    return None

def get_location_details(latlon):
    """Koordinatlardan konum detaylarını al"""
    location = geolocator.reverse(latlon, exactly_one=True)
    return location.raw.get('address', {})

def generate_gpt_response(prompt, context=[]):
    """GPT-4o-mini ile cevap oluştur"""
    messages = [
        {"role": "system", "content": "Sen Türkiye'nin bölgesel dil ve kültür uzmanı bir asistansın."},
        *context,
        {"role": "user", "content": prompt}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-4-mini",  # Gerçek model adını kullanın
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message['content']

# Streamlit arayüzü
st.title("RELABALOR - Bölgesel Asistan")
st.subheader("Fotoğrafınızı Yükleyin, Konumunuz Belirlensin, Sorularınızı Cevaplayalım!")

# Sohbet geçmişi
if "messages" not in st.session_state:
    st.session_state.messages = []

# Fotoğraf yükleme
uploaded_file = st.file_uploader("Bir fotoğraf yükleyin", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # EXIF'den konum bilgisi
    latlon = get_location_from_exif(uploaded_file)
    if latlon:
        location_details = get_location_details(latlon)
        context = f"Konum: {location_details.get('city', 'Bilinmeyen')}, {location_details.get('state', 'Bilinmeyen')}"
        
        # Otomatik başlangıç soruları
        initial_questions = generate_gpt_response(
            f"Şu konum için 3 tane turistik ve kültürel soru üret: {context}. Soruları madde işaretleriyle ver."
        )
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"{context}\n\n{initial_questions}"
        })
    else:
        st.error("Fotoğrafta konum bilgisi bulunamadı")

# Sohbet geçmişini göster
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Kullanıcı girişi
if prompt := st.chat_input("Sorunuzu yazın veya aşağıdaki sorulardan birini seçin"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # GPT ile cevap oluştur
    response = generate_gpt_response(
        prompt,
        context=st.session_state.messages
    )
    
    # Takip soruları oluştur
    follow_up = generate_gpt_response(
        "Bu cevap için 2 tane kısa takip sorusu üret. Sadece soruları madde işaretleriyle ver."
    )
    
    full_response = f"{response}\n\n**Takip Soruları:**\n{follow_up}"
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()