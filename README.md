# PIPELINE

A simple clone-ready video shorts pipeline for ranking and composing TikTok / YouTube clips with text-to-speech and title overlays.

## What this repo does

- downloads videos from URLs using `yt-dlp`
- ranks and orders clips with `ranker.py`
- generates narration audio with `tts.py`
- builds a final video using FFmpeg via `composer.py`
- supports a FastAPI web UI in `app/server.py`

## Clone and install

```bash
git clone <repo-url> d:\PIPELINE
cd d:\PIPELINE
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Required setup

1. Install FFmpeg and FFprobe.
2. Update `config.json` with the correct Windows paths:

```json
{
  "ffmpeg_path": "C:\\ffmpeg-8.1.1-essentials_build\\bin\\ffmpeg.exe",
  "ffprobe_path": "C:\\ffmpeg-8.1.1-essentials_build\\bin\\ffprobe.exe"
}
```

3. Set `input_dir`, `output_dir`, and `tts_cache_dir` in `config.json`.

## Run the pipeline

```bash
python main.py
```

## Run the web UI

```bash
python -m uvicorn app.server:app --reload --port 8000
```

Open: `http://localhost:8000`

## Key files

- `main.py` - loads config and runs the compose pipeline
- `downloader.py` - downloads source clips with `yt-dlp`
- `ranker.py` - lists clips and prepares selections
- `composer.py` - builds the final video with titles and audio
- `tts.py` - generates custom TTS audio
- `config.json` - pipeline settings and paths
- `selections.json` - selected clips metadata

## Web app files

- `app/server.py` - API and UI server
- `app/storage.py` - project data storage
- `app/pipeline_bridge.py` - web-to-pipeline integration
- `app/templates/index.html` - frontend page
- `app/static/style.css` - frontend styles

## Folder layout

```
PIPELINE/
├── app/
├── data/
├── generated/
├── projects/
├── composer.py
├── downloader.py
├── main.py
├── ranker.py
├── tts.py
├── config.json
├── requirements.txt
├── selections.json
```

## What to edit

Update `config.json` for:

- `input_dir`
- `output_dir`
- `tts_cache_dir`
- `ffmpeg_path`
- `ffprobe_path`
- `urls`
- `ranking`
- `compose`
- `video`

## Notes

- Use `projects/<project-name>/` for per-project clips, output, overlay, and TTS cache.
- `generated/` stores preview outputs.
- The web UI is optional; the CLI works on its own.
- Keep FFmpeg installed and available at the paths in `config.json`.

## Minimal commands

```bash
python main.py
python -m uvicorn app.server:app --reload --port 8000
```

That's it.
