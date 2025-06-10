import streamlit as st
import openai
from PIL import Image
from dotenv import load_dotenv
import exifread
import os
import tempfile
from geopy.geocoders import Nominatim
from io import BytesIO
from picarta import Picarta
import json

load_dotenv()

PICARTA_API_TOKEN = os.getenv("PICARTA_API_TOKEN")
picarta_localizer = Picarta(PICARTA_API_TOKEN)

openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="RELABALOR")

st.set_page_config(page_title="RELABALOR - Neresi Burası?", page_icon="📸")
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        display: flex !important;
        white-space: normal;
        word-wrap: break-word;
    }
    </style>
""", unsafe_allow_html=True)

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

if "dialect_text" not in st.session_state:
    st.session_state.dialect_text = ""

with open("dialects.json", "r", encoding="utf-8") as f:
    dialects = json.load(f)

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

def get_location_from_picarta(image_file):
    try:
        image = Image.open(image_file)
        image = image.convert("RGB")
        with tempfile.NamedTemporaryFile(suffix=".jpg", mode='wb', delete=False) as tmp:
            image.save(tmp, format='JPEG')
            tmp.flush()
            result = picarta_localizer.localize(img_path=tmp.name)
        if result:
            city = result.get("city", "Bilinmeyen")
            province = result.get("province", "Bilinmeyen")
            country = result.get("ai_country", "Bilinmeyen")
            lat = result.get("ai_lat")
            lon = result.get("ai_lon")
            if lat and lon:
                location_text = f"{city}, {province}, {country}"
                return {
                    "latlon": f"{lat:.6f}, {lon:.6f}",
                    "location_text": location_text,
                    "confidence": result.get("confidence", 0),
                    "full_result": result
                }
        return None
    except Exception as e:
        print(f"Picarta hatası: {e}")
        return None

def get_dialect_text_for_location(location_text, dialects):
    location_parts = location_text.lower().split(",")
    location_parts = [part.strip() for part in location_parts if part.strip()]
    
    for part in location_parts:
        for region, text in dialects.items():
            if region.lower() in part:
                return text.strip()
    
    for region, text in dialects.items():
        if region.lower() in location_text.lower():
            return text.strip()
    
    return ""

def ask_gpt(prompt, messages=None, dialect_text=None):
    system_msg = (
        "Sen Türkiye'nin bölgelerini çok iyi tanıyan, yerel kültüre hakim, samimi bir asistansın.\n\n"
        "Aşağıda sana sadece konuşma tarzını örnek alman için yerel bir ağızdan yazılmış metin verilecek. "
        "Bu metindeki **olaylar, kişiler, yerler** tamamen kurgusaldır, onları asla cevabına dahil etme. "
        "Sadece metnin **dil üslubunu** (kelime seçimi, cümle yapısı, samimiyet seviyesi gibi) al ve cevabını bu şekilde yaz.\n\n"
    )
    if dialect_text:
        sample = (dialect_text[:500] + "...") if len(dialect_text) > 500 else dialect_text
        system_msg += f"Örnek şive metni:\n\n{sample}\n\n---\n\n"
    else:
        system_msg += "Şive örneği bulunamadı."

    base = [{"role": "system", "content": system_msg}]
    if messages:
        base += messages
    base.append({"role": "user", "content": prompt})

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=base,
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def initialize_chat(location_text, dialect_text):
    intro = ask_gpt(f"{location_text} hakkında kısa, sıcak ve etkileyici bir tanıtım yap.", dialect_text=dialect_text)
    st.session_state.chat.append(("assistant", f"🗺️ **İşte burası hakkında biraz bilgi:**\n\n{intro}"))
    questions_text = ask_gpt(
        "Kullanıcının bu bölge hakkında, bir rehbere sorabileceği 3 bilgi odaklı ve kültürel soru üret. "
        "Sorular yerel gelenekler, tarihi, doğası, meşhur yemekleri gibi konularda olsun. "
        "Senli benli dil kullanma. Sadece madde işaretiyle listele.",
        dialect_text=dialect_text
    )
    st.session_state.questions = [q.strip("-• ") for q in questions_text.split("\n") if q.strip()]

uploaded_file = st.file_uploader("Bir fotoğraf yükle 👇", type=["jpg", "jpeg"])

if uploaded_file and not st.session_state.initialized:
    st.image(uploaded_file, caption="📸 Yüklediğin fotoğraf", use_container_width=True)
    latlon = get_location_from_exif(uploaded_file)
    if not latlon:
        with st.spinner("EXIF verisi bulunamadı, görsel içeriğe göre konum tahmini yapılıyor... 📍"):
            result = get_location_from_picarta(uploaded_file)
            latlon = result["latlon"] if result else None
            if result:
                location_text = result["location_text"]
            else:
                location_text = None
    else:
        location_text = get_location_details(latlon)
    if latlon and location_text:
        st.session_state.location_context = location_text
        dialect_text = get_dialect_text_for_location(location_text, dialects)
        st.session_state.dialect_text = dialect_text
        with st.spinner("Fotoğrafa göre yer tespiti yapılıyor ve tanıtım hazırlanıyor... ⏳"):
            initialize_chat(location_text, dialect_text)
        st.session_state.initialized = True
    else:
        st.warning("📍 Fotoğraftan konum bilgisi alınamadı. Aşağıya tahmini yer adını gir lütfen:")
        st.session_state.manual_location = st.text_input("Yer adı (örnek: Safranbolu, Karabük)", key="manual_location_input")
        if st.session_state.manual_location:
            st.session_state.location_context = st.session_state.manual_location
            dialect_text = get_dialect_text_for_location(st.session_state.manual_location, dialects)
            st.session_state.dialect_text = dialect_text
            with st.spinner("Girdiğin konuma göre bilgi hazırlanıyor... ⏳"):
                initialize_chat(st.session_state.manual_location, dialect_text)
            st.session_state.initialized = True
            st.rerun()

for role, msg in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(msg)

if "selected_question" not in st.session_state:
    st.session_state.selected_question = None

if st.session_state.selected_question is None:
    for idx, q in enumerate(st.session_state.questions):
        if st.button(q, key=f"soru_{idx}"):
            st.session_state.selected_question = q
            st.session_state.chat.append(("user", q))
            response = ask_gpt(q, messages=[{"role": role, "content": msg} for role, msg in st.session_state.chat], dialect_text=st.session_state.dialect_text)
            st.session_state.chat.append(("assistant", response))
            follow_up = ask_gpt(
                "Yukarıdaki cevaba göre, bir rehbere yöneltilmiş gibi olabilecek 3 yeni kültürel ya da yerel bilgi odaklı soru yaz. "
                "Samimi ya da resmi olmasına gerek yok, ama rehbere sorulabilir türden olsun. "
                "Sadece madde işaretiyle listele.",
                messages=[{"role": role, "content": msg} for role, msg in st.session_state.chat],
                dialect_text=st.session_state.dialect_text
            )
            st.session_state.questions = [q.strip("-• ") for q in follow_up.split("\n") if q.strip()]
            st.session_state.selected_question = None
            st.rerun()