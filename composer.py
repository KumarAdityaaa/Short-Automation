import hashlib
import os
import subprocess

from ranker import load_selections
from tts import generate_custom_tts


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


def get_audio_duration(ffprobe_path: str, audio_path: str) -> float:
    if not audio_path or not os.path.exists(audio_path):
        return 0.0
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def has_audio_stream(ffprobe_path: str, input_path: str) -> bool:
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        input_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return bool((result.stdout or "").strip())


def escape_drawtext_text(text: str) -> str:
    text = str(text or "")
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", r"\'")
    text = text.replace(",", r"\,")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    text = text.replace("%", r"\%")
    return text


def escape_fontfile_path(path: str) -> str:
    value = str(path or "").strip()
    value = value.replace("\\", "/")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value


def safe_filename_from_text(text: str) -> str:
    digest = hashlib.md5(text.strip().encode("utf-8")).hexdigest()[:12]
    return f"custom_{digest}.wav"


def hex_to_ffmpeg_color(value: str, fallback: str = "white") -> str:
    value = (value or "").strip()
    if not value:
        return fallback
    if value.startswith("#") and len(value) in (7, 9):
        return value
    return fallback


def resolve_fontfile(font_family: str) -> str | None:
    family = (font_family or "").lower()

    candidates = [
        ("impact", r"C:\Windows\Fonts\impact.ttf"),
        ("arial black", r"C:\Windows\Fonts\ariblk.ttf"),
        ("arial", r"C:\Windows\Fonts\arial.ttf"),
        ("verdana", r"C:\Windows\Fonts\verdana.ttf"),
        ("tahoma", r"C:\Windows\Fonts\tahoma.ttf"),
        ("trebuchet ms", r"C:\Windows\Fonts\trebuc.ttf"),
        ("georgia", r"C:\Windows\Fonts\georgia.ttf"),
        ("times new roman", r"C:\Windows\Fonts\times.ttf"),
        ("courier new", r"C:\Windows\Fonts\cour.ttf"),
    ]

    for token, path in candidates:
        if token in family and os.path.exists(path):
            return path

    return None


def resolve_clip_tts_path(clip: dict, rank_num: int, tts_cache_dir: str) -> str | None:
    intro_text = (clip.get("intro_text") or "").strip()
    intro_tts_path = (clip.get("intro_tts_path") or "").strip()

    if intro_text:
        if not intro_tts_path:
            intro_tts_path = os.path.join(tts_cache_dir, safe_filename_from_text(intro_text))
            clip["intro_tts_path"] = intro_tts_path

        print(f"[INFO] Generating custom intro TTS -> {intro_tts_path}")
        generated = generate_custom_tts(intro_text, intro_tts_path)
        return generated if generated and os.path.exists(generated) else None

    numbered_tts = os.path.join(tts_cache_dir, f"number_{rank_num}.wav")
    if os.path.exists(numbered_tts):
        return numbered_tts

    return None


def estimate_text_width(text: str, font_size: int) -> int:
    clean = str(text or "").strip()
    if not clean:
        return 0
    return max(40, int(len(clean) * font_size * 0.58))


def build_title_drawtext(title_blocks: list[dict]) -> str:
    filters: list[str] = []
    row_1 = title_blocks[:2]
    row_2 = title_blocks[2:]

    start_y = 22
    row_gap = 6

    def add_row(blocks: list[dict], y: int) -> None:
        nonlocal filters
        if not blocks:
            return

        gap = 10
        blocks_with_text: list[tuple[dict, str, int, int, str | None]] = []

        for block in blocks:
            text_raw = block.get("text", "")
            text = escape_drawtext_text(text_raw)
            if not text:
                continue

            font_size = int(block.get("font_size", 40))
            est_width = estimate_text_width(text_raw, font_size)
            fontfile = resolve_fontfile(block.get("font_family", ""))

            blocks_with_text.append((block, text, font_size, est_width, fontfile))

        if not blocks_with_text:
            return

        total_width = sum(item[3] for item in blocks_with_text) + gap * (len(blocks_with_text) - 1)
        offset = 0

        for block, text, font_size, est_width, fontfile in blocks_with_text:
            color = hex_to_ffmpeg_color(block.get("color"), "white")
            stroke_color = hex_to_ffmpeg_color(block.get("stroke_color"), "black")
            stroke_width = int(block.get("stroke_width", 2))

            parts = [
                "drawtext=",
                f"text='{text}'",
                f"fontcolor={color}",
                f"fontsize={font_size}",
                f"bordercolor={stroke_color}",
                f"borderw={stroke_width}",
                f"x=(w-{total_width})/2+{offset}",
                f"y={y}",
            ]

            if fontfile:
                parts.insert(2, f"fontfile='{escape_fontfile_path(fontfile)}'")

            filters.append(":".join(parts))
            offset += est_width + gap

    row1_max_font = max([int(b.get("font_size", 40)) for b in row_1], default=40)
    add_row(row_1, start_y)
    add_row(row_2, start_y + row1_max_font + row_gap)

    return ",".join(filters)


def build_rank_drawtext(clip: dict, rank_num: int) -> str:
    rank_text = escape_drawtext_text(clip.get("rank_text") or f"{rank_num}.")
    rank_color = hex_to_ffmpeg_color(clip.get("rank_color"), "#ffe600")
    rank_stroke_color = hex_to_ffmpeg_color(clip.get("rank_stroke_color"), "#000000")
    rank_stroke_width = int(clip.get("rank_stroke_width", 2))
    rank_font_size = 150

    print("[DEBUG] build_rank_drawtext rank_font_size =", rank_font_size)

    rank_fontfile = resolve_fontfile("impact") or resolve_fontfile("arial black") or resolve_fontfile("arial")

    parts = [
        "drawtext=",
        f"text='{rank_text}'",
        f"fontcolor={rank_color}",
        f"fontsize={rank_font_size}",
        f"bordercolor={rank_stroke_color}",
        f"borderw={rank_stroke_width}",
        "x=70",
        "y=300",
    ]

    if rank_fontfile:
        parts.insert(2, f"fontfile='{escape_fontfile_path(rank_fontfile)}'")

    return ":".join(parts)


def get_overlay_image_path(config: dict) -> str:
    overlay = config.get("overlay", {})
    if not isinstance(overlay, dict):
        return ""
    path = str(overlay.get("image_path", "") or "").strip()
    if path and os.path.exists(path):
        return path
    return ""


def build_video_filter(
    width: int,
    height: int,
    title_blocks: list[dict],
    clip: dict,
    rank_num: int,
    overlay_image_path: str = "",
) -> tuple[str, bool]:
    base = (
        "setpts=PTS-STARTPTS,"
        f"scale='if(gt(a,{width}/{height}),{width},-2)':'if(gt(a,{width}/{height}),-2,{height})',"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )

    # If PNG exists, we’ll use it for title only and draw rank via drawtext later.
    if overlay_image_path and os.path.exists(overlay_image_path):
        return base, True

    # No PNG: fall back to pure drawtext for both title + rank
    overlays: list[str] = []
    title_overlay = build_title_drawtext(title_blocks)
    if title_overlay:
        overlays.append(title_overlay)

    overlays.append(build_rank_drawtext(clip, rank_num))
    return base + "," + ",".join(overlays), False


def build_audio_filter_for_segment(
    intro_duration: float,
    has_tts: bool,
    duck_original_audio: bool,
    source_has_audio: bool,
    tts_input_index: int | None,
) -> tuple[str, str]:
    intro_ms = int(round(intro_duration * 1000))

    if source_has_audio and has_tts and intro_duration > 0 and tts_input_index is not None:
        base_volume = 0.35 if duck_original_audio else 1.0
        tts_label = f"[{tts_input_index}:a]"
        filter_complex = (
            "[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"volume={base_volume},"
            f"adelay={intro_ms}|{intro_ms},"
            "asetpts=PTS-STARTPTS[base_delayed];"
            f"{tts_label}aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            "volume=1.8,asetpts=PTS-STARTPTS[tts];"
            "[base_delayed][tts]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]"
        )
        return filter_complex, "[aout]"

    if source_has_audio and not has_tts:
        filter_complex = (
            "[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            "asetpts=PTS-STARTPTS[aout]"
        )
        return filter_complex, "[aout]"

    if not source_has_audio and has_tts and intro_duration > 0 and tts_input_index is not None:
        tts_label = f"[{tts_input_index}:a]"
        filter_complex = (
            f"{tts_label}aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            "volume=1.8,asetpts=PTS-STARTPTS[aout]"
        )
        return filter_complex, "[aout]"

    filter_complex = "anullsrc=channel_layout=stereo:sample_rate=48000[aout]"
    return filter_complex, "[aout]"


def make_segment(
    ffmpeg_path: str,
    ffprobe_path: str,
    input_path: str,
    tts_path: str | None,
    output_path: str,
    title_blocks: list[dict],
    clip: dict,
    rank_num: int,
    width: int,
    height: int,
    fps: int,
    duck_original_audio: bool = True,
    overlay_image_path: str = "",
) -> None:
    vf, use_overlay_image = build_video_filter(
        width=width,
        height=height,
        title_blocks=title_blocks,
        clip=clip,
        rank_num=rank_num,
        overlay_image_path=overlay_image_path,
    )

    source_has_audio = has_audio_stream(ffprobe_path, input_path)
    has_tts = bool(tts_path and os.path.exists(tts_path))
    intro_duration = get_audio_duration(ffprobe_path, tts_path) if has_tts else 0.0
    video_duration = get_video_duration(ffprobe_path, input_path)
    total_duration = video_duration + (intro_duration if has_tts and intro_duration > 0 else 0.0)

    cmd = [
        ffmpeg_path,
        "-y",
        "-i", input_path,
    ]

    # Input ordering:
    # 0: main video
    # 1: overlay PNG (if any)
    # 2 or 1: TTS audio (depending on overlay)
    if use_overlay_image:
        cmd += ["-i", overlay_image_path]

    tts_input_index: int | None = None
    if has_tts:
        tts_input_index = 2 if use_overlay_image else 1
        cmd += ["-i", tts_path]

    audio_filter_complex, audio_map = build_audio_filter_for_segment(
        intro_duration=intro_duration,
        has_tts=has_tts,
        duck_original_audio=duck_original_audio,
        source_has_audio=source_has_audio,
        tts_input_index=tts_input_index,
    )

    # Build video filter_complex
    if use_overlay_image:
        rank_expr = build_rank_drawtext(clip, rank_num)

        if has_tts and intro_duration > 0:
            video_filter_complex = (
                f"[0:v]{vf},tpad=start_duration={intro_duration}:start_mode=clone,setsar=1[basev];"
                f"[1:v]format=rgba[overlayv];"
                f"[basev][overlayv]overlay=0:0:format=auto[with_overlay];"
                f"[with_overlay]{rank_expr}[vout]"
            )
        else:
            video_filter_complex = (
                f"[0:v]{vf},setsar=1[basev];"
                f"[1:v]format=rgba[overlayv];"
                f"[basev][overlayv]overlay=0:0:format=auto[with_overlay];"
                f"[with_overlay]{rank_expr}[vout]"
            )
    else:
        if has_tts and intro_duration > 0:
            video_filter_complex = f"[0:v]{vf},tpad=start_duration={intro_duration}:start_mode=clone,setsar=1[vout]"
        else:
            video_filter_complex = f"[0:v]{vf},setsar=1[vout]"

    if total_duration <= 0:
        total_duration = None

    cmd += [
        "-filter_complex",
        video_filter_complex + ";" + audio_filter_complex,
        "-map", "[vout]",
        "-map", audio_map,
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-ar", "48000",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]

    if total_duration is not None:
        cmd += ["-t", f"{total_duration:.3f}"]

    cmd += [output_path]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Failed to create segment: {input_path}")
        lines = result.stderr.strip().splitlines()
        for line in lines[-50:]:
            print("   ", line)
        raise RuntimeError(f"Failed to create segment for input: {input_path}")


def concat_segments(ffmpeg_path: str, segment_paths: list[str], output_path: str) -> None:
    if not segment_paths:
        raise RuntimeError("No segment files to concatenate.")

    cmd = [ffmpeg_path, "-y"]

    for segment_path in segment_paths:
        cmd += ["-i", segment_path]

    concat_inputs = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(len(segment_paths)))
    filter_complex = f"{concat_inputs}concat=n={len(segment_paths)}:v=1:a=1[v][a]"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-ar", "48000",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("[ERROR] Failed to concat final short.")
        lines = result.stderr.strip().splitlines()
        for line in lines[-50:]:
            print("   ", line)
        raise RuntimeError("Failed to concat final short.")


def compose(config: dict) -> None:
    ffmpeg_path = config["ffmpeg_path"]
    ffprobe_path = config["ffprobe_path"]
    output_dir = config["output_dir"]
    output_name = config["compose"]["output_name"]
    width, height = config["video"]["resolution"]
    fps = config["video"]["fps"]
    tts_cache_dir = config["tts_cache_dir"]

    title_blocks = config.get("ranking", {}).get("title_blocks", [])
    if not isinstance(title_blocks, list):
        title_blocks = []

    overlay_image_path = get_overlay_image_path(config)
    if overlay_image_path:
        print(f"[INFO] Using saved preview overlay image: {overlay_image_path}")
    else:
        print("[INFO] No overlay image found. Falling back to drawtext rendering.")

    selected_clips = load_selections()
    if not selected_clips:
        raise RuntimeError("No selections found in selections.json.")

    normalized_clips: list[dict] = []
    for item in selected_clips:
        if isinstance(item, str):
            normalized_clips.append({
                "clip_path": item,
                "intro_text": "",
                "intro_tts_path": "",
                "duck_original_audio": True,
                "rank_text": "",
                "rank_color": "#ffe600",
                "rank_stroke_color": "#000000",
                "rank_stroke_width": 2,
                "rank_font_size": 58,
            })
        elif isinstance(item, dict):
            normalized_clips.append({
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
        else:
            raise RuntimeError(f"Unsupported clip entry in selections.json: {item}")

    for clip in normalized_clips:
        clip_path = clip["clip_path"]
        if not clip_path or not os.path.exists(clip_path):
            raise RuntimeError(f"Selected clip not found: {clip_path}")

    temp_dir = os.path.join(output_dir, "temp_segments")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(tts_cache_dir, exist_ok=True)

    final_output = os.path.join(output_dir, output_name)
    final_output_tmp = os.path.join(output_dir, f"__tmp__{output_name}")
    total_clips = len(normalized_clips)

    print("\n[INFO] Creating normalized segments...")

    segment_paths: list[str] = []
    for idx, clip in enumerate(normalized_clips):
        clip_path = clip["clip_path"]
        rank_num = total_clips - idx
        segment_name = f"segment_{idx + 1:02d}.mp4"
        segment_path = os.path.join(temp_dir, segment_name)

        tts_path = resolve_clip_tts_path(
            clip=clip,
            rank_num=rank_num,
            tts_cache_dir=tts_cache_dir,
        )

        duck_original_audio = bool(clip.get("duck_original_audio", True))

        print(f"[INFO] Segment {idx + 1}/{total_clips}: {os.path.basename(clip_path)} -> rank #{rank_num}")

        make_segment(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            input_path=clip_path,
            tts_path=tts_path,
            output_path=segment_path,
            title_blocks=title_blocks,
            clip=clip,
            rank_num=rank_num,
            width=width,
            height=height,
            fps=fps,
            duck_original_audio=duck_original_audio,
            overlay_image_path=overlay_image_path,
        )

        if not os.path.exists(segment_path):
            raise RuntimeError(f"Segment file not created: {segment_path}")

        segment_paths.append(segment_path)

    print("[INFO] Concatenating final short...")
    concat_segments(ffmpeg_path, segment_paths, final_output_tmp)

    if not os.path.exists(final_output_tmp):
        raise RuntimeError("Temporary final output was not created.")

    os.replace(final_output_tmp, final_output)

    duration = get_video_duration(ffprobe_path, final_output)
    if duration <= 0:
        print("[WARN] Final short created, but duration could not be verified.")
    else:
        print(f"[OK] Final short duration: {duration:.2f}s")

    print(f"[OK] Final short saved to: {final_output}")