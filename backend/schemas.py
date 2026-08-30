from pydantic import BaseModel

class ShotCreate(BaseModel):
    session_id: int
    shot_number: int
    elbow_angle_deg: float
    head_movement_cm: float
    cue_deviation_deg: float
    is_success: bool