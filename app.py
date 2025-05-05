import streamlit as st
from PIL import Image
import piexif
import geopy
from geopy.geocoders import Nominatim
import os
import json

# === API Anahtarı ===
# openai.api_key = os.getenv("OPENAI_API_KEY")  # OpenAI API artık kullanılmıyor

# === EXIF verisinden Konum Bilgisi Çekme ===
def get_location_from_exif(image_path):
    try:
        # Görselin EXIF verilerini al
        exif_dict = piexif.load(image_path)
        
        # GPS verisini al
        if "GPS" in exif_dict:
            gps_info = exif_dict["GPS"]
            if gps_info:
                lat_ref = gps_info.get(piexif.GPSIFD.GPSLatitudeRef)
                lon_ref = gps_info.get(piexif.GPSIFD.GPSLongitudeRef)
                lat = gps_info.get(piexif.GPSIFD.GPSLatitude)
                lon = gps_info.get(piexif.GPSIFD.GPSLongitude)
                
                # GPS koordinatlarını derece cinsine çevir
                if lat and lon:
                    lat_deg = lat[0][0] / lat[0][1] + lat[1][0] / lat[1][1] / 60 + lat[2][0] / lat[2][1] / 3600
                    lon_deg = lon[0][0] / lon[0][1] + lon[1][0] / lon[1][1] / 60 + lon[2][0] / lon[2][1] / 3600
                    
                    # Koordinatların doğru yönünü almak için
                    if lat_ref != "N":
                        lat_deg = -lat_deg
                    if lon_ref != "E":
                        lon_deg = -lon_deg
                    
                    # Geopy ile koordinatlara ait adresi bul
                    geolocator = Nominatim(user_agent="relabalor_app")
                    location = geolocator.reverse((lat_deg, lon_deg), language='tr')
                    
                    if location:
                        return {"location": location.address, "confidence": "yüksek"}
                    else:
                        return {"location": None, "confidence": "düşük"}
                else:
                    return {"location": None, "confidence": "düşük"}
        else:
            return {"location": None, "confidence": "düşük"}
    except Exception as e:
        return {"location": None, "error": str(e)}

# === Yöresel Yanıt ===
def get_response(prompt, location):
    # Yöresel yanıt için API kullanımı burada geçerli değil çünkü EXIF verisiyle doğrudan cevap dönülecek.
    return f"{location} hakkında sorunuza cevap verdim: {prompt}"

# === Uygulama Başlığı ve Oturum Yönetimi ===
st.set_page_config(page_title="RELABALOR", layout="centered")
st.title("📸 RELABALOR - Yöresel Rehber")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "location" not in st.session_state:
    st.session_state.location = None

# === Görsel Yükleme: İlk Mesaj Gibi Göster ===
if not st.session_state.location:
    with st.chat_message("assistant"):
        st.markdown("📍 Merhaba! Lütfen bulunduğun yerden bir fotoğraf yükleyerek konumunu paylaş.")

    uploaded_file = st.file_uploader("Görsel yükle", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file:
        image = Image.open(uploaded_file)
        with st.chat_message("assistant"):
            st.image(image, caption="Yüklenen görsel")

        # EXIF verisinden konum bilgisi al
        with st.chat_message("assistant"):
            with st.spinner("Konum tespit ediliyor..."):
                # Yüklenen dosyanın geçici yolu
                with open("temp_image.jpg", "wb") as f:
                    f.write(uploaded_file.getbuffer())

                location_data = get_location_from_exif("temp_image.jpg")
                
                if location_data.get("location"):
                    st.session_state.location = location_data["location"]
                    st.success(f"📌 Tespit edilen konum: **{st.session_state.location}**")
                else:
                    st.error(f"Konum tespit edilemedi: {location_data.get('error', 'Bilinmeyen hata')}")

# === Sohbet Arayüzü ===
if st.session_state.location:
    st.markdown(f"🗺️ Şu an {st.session_state.location} için yöresel bilgi modundasınız.")

    # Önceki mesajları göster
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Yeni mesaj girişi
    if prompt := st.chat_input("Yöresel rehberine bir şey sor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Yanıt hazırlanıyor..."):
                reply = get_response(prompt, st.session_state.location)
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})