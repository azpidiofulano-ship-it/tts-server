import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import io

app = FastAPI(title="Edge TTS Server")

@app.get("/")
def root():
    return {"status": "Edge TTS Server running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/voices")
async def list_voices():
    voices = await edge_tts.list_voices()
    return JSONResponse(content=voices)

@app.post("/tts")
async def synthesize(request: Request):
    data = await request.json()
    text  = data.get("text", "").strip()
    voice = data.get("voice", "es-ES-AlvaroNeural")
    rate  = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")

    if not text:
        raise HTTPException(status_code=400, detail="Texto vacío")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Texto demasiado largo")

    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
