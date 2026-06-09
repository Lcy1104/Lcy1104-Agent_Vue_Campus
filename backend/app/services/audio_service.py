"""Audio service for speech recognition and text-to-speech."""
import tempfile
from pathlib import Path

from fastapi import UploadFile


async def transcribe_upload(file: UploadFile, language: str = "zh-CN") -> dict:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(await file.read())

    wav_path = _ensure_wav(tmp_path)
    try:
        with sr.AudioFile(str(wav_path)) as source:
            audio_data = recognizer.record(source)
        return {"text": recognizer.recognize_google(audio_data, language=language)}
    finally:
        tmp_path.unlink(missing_ok=True)
        if wav_path != tmp_path:
            wav_path.unlink(missing_ok=True)


def transcribe_microphone(language: str = "zh-CN", timeout: int = 5, phrase_time_limit: int = 10) -> dict:
    """Use server-side microphone input with SpeechRecognition and PyAudio."""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    return {"text": recognizer.recognize_google(audio_data, language=language)}


def synthesize_text(text: str, language: str = "zh-CN", voice: str | None = None, rate: int | None = None) -> Path:
    import pyttsx3

    output_path = Path(tempfile.gettempdir()) / f"campus_agent_tts_{abs(hash((text, language, voice, rate)))}.wav"
    engine = pyttsx3.init()
    if rate:
        engine.setProperty("rate", rate)

    selected_voice_id = _select_voice(engine, language, voice)
    if selected_voice_id:
        engine.setProperty("voice", selected_voice_id)

    engine.save_to_file(text[:2000], str(output_path))
    engine.runAndWait()
    return output_path


def _select_voice(engine, language: str, preferred_voice: str | None) -> str | None:
    voices = engine.getProperty("voices") or []
    if preferred_voice:
        for item in voices:
            if preferred_voice.lower() in (item.id or "").lower() or preferred_voice.lower() in (item.name or "").lower():
                return item.id

    language_prefix = (language or "").split("-")[0].lower()
    for item in voices:
        languages = " ".join(str(value).lower() for value in getattr(item, "languages", []) or [])
        name = (getattr(item, "name", "") or "").lower()
        if language_prefix and (language_prefix in languages or language_prefix in name):
            return item.id
    return None


def _ensure_wav(path: Path) -> Path:
    if path.suffix.lower() == ".wav":
        return path
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(path))
        wav_path = path.with_suffix(".wav")
        audio.export(str(wav_path), format="wav")
        return wav_path
    except Exception as exc:
        raise ValueError("当前音频格式无法转换为 WAV，请确认已安装 ffmpeg 或上传 wav/flac/aiff") from exc
