import os
import soundfile as sf


TTS_VOICE = "af_heart"


def get_voice_lines(count: int) -> dict:
    """
    Returns a dict mapping rank number to the spoken line text.
    e.g. {5: "Number 5", 4: "Number 4", ..., 1: "Number 1!"}
    """
    lines = {}
    for i in range(count, 0, -1):
        if i == 1:
            lines[i] = "Number 1!"
        else:
            lines[i] = f"Number {i}"
    return lines


def generate_tts_files(count: int, cache_dir: str) -> dict:
    """
    Generates a .wav file for each ranking position voice line.
    Skips generation if the file already exists (cache).
    Returns dict mapping rank number to wav file path.
    """
    os.makedirs(cache_dir, exist_ok=True)

    # Import here so startup is fast if TTS is not needed
    from kokoro import KPipeline

    print("[INFO] Loading Kokoro TTS model (first run downloads ~500MB)...")
    pipeline = KPipeline(lang_code="a")  # "a" = American English

    voice_lines = get_voice_lines(count)
    output_paths = {}

    for rank, text in voice_lines.items():
        out_path = os.path.join(cache_dir, f"number_{rank}.wav")

        if os.path.exists(out_path):
            print(f"[CACHE] {out_path} already exists, skipping.")
            output_paths[rank] = out_path
            continue

        print(f"[INFO] Generating TTS: '{text}' -> {out_path}")

        samples = []
        for result in pipeline(text, voice=TTS_VOICE):
            if result.audio is not None:
                samples.append(result.audio)

        if not samples:
            print(f"[ERROR] TTS produced no audio for: '{text}'")
            continue

        import numpy as np
        audio = np.concatenate(samples)
        sf.write(out_path, audio, 24000)
        print(f"[OK] Saved: {out_path}")
        output_paths[rank] = out_path

    return output_paths


def verify_tts_files(output_paths: dict, count: int) -> bool:
    """Check all expected files exist and are non-empty."""
    for rank in range(count, 0, -1):
        path = output_paths.get(rank)
        if not path or not os.path.exists(path):
            print(f"[ERROR] Missing TTS file for rank {rank}")
            return False
        if os.path.getsize(path) == 0:
            print(f"[ERROR] TTS file is empty for rank {rank}: {path}")
            return False
    print(f"[OK] All {count} TTS voice files verified.")
    return True