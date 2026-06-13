import os
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.pipeline_bridge import run_full_pipeline_for_project, download_project_clips
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
    project_input_clips_path,
    build_project_clips_with_preview,
    load_project_history,
    add_project_history_item,
    update_latest_project_history_item,
    delete_project_history_item,
)


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")


class CreateProjectPayload(BaseModel):
    project_name: str


class SaveStatePayload(BaseModel):
    project_name: str
    title_blocks: list[dict] = []
    background_color: str = "#000000"
    urls: list[str] = []
    clips: list[dict] = []


@app.on_event("startup")
def startup_event():
    ensure_data_files()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse(request, "index.html", context)


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
    return {"ok": True, "state": load_project_state(payload.project_name)}


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

    return {"ok": True, "clips": refreshed_state["clips"], "message": message}


@app.post("/api/projects/{project_name}/clips/load-from-urls")
def load_clips_from_urls(project_name: str):
    state = load_project_state(project_name)
    urls = state.get("urls", [])
    clips = build_project_clips_with_preview(project_name, urls, state.get("clips", []))

    state["clips"] = clips
    save_project_state(project_name, state)
    return {"ok": True, "clips": clips}


@app.post("/api/projects/{project_name}/clips/move/{index}/{direction}")
def move_clip_route(project_name: str, index: int, direction: str):
    if direction not in {"up", "down"}:
        return JSONResponse({"ok": False, "error": "invalid direction"}, status_code=400)

    ok = move_clip(project_name, index, direction)
    state = load_project_state(project_name)
    return {"ok": ok, "clips": state.get("clips", [])}


@app.post("/api/projects/{project_name}/clips/delete/{index}")
def delete_clip_route(project_name: str, index: int):
    ok = delete_clip(project_name, index)
    state = load_project_state(project_name)
    return {"ok": ok, "clips": state.get("clips", [])}


@app.post("/api/projects/{project_name}/generate")
def generate_project(project_name: str):
    state = load_project_state(project_name)

    if not state.get("urls"):
        return JSONResponse(
            {"ok": False, "error": "No URLs saved in this project."},
            status_code=400
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
    else:
        update_latest_project_history_item(
            project_name,
            {
                "status": f"error: {result}"
            }
        )

    history = load_project_history(project_name)
    return {
        "ok": ok,
        "result": result,
        "history": history
    }


@app.delete("/api/projects/{project_name}")
def delete_project_route(project_name: str):
    ok = delete_project(project_name)
    return {"ok": ok, "projects": list_projects()}


@app.post("/api/projects/{project_name}/history/delete/{index}")
def delete_project_history_route(project_name: str, index: int):
    ok = delete_project_history_item(project_name, index)
    history = load_project_history(project_name)
    return {"ok": ok, "history": history}