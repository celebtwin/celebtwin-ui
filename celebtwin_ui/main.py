import threading
from textwrap import dedent
from typing import Any, cast

import requests
import streamlit as st
from PIL import ExifTags, Image, ImageOps
from streamlit.runtime.uploaded_file_manager import UploadedFile

SERVICE_ROOT = "https://celebtwin-api-244684580447.europe-west4.run.app"
# SERVICE_ROOT = "http://127.0.0.1:8000"
PING_URL = SERVICE_ROOT + "/"
API_URL = SERVICE_ROOT + "/predict-annoy/"


class HTTPError(Exception):
    """Custom exception for HTTP errors."""

    def __init__(self, response):
        super().__init__(f"HTTP Error {response.status_code}: {response.text}")
        self.status_code = response.status_code
        self.message = response.text


def predict(status: Any, model: str, uploaded_file: UploadedFile) \
        -> tuple[dict | None, Exception | str | None]:
    """Send the uploaded file to the API and return the prediction."""
    # Streamlit apparently wants us to reset the file position ourselves.
    uploaded_file.seek(0)
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    try:
        response = requests.post(API_URL + model, files=files)
    except Exception as error:
        return report_error(status, error)
    if response.status_code != 200:
        return report_error(status, HTTPError(response))
    st.session_state["response"] = response.json()
    return response.json(), None


response_and_error = tuple[dict, None] | tuple[None, Exception | str]

class PingThread(threading.Thread):

    def __init__(self):
        super().__init__()
        self.result, self.error = None, None
        st.session_state["ping_thread"] = self

    def run(self) -> None:
        try:
            response = requests.get(PING_URL)
        except Exception as error:
            self.error = error
            return
        if response.status_code != 200:
            self.error = HTTPError(response)
            return
        self.result = response.json()

    def get_result(self, status: Any) -> response_and_error:
        self.join()
        if self.error:
            return report_error(status, self.error)
        st.session_state["ping_response"] = self.result
        return self.result, None


def report_error(status: Any, error: Exception | str, icon: str = "❌") \
        -> tuple[None, Exception | str]:
    st.session_state["error"] = error
    status.error(f"Erreur: {error}", icon=icon)
    return None, error


def make_image_url(response):
    image_root = "https://storage.googleapis.com/celebtwin/public/img/"
    image_dir = response["class"].lower().replace(" ", "-").replace(".", "")
    image_url = image_root + image_dir + "/" + response["name"]
    return image_url


def center_html(html):
    st.markdown(f"<p style='text-align: center;'>{html}</p>",
                unsafe_allow_html=True)


def main() -> None:
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

    status = st.empty()
    ping_thread = st.session_state.get("ping_thread", None)
    ping_response = st.session_state.get("ping_response", None)
    response = st.session_state.get("response", None)
    error = st.session_state.get("error", None)

    if error:
        status.error(error)

    model_choices = {"facenet": "v1 – Facenet", "vggface": "v2 – VGG-Face"}
    model = st.pills(
        label="Modèle", options=list(model_choices.keys()), default="vggface",
        format_func=lambda x: model_choices[x], on_change=upload_callback,
        label_visibility="collapsed")
    assert model in model_choices

    if ping_thread is None:
        ping_thread = PingThread()
        ping_thread.start()

    if ping_response is None and error is None:
        status.info("Démarrage du service...", icon="🚀")

    if uploaded_file and uploaded_file.type == "image/jpeg":
        image = Image.open(uploaded_file)
        orientation_key = next(
            k for k, v in ExifTags.TAGS.items() if v == 'Orientation')
        orientation = image.getexif().get(orientation_key, 1)
        if orientation > 1:
            # Apply EXIF orientation automatically
            print("Applying EXIF orientation")
            ImageOps.exif_transpose(image, in_place=True)
            # Replace uploaded_file value by jpeg compressed image
            uploaded_file.seek(0)
            image.save(uploaded_file, "jpeg")

    if uploaded_file:
        col1, col2 = st.columns(2)
        with col1:
            center_html("📷 &nbsp; Ta photo")
            st.image(uploaded_file, use_container_width=True)
        with col2:
            right_column = st.empty()

    if ping_response is None and error is None:
        ping_response, error = ping_thread.get_result(status)

    if not uploaded_file:
        status.info(
            "Upload une photo pour trouver ton jumeau célèbre", icon="👀")
        return

    if response is None and error is None:
        status.info("Analyse en cours...", icon="🧠")
        with right_column.container():
            center_html("Attends, je cherche ton jumeau célèbre...")
            st.markdown(dedent("""
                <div style="text-align: center; padding-top: 3em">
                <img src="app/static/spinner.gif">
                </div>"""), unsafe_allow_html=True)
        response, error = predict(status, model, uploaded_file)

    if error:
        right_column.button("Réessayer", on_click=upload_callback)
        return

    if response["status"] == "ok":
        status.success(f"Ton jumeau célèbre est : **{response['class']}**",
                       icon="🎉")
        with right_column.container():
            center_html(f"🎬 &nbsp; {response['class']}")
            image_url = make_image_url(response)
            st.image(image_url, use_container_width=True)
        return

    if response["status"] == "error":
        right_column.empty()
        if response["error"] == "NoFaceDetectedError":
            report_error(
                status, "Aucun visage détecté dans la photo", icon="❓")
        else:
            report_error(status, response["error"])
        return

    status.error("Une erreur est survenue", icon="💣")
