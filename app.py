import io

import requests
import streamlit as st
from PIL import Image

"https://celebtwin-api-244684580447.europe-west4.run.app/predict-annoy/"
SERVICE_ROOT = "https://celebtwin-api-244684580447.europe-west4.run.app"
API_URL = SERVICE_ROOT + "/predict-annoy/"
# API_URL = "http://127.0.0.1:8000/predict-annoy/"


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
            f"""❌ Erreur serveur: code {error.status_code}

            {error.message}""")
    else:
        st.error(
            f"""❌ Erreur client:

            `{error}`""")


def main():
    """🎬 Interface principale"""

    st.title("👯‍♂️ Trouve ton jumeau célèbre – CelebTwin")
    uploaded_file = st.file_uploader(
        "📷 Upload une photo", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Image chargée", use_container_width=True)
        if st.button("🔍 Qui est mon jumeau célèbre ?"):

            # 🔗 Appel à l'API de prédiction
            try:
                result = predict(uploaded_file)
            except Exception as error:
                render_error(error)
                st.stop()

            if 'class' in result and 'name' in result:
                display_two_columns(image, result)
            else:
                st.error(
                    f"""❌ Réponse API invalide:

                    ```{result}```
                    """)


def display_two_columns(image, result):
    celebrity_name = result['class']
    file_name = result['name']
    st.success(
        f"🎉 Ton jumeau célèbre est : **{celebrity_name}**")

    col1, col2 = st.columns(2)
    with col1:
        st.image(image, caption="📷 Photo initiale", width=300)
    with col2:
        image_root = "https://storage.googleapis.com/celebtwin/public/img/"
        image_dir = celebrity_name.lower().replace(' ', '-').replace('.', '')
        image_url = image_root + image_dir + '/' + file_name
        st.image(image_url, caption=f"🎬 {celebrity_name}", width=300)

main()
