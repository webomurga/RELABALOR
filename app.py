import streamlit as st
import openai
import os
from PIL import Image
import io
import base64
import json

# === API Anahtarı ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Sistem Prompt'ları ===
GEOLOCATION_PROMPT = """Bu görseldeki konumu Türkiye'deki bir şehir veya bölge bazında tespit et. 
Yalnızca şu formatta cevap ver: 
{"location": "konum_adi", "confidence": "yuksek/orta/dusuk"}"""

DIALECT_PROMPT = """Aşağıdaki kullanıcı mesajına, şu konumun yerel diyalektine uygun şekilde yanıt ver: {location}. 
Cevabını kültürel özellikleri, turistik bilgileri ve yerel dil varyasyonlarını içerecek şekilde hazırla. 
Resmi dilbilgisi kuralları kullanma, samimi ve yerel ifadelerle yaz."""

# === Görselden Konum Tahmini ===
def get_location_from_image(image):
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        response = openai.ChatCompletion.create(
            model="meta-llama/llama-4-maverick:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": GEOLOCATION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{base64_image}",
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"location": None, "error": str(e)}

# === Yöresel Yanıt ===
def get_response(prompt, location):
    enhanced_prompt = DIALECT_PROMPT.format(location=location) + "\n\n" + prompt
    response = openai.ChatCompletion.create(
        model="meta-llama/llama-4-maverick:free",
        messages=[
            {"role": "system", "content": "Sen Türkiye'nin yöresel diyalektlerinde konuşan bir rehbersin."},
            {"role": "user", "content": enhanced_prompt}
        ]
    )
    return response.choices[0].message.content

# === Uygulama Başlığı ve Oturum Yönetimi ===
st.set_page_config(page_title="RELABALOR", layout="centered")
st.title("📸 RELABALOR - Yöresel Rehber")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "location" not in st.session_state:
    st.session_state.location = None

# === Görsel Yükleme: İlk Mesaj Gibi Göster ===
if not st.session_state.location:
    with st.chat_message("user"):
        st.markdown("📍 Merhaba! Lütfen bulunduğun yerden bir fotoğraf yükleyerek konumunu paylaş.")

    uploaded_file = st.file_uploader("Görsel yükle", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file:
        image = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image, caption="Yüklenen görsel")
        with st.chat_message("assistant"):
            with st.spinner("Konum tespit ediliyor..."):
                location_data = get_location_from_image(image)
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