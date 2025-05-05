import streamlit as st
import openai
import os
from geopy.geocoders import Nominatim
from PIL import Image
import io
import json
from streamlit.components.v1 import html

# OpenAI API configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="RELABALOR_APP")

# Function to get GPS coordinates using custom HTML + JS
def get_gps_coordinates():
    # Custom HTML/JS component for GPS
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
                // Send back the data to Streamlit using window.parent.postMessage
                window.parent.postMessage({type: 'success', data: coords}, '*');
            } catch (error) {
                window.parent.postMessage({type: 'error', data: error}, '*');
            }
        }

        main();  // Call the main function to get the location
    </script>
    """

    # Embed the HTML/JS code inside the Streamlit app
    html(gps_code, height=0)

    # This will allow Streamlit to capture the response from JS
    result = st.experimental_get_query_params()
    return result

# Streamlit UI
st.set_page_config(page_title="RELABALOR", page_icon="🌍")
st.title("Yöresel Rehber 🌍")
st.markdown("Konumunu algıla, yöresel bilgileri keşfet!")

# Get GPS coordinates and display them
if st.button("📡 GPS ile Konumumu Algıla"):
    gps_coords = get_gps_coordinates()
    if gps_coords:
        st.success(f"Konumunuz: {gps_coords}")
    else:
        st.error("Konum alınamadı. Lütfen izinleri kontrol edin.")
