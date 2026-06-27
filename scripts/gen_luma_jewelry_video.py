#!/usr/bin/env python3
"""
Luma Ray 3.2 image-to-video generator for jewelry commercial.

Usage (run locally on Mac):
  export FAL_KEY=your_fal_api_key_here
  python3 scripts/gen_luma_jewelry_video.py

Requirements:
  pip install requests
"""

import base64
import os
import sys
import time
import urllib.request
from pathlib import Path

IMAGE_PATH = Path.home() / "Downloads" / "photo-1611107683227-e9060eccd846-removebg-preview.png"
OUTPUT_PATH = Path.home() / "Downloads" / "vidcel_demo_jewelry_luma.mp4"
MODEL = "fal-ai/luma/agent/ray/v3.2/image-to-video"
PROMPT = (
    "Gold jewelry collection on a luxury marble surface, cinematic studio lighting, "
    "slow gentle push-in, ultra-realistic details, shallow depth of field, "
    "luxury jewelry commercial, 9:16 vertical"
)


def load_image_as_data_url(path: Path) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.suffix.lstrip(".")
    mime = "image/png" if ext == "png" else f"image/{ext}"
    return f"data:{mime};base64,{data}"


def submit_job(fal_key: str, image_url: str) -> str:
    import json
    import urllib.request

    payload = json.dumps({
        "image_url": image_url,
        "prompt": PROMPT,
        "duration": 5,
        "aspect_ratio": "9:16",
        "resolution": "1080p",
    }).encode()

    req = urllib.request.Request(
        f"https://queue.fal.run/{MODEL}",
        data=payload,
        headers={
            "Authorization": f"Key {fal_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    request_id = result.get("request_id")
    if not request_id:
        raise RuntimeError(f"No request_id in response: {result}")
    print(f"Job submitted. request_id: {request_id}")
    return request_id


def poll_result(fal_key: str, request_id: str, timeout: int = 600) -> dict:
    import json

    status_url = f"https://queue.fal.run/{MODEL}/requests/{request_id}/status"
    result_url = f"https://queue.fal.run/{MODEL}/requests/{request_id}"
    deadline = time.time() + timeout

    while time.time() < deadline:
        req = urllib.request.Request(
            status_url,
            headers={"Authorization": f"Key {fal_key}"},
        )
        with urllib.request.urlopen(req) as resp:
            status = json.loads(resp.read())

        state = status.get("status", "")
        print(f"  status: {state}", flush=True)

        if state == "COMPLETED":
            req2 = urllib.request.Request(
                result_url,
                headers={"Authorization": f"Key {fal_key}"},
            )
            with urllib.request.urlopen(req2) as resp2:
                return json.loads(resp2.read())

        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Job {state}: {status}")

        time.sleep(10)

    raise TimeoutError(f"Job did not complete within {timeout}s")


def download_video(video_url: str, dest: Path) -> None:
    print(f"Downloading video from {video_url} ...")
    urllib.request.urlretrieve(video_url, dest)
    print(f"Saved to {dest}")


def main() -> None:
    fal_key = os.environ.get("FAL_KEY", "").strip()
    if not fal_key:
        sys.exit("Error: FAL_KEY environment variable is not set.\n"
                 "  export FAL_KEY=your_fal_api_key_here")

    if not IMAGE_PATH.exists():
        sys.exit(f"Error: Image not found at {IMAGE_PATH}")

    print(f"Encoding image: {IMAGE_PATH}")
    image_url = load_image_as_data_url(IMAGE_PATH)
    print(f"Image size (base64): {len(image_url):,} chars")

    request_id = submit_job(fal_key, image_url)

    print("Waiting for video generation (may take 1-3 minutes)...")
    result = poll_result(fal_key, request_id)

    video_url = None
    if isinstance(result.get("video"), dict):
        video_url = result["video"].get("url")
    elif isinstance(result.get("video"), str):
        video_url = result["video"]

    if not video_url:
        sys.exit(f"Error: could not find video URL in result:\n{result}")

    download_video(video_url, OUTPUT_PATH)
    print(f"\nDone! Video saved to:\n  {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
