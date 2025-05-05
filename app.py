import base64
import openai
import json
import os
from PIL import Image
from io import BytesIO
import streamlit as st

# OpenAI API konfigürasyonu
openai.api_key = os.getenv("OPENAI_API_KEY")

# Görseli Base64 formatına dönüştürme fonksiyonu
def image_to_base64(image):
    """Görseli base64 formatına dönüştürme fonksiyonu"""
    try:
        # Görseli bir byte buffer'a kaydediyoruz
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        # Base64 formatına dönüştürüyoruz
        encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return encoded_string
    except Exception as e:
        return str(e)

# Konum tespiti için OpenAI API'yi kullanma fonksiyonu
def get_location_from_image_base64(base64_image):
    """Base64 formatındaki görseli OpenAI API'ye gönderme fonksiyonu"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # GPT-4o-mini modelini kullanıyoruz
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Bu görseldeki konumu Türkiye'deki bir şehir veya bölge bazında tespit et."},
                    {"type": "text", "text": base64_image}  # Burada base64 görsel verisi kullanılıyor
                ]
            }]
        )

        # Yanıtı işleyip döndürme
        location_data = json.loads(response.choices[0].message.content)
        return location_data
    except Exception as e:
        return {"error": str(e)}

# Streamlit UI
st.set_page_config(page_title="Konum Tespit", page_icon="🌍")
st.title("Konum Tespit Uygulaması")

# Görsel yükleme alanı
uploaded_file = st.file_uploader("Bir görsel yükleyin", type=["jpg", "jpeg", "png"])
if uploaded_file:
    # Yüklenen görseli açıyoruz
    image = Image.open(uploaded_file)
    st.image(image, caption="Yüklenen Görsel", use_column_width=True)

    # Görseli base64 formatına dönüştürme
    base64_image = image_to_base64(image)
    
    if base64_image:
        # Base64 görsel verisini OpenAI API'ye gönderme
        location_data = get_location_from_image_base64(base64_image)
        
        if location_data.get("location"):
            st.success(f"Konum Tespit Edildi: {location_data['location']}")
        else:
            st.error("Konum tespiti yapılamadı.")
    else:
        st.error("Görseli base64 formatına dönüştürürken bir hata oluştu.")
