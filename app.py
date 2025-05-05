import openai, os
import streamlit as st
from PIL import Image
import base64
from io import BytesIO

# OpenAI API anahtarınızı buraya ekleyin
openai.api_key = os.getenv("OPENAI_API_KEY")

# Streamlit arayüzü
st.title("ChatGPT ile Yazışma & Fotoğraf Yükleme")

# Kullanıcıdan bir metin girmesini istemek
user_input = st.text_input("Sorunuzu buraya yazın:")

# Fotoğraf yükleme
uploaded_file = st.file_uploader("Bir fotoğraf yükleyin", type=["png", "jpg", "jpeg"])

# Base64 formatında fotoğrafı almak için yardımcı fonksiyon
def get_image_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Fotoğraf yüklendiğinde base64 formatında gösterme
if uploaded_file is not None:
    img = Image.open(uploaded_file)
    img_base64 = get_image_base64(img)
    st.image(img, caption="Yüklenen Fotoğraf", use_column_width=True)
    st.text("Fotoğrafın Base64 Kodlaması:")
    st.code(img_base64)

# Kullanıcı metni girdiyse, OpenAI API ile yanıt alma
if user_input:
    # GPT-4o-mini modelini kullanarak API'den yanıt almak
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Burada gpt-4o-mini kullanılacak
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input},
        ],
        max_tokens=150
    )
    
    # Yanıtı gösterme
    st.subheader("ChatGPT'nin Yanıtı:")
    st.write(response['choices'][0]['message']['content'].strip())