import pytest
from pipeline import get_transcription, get_summary

def test_stt():
    text = get_transcription("sample_audio.wav")  # Тестовый аудио
    assert len(text) > 0

def test_llm():
    dummy_text = "Тестовый текст для саммари."
    response = get_summary(dummy_text)
    assert 'summary' in response.lower() or 'выжимка' in response.lower()  # Адаптировал под русский
