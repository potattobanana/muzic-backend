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
        'skip_download': True,
        'youtube_include_dash_manifest': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False
            )

            # Get the selected format URL directly
            url = info.get('url')
            if not url:
                # Try getting from formats list
                formats = info.get('formats', [])
                # Prefer audio-only formats
                audio_only = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
                if audio_only:
                    audio_only.sort(key=lambda f: f.get('abr') or f.get('tbr') or 0, reverse=True)
                    url = audio_only[0]['url']
                elif formats:
                    # Fall back to any format with a URL
                    url = formats[-1]['url']

            if not url:
                raise HTTPException(status_code=404, detail="No audio URL found")

            return {
                "url": url,
                "title": info.get('title'),
                "duration": info.get('duration'),
                "thumbnail": info.get('thumbnail'),
            }

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
