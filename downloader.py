import os
import subprocess


def download_clips(urls: list, output_dir: str, ffmpeg_path: str) -> list:
    """
    Downloads each URL as an MP4 into output_dir using yt-dlp and forces FFmpeg
    merging through the provided ffmpeg_path.
    Returns a list of successfully downloaded file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []

    ffmpeg_dir = os.path.dirname(ffmpeg_path)

    for i, url in enumerate(urls):
        output_path = os.path.join(output_dir, f"clip_{i+1:02d}.mp4")

        print(f"\n[INFO] Downloading {i+1}/{len(urls)}: {url}")

        cmd = [
            "yt-dlp",
            "--ffmpeg-location", ffmpeg_dir,
            "-f", "bv*+ba/b",
            "--merge-output-format", "mp4",
            "--no-playlist",
            "-o", output_path,
            url,
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"[ERROR] Failed to download: {url}")
            lines = (result.stderr or "").strip().splitlines()
            if not lines:
                lines = (result.stdout or "").strip().splitlines()
            for line in lines[-15:]:
                print(f"       {line}")
            continue

        if not os.path.exists(output_path):
            print(f"[ERROR] Download reported success but file not found: {output_path}")
            continue

        if os.path.getsize(output_path) == 0:
            print(f"[ERROR] Downloaded file is empty: {output_path}")
            continue

        print(f"[OK] Saved: {output_path}")
        downloaded.append(output_path)

    return downloaded