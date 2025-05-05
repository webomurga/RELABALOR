import streamlit as st
import openai
from PIL import Image
import exifread
import os
from geopy.geocoders import Nominatim
from io import BytesIO

openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="RELABALOR")

st.set_page_config(page_title="RELABALOR - Neresi Burası?", page_icon="📸")

st.title("📸 RELABALOR - Burası Neresi?")
st.subheader("Bir fotoğraf yükle, neresi olduğunu ve neler olduğunu birlikte keşfedelim!")

if "chat" not in st.session_state:
    st.session_state.chat = []

if "questions" not in st.session_state:
    st.session_state.questions = []

if "location_context" not in st.session_state:
    st.session_state.location_context = ""

if "initialized" not in st.session_state:
    st.session_state.initialized = False

def get_location_from_exif(uploaded_file):
    try:
        img_bytes = uploaded_file.getvalue()
        tags = exifread.process_file(BytesIO(img_bytes))
        
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef', 'N')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef', 'E')

        if gps_latitude and gps_longitude:
            def dms_to_decimal(dms, ref):
                degrees = dms.values[0].num / dms.values[0].den
                minutes = dms.values[1].num / dms.values[1].den
                seconds = dms.values[2].num / dms.values[2].den
                decimal = degrees + minutes / 60 + seconds / 3600
                return decimal if ref in ['N', 'E'] else -decimal

            lat = dms_to_decimal(gps_latitude, str(gps_latitude_ref))
            lon = dms_to_decimal(gps_longitude, str(gps_longitude_ref))
            return f"{lat:.6f}, {lon:.6f}"
        return None
    except Exception:
        return None

def get_location_details(latlon):
    try:
        location = geolocator.reverse(latlon, exactly_one=True)
        address = location.raw.get('address', {})
        city = address.get('city') or address.get('town') or address.get('village') or address.get('county') or 'Bilinmeyen'
        state = address.get('state') or 'Bilinmeyen'
        return f"{city}, {state}"
    except Exception:
        return "Bilinmeyen"

def ask_gpt(prompt, messages=None):
    base = [{"role": "system", "content": "Sen Türkiye'nin bölgelerini çok iyi tanıyan, yerel kültüre hakim, samimi bir asistansın."}]
    if messages:
        base += messages
    base.append({"role": "user", "content": prompt})
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=base,
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def initialize_chat(location_text):
    intro = ask_gpt(f"{location_text} hakkında kısa, sıcak ve etkileyici bir tanıtım yap.")
    st.session_state.chat.append((
        "assistant", 
        f"🗺️ **İşte burası hakkında biraz bilgi:**\n\n{intro}"
    ))

    questions_text = ask_gpt("Bu konum hakkında kullanıcıyı merak ettirecek 3 soru yaz. Samimi, senli benli ol. Sadece madde işaretiyle listele.")
    st.session_state.questions = [q.strip("-• ") for q in questions_text.split("\n") if q.strip()]

uploaded_file = st.file_uploader("Bir fotoğraf yükle 👇", type=["jpg", "jpeg"])

if uploaded_file and not st.session_state.initialized:
    st.image(uploaded_file, caption="📸 Yüklediğin fotoğraf", use_container_width=True)

    latlon = get_location_from_exif(uploaded_file)
    if latlon:
        location_text = get_location_details(latlon)
        st.session_state.location_context = location_text

        with st.spinner("Fotoğrafa göre yer tespiti yapılıyor ve tanıtım hazırlanıyor... ⏳"):
            initialize_chat(location_text)

        st.session_state.initialized = True
    else:
        st.error("❌ Fotoğrafta konum bilgisi bulunamadı. Başka bir fotoğraf dene istersen.")

for role, msg in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(msg)

if "selected_question" not in st.session_state:
    st.session_state.selected_question = None

if st.session_state.selected_question is None:
    #st.markdown("### Sorularını beklerim 👇")
    for idx, q in enumerate(st.session_state.questions):
        if st.button(q, key=f"soru_{idx}"):
            st.session_state.selected_question = q
            st.session_state.chat.append(("user", q))

            response = ask_gpt(q, messages=[{"role": role, "content": msg} for role, msg in st.session_state.chat])
            st.session_state.chat.append(("assistant", response))

            follow_up = ask_gpt(
                "Bu cevaba göre kullanıcıya sorulabilecek 3 kısa, senli-benli, merak uyandıran soru yaz. Sadece madde işaretiyle listele.",
                messages=[{"role": role, "content": msg} for role, msg in st.session_state.chat]
            )
            st.session_state.questions = [q.strip("-• ") for q in follow_up.split("\n") if q.strip()]
            st.session_state.selected_question = None  # yeni sorulara geçince sıfırla
            st.rerun()