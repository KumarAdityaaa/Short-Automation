import json
import os
import subprocess


DEFAULT_SELECTIONS_PATH = "selections.json"


def get_video_info(filepath: str, ffprobe_path: str | None = None) -> dict:
    """Use ffprobe to get duration and file size of a video."""
    probe_bin = ffprobe_path or "ffprobe"

    cmd = [
        probe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        filepath,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        return {"duration": "unknown", "size_mb": "unknown"}

    data = json.loads(result.stdout.decode(errors="replace"))
    fmt = data.get("format", {})
    duration_sec = float(fmt.get("duration", 0))
    size_bytes = int(fmt.get("size", 0))

    return {
        "duration": f"{duration_sec:.1f}s",
        "size_mb": f"{size_bytes / (1024 * 1024):.1f} MB",
    }


def list_clips(input_dir: str) -> list:
    """Return sorted list of .mp4 files in input_dir."""
    if not os.path.exists(input_dir):
        return []
    files = sorted([
        f for f in os.listdir(input_dir)
        if f.lower().endswith(".mp4")
    ])
    return [os.path.join(input_dir, f) for f in files]


def run_ranker(
    input_dir: str,
    ffprobe_path: str | None = None,
    selections_path: str = DEFAULT_SELECTIONS_PATH
) -> list:
    """
    Show all clips with metadata, let user pick and order them.
    Returns ordered list of selected clip dicts.
    """
    clips = list_clips(input_dir)

    if not clips:
        print("[ERROR] No .mp4 files found in input_clips/")
        return []

    print("\n=== Available Clips ===\n")
    for i, path in enumerate(clips):
        info = get_video_info(path, ffprobe_path=ffprobe_path)
        print(f"  [{i+1}] {os.path.basename(path)}")
        print(f"       Duration: {info['duration']}  |  Size: {info['size_mb']}")

    print()
    print("Enter clip numbers in order WORST to BEST (last number = #1 best).")
    print("Example: 3 1 2 4 5  (clip 3 plays first as #5, clip 5 plays last as #1)")
    print("Press Enter with no input to use all clips in default order.\n")

    raw = input("Your selection: ").strip()

    if raw == "":
        selected = list(range(1, len(clips) + 1))
        print("[INFO] No input — using all clips in default order.")
    else:
        try:
            selected = [int(x) for x in raw.split()]
        except ValueError:
            print("[ERROR] Invalid input. Only enter numbers separated by spaces.")
            return []

        for n in selected:
            if n < 1 or n > len(clips):
                print(f"[ERROR] '{n}' is out of range. Valid range is 1 to {len(clips)}.")
                return []

    ordered_paths = [clips[n - 1] for n in selected]

    print("\n=== Your Selection (worst to best) ===\n")
    rank = len(ordered_paths)
    for path in ordered_paths:
        print(f"  #{rank} -> {os.path.basename(path)}")
        rank -= 1

    selected_clips = [
        {
            "clip_path": path,
            "intro_text": "",
            "intro_tts_path": "",
            "duck_original_audio": True,
        }
        for path in ordered_paths
    ]

    save_selections(selected_clips, selections_path=selections_path)
    return selected_clips


def save_selections(selected_clips: list, selections_path: str = DEFAULT_SELECTIONS_PATH) -> None:
    data = {"selected_clips": selected_clips}
    os.makedirs(os.path.dirname(os.path.abspath(selections_path)), exist_ok=True)

    with open(selections_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\n[OK] Selection saved to {selections_path}")


def load_selections(selections_path: str = DEFAULT_SELECTIONS_PATH) -> list:
    if not os.path.exists(selections_path):
        print(f"[ERROR] {selections_path} not found. Run the ranker first.")
        return []

    with open(selections_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    selected_clips = data.get("selected_clips", [])

    if not isinstance(selected_clips, list):
        return []

    normalized = []
    for item in selected_clips:
        if isinstance(item, str):
            normalized.append({
                "clip_path": item,
                "intro_text": "",
                "intro_tts_path": "",
                "duck_original_audio": True,
            })
        elif isinstance(item, dict):
            normalized.append({
                "clip_path": item.get("clip_path") or item.get("path") or "",
                "intro_text": item.get("intro_text", ""),
                "intro_tts_path": item.get("intro_tts_path", ""),
                "duck_original_audio": item.get("duck_original_audio", True),
                "rank_text": item.get("rank_text", ""),
                "rank_color": item.get("rank_color", "#ffe600"),
                "rank_stroke_color": item.get("rank_stroke_color", "#000000"),
                "rank_stroke_width": item.get("rank_stroke_width", 2),
                "rank_font_size": item.get("rank_font_size", 58),
            })

    return normalized