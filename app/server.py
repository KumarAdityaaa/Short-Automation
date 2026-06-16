import hashlib
import base64
import os
import threading
import uuid
from datetime import datetime


from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


from app.pipeline_bridge import (
    run_full_pipeline_for_project,
    download_project_clips,
    update_config_from_project_state,
    write_selections_from_project_state,
)
from app.storage import (
    ensure_data_files,
    list_projects,
    create_project,
    load_project_state,
    save_project_state,
    delete_project,
    move_clip,
    delete_clip,
    sanitize_project_name,
    project_folder_path,
    project_input_clips_path,
    build_project_clips_with_preview,
    load_project_history,
    add_project_history_item,
    update_latest_project_history_item,
    delete_project_history_item,
)
from tts import generate_custom_tts


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")


class CreateProjectPayload(BaseModel):
    project_name: str

class SaveOverlayPayload(BaseModel):
    image_data: str

class SaveStatePayload(BaseModel):
    project_name: str
    title_blocks: list[dict] = []
    background_color: str = "#000000"
    urls: list[str] = []
    clips: list[dict] = []


generation_jobs = {}
generation_jobs_lock = threading.Lock()


@app.on_event("startup")
def startup_event():
    ensure_data_files()

def project_overlay_path(project_name: str) -> str:
    safe_name = sanitize_project_name(project_name)
    path = os.path.join(project_folder_path(safe_name), "overlay")
    os.makedirs(path, exist_ok=True)
    return path

def safe_filename_from_text(text: str) -> str:
    digest = hashlib.md5(text.strip().encode("utf-8")).hexdigest()[:12]
    return f"custom_{digest}.wav"


def project_tts_cache_path(project_name: str) -> str:
    safe_name = sanitize_project_name(project_name)
    path = os.path.join(project_folder_path(safe_name), "tts_cache")
    os.makedirs(path, exist_ok=True)
    return path


def set_generation_job(job_id: str, data: dict) -> None:
    with generation_jobs_lock:
        generation_jobs[job_id] = data


def update_generation_job(job_id: str, **updates) -> None:
    with generation_jobs_lock:
        if job_id in generation_jobs:
            generation_jobs[job_id].update(updates)


def get_generation_job(job_id: str) -> dict | None:
    with generation_jobs_lock:
        job = generation_jobs.get(job_id)
        return dict(job) if job else None


def run_generation_job(job_id: str, project_name: str, state: dict) -> None:
    try:
        start_ts = datetime.now().timestamp()
        update_generation_job(
            job_id,
            status="processing",
            message="Generating final short...",
            progress=10,
            progress_label="Preparing project",
            started_at_ts=start_ts,
            finished_at_ts=None,
        )

        add_project_history_item(
            project_name,
            {
                "title": "Generated Short",
                "file_name": "",
                "file_path": "",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "processing"
            }
        )

        update_generation_job(
            job_id,
            progress=35,
            progress_label="Rendering clips"
        )

        ok, result = run_full_pipeline_for_project(project_name, state)

        if ok:
            update_latest_project_history_item(
                project_name,
                {
                    "file_name": os.path.basename(result),
                    "file_path": result,
                    "status": "ready"
                }
            )
            history = load_project_history(project_name)
            update_generation_job(
                job_id,
                status="ready",
                ok=True,
                result=result,
                history=history,
                message="Generation complete.",
                progress=100,
                progress_label="Done",
                finished_at_ts=datetime.now().timestamp()
            )
        else:
            update_latest_project_history_item(
                project_name,
                {
                    "status": f"error: {result}"
                }
            )
            history = load_project_history(project_name)
            update_generation_job(
                job_id,
                status="failed",
                ok=False,
                result=result,
                history=history,
                message=str(result),
                progress=100,
                progress_label="Failed",
                finished_at_ts=datetime.now().timestamp()
            )
    except Exception as e:
        update_latest_project_history_item(
            project_name,
            {
                "status": f"error: {e}"
            }
        )
        history = load_project_history(project_name)
        update_generation_job(
            job_id,
            status="failed",
            ok=False,
            result=str(e),
            history=history,
            message=str(e),
            progress=100,
            progress_label="Failed",
            finished_at_ts=datetime.now().timestamp()
        )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse(request, "index.html", context)

@app.post("/api/projects/{project_name}/overlay/save")
def save_project_overlay(project_name: str, payload: SaveOverlayPayload):
    safe_name = sanitize_project_name(project_name)
    state = load_project_state(safe_name)

    image_data = (payload.image_data or "").strip()
    if not image_data:
        return JSONResponse({"ok": False, "error": "Missing image data."}, status_code=400)

    if "," not in image_data:
        return JSONResponse({"ok": False, "error": "Invalid image data format."}, status_code=400)

    header, encoded = image_data.split(",", 1)
    if not header.startswith("data:image/png;base64"):
        return JSONResponse({"ok": False, "error": "Overlay must be a PNG image."}, status_code=400)

    try:
        binary = base64.b64decode(encoded)
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid base64 image data."}, status_code=400)

    overlay_dir = project_overlay_path(safe_name)
    overlay_file = os.path.join(overlay_dir, "preview_overlay.png")

    try:
        with open(overlay_file, "wb") as f:
            f.write(binary)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Failed to save overlay: {e}"}, status_code=500)

    state["overlay_image_path"] = overlay_file
    state["overlay_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_project_state(safe_name, state)

    return {
        "ok": True,
        "overlay_image_path": overlay_file,
        "overlay_updated_at": state["overlay_updated_at"],
    }

@app.get("/api/projects")
def get_projects():
    return {"projects": list_projects()}


@app.post("/api/projects")
def create_project_api(payload: CreateProjectPayload):
    name = payload.project_name.strip()
    if not name:
        return JSONResponse({"ok": False, "error": "Project name is required."}, status_code=400)

    try:
        project = create_project(name)
        return {"ok": True, "project": project, "projects": list_projects()}
    except FileExistsError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/projects/{project_name}")
def get_project_state(project_name: str):
    state = load_project_state(project_name)
    history = load_project_history(project_name)
    return {
        "state": state,
        "history": history,
        "projects": list_projects(),
    }


@app.get("/api/projects/{project_name}/files/input_clips/{filename}")
def serve_project_input_clip(project_name: str, filename: str):
    safe_name = sanitize_project_name(project_name)
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = os.path.join(project_input_clips_path(safe_name), filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, media_type="video/mp4")


@app.get("/api/projects/{project_name}/audio-preview/{filename}")
def serve_generated_intro_audio(project_name: str, filename: str):
    safe_name = sanitize_project_name(project_name)

    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    audio_path = os.path.join(project_tts_cache_path(safe_name), filename)
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(audio_path, media_type="audio/wav")


@app.post("/api/projects/{project_name}/clips/{index}/generate-intro-audio")
def generate_intro_audio_route(project_name: str, index: int):
    state = load_project_state(project_name)
    clips = state.get("clips", [])

    if index < 0 or index >= len(clips):
        return JSONResponse({"ok": False, "error": "Invalid clip index."}, status_code=400)

    clip = clips[index]
    intro_text = (clip.get("intro_text") or "").strip()

    if not intro_text:
        return JSONResponse({"ok": False, "error": "No intro text provided."}, status_code=400)

    cache_dir = project_tts_cache_path(project_name)
    out_name = safe_filename_from_text(intro_text)
    out_path = os.path.join(cache_dir, out_name)

    try:
        generated_path = generate_custom_tts(intro_text, out_path)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"TTS generation failed: {e}"}, status_code=500)

    if not generated_path or not os.path.exists(generated_path):
        return JSONResponse({"ok": False, "error": "TTS generation failed."}, status_code=500)

    clip["intro_tts_path"] = generated_path
    clips[index] = clip
    state["clips"] = clips
    save_project_state(project_name, state)

    preview_url = f"/api/projects/{sanitize_project_name(project_name)}/audio-preview/{os.path.basename(generated_path)}"

    return {
        "ok": True,
        "intro_tts_path": generated_path,
        "preview_url": preview_url,
        "clips": clips,
    }


@app.post("/api/save")
def save_state_api(payload: SaveStatePayload):
    current_state = load_project_state(payload.project_name)

    new_state = {
        "title_blocks": payload.title_blocks,
        "background_color": payload.background_color,
        "urls": payload.urls,
        "clips": payload.clips if payload.clips else current_state.get("clips", []),
    }

    save_project_state(payload.project_name, new_state)
    saved_state = load_project_state(payload.project_name)

    # keep selections.json in sync with every save
    clips = saved_state.get("clips", [])
    if clips:
        write_selections_from_project_state(payload.project_name, saved_state)

    return {"ok": True, "state": saved_state}


@app.post("/api/projects/{project_name}/download-clips")
def download_clips_for_project(project_name: str):
    state = load_project_state(project_name)
    urls = state.get("urls", [])

    ok, message = download_project_clips(project_name, urls)
    if not ok:
        return JSONResponse({"ok": False, "error": message}, status_code=400)

    refreshed_state = load_project_state(project_name)
    refreshed_state["clips"] = build_project_clips_with_preview(
        project_name,
        refreshed_state.get("urls", []),
        refreshed_state.get("clips", [])
    )
    save_project_state(project_name, refreshed_state)

    # write selections.json immediately after download
    update_config_from_project_state(project_name, refreshed_state)
    write_selections_from_project_state(project_name, refreshed_state)

    return {"ok": True, "clips": refreshed_state["clips"], "message": message}


@app.post("/api/projects/{project_name}/clips/load-from-urls")
def load_clips_from_urls(project_name: str):
    state = load_project_state(project_name)
    urls = state.get("urls", [])
    clips = build_project_clips_with_preview(project_name, urls, state.get("clips", []))

    state["clips"] = clips
    save_project_state(project_name, state)
    return {"ok": True, "clips": clips}


@app.post("/api/projects/{project_name}/clips/{index}/move/{direction}")
def move_clip_route(project_name: str, index: int, direction: str):
    if direction not in {"up", "down"}:
        return JSONResponse({"ok": False, "error": "invalid direction"}, status_code=400)

    ok = move_clip(project_name, index, direction)
    state = load_project_state(project_name)
    return {"ok": ok, "clips": state.get("clips", [])}


@app.post("/api/projects/{project_name}/clips/{index}/delete")
def delete_clip_route(project_name: str, index: int):
    ok = delete_clip(project_name, index)
    state = load_project_state(project_name)
    return {"ok": ok, "clips": state.get("clips", [])}


@app.post("/api/projects/{project_name}/generate/start")
def generate_project_start(project_name: str):
    state = load_project_state(project_name)

    if not state.get("urls"):
        return JSONResponse(
            {"ok": False, "error": "No URLs saved in this project."},
            status_code=400
        )

    job_id = uuid.uuid4().hex
    set_generation_job(
        job_id,
        {
            "job_id": job_id,
            "project_name": project_name,
            "status": "queued",
            "ok": None,
            "result": "",
            "message": "Queued for generation.",
            "history": load_project_history(project_name),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "started_at_ts": None,
            "finished_at_ts": None,
            "progress": 0,
            "progress_label": "Queued",
        }
    )

    thread = threading.Thread(
        target=run_generation_job,
        args=(job_id, project_name, state),
        daemon=True
    )
    thread.start()

    return {
        "ok": True,
        "job_id": job_id,
        "status": "queued",
        "message": "Generation started.",
        "progress": 0,
        "progress_label": "Queued",
    }


@app.get("/api/projects/{project_name}/generate/status/{job_id}")
def generate_project_status(project_name: str, job_id: str):
    job = get_generation_job(job_id)
    if not job or job.get("project_name") != project_name:
        return JSONResponse({"ok": False, "error": "Job not found."}, status_code=404)

    job["history"] = load_project_history(project_name)
    return {"ok": True, **job}


@app.delete("/api/projects/{project_name}")
def delete_project_route(project_name: str):
    ok = delete_project(project_name)
    return {"ok": ok, "projects": list_projects()}


@app.post("/api/projects/{project_name}/history/delete/{index}")
def delete_project_history_route(project_name: str, index: int):
    ok = delete_project_history_item(project_name, index)
    history = load_project_history(project_name)
    return {"ok": ok, "history": history}