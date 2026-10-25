# ฝึกและทดสอบ YOLOv8 สำหรับ M1–M3 ตามรายงาน

## สิ่งที่ชุดโค้ดนี้ทำให้แล้ว

- M1 ใช้ MediaPipe โดยไม่ฝึกโมเดลท่าทางใหม่
- M2 ใช้มาร์กเกอร์คิว และใช้ YOLO เมื่อเปิดกล้องด้านบนเพื่อประมาณเวลาลูกเริ่มเคลื่อน
- M3 มีทั้ง HSV สำหรับนำร่อง และ YOLO สำหรับรอบประเมินตามรายงาน
- มีเครื่องมือเก็บภาพ ตรวจ annotation แบ่งชุดข้อมูล ฝึก และประเมินผล

โค้ดไม่สามารถแทนข้อมูลและ annotation จริงได้ การมีไฟล์ yolov8n.pt ทั่วไป
ยังไม่ใช่โมเดลตรวจลูกสนุกเกอร์ ระบบจะตรวจคลาสก่อนใช้งาน
ไม่รวม M4 ในขั้นตอนนี้

## 1. ติดตั้งส่วน YOLO

จาก root ของโปรเจกต์:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-camera.ps1 -Yolo
```

ตัวเลือกนี้ติดตั้ง Ultralytics/PyTorch และ dependencies เพิ่มใน .venv อาจใช้เวลาดาวน์โหลด
ไม่เริ่มฝึก ไม่เปิดกล้อง และไม่สร้าง weights ลูกสนุกเกอร์แทนผู้จัดทำ
ตรวจ environment หลังติดตั้งด้วย `.\.venv\Scripts\python.exe -m pip check`

## 2. เก็บและกำกับภาพ

ปิดกล้องจากหน้าเว็บก่อนใช้ตัวเก็บภาพ แล้วรันจาก root:

```powershell
.\.venv\Scripts\python.exe backend/tools/capture_dataset.py --camera 1 --group session-a --out data/collection/session-a
```

- กด S เพื่อเก็บภาพ Q เพื่อจบ
- เปลี่ยนรอบถ่าย แสง ตำแหน่ง/ความเร็วลูก และกลุ่มข้อมูล ให้ครอบคลุมสภาพที่จะทดลอง
- ทำ annotation เป็น YOLO detection: `class x_center y_center width height` พิกัด normalized 0–1
- คลาส **0 = cue_ball**, **1 = target_ball**
- สร้างไฟล์ label ชื่อเดียวกับภาพใน labels/ หลังทำ annotation
- ไฟล์ label ว่างหมายถึงผู้กำกับยืนยันว่าไม่มีวัตถุ ห้ามสร้างไฟล์ว่างแทนภาพที่ยังไม่ได้กำกับ
- ไฟล์ capture.csv บันทึกพาธภาพ/label/กลุ่มไว้ให้ แต่ไม่สร้าง label อัตโนมัติ

รวมรายการลง manifest CSV ตาม configs/dataset-manifest.example.csv
พาธ image และ label อ้างอิงโฟลเดอร์ที่วาง manifest เช่น
`session-a/images/...jpg` และ `session-a/labels/...txt`
ใช้ group เดียวกันสำหรับภาพจากวิดีโอหรือรอบถ่ายเดียวกัน เพื่อป้องกันข้อมูลรั่วข้ามชุด

## 3. ตรวจและแบ่งชุดข้อมูล

```powershell
.\.venv\Scripts\python.exe backend/tools/prepare_dataset.py --manifest data/collection/manifest.csv --out data/dataset-v1 --seed 42
```

- กำหนด split เป็น train/val/test ทุกแถวเองได้ หรือเว้นทุกแถวให้โปรแกรมแบ่งตาม group
- ต้องมีอย่างน้อยสามกลุ่มเพื่อให้แบ่งได้ ไม่ใช่การยืนยันว่าข้อมูลสามกลุ่มเพียงพอต่อการฝึก
- ไม่แบ่งเฟรมจากกลุ่มเดียวกันข้ามชุด ตรวจภาพซ้ำด้วย SHA256 และตรวจ bbox/คลาส
- Training ต้องมีทั้งสองคลาส ทุก split ต้องไม่ว่าง
- Output ต้องเป็นโฟลเดอร์ใหม่ ไม่มีการทับ dataset เดิม
- ได้ data.yaml และ manifest.json พร้อมกลุ่ม ชุดข้อมูล และ hash ของภาพ/label

สัดส่วนเริ่มต้น val/test อย่างละ 0.2 เป็นค่าของเครื่องมือ เปลี่ยนด้วย
--val-fraction และ --test-fraction ตามแผนจริง แล้วรายงานจำนวนภาพและกลุ่มจริง
ไม่ย้ายโฟลเดอร์ dataset หลังเตรียม เพราะ data.yaml ระบุพาธเต็ม

## 4. ฝึกโมเดล

ตัวอย่างคำสั่ง (50 epochs/ขนาดภาพ/batch เป็นตัวอย่างการรัน ไม่ใช่ค่าที่รับรองจากรายงาน):

```powershell
.\.venv\Scripts\python.exe backend/tools/train_detector.py --data data/dataset-v1/data.yaml --model yolov8n.pt --epochs 50 --imgsz 640 --batch 8 --device cpu --name snooker-v1 --export-model backend/models/snooker-v1.pt
```

เลือก hyperparameters ด้วยชุด validation และข้อจำกัดของเครื่อง ก่อนล็อกโมเดลสำหรับทดสอบ
หากใช้ชื่อ yolov8n.pt และไม่มีไฟล์ Ultralytics อาจดาวน์โหลดน้ำหนักเริ่มต้นเมื่อสั่งฝึก
ใช้ชื่อ YOLOv8 ให้ตรงรายงาน ไม่เปลี่ยนเป็นตระกูลอื่นโดยไม่ปรับวิธีดำเนินงาน

ได้ weights/best.pt และ training-info.json ใน data/training/snooker-v1/
พร้อม argument, รุ่น Ultralytics, dataset hash และ model hash
ตัวเลือก export-model คัดลอก weights ที่ฝึกจริงไป backend/models โดยไม่ทับไฟล์เดิม
ตัวเรียก train_balls.py เดิมส่งต่อมายังเครื่องมือนี้ แต่ต้องเพิ่ม --name ตามรูปแบบใหม่

## 5. ประเมิน held-out test

```powershell
.\.venv\Scripts\python.exe backend/tools/validate_detector.py --model backend/models/snooker-v1.pt --data data/dataset-v1/data.yaml --split test --device cpu --name snooker-v1-test
```

บันทึกผลที่ Ultralytics คำนวณจริงและ hash ใน data/validation/snooker-v1-test/
ห้ามใช้ผล test ปรับ hyperparameters ซ้ำแล้วเรียกผลเดิมว่า held-out
ผล PR/mAP ของ Ultralytics ใช้ protocol ของไลบรารี ถ้าต้องการ Precision/Recall
ที่ IoU/confidence คงที่ ให้ใช้ EVALUATION.md และระบุเกณฑ์จับคู่ก่อนทดลอง

API train/val อ้างอิงคู่มือทางการ:
- https://docs.ultralytics.com/modes/train/
- https://docs.ultralytics.com/modes/val/

## 6. ใช้ในหน้าเว็บ

1. เปิดระบบด้วย PostgreSQL ตาม TABLE-TRIAL.md
2. ตั้งค่ากล้องและสอบเทียบโต๊ะ
3. ใน "โมเดลและการกรองข้อมูลตามรายงาน" เลือก YOLOv8
4. ระบุ `models/snooker-v1.pt` และกดตรวจไฟล์/คลาส
5. คลาสมาตรฐานต้องเป็น cue_ball/target_ball หากโมเดลเดิมใช้ชื่ออื่น ให้ map เช่น
   `"ball_roles":{"white":"cue_ball","red":"target_ball"}` ใน JSON
6. กดตรวจความพร้อม ดูกรอบตรวจจับและทดลองนำร่องก่อนสร้างเกณฑ์

M1 และ M2 ที่ใช้กล้องด้านข้างอย่างเดียวไม่บังคับโมเดลลูก
รอบ ASSESSMENT ที่ใช้กล้องด้านบนจะไม่ยอมใช้ HSV แทน YOLO ตามรายงาน
การเปลี่ยน detector/weights/filter/กล้อง ถือเป็นการเปลี่ยนการตั้งค่าที่มีผลต่อการวัด

## 7. จำนวนครั้งและผลรายรอบ

- หน้าสร้างเกณฑ์มีแผน N, อัตราผ่านขั้นต่ำ และเหตุผลจากการนำร่อง ไม่มีตัวเลขมาตรฐานใส่ให้
- เลือก PILOT เพื่อเก็บค่าก่อนยืนยันแผน ไม่ตัดสินการผ่านบทเรียนจากรอบนี้
- เลือก ASSESSMENT เพื่อใช้เกณฑ์ยืนยันและข้อมูล LIVE
- PASS/FAIL นับเข้า N ส่วน INVALID/ABORTED ไม่นับ
- ครบ N แล้วเริ่มครั้งใหม่ไม่ได้ ต้องจบรอบจึงตัดสิน PASS/FAIL รายรอบ
- ถ้าไม่ครบ N ให้ทำต่อหรือเลือกยุติรอบ ไม่แสดงว่าผ่านเพราะทำครบจำนวนการกดปุ่ม
- ไม่ใช่ระบบดาว/ปลดล็อก และผลผ่านรอบไม่ยืนยันว่าทักษะดีขึ้นเพราะระบบ

## 8. Moving Average

ปรับ window ในหน้าโมเดลได้ 1–31 เฟรม ค่า 1 คือไม่กรอง
กรองค่าร่างกาย/จุดอ้างอิงคิวเพื่อแสดงผล แต่ใช้ค่าดิบประเมินเป็นค่าเริ่มต้น
หากเลือกใช้ค่ากรองประเมิน ต้องกำหนดเหตุผลและใช้เงื่อนไขเดียวกันในรอบที่เปรียบเทียบ
เก็บ raw_measurements และ display_measurements ใน JSON ไม่เติมจุดที่ขาดหาย
ไม่กรองเส้นทางลูกเพราะอาจเลื่อนเวลาประมาณเหตุการณ์กระทบ
เมื่อเริ่มครั้งใหม่หรือเกิดช่องว่างข้อมูล จะ reset ประวัติกรอง

หาก FPS ต่ำจนมีเฟรมในช่วงฐานไม่พอ ให้ปรับช่วงเก็บท่าตั้งต้นในหน้าตั้งค่า
และคงท่าหลังเริ่มบันทึกให้ครบช่วงที่ตั้งไว้ ตรวจจำนวนเฟรมจริงก่อนกำหนด min_valid_frames/min_valid_ratio
ค่าเริ่มต้น 5 เฟรม/0.7 เป็นพารามิเตอร์นำร่องของโปรแกรม ไม่ใช่เกณฑ์มาตรฐานทางกีฬา
