import json
import os
import sys

from composer import compose


DEFAULT_CONFIG_PATH = "config.json"


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        print(f"[ERROR] Config file not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] config file is not valid JSON: {e}")
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
        "compose",
    ]

    for key in required_keys:
        if key not in config:
            print(f"[ERROR] Missing required key in config: '{key}'")
            sys.exit(1)

    for key in ["ffmpeg_path", "ffprobe_path"]:
        if not os.path.exists(config[key]):
            print(f"[ERROR] File not found: {config[key]}")
            sys.exit(1)

    print("[OK] Config loaded and validated.")


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


def resolve_config_path() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    return DEFAULT_CONFIG_PATH


def main():
    print("=== Shorts Pipeline ===")

    config_path = resolve_config_path()
    config = load_config(config_path)
    validate_config(config)
    ensure_dirs(config)
    check_ffmpeg_tools(config)

    if not config.get("compose", {}).get("enabled", False):
        print("[INFO] Composition disabled in config.")
        return

    project_dir = os.path.dirname(os.path.abspath(config_path))
    selections_path = os.path.join(project_dir, "selections.json")

    compose(config, selections_path=selections_path)


if __name__ == "__main__":
    main()