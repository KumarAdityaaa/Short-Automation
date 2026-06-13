import os
import subprocess
import sys

from ranker import load_selections


def get_video_duration(ffprobe_path: str, video_path: str) -> float:
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def escape_drawtext_text(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", r"\'")
    text = text.replace(",", r"\,")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    return text


def make_segment(
    ffmpeg_path: str,
    input_path: str,
    tts_path: str,
    output_path: str,
    title: str,
    rank_num: int,
    width: int,
    height: int,
    fps: int
) -> None:
    safe_title = escape_drawtext_text(title)
    rank_text = f"#{rank_num}"

    vf = (
        f"scale='if(gt(a,{width}/{height}),{width},-2)':'if(gt(a,{width}/{height}),-2,{height})',"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"drawtext=text='{safe_title}':fontcolor=white:fontsize=48:"
        f"x=(w-text_w)/2:y=40:box=1:boxcolor=black@0.45:boxborderw=20,"
        f"drawtext=text='{rank_text}':fontcolor=yellow:fontsize=72:"
        f"x=60:y=120:box=1:boxcolor=black@0.45:boxborderw=18"
    )

    has_tts = os.path.exists(tts_path)

    if has_tts:
        cmd = [
            ffmpeg_path,
            "-y",
            "-i", input_path,
            "-i", tts_path,
            "-filter_complex",
            "[0:a]volume=1.0[base];"
            "[1:a]volume=1.8[tts];"
            "[base][tts]amix=inputs=2:duration=first:dropout_transition=0[mix]",
            "-vf", vf,
            "-map", "0:v:0",
            "-map", "[mix]",
            "-r", str(fps),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-ac", "2",
            "-ar", "48000",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]
    else:
        cmd = [
            ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vf", vf,
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-r", str(fps),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-ac", "2",
            "-ar", "48000",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Failed to create segment: {input_path}")
        lines = result.stderr.strip().splitlines()
        for line in lines[-25:]:
            print("   ", line)
        sys.exit(1)


def concat_segments(ffmpeg_path: str, concat_file: str, output_path: str) -> None:
    cmd = [
        ffmpeg_path,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("[ERROR] Failed to concat final short.")
        lines = result.stderr.strip().splitlines()
        for line in lines[-20:]:
            print("   ", line)
        sys.exit(1)


def compose(config: dict) -> None:
    ffmpeg_path = config["ffmpeg_path"]
    ffprobe_path = config["ffprobe_path"]
    output_dir = config["output_dir"]
    output_name = config["compose"]["output_name"]
    title = config["ranking"]["title"]
    width, height = config["video"]["resolution"]
    fps = config["video"]["fps"]
    tts_cache_dir = config["tts_cache_dir"]

    selected_clips = load_selections()
    if not selected_clips:
        print("[ERROR] No selections found in selections.json.")
        sys.exit(1)

    for clip_path in selected_clips:
        if not os.path.exists(clip_path):
            print(f"[ERROR] Selected clip not found: {clip_path}")
            sys.exit(1)

    temp_dir = os.path.join(output_dir, "temp_segments")
    os.makedirs(temp_dir, exist_ok=True)

    concat_file = os.path.join(output_dir, "concat_list.txt")
    final_output = os.path.join(output_dir, output_name)

    total_clips = len(selected_clips)

    print("\n[INFO] Creating normalized segments...")

    segment_paths = []
    for idx, clip_path in enumerate(selected_clips):
        rank_num = total_clips - idx
        segment_name = f"segment_{idx + 1:02d}.mp4"
        segment_path = os.path.join(temp_dir, segment_name)
        tts_path = os.path.join(tts_cache_dir, f"number_{rank_num}.wav")

        print(f"[INFO] Segment {idx + 1}/{total_clips}: {os.path.basename(clip_path)} -> rank #{rank_num}")

        make_segment(
            ffmpeg_path=ffmpeg_path,
            input_path=clip_path,
            tts_path=tts_path,
            output_path=segment_path,
            title=title,
            rank_num=rank_num,
            width=width,
            height=height,
            fps=fps,
        )

        if not os.path.exists(segment_path):
            print(f"[ERROR] Segment file not created: {segment_path}")
            sys.exit(1)

        segment_paths.append(segment_path)

    with open(concat_file, "w", encoding="utf-8") as f:
        for segment_path in segment_paths:
            f.write(f"file '{os.path.abspath(segment_path).replace(os.sep, '/')}'\n")

    print("[INFO] Concatenating final short...")
    concat_segments(ffmpeg_path, concat_file, final_output)

    if not os.path.exists(final_output):
        print("[ERROR] Final output was not created.")
        sys.exit(1)

    duration = get_video_duration(ffprobe_path, final_output)
    if duration <= 0:
        print("[WARN] Final short created, but duration could not be verified.")
    else:
        print(f"[OK] Final short duration: {duration:.2f}s")

    print(f"[OK] Final short saved to: {final_output}")