# โมเดลที่ค้นพบสำหรับ AI-Snooker

## ดาวน์โหลดแล้ว

- ผู้เผยแพร่: Binssin/PoolBall
- แหล่ง: https://huggingface.co/Binssin/PoolBall
- Model card: https://huggingface.co/Binssin/PoolBall/blob/38eb6c7f0ae8c30db5ab1c28870128695490ec35/model_card.md
- Revision: 38eb6c7f0ae8c30db5ab1c28870128695490ec35
- ไฟล์: backend/models/poolball-yolov8n-community.pt
- ขนาด: 6244387 bytes
- SHA256: 7f3079fdf942b7f2df062a70a63c0e74d34b8fa8b200d06236cdc684ac144b6e
- ผู้เผยแพร่ระบุ YOLOv8n และ license MIT ใน model_card.md
- ตรวจโครงสร้าง ZIP และ pickle opcodes แบบไม่ execute checkpoint แล้ว
- ชื่อคลาสใน weights จริง: 0 = ball (คลาสเดียว)

## ข้อจำกัดกับระบบปัจจุบัน

โมเดลนี้ตรวจตำแหน่งลูก แต่ไม่ได้แยกลูกขาวและลูกแดงในตัว
ระบบปัจจุบันต้องมี cue_ball และ target_ball จึงไม่ควรเปลี่ยนชื่อไฟล์นี้เป็น snooker.pt
แล้วอ้างว่าใช้งานได้ครบโดยไม่ปรับวิธีจำแนกบทบาท
ยังไม่ได้ทดสอบ inference หรือความแม่นยำบนโต๊ะจริง และไม่ได้เปลี่ยนค่าเริ่มต้นในระบบ
ไม่ใช้ค่าความแม่นยำใน model card เป็นผลทดลองของโครงงานนี้

แนวทางใช้:
1. ใช้ checkpoint นี้แทนโมเดลตั้งต้นในการฝึกด้วยข้อมูลสองคลาสของเรา
   ดู MODEL-TRAINING.md (เปลี่ยน --model เป็นพาธไฟล์นี้)
2. ถ้าต้องการทดลองโดยไม่ฝึกทันที ต้องเพิ่มขั้นตอน YOLO ตรวจลูก + HSV จำแนกขาว/แดง
   และอธิบายวิธีผสมนี้ในรายงาน การ map คลาส ball เดียวเป็นทั้งสองบทบาทอย่างเดียวทำไม่ได้

## แหล่งอื่นที่ตรวจ

- Zulfi2003/snookerball_tracking มี trained best.pt แต่ตรวจพบคลาสเดียวจาก weights
  https://github.com/Zulfi2003/snookerball_tracking/tree/main/models/runs/detect/train3/weights
- HereLiesAz/cuedetat-pool-detector มี model card ระบุ YOLOv8 และ AGPL-3.0
  แต่ metadata ของส่วนที่เปิดเผยระบุ pool-table/pool-table-hole/pool-table-side
  ไม่ใช่โมเดลแยก white/red ที่ใช้แทนได้โดยตรง
  https://huggingface.co/HereLiesAz/cuedetat-pool-detector
- jchadwick/billiards มี YOLOv8n weights แต่เอกสาร config ไม่ยืนยันคลาส white/red
  และข้อมูลจำนวนคลาสในเอกสารไม่สอดคล้องกัน จึงยังไม่เลือกใช้
  https://huggingface.co/jchadwick/billiards/tree/main/v1

สรุป: ได้ weights สำหรับเป็นโมเดลตั้งต้นจริงแล้ว แต่ยังไม่พบโมเดลที่ยืนยันได้ว่า
แยกลูกขาวและลูกแดงพร้อมใช้กับโค้ดปัจจุบันโดยไม่ปรับหรือฝึกต่อ
