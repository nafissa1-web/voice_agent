import os

import streamlit as st
import whisper

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "tiny")


@st.cache_resource
def load_whisper_model():
    """Loaded once per Streamlit session thanks to st.cache_resource."""
    return whisper.load_model(WHISPER_MODEL_SIZE, download_root=".")


def transcribe_audio(model, audio_bytes: bytes) -> str:
    """Writes the recorded bytes to a temp wav file and transcribes it.
    Returns the text, or a string starting with 'ERROR::' on failure.
    """
    temp_filename = "temp_voice.wav"
    try:
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
        result = model.transcribe(temp_filename)
        return result["text"].strip()
    except Exception as e:
        return f"ERROR::خطأ أثناء تفريغ الصوت: {e}"
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
