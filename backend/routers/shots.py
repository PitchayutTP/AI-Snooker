from fastapi import APIRouter, HTTPException
from schemas import ShotCreate
from database import get_db_connection

router = APIRouter()

@router.post("/shots")
async def record_shot(shot: ShotCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        sql_insert = """
            INSERT INTO shots 
            (session_id, shot_number, elbow_angle_deg, head_movement_cm, cue_deviation_deg, is_success)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING shot_id;
        """
        
        values = (
            shot.session_id, 
            shot.shot_number, 
            shot.elbow_angle_deg, 
            shot.head_movement_cm, 
            shot.cue_deviation_deg, 
            shot.is_success
        )
        
        cursor.execute(sql_insert, values)
        new_shot_id = cursor.fetchone()[0]
        conn.commit()
        
        return {
            "status": "success",
            "message": "บันทึกช็อตสำเร็จ",
            "shot_id": new_shot_id
        }
        
    except Exception as e:
        conn.rollback()
        print("❌ Insert Error:", e)
        raise HTTPException(status_code=400, detail="บันทึกข้อมูลไม่สำเร็จ")
        
    finally:
        cursor.close()
        conn.close()