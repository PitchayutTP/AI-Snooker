import cv2
import mediapipe as mp
import math
import requests
import numpy as np

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
API_URL = "http://127.0.0.1:8000/api/shots"
SESSION_ID, shot_counter = 104, 1

def calc_angle(a, b, c):
    rad = math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0])
    ang = abs(rad * 180.0 / math.pi)
    return 360 - ang if ang > 180.0 else ang

cap = cv2.VideoCapture(0)
with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        elbow_angle = 0.0
        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            shoulder = [lm[12].x, lm[12].y]
            elbow = [lm[14].x, lm[14].y]
            wrist = [lm[16].x, lm[16].y]
            elbow_angle = calc_angle(shoulder, elbow, wrist)
            cv2.putText(image, f"{elbow_angle:.2f}", tuple(np.multiply(elbow, [640,480]).astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        cv2.imshow('AI Snooker', image)
        
        key = cv2.waitKey(10) & 0xFF
        if key == ord('s'):  # กด 's' เพื่อยิง API
            payload = {"session_id": SESSION_ID, "shot_number": shot_counter, "elbow_angle_deg": round(elbow_angle, 2), "head_movement_cm": 1.5, "cue_deviation_deg": 0.2, "is_success": 85 <= elbow_angle <= 95}
            try:
                print("Response:", requests.post(API_URL, json=payload).json())
                shot_counter += 1
            except Exception as e: print("API Error:", e)
        elif key == ord('q'): break
cap.release()
cv2.destroyAllWindows()