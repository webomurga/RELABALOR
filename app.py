import streamlit as st
import openai
import os
import requests
from geopy.geocoders import Nominatim
from PIL import Image
import io
import json
from streamlit_js_eval import st_js

# OpenAI API konfigürasyonu
openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="RELABALOR_APP")

# Sistem prompt'ları
GEOLOCATION_PROMPT = """Bu görseldeki konumu Türkiye'deki bir şehir veya bölge bazında tespit et. 
Yanıtı yalnızca şu formatta ver: {"location": "konum_adi", "confidence": "yuksek/orta/dusuk"}"""

DIALECT_PROMPT = """Aşağıdaki kullanıcı sorusuna, {location} yöresinin şivesi ve kültürel özelliklerini kullanarak cevap ver:
- Günlük konuşma dilini kullan
- Yöresel kelimeler ve deyimler ekle
- Turistik bilgileri vurgula
- Resmi dil kullanma

Soru: {question}"""

# Yardımcı fonksiyonlar
def get_location_from_image(image):
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": GEOLOCATION_PROMPT},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{image.tobytes().hex()}"}
                    ]
                }
            ],
            max_tokens=300
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        return {"error": str(e)}

def reverse_geocode(lat, lon):
    try:
        location = geolocator.reverse(f"{lat}, {lon}", language="tr")
        return location.raw.get('address', {}).get('city', 'Bilinmeyen Konum')
    except:
        return "Bilinmeyen Konum"

def get_gps_coordinates():
    js_code = """
    async function getLocation() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                position => resolve([position.coords.latitude, position.coords.longitude]),
                error => reject(error.message)
            );
        });
    }

    async function main() {
        try {
            const coords = await getLocation();
            return {type: 'success', data: coords};
        } catch (error) {
            return {type: 'error', data: error};
        }
    }

    return main();
    """

    result = streamlit_js_eval(js_expressions=js_code, key="get_gps", debounce=0)
    return result

def generate_response(location, question):
    try:
        prompt = DIALECT_PROMPT.format(location=location, question=question)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen Türkiye'nin yerel şivelerini kullanan bir kültür rehberisin."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Hata oluştu: {str(e)}"

# Streamlit UI
st.set_page_config(page_title="RELABALOR", page_icon="🌍")
st.title("Yöresel Rehber 🌍")
st.markdown("Konumunu algıla, yöresel bilgileri keşfet!")

# Oturum durumu yönetimi
if "messages" not in st.session_state:
    st.session_state.messages = []
if "location" not in st.session_state:
    st.session_state.location = None

# Konum belirleme bölümü
with st.expander("📍 Konumumu Belirle", expanded=True):
    col1, col2 = st.columns([2, 3])
    
    with col1:
        uploaded_file = st.file_uploader("Görsel yükle", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption='Yüklenen Görsel', use_column_width=True)
            location_data = get_location_from_image(image)
            if location_data.get("location"):
                st.session_state.location = location_data["location"]
                st.success(f"Konum tespit edildi: {st.session_state.location}")
    
    with col2:
        st.markdown("**Veya**")
        if st.button("📡 GPS ile Konumumu Algıla"):
            result = get_gps_coordinates()
            if result and result.get('type') == 'success':
                lat, lon = result['data']
                location_name = reverse_geocode(lat, lon)
                st.session_state.location = location_name
                st.success(f"Konumunuz: {location_name}")
            else:
                st.error("Konum alınamadı. Lütfen izinleri kontrol edin.")

# Sohbet arayüzü
st.divider()
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Yöresel rehberinize soru sorun..."):
    if not st.session_state.location:
        st.error("Lütfen önce konumunuzu belirleyin!")
        st.stop()
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="🌍"):
        response = generate_response(st.session_state.location, prompt)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# Yöresel öneriler
if st.session_state.location:
    st.divider()
    st.subheader(f"🏙️ {st.session_state.location} Özel Tavsiyeler")
    
    suggestions = generate_response(
        st.session_state.location,
        "Bu konum için 3 maddelik kısa turistik öneri listesi oluştur"
    )
    
    for line in suggestions.split('\n'):
        if line.strip():
            with st.expander(line.split('.')[-1].strip()):
                details = generate_response(
                    st.session_state.location,
                    f"'{line}' hakkında detaylı bilgi ver"
                )
                st.write(details)