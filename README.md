# 🎬 PIPELINE - Shorts Ranking Studio

A Python-based automation system for creating engaging "TOP 5" style short-form videos. Download videos from TikTok/YouTube, rank them, add styled titles and TTS narration, then compose them into a single polished video file.

**Current Version:** 1.0 (Active Development)  
**Platform:** Windows/Linux/macOS  
**License:** MIT

---

## 🎯 Overview

PIPELINE (Shorts Ranking Studio) automates the entire workflow for creating ranked video compilations:

1. **Download** videos from URLs (TikTok, YouTube, Instagram)
2. **Rank & Select** the best clips through interactive selection
3. **Generate** text-to-speech narration for intros and titles
4. **Compose** final video with styled titles, overlays, and effects
5. **Preview** results through the web interface

Perfect for creating "TOP 5 Memes", "Funniest Animal Moments", "Best Gaming Clips", etc.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **FFmpeg & FFprobe** - [Download](https://ffmpeg.org/download.html)
- **pip** (Python package manager)
- **yt-dlp** (installed via requirements.txt)

### Installation

1. **Clone or navigate to project:**
   ```bash
   cd d:\PIPELINE
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure FFmpeg paths in `config.json`:**
   ```json
   {
     "ffmpeg_path": "C:\\path\\to\\ffmpeg.exe",
     "ffprobe_path": "C:\\path\\to\\ffprobe.exe"
   }
   ```

### Running the Web Interface

```bash
# Start the web server
python -m uvicorn app.server:app --reload --port 8000

# Open browser to http://localhost:8000
```

### Running the CLI Pipeline

```bash
# Execute pipeline with current config
python main.py
```

---

## 📁 Project Structure

```
PIPELINE/
├── 📄 main.py                    # CLI entry point & orchestrator
├── 📄 downloader.py              # Video download handler (yt-dlp)
├── 📄 ranker.py                  # Interactive clip selection/ranking
├── 📄 composer.py                # Video composition & rendering
├── 📄 tts.py                     # Text-to-speech generation (Kokoro)
│
├── 📄 config.json                # Project configuration
├── 📄 selections.json            # Selected clips & their properties
├── 📄 requirements.txt           # Python dependencies
│
├── app/                          # FastAPI Web Application
│   ├── 📄 server.py              # FastAPI routes & endpoints
│   ├── 📄 storage.py             # JSON data storage & management
│   ├── 📄 pipeline_bridge.py     # CLI ↔ Web integration
│   ├── 📄 __init__.py
│   │
│   ├── static/                   # Frontend assets
│   │   └── 📄 style.css          # UI styling (dark theme)
│   │
│   └── templates/                # HTML templates
│       └── 📄 index.html         # Web interface
│
├── data/                         # Global metadata
│   ├── 📄 history.json           # Global project history
│   └── 📄 projects.json          # Projects registry
│
├── projects/                     # Project directories
│   ├── TOP 5 FIFA MEME/
│   │   ├── 📄 project.json       # Project state
│   │   ├── 📄 history.json       # Project audit log
│   │   ├── input_clips/          # Downloaded videos
│   │   ├── output/               # Rendered output
│   │   │   ├── 📄 final_short.mp4    # Compiled video
│   │   │   └── temp_segments/    # Temporary render files
│   │   ├── overlay/              # Custom overlay images
│   │   └── tts_cache/            # Cached TTS audio
│   │
│   └── TOP 5 FUNNY ANIMAL MOMENTS/
│       └── [same structure as above]
│
└── generated/                    # Generated preview videos
    └── 📄 preview_*.mp4          # Export files
```

---

## 🔧 Core Modules

### **main.py** - CLI Orchestrator
Entry point for command-line pipeline execution.

**Key Functions:**
- `load_config(path)` - Load and parse config.json
- `validate_config(config)` - Verify required fields and paths
- `ensure_dirs(config)` - Create necessary directories
- `check_ffmpeg_tools(config)` - Validate FFmpeg/FFprobe availability
- `main()` - Run complete pipeline

**Usage:**
```bash
python main.py
```

**Flow:**
1. Loads config.json
2. Validates configuration
3. Creates directories
4. Checks FFmpeg availability
5. Calls `composer.compose(config)` if enabled

---

### **downloader.py** - Video Download Manager
Downloads videos from URLs using yt-dlp.

**Key Function:**
```python
download_clips(urls: list, output_dir: str, ffmpeg_path: str) -> list
```

**Process:**
- Takes list of URLs (TikTok, YouTube, etc.)
- Downloads each as MP4 using yt-dlp
- Merges audio/video with FFmpeg
- Saves as `clip_01.mp4`, `clip_02.mp4`, etc.
- Returns list of successful download paths

**Example:**
```python
from downloader import download_clips

urls = [
    "https://www.tiktok.com/@user/video/123456",
    "https://www.youtube.com/watch?v=abc123"
]
downloaded = download_clips(urls, "input_clips/", "ffmpeg.exe")
```

---

### **ranker.py** - Clip Selection & Ranking
Interactive tool for selecting and ordering video clips.

**Key Functions:**
```python
list_clips(input_dir: str) -> list
get_video_info(filepath: str) -> dict  # duration, size
run_ranker(input_dir: str) -> list     # interactive selection
```

**Interactive Selection:**
- Displays all downloaded clips with metadata
- User enters numbers in order from WORST to BEST
- Example input: `3 1 2 4 5` (clip 3 is worst, clip 5 is best)
- Outputs ordered list with rank information

**Output Format:**
```json
{
  "selected_clips": [
    {
      "clip_path": "path/to/clip.mp4",
      "intro_text": "Optional intro narration",
      "intro_tts_path": "",
      "duck_original_audio": true,
      "rank_text": "#1",
      "rank_color": "#ffe600",
      "rank_font_size": 58
    }
  ]
}
```

---

### **composer.py** - Video Composition & Rendering
Handles final video assembly with titles, overlays, and effects.

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `get_video_duration()` | Extract video length via FFprobe |
| `has_audio_stream()` | Check if video has audio track |
| `resolve_fontfile()` | Map font names to system fonts |
| `build_title_drawtext()` | Generate FFmpeg drawtext filters for titles |
| `resolve_clip_tts_path()` | Resolve or generate intro TTS |
| `escape_drawtext_text()` | Escape special characters for FFmpeg |
| `hex_to_ffmpeg_color()` | Convert hex colors to FFmpeg format |

**Composition Process:**
1. Loads selected clips from selections.json
2. Generates/loads TTS audio for intros
3. Builds FFmpeg filter chain with titles
4. Merges video clips with transitions
5. Overlays rank numbers and custom text
6. Mixes original audio + TTS narration
7. Encodes final video to H.264/MP4
8. Saves to `output/final_short.mp4`

**Font Support:**
- Impact, Arial Black, Arial, Verdana, Tahoma, Trebuchet MS, Georgia, Times New Roman, Courier New

---

### **tts.py** - Text-to-Speech Engine
Generates high-quality narration using Kokoro TTS.

**Key Function:**
```python
generate_custom_tts(text: str, out_path: str) -> str
```

**Features:**
- Voice: `af_heart` (female, emotional)
- Sample Rate: 24kHz
- Format: WAV
- Language: American English (lang_code="a")
- Caching: Reuses existing audio to avoid regeneration

**Example:**
```python
from tts import generate_custom_tts

audio_path = generate_custom_tts(
    "Number one, the funniest moment!",
    "tts_cache/custom_intro.wav"
)
```

**Dependencies:**
- Kokoro >= 0.9.4
- soundfile (for WAV output)
- numpy

---

### **app/server.py** - FastAPI Web Server
REST API and web interface for project management.

**Routes:**

#### Home & Projects
```
GET  /                          # Web interface
GET  /api/projects              # List all projects
POST /api/projects              # Create new project
GET  /api/projects/{id}         # Get project state
PUT  /api/projects/{id}         # Update project state
DELETE /api/projects/{id}       # Delete project
```

#### Clip Management
```
GET  /api/projects/{id}/clips   # List project clips
POST /api/projects/{id}/clips   # Add/reorder clips
DELETE /api/projects/{id}/clips/{clip_id}  # Delete clip
```

#### Generation
```
POST /api/projects/{id}/run     # Start generation
GET  /api/jobs/{job_id}         # Check job status
```

#### Asset Management
```
POST /api/projects/{id}/overlay # Save overlay image
GET  /generated/{filename}      # Stream generated video
```

**Data Models:**
```python
class CreateProjectPayload(BaseModel):
    project_name: str

class SaveStatePayload(BaseModel):
    project_name: str
    title_blocks: list[dict] = []
    background_color: str = "#000000"
    urls: list[str] = []
    clips: list[dict] = []

class SaveOverlayPayload(BaseModel):
    image_data: str  # base64 encoded
```

---

### **app/storage.py** - Data Persistence
JSON-based file storage for all project data.

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `ensure_project_structure()` | Create project directories & files |
| `list_projects()` | Get all projects |
| `create_project()` | Initialize new project |
| `load_project_state()` | Read project.json |
| `save_project_state()` | Write project.json |
| `load_project_history()` | Get audit trail |
| `add_project_history_item()` | Log event |
| `sanitize_project_name()` | Clean filename |

**Storage Paths:**
```
projects/
├── PROJECT_NAME/
│   ├── project.json          # State
│   ├── history.json          # Audit log
│   ├── input_clips/          # Downloaded videos
│   ├── output/               # Rendered videos
│   ├── overlay/              # Custom overlays
│   └── tts_cache/            # TTS audio
```

---

### **app/pipeline_bridge.py** - CLI ↔ Web Integration
Bridges web API to command-line pipeline.

**Key Functions:**
```python
run_full_pipeline_for_project(project_name, state) -> (bool, str)
download_project_clips(project_name, urls) -> list
```

**Purpose:**
- Adapts web requests to CLI pipeline functions
- Manages threading for long-running operations
- Handles error recovery and status updates

---

## ⚙️ Configuration Reference

### config.json Structure

```json
{
  "input_dir": "projects/PROJECT_NAME/input_clips",
  "output_dir": "projects/PROJECT_NAME/output",
  "tts_cache_dir": "projects/PROJECT_NAME/tts_cache",
  "ffmpeg_path": "C:\\ffmpeg\\bin\\ffmpeg.exe",
  "ffprobe_path": "C:\\ffmpeg\\bin\\ffprobe.exe",
  
  "urls": [
    "https://www.tiktok.com/@user/video/123",
    "https://www.youtube.com/watch?v=abc"
  ],
  
  "overlay": {
    "enabled": true,
    "image_path": "projects/PROJECT_NAME/overlay/overlay.png",
    "updated_at": "2026-06-14 22:46:56"
  },
  
  "ranking": {
    "count": 5,
    "title": "TOP 5 FUNNY MOMENTS",
    "title_blocks": [
      {
        "text": "TOP",
        "font_family": "Impact, Arial Black",
        "font_size": 100,
        "color": "#ffffff",
        "stroke_color": "#000000",
        "stroke_width": 2
      },
      {
        "text": "5",
        "font_family": "Impact",
        "font_size": 100,
        "color": "#ff2b2b",
        "stroke_color": "#000000",
        "stroke_width": 2
      }
    ]
  },
  
  "compose": {
    "enabled": true,
    "output_name": "final_short.mp4"
  },
  
  "video": {
    "resolution": [1080, 1920],
    "fps": 30
  }
}
```

### Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_dir` | string | Directory containing downloaded clips |
| `output_dir` | string | Where final video is saved |
| `tts_cache_dir` | string | TTS audio caching directory |
| `ffmpeg_path` | string | Path to ffmpeg.exe |
| `ffprobe_path` | string | Path to ffprobe.exe |
| `urls` | array | Video source URLs |
| `overlay.enabled` | boolean | Use overlay image |
| `overlay.image_path` | string | Path to overlay PNG/JPG |
| `ranking.count` | number | Number of clips to include (e.g., 5) |
| `ranking.title_blocks` | array | Title text configuration |
| `compose.enabled` | boolean | Run composition step |
| `compose.output_name` | string | Output filename |
| `video.resolution` | array | [width, height] e.g., [1080, 1920] |
| `video.fps` | number | Frames per second (e.g., 30) |

---

## 📊 Workflow & Pipeline

```
┌─────────────────────────────────────┐
│  1. DOWNLOAD (downloader.py)        │
│  • Fetch videos from URLs           │
│  • Convert to MP4 with FFmpeg       │
│  • Store as clip_01.mp4, etc.       │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  2. SELECT & RANK (ranker.py)       │
│  • List clips with metadata         │
│  • User selects + orders            │
│  • Save to selections.json          │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  3. GENERATE TTS (tts.py)           │
│  • Create narration audio           │
│  • Cache for reuse                  │
│  • Kokoro engine @ 24kHz            │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  4. COMPOSE (composer.py)           │
│  • Build FFmpeg filter chain        │
│  • Overlay titles & ranks           │
│  • Merge clips + audio              │
│  • Encode to H.264                  │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  5. OUTPUT                          │
│  • Save to output/final_short.mp4   │
│  • Update history                   │
│  • Ready for preview/export         │
└─────────────────────────────────────┘
```

---

## 🌐 Web Interface

### Dashboard (Home Screen)
- Create new projects
- View existing projects with status
- Quick access to project settings

### Editor Screen
- Configure project title and styling
- Manage video clips
- Set title blocks (customizable text, fonts, colors)
- Upload overlay image
- Real-time preview
- Generation status and progress

### Project Organization
- Each project isolated in `projects/ProjectName/`
- History tracking for all changes
- Cached assets for quick regeneration
- Clean separation of clips, output, and overlays

---

## 📦 Dependencies

```
yt-dlp>=2024.0.0              # Video downloading
ffmpeg-python                  # FFmpeg wrapper
kokoro>=0.9.4                  # TTS engine
soundfile                      # WAV file I/O
fastapi                        # Web framework
uvicorn                        # ASGI server
jinja2                         # HTML templates
python-multipart               # Form parsing
```

**Installation:**
```bash
pip install -r requirements.txt
```

---

## 🛠️ Troubleshooting

### FFmpeg Not Found
```
Error: [ERROR] ffmpeg.exe not found: C:\path\to\ffmpeg.exe

Solution:
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to a known location
3. Update ffmpeg_path in config.json
4. Verify: ffmpeg -version
```

### Video Download Fails
```
Error: [ERROR] Failed to download: https://www.tiktok.com/...

Solution:
1. Update yt-dlp: pip install --upgrade yt-dlp
2. Check URL is publicly accessible
3. Verify internet connection
4. Try manual download first to test
```

### TTS Generation Slow
```
Solution:
1. First run generates TTS model (~500MB)
2. Subsequent runs use cache (much faster)
3. Ensure sufficient disk space (20GB recommended)
4. Check tts_cache_dir has write permissions
```

### Video Composition Fails
```
Solution:
1. Verify all input clips are valid MP4
2. Check output directory has write permissions
3. Ensure sufficient disk space
4. Try reducing resolution in config.json
5. Check FFmpeg supports codec: ffmpeg -codecs
```

### Web Server Won't Start
```
Error: Port 8000 already in use

Solution:
1. Find process: netstat -ano | findstr :8000
2. Kill process: taskkill /PID <pid> /F
3. Or use different port: uvicorn app.server:app --port 8001
```

---

## 📈 System Requirements

### Minimum
- **CPU:** Dual-core (video rendering is CPU-intensive)
- **RAM:** 4GB
- **Disk:** 50GB (for downloads + processing)
- **Python:** 3.8+

### Recommended
- **CPU:** Quad-core or better
- **RAM:** 8GB+
- **Disk:** 100GB+ (for caching)
- **GPU:** NVIDIA CUDA (optional, for faster encoding)
- **Internet:** High-speed (for downloading videos)

### Performance Notes
- Video rendering time depends on CPU speed
- TTS model loads on first use (~30 seconds)
- Subsequent projects benefit from TTS cache
- Consider video length when setting resolution/fps

---

## 📝 Data Format Examples

### selections.json Structure
```json
{
  "selected_clips": [
    {
      "clip_path": "projects/TOP 5 FIFA/input_clips/clip_01.mp4",
      "intro_text": "Number five...",
      "intro_tts_path": "projects/TOP 5 FIFA/tts_cache/custom_123abc.wav",
      "duck_original_audio": true,
      "rank_text": "#5",
      "rank_color": "#ffe600",
      "rank_stroke_color": "#000000",
      "rank_stroke_width": 2,
      "rank_font_size": 58
    }
  ]
}
```

### project.json Structure
```json
{
  "project_name": "TOP 5 FIFA MEME",
  "title_blocks": [
    {
      "text": "TOP",
      "font_family": "Impact",
      "font_size": 100,
      "color": "#ffffff",
      "stroke_color": "#000000",
      "stroke_width": 2
    }
  ],
  "background_color": "#000000",
  "urls": ["https://tiktok.com/..."],
  "clips": [{"clip_path": "..."}],
  "overlay_image_path": "...",
  "overlay_updated_at": ""
}
```

### history.json Structure
```json
[
  {
    "title": "Generated Short",
    "file_name": "final_short.mp4",
    "file_path": "projects/TOP 5 FIFA/output/final_short.mp4",
    "created_at": "2026-06-15 10:30:45",
    "status": "ready"
  }
]
```

---

## 🚀 Advanced Usage

### Command-Line Only
```bash
# Configure config.json for your project
python main.py
```

### Web-Only Workflow
```bash
# Start server
python -m uvicorn app.server:app --port 8000

# Access interface
open http://localhost:8000
```

### Batch Processing
```python
# Process multiple projects programmatically
from app.pipeline_bridge import run_full_pipeline_for_project

projects = ["TOP 5 FIFA", "TOP 5 CATS", "TOP 5 FAILS"]
for proj in projects:
    run_full_pipeline_for_project(proj, {})
```

---

## 📋 Typical Workflow

1. **Create Project**
   - Open web interface
   - Click "Create New Short"
   - Enter project name (e.g., "TOP 5 FIFA MEME")

2. **Add Videos**
   - Paste TikTok/YouTube URLs
   - Click "Download Clips"
   - Wait for downloads to complete

3. **Configure Title**
   - Edit title blocks (TOP, 5, FIFA, MEME, etc.)
   - Set fonts, colors, stroke width
   - Preview in real-time

4. **Select & Order**
   - View downloaded clips
   - Reorder by importance
   - Optionally add per-clip narration

5. **Optional: Upload Overlay**
   - Add custom background image
   - Position on final video

6. **Generate**
   - Click "Generate Final Short"
   - Monitor progress bar
   - View completed video in preview

7. **Export**
   - Download final_short.mp4
   - Share on social media

---

## 🔄 System Architecture

```
USER INTERFACE (Web)
        ↓
    FastAPI (server.py)
        ↓
    Storage Layer (storage.py)
        ↓
    Pipeline Bridge (pipeline_bridge.py)
        ↓
┌───────────────────────────────┐
│   CLI Pipeline (main.py)      │
├───────────────────────────────┤
│ • Downloader (yt-dlp)         │
│ • Ranker (clip selection)     │
│ • TTS (Kokoro)                │
│ • Composer (FFmpeg)           │
└───────────────────────────────┘
        ↓
    FFmpeg/FFprobe (system)
        ↓
    OUTPUT: final_short.mp4
```

---

## 📚 Additional Resources

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [Kokoro TTS](https://github.com/remsky/Kokoro-FastAPI)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

---

## 📄 License & Attribution

This project is designed for personal and educational use. Respect copyright and licensing of downloaded videos.

**Last Updated:** 2026-06-15  
**Status:** Actively Maintained  
**Contributions:** Welcome

---

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Verify config.json is properly formatted
3. Ensure all prerequisites are installed
4. Check directory permissions
5. Review logs for detailed error messages

---

**Happy video creation! 🎥✨**
