from textwrap import dedent

import requests
import streamlit as st


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
    if response.status_code != 200:
        raise HTTPError(response)
    return response.json()


def make_image_url(response):
    image_root = "https://storage.googleapis.com/celebtwin/public/img/"
    image_dir = response["class"].lower().replace(" ", "-").replace(".", "")
    image_url = image_root + image_dir + "/" + response["name"]
    return image_url


def center_html(html):
    st.markdown(f"<p style='text-align: center;'>{html}</p>",
                unsafe_allow_html=True)


def main():
    """🎬 Interface principale"""

    st.markdown(dedent("""
        <h1 style="text-align: center">
        👯‍♂️ Trouve ton jumeau célèbre
        </h1>"""), unsafe_allow_html=True)

    def upload_callback():
        st.session_state.pop("response", None)
        st.session_state.pop("error", None)

    uploaded_file = st.file_uploader(
        "Upload une photo", label_visibility="collapsed",
        type=["jpg", "jpeg", "png"], on_change=upload_callback)
    if uploaded_file is None:
        st.info("Upload une photo pour trouver ton jumeau célèbre", icon="👀")
        st.stop()

    response = st.session_state.get("response", None)
    if "error" in st.session_state:
        if isinstance(st.session_state["error"], HTTPError):
            st.error(f"Erreur: {st.session_state['error']}", icon="❌")
        else:
            st.exception(st.session_state["error"])
    elif response is None:
        st.info("Analyse en cours...", icon="🧠")
    elif response.get("error") == "NoFaceDetectedError":
        st.error("Aucun visage détecté dans la photo", icon="❓")
    elif "error" in response:
        st.error(f"Erreur: {response["message"]}", icon="❌")
    elif "class" in response:
        st.success(f"Ton jumeau célèbre est : **{response["class"]}**",
                   icon="🎉")
    else:
        st.error("Something went wrong", icon="💣")

    col1, col2 = st.columns(2)
    with col1:
        center_html("📷 &nbsp; Ta photo")
        st.image(uploaded_file, use_container_width=True)
    with col2:
        if "error" in st.session_state:
            st.button("Réessayer", on_click=upload_callback)
        elif response is None:
            center_html("Attends, je cherche ton jumeau célèbre...")
            st.markdown(dedent("""
                <div style="text-align: center; padding-top: 3em">
                <img src="app/static/spinner.gif">
                </div>"""), unsafe_allow_html=True)
        elif response["status"] == "ok":
            center_html(f"🎬 &nbsp; {response['class']}")
            image_url = make_image_url(response)
            st.image(image_url, use_container_width=True)

    if response is None and "error" not in st.session_state:
        try:
            response = predict(uploaded_file)
        except Exception as error:
            st.session_state["error"] = error
            response = None
        st.session_state["response"] = response
        st.rerun()


main()
