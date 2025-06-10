
import streamlit as st
import requests
from PIL import Image


API_URL = "https://celebtwin-api-244684580447.europe-west4.run.app/predict/"
# API_URL = "http://127.0.0.1:8000/predict/"


class HTTPError(Exception):
    """Custom exception for HTTP errors."""

    def __init__(self, response):
        super().__init__(f"HTTP Error {response.status_code}: {response.text}")
        self.status_code = response.status_code
        self.message = response.text


def predict(uploaded_file):
    """Send the uploaded file to the API and return the prediction."""
    # Streamlit apparently wants us to reset the file position ourselves.
    uploaded_file.seek(0)
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    response = requests.post(API_URL, files=files)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPError(response)


def render_error(error):
    """Render an error message in the Streamlit app."""
    if isinstance(error, HTTPError):
        st.error(
            f"""Erreur serveur: code {error.status_code}

            {error.message}""")
    else:
        st.error(
            f"""Erreur client:

            `{error}`""")


st.title("👯‍♂️ Trouve ton jumeau célèbre – CelebTwin")

# Upload control for image.
uploaded_file = st.file_uploader(
    "📷 Upload une photo de toi", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image chargée", use_container_width=True)

    # Button that initiates the prediction.
    if st.button("🔍 Qui est mon jumeau célèbre ?"):
        try:
            result = predict(uploaded_file)
            st.success(f"🎉 Ton jumeau célèbre est : **{result['result']}**")
        except Exception as error:
            render_error(error)
