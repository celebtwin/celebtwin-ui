import threading
from textwrap import dedent

import requests
import streamlit as st
from PIL import ExifTags, Image, ImageOps
from streamlit.runtime.uploaded_file_manager import UploadedFile

SERVICE_ROOT = "https://celebtwin-api-244684580447.europe-west4.run.app"
PING_URL = SERVICE_ROOT + "/"
API_URL = SERVICE_ROOT + "/predict-annoy/"
# API_URL = "http://127.0.0.1:8000/predict-annoy/"


class HTTPError(Exception):
    """Custom exception for HTTP errors."""

    def __init__(self, response):
        super().__init__(f"HTTP Error {response.status_code}: {response.text}")
        self.status_code = response.status_code
        self.message = response.text


def predict(model: str, uploaded_file: UploadedFile) -> dict | Exception:
    """Send the uploaded file to the API and return the prediction."""
    # Streamlit apparently wants us to reset the file position ourselves.
    uploaded_file.seek(0)
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    try:
        response = requests.post(API_URL + model, files=files)
    except Exception as error:
        return error
    if response.status_code != 200:
        return HTTPError(response)
    return response.json()


class PingThread(threading.Thread):

    def __init__(self) -> None:
        super().__init__()
        self.result: dict | Exception | None = None

    def run(self) -> None:
        try:
            response = requests.get(PING_URL)
            if response.status_code == 200:
                self.result = response.json()
            else:
                self.result = HTTPError(response)
        except Exception as error:
            self.result = error


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

    if uploaded_file is not None:
        if uploaded_file.type == "image/jpeg":
            image = Image.open(uploaded_file)
            orientation_key = next(
                k for k, v in ExifTags.TAGS.items() if v == 'Orientation')
            orientation = image.getexif().get(orientation_key, 1)
            if orientation > 1:
                # Apply EXIF orientation automatically
                image = ImageOps.exif_transpose(image)
                # Replace uploaded_file value by jpeg compressed image
                uploaded_file.seek(0)
                image.save(uploaded_file, "jpeg")

    ping_thread = st.session_state.get("ping_thread", None)
    ping_response = st.session_state.get("ping_response", None)
    response = st.session_state.get("response", None)
    error = st.session_state.get("error", None)

    if ping_thread is None:
        ping_thread = PingThread()
        ping_thread.start()
        st.session_state["ping_thread"] = ping_thread
        # Wait for a little bit, so the startup message does not blink if the
        # service is already started.
        ping_thread.join(0.1)

    if uploaded_file is None:
        st.info("Upload une photo pour trouver ton jumeau célèbre", icon="👀")
    if error:
        st.error(f"Erreur: {error}", icon="❌")
        # st.exception(st.session_state["error"])
    if ping_thread.is_alive():
        st.info("Démarrage du service...", icon="🚀")
    elif uploaded_file is None:
        pass
    elif response is None:
        st.info("Analyse en cours...", icon="🧠")
    elif "class" in response:
        st.success(f"Ton jumeau célèbre est : **{response["class"]}**",
                   icon="🎉")
    elif response.get("error") == "NoFaceDetectedError":
        st.error("Aucun visage détecté dans la photo", icon="❓")
    elif "error" in response:
        st.error(f"Erreur: {response["message"]}", icon="❌")
    else:
        st.error("Something went wrong", icon="💣")

    model_choices = {"facenet": "v1 – Facenet", "vggface": "v2 – VGG-Face"}
    model = st.pills(
        label="Model", options=list(model_choices.keys()), default="vggface",
        format_func=lambda x: model_choices[x], on_change=upload_callback)

    if uploaded_file:
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

    if ping_response is None:
        ping_thread.join()
        if isinstance(ping_thread.result, Exception):
            st.session_state["error"] = ping_thread.result
        st.session_state["ping_response"] = ping_thread.result
        st.rerun()

    if uploaded_file and response is None and error is None:
        response = predict(model, uploaded_file)
        if isinstance(response, Exception):
            st.session_state["error"] = response
            response = None
        st.session_state["response"] = response
        st.rerun()


main()
