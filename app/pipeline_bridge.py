import glob
import json
import os
import subprocess
import sys


from app.storage import (
    sanitize_project_name,
    project_output_path,
    project_input_clips_path,
    project_folder_path,
)


CONFIG_PATH = "config.json"
SELECTIONS_PATH = "selections.json"
MAIN_SCRIPT = "main.py"


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("config.json not found")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def project_tts_cache_path(project_name: str) -> str:
    safe_name = sanitize_project_name(project_name)
    return os.path.join(project_folder_path(safe_name), "tts_cache")


def update_config_from_project_state(project_name: str, state: dict) -> dict:
    config = load_config()

    safe_project = sanitize_project_name(project_name)
    urls = state.get("urls", [])
    title_text = state.get("title_text", "") or ""
    raw_title_blocks = state.get("title_blocks", []) or []
    clips = state.get("clips", []) or []
    overlay_image_path = state.get("overlay_image_path", "") or ""
    overlay_updated_at = state.get("overlay_updated_at", "") or ""

    input_dir = project_input_clips_path(safe_project)
    output_dir = project_output_path(safe_project)
    tts_cache_dir = project_tts_cache_path(safe_project)

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(tts_cache_dir, exist_ok=True)

    normalized_title_blocks = []
    if isinstance(raw_title_blocks, list):
        for block in raw_title_blocks:
            if not isinstance(block, dict):
                continue
            normalized_title_blocks.append({
                "text": block.get("text", "") or "",
                "font_family": block.get("font_family", "") or "",
                "font_size": int(block.get("font_size", 40) or 40),
                "color": block.get("color", "#ffffff") or "#ffffff",
                "stroke_color": block.get("stroke_color", "#000000") or "#000000",
                "stroke_width": int(block.get("stroke_width", 2) or 2),
            })

    config["input_dir"] = input_dir
    config["output_dir"] = output_dir
    config["tts_cache_dir"] = tts_cache_dir
    config["urls"] = urls
    config["overlay"] = {
    "enabled": bool(overlay_image_path and os.path.exists(overlay_image_path)),
    "image_path": overlay_image_path,
    "updated_at": overlay_updated_at,
    }   

    if "ranking" not in config or not isinstance(config["ranking"], dict):
        config["ranking"] = {}

    config["ranking"]["title"] = title_text
    config["ranking"]["title_blocks"] = normalized_title_blocks
    config["ranking"]["count"] = len(clips) if clips else config["ranking"].get("count", 0)

    save_config(config)
    return config


def clear_project_input_clips(project_name: str) -> None:
    input_dir = project_input_clips_path(project_name)
    os.makedirs(input_dir, exist_ok=True)

    for path in glob.glob(os.path.join(input_dir, "*")):
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def download_project_clips(project_name: str, urls: list[str]) -> tuple[bool, str]:
    if not urls:
        return False, "No URLs provided."

    input_dir = project_input_clips_path(project_name)
    os.makedirs(input_dir, exist_ok=True)

    clear_project_input_clips(project_name)

    for i, url in enumerate(urls, start=1):
        output_template = os.path.join(input_dir, f"clip_{i:02d}.%(ext)s")
        cookies_path = r"C:\Users\kumar\Downloads\cookies.txt"
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--js-runtimes", r"deno:C:\Users\kumar\.deno\bin\deno.exe",
            "-f", "18/best",
            "--cookies", cookies_path,
            "-o",
            output_template,
            url,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            error_message = stderr or stdout or f"yt-dlp failed for URL #{i}"
            print(f"[ERROR] download_project_clips URL #{i}: {error_message}")
            return False, error_message

    return True, "Download complete."


def resolve_project_clip_path(project_name: str, clip: dict, index: int) -> str:
    input_dir = project_input_clips_path(project_name)

    local_file = (clip.get("local_file") or "").strip()
    preview_url = (clip.get("preview_url") or "").strip()
    name = (clip.get("name") or "").strip()

    if local_file:
        candidate = os.path.join(input_dir, local_file)
        if os.path.exists(candidate):
            return candidate

    if preview_url:
        preview_name = os.path.basename(preview_url.split("?")[0])
        candidate = os.path.join(input_dir, preview_name)
        if os.path.exists(candidate):
            return candidate

    if name:
        candidate = os.path.join(input_dir, name)
        if os.path.exists(candidate):
            return candidate

    all_video_files = sorted(
        glob.glob(os.path.join(input_dir, "*.mp4")) +
        glob.glob(os.path.join(input_dir, "*.mkv")) +
        glob.glob(os.path.join(input_dir, "*.webm")) +
        glob.glob(os.path.join(input_dir, "*.mov"))
    )
    if 0 <= index < len(all_video_files):
        return all_video_files[index]

    return ""


def write_selections_from_project_state(project_name: str, state: dict) -> None:
    clips = state.get("clips", []) or []

    selected_clips = []
    for index, clip in enumerate(clips):
        clip_path = resolve_project_clip_path(project_name, clip, index)

        selected_clips.append({
            "clip_path": clip_path,
            "intro_text": clip.get("intro_text", "") or "",
            "intro_tts_path": clip.get("intro_tts_path", "") or "",
            "duck_original_audio": bool(clip.get("duck_original_audio", True)),
            "rank_text": clip.get("rank_text", "") or "",
            "rank_color": clip.get("rank_color", "#ffe600") or "#ffe600",
            "rank_stroke_color": clip.get("rank_stroke_color", "#000000") or "#000000",
            "rank_stroke_width": int(clip.get("rank_stroke_width", 2) or 2),
            "rank_font_size": int(clip.get("rank_font_size", 58) or 58),
        })

    with open(SELECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump({"selected_clips": selected_clips}, f, indent=2)


def run_main_py() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, MAIN_SCRIPT],
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as e:
        return False, f"Failed to start main.py: {e}"

    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        return False, stderr or stdout or f"main.py exited with code {result.returncode}"

    return True, result.stdout.strip()


def run_full_pipeline_for_project(project_name: str, state: dict) -> tuple[bool, str]:
    config = update_config_from_project_state(project_name, state)
    write_selections_from_project_state(project_name, state)

    ok, message = run_main_py()
    if not ok:
        return False, message

    final_path = os.path.join(config["output_dir"], config["compose"]["output_name"])
    if not os.path.exists(final_path):
        return False, f"Expected output not found: {final_path}"

    return True, final_path