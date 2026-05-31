from fastapi import FastAPI, HTTPException, Request
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
    expose_headers=["X-Song-Title", "X-Song-Duration", "X-Song-Thumb"],
)

def is_valid_video_id(video_id: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))

def get_audio_info(video_id: str):
    ydl_opts = {
        # Prefer mp4a/m4a audio which browsers handle best
        'format': 'bestaudio[ext=m4a]/bestaudio[acodec=aac]/bestaudio/best',
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
        ext = info.get('ext', 'm4a')
        mime = 'audio/mp4'

        if not url:
            formats = info.get('formats', [])
            # Prefer m4a/aac formats
            m4a = [f for f in formats if f.get('ext') == 'm4a' and f.get('url')]
            if m4a:
                m4a.sort(key=lambda f: f.get('abr') or 0, reverse=True)
                url = m4a[0]['url']
                mime = 'audio/mp4'
            else:
                audio_only = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
                if audio_only:
                    audio_only.sort(key=lambda f: f.get('abr') or 0, reverse=True)
                    best = audio_only[0]
                    url = best['url']
                    ext = best.get('ext', 'webm')
                    mime = 'audio/webm' if ext == 'webm' else 'audio/mp4'

        return {
            "url": url,
            "mime": mime,
            "title": info.get('title', ''),
            "duration": info.get('duration', 0),
            "thumbnail": info.get('thumbnail', ''),
        }

@app.get("/")
def root():
    return {"status": "Muzic backend running"}

@app.get("/info/{video_id}")
def get_info(video_id: str):
    if not is_valid_video_id(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    try:
        return get_audio_info(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{video_id}")
async def stream_audio(video_id: str, request: Request):
    if not is_valid_video_id(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    try:
        info = get_audio_info(video_id)
        audio_url = info.get('url')
        if not audio_url:
            raise HTTPException(status_code=404, detail="No audio URL found")

        # Forward range header if present (needed for seeking)
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1)',
            'Referer': 'https://www.youtube.com/',
        }
        range_header = request.headers.get('range')
        if range_header:
            headers['Range'] = range_header

        async def audio_generator():
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                async with client.stream('GET', audio_url, headers=headers) as response:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        yield chunk

        return StreamingResponse(
            audio_generator(),
            media_type=info['mime'],
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "X-Song-Title": info.get('title', ''),
                "X-Song-Duration": str(info.get('duration', 0)),
                "X-Song-Thumb": info.get('thumbnail', ''),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
