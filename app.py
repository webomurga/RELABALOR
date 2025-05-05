import streamlit as st
import openai
import os
from geopy.geocoders import Nominatim

# OpenAI API configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="RELABALOR_APP")

# Custom HTML + JavaScript component for GPS retrieval
def get_gps_coordinates():
    # HTML/JS code to get geolocation
    gps_code = """
    <script>
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
                // Sending back the data to Streamlit
                window.parent.postMessage({type: 'success', data: coords}, '*');
            } catch (error) {
                window.parent.postMessage({type: 'error', data: error}, '*');
            }
        }

        main();  // Call the main function to get the location
    </script>
    """

    # Embed the HTML/JS code into Streamlit app
    st.components.v1.html(gps_code, height=0)

# Streamlit UI
st.set_page_config(page_title="RELABALOR", page_icon="🌍")
st.title("Yöresel Rehber 🌍")
st.markdown("Konumunu algıla, yöresel bilgileri keşfet!")

# Konum belirleme
st.subheader("Konumunuzu Belirleyin")

# GPS verilerini almak için buton
if st.button("📡 Konumumu Al"):
    get_gps_coordinates()

# Burada kullanıcının konumunu işlemek için gerekli işlemleri yapabiliriz
if 'location' in st.session_state:
    st.subheader(f"🏙️ {st.session_state['location']} Özel Tavsiyeler")

    # Konumla ilgili öneri oluşturma
    suggestion = "Bu konum için 3 maddelik kısa turistik öneri listesi oluştur"
    suggestions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Sen Türkiye'nin yerel şivelerini kullanan bir kültür rehberisin."},
                  {"role": "user", "content": f"{st.session_state['location']}: {suggestion}"}]
    )

    for line in suggestions.choices[0].message.content.split('\n'):
        if line.strip():
            with st.expander(line.strip()):
                details = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "Sen Türkiye'nin yerel şivelerini kullanan bir kültür rehberisin."},
                              {"role": "user", "content": f"{line.strip()} hakkında detaylı bilgi ver"}]
                )
                st.write(details.choices[0].message.content)

# Handle GPS success or error
st.components.v1.html("""
<script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'success') {
            const coords = event.data.data;
            window.parent.postMessage({type: 'location', data: coords}, '*');
        } else if (event.data.type === 'error') {
            window.parent.postMessage({type: 'location_error', data: event.data.data}, '*');
        }
    });
</script>
""", height=0)

# Implement logic for handling GPS response in Python
if 'location' in st.session_state:
    location = st.session_state.location
    st.write(f"Konumunuz: {location}")
