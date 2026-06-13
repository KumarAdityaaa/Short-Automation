import json
import os
import sys

from downloader import download_clips
from ranker import run_ranker
from tts import generate_tts_files, verify_tts_files
from composer import compose

CONFIG_PATH = "config.json"


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        print(f"[ERROR] Config file not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] config.json is not valid JSON: {e}")
            sys.exit(1)

    return config


def validate_config(config: dict) -> None:
    required_keys = [
        "input_dir",
        "output_dir",
        "tts_cache_dir",
        "ffmpeg_path",
        "ffprobe_path",
        "urls",
        "ranking",
        "video",
        "compose"
    ]

    for key in required_keys:
        if key not in config:
            print(f"[ERROR] Missing required key in config.json: '{key}'")
            sys.exit(1)

    for key in ["ffmpeg_path", "ffprobe_path"]:
        if not os.path.exists(config[key]):
            print(f"[ERROR] File not found: {config[key]}")
            sys.exit(1)

    print("[OK] config.json loaded and validated.")


def ensure_dirs(config: dict) -> None:
    for key in ["input_dir", "output_dir", "tts_cache_dir"]:
        path = config[key]
        os.makedirs(path, exist_ok=True)
        print(f"[OK] Directory ready: {path}/")


def check_ffmpeg_tools(config: dict) -> None:
    ffmpeg_path = config["ffmpeg_path"]
    ffprobe_path = config["ffprobe_path"]

    if not os.path.isfile(ffmpeg_path):
        print(f"[ERROR] ffmpeg.exe not found: {ffmpeg_path}")
        sys.exit(1)

    if not os.path.isfile(ffprobe_path):
        print(f"[ERROR] ffprobe.exe not found: {ffprobe_path}")
        sys.exit(1)

    print(f"[OK] ffmpeg executable found: {ffmpeg_path}")
    print(f"[OK] ffprobe executable found: {ffprobe_path}")


def main():
    print("=== Shorts Pipeline ===")

    config = load_config(CONFIG_PATH)
    validate_config(config)
    ensure_dirs(config)
    check_ffmpeg_tools(config)

    urls = config.get("urls", [])
    if not urls:
        print("[INFO] No URLs in config.json.")
        return

    downloaded = download_clips(urls, config["input_dir"], config["ffmpeg_path"])
    print(f"\n[DONE] {len(downloaded)}/{len(urls)} clips downloaded.")

    if not downloaded:
        print("[ERROR] No clips downloaded. Cannot proceed.")
        return

    selected = run_ranker(config["input_dir"])
    if not selected:
        print("[ERROR] No ranked selection created. Cannot proceed.")
        return

    count = config["ranking"]["count"]
    print(f"\n[INFO] Generating {count} TTS voice lines...")
    tts_paths = generate_tts_files(count, config["tts_cache_dir"])

    if not verify_tts_files(tts_paths, count):
        print("[ERROR] TTS verification failed.")
        return

    if config["compose"]["enabled"]:
        compose(config)
    else:
        print("[INFO] Composition disabled in config.")


if __name__ == "__main__":
    main()