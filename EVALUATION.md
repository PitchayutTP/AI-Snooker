# ประเมิน M1–M3 ด้วยข้อมูลอ้างอิง

## เก็บหลักฐานเฟรมที่ตรงกับผลตรวจจับ

1. ในหน้าโมเดล ติ๊ก "เก็บภาพดิบแต่ละเฟรมขณะบันทึก" เฉพาะรอบเก็บข้อมูลอ้างอิง
2. บันทึกการฝึกและจบรอบ ภาพเก็บในเครื่อง Backend ภายใต้ data/recordings แยกบัญชี/รอบ/ครั้ง
3. ดาวน์โหลด ZIP หลักฐานและภาพดิบจากหน้าสรุป แล้วแตกไฟล์
4. ZIP มี session.json และ recordings/<attempt-id>/side หรือ top/000000.jpg
5. ลำดับเลขภาพตรงกับ index ของ samples ในหลักฐาน ไม่ใช้วิดีโอจากคนละเวลามาจับคู่โดยไม่ตรวจสอบ
6. ถ้าภาพถูกลบไปแล้ว bundle_summary จะแจ้งจำนวน missing_images ไม่ถือว่ามีหลักฐานครบ

การเก็บ JPEG เพิ่มเวลา I/O และพื้นที่ดิสก์ ต้องรายงานว่าเปิดการเก็บภาพหรือไม่
ความเร็ว/ความล่าช้าเปรียบเทียบภายใต้การตั้งค่าเดียวกัน ภาพไม่ถูกอัปโหลดภายนอก

## แปลงผลเป็นไฟล์สำหรับเทียบ

จาก root ของโปรเจกต์ ระบุไฟล์ session.json ที่แตกจาก ZIP:

```powershell
.\.venv\Scripts\python.exe backend/tools/export_trial.py --session data/trial-evidence/session.json --attempt-id YOUR_ATTEMPT_UUID --coordinates image --unit pixel --out data/comparison-v1
```

ได้ predictions.json และ measurements.csv คำสั่งไม่สร้าง ground truth ให้
ใช้ --coordinates table --unit mm หากต้องการเทียบพิกัดโต๊ะที่สอบเทียบเป็นมิลลิเมตร
อย่าเปลี่ยนชื่อหน่วยเป็น mm ถ้าตอนสอบเทียบใช้หน่วยอื่น

## Precision/Recall และ Tracking จากภาพ

กำกับภาพด้านบนอย่างอิสระเป็น YOLO label: 0 cue_ball, 1 target_ball
ชื่อ 000000.txt ตรงกับ 000000.jpg ไม่คัดลอก bbox ที่โมเดลทำนายมาเป็นค่าจริง
ไฟล์ว่างหมายถึงยืนยันไม่มีวัตถุ ส่วนไฟล์ที่ไม่มีจะถูกนับเป็น unlabelled ไม่ใช่ negative

```powershell
.\.venv\Scripts\python.exe backend/tools/reference_from_labels.py --predictions data/comparison-v1/predictions.json --labels data/independent-labels --out data/comparison-v1/reference.json
```

ตัวแปลงนี้เหมาะกับแบบฝึกที่มีลูกขาวหนึ่งลูก ลูกแดงหนึ่งลูก ใช้ชื่อบทบาทเป็น identity
หากมีหลายลูกต่อบทบาท ต้องเตรียมรหัส ground truth เอง ไม่สมมุติว่าเป็นลูกเดียวกัน
ตำแหน่งอ้างอิงคือศูนย์กลาง bbox ที่ผู้กำกับวาด หน่วย pixel ไม่ใช่พิกัดโลกอิสระ
การประเมิน calibration ต้องใช้จุดวัดจริงบนโต๊ะแยกต่างหาก

ตัวอย่างการประเมินที่เกณฑ์จับคู่คงที่ (ตัวเลขเป็นตัวอย่าง ต้องกำหนดและล็อกเกณฑ์ตามแผนจริง):

```powershell
.\.venv\Scripts\python.exe backend/tools/evaluate_trial.py detection --reference data/comparison-v1/reference.json --prediction data/comparison-v1/predictions.json --iou 0.5 --confidence 0.5 --out data/comparison-v1/detection.json
.\.venv\Scripts\python.exe backend/tools/evaluate_trial.py tracking --reference data/comparison-v1/reference.json --prediction data/comparison-v1/predictions.json --max-distance 10 --out data/comparison-v1/tracking.json
```

- Detection: confidence descending, class ตรงกัน, จับคู่หนึ่งต่อหนึ่งด้วย IoU
- ได้ TP/FP/FN, Precision/Recall แยกคลาสและรวม หากตัวหารศูนย์เป็น null
- Tracking: จับคู่คลาสเดียวกันด้วยระยะใกล้สุดภายใน max-distance ในหน่วยเดียวกัน
- ได้ mean position error, MAE แกน x/y, missing/untracked rate และ ID switches
- การนับ ID switches ใช้เฟรมอ้างอิงต่อเนื่องตามลำดับในไฟล์ และ reset เมื่อข้อมูลหาย
- เฟรมที่ไม่กำกับไม่ถูกนับเป็น negative รายงานจำนวน prediction frames ที่ไม่มี label แยกไว้
- ค่า confidence ของ HSV ไม่ใช่ความมั่นใจจากโมเดล ถ้าไม่มี field จะถือเป็น 1 เพื่อกรองข้อมูลเท่านั้น

## MAE ของมุม/ระยะ/เหลี่ยม/Follow-through

เปิด measurements.csv แล้วใส่ reference จากวิธีวัดที่กำหนดไว้ เช่น มุมจากจุดที่ผู้กำกับกำหนด
ระยะจากภาพอ้างอิง หรือเหลี่ยมที่จัดและตรวจยืนยัน ต้องจับคู่ช่วงเวลาและวิธีสรุปให้ตรงกับระบบ
อย่าใช้เพียงชื่อแบบฝึกที่เลือกเป็นหลักฐานว่าผู้ฝึกแทงได้เหลี่ยมนั้นจริง

```powershell
.\.venv\Scripts\python.exe backend/tools/evaluate_trial.py measurements --csv data/comparison-v1/measurements.csv --out data/comparison-v1/measurements-result.json
```

รายงานแยก metric และ unit มีจำนวนทั้งหมด จำนวนคู่ที่ประเมินได้/ไม่ได้ MAE, RMSE และ bias
ไม่รวมหน่วยต่างกัน และไม่แทนค่าที่ไม่มี reference เป็นศูนย์
ใช้ปลายคิว/แนวเล็งตามชนิดที่วัดจริง Follow-through ยังเป็นค่าประมาณจากมาร์กเกอร์และเวลาลูกเริ่มเคลื่อน
CSV ที่สรุปรายครั้งต้องใช้ค่ามุม/ระยะอ้างอิงที่สรุปจากช่วง active เดียวกัน ไม่เทียบค่าเฉลี่ยกับเฟรมเดียว

## PostgreSQL

ตรวจ connection และตารางแบบอ่านอย่างเดียวจาก Terminal ที่ตั้ง DATABASE_URL แล้ว:

```powershell
.\.venv\Scripts\python.exe backend/tools/check_database.py
```

เครื่องมือนี้ไม่ย้ายข้อมูล ไม่สร้างตาราง และไม่ลบฐานข้อมูล
หากยังไม่มีตาราง ให้เปิด Backend เพื่อ init ตารางก่อน แล้วสมัครบัญชี/บันทึก/เปิดประวัติจริง

## การตรวจโค้ดที่ไม่ใช้กล้อง/ฐานข้อมูล

```powershell
.\.venv\Scripts\python.exe backend/tools/verify_trial.py GeometryChecks
.\.venv\Scripts\python.exe backend/tools/verify_report_scope.py
```

การตรวจด้วยข้อมูลจำลองไม่แทนการประเมินความแม่นยำกับโต๊ะจริง
ต้องเก็บผลกล้องจริง/โมเดลที่ฝึกจริง/การทำงานผ่าน PostgreSQL เพิ่มก่อนรายงานผลโครงงาน
