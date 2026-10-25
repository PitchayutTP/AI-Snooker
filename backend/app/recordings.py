"""Optional raw reference frames, scoped to a profile/session/attempt."""
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).resolve().parents[2]
RECORDINGS=ROOT/'data/recordings'


def recorded_path(value,profile_id):
    path=(ROOT/value).resolve()
    allowed=(RECORDINGS/str(int(profile_id))).resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower()!='.jpg':raise ValueError('Invalid recording path')
    return path


class FrameRecorder:
    def __init__(self,profile_id,session_id,attempt_id):
        self.folder=RECORDINGS/str(int(profile_id))/str(UUID(session_id))/str(UUID(attempt_id))
        self.folder.mkdir(parents=True,exist_ok=False)

    def write(self,frames,index):
        import cv2
        result={}
        for camera,frame in frames.items():
            if camera not in ('side','top'):raise ValueError('Unknown recording camera')
            folder=self.folder/camera;folder.mkdir(exist_ok=True)
            path=folder/f'{index:06d}.jpg'
            ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,95])
            if not ok:raise ValueError('Cannot encode reference frame')
            with path.open('xb') as output:output.write(encoded.tobytes())
            result[camera]=path.relative_to(ROOT).as_posix()
        return result
