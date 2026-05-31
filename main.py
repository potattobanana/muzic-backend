from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
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

@app.get("/")
def root():
    return {"status": "Muzic backend running"}

@app.get("/audio/{video_id}")
def get_audio(video_id: str):
    if not is_valid_video_id(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            
            # Get best audio format
            formats = info.get('formats', [])
            audio_formats = [
                f for f in formats
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
            ]
            
            if not audio_formats:
                # Fallback to any format with audio
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
            
            if not audio_formats:
                raise HTTPException(status_code=404, detail="No audio found")
            
            # Sort by quality (abr = audio bitrate)
            audio_formats.sort(key=lambda f: f.get('abr') or 0, reverse=True)
            best = audio_formats[0]
            
            return {
                "url": best['url'],
                "title": info.get('title'),
                "duration": info.get('duration'),
                "thumbnail": info.get('thumbnail'),
                "ext": best.get('ext', 'webm'),
                "abr": best.get('abr'),
            }
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
