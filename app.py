import io

import requests
import streamlit as st
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
            f"""❌ Erreur serveur: code {error.status_code}

            {error.message}""")
    else:
        st.error(
            f"""❌ Erreur client:

            `{error}`""")


# 📁 Dictionnaire des célébrités avec leurs images en ligne
celebrity_image_paths = {
    "AdrianaLima": "https://i.ibb.co/gLNxskvB/Adriana-Lima15-52.jpg",
    "AlexandraDaddario": "https://i.ibb.co/W40dfVv6/Alexandra-Daddario3-366.jpg",
    "AlvaroMorte": "https://i.ibb.co/wNFKbyt1/Alvaro-Morte29-239.jpg",
    "AmandaCrew": "https://i.ibb.co/ZPMbWVT/Amanda-Crew0-0.jpg",
    "AlexLawther": "https://i.ibb.co/xqKrXGF1/Alex-Lawther13-25.jpg"
    # ➕ On peut ajouter d'autres célébrités ici
}


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

            if 'result' in result:
                display_two_columns(image, result['result'])
            else:
                st.error("❌ Réponse API invalide (pas de résultat).")


def display_two_columns(image, celebrity_name):
    st.success(
        f"🎉 Ton jumeau célèbre est : **{celebrity_name}**")

    # 🖼️ Affichage côte à côte
    col1, col2 = st.columns(2)
    with col1:
        st.image(image, caption="📷 Photo initiale", width=300)

    if celebrity_name in celebrity_image_paths:
        image_url = celebrity_image_paths[celebrity_name]
        try:
            celeb_response = requests.get(image_url)
            if celeb_response.status_code == 200:
                celeb_image = Image.open(
                    io.BytesIO(celeb_response.content))
                with col2:
                    st.image(
                        celeb_image, caption=f"🎬 {celebrity_name}", width=300)
            else:
                # (code HTTP)
                st.warning("❌ Image de célébrité introuvable.")
        except Exception as img_error:
            st.error(
                f"⚠️ Erreur image célébrité : {img_error}")
    else:
        st.warning(
            "🤷 Image non trouvée pour ce jumeau célèbre.")


main()
