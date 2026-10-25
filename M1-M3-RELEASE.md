# Prototype v1 — M1–M3 ตามรายงาน (software 0.4.0)

## โค้ดที่เพิ่ม

- PILOT/ASSESSMENT และแผนจำนวนผล PASS/FAIL (N), อัตราผ่าน, เหตุผล
- ป้องกันเริ่มรอบประเมินด้วย DEMO/เกณฑ์ไม่ยืนยัน/แผนไม่ครบ
- รอบที่ใช้กล้องบนเพื่อประเมินต้องเลือก YOLO และมี calibration image size
- ป้องกันบันทึกเกิน N และจบรอบประเมินก่อนครบ ยุติรอบได้โดยไม่แสดงว่าผ่าน
- Moving Average ที่ไม่เติมข้อมูลหาย เก็บ raw/display แยก และเลือกวิธีประเมินชัดเจน
- ค่าคุณภาพข้อมูลและช่วงฐานปรับได้ตามการนำร่อง เก็บ valid counts รายสัญญาณ
- ตรวจคลาสโมเดล YOLO, ByteTrack เป็นค่าเริ่มต้น และ model hash
- เก็บภาพดิบขณะบันทึกแบบ opt-in, ZIP หลักฐานแยกสิทธิ์บัญชี, แจ้งภาพที่ขาดหาย
- เก็บภาพ dataset, ตรวจ YOLO labels, แบ่งตาม capture group และตรวจภาพซ้ำ
- ฝึก/ส่งออก YOLOv8 และประเมิน held-out test โดยบันทึก argument/hash
- ส่งออก predictions/worksheet และสร้าง reference จาก labels ที่กำกับอิสระ
- MAE/RMSE/bias แยกหน่วย, Precision/Recall ที่เกณฑ์คงที่, Tracking error/missing/ID switches
- Frontend components สำหรับโมเดล แผนประเมิน ความก้าวหน้า และดาวน์โหลดหลักฐาน

ยังใช้ PostgreSQL เท่านั้น เก็บแผนใน criteria JSON และข้อมูลใหม่ใน evidence JSON
ไม่ต้องเพิ่มตารางหรือลบข้อมูลเดิม ไม่เปิดใช้ M4 และไม่ได้ push GitHub

## คู่มือ

- TABLE-TRIAL.md: เปิดระบบและตั้งกล้อง
- MODEL-TRAINING.md: dataset/YOLO/แผน N/Moving Average
- EVALUATION.md: เก็บภาพอ้างอิงและประเมินผล

## ตรวจแล้ว

- Offline checks 19 รายการ: geometry, สี/ID, calibration, protocol, smoothing,
  metrics, dataset split, recording path/overwrite และคุณภาพข้อมูล
- Frontend lint/build และ render checks 10 สถานะ
- Python syntax และ API OpenAPI/schema validation โดยไม่เชื่อมฐานข้อมูล
- PowerShell syntax และ CLI help ของเครื่องมือหลัก

## ขอบเขตที่ยังต้องใช้ข้อมูล/อุปกรณ์จริง

- ยังไม่ได้ฝึก YOLO กับภาพโต๊ะจริงในการทำงานครั้งนี้ ZIP ไม่รวม dataset/weights
- ต้องทำ annotation และฝึก/เลือกโมเดลจริงก่อนใช้รอบประเมินกล้องบน
- ยังไม่ได้ยืนยันความแม่นยำ/การใช้งานกล้องสองตัวกับโต๊ะจริง
- ยังไม่ได้ตรวจการบันทึกครบวงจรบน PostgreSQL จริงในครั้งนี้
- ตัวเลขเกณฑ์ N, อัตราผ่าน และค่าคลาดเคลื่อน ต้องกำหนดจากแหล่งอ้างอิง/การนำร่อง
- Follow-through/แนวเล็ง/เหลี่ยมกระทบยังเป็นค่าประมาณ ไม่ใช่เซนเซอร์วัดจุดสัมผัสจริง
