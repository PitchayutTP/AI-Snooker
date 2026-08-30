from fastapi import FastAPI
from routers import shots

app = FastAPI(title="AI Snooker Coach API")
app.include_router(shots.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "Backend is running securely"}

@router.get("/shots/{session_id}")
async def get_session_stats(session_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        sql_select = """
            SELECT shot_number, elbow_angle_deg, head_movement_cm, is_success
            FROM shots 
            WHERE session_id = %s
            ORDER BY shot_number ASC;
        """
        cursor.execute(sql_select, (session_id,))
        records = cursor.fetchall()
        
        shots_data = []
        for row in records:
            shots_data.append({
                "shot_number": row[0],
                "elbow_angle_deg": float(row[1]),
                "head_movement_cm": float(row[2]),
                "is_success": row[3]
            })
            
        return {"session_id": session_id, "data": shots_data}
        
    except Exception as e:
        print("❌ Select Error:", e)
        raise HTTPException(status_code=400, detail="ดึงข้อมูลไม่สำเร็จ")
    finally:
        cursor.close()
        conn.close()