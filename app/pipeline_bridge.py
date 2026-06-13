import glob
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

from app.storage import (
    sanitize_project_name,
    project_output_path,
    project_input_clips_path,
)


CONFIG_PATH = "config.json"
MAIN_SCRIPT = "main.py"
PIPELINE_OUTPUT_PATH = os.path.join("output", "final_short.mp4")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("config.json not found")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def update_config_from_project_state(state: dict) -> None:
    config = load_config()

    urls = state.get("urls", [])
    title = state.get("title_text", "Top 5 Moments")

    config["urls"] = urls

    if "ranking" not in config or not isinstance(config["ranking"], dict):
        config["ranking"] = {}

    config["ranking"]["title"] = title
    save_config(config)


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

        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
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
            return False, stderr or stdout or f"yt-dlp failed for URL #{i}"

    return True, "Download complete."


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


def copy_output_to_project(project_name: str, title_text: str) -> str:
    if not os.path.exists(PIPELINE_OUTPUT_PATH):
        raise FileNotFoundError(f"Expected output not found: {PIPELINE_OUTPUT_PATH}")

    safe_project = sanitize_project_name(project_name)
    output_dir = project_output_path(safe_project)
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title_text).strip()
    safe_title = safe_title.replace(" ", "_") or "short"

    filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    destination = os.path.join(output_dir, filename)

    shutil.copy2(PIPELINE_OUTPUT_PATH, destination)
    return destination


def run_full_pipeline_for_project(project_name: str, state: dict) -> tuple[bool, str]:
    update_config_from_project_state(state)

    ok, message = run_main_py()
    if not ok:
        return False, message

    try:
        final_path = copy_output_to_project(project_name, state.get("title_text", "short"))
        return True, final_path
    except Exception as e:
        return False, str(e)