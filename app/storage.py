import json
import os
import re
import shutil
from typing import Any
import re as _re

DATA_DIR = "data"
GENERATED_DIR = "generated"
PROJECTS_ROOT = "projects"

DEFAULT_TITLE_BLOCKS = []

DEFAULT_PROJECT_STATE = {
    "title_text": "",
    "title_blocks": [],
    "background_color": "#000000",
    "urls": [],
    "clips": [],
    "overlay_image_path": "",
    "overlay_updated_at": ""
}


def ensure_data_files() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(GENERATED_DIR, exist_ok=True)
    os.makedirs(PROJECTS_ROOT, exist_ok=True)


def read_json(path: str, fallback: Any) -> Any:
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def sanitize_project_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80] or "Untitled Project"


def project_folder_path(project_name: str) -> str:
    safe_name = sanitize_project_name(project_name)
    return os.path.join(PROJECTS_ROOT, safe_name)


def project_json_path(project_name: str) -> str:
    return os.path.join(project_folder_path(project_name), "project.json")


def project_history_path(project_name: str) -> str:
    return os.path.join(project_folder_path(project_name), "history.json")


def project_input_clips_path(project_name: str) -> str:
    return os.path.join(project_folder_path(project_name), "input_clips")


def project_output_path(project_name: str) -> str:
    return os.path.join(project_folder_path(project_name), "output")


def ensure_project_structure(project_name: str) -> None:
    safe_name = sanitize_project_name(project_name)
    folder = project_folder_path(safe_name)

    os.makedirs(folder, exist_ok=True)
    os.makedirs(project_input_clips_path(safe_name), exist_ok=True)
    os.makedirs(project_output_path(safe_name), exist_ok=True)

    if not os.path.exists(project_json_path(safe_name)):
        project_data = json.loads(json.dumps(DEFAULT_PROJECT_STATE))
        project_data["project_name"] = safe_name
        write_json(project_json_path(safe_name), project_data)

    if not os.path.exists(project_history_path(safe_name)):
        write_json(project_history_path(safe_name), [])




def normalize_title_blocks(title_blocks: Any) -> list[dict]:
    if not isinstance(title_blocks, list):
        return []

    normalized = []
    for block in title_blocks:
        if not isinstance(block, dict):
            continue
        normalized.append(
            {
                "text": str(block.get("text", "")).strip() or "Word",
                "font_family": str(block.get("font_family", "Impact, Arial Black, sans-serif")),
                "font_size": int(block.get("font_size", 40)),
                "color": str(block.get("color", "#ffffff")),
                "stroke_color": str(block.get("stroke_color", "#000000")),
                "stroke_width": int(block.get("stroke_width", 2)),
            }
        )

    return normalized


def ensure_clip_defaults(clip: dict, index: int) -> dict:
    name = clip.get("name") or f"Clip {index + 1}"
    return {
        "name": name,
        "url": clip.get("url"),
        "local_file": clip.get("local_file"),
        "preview_url": clip.get("preview_url"),
        "rank_text": clip.get("rank_text", ""),        # ← no longer force-overrides
        "rank_color": clip.get("rank_color", "#ffe600"),
        "rank_stroke_color": clip.get("rank_stroke_color", "#000000"),
        "rank_stroke_width": int(clip.get("rank_stroke_width", 2)),
        "rank_font_size": int(clip.get("rank_font_size", 58)),
        "intro_text": str(clip.get("intro_text", "") or ""),
        "intro_tts_path": str(clip.get("intro_tts_path", "") or ""),
        "duck_original_audio": bool(clip.get("duck_original_audio", True)),
    }


def create_project(project_name: str) -> dict:
    ensure_data_files()

    safe_name = sanitize_project_name(project_name)
    folder = project_folder_path(safe_name)

    if os.path.exists(folder):
        raise FileExistsError(f"Project already exists: {safe_name}")

    ensure_project_structure(safe_name)

    project_data = json.loads(json.dumps(DEFAULT_PROJECT_STATE))
    project_data["project_name"] = safe_name
    write_json(project_json_path(safe_name), project_data)
    write_json(project_history_path(safe_name), [])
    return project_data


def list_projects() -> list:
    ensure_data_files()
    items = []

    for name in os.listdir(PROJECTS_ROOT):
        folder = os.path.join(PROJECTS_ROOT, name)
        project_file = os.path.join(folder, "project.json")

        if os.path.isdir(folder) and os.path.exists(project_file):
            data = read_json(project_file, {})
            items.append(
                {
                    "project_name": data.get("project_name", name),
                    "folder_name": name,
                    "path": folder,
                }
            )

    items.sort(key=lambda x: x["project_name"].lower())
    return items


def build_project_clips_with_preview(project_name: str, urls: list[str], existing_clips: list | None = None) -> list[dict]:
    clips = []
    input_dir = project_input_clips_path(project_name)
    existing_clips = existing_clips or []

    for i, url in enumerate(urls):
        local_filename = None
        preview_url = None

        expected_base = f"clip_{i + 1:02d}"
        if os.path.isdir(input_dir):
            for file_name in os.listdir(input_dir):
                file_root, _ = os.path.splitext(file_name)
                if file_root == expected_base:
                    local_filename = file_name
                    preview_url = f"/api/projects/{sanitize_project_name(project_name)}/files/input_clips/{file_name}"
                    break

        existing = existing_clips[i] if i < len(existing_clips) and isinstance(existing_clips[i], dict) else {}

        clip = ensure_clip_defaults(
            {
                "name": existing.get("name", f"Clip {i + 1}"),
                "url": url,
                "local_file": local_filename,
                "preview_url": preview_url,
                "rank_text": existing.get("rank_text", ""),
                "rank_color": existing.get("rank_color", "#ffe600"),
                "rank_stroke_color": existing.get("rank_stroke_color", "#000000"),
                "rank_stroke_width": existing.get("rank_stroke_width", 2),
                "rank_font_size": existing.get("rank_font_size", 58),
                "intro_text": existing.get("intro_text", ""),
                "intro_tts_path": existing.get("intro_tts_path", ""),
                "duck_original_audio": existing.get("duck_original_audio", True),
            },
            i
        )
        clips.append(clip)

    return clips


def load_project_state(project_name: str) -> dict:
    ensure_data_files()

    safe_name = sanitize_project_name(project_name)
    ensure_project_structure(safe_name)

    data = read_json(project_json_path(safe_name), json.loads(json.dumps(DEFAULT_PROJECT_STATE)))
    merged = json.loads(json.dumps(DEFAULT_PROJECT_STATE))
    merged.update(data)
    merged["project_name"] = safe_name

    merged["title_text"] = str(merged.get("title_text", "") or "")
    merged["title_blocks"] = normalize_title_blocks(merged.get("title_blocks", []))
    merged["overlay_image_path"] = str(merged.get("overlay_image_path", "") or "")
    merged["overlay_updated_at"] = str(merged.get("overlay_updated_at", "") or "")

    urls = merged.get("urls", [])
    clips = merged.get("clips", [])

    if not isinstance(urls, list):
        urls = []

    if not isinstance(clips, list):
        clips = []

    normalized_clips = []
    for i, clip in enumerate(clips):
        normalized = ensure_clip_defaults(clip, i)

        stored_rank = (normalized.get("rank_text") or "").strip()
        if re.fullmatch(r"\d+\.", stored_rank):
            normalized["rank_text"] = ""

        local_file = normalized.get("local_file")
        if local_file:
            local_path = os.path.join(project_input_clips_path(safe_name), local_file)
            normalized["preview_url"] = f"/api/projects/{safe_name}/files/input_clips/{local_file}" if os.path.exists(local_path) else None

        normalized_clips.append(normalized)
    return merged


def save_project_state(project_name: str, state: dict) -> None:
    ensure_data_files()

    safe_name = sanitize_project_name(project_name)
    ensure_project_structure(safe_name)

    merged = json.loads(json.dumps(DEFAULT_PROJECT_STATE))
    merged.update(state)
    merged["project_name"] = safe_name
    merged["title_text"] = str(merged.get("title_text", "") or "")
    merged["title_blocks"] = normalize_title_blocks(merged.get("title_blocks", []))
    merged["overlay_image_path"] = str(merged.get("overlay_image_path", "") or "")
    merged["overlay_updated_at"] = str(merged.get("overlay_updated_at", "") or "")

    clips = merged.get("clips", [])
    if not isinstance(clips, list):
        clips = []

    cleaned_clips = []
    for i, c in enumerate(clips):
        normalized = ensure_clip_defaults(c, i)

        stored_rank = (normalized.get("rank_text") or "").strip()
        if re.fullmatch(r"\d+\.", stored_rank):
            normalized["rank_text"] = ""

        cleaned_clips.append(normalized)

    merged["clips"] = cleaned_clips

    write_json(project_json_path(safe_name), merged)


def delete_project(project_name: str) -> bool:
    safe_name = sanitize_project_name(project_name)
    folder = project_folder_path(safe_name)

    if not os.path.exists(folder):
        return False

    shutil.rmtree(folder, ignore_errors=True)
    return True


def load_project_history(project_name: str) -> list:
    safe_name = sanitize_project_name(project_name)
    ensure_project_structure(safe_name)

    data = read_json(project_history_path(safe_name), [])
    if not isinstance(data, list):
        return []
    return data


def save_project_history(project_name: str, items: list) -> None:
    safe_name = sanitize_project_name(project_name)
    ensure_project_structure(safe_name)
    write_json(project_history_path(safe_name), items)


def add_project_history_item(project_name: str, item: dict) -> None:
    items = load_project_history(project_name)
    items.insert(0, item)
    save_project_history(project_name, items)


def update_latest_project_history_item(project_name: str, item: dict) -> None:
    items = load_project_history(project_name)
    if not items:
        return

    items[0].update(item)
    save_project_history(project_name, items)


def delete_project_history_item(project_name: str, index: int) -> bool:
    items = load_project_history(project_name)
    if index < 0 or index >= len(items):
        return False

    item = items[index]
    file_path = item.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    del items[index]
    save_project_history(project_name, items)
    return True


def move_clip(project_name: str, index: int, direction: str) -> bool:
    state = load_project_state(project_name)
    clips = state.get("clips", [])

    if not isinstance(clips, list):
        return False
    if index < 0 or index >= len(clips):
        return False

    if direction == "up" and index > 0:
        clips[index - 1], clips[index] = clips[index], clips[index - 1]
    elif direction == "down" and index < len(clips) - 1:
        clips[index], clips[index + 1] = clips[index + 1], clips[index]  # ← fixed swap
    else:
        return False

    state["clips"] = clips
    save_project_state(project_name, state)
    return True


def delete_clip(project_name: str, index: int) -> bool:
    state = load_project_state(project_name)
    clips = state.get("clips", [])

    if not isinstance(clips, list):
        return False
    if index < 0 or index >= len(clips):
        return False

    del clips[index]
    state["clips"] = clips
    save_project_state(project_name, state)
    return True