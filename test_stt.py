from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="cpu", compute_type="int8")  # CPU для Mac, int8 для экономии RAM
segments, _ = model.transcribe("sample_audio.wav", language="ru")  # Замени на твой WAV-файл
text = " ".join([seg.text for seg in segments])
print(text)
