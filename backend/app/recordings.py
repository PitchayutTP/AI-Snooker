"""Optional raw reference frames, scoped to a profile/session/attempt."""

import queue
import threading
from pathlib import Path
from statistics import median
from tempfile import NamedTemporaryFile
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
RECORDINGS = ROOT / "data/recordings"


def recorded_path(value, profile_id):
    path = (ROOT / value).resolve()
    allowed = (RECORDINGS / str(int(profile_id))).resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower() != ".jpg":
        raise ValueError("Invalid recording path")
    return path


def recorded_video_path(value, profile_id):
    path = (ROOT / value).resolve()
    allowed = (RECORDINGS / str(int(profile_id))).resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower() != ".webm":
        raise ValueError("Invalid video path")
    return path


class VideoRecorder:
    """Write a silent WebM per camera on a bounded background queue."""

    def __init__(self, profile_id, session_id, attempt_id):
        self.folder = (
            RECORDINGS / str(int(profile_id)) / str(UUID(session_id)) / str(UUID(attempt_id))
        )
        self.folder.mkdir(parents=True, exist_ok=False)
        self.frames = queue.Queue(maxsize=32)
        self.closing = threading.Event()
        self.error = None
        self.videos = {}
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def write(self, frames, stamp):
        if self.error:
            raise ValueError(self.error)
        if self.closing.is_set():
            raise ValueError("Video recording is closed")
        if not frames:
            return
        try:
            self.frames.put_nowait((frames, stamp))
        except queue.Full:
            self.error = "เขียนวิดีโอไม่ทัน คลิปอาจไม่ครบ ลดความละเอียดกล้องก่อนรอบถัดไป"
            self.closing.set()
            raise ValueError(self.error)

    def _run(self):
        import cv2

        writers = {}
        fps = 20.0
        try:
            while not self.closing.is_set() or not self.frames.empty():
                try:
                    frames, stamp = self.frames.get(timeout=0.1)
                except queue.Empty:
                    continue
                for camera, frame in frames.items():
                    if camera not in ("side", "top"):
                        raise ValueError("Unknown recording camera")
                    if camera not in writers:
                        height, width = frame.shape[:2]
                        size = (width - width % 2, height - height % 2)
                        path = self.folder / f"{camera}.webm"
                        writer = cv2.VideoWriter(
                            str(path), cv2.VideoWriter_fourcc(*"vp09"), fps, size
                        )
                        if not writer.isOpened():
                            writer.release()
                            raise ValueError("เครื่องนี้เปิดตัวเข้ารหัส WebM ไม่สำเร็จ")
                        writers[camera] = {
                            "writer": writer,
                            "size": size,
                            "start": stamp,
                            "last_stamp": stamp,
                            "last_frame": None,
                            "written": 0,
                            "captured": 0,
                            "path": path,
                        }
                    state = writers[camera]
                    if stamp < state["last_stamp"]:
                        raise ValueError("Video timestamps out of order")
                    if frame.shape[1::-1] != state["size"]:
                        frame = cv2.resize(frame, state["size"])
                    target = int((stamp - state["start"]) * fps + 1e-6)
                    # Hold the previous real image over variable capture intervals,
                    # so playback follows elapsed time instead of speeding up.
                    while state["written"] < target:
                        state["writer"].write(
                            state["last_frame"] if state["last_frame"] is not None else frame
                        )
                        state["written"] += 1
                    if state["written"] == target:
                        state["writer"].write(frame)
                        state["written"] += 1
                    state.update(last_frame=frame, last_stamp=stamp, captured=state["captured"] + 1)
        except Exception as exc:
            self.error = f"บันทึกวิดีโอไม่สำเร็จ: {exc}"
        finally:
            for camera, state in writers.items():
                state["writer"].release()
                if state["written"] and state["path"].is_file() and state["path"].stat().st_size:
                    self.videos[camera] = {
                        "path": state["path"].relative_to(ROOT).as_posix(),
                        "frames": state["written"],
                        "captured_frames": state["captured"],
                        "fps": fps,
                        "start_t": state["start"],
                        "end_t": state["last_stamp"],
                        "duration_s": state["last_stamp"] - state["start"],
                        "format": "webm",
                        "audio": False,
                    }

    def close(self):
        self.closing.set()
        self.thread.join(timeout=15)
        if self.thread.is_alive():
            raise ValueError("วิดีโอยังเขียนไม่เสร็จ กรุณารอสักครู่แล้วจบครั้งฝึกอีกครั้ง")
        return dict(self.videos)


def render_clip(samples, profile_id, camera):
    """Encode a silent replay on demand from the attempt's original camera frames."""
    import cv2
    import numpy as np

    frames = []
    for sample in samples:
        value = sample.get("recorded_images", {}).get(camera)
        if value:
            path = recorded_path(value, profile_id)
            if path.is_file():
                frames.append((sample["t"], path))
    if not frames:
        raise FileNotFoundError("No recorded frames")

    intervals = [
        right[0] - left[0] for left, right in zip(frames, frames[1:]) if right[0] > left[0]
    ]
    fps = min(60, max(1, 1 / median(intervals))) if intervals else 1
    with NamedTemporaryFile(prefix="snooker-", suffix=".webm", delete=False) as temporary:
        output = Path(temporary.name)
    writer = None
    written = 0
    try:
        try:
            for _, path in frames:
                try:
                    image = cv2.imdecode(
                        np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR
                    )
                except FileNotFoundError:
                    continue
                if image is None:
                    continue
                if writer is None:
                    height, width = image.shape[:2]
                    size = (width - width % 2, height - height % 2)
                    writer = cv2.VideoWriter(
                        str(output), cv2.VideoWriter_fourcc(*"vp09"), fps, size
                    )
                    if not writer.isOpened():
                        raise RuntimeError("WebM encoder unavailable")
                if image.shape[1::-1] != size:
                    image = cv2.resize(image, size)
                writer.write(image)
                written += 1
        finally:
            if writer is not None:
                writer.release()
        if not written or not output.stat().st_size:
            raise RuntimeError("Cannot generate clip")
        return output
    except Exception:
        output.unlink(missing_ok=True)
        raise
