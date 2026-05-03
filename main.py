import asyncio
import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import io

app = FastAPI(title="Edge TTS Server")

class TTSRequest(BaseModel):
    text: str
    voice: str = "es-ES-AlvaroNeural"
    rate: str = "+0%"    # velocidad: -50% a +100%
    pitch: str = "+0Hz"  # tono: -50Hz a +50Hz

@app.get("/")
def root():
    return {"status": "Edge TTS Server running"}

@app.get("/voices")
async def list_voices():
    """Devuelve todas las voces disponibles (~400 voces, 40+ idiomas)"""
    voices = await edge_tts.list_voices()
    return JSONResponse(voices)

@app.get("/voices/{locale}")
async def voices_by_locale(locale: str):
    """Voces filtradas por locale, p.ej. /voices/es-ES"""
    all_voices = await edge_tts.list_voices()
    filtered = [v for v in all_voices if v["Locale"].lower().startswith(locale.lower())]
    return JSONResponse(filtered)

@app.post("/tts")
async def synthesize(req: TTSRequest):
    """
    Sintetiza texto con la voz indicada.
    Devuelve audio/mpeg (MP3) directamente en el body.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")
    if len(req.text) > 5000:
        raise HTTPException(status_code=400, detail="Texto demasiado largo (máx 5000 chars)")

    try:
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch
        )

        # Acumula el audio en memoria
        audio_buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buf.write(chunk["data"])

        audio_buf.seek(0)
        if audio_buf.getbuffer().nbytes == 0:
            raise HTTPException(status_code=500, detail="No se generó audio")

        return StreamingResponse(
            audio_buf,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=tts.mp3"}
        )

    except edge_tts.exceptions.NoAudioReceived:
        raise HTTPException(status_code=500, detail=f"La voz '{req.voice}' no generó audio")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
