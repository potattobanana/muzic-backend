from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import httpx
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def is_valid_video_id(video_id: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))

def get_audio_info(video_id: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'youtube_include_dash_manifest': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}",
            download=False
        )
        url = info.get('url')
        if not url:
            formats = info.get('formats', [])
            audio_only = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
            if audio_only:
                audio_only.sort(key=lambda f: f.get('abr') or f.get('tbr') or 0, reverse=True)
                url = audio_only[0]['url']
            elif formats:
                url = formats[-1]['url']
        return {
            "url": url,
            "title": info.get('title'),
            "duration": info.get('duration'),
            "thumbnail": info.get('thumbnail'),
        }

@app.get("/")
def root():
    return {"status": "Muzic backend running"}

@app.get("/info/{video_id}")
def get_info(video_id: str):
    """Get audio info without proxying - for metadata"""
    if not is_valid_video_id(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    try:
        return get_audio_info(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{video_id}")
async def stream_audio(video_id: str):
    """Proxy the audio stream to avoid CORS issues"""
    if not is_valid_video_id(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    try:
        info = get_audio_info(video_id)
        audio_url = info.get('url')
        if not audio_url:
            raise HTTPException(status_code=404, detail="No audio URL found")

        # Stream the audio through our server
        async def audio_generator():
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream('GET', audio_url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://www.youtube.com/',
                }) as response:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk

        return StreamingResponse(
            audio_generator(),
            media_type="audio/webm",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "X-Song-Title": info.get('title', ''),
                "X-Song-Duration": str(info.get('duration', 0)),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
