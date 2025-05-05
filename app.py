import streamlit as st
import openai
from PIL import Image
import exifread
import os
from geopy.geocoders import Nominatim
from io import BytesIO

openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="replabalor_app")

def get_location_from_exif(uploaded_file):
    try:
        img_bytes = uploaded_file.getvalue()
        tags = exifread.process_file(BytesIO(img_bytes))
        
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef', 'N')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef', 'E')

        if all([gps_latitude, gps_longitude]):
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
        st.error(f"Hmm... Konum bilgisini çıkaramadık 😕 ({str(e)})")
        return None

def get_location_details(latlon):
    try:
        location = geolocator.reverse(latlon, exactly_one=True)
        address = location.raw.get('address', {})
        
        city = address.get('city') or address.get('town') or address.get('village') or address.get('county') or 'Bilinmeyen'
        state = address.get('state') or 'Bilinmeyen'
        
        return {
            'city': city,
            'state': state
        }
    except Exception as e:
        st.error(f"Yer bilgisi alınamadı 😓 ({str(e)})")
        return {}


def generate_gpt_response(prompt, context=[]):
    messages = [
        {"role": "system", "content": "Sen Türkiye'nin bölgesel dil ve kültür uzmanı, samimi bir asistansın."},
        *context,
        {"role": "user", "content": prompt}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message['content']

st.title("📸 RELABALOR - Burası Neresi?")
st.subheader("Fotoğrafını yükle, neredesin söyleyelim! Üstüne bir de sana özel sorularla muhabbet edelim 😎")

st.set_page_config(
    page_title="RELABALOR - Neresi Burası?",
    page_icon="📸"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

uploaded_file = st.file_uploader("Hadi bi fotoğraf at bakalım 👇", type=["jpg", "jpeg", "png"])

if uploaded_file:
    latlon = get_location_from_exif(uploaded_file)
    if latlon:
        location_details = get_location_details(latlon)
        context = f"{location_details.get('city', 'Bilinmeyen')} - {location_details.get('state', 'Bilinmeyen')}"
        
        initial_questions = generate_gpt_response(
            f"{context} konumuna özel 3 tane kültürel ya da turistik soru üret. Madde madde olsun lütfen."
        )

        image_bytes = uploaded_file.getvalue()
        image_md = f"![Yüklediğin fotoğraf](data:image/jpeg;base64,{image_bytes.hex()})"
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📍 Şöyle bir yerde çekilmişsin: **{context}**\n\nBunlar da sana özel sorular 🎯:\n\n{initial_questions}"
        })
    else:
        st.error("Hmm... Bu fotoğrafta konum bilgisi yok gibi 🤷‍♀️")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ne merak ettin? Ya da yukarıdaki sorulardan birine dalalım mı? 🧐"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    response = generate_gpt_response(
        prompt,
        context=st.session_state.messages
    )
    
    follow_up = generate_gpt_response(
        "Bu cevap için 2 tane kısa takip sorusu üret. Sadece soruları madde işaretleriyle ver."
    )
    
    full_response = f"{response}\n\n💡 **Devam Soruları:**\n{follow_up}"
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()