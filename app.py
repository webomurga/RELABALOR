import streamlit as st
from PIL import Image
import piexif
import base64
from io import BytesIO
import openai
import os
import json

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# EXIF metadata'dan konum bilgisi almayı deneyen fonksiyon
def get_location_from_exif(image):
    try:
        # EXIF verisini almak
        exif_data = piexif.load(image)
        gps_info = exif_data.get("GPS", {})

        # GPS verisi mevcutsa
        if gps_info:
            latitude = gps_info.get(piexif.GPSIFD.GPSLatitude)
            longitude = gps_info.get(piexif.GPSIFD.GPSLongitude)

            # Latitude ve Longitude mevcutsa, derece, dakika, saniye formatını ondalıklı sayıya çevir
            if latitude and longitude:
                lat = (latitude[0][0] + latitude[1][0] / 60 + latitude[2][0] / 3600)
                lon = (longitude[0][0] + longitude[1][0] / 60 + longitude[2][0] / 3600)

                lat_ref = gps_info.get(piexif.GPSIFD.GPSLatitudeRef)
                lon_ref = gps_info.get(piexif.GPSIFD.GPSLongitudeRef)

                # Konumun doğruluğu için, koordinatları pozitif/negatif yapmak
                if lat_ref != "N":
                    lat = -lat
                if lon_ref != "E":
                    lon = -lon

                return lat, lon

        return None, None
    except Exception as e:
        return None, None

# GPT-4o-mini ile görselden konum çözümleme
def get_location_from_image(image):
    try:
        # Fotoğrafı base64 formatına çevirme
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # GPT-4o-mini'ye gönderme
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # GPT-4o-mini kullanılacak
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Bu görseldeki konumu Türkiye'deki bir şehir veya bölge bazında tespit et."},
                    {"type": "image", "image": {"base64": img_base64}}  # Burada 'image' tipi ve 'base64' verisi kullanılıyor
                ]
            }]
        )

        # Yanıtı işleyip döndürme
        location_data = json.loads(response.choices[0].message.content)
        return location_data
    except Exception as e:
        return {"error": str(e)}

# Streamlit UI
st.set_page_config(page_title="RELABALOR", page_icon="🌍")
st.title("Yöresel Rehber 🌍")
st.markdown("Konumunu algıla, yöresel bilgileri keşfet!")

# Fotoğrafı yükleme
uploaded_file = st.file_uploader("Görsel yükle", type=["jpg", "jpeg", "png"])

# Fotoğraf işlemesi
if uploaded_file:
    image = Image.open(uploaded_file)  # Yüklenen dosyayı PIL.Image formatına dönüştürme
    st.image(image, caption='Yüklenen Görsel', use_column_width=True)
    
    # EXIF metadata'dan konum verisi çekmeye çalış
    st.warning("Fotoğrafın EXIF verisi kontrol ediliyor...")
    lat, lon = get_location_from_exif(uploaded_file)

    if lat and lon:
        st.success(f"Fotoğrafın EXIF verisinden konum tespit edildi: Latitude {lat}, Longitude {lon}")
        st.session_state.location = f"Lat: {lat}, Lon: {lon}"
    else:
        # Eğer EXIF verisinde konum yoksa, GPT-4o-mini'ye gönder
        st.warning("EXIF verisinde konum bulunamadı, GPT-4o-mini ile çözümleme yapılıyor...")
        location_data = get_location_from_image(image)  # Burada image nesnesini gönderiyoruz
        
        if "location" in location_data:
            st.success(f"Konum Tespit Edildi: {location_data['location']}")
            st.session_state.location = location_data['location']
        else:
            st.error(f"Konum tespiti yapılamadı: {location_data.get('error', 'Bilinmeyen hata')}")
