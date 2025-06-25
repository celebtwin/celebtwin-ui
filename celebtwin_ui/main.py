import functools
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import TYPE_CHECKING, NamedTuple

import requests
import streamlit as st
from PIL import Image, ImageOps

if TYPE_CHECKING:
    from tempfile import _TemporaryFileWrapper
    from typing import Any, Callable, Self

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.runtime.uploaded_file_manager import UploadedFile


SERVICE_ROOT = "https://celebtwin-api-244684580447.europe-west4.run.app"
# SERVICE_ROOT = "http://127.0.0.1:8000"
PING_URL = SERVICE_ROOT + "/"
API_URL = SERVICE_ROOT + "/predict-annoy/"


class HTTPError(Exception):
    """Custom exception for HTTP errors."""

    def __init__(self, response: requests.Response) -> None:
        super().__init__(f"HTTP Error {response.status_code}: {response.text}")
        self.status_code: int = response.status_code
        self.message: str = response.text


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, response: dict[str, str]) -> None:
        assert response['status'] == 'error'
        super().__init__(f"{response['error']}: {response['message']}")
        self.error = response['error']
        self.message = response['message']


class Result[Value, Error](NamedTuple):
    value: Value
    error: Error


type ErrorResult = \
    Result[None, Exception] | Result[None, HTTPError] | Result[None, APIError]
type ValueResult[T] = Result[T, None]
type ValueOrError[T] = ValueResult[T] | ErrorResult


def session_state(key: str):
    """Decorator to store the result of a function in the session state."""
    def inner(func):
        def wrapper(*args, **kwargs):
            if key in st.session_state:
                return st.session_state[key]
            st.session_state[key] = result = func(*args, **kwargs)
            return result

        def clear():
            state = st.session_state.pop(key, None)
            if hasattr(state, "close"):
                state.close()
        wrapper.clear = clear

        def done():
            return key in st.session_state
        wrapper.done = done
        return functools.update_wrapper(wrapper, func)
    return inner


class Status:

    def __init__(self) -> None:
        self._status = st.empty()
        command = st.session_state.get("status", lambda x: None)
        command(self._status)

    def _delegate(self, command: "Callable[[DeltaGenerator], Any]") -> None:
        st.session_state["status"] = command
        command(self._status)

    def info(self, message: str, icon: str | None = None) -> None:
        self._delegate(lambda x: x.info(message, icon=icon))

    def success(self, message: str, icon: str | None = None) -> None:
        self._delegate(lambda x: x.success(message, icon=icon))

    def error(self, message: str, icon: str | None = None) -> None:
        self._delegate(lambda x: x.error(message, icon=icon))

    def exception(self, error: Exception) -> None:
        self._delegate(lambda x: x.exception(error))


def report_error(
        status: Status, error: Exception | str, icon: str = "❌") -> None:
    if isinstance(error, (HTTPError, APIError)):
        status.error(str(error), icon=icon)
    if isinstance(error, Exception):
        status.exception(error)
    else:
        status.error(error, icon=icon)


class PingThread(threading.Thread):

    def __init__(self) -> None:
        super().__init__()
        self._result: dict | None = None
        self._error: Exception | None = None

    @classmethod
    @session_state("ping_thread")
    def get(cls) -> "Self":
        thread = cls()
        thread.start()
        return thread

    def run(self) -> None:
        try:
            response = requests.get(PING_URL)
        except Exception as error:
            self._error = error
            return
        if response.status_code != 200:
            self._error = HTTPError(response)
            return
        self._result = response.json()

    @session_state("ping_result")
    def get_result(self) -> ValueOrError[dict]:
        self.join()
        if self._error:
            return Result(None, self._error)
        assert self._result
        return Result(self._result, None)


class UploadedImage:

    def __init__(self, uploaded_file: "UploadedFile") -> None:
        self.uploaded_file = uploaded_file
        self.suffix = Path(uploaded_file.name).suffix.lower()
        assert self.suffix in [".jpg", ".jpeg", ".png"]
        assert uploaded_file.type in ["image/jpeg", "image/png"]
        self.file_type = uploaded_file.type.split("/")[1]
        self._thumbnail_file: '_TemporaryFileWrapper[bytes]' | None = None

    def close(self) -> None:
        if self._thumbnail_file:
            self._thumbnail_file.close()

    @classmethod
    @session_state("uploaded_image")
    def get(cls, uploaded_file: "UploadedFile") -> "UploadedImage":
        return cls(uploaded_file)

    def fullres_image(self) -> Image.Image:
        image = Image.open(self.uploaded_file)
        if self.file_type == "jpeg":
            ImageOps.exif_transpose(image, in_place=True)
        return image

    def thumbnail_file(self) -> '_TemporaryFileWrapper[bytes]':
        if self._thumbnail_file is None:
            self._thumbnail_file = NamedTemporaryFile(suffix=self.suffix)
            image = self.fullres_image()
            image.thumbnail((512, 512))
            image.save(self._thumbnail_file)
        return self._thumbnail_file

    @session_state("predict_result")
    def predict(self, model: str) -> ValueOrError['PredictResponse']:
        """Send the uploaded file to the API and return the prediction."""
        thumbnail = self.thumbnail_file()
        thumbnail.seek(0)
        try:
            response = requests.post(
                API_URL + model, files={"file": thumbnail})
        except Exception as error:
            return Result(None, error)
        if response.status_code != 200:
            return Result(None, HTTPError(response))
        json = response.json()
        if json["status"] != "ok":
            return Result(None, APIError(json))
        return Result(PredictResponse(json), None)


class PredictResponse:

    def __init__(self, json: dict) -> None:
        self._json = json
        self.celebrity = json["class"]

    def image_url(self) -> str:
        image_root = "https://storage.googleapis.com/celebtwin/public/img/"
        image_dir = \
            self._json["class"].lower().replace(" ", "-").replace(".", "")
        image_url = image_root + image_dir + "/" + self._json["name"]
        return image_url


def center_html(html: str) -> None:
    st.markdown(f"<p style='text-align: center;'>{html}</p>",
                unsafe_allow_html=True)


class CelebtwinPage:
    """🎬 Interface principale"""

    def upload_callback(self) -> None:
        UploadedImage.get.clear()
        UploadedImage.predict.clear()

    def run(self) -> None:
        st.markdown(dedent("""
            <h1 style="text-align: center">
            👯‍♂️ Trouve ton jumeau célèbre
            </h1>"""), unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload une photo", label_visibility="collapsed",
            key="uploaded_file",
            type=["jpg", "jpeg", "png"], on_change=self.upload_callback)

        status = Status()

        model_choices = {"facenet": "v1 – Facenet", "vggface": "v2 – VGG-Face"}
        model = st.pills(
            label="Modèle", label_visibility="collapsed", key="model",
            options=list(model_choices.keys()), default="vggface",
            format_func=lambda x: model_choices[x],
            on_change=self.upload_callback)

        ping_thread = PingThread.get()
        if ping_thread.is_alive():
            status.info("Démarrage du service...", icon="🚀")

        if uploaded_file:
            uploaded_image = UploadedImage.get(uploaded_file)
            col1, col2 = st.columns(2)
            with col1:
                center_html("📷 &nbsp; Ta photo")
                st.image(
                    uploaded_image.thumbnail_file().name,
                    use_container_width=True)
            with col2:
                right_column = st.empty()

        _, ping_error = ping_thread.get_result()
        if ping_error:
            report_error(status, ping_error)
        elif not uploaded_file:
            status.info(
                "Upload une photo pour trouver ton jumeau célèbre",
                icon="👀")
        if not uploaded_file:
            return
        if not model:
            status.info("Choisis un modèle", icon="👉")
            return

        if not uploaded_image.predict.done():
            status.info("Analyse en cours...", icon="🧠")
            with right_column.container():
                center_html("Attends, je cherche ton jumeau célèbre...")
                st.markdown(dedent("""
                    <div style="text-align: center; padding-top: 3em">
                    <img src="app/static/spinner.gif">
                    </div>"""), unsafe_allow_html=True)
        response, error = uploaded_image.predict(model)

        if isinstance(error, APIError):
            if error.error == "NoFaceDetectedError":
                status.error(
                    "Aucun visage détecté dans la photo", icon="❓")
                right_column.empty()
                return
        if error:
            report_error(status, error)
            right_column.button("Réessayer", on_click=self.upload_callback)
            return

        status.success(
            f"Ton jumeau célèbre est : **{response.celebrity}**",
            icon="🎉")
        with right_column.container():
            center_html(f"🎬 &nbsp; {response.celebrity}")
            st.image(response.image_url(), use_container_width=True)


def main() -> None:
    CelebtwinPage().run()
