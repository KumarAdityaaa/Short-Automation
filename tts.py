import os
import soundfile as sf

TTS_VOICE = "af_heart"

def generate_custom_tts(text: str, out_path: str) -> str:
    """
    Generate a single TTS wav file for an arbitrary text line.
    Returns the output path. Uses simple caching: if the file
    already exists and is non-empty, it is reused.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"[CACHE] Custom TTS exists: {out_path}")
        return out_path

    if not text or not text.strip():
        raise ValueError("Custom TTS text is empty")

    from kokoro import KPipeline

    print("[INFO] Loading Kokoro TTS model for custom line...")
    pipeline = KPipeline(lang_code="a")  # American English

    samples = []
    for result in pipeline(text, voice=TTS_VOICE):
        if result.audio is not None:
            samples.append(result.audio)

    if not samples:
        raise RuntimeError(f"TTS produced no audio for custom text: {text!r}")

    import numpy as np
    audio = np.concatenate(samples)
    sf.write(out_path, audio, 24000)
    print(f"[OK] Custom TTS saved: {out_path}")
    return out_path