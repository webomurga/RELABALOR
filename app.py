import streamlit as st
import openai
from PIL import Image
import exifread
import os
from geopy.geocoders import Nominatim
from io import BytesIO

# OpenAI ve coğrafi konumlandırma ayarları
openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="replabalor_app")

def get_location_from_exif(uploaded_file):
    """Fotoğrafın EXIF verisinden konumu çıkar"""
    try:
        # UploadedFile'dan bytes oku
        img_bytes = uploaded_file.getvalue()
        tags = exifread.process_file(BytesIO(img_bytes))
        
        # GPS koordinatlarını işle
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef')

        if all([gps_latitude, gps_longitude, gps_latitude_ref, gps_longitude_ref]):
            # Koordinatları ondalık dereceye çevir
            lat = sum([float(rat.num)/float(rat.den) for rat in gps_latitude.values]) / len(gps_latitude.values)
            lon = sum([float(rat.num)/float(rat.den) for rat in gps_longitude.values]) / len(gps_longitude.values)
            
            # Referanslara göre işaret ayarı
            lat = lat if gps_latitude_ref.values == 'N' else -lat
            lon = lon if gps_longitude_ref.values == 'E' else -lon
            
            return f"{lat}, {lon}"
        return None
        
    except Exception as e:
        st.error(f"EXIF okuma hatası: {str(e)}")
        return None

def get_location_details(latlon):
    """Koordinatlardan konum detaylarını al"""
    try:
        location = geolocator.reverse(latlon, exactly_one=True)
        return location.raw.get('address', {})
    except Exception as e:
        st.error(f"Konum bulma hatası: {str(e)}")
        return {}

def generate_gpt_response(prompt, context=[]):
    """GPT-4o-mini ile cevap oluştur"""
    messages = [
        {"role": "system", "content": "Sen Türkiye'nin bölgesel dil ve kültür uzmanı bir asistansın."},
        *context,
        {"role": "user", "content": prompt}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Gerçek model adını kullanın
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