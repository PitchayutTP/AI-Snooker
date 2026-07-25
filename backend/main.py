from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import List

# สร้างตัวแอปพลิเคชัน
app = FastAPI(title="Snooker AI Coach API")

# ==========================================
# 1. สร้าง Schema (Data Models) เพื่อดักจับข้อมูลที่ยิงเข้ามา
# ==========================================
class UserCreate(BaseModel):
    username: str
    password: str

class SessionStart(BaseModel):
    user_id: int
    module_id: int

class ShotRecord(BaseModel):
    session_id: int
    shot_number: int
    elbow_angle_deg: float
    head_movement_cm: float
    cue_deviation_deg: float
    is_success: bool

# ==========================================
# 2. สร้าง Endpoints (Routes) สำหรับยิง API
# ==========================================

# Endpoint 1: สร้างผู้เล่นใหม่
@app.post("/api/users")
async def create_user(user: UserCreate):
    return {
        "status": "success",
        "message": f"User {user.username} created successfully",
        "user_id": 1
    }

# Endpoint 2: ดึงข้อมูลความคืบหน้า (ใช้ GET ไม่ต้องส่ง Body)
@app.get("/api/users/{user_id}/progress")
async def get_user_progress(user_id: int):
    return {
        "user_id": user_id,
        "username": "Pitchayut_67",
        "progress": [
            {"module_id": 1, "module_name": "The Foundation", "status": "passed", "stars_earned": 3},
            {"module_id": 2, "module_name": "The Delivery", "status": "unlocked", "stars_earned": 0},
            {"module_id": 3, "module_name": "Basic Potting", "status": "locked", "stars_earned": 0}
        ]
    }

# Endpoint 3: กดเริ่มซ้อม
@app.post("/api/sessions")
async def start_session(session: SessionStart):
    return {
        "status": "success",
        "message": "Session started",
        "session_id": 104,
        "start_time": datetime.now().isoformat()
    }

# Endpoint 4: กดจบการซ้อม
@app.put("/api/sessions/{session_id}/end")
async def end_session(session_id: int):
    return {
        "status": "success",
        "message": f"Session {session_id} ended",
        "is_passed": True
    }

# Endpoint 5: บันทึกข้อมูลสถิติรายช็อต (อันนี้ใช้ทดสอบยิงรัวๆ)
@app.post("/api/shots")
async def record_shot(shot: ShotRecord):
    # ปรินต์ข้อมูลออกทาง Terminal ให้ดูว่ารับค่ามาได้จริง
    print(f"📥 Received Shot #{shot.shot_number} | Angle: {shot.elbow_angle_deg} | Deviation: {shot.cue_deviation_deg}")
    
    return {
        "status": "success",
        "message": "Shot recorded",
        "data_received": shot.model_dump()
    }