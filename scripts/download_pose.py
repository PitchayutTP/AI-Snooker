"""Download the official MediaPipe Pose Landmarker Lite model, without replacing it."""
import hashlib
import tempfile
import urllib.request
from pathlib import Path

URL = ('https://storage.googleapis.com/mediapipe-models/pose_landmarker/'
       'pose_landmarker_lite/float16/1/pose_landmarker_lite.task')
TARGET = Path(__file__).resolve().parents[1] / 'backend/models/pose_landmarker.task'


def main():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        print(f'Already exists (kept): {TARGET}')
        return
    temporary = None
    try:
        with urllib.request.urlopen(URL, timeout=120) as source:
            with tempfile.NamedTemporaryFile(dir=TARGET.parent, suffix='.download', delete=False) as output:
                temporary = Path(output.name)
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
        if temporary.stat().st_size < 1_000_000:
            raise ValueError('Downloaded model is unexpectedly small')
        # rename refuses to overwrite a concurrently created model on Windows.
        temporary.rename(TARGET)
        print(f'Downloaded: {TARGET}')
        print(f'SHA256: {hashlib.sha256(TARGET.read_bytes()).hexdigest()}')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
