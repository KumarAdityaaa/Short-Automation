import os
import json
import subprocess


SELECTIONS_PATH = "selections.json"


def get_video_info(filepath: str) -> dict:
    """Use ffprobe to get duration and file size of a video."""
    cmd = [
        "ffprobe",
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


def run_ranker(input_dir: str) -> list:
    """
    Show all clips with metadata, let user pick and order them.
    Returns ordered list of selected file paths.
    """
    clips = list_clips(input_dir)

    if not clips:
        print("[ERROR] No .mp4 files found in input_clips/")
        return []

    print("\n=== Available Clips ===\n")
    for i, path in enumerate(clips):
        info = get_video_info(path)
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

    save_selections(ordered_paths)
    return ordered_paths


def save_selections(ordered_paths: list) -> None:
    data = {"selected_clips": ordered_paths}
    with open(SELECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\n[OK] Selection saved to {SELECTIONS_PATH}")


def load_selections() -> list:
    if not os.path.exists(SELECTIONS_PATH):
        print(f"[ERROR] {SELECTIONS_PATH} not found. Run the ranker first.")
        return []
    with open(SELECTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("selected_clips", [])