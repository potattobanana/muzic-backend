# Muzic Backend

A simple FastAPI server that extracts the best quality audio URL from YouTube videos using yt-dlp. Used by the Muzic app to play audio without ads.

## API

### GET /audio/{video_id}
Returns the best audio stream URL for a YouTube video.

**Example:** `/audio/dQw4w9WgXcQ`

**Response:**
```json
{
  "url": "https://...",
  "title": "Never Gonna Give You Up",
  "duration": 212,
  "thumbnail": "https://...",
  "ext": "webm",
  "abr": 160
}
```

## Deploy to Render
1. Push this folder to a GitHub repo
2. Go to render.com → New Web Service
3. Connect the repo
4. It auto-detects render.yaml and deploys
