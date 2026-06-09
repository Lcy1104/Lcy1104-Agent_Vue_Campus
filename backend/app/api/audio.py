"""Audio APIs for speech-to-text and text-to-speech."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import get_current_user
from app.services import audio_service

router = APIRouter(prefix="/api/audio", tags=["语音"], dependencies=[Depends(get_current_user)])


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), language: str = Form("zh-CN")):
    try:
        return await audio_service.transcribe_upload(file, language)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"语音识别失败：{exc}")


@router.post("/transcribe/microphone")
async def transcribe_microphone(payload: dict | None = None):
    payload = payload or {}
    try:
        return audio_service.transcribe_microphone(
            language=str(payload.get("language") or "zh-CN"),
            timeout=int(payload.get("timeout") or 5),
            phrase_time_limit=int(payload.get("phrase_time_limit") or 10),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"麦克风语音识别失败：{exc}")


@router.post("/tts")
async def text_to_speech(payload: dict):
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="朗读文本不能为空")
    try:
        output_path = audio_service.synthesize_text(
            text,
            language=str(payload.get("language") or "zh-CN"),
            voice=payload.get("voice"),
            rate=int(payload["rate"]) if payload.get("rate") else None,
        )
        return FileResponse(str(output_path), media_type="audio/wav", filename="tts.wav")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"语音合成失败：{exc}")
