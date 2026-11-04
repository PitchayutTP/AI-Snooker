"""Download a version-pinned official MediaPipe bundle; never overwrite models."""

import argparse
import hashlib
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend/models"


def validate_bundle(path):
    with zipfile.ZipFile(path) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("Corrupt pose model bundle")
        required = {"pose_detector.tflite", "pose_landmarks_detector.tflite"}
        if not required.issubset(bundle.namelist()):
            raise ValueError("Missing MediaPipe pose detector/landmarker")


def download(variant="full"):
    if variant not in ("lite", "full", "heavy"):
        raise ValueError("Unknown pose variant")
    url = (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        f"pose_landmarker_{variant}/float16/1/pose_landmarker_{variant}.task"
    )
    target = ROOT / (
        "pose_landmarker.task"
        if variant == "lite"
        else f"pose_landmarker_{variant}.task"
    )
    ROOT.mkdir(parents=True, exist_ok=True)
    if target.exists():
        validate_bundle(target)
        print(f"Already exists (kept): {target}")
        return target
    temporary = None
    try:
        with urllib.request.urlopen(url, timeout=120) as source:
            with tempfile.NamedTemporaryFile(
                dir=ROOT, suffix=".download", delete=False
            ) as output:
                temporary = Path(output.name)
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
        validate_bundle(temporary)
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.rename(target)
        metadata = {
            "variant": variant,
            "version": 1,
            "url": url,
            "sha256": digest,
            "note": "Official pretrained bundle, not fine-tuned for snooker. SHA256 records this download; not publisher signature verification.",
        }
        target.with_suffix(".json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        print(f"Downloaded: {target}\nSHA256: {digest}")
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["lite", "full", "heavy"], default="full")
    download(parser.parse_args().variant)


if __name__ == "__main__":
    main()
